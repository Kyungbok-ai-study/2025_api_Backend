"""
인증 관련 의존성 함수들
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime
import logging

from app.db.database import get_db
from app.models.user import User
from app.core.config import settings

logger = logging.getLogger(__name__)

# Bearer 토큰 스키마
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    현재 인증된 사용자 조회
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보가 유효하지 않습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # JWT 토큰 디코딩
        payload = jwt.decode(
            credentials.credentials, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
            
    except JWTError as e:
        logger.warning(f"JWT 디코딩 실패: {str(e)}")
        raise credentials_exception
    
    # 사용자 조회
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        logger.warning(f"사용자를 찾을 수 없음: user_id={user_id}")
        raise credentials_exception
    
    # 사용자 활성화 상태 확인
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="비활성화된 계정입니다"
        )
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    현재 활성 사용자 조회 (별칭)
    """
    return current_user

async def get_current_student(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    현재 학생 사용자 조회 (학생 권한 필요)
    """
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="학생 권한이 필요합니다"
        )
    return current_user

async def get_current_professor(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    현재 교수 사용자 조회 (교수 권한 필요)
    """
    if current_user.role != "professor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="교수 권한이 필요합니다"
        )
    return current_user

async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    현재 관리자 사용자 조회 (관리자 권한 필요)
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다"
        )
    return current_user

def require_roles(*allowed_roles: str):
    """
    특정 역할이 필요한 의존성 팩토리
    
    Usage:
        @app.get("/admin-only")
        def admin_endpoint(user: User = Depends(require_roles("admin"))):
            pass
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"필요한 권한: {', '.join(allowed_roles)}"
            )
        return current_user
    
    return role_checker

class RoleChecker:
    """
    역할 기반 권한 체크 클래스
    """
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles
    
    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"필요한 권한: {', '.join(self.allowed_roles)}"
            )
        return current_user

# 자주 사용되는 권한 체커 인스턴스들
allow_student_and_professor = RoleChecker(["student", "professor"])
allow_professor_and_admin = RoleChecker(["professor", "admin"])
allow_all_authenticated = RoleChecker(["student", "professor", "admin"])

def verify_token_not_expired(token_payload: dict) -> bool:
    """
    토큰 만료 시간 확인
    """
    exp = token_payload.get("exp")
    if exp is None:
        return False
    
    current_time = datetime.utcnow().timestamp()
    return current_time < exp

def verify_token_scope(token_payload: dict, required_scope: str) -> bool:
    """
    토큰 스코프 확인
    """
    token_scopes = token_payload.get("scopes", [])
    return required_scope in token_scopes

async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User | None:
    """
    선택적 사용자 인증 (토큰이 없거나 유효하지 않아도 None 반환)
    """
    if not credentials:
        return None
    
    try:
        payload = jwt.decode(
            credentials.credentials, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: int = payload.get("user_id")
        if user_id is None:
            return None
            
        user = db.query(User).filter(User.id == user_id).first()
        if user is None or not user.is_active:
            return None
            
        return user
        
    except JWTError:
        return None 