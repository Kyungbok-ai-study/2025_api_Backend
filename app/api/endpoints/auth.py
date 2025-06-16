"""
인증 관련 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import re
import os
import uuid
from pathlib import Path
import shutil
import json
import logging

from app.db.database import get_db
from app.models.user import User
from app.core.config import get_settings
from app.auth.dependencies import get_current_user, get_current_active_user
from app.utils.auth import (
    verify_password, get_password_hash, create_access_token, 
    create_refresh_token, verify_token
)
from app.models.verification import VerificationRequest

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)

# Request/Response 스키마
from pydantic import BaseModel, Field, field_validator

class UserRegister(BaseModel):
    user_id: str = Field(..., min_length=4, max_length=20)
    password: str = Field(..., min_length=8, max_length=100)
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., max_length=255)
    school: str = Field(..., max_length=255)
    department: str = Field(..., max_length=100)
    admission_year: int = Field(...)
    phone_number: str = Field(..., max_length=20)
    verification_method: str = Field(..., max_length=20)
    
    # 이용약관 동의 정보
    terms_agreed: bool = Field(...)
    privacy_agreed: bool = Field(...)
    privacy_optional_agreed: bool = Field(default=False)
    marketing_agreed: bool = Field(default=False)
    identity_verified: bool = Field(...)
    age_verified: bool = Field(...)

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        if not re.match(r'^[a-zA-Z0-9]+$', v):
            raise ValueError('아이디는 영문자와 숫자만 사용 가능합니다')
        return v

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('유효한 이메일 주소를 입력해주세요')
        return v

    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v):
        if v and not re.match(r'^[0-9-+\s()]+$', v):
            raise ValueError('유효한 전화번호를 입력해주세요')
        return v
        
    @field_validator('verification_method')
    @classmethod
    def validate_verification_method(cls, v):
        if v not in ["phone", "ipin"]:
            raise ValueError('인증 방법은 phone 또는 ipin이어야 합니다')
        return v

class UserLogin(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)

class UserResponse(BaseModel):
    id: int
    school: str
    user_id: str
    student_id: str | None
    name: str
    email: str | None
    role: str
    is_active: bool
    is_first_login: bool
    profile_image: str | None
    profile_image_url: str | None
    department: str | None
    admission_year: int | None
    phone_number: str | None
    verification_method: str | None
    terms_agreed: bool
    privacy_agreed: bool
    privacy_optional_agreed: bool
    marketing_agreed: bool
    identity_verified: bool
    age_verified: bool
    diagnostic_test_completed: bool
    diagnostic_test_completed_at: datetime | None
    created_at: datetime
    last_login_at: datetime | None

    class Config:
        from_attributes = True

    @classmethod
    def from_user(cls, user: User):
        """User 모델에서 UserResponse 생성"""
        profile_image_url = None
        if user.profile_image and os.path.exists(user.profile_image):
            profile_image_url = f"/api/auth/profile-image/{user.id}"
        
        # 사용자 역할 결정
        # 1. 기본적으로 DB의 role 값을 사용하되
        # 2. student인 경우, 인증 상태에 따라 최종 role 결정
        final_role = user.role
        
        if user.role == "student":
            # 모든 필수 약관에 동의하고 인증이 완료된 경우: student (재학생)
            # 하나라도 미동의/미인증인 경우: unverified (미인증 사용자)
            if (user.terms_agreed and 
                user.privacy_agreed and 
                user.identity_verified and 
                user.age_verified):
                final_role = "student"  # 인증된 재학생
            else:
                final_role = "unverified"  # 미인증 사용자
        
        return cls(
            id=user.id,
            school=user.school,
            user_id=user.user_id,
            student_id=user.student_id,
            name=user.name,
            email=user.email,
            role=final_role,
            is_active=user.is_active,
            is_first_login=user.is_first_login,
            profile_image=user.profile_image,
            profile_image_url=profile_image_url,
            department=user.department,
            admission_year=user.admission_year,
            phone_number=user.phone_number,
            verification_method=user.verification_method,
            terms_agreed=user.terms_agreed,
            privacy_agreed=user.privacy_agreed,
            privacy_optional_agreed=user.privacy_optional_agreed,
            marketing_agreed=user.marketing_agreed,
            identity_verified=user.identity_verified,
            age_verified=user.age_verified,
            diagnostic_test_completed=getattr(user, 'diagnostic_test_completed', False),
            diagnostic_test_completed_at=getattr(user, 'diagnostic_test_completed_at', None),
            created_at=user.created_at,
            last_login_at=getattr(user, 'last_login_at', None)
        )

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

class UserIdCheckResponse(BaseModel):
    available: bool
    message: str

class VerificationRequestCreate(BaseModel):
    verification_type: str = Field(..., pattern="^(student|professor)$")
    reason: str = Field(..., min_length=10, max_length=1000)
    documents: Optional[List[Dict[str, Any]]] = []

@router.get("/check-userid/{user_id}", response_model=dict)
async def check_user_id_duplicate(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    아이디 중복 확인
    """
    try:
        # 아이디 유효성 검사
        if len(user_id) < 4 or len(user_id) > 20:
            return {
                "success": False,
                "message": "아이디는 4-20자리이어야 합니다.",
                "data": {"available": False}
            }
        
        if not re.match(r'^[a-zA-Z0-9]+$', user_id):
            return {
                "success": False,
                "message": "아이디는 영문자와 숫자만 사용 가능합니다.",
                "data": {"available": False}
            }
        
        # 중복 확인
        existing_user = db.query(User).filter(User.user_id == user_id).first()
        
        if existing_user:
            return {
                "success": True,
                "message": "이미 사용 중인 아이디입니다.",
                "data": {"available": False}
            }
        else:
            return {
                "success": True,
                "message": "사용 가능한 아이디입니다.",
                "data": {"available": True}
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"아이디 중복 확인 중 오류가 발생했습니다: {str(e)}",
            "data": {"available": False}
        }

