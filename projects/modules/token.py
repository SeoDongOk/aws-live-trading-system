"""
키움증권 API 토큰 관리 모듈
"""
import requests
import time
from datetime import datetime, timedelta
from typing import Optional
import json
import os
from dotenv import load_dotenv
from ..utils.logger_config import setup_logger
logger = setup_logger("system")

load_dotenv()


class TokenManager:
    """API 인증 토큰 관리 클래스"""
    
    def __init__(self):
        self.app_key = os.getenv('KIWOOM_APP_KEY')
        self.app_secret = os.getenv('KIWOOM_APP_SECRET')
        self.base_url = os.getenv('KIWOOM_REST_URL')
        self.mode = os.getenv('KIWOOM_MODE', 'virtual')
        
        self.access_token: Optional[str] = None
        self.token_expired_time: Optional[datetime] = None
        
        if not all([self.app_key, self.app_secret, self.base_url]):
            raise ValueError("API 인증 정보가 .env 파일에 설정되지 않았습니다.")
    
    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        액세스 토큰 조회 (만료 시 자동 갱신)
        
        Args:
            force_refresh: 강제 토큰 갱신 여부
            
        Returns:
            str: 액세스 토큰
        """
        # 토큰이 유효한 경우
        if not force_refresh and self.access_token and self.token_expired_time:
            if datetime.now() < self.token_expired_time - timedelta(minutes=5):
                return self.access_token
        
        # 토큰 갱신 필요
        return self._issue_token()
    
    def _issue_token(self) -> str:
        """새로운 액세스 토큰 발급"""
        url = f"{self.base_url}/oauth2/token"
        
        headers = {
            "Content-Type": "application/json;charset=UTF-8" 
        }
        
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.app_secret
        }
        
        try:
            response = requests.post(url, headers=headers, json=body)  # json=
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('return_code') != 0:
                raise Exception(f"토큰 발급 실패: {data.get('return_msg')}")
            
            self.access_token = data.get('token')
            
            # expires_dt 파싱 (예: "20241107083713")
            expires_dt = data.get('expires_dt')
            if expires_dt:
                self.token_expired_time = datetime.strptime(expires_dt, '%Y%m%d%H%M%S')
            else:
                self.token_expired_time = datetime.now() + timedelta(hours=24)
            
            logger.info(f"토큰 발급 성공 (만료: {self.token_expired_time})")
            
            return self.access_token
            
        except Exception as e:
            logger.info(f"토큰 발급 실패: {e}")
            raise
    
    
    def get_auth_headers(self) -> dict:
        """
        REST API 요청에 필요한 인증 헤더 반환
        
        Returns:
            dict: 인증 헤더
        """
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.get_access_token()}",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }


if __name__ == "__main__":
    # 테스트 코드
    token_manager = TokenManager()
    
    # 액세스 토큰 발급
    access_token = token_manager.get_access_token()
    logger.info(f"\nAccess Token: {access_token[:50]}...")
    
    