"""
사용자 모델 정의
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression, func

from app.db.database import Base

class User(Base):
    """
    사용자 모델 클래스
    
    Attributes:
        id (int): 사용자 고유 ID
        school (str): 학교 이름 (기본값: '경복대학교')
        user_id (str): 로그인용 아이디 (고유)
        student_id (str): 학번 또는 교수 ID (선택 사항)
        name (str): 이름
        email (str): 이메일 주소 (선택 사항)
        hashed_password (str): 암호화된 비밀번호
        role (str): 역할 ('student', 'professor', 'admin')
        is_first_login (bool): 첫 로그인 여부
        is_active (bool): 계정 활성화 상태
        profile_image (str): 프로필 이미지 URL (선택 사항)
        department (str): 학과/부서
        admission_year (int): 입학 연도 (선택 사항)
        phone_number (str): 전화번호 (선택 사항)
        terms_agreed (bool): 서비스 이용약관 동의 여부
        privacy_agreed (bool): 개인정보 수집 및 이용 동의 여부 (필수)
        privacy_optional_agreed (bool): 개인정보 수집 및 이용 동의 여부 (선택)
        marketing_agreed (bool): 광고성 정보 수신 동의 여부
        identity_verified (bool): 본인 명의 확인 여부
        age_verified (bool): 만 14세 이상 확인 여부
        verification_method (str): 본인인증 방법 ('phone', 'ipin')
        created_at (datetime): 계정 생성 시간
        updated_at (datetime): 계정 정보 업데이트 시간
        last_login_at (datetime): 마지막 로그인 시간 (선택 사항)
        diagnostic_test_completed (bool): 진단테스트 완료 여부
        diagnostic_test_completed_at (datetime): 진단테스트 완료 일시
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    school = Column(String(255), default="경복대학교", nullable=False)
    user_id = Column(String(50), unique=True, index=True, nullable=False)
    student_id = Column(String(50), index=True, nullable=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    hashed_password = Column(String(200), nullable=False)
    role = Column(String(20), nullable=False, default="student")
    is_first_login = Column(Boolean, default=True, server_default=expression.true(), nullable=False)
    is_active = Column(Boolean, default=True, server_default=expression.true(), nullable=False)
    profile_image = Column(String(500), nullable=True)
    department = Column(String(100), nullable=True)
    admission_year = Column(Integer, nullable=True)
    phone_number = Column(String(20), nullable=True)
    
    # 이용약관 동의 관련 필드
    terms_agreed = Column(Boolean, default=False, nullable=False)
    privacy_agreed = Column(Boolean, default=False, nullable=False)
    privacy_optional_agreed = Column(Boolean, default=False, nullable=False)
    marketing_agreed = Column(Boolean, default=False, nullable=False)
    identity_verified = Column(Boolean, default=False, nullable=False)
    age_verified = Column(Boolean, default=False, nullable=False)
    verification_method = Column(String(20), nullable=True)  # 'phone' or 'ipin'
    
    # 진단테스트 완료 여부
    diagnostic_test_completed = Column(Boolean, default=False, nullable=False)
    diagnostic_test_completed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    
    # 인증 요청 관계 (문자열로 정의하여 순환 참조 방지)
    verification_requests = relationship("VerificationRequest", back_populates="user", cascade="all, delete-orphan")
    
    # 딥시크 학습 세션 관계
    deepseek_sessions = relationship("DeepSeekLearningSession", back_populates="professor", cascade="all, delete-orphan")
    
    def __repr__(self):
        """사용자 객체의 문자열 표현"""
        return f"<User(id={self.id}, name={self.name}, user_id={self.user_id}, role={self.role})>"
    
    @property
    def is_student(self) -> bool:
        """학생 여부 확인"""
        return self.role == "student"
    
    @property
    def is_professor(self) -> bool:
        """교수 여부 확인"""
        return self.role == "professor"
    
    @property
    def is_admin(self) -> bool:
        """관리자 여부 확인"""
        return self.role == "admin"