@router.post("/register", response_model=dict)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    사용자 회원가입
    - 아이디 중복 체크
    - 이메일 중복 체크
    - 비밀번호 암호화
    - 이용약관 동의 정보 저장
    """
    try:
        # 필수 약관 동의 확인
        if not user_data.terms_agreed or not user_data.privacy_agreed or not user_data.identity_verified or not user_data.age_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="필수 약관에 동의해주세요."
            )
        
        # 아이디 중복 체크
        existing_user = db.query(User).filter(User.user_id == user_data.user_id).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 등록된 아이디입니다."
            )
        
        # 이메일 중복 체크
        if user_data.email:
            existing_email = db.query(User).filter(User.email == user_data.email).first()
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="이미 등록된 이메일입니다."
                )
        
        # 비밀번호 암호화
        hashed_password = get_password_hash(user_data.password)
        
        # 새 사용자 생성
        db_user = User(
            user_id=user_data.user_id,
            name=user_data.name,
            email=user_data.email,
            hashed_password=hashed_password,
            school=user_data.school,
            department=user_data.department,
            admission_year=user_data.admission_year,
            phone_number=user_data.phone_number,
            verification_method=user_data.verification_method,
            role="student",
            terms_agreed=user_data.terms_agreed,
            privacy_agreed=user_data.privacy_agreed,
            privacy_optional_agreed=user_data.privacy_optional_agreed,
            marketing_agreed=user_data.marketing_agreed,
            identity_verified=user_data.identity_verified,
            age_verified=user_data.age_verified,
            is_active=True,
            is_first_login=True
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return {
            "success": True,
            "message": "회원가입이 완료되었습니다.",
            "data": UserResponse.from_user(db_user)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "message": f"회원가입 중 오류가 발생했습니다: {str(e)}",
            "data": None
        }

@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    사용자 로그인 (OAuth2 형식)
    - 아이디와 비밀번호로 인증
    - JWT 토큰 발급
    """
    try:
        # 사용자 인증
        user = db.query(User).filter(User.user_id == form_data.username).first()
        
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="아이디 또는 비밀번호가 잘못되었습니다.",
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
            data={"sub": user.user_id, "user_id": user.id, "role": user.role},
            expires_delta=access_token_expires
        )
        
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = create_refresh_token(
            data={"sub": user.user_id, "user_id": user.id},
            expires_delta=refresh_token_expires
        )
        
        # 마지막 로그인 시간 업데이트
        user.update_last_login()
        # is_first_login이 True면 False로 변경
        if user.is_first_login:
            user.set_account_status(is_first_login=False)
        
        db.commit()
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.from_user(user)
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
    - 아이디와 비밀번호로 인증
    """
    try:
        # 사용자 인증
        user = db.query(User).filter(User.user_id == login_data.user_id).first()
        
        if not user or not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="아이디 또는 비밀번호가 잘못되었습니다."
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="비활성화된 계정입니다."
            )
        
        # 토큰 생성
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.user_id, "user_id": user.id, "role": user.role},
            expires_delta=access_token_expires
        )
        
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = create_refresh_token(
            data={"sub": user.user_id, "user_id": user.id},
            expires_delta=refresh_token_expires
        )
        
        # 마지막 로그인 시간 업데이트
        user.update_last_login()
        # is_first_login이 True면 False로 변경
        if user.is_first_login:
            user.set_account_status(is_first_login=False)
        
        db.commit()
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.from_user(user)
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
            data={"sub": user.user_id, "user_id": user.id, "role": user.role},
            expires_delta=access_token_expires
        )
        
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        new_refresh_token = create_refresh_token(
            data={"sub": user.user_id, "user_id": user.id},
            expires_delta=refresh_token_expires
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.from_user(user)
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
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    현재 로그인한 사용자 정보 조회
    """
    # 🎯 데이터베이스에서 최신 사용자 정보 새로고침
    db.refresh(current_user)
    return UserResponse.from_user(current_user)

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
        
        return UserResponse.from_user(current_user)
        
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
    return [UserResponse.from_user(user) for user in users]

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

