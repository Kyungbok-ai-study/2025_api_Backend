"""
사용자 모델 정의 - 최적화된 버전으로 업그레이드
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression, func
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

from app.db.database import Base

class User(Base):
    """
    최적화된 사용자 모델 - 26개 컬럼에서 15개 컬럼으로 최적화
    JSON 필드를 활용한 관련 정보 통합
    """
    __tablename__ = "users"
    
    # 핵심 식별 정보 (필수)
    id = Column(Integer, primary_key=True, index=True)
    school = Column(String(255), default="경복대학교", nullable=False)
    user_id = Column(String(50), unique=True, index=True, nullable=False)  # 로그인 ID
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    hashed_password = Column(String(200), nullable=False)
    role = Column(String(20), nullable=False, default="student", index=True)
    
    # 프로필 정보 (통합)
    profile_info = Column(JSONB, nullable=True)  # {
    #     "student_id": "2024001234",           # 학번 (기존 student_id)
    #     "department": "간호학과",
    #     "admission_year": 2024,
    #     "phone_number": "010-1234-5678",
    #     "profile_image": "/images/profile.jpg"
    # }
    
    # 계정 상태 (통합)
    account_status = Column(JSONB, nullable=True)  # {
    #     "is_active": true,
    #     "is_first_login": true,
    #     "last_login_at": "2024-01-01T00:00:00"
    # }
    
    # 이용약관 및 인증 정보 (통합)
    agreements_verification = Column(JSONB, nullable=True)  # {
    #     "terms_agreed": true,
    #     "privacy_agreed": true,
    #     "privacy_optional_agreed": false,
    #     "marketing_agreed": false,
    #     "identity_verified": true,
    #     "age_verified": true,
    #     "verification_method": "phone"
    # }
    
    # 진단테스트 정보 (통합)
    diagnosis_info = Column(JSONB, nullable=True)  # {
    #     "completed": true,
    #     "completed_at": "2024-01-01T00:00:00",
    #     "latest_score": 85.5,
    #     "test_count": 3
    # }
    
    # 기본 타임스탬프 (필수)
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 관계 설정 (기존 호환성 유지)
    verification_requests = relationship("VerificationRequest", back_populates="user", cascade="all, delete-orphan")
    
    # 교수-학생 매칭 관계
    supervised_students = relationship("ProfessorStudentMatch", foreign_keys="ProfessorStudentMatch.professor_id", back_populates="professor")
    supervisors = relationship("ProfessorStudentMatch", foreign_keys="ProfessorStudentMatch.student_id", back_populates="student")
    
    # 진단테스트 진행 상황 관계
    diagnosis_progress = relationship("StudentDiagnosisProgress", back_populates="user", cascade="all, delete-orphan")

    
    def __repr__(self):
        return f"<User(id={self.id}, user_id={self.user_id}, role={self.role})>"
    
    # 편의 메서드들 (기존 호환성)
    
    @property
    def student_id(self):
        """학번 반환 (기존 호환성)"""
        return self.profile_info.get("student_id") if self.profile_info else None
    
    @property
    def department(self):
        """학과 반환"""
        return self.profile_info.get("department") if self.profile_info else None
    
    @property
    def admission_year(self):
        """입학년도 반환"""
        return self.profile_info.get("admission_year") if self.profile_info else None
    
    @property
    def phone_number(self):
        """전화번호 반환"""
        return self.profile_info.get("phone_number") if self.profile_info else None
    
    @property
    def profile_image(self):
        """프로필 이미지 반환"""
        return self.profile_info.get("profile_image") if self.profile_info else None
    
    @property
    def is_active(self):
        """활성화 상태 반환"""
        return self.account_status.get("is_active", True) if self.account_status else True
    
    @property
    def is_first_login(self):
        """첫 로그인 여부 반환"""
        return self.account_status.get("is_first_login", True) if self.account_status else True
    
    @property
    def last_login_at(self):
        """마지막 로그인 시간 반환"""
        return self.account_status.get("last_login_at") if self.account_status else None
    
    @property
    def terms_agreed(self):
        """약관 동의 여부 반환"""
        return self.agreements_verification.get("terms_agreed", False) if self.agreements_verification else False
    
    @property
    def privacy_agreed(self):
        """개인정보 동의 여부 반환"""
        return self.agreements_verification.get("privacy_agreed", False) if self.agreements_verification else False
    
    @property
    def privacy_optional_agreed(self):
        """개인정보 선택 동의 여부 반환"""
        return self.agreements_verification.get("privacy_optional_agreed", False) if self.agreements_verification else False
    
    @property
    def marketing_agreed(self):
        """마케팅 동의 여부 반환"""
        return self.agreements_verification.get("marketing_agreed", False) if self.agreements_verification else False
    
    @property
    def identity_verified(self):
        """본인인증 여부 반환"""
        return self.agreements_verification.get("identity_verified", False) if self.agreements_verification else False
    
    @property
    def age_verified(self):
        """연령 인증 여부 반환"""
        return self.agreements_verification.get("age_verified", False) if self.agreements_verification else False
    
    @property
    def verification_method(self):
        """인증 방법 반환"""
        return self.agreements_verification.get("verification_method") if self.agreements_verification else None
    
    @property
    def diagnostic_test_completed(self):
        """진단테스트 완료 여부 반환"""
        return self.diagnosis_info.get("completed", False) if self.diagnosis_info else False
    
    @property
    def diagnostic_test_completed_at(self):
        """진단테스트 완료 시간 반환"""
        return self.diagnosis_info.get("completed_at") if self.diagnosis_info else None
    
    # 설정 메서드들
    
    def set_profile_info(self, student_id=None, department=None, admission_year=None, 
                        phone_number=None, profile_image=None):
        """프로필 정보 설정"""
        if not self.profile_info:
            self.profile_info = {}
        
        if student_id is not None:
            self.profile_info["student_id"] = student_id
        if department is not None:
            self.profile_info["department"] = department
        if admission_year is not None:
            self.profile_info["admission_year"] = admission_year
        if phone_number is not None:
            self.profile_info["phone_number"] = phone_number
        if profile_image is not None:
            self.profile_info["profile_image"] = profile_image
    
    def set_account_status(self, is_active=None, is_first_login=None, last_login_at=None):
        """계정 상태 설정"""
        if not self.account_status:
            self.account_status = {}
        
        if is_active is not None:
            self.account_status["is_active"] = is_active
        if is_first_login is not None:
            self.account_status["is_first_login"] = is_first_login
        if last_login_at is not None:
            self.account_status["last_login_at"] = last_login_at
    
    def set_agreements(self, terms_agreed=None, privacy_agreed=None, 
                       privacy_optional_agreed=None, marketing_agreed=None):
        """약관 동의 정보 설정"""
        if not self.agreements_verification:
            self.agreements_verification = {}
        
        if terms_agreed is not None:
            self.agreements_verification["terms_agreed"] = terms_agreed
        if privacy_agreed is not None:
            self.agreements_verification["privacy_agreed"] = privacy_agreed
        if privacy_optional_agreed is not None:
            self.agreements_verification["privacy_optional_agreed"] = privacy_optional_agreed
        if marketing_agreed is not None:
            self.agreements_verification["marketing_agreed"] = marketing_agreed
    
    def set_verification_status(self, identity_verified=None, age_verified=None, 
                               verification_method=None):
        """인증 상태 설정"""
        if not self.agreements_verification:
            self.agreements_verification = {}
        
        if identity_verified is not None:
            self.agreements_verification["identity_verified"] = identity_verified
        if age_verified is not None:
            self.agreements_verification["age_verified"] = age_verified
        if verification_method is not None:
            self.agreements_verification["verification_method"] = verification_method
    
    def set_diagnostic_test_info(self, completed=None, completed_at=None, 
                                latest_score=None, test_count=None):
        """진단테스트 정보 설정"""
        if not self.diagnosis_info:
            self.diagnosis_info = {}
        
        if completed is not None:
            self.diagnosis_info["completed"] = completed
        if completed_at is not None:
            self.diagnosis_info["completed_at"] = completed_at
        if latest_score is not None:
            self.diagnosis_info["latest_score"] = latest_score
        if test_count is not None:
            self.diagnosis_info["test_count"] = test_count
    
    def update_last_login(self):
        """마지막 로그인 시간 업데이트"""
        if not self.account_status:
            self.account_status = {}
        self.account_status["last_login_at"] = datetime.utcnow().isoformat()
        self.account_status["is_first_login"] = False
    
    # 역할 확인 메서드들 (기존 호환성)
    
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