"""
보안 서비스 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.db.database import get_db
from app.auth.dependencies import get_current_user, get_current_admin
from app.models.user import User
from app.services.security_service import security_service

router = APIRouter()

@router.get("/analyze/login")
async def analyze_login_security(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """로그인 보안 분석"""
    try:
        return await security_service.analyze_login_security(
            db=db,
            user_id=current_user.id,
            request=request
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"보안 분석 실패: {str(e)}")

@router.post("/password/validate")
async def validate_password_strength(
    password: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """비밀번호 강도 검증"""
    try:
        return await security_service.validate_password_strength(password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"비밀번호 검증 실패: {str(e)}")

@router.post("/2fa/setup")
async def setup_2fa(
    method: str = "totp",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """2단계 인증 설정"""
    try:
        return await security_service.implement_2fa(
            db=db,
            user_id=current_user.id,
            method=method
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"2FA 설정 실패: {str(e)}")

@router.get("/audit/events")
async def get_security_audit(
    days: int = 30,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """보안 이벤트 감사 (관리자 전용)"""
    try:
        return await security_service.audit_security_events(
            db=db,
            days=days
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"보안 감사 실패: {str(e)}")

@router.post("/session/validate")
async def validate_session_security(
    session_token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """세션 보안 검증"""
    try:
        return await security_service.implement_session_security(
            db=db,
            user_id=current_user.id,
            session_token=session_token
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"세션 검증 실패: {str(e)}")

@router.get("/rate-limit/check")
async def check_rate_limit(
    request: Request,
    endpoint: str
) -> Dict[str, Any]:
    """요청 속도 제한 확인"""
    try:
        return await security_service.implement_rate_limiting(
            request=request,
            endpoint=endpoint
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"속도 제한 확인 실패: {str(e)}")

@router.get("/security/dashboard")
async def get_security_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """개인 보안 대시보드"""
    try:
        # 사용자별 보안 현황
        return {
            "user_id": current_user.id,
            "security_score": 85,  # 100점 만점
            "2fa_enabled": False,
            "password_strength": "strong",
            "last_password_change": "2024-01-15",
            "suspicious_activities": 0,
            "active_sessions": 2,
            "login_locations": ["Seoul, KR", "Busan, KR"],
            "security_recommendations": [
                "2단계 인증 활성화",
                "비밀번호 정기 변경",
                "의심스러운 활동 모니터링"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"보안 대시보드 조회 실패: {str(e)}") 