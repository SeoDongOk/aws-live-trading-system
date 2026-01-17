
import asyncio
import sys
from projects.utils.logger_config import setup_logger


from datetime import datetime
from projects.modules.token import TokenManager
from projects.modules.kiwoom_base import KiwoomWebSocket
from projects.modules.trade import TradeExecutor
from projects.modules.account_state import AccountState
from projects.modules.api_client import KiwoomApiClient
from projects.modules.config import TradingConfig
from projects.controls.db_controll import insert_trade_order, upsert_account_info


# 로깅 설정
logger = setup_logger('trade')


class TradingMain:
    """메인 통합 클래스 (24시간 운영)"""
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.is_trading_active = False  # 현재 매매 활성 상태
        
        # 토큰 관리
        self.token_manager = TokenManager()
        
        self.trade_executor = TradeExecutor(self.token_manager, is_mock=True)
        # API 클라이언트
        self.api_client = KiwoomApiClient(
            self.token_manager,
            trade_executor=self.trade_executor  # 전달
        )

        
        # 계좌 상태
        self.account_state = AccountState()
        
        # WebSocket 클라이언트
        self.ws_client = KiwoomWebSocket(self.token_manager)
        
        self.trading_controller = None
        
        logger.info("TradingMain 초기화 완료")
    
    async def on_order_execution(self, data):
        """체결 콜백"""
        logger.info(f"체결 통보: {data['action']} {data['stock_code']}")
        
        # 체결 데이터를 DB에 저장
        try:
            order_data = {
                'order_no': data.get('order_no', ''),
                'stock_code': data.get('stock_code', ''),
                'stock_name': data.get('stock_name', ''),
                'action': data.get('action', ''),
                'order_status': data.get('order_status', ''),
                'exec_qty': data.get('exec_qty', 0),
                'exec_price': data.get('exec_price', 0),
                'remain_qty': data.get('remain_qty', 0),
                'created_at': datetime.now().isoformat()
            }
            insert_trade_order(order_data)
        except Exception as e:
            logger.error(f"체결 데이터 저장 실패: {e}")
        
        if self.trading_controller:
            await self.trading_controller.on_order_execution(data)
    
    async def initialize_account(self):
        """계좌 초기화 (잔고 조회)"""
        logger.info("계좌 정보 조회 중...")
        
        balance = await self.api_client.get_account_balance()
        if balance:
            self.account_state.update_from_api_response(balance)
            
            # 계좌 정보를 DB에 저장
            try:
                account_data = [{
                    'available_cash': balance.get('available_cash', 0),
                    'total_balance': balance.get('total_balance', 0),
                    'updated_at': datetime.now().isoformat()
                }]
                upsert_account_info(account_data)
            except Exception as e:
                logger.error(f"계좌 정보 저장 실패: {e}")
        else:
            logger.warning("잔고 조회 실패")
            logger.info("테스트용: 임시 예수금 1,000,000원 설정")
            self.account_state.available_cash = 1000000
    
    async def connect_websocket(self):
        """WebSocket 연결 및 구독"""
        if not self.ws_client.is_connected:
            logger.info("WebSocket 연결 중...")
            await self.ws_client.connect()
            await asyncio.sleep(2)
            
            # 체결 구독
            self.ws_client.register_callback('order_execution', self.on_order_execution)
            await self.ws_client.subscribe_order_execution()
            await asyncio.sleep(1)
            
            logger.info("WebSocket 연결 완료")
    
    async def start_trading(self):
        """매매 시작"""
        if self.is_trading_active:
            return
        
        logger.info("\n" + "="*60)
        logger.info("매매 시작")
        logger.info("="*60)
        
        self.is_trading_active = True
        
        # 계좌 정보 갱신
        await self.initialize_account()
        
        # WebSocket 연결
        await self.connect_websocket()
        
        if self.trading_controller:
            self.trading_task = asyncio.create_task(
                self.trading_controller.trading_loop(),
                name="매매 루프"
            )
    
    async def stop_trading(self):
        """매매 중지 (포지션 정리)"""
        if not self.is_trading_active:
            return
        
        logger.info("\n" + "="*60)
        logger.info("매매 중지")
        logger.info("="*60)
        
        self.is_trading_active = False
        
        logger.info("전량매도")
        
        # 보유 종목 전량 매도
        results = await self.api_client.sell_all_positions()
        
        for r in results:
            if r['result'].get('success'):
                logger.info(f"{r['stock_name']} 매도 완료")
            else:
                logger.error(f"{r['stock_name']} 매도 실패")

        
        # 매매 루프 취소
        if hasattr(self, 'trading_task') and not self.trading_task.done():
            self.trading_task.cancel()
            try:
                await self.trading_task
            except asyncio.CancelledError:
                logger.info("매매 루프 중지 완료")
    
    async def monitor_trading_time(self):
        """장 시간 모니터링 (24시간 실행)"""
        logger.info("시간 모니터링 시작")
        
        while True:
            is_trading_time = self.config.is_trading_time()
                
            # 장 시작 시간 & 매매 비활성 → 매매 시작
            if is_trading_time and not self.is_trading_active:
                logger.info("장 시작 - 매매 활성화")
                if not self.config.IS_OVER_NIGHT_MODE:
                    logger.info("야간 모드 - 전량매도 진행")
                    # 보유 종목 전량 매도
                    results = await self.api_client.sell_all_positions()
                    
                    for r in results:
                        if r['result'].get('success'):
                            logger.info(f"{r['stock_name']} 매도 완료")
                        else:
                            logger.error(f"{r['stock_name']} 매도 실패")

                await self.start_trading()
            
            # 장 마감 시간 & 매매 활성 → 매매 중지
            elif not is_trading_time and self.is_trading_active:
                logger.info("장 마감 - 매매 비활성화")
                await self.stop_trading()
                
                # 다음 장 시작까지 대기 시간 표시
                time_until = self.config.get_time_until_start()
                logger.info(f"다음 장 시작: {time_until} 후")
            
            # 장 외 시간 - 상태 표시
            elif not is_trading_time:
                now = datetime.now().strftime('%H:%M:%S')
                logger.debug(f"대기 중... ({now})")
            
            # 1분마다 체크
            await asyncio.sleep(60)
    
    async def start(self):
        """봇 시작 (24시간 운영)"""
        try:
            logger.info("\n" + "="*60)
            logger.info("자동매매 봇 시작 (24시간 운영)")
            logger.info("="*60 + "\n")
            
            # 초기 상태 확인
            if self.config.is_trading_time():
                logger.info("현재 장 운영 시간 - 매매 시작")
                await self.start_trading()
            else:
                logger.info("현재 장 마감 시간 - 대기 모드")
                time_until = self.config.get_time_until_start()
                logger.info(f"다음 장 시작: {time_until} 후")
            
            # 시간 모니터링 태스크
            time_monitor_task = asyncio.create_task(
                self.monitor_trading_time(),
                name="시간 모니터"
            )
            
            await time_monitor_task

            
        except KeyboardInterrupt:
            logger.info("\n사용자 종료 요청")
        
        except Exception as e:
            logger.error(f"\n오류 발생: {e}")
        
        finally:
            # 매매 중지 및 정리
            await self.stop_trading()
            await self.ws_client.disconnect()
            logger.info("프로그램 종료")


async def main():
    """메인 함수"""
    # 설정 로드
    config = TradingConfig()
    
    trading_main = TradingMain(config)
    await trading_main.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n종료")
        sys.exit(0)