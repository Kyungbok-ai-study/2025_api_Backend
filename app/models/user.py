"""
사용자 모델 정의
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression, func

from app.db.database import Base

class User(Base):
    """
    사용자 모델 클래스
    
    Attributes:
        id (int): 사용자 고유 ID
        school (str): 학교 이름 (기본값: '경복대학교')
        student_id (str): 학번 또는 교수 ID
        name (str): 이름
        email (str): 이메일 주소 (선택 사항)
        hashed_password (str): 암호화된 비밀번호
        role (str): 역할 ('student', 'professor', 'admin')
        is_first_login (bool): 첫 로그인 여부
        is_active (bool): 계정 활성화 상태
        profile_image (str): 프로필 이미지 URL (선택 사항)
        department (str): 학과/부서
        created_at (datetime): 계정 생성 시간
        updated_at (datetime): 계정 정보 업데이트 시간
        last_login_at (datetime): 마지막 로그인 시간 (선택 사항)
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    school = Column(String(255), default="경복대학교", nullable=False)
    student_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    hashed_password = Column(String(200), nullable=False)
    role = Column(String(20), nullable=False)
    is_first_login = Column(Boolean, default=True, server_default=expression.true(), nullable=False)
    is_active = Column(Boolean, default=True, server_default=expression.true(), nullable=False)
    profile_image = Column(String(500), nullable=True)
    department = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    
    # 관계 설정 (진단 및 학습 관련)
    test_sessions = relationship("TestSession", back_populates="user", cascade="all, delete-orphan")
    diagnosis_results = relationship("DiagnosisResult", back_populates="user", cascade="all, delete-orphan")
    learning_history = relationship("LearningLevelHistory", back_populates="user", cascade="all, delete-orphan")
    
    # 문제 풀이 관련 관계 (향후 추가 예정)
    # problem_submissions = relationship("ProblemSubmission", back_populates="user")
    # user_preferences = relationship("UserPreference", back_populates="user")
    
    def __repr__(self):
        """사용자 객체의 문자열 표현"""
        return f"<User(id={self.id}, name={self.name}, student_id={self.student_id}, role={self.role})>"
    
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
    
    def get_latest_diagnosis_result(self):
        """최신 진단 결과 가져오기"""
        if self.diagnosis_results:
            return max(self.diagnosis_results, key=lambda x: x.calculated_at)
        return None
    
    def get_current_learning_level(self, subject: str = None) -> float:
        """현재 학습 수준 가져오기"""
        latest_result = self.get_latest_diagnosis_result()
        if latest_result:
            return latest_result.learning_level
        return 0.0 