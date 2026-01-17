"""
매매 설정 관리
"""
import os
from datetime import datetime, time
from dotenv import load_dotenv
from ..utils.logger_config import setup_logger
logger = setup_logger("setting")

load_dotenv()


class TradingConfig:
    """매매 설정 클래스"""
    
    def __init__(self):
        # ========== 시간 설정 ==========
        self.START_HOUR = int(os.getenv('START_HOUR', 9))
        self.START_MINUTE = int(os.getenv('START_MINUTE', 1))
        self.END_HOUR = int(os.getenv('END_HOUR', 15))
        self.END_MINUTE = int(os.getenv('END_MINUTE', 30))
        
        # ========== 매매 간격 ==========
        self.INTERVAL_MINUTES = int(os.getenv('INTERVAL_MINUTES', 15))  # 타임아웃
        self.INTERVAL = int(os.getenv('INTERVAL', 60))  # 데이터 수집 간격
        
        # ========== 리스크 관리 ==========
        self.MAX_ROUNDS_IN_MEMORY = int(os.getenv('MAX_ROUNDS_IN_MEMORY', 50))
        self.SAFE_MAX_VALUE_RATE = float(os.getenv('SAFE_MAX_VALUE_RATE', 0.98))
        self.SAFE_TRADING_FEE_RATIO = float(os.getenv('SAFE_TRADING_FEE_RATIO', 0.0005))
        
        # ========== 매도 조건 ==========
        self.SELL_SLOP_PCT = float(os.getenv('SELL_SLOP_PCT', 0.09))  # 익절 9%
        self.SELL_THRESHOLD_PCT = float(os.getenv('SELL_THRESHOLD_PCT', 0.03))  # 익절 3%
        self.SELL_LOSS_PCT = float(os.getenv('SELL_LOSS_PCT', 0.05))  # 손절 5%
        
        # ========== 모드 설정 ==========
        self.IS_SELL_MODE = os.getenv('IS_SELL_MODE', 'True').lower() == 'true'
        self.IS_OVER_NIGHT_MODE = os.getenv('IS_OVER_NIGHT_MODE', 'True').lower() == 'true'
        
        logger.info("TradingConfig 로드 완료")
        self.logger_info_config()
    
    def logger_info_config(self):
        """설정 출력 (전략 관련 정보 제외)"""
        logger.info(f"""
    ┌──────────────────────────────────────────────┐
    │              매매 설정                        │
    ├──────────────────────────────────────────────┤
    │  장 시작: {self.START_HOUR:02d}:{self.START_MINUTE:02d}                          │
    │  장 종료: {self.END_HOUR:02d}:{self.END_MINUTE:02d}                          │
    │  타임아웃: {self.INTERVAL_MINUTES}분                          │
    │  데이터 수집 간격: {self.INTERVAL}초                   │
    ├──────────────────────────────────────────────┤
    │  자동 매도: {'활성화' if self.IS_SELL_MODE else '비활성화'}{'  ' if self.IS_SELL_MODE else ' '}                    │
    │  오버나잇: {'활성화' if self.IS_OVER_NIGHT_MODE else '비활성화'}{'  ' if self.IS_OVER_NIGHT_MODE else ' '}                     │
    └──────────────────────────────────────────────┘
        """)
    
    def is_trading_time(self) -> bool:
        """
        현재 매매 가능 시간인지 체크
        
        Returns:
            bool: 매매 가능하면 True
        """
        now = datetime.now()
        current_time = now.time()
        
        start = time(self.START_HOUR, self.START_MINUTE)
        end = time(self.END_HOUR, self.END_MINUTE)
        
        # 주말 체크
        if now.weekday() >= 5:  # 5=토요일, 6=일요일
            return False
        
        # 시간 체크
        return start <= current_time <= end
    
    def get_time_until_start(self) -> str:
        """장 시작까지 남은 시간"""
        now = datetime.now()
        start = now.replace(hour=self.START_HOUR, minute=self.START_MINUTE, second=0)
        
        if now > start:
            # 다음날 시작 시간
            from datetime import timedelta
            start += timedelta(days=1)
        
        delta = start - now
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        
        return f"{hours}시간 {minutes}분"
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환 (trade_main.py 호환)"""
        return {
            'TIMEOUT_MINUTES': self.INTERVAL_MINUTES,
            'PROFIT_TARGET': self.SELL_THRESHOLD_PCT,
            'PROFIT_TARGET_HIGH': self.SELL_SLOP_PCT,
            'STOP_LOSS': self.SELL_LOSS_PCT,
            'SAFE_MAX_VALUE_RATE': self.SAFE_MAX_VALUE_RATE,
            'IS_SELL_MODE': self.IS_SELL_MODE,
            'IS_OVER_NIGHT_MODE': self.IS_OVER_NIGHT_MODE,
        }