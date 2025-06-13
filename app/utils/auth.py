"""
인증 관련 유틸리티 함수들
"""
from datetime import datetime, timedelta
from typing import Optional, Union, Any
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# 패스워드 해싱 컨텍스트
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    평문 비밀번호와 해시된 비밀번호 비교
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    비밀번호 해싱
    """
    return pwd_context.hash(password)

def create_access_token(
    data: dict, 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    JWT 액세스 토큰 생성
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt

def create_refresh_token(
    data: dict, 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    JWT 리프레시 토큰 생성
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """
    JWT 토큰 검증 및 페이로드 반환
    """
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None

def decode_access_token(token: str) -> Optional[dict]:
    """
    액세스 토큰 디코딩
    """
    payload = verify_token(token)
    if payload and payload.get("type") == "access":
        return payload
    return None

def decode_refresh_token(token: str) -> Optional[dict]:
    """
    리프레시 토큰 디코딩
    """
    payload = verify_token(token)
    if payload and payload.get("type") == "refresh":
        return payload
    return None

def is_token_expired(token: str) -> bool:
    """
    토큰 만료 여부 확인
    """
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False}  # 만료 시간 검증 비활성화
        )
        
        exp = payload.get("exp")
        if exp:
            exp_datetime = datetime.fromtimestamp(exp)
            return datetime.utcnow() > exp_datetime
        return True
        
    except JWTError:
        return True

def get_token_remaining_time(token: str) -> Optional[int]:
    """
    토큰의 남은 유효 시간 반환 (초 단위)
    """
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False}
        )
        
        exp = payload.get("exp")
        if exp:
            exp_datetime = datetime.fromtimestamp(exp)
            remaining = exp_datetime - datetime.utcnow()
            return max(0, int(remaining.total_seconds()))
        return 0
        
    except JWTError:
        return None

def extract_user_id_from_token(token: str) -> Optional[int]:
    """
    토큰에서 사용자 ID 추출
    """
    payload = decode_access_token(token)
    if payload:
        return payload.get("user_id")
    return None

def extract_student_id_from_token(token: str) -> Optional[str]:
    """
    토큰에서 학번 추출
    """
    payload = decode_access_token(token)
    if payload:
        return payload.get("sub")
    return None

def extract_role_from_token(token: str) -> Optional[str]:
    """
    토큰에서 사용자 역할 추출
    """
    payload = decode_access_token(token)
    if payload:
        return payload.get("role")
    return None

def create_password_reset_token(student_id: str) -> str:
    """
    비밀번호 재설정 토큰 생성
    """
    data = {"sub": student_id, "type": "password_reset"}
    expires_delta = timedelta(hours=1)  # 1시간 유효
    
    expire = datetime.utcnow() + expires_delta
    data.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        data, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt

def verify_password_reset_token(token: str) -> Optional[str]:
    """
    비밀번호 재설정 토큰 검증
    """
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        if payload.get("type") == "password_reset":
            return payload.get("sub")
        return None
        
    except JWTError:
        return None

def is_strong_password(password: str) -> tuple[bool, list[str]]:
    """
    비밀번호 강도 검사
    
    Returns:
        tuple: (is_strong, error_messages)
    """
    errors = []
    
    if len(password) < 8:
        errors.append("비밀번호는 최소 8자 이상이어야 합니다.")
    
    if not any(c.islower() for c in password):
        errors.append("소문자를 최소 1개 포함해야 합니다.")
    
    if not any(c.isupper() for c in password):
        errors.append("대문자를 최소 1개 포함해야 합니다.")
    
    if not any(c.isdigit() for c in password):
        errors.append("숫자를 최소 1개 포함해야 합니다.")
    
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        errors.append("특수문자를 최소 1개 포함해야 합니다.")
    
    return len(errors) == 0, errors

def generate_api_key() -> str:
    """
    API 키 생성 (관리자용)
    """
    import secrets
    return secrets.token_urlsafe(32)

def create_email_verification_token(email: str) -> str:
    """
    이메일 인증 토큰 생성
    """
    data = {"email": email, "type": "email_verification"}
    expires_delta = timedelta(hours=24)  # 24시간 유효
    
    expire = datetime.utcnow() + expires_delta
    data.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        data, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt

def verify_email_verification_token(token: str) -> Optional[str]:
    """
    이메일 인증 토큰 검증
    """
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        if payload.get("type") == "email_verification":
            return payload.get("email")
        return None
        
    except JWTError:
        return None 