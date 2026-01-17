"""
키움증권 REST API 클라이언트
"""
import asyncio
import requests
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from datetime import datetime
from ..utils.logger_config import setup_logger
from ..controls.db_controll import upsert_account_info, upsert_send_order_list

logger = setup_logger("system")

load_dotenv()


class KiwoomApiClient:
    """키움증권 REST API 클라이언트"""
    
    def __init__(self, token_manager, trade_executor=None):
        self.token_manager = token_manager
        self.base_url = os.getenv('KIWOOM_REST_URL', 'https://mockapi.kiwoom.com')
        self.account_no = os.getenv('KIWOOM_ACCOUNT_NO')
        self.trade_executor = trade_executor
        
        logger.info(f"KiwoomApiClient 초기화 (계좌: {self.account_no})")
    
    async def get_account_balance(self) -> Optional[Dict[str, Any]]:
        """
        계좌 잔고 조회
        
        Returns:
            dict: {'available_cash': int, 'total_balance': int}
            None: 조회 실패
        """
        try:
            url = f"{self.base_url}/api/dostk/acnt"
            
            headers = self.token_manager.get_auth_headers()
            headers['api-id'] = 'kt00001'
            
            params = {
                'qry_tp': '3'
            }
            
            logger.info(f"잔고 조회 요청...: {params}, {headers}")
            
            response = requests.post(url, headers=headers, json=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"잔고 조회 응답: {data}")
            if data:
                result = {
                    'available_cash': int(data.get('entr', 0)),
                    'raw_data': data
                }
                
                logger.info(f"잔고 조회 성공: 예수금={result['available_cash']:,}원")
                
                # 계좌 정보를 DB에 저장
                try:
                    account_data = [{
                        'available_cash': result.get('available_cash', 0),
                        'total_balance': result.get('total_balance', 0),
                        'updated_at': datetime.now().isoformat()
                    }]
                    upsert_account_info(account_data)
                except Exception as e:
                    logger.error(f"계좌 정보 저장 실패: {e}")
                
                return result
            else:
                logger.info(f"잔고 조회 실패: {data}")
                return None
                
        except Exception as e:
            logger.info(f"잔고 조회 오류: {e}")
            import traceback
            traceback.logger.info_exc()
            return None
    
    async def get_current_price(self, stock_code: str) -> Optional[int]:
        """
        종목 현재가 조회
        
        Args:
            stock_code: 종목코드 (6자리)
            
        Returns:
            int: 현재가
            None: 조회 실패
        """
        try:
            url = f"{self.base_url}/api/dostk/trade"
            
            headers = self.token_manager.get_auth_headers()
            headers['api-id'] = 'ka30012'  # 주식현재가 시세
            
            params = {
                'stk_cd': stock_code, 
            }
            
            response = requests.post(url, headers=headers, json=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # 응답 파싱
            if data:
                output = data
                
                current_price = abs(int(output.get('cur_prc', 0)))

                
                if current_price > 0:
                    logger.info(f"{stock_code} 현재가: {current_price:,}원")
                    return current_price
                else:
                    logger.info(f"{stock_code} 현재가 0원 (장 마감 또는 미거래)")
                    return None
            else:
                logger.info(f"현재가 조회 실패: {data}")
                return None
                
        except Exception as e:
            logger.info(f"현재가 조회 오류 ({stock_code}): {e}")
            return None
    
    async def get_account_holdings(self) -> Optional[dict]:
        """
        보유 종목 조회 - 원시 응답 반환
        
        Returns:
            dict: API 원시 응답 데이터
        """
        try:
            url = f"{self.base_url}/api/dostk/acnt"
            
            headers = {
                'Content-Type': 'application/json;charset=UTF-8',
                'authorization': f'Bearer {self.token_manager.get_access_token()}',
                'api-id': 'kt00004'
            }
            
            body = {
                'qry_tp': '0',  # 0:전체, 1:상장폐지종목제외
                'dmst_stex_tp': 'KRX'  # KRX:한국거래소
            }
            
            logger.info(f"보유 종목 조회 요청...")
            
            response = requests.post(url, headers=headers, json=body, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('return_code') == 0:
                logger.info(f"보유 종목 조회 성공")
                return data
            else:
                logger.warning(f"보유 종목 조회 실패: {data.get('return_msg')}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("보유 종목 조회 시간 초과")
            return None
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"보유 종목 조회 HTTP 오류: {e}")
            return None
            
        except Exception as e:
            logger.error(f"보유 종목 조회 오류: {e}", exc_info=True)
            return None


    async def get_sellable_positions(self):
        """
        매도 가능한 보유 종목 조회
        
        Returns:
            list: [{'stock_code': str, 'quantity': int, 'price': int}, ...]
        """
        # 1. 계좌 잔고 조회
        data = await self.get_account_holdings()
        
        if not data:
            logger.error("계좌 조회 실패")
            return []
        
        # 2. 보유 종목 리스트 파싱
        stk_list = data.get('stk_acnt_evlt_prst', [])
        
        # 3. 매도 가능한 종목만 추출
        sellable = []
        
        for item in stk_list:
            stock_code = item.get('stk_cd', '')  # "A005930"
            quantity = int(item.get('rmnd_qty', 0))  # 보유수량
            current_price = int(item.get('cur_prc', 0))  # 현재가
            
            # 수량이 있는 경우만
            if quantity > 0 and current_price > 0:
                # A 접두사 제거 (필요시)
                stock_code = stock_code.lstrip('AJQK')
                
                sellable.append({
                    'stock_code': stock_code,  # "005930"
                    'stock_name': item.get('stk_nm', ''),
                    'quantity': quantity,
                    'price': current_price
                })
        
        logger.info(f"매도 가능 종목: {len(sellable)}개")
        return sellable

    async def sell_all_positions(self):
        """
        전 종목 일괄 매도
        
        Returns:
            list: 매도 결과 리스트
        """
        positions = await self.get_sellable_positions()
        
        if not positions:
            logger.info("매도할 종목 없음")
            return []
        
        results = []
        
        for pos in positions:
            logger.info(f"매도: {pos['stock_name']} ({pos['stock_code']}) "
                    f"{pos['quantity']}주 @ {pos['price']:,}원")
            
            result = self.trade_executor.limit_sell(
                stock_code=pos['stock_code'],
                quantity=pos['quantity'],
                price=pos['price']
            )
            
            # 주문 전송 데이터를 DB에 저장
            try:
                send_order_data = [{
                    'stock_code': pos['stock_code'],
                    'stock_name': pos['stock_name'],
                    'action': '매도',
                    'quantity': pos['quantity'],
                    'price': pos['price'],
                    'order_no': result.get('order_no', ''),
                    'success': result.get('success', False),
                    'created_at': datetime.now().isoformat()
                }]
                upsert_send_order_list(send_order_data)
            except Exception as e:
                logger.error(f"주문 전송 데이터 저장 실패: {e}")
            
            results.append({
                'stock_code': pos['stock_code'],
                'stock_name': pos['stock_name'],
                'result': result
            })
            
            await asyncio.sleep(0.5)  # API 부하 방지
        
        return results

    async def get_holding_quantity(self, stock_code: str) -> int:
        """
        특정 종목 보유 수량 조회
        
        Args:
            stock_code: 종목코드 (예: '005930' 또는 'A005930')
            
        Returns:
            int: 보유 수량
        """
        data = await self.get_account_holdings()
        
        if not data:
            return 0
        
        stk_list = data.get('stk_acnt_evlt_prst', [])
        
        # 검색할 종목코드에서 접두사 제거
        search_clean = stock_code.lstrip('AJQK')
        
        for item in stk_list:
            api_code = item.get('stk_cd', '')  # "J57LADV"
            api_clean = api_code.lstrip('AJQK')  # "57LADV"
            
            if api_clean == search_clean:
                qty = int(item.get('rmnd_qty', 0))
                logger.info(f"{stock_code} 보유 수량: {qty}주 (API: {api_code})")
                return qty
        
        logger.warning(f"{stock_code} 보유 없음")
        return 0

