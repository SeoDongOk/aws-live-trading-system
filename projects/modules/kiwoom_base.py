"""
키움증권 WebSocket 기본 연결 모듈 (수정)
"""
import asyncio
import websockets
import json
import os
from datetime import datetime
from typing import Callable, Optional, Dict, Any
from dotenv import load_dotenv
from .token import TokenManager
from ..utils.logger_config import setup_logger
logger = setup_logger("system")

load_dotenv()


class KiwoomWebSocket:
    """키움증권 WebSocket 클라이언트 (단일 연결)"""
    
    def __init__(self, token_manager: TokenManager):
        self.token_manager = token_manager
        self.ws_url = os.getenv('KIWOOM_WS_URL', 'wss://mockapi.kiwoom.com:10000')
        self.account_no = os.getenv('KIWOOM_ACCOUNT_NO')
        
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.callbacks: Dict[str, Callable] = {}
        
        # 구독 정보
        self.subscriptions = []
        # 타이머 관리
        self.order_timers = {}  
        
        logger.info(f"KiwoomWebSocket 초기화 (계좌: {self.account_no})")
    
    async def connect(self):
        """WebSocket 연결"""
        try:
            access_token = self.token_manager.get_access_token()
            url = f"{self.ws_url}/api/dostk/websocket"
            
            logger.info(f"WebSocket 연결 중: {url}")
            
            self.websocket = await websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=10
            )
            
            self.is_connected = True
            logger.info("WebSocket 연결 성공")
            
            # 로그인 메시지 전송 (flat 구조)
            asyncio.create_task(self.receive_messages())

            await self._send_login(access_token)

            
        except Exception as e:
            logger.info(f"WebSocket 연결 실패: {e}")
            self.is_connected = False
            raise
    
    async def _send_login(self, access_token):
        """로그인 메시지 전송 (수정)"""
        login_data = {
            "trnm": "LOGIN",
            "token": access_token
        }
        
        if self.websocket and self.is_connected:
            await self.websocket.send(json.dumps(login_data))
            logger.info("로그인 메시지 전송")
            logger.info(f"   → {json.dumps(login_data, ensure_ascii=False)}")
            await asyncio.sleep(1)  # 로그인 응답 대기
    
    async def disconnect(self):
        """WebSocket 연결 종료"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info("WebSocket 연결 종료")
    
    def register_callback(self, event_type: str, callback: Callable):
        """
        이벤트 콜백 함수 등록
        """
        self.callbacks[event_type] = callback
        logger.info(f"콜백 등록: {event_type}")
    
    async def subscribe_order_execution(self):
        """주문 체결 실시간 구독 (수정)"""
        if not self.account_no:
            logger.info("계좌번호가 설정되지 않았습니다.")
            return
        
        # flat 구조로 변경
        subscribe_data = {
            "trnm": "REG",
            "grp_no": "0001",
            "refresh": "Y",
            "data": [{
                "item": [self.account_no],  # 계좌번호
                "type": ["00"]  # 00: 주문체결
            }]
        }
        
        if self.websocket and self.is_connected:
            await self.websocket.send(json.dumps(subscribe_data))
            self.subscriptions.append('order_execution')
            logger.info(f"주문체결 구독 요청")
            logger.info(f"   → {json.dumps(subscribe_data, ensure_ascii=False)}")
        else:
            logger.info("WebSocket이 연결되지 않았습니다.")
    
    async def subscribe_account_balance(self):
        """잔고 실시간 구독 (수정)"""
        if not self.account_no:
            logger.info("계좌번호가 설정되지 않았습니다.")
            return
        
        # flat 구조, 계좌번호 명시
        subscribe_data = {
            "trnm": "REG",
            "grp_no": "0002",
            "refresh": "Y",
            "data": [{
                "item": [self.account_no],  # 계좌번호
                "type": ["04"]  # 04: 체결통보
            }]
        }
        
        if self.websocket and self.is_connected:
            await self.websocket.send(json.dumps(subscribe_data))
            self.subscriptions.append('balance')
            logger.info(f"잔고 구독 요청")
            logger.info(f"   → {json.dumps(subscribe_data, ensure_ascii=False)}")
        else:
            logger.info("WebSocket이 연결되지 않았습니다.")
    
    async def receive_messages(self):
        """
        단일 메시지 수신 루프
        """
        logger.info("메시지 수신 루프 시작")
        
        while self.is_connected:
            try:
                message = await self.websocket.recv()
                response = json.loads(message) if isinstance(message, str) else message
                
                # 응답 타입별 처리
                trnm = response.get('trnm', '')
                
                if trnm == 'LOGIN':
                    await self._handle_login(response)
                
                elif trnm == 'PING':
                    # PING 응답
                    await self.websocket.send(json.dumps(response))
                
                elif trnm == 'REAL':
                    await self._handle_realtime_data(response)
                    
                elif trnm == 'REG':
                    # 등록 완료
                    if response.get('return_code') == 0:
                        logger.info(f"실시간 등록 성공: {response.get('return_msg', '')}")
                    else:
                        logger.info(f"실시간 등록 실패: {response.get('return_msg', '')}")
                
                elif trnm == 'SYSTEM':
                    # 시스템 메시지
                    logger.info(f"시스템 메시지: {response.get('message', '')}")
                    if 'R10004' in response.get('code', ''):
                        logger.info("로그인 실패 - 연결 종료")
                        self.is_connected = False
                        break
                
                else:
                    # 디버깅용
                    if trnm != '':
                        logger.info(f"응답 [trnm={trnm}]: {response}")
                    else:
                        logger.info(f"trnm 없는 응답: {response}")
                
            except websockets.ConnectionClosed:
                logger.info("WebSocket 연결이 종료되었습니다.")
                self.is_connected = False
                break
            
            except json.JSONDecodeError as e:
                logger.info(f"JSON 파싱 오류: {e}")
            
            except Exception as e:
                logger.info(f"메시지 수신 오류: {e}")
    
    async def _handle_login(self, response):
        """로그인 응답 처리"""
        return_code = response.get('return_code', -1)
        return_msg = response.get('return_msg', '')
        
        if return_code == 0:
            logger.info(f"WebSocket 로그인 성공! {return_msg}")
        else:
            logger.info(f"로그인 실패 (코드: {return_code}): {return_msg}")
            await self.disconnect()
    
    async def _handle_realtime_data(self, response):
        """실시간 데이터 처리"""
        data_list = response.get('data', [])
        
        for data in data_list:
            rt_type = data.get('type')
            
            if rt_type in ['04', '00']:
                parsed_data = self._parse_order_execution(data)
                
                await self._manage_order_timer(parsed_data)
                
                # 콜백 호출
                if 'order_execution' in self.callbacks:
                    await self.callbacks['order_execution'](parsed_data)
                    
            # 잔고통보 (type: '05')
            elif rt_type == '05':
                parsed_data = self._parse_balance(data)
                if 'balance_update' in self.callbacks:
                    await self.callbacks['balance_update'](parsed_data)


    async def _manage_order_timer(self, data):
        """주문 타이머 관리"""
        order_no = data['order_no']
        order_status = data['order_status']
        
        # '접수' → 5분 타이머 시작
        if order_status == '접수':
            logger.info(f"[{order_no}] 5분 타이머 시작")
            
            # 기존 타이머 취소
            if order_no in self.order_timers:
                self.order_timers[order_no].cancel()
            
            # 새 타이머 시작
            timer_task = asyncio.create_task(
                self._order_timeout(order_no, data)
            )
            self.order_timers[order_no] = timer_task
        
        # '체결' → 타이머 취소
        elif order_status == '체결':
            if order_no in self.order_timers:
                self.order_timers[order_no].cancel()
                del self.order_timers[order_no]
                logger.info(f"[{order_no}] 타이머 취소 (체결 완료)")

    async def _order_timeout(self, order_no, data):
        """5분 타임아웃"""
        try:
            await asyncio.sleep(300)  # 5분 = 300초
            
            logger.info(f"\n{'='*60}")
            logger.info(f"타임아웃! 주문번호: {order_no}")
            logger.info(f"   종목: {data['stock_code']}")
            logger.info(f"   구분: {data['buy_sell']}")
            logger.info(f"   5분 이내 체결 안됨 → 주문 취소 필요")
            logger.info(f"{'='*60}\n")
            
            if order_no in self.order_timers:
                del self.order_timers[order_no]
        
        except asyncio.CancelledError:
            pass

    def _parse_order_execution(self, data):
        """주문체결 데이터 파싱"""
        values = data.get('values', {})
        def safe_int(value, default=0):
            if not value or str(value).strip() == '':
                return default
            try:
                return int(value)
            except:
                return default


        order_status = values.get('913', '')  # 주문상태
        buy_sell = values.get('907', '')      # 1:매도, 2:매수
        if values.get('913', '0') == '주문':
            logger.info("주문 접수 상태 수신, 체결 아님.")
            order_status = '접수'

        parsed = {
            'order_no': values.get('9203', ''),
            'stock_code': values.get('9001', ''),
            'stock_name': values.get('302', ''),
            'order_status': order_status,
            'buy_sell': '매수' if buy_sell == '2' else '매도',
            'action': '매수' if buy_sell == '2' else '매도',
            'order_qty': safe_int(values.get('900', '0')),
            'exec_qty': safe_int(values.get('911', '0')),
            'exec_price': safe_int(values.get('910', '0')),
            'remain_qty': safe_int(values.get('902', '0')),
        }

        return parsed
    
    def _parse_balance(self, data):
        """잔고 통보 파싱"""
        return {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ord_psbl_cash': data.get('ord_psbl_cash', '0'),
            'tot_evlu_amt': data.get('tot_evlu_amt', '0'),
            'stock_code': data.get('stck_shrn_iscd', ''),
            'holding_qty': data.get('hldg_qty', '0'),
            'avg_price': data.get('pchs_avg_pric', '0'),
            'raw_data': data
        }