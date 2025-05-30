"""
인증 관련 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List

from app.db.database import get_db
from app.models.user import User
from app.core.config import get_settings
from app.auth.dependencies import get_current_user, get_current_active_user
from app.utils.auth import (
    verify_password, get_password_hash, create_access_token, 
    create_refresh_token, verify_token
)

router = APIRouter()
settings = get_settings()

# Request/Response 스키마
from pydantic import BaseModel, Field, field_validator
import re

class UserRegister(BaseModel):
    school: str = Field(default="경복대학교", max_length=255)
    student_id: str = Field(..., min_length=4, max_length=50)
    name: str = Field(..., min_length=2, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    password: str = Field(..., min_length=6, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    role: str = Field(default="student")

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v not in ["student", "professor", "admin"]:
            raise ValueError('role must be one of: student, professor, admin')
        return v

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('유효한 이메일 주소를 입력해주세요')
        return v

class UserLogin(BaseModel):
    student_id: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)

class UserResponse(BaseModel):
    id: int
    school: str
    student_id: str
    name: str
    email: Optional[str]
    role: str
    is_active: bool
    is_first_login: bool
    department: Optional[str]
    created_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

class TokenRefresh(BaseModel):
    refresh_token: str

class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=100)

@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    사용자 회원가입
    - 학번 중복 체크
    - 비밀번호 암호화
    - 기본 역할: student
    """
    try:
        # 학번 중복 체크
        existing_user = db.query(User).filter(User.student_id == user_data.student_id).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 등록된 학번입니다."
            )
        
        # 이메일 중복 체크 (이메일이 제공된 경우)
        if user_data.email:
            existing_email = db.query(User).filter(User.email == user_data.email).first()
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이미 등록된 이메일입니다."
                )
        
        # 비밀번호 암호화
        hashed_password = get_password_hash(user_data.password)
        
        # 새 사용자 생성
        db_user = User(
            school=user_data.school,
            student_id=user_data.student_id,
            name=user_data.name,
            email=user_data.email,
            hashed_password=hashed_password,
            role=user_data.role,
            department=user_data.department,
            is_active=True,
            is_first_login=True
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return UserResponse.model_validate(db_user)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"회원가입 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    사용자 로그인 (OAuth2 형식)
    - 학번과 비밀번호로 인증
    - JWT 토큰 발급
    """
    try:
        # 사용자 인증
        user = db.query(User).filter(User.student_id == form_data.username).first()
        
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="학번 또는 비밀번호가 잘못되었습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="비활성화된 계정입니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 토큰 생성
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.student_id, "user_id": user.id, "role": user.role},
            expires_delta=access_token_expires
        )
        
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = create_refresh_token(
            data={"sub": user.student_id, "user_id": user.id},
            expires_delta=refresh_token_expires
        )
        
        # 마지막 로그인 시간 업데이트
        user.last_login_at = datetime.utcnow()
        if user.is_first_login:
            user.is_first_login = False
        
        db.commit()
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"로그인 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/login-direct", response_model=TokenResponse)
async def login_direct(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    직접 로그인 (JSON 형식)
    - 학번과 비밀번호로 인증
    """
    try:
        # 사용자 인증
        user = db.query(User).filter(User.student_id == login_data.student_id).first()
        
        if not user or not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="학번 또는 비밀번호가 잘못되었습니다."
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="비활성화된 계정입니다."
            )
        
        # 토큰 생성
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.student_id, "user_id": user.id, "role": user.role},
            expires_delta=access_token_expires
        )
        
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = create_refresh_token(
            data={"sub": user.student_id, "user_id": user.id},
            expires_delta=refresh_token_expires
        )
        
        # 마지막 로그인 시간 업데이트
        user.last_login_at = datetime.utcnow()
        if user.is_first_login:
            user.is_first_login = False
        
        db.commit()
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"로그인 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: TokenRefresh,
    db: Session = Depends(get_db)
):
    """
    리프레시 토큰으로 새 액세스 토큰 발급
    """
    try:
        # 리프레시 토큰 검증
        payload = verify_token(token_data.refresh_token)
        student_id = payload.get("sub")
        user_id = payload.get("user_id")
        
        if not student_id or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 리프레시 토큰입니다."
            )
        
        # 사용자 조회
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="사용자를 찾을 수 없거나 비활성화된 계정입니다."
            )
        
        # 새 토큰 생성
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.student_id, "user_id": user.id, "role": user.role},
            expires_delta=access_token_expires
        )
        
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        new_refresh_token = create_refresh_token(
            data={"sub": user.student_id, "user_id": user.id},
            expires_delta=refresh_token_expires
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰 갱신에 실패했습니다."
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    현재 로그인한 사용자 정보 조회
    """
    return UserResponse.model_validate(current_user)

@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    name: Optional[str] = None,
    email: Optional[str] = None,
    department: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    사용자 프로필 정보 업데이트
    """
    try:
        # 업데이트할 필드들
        if name is not None:
            current_user.name = name
        
        if email is not None:
            # 이메일 중복 체크
            if email != current_user.email:
                existing_email = db.query(User).filter(
                    User.email == email,
                    User.id != current_user.id
                ).first()
                if existing_email:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="이미 사용 중인 이메일입니다."
                    )
            current_user.email = email
        
        if department is not None:
            current_user.department = department
        
        current_user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(current_user)
        
        return UserResponse.model_validate(current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"프로필 업데이트 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    비밀번호 변경
    """
    try:
        # 현재 비밀번호 확인
        if not verify_password(password_data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="현재 비밀번호가 올바르지 않습니다."
            )
        
        # 새 비밀번호 암호화 및 저장
        current_user.hashed_password = get_password_hash(password_data.new_password)
        current_user.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {"message": "비밀번호가 성공적으로 변경되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"비밀번호 변경 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    로그아웃
    - 클라이언트에서 토큰 삭제 안내
    """
    return {
        "message": "성공적으로 로그아웃되었습니다.",
        "detail": "클라이언트에서 저장된 토큰을 삭제해주세요."
    }

@router.delete("/deactivate")
async def deactivate_account(
    password: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    계정 비활성화 (탈퇴)
    """
    try:
        # 비밀번호 확인
        if not verify_password(password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="비밀번호가 올바르지 않습니다."
            )
        
        # 계정 비활성화
        current_user.is_active = False
        current_user.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {"message": "계정이 비활성화되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"계정 비활성화 중 오류가 발생했습니다: {str(e)}"
        )

# 관리자 전용 엔드포인트
@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    사용자 목록 조회 (관리자 전용)
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다."
        )
    
    users = db.query(User).offset(skip).limit(limit).all()
    return [UserResponse.model_validate(user) for user in users]

@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    new_role: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    사용자 역할 변경 (관리자 전용)
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다."
        )
    
    if new_role not in ["student", "professor", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 역할입니다."
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    user.role = new_role
    user.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": f"사용자 역할이 {new_role}로 변경되었습니다."} 