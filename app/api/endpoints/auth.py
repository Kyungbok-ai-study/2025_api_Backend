"""
인증 관련 API 엔드포인트
"""
from datetime import timedelta, datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import exc, func, text

from app.auth.utils import create_access_token, get_password_hash, verify_password
from app.auth.dependencies import get_current_user, get_current_active_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import Token, UserCreate, UserLogin, User as UserSchema

router = APIRouter()

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user_in: Dict, db: AsyncSession = Depends(get_db)) -> Dict:
    """
    사용자 회원가입 엔드포인트
    
    Args:
        user_in (Dict): 사용자 생성 정보
        db (AsyncSession, optional): 데이터베이스 세션. Defaults to Depends(get_db).
        
    Returns:
        Dict: 생성된 사용자 정보
    """
    # Dict 형식으로 변환된 UserCreate 데이터를 처리
    user_create = UserCreate.from_dict(user_in)
    
    # 1. 사용자 이미 존재하는지 확인
    result = await db.execute(select(User).where(User.student_id == user_create.student_id))
    user_exists = result.scalars().first()
    
    if user_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"학번 {user_create.student_id}는 이미 등록되어 있습니다."
        )
    
    # 2. 비밀번호 해싱
    hashed_password = get_password_hash(user_create.password)
    
    # 3. 사용자 객체 생성
    new_user = User(
        student_id=user_create.student_id,
        name=user_create.name,
        role=user_create.role,
        hashed_password=hashed_password,
    )
    
    try:
        # 4. 데이터베이스에 사용자 추가
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # 5. 생성된 사용자 반환 (비밀번호는 제외)
        return {
            "id": new_user.id,
            "student_id": new_user.student_id,
            "name": new_user.name,
            "role": new_user.role,
            "school": new_user.school,
            "is_first_login": new_user.is_first_login,
            "message": "회원가입이 성공적으로 완료되었습니다."
        }
    except exc.SQLAlchemyError as e:
        # 데이터베이스 오류 처리
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 오류: {str(e)}"
        )

@router.post("/login", response_model=Dict)
async def login(user_in: Dict, db: AsyncSession = Depends(get_db)) -> Dict:
    """
    사용자 로그인 엔드포인트
    
    Args:
        user_in (Dict): 사용자 로그인 정보
        db (AsyncSession, optional): 데이터베이스 세션. Defaults to Depends(get_db).
        
    Returns:
        Dict: 액세스 토큰 및 사용자 정보
    """
    # Dict 형식으로 변환된 UserLogin 데이터를 처리
    user_login = UserLogin.from_dict(user_in)
    
    # 1. 학번으로 사용자 찾기
    result = await db.execute(select(User).where(User.student_id == user_login.student_id))
    user = result.scalars().first()
    
    # 2. 사용자가 존재하지 않거나 비밀번호가 일치하지 않으면 에러
    if not user or not verify_password(user_login.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="학번 또는 비밀번호가 올바르지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. 액세스 토큰 생성
    access_token_expires = timedelta(minutes=30)  # 토큰 유효 시간: 30분
    
    # 토큰에 포함될 데이터
    access_token = create_access_token(
        data={"sub": user.student_id, "role": user.role}, 
        expires_delta=access_token_expires
    )
    
    # 4. 첫 로그인이면 is_first_login 필드 업데이트
    if user.is_first_login:
        user.is_first_login = False
        user.last_login_at = datetime.utcnow()
        await db.commit()
    
    # 5. 토큰 및 사용자 기본 정보 반환
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "student_id": user.student_id,
            "name": user.name,
            "role": user.role,
            "is_first_login": user.is_first_login
        }
    }

@router.get("/check-first-login")
async def check_first_login(current_user: User = Depends(get_current_active_user)) -> Dict:
    """
    현재 로그인한 사용자의 최초 로그인 여부 확인
    
    Args:
        current_user (User): 현재 인증된 사용자
        
    Returns:
        Dict: 최초 로그인 여부 및 사용자 정보
    """
    return {
        "is_first_login": current_user.is_first_login,
        "user": {
            "id": current_user.id,
            "student_id": current_user.student_id,
            "name": current_user.name,
            "role": current_user.role
        }
    }

@router.post("/reset-first-login")
async def reset_first_login(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    최초 로그인 상태 재설정 (테스트용)
    
    Args:
        current_user (User): 현재 인증된 사용자
        db (AsyncSession): 데이터베이스 세션
        
    Returns:
        Dict: 처리 결과
    """
    # 최초 로그인 상태로 재설정
    current_user.is_first_login = True
    await db.commit()
    
    return {
        "message": "최초 로그인 상태로 재설정되었습니다.",
        "is_first_login": current_user.is_first_login
    } 