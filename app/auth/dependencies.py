"""
인증 관련 의존성 함수
"""
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.utils import ALGORITHM, SECRET_KEY
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import TokenData

# OAuth2 스키마 설정
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    토큰에서 사용자 정보를 추출하여 현재 인증된 사용자를 반환
    
    Args:
        token: JWT 토큰
        db: 데이터베이스 세션
        
    Returns:
        User: 현재 인증된 사용자 모델
        
    Raises:
        HTTPException: 인증 실패 시 발생
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보가 유효하지 않습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 토큰 디코딩
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        student_id: str = payload.get("sub")
        
        if student_id is None:
            raise credentials_exception
            
        token_data = TokenData(student_id=student_id)
    except JWTError:
        raise credentials_exception
        
    # 데이터베이스에서 사용자 조회
    result = await db.execute(select(User).where(User.student_id == token_data.student_id))
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
        
    return user

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    현재 활성화된 사용자 확인
    
    Args:
        current_user: 인증된 현재 사용자
        
    Returns:
        User: 활성화된 사용자
        
    Raises:
        HTTPException: 사용자가 비활성화 상태일 때 발생
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비활성화된 사용자입니다"
        )
    
    return current_user 