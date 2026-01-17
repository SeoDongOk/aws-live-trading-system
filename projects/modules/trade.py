"""
키움증권 매수/매도 트레이딩 모듈 (리팩토링)
"""
import requests
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime
from ..utils.logger_config import setup_logger
from ..controls.db_controll import upsert_send_order_list

logger = setup_logger("trade")


class ExchangeType(Enum):
    """거래소 구분"""
    KRX = "KRX"
    NXT = "NXT"
    SOR = "SOR"


class OrderType(Enum):
    """주문 유형"""
    NORMAL = "0"  # 지정가
    MARKET = "3"  # 시장가
    CONDITIONAL = "5"
    BEST_BID = "6"
    PRIORITY = "7"


class TradeExecutor:
    """매수/매도 실행 클래스"""
    
    PRODUCTION_URL = "https://api.kiwoom.com"
    MOCK_URL = "https://mockapi.kiwoom.com"
    ORDER_ENDPOINT = "/api/dostk/ordr"
    
    BUY_API_ID = "kt10000"
    SELL_API_ID = "kt10001"
    
    def __init__(self, token_manager, is_mock: bool = True):
        self.token_manager = token_manager
        self.is_mock = is_mock
        self.base_url = self.MOCK_URL if is_mock else self.PRODUCTION_URL
        self.session = requests.Session()
        
        logger.info(f"TradeExecutor 초기화 ({'모의투자' if is_mock else '실전투자'})")
    
    def _get_access_token(self) -> str:
        """현재 유효한 액세스 토큰 가져오기"""
        token_data = self.token_manager.get_access_token()
        
        if isinstance(token_data, dict):
            return token_data.get('access_token', token_data)
        
        return token_data
    
    def _create_headers(self, api_id: str) -> Dict[str, str]:
        """API 요청 헤더 생성"""
        access_token = self._get_access_token()
        return {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"Bearer {access_token}",
            "api-id": api_id
        }
    
    def _send_order(self, api_id: str, stock_code: str, quantity: int,
                   exchange: ExchangeType = ExchangeType.KRX,
                   order_type: OrderType = OrderType.MARKET,
                   price: Optional[int] = None) -> Dict[str, Any]:
        """주문 전송"""
        url = f"{self.base_url}{self.ORDER_ENDPOINT}"
        headers = self._create_headers(api_id)
        
        body = {
            "dmst_stex_tp": exchange.value,
            "stk_cd": stock_code,
            "ord_qty": str(quantity),
            "trde_tp": order_type.value
        }
        
        if price is not None and order_type == OrderType.NORMAL:
            body["ord_uv"] = str(price)
        
        try:
            response = self.session.post(url, headers=headers, json=body, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            # 주문번호 파싱 개선
            order_no = result.get('output', {}).get('ord_no', result.get('ord_no', 'N/A'))
            
            return {
                "success": True,
                "status_code": response.status_code,
                "order_no": order_no,
                "raw_response": result
            }
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP 오류: {e}"
            try:
                error_detail = e.response.json()
                error_msg += f" - {error_detail}"
            except:
                pass
            
            return {
                "success": False,
                "error": error_msg,
                "error_type": "HTTPError",
                "status_code": e.response.status_code if e.response else None
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def buy(self, stock_code: str, quantity: int, price: Optional[int] = None,
            order_type: OrderType = OrderType.NORMAL,
            exchange: ExchangeType = ExchangeType.KRX) -> Dict[str, Any]:
        """매수 주문"""
        order_type_name = "시장가" if order_type == OrderType.MARKET else "지정가"
        price_str = f" @ {price:,}원" if price else ""
        
        logger.info(f"\n{'='*60}")
        logger.info(f"종목: {stock_code} | 수량: {quantity}주 | {order_type_name}{price_str}")
        logger.info(f"{'='*60}")
        logger.info(f"매수 주문: ",  {
            "api_id": self.BUY_API_ID,
            "stock_code": stock_code,
            "quantity": quantity,
            "exchange": exchange,
            "order_type": order_type,
            "price": price
        })
        
        result = self._send_order(
            api_id=self.BUY_API_ID,
            stock_code=stock_code,
            quantity=quantity,
            exchange=exchange,
            order_type=order_type,
            price=price
        )
        logger.info("매수 주문 응답: ", result)
        if result.get("success"):
            logger.info(f"매수 주문 성공! 주문번호: {result.get('order_no')}")
        else:
            logger.info(f"매수 주문 실패: {result.get('error')}")
        
        # 주문 전송 데이터를 DB에 저장
        try:
            send_order_data = [{
                'stock_code': stock_code,
                'action': '매수',
                'quantity': quantity,
                'price': price or 0,
                'order_type': order_type_name,
                'order_no': result.get('order_no', ''),
                'success': result.get('success', False),
                'error': result.get('error', ''),
                'created_at': datetime.now().isoformat()
            }]
            upsert_send_order_list(send_order_data)
        except Exception as e:
            logger.error(f"주문 전송 데이터 저장 실패: {e}")
        
        logger.info(f"{'='*60}\n")
        
        return result
    
    def sell(self, stock_code: str, quantity: int, price: Optional[int] = None,
             order_type: OrderType = OrderType.MARKET,
             exchange: ExchangeType = ExchangeType.KRX) -> Dict[str, Any]:
        """매도 주문"""
        order_type_name = "시장가" if order_type == OrderType.MARKET else "지정가"
        price_str = f" @ {price:,}원" if price else ""
        
        logger.info(f"\n{'='*60}")
        logger.info(f"매도 주문")
        logger.info(f"종목: {stock_code} | 수량: {quantity}주 | {order_type_name}{price_str}")
        logger.info(f"{'='*60}")
        
        result = self._send_order(
            api_id=self.SELL_API_ID,
            stock_code=stock_code,
            quantity=quantity,
            exchange=exchange,
            order_type=order_type,
            price=price
        )
        logger.info(f"매도 주문 응답: {result}")
        if result.get("success"):
            logger.info(f"매도 주문 성공! 주문번호: {result.get('order_no')}")
        else:
            logger.info(f"매도 주문 실패: {result.get('error')}")
        
        # 주문 전송 데이터를 DB에 저장
        try:
            send_order_data = [{
                'stock_code': stock_code,
                'action': '매도',
                'quantity': quantity,
                'price': price or 0,
                'order_type': order_type_name,
                'order_no': result.get('order_no', ''),
                'success': result.get('success', False),
                'error': result.get('error', ''),
                'created_at': datetime.now().isoformat()
            }]
            upsert_send_order_list(send_order_data)
        except Exception as e:
            logger.error(f"주문 전송 데이터 저장 실패: {e}")
        
        logger.info(f"{'='*60}\n")
        
        return result
    
    # 매서드화, 로직 비공개
    def market_buy(self, stock_code: str, quantity: int) -> Dict[str, Any]:
        """시장가 매수"""
        return self.buy(stock_code, quantity, order_type=OrderType.MARKET)
    
    def market_sell(self, stock_code: str, quantity: int) -> Dict[str, Any]:
        """시장가 매도"""
        return self.sell(stock_code, quantity, order_type=OrderType.MARKET)
    
    def limit_buy(self, stock_code: str, quantity: int, price: int) -> Dict[str, Any]:
        """지정가 매수"""
        return self.buy(stock_code, quantity, price=price, order_type=OrderType.NORMAL)
    
    def limit_sell(self, stock_code: str, quantity: int, price: int) -> Dict[str, Any]:
        """지정가 매도"""
        return self.sell(stock_code, quantity, price=price, order_type=OrderType.NORMAL)