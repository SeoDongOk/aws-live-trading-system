"""
Supabase 데이터베이스 제어 모듈
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from projects.controls.supabase_connect import get_supabase_client, get_supabase_service_client
from ..utils.logger_config import setup_logger

logger = setup_logger("system")

# 서비스 클라이언트 사용 (관리자 권한)
supabase = get_supabase_service_client()

# ========== 트레이딩 관련 함수 ==========

def select_all_trade() -> List[Dict[str, Any]]:
    """모든 트레이딩 데이터 조회"""
    try:
        response = (
            supabase.table("trade")
            .select("*")
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.error(f"트레이딩 데이터 조회 실패: {e}")
        return []

def select_all_trade_by_count_sort_desc() -> List[Dict[str, Any]]:
    """트레이딩 데이터를 카운트 기준 내림차순으로 조회 (RPC)"""
    try:
        response = supabase.rpc("sp_trade_monotonicity_15_q").execute()
        return response.data or []
    except Exception as e:
        logger.error(f"트레이딩 RPC 조회 실패: {e}")
        return []

def insert_trade(data: dict) -> Optional[List[Dict[str, Any]]]:
    """트레이딩 데이터 삽입 -> 보안상 위험하나 코드 간소화를 위해 사용"""
    if not data:
        return None
    try:
        response = (
            supabase.table("trade")
            .insert(data)
            .execute()
        )
        return response.data
    except Exception as e:
        logger.error(f"트레이딩 데이터 삽입 실패: {e}")
        return None

def upsert_trade(data: list) -> Optional[List[Dict[str, Any]]]:
    """트레이딩 데이터 업서트 -> 보안상 위험하나 코드 간소화를 위해 사용"""
    if not data:
        return None
    try:
        response = (
            supabase.table("trade")
            .upsert(data)
            .execute()
        )
        return response.data
    except Exception as e:
        logger.error(f"트레이딩 데이터 업서트 실패: {e}")
        return None

def delete_all_trade() -> List[Dict[str, Any]]:
    """오늘 생성된 모든 트레이딩 데이터 삭제 -> 보안상 위험하나 코드 간소화를 위해 사용"""
    try:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()
        response = (
            supabase.table("trade")
            .delete()
            .gte("created_at", today_start)
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.error(f"트레이딩 데이터 삭제 실패: {e}")
        return []

# ========== 주문 관련 함수 ==========

def select_trade_order_list() -> List[Dict[str, Any]]:
    """모든 트레이딩 주문 목록 조회"""
    try:
        response = (
            supabase.table("trade_order")
            .select("*")
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.error(f"트레이딩 주문 목록 조회 실패: {e}")
        return []

def insert_trade_order(data: dict) -> Optional[List[Dict[str, Any]]]:
    """트레이딩 주문 데이터 삽입 -> 보안상 위험하나 코드 간소화를 위해 사용"""
    if not data:
        return None
    try:
        response = (
            supabase.table("trade_order")
            .insert(data)
            .execute()
        )
        return response.data
    except Exception as e:
        logger.error(f"트레이딩 주문 데이터 삽입 실패: {e}")
        return None

def upsert_trade_order(data: list) -> Optional[List[Dict[str, Any]]]:
    """트레이딩 주문 데이터 업서트 -> 보안상 위험하나 코드 간소화를 위해 사용"""
    if not data:
        return None
    try:
        response = (
            supabase.table("trade_order")
            .upsert(data)
            .execute()
        )
        return response.data
    except Exception as e:
        logger.error(f"트레이딩 주문 데이터 업서트 실패: {e}")
        return None

def delete_all_trade_order() -> List[Dict[str, Any]]:
    """오늘 생성된 모든 트레이딩 주문 데이터 삭제 -> 보안상 위험하나 코드 간소화를 위해 사용"""
    try:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()
        response = (
            supabase.table("trade_order")
            .delete()
            .gte("created_at", today_start)
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.error(f"트레이딩 주문 데이터 삭제 실패: {e}")
        return []



# ========== 주문 전송 관련 함수 ==========

def upsert_send_order_list(data: list) -> Optional[List[Dict[str, Any]]]:
    """트레이딩 주문 전송 목록 업서트 -> 보안상 위험하나 코드 간소화를 위해 사용"""
    if not data:
        return None
    try:
        response = (
            supabase.table("trade_send_order")
            .upsert(data)
            .execute()
        )
        return response.data
    except Exception as e:
        logger.error(f"주문 전송 목록 업서트 실패: {e}")
        return None

# ========== 계좌 정보 관련 함수 ==========

def upsert_account_info(data: list) -> Optional[List[Dict[str, Any]]]:
    """계좌 정보 업서트 -> 보안상 위험하나 코드 간소화를 위해 사용"""
    if not data:
        return None
    try:
        response = (
            supabase.table("account_balance")
            .upsert(data)
            .execute()
        )
        return response.data
    except Exception as e:
        logger.error(f"계좌 정보 업서트 실패: {e}")
        return None

# ========== 주문 이유 관련 함수 ==========

def upsert_trade_order_reason(data: list) -> Optional[List[Dict[str, Any]]]:
    """트레이딩 주문 이유 업서트 -> 보안상 위험하나 코드 간소화를 위해 사용"""
    if not data:
        return None
    try:
        response = (
            supabase.table("trade_order_reason")
            .upsert(data)
            .execute()
        )
        return response.data
    except Exception as e:
        logger.error(f"주문 이유 업서트 실패: {e}")
        return None

# 하위 호환성을 위한 별칭
trade_order_reason = upsert_trade_order_reason
