"""
계좌 상태 공유 객체 (단순화)
"""
import asyncio
from datetime import datetime
from ..utils.logger_config import setup_logger

logger = setup_logger("system")


class AccountState:
    """계좌 상태 공유 객체 (순수 상태 관리만)"""
    
    def __init__(self):
        # 예수금
        self.available_cash = 0
        self.total_balance = 0
        
        # 보유 종목
        self.positions = {}  # {종목코드: {수량, 평균단가, ...}}
        
        # 업데이트 시간
        self.last_update = None
        
        logger.info("AccountState 초기화")
    
    def update_from_api_response(self, data: dict):
        """
        API 응답으로 상태 업데이트
        
        Args:
            data: KiwoomApiClient.get_account_balance() 응답
        """
        logger.info("계좌 상태 업데이트 중...: ")
        self.available_cash = data.get('available_cash', 0)
        self.last_update = datetime.now()
        
        logger.info(f"계좌 상태 업데이트: 예수금={self.available_cash:,}원")
    
    def update_holdings(self, holdings: list):
        """
        보유 종목 업데이트
        
        Args:
            holdings: KiwoomApiClient.get_account_holdings() 응답
        """
        self.positions = {}
        for item in holdings:
            stock_code = item['stock_code']
            self.positions[stock_code] = item
        
        logger.info(f"보유 종목 업데이트: {len(self.positions)}건")
    
    def get_available_cash(self):
        """주문 가능 금액 조회"""
        return self.available_cash
    
    def get_position(self, stock_code):
        """특정 종목 보유 정보 조회"""
        return self.positions.get(stock_code)
    
    def has_position(self, stock_code):
        """종목 보유 여부"""
        position = self.positions.get(stock_code, {})
        return position.get('quantity', 0) > 0
    
    def calculate_max_quantity(self, price: int, margin: float = 0.9) -> int:
        """
        최대 구매 수량 계산
        
        Args:
            price: 주문 단가
            margin: 안전 마진 (95% = 0.95)
            
        Returns:
            int: 최대 구매 가능 수량
        """
        if price <= 0:
            return 0

        usable_cash = abs(int(self.available_cash * margin))
        max_qty = usable_cash // price
        max_qty = int(max_qty/10) * 10  # 10주 단위 절사
        logger.info(f"최대 구매 수량: {usable_cash:,}원 ÷ {price:,}원 = {max_qty}주")
        
        return int(max(0, max_qty))