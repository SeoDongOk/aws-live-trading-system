"""
로깅 설정 모듈
"""
import logging
import os
from datetime import datetime


class CustomFormatter(logging.Formatter):
    """커스텀 포맷터: error/info/wrong 구분 및 에러 위치 강조"""
    
    def format(self, record):
        # 레벨명을 error/info/wrong으로 변환
        level_map = {
            'DEBUG': 'info',
            'INFO': 'info',
            'WARNING': 'wrong',
            'ERROR': 'error',
            'CRITICAL': 'error'
        }
        level_display = level_map.get(record.levelname, record.levelname.lower())
        
        # 에러인 경우 위치를 크게 표시
        if record.levelno >= logging.ERROR:
            # 파일명과 라인 번호 추출
            pathname = record.pathname
            filename = os.path.basename(pathname)
            lineno = record.lineno
            location = f"\n{'='*80}\n>>> ERROR LOCATION: {filename}:{lineno} <<<\n{'='*80}\n"
            message = f"{location}{record.getMessage()}"
        else:
            message = record.getMessage()
        
        # 타임스탬프 포맷
        if self.datefmt:
            timestamp = datetime.fromtimestamp(record.created).strftime(self.datefmt)
        else:
            timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        return f"{timestamp} [{level_display}] {message}"


def setup_logger(name='trading_bot', log_dir='logs'):
    """
    로거 설정 (콘솔 + 파일)
    
    Returns:
        logger: 설정된 로거
    """
    # 로그 디렉토리 생성
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 기존 핸들러 제거
    if logger.handlers:
        logger.handlers.clear()
    
    # 포맷
    console_fmt = CustomFormatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    
    file_fmt = CustomFormatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 1. 콘솔
    console = logging.StreamHandler()
    console.setFormatter(console_fmt)
    logger.addHandler(console)
    
    # 2. 날짜별 파일
    today = datetime.now().strftime('%Y%m%d')
    log_file = os.path.join(log_dir, f'{name}_{today}.log')
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)
    
    # 3. 에러 전용 파일
    error_file = os.path.join(log_dir, f'{name}_error_{today}.log')
    error_handler = logging.FileHandler(error_file, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_fmt)
    logger.addHandler(error_handler)
    
    logger.info(f"로거 초기화 (파일: {log_file})")
    
    return logger