@router.post("/upload-profile-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    프로필 이미지 업로드
    """
    try:
        # 파일 유효성 검사
        if not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미지 파일만 업로드 가능합니다."
            )
        
        # 파일 크기 제한 (5MB)
        file_size = 0
        temp_file = file.file
        temp_file.seek(0, 2)  # 파일 끝으로 이동
        file_size = temp_file.tell()
        temp_file.seek(0)  # 파일 시작으로 되돌리기
        
        if file_size > 5 * 1024 * 1024:  # 5MB
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="파일 크기는 5MB를 초과할 수 없습니다."
            )
        
        # 업로드 디렉토리 생성
        upload_dir = Path("uploads/profile_images")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 파일 확장자 추출
        file_extension = Path(file.filename).suffix
        if not file_extension:
            file_extension = '.jpg'
        
        # 고유 파일명 생성
        unique_filename = f"{current_user.id}_{uuid.uuid4().hex}{file_extension}"
        file_path = upload_dir / unique_filename
        
        # 기존 프로필 이미지 삭제
        if current_user.profile_image and os.path.exists(current_user.profile_image):
            try:
                os.remove(current_user.profile_image)
            except:
                pass  # 삭제 실패해도 계속 진행
        
        # 파일 저장
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 데이터베이스 업데이트
        current_user.profile_image = str(file_path)
        current_user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(current_user)
        
        return {
            "message": "프로필 이미지가 성공적으로 업로드되었습니다.",
            "profile_image_url": f"/api/auth/profile-image/{current_user.id}",
            "user": UserResponse.from_user(current_user)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"프로필 이미지 업로드 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/profile-image/{user_id}")
async def get_profile_image(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    프로필 이미지 조회
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    if not user.profile_image or not os.path.exists(user.profile_image):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="프로필 이미지를 찾을 수 없습니다."
        )
    
    return FileResponse(
        user.profile_image,
        media_type="image/jpeg",
        headers={"Cache-Control": "max-age=3600"}
    )

@router.delete("/delete-profile-image")
async def delete_profile_image(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    프로필 이미지 삭제
    """
    try:
        # 기존 파일 삭제
        if current_user.profile_image and os.path.exists(current_user.profile_image):
            try:
                os.remove(current_user.profile_image)
            except:
                pass  # 파일 삭제 실패해도 계속 진행
        
        # 데이터베이스에서 프로필 이미지 경로 제거
        current_user.profile_image = None
        current_user.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {"message": "프로필 이미지가 성공적으로 삭제되었습니다."}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"프로필 이미지 삭제 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/verification-history", response_model=List[dict])
async def get_verification_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    현재 사용자의 인증 기록 조회
    """
    try:
        # 현재 사용자의 인증 기록 조회
        verification_records = db.query(VerificationRequest).filter(
            VerificationRequest.user_id == current_user.id
        ).order_by(VerificationRequest.submitted_at.desc()).all()
        
        # 응답 데이터 구성
        history_data = []
        for record in verification_records:
            # documents JSON 파싱
            documents = []
            if record.documents:
                try:
                    documents = json.loads(record.documents)
                except json.JSONDecodeError:
                    documents = []
            
            history_data.append({
                "id": record.id,
                "requestNumber": record.request_number,
                "verificationType": record.verification_type,
                "reason": record.reason,
                "status": record.status,
                "submittedAt": record.submitted_at.isoformat() if record.submitted_at else None,
                "reviewedAt": record.reviewed_at.isoformat() if record.reviewed_at else None,
                "reviewerComment": record.reviewer_comment,
                "rejectionReason": record.rejection_reason,
                "documents": documents
            })
        
        return history_data
        
    except Exception as e:
        logger.error(f"인증 기록 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="인증 기록 조회에 실패했습니다"
        )

@router.post("/verification-request")
async def create_verification_request(
    verification_data: VerificationRequestCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    인증 요청 생성
    """
    try:
        # 이미 인증된 사용자인지 확인
        if current_user.role in ['student', 'professor', 'admin']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 인증된 사용자입니다."
            )
        
        # 이미 대기 중인 인증 요청이 있는지 확인
        existing_request = db.query(VerificationRequest).filter(
            VerificationRequest.user_id == current_user.id,
            VerificationRequest.status == 'pending'
        ).first()
        
        if existing_request:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 처리 대기 중인 인증 요청이 있습니다."
            )
        
        # 다음 요청 번호 생성
        last_request = db.query(VerificationRequest).order_by(
            VerificationRequest.request_number.desc()
        ).first()
        next_request_number = (last_request.request_number + 1) if last_request else 1
        
        # 새 인증 요청 생성
        new_request = VerificationRequest(
            request_number=next_request_number,
            user_id=current_user.id,
            verification_type=verification_data.verification_type,
            reason=verification_data.reason,
            status='pending',
            submitted_at=datetime.now(),
            documents=json.dumps(verification_data.documents) if verification_data.documents else None
        )
        
        db.add(new_request)
        db.commit()
        db.refresh(new_request)
        
        logger.info(f"새 인증 요청 생성: {current_user.user_id} - {verification_data.verification_type}")
        
        return {
            "success": True,
            "message": "인증 요청이 성공적으로 제출되었습니다.",
            "request_id": new_request.id,
            "request_number": new_request.request_number
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"인증 요청 생성 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="인증 요청 제출 중 오류가 발생했습니다."
        )

@router.post("/complete-diagnostic-test", response_model=dict)
async def complete_diagnostic_test(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    진단테스트 완료 처리
    - 학생의 진단테스트 완료 상태를 업데이트
    - 진단테스트 완료 후 모든 기능 이용 가능
    """
    try:
        # 학생만 진단테스트 완료 가능
        if current_user.role != "student":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="학생만 진단테스트를 완료할 수 있습니다."
            )
        
        # 이미 완료된 경우 처리
        if getattr(current_user, 'diagnostic_test_completed', False):
            return {
                "success": True,
                "message": "이미 진단테스트를 완료하였습니다.",
                "data": {
                    "diagnostic_test_completed": True,
                    "diagnostic_test_completed_at": getattr(current_user, 'diagnostic_test_completed_at', None)
                }
            }
        
        # 진단테스트 완료 상태 업데이트
        current_user.diagnostic_test_completed = True
        current_user.diagnostic_test_completed_at = datetime.utcnow()
        current_user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(current_user)
        
        return {
            "success": True,
            "message": "진단테스트가 완료되었습니다. 이제 모든 기능을 이용할 수 있습니다.",
            "data": {
                "diagnostic_test_completed": True,
                "diagnostic_test_completed_at": current_user.diagnostic_test_completed_at
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"진단테스트 완료 처리 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/diagnostic-test-status", response_model=dict)
async def get_diagnostic_test_status(
    current_user: User = Depends(get_current_active_user)
):
    """
    현재 사용자의 진단테스트 완료 상태 조회
    """
    return {
        "success": True,
        "data": {
            "diagnostic_test_completed": getattr(current_user, 'diagnostic_test_completed', False),
            "diagnostic_test_completed_at": getattr(current_user, 'diagnostic_test_completed_at', None),
            "can_access_features": getattr(current_user, 'diagnostic_test_completed', False)
        }
    } 