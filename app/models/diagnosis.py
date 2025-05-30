"""
진단 테스트 관련 데이터베이스 모델
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ENUM
import enum

from app.db.database import Base

class DiagnosisStatus(enum.Enum):
    """진단 테스트 상태"""
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class QuestionType(enum.Enum):
    """문제 유형"""
    MULTIPLE_CHOICE = "multiple_choice"
    SHORT_ANSWER = "short_answer"
    TRUE_FALSE = "true_false"
    ESSAY = "essay"

class DiagnosisSubject(enum.Enum):
    """진단 과목"""
    COMPUTER_SCIENCE = "computer_science"
    DATA_STRUCTURE = "data_structure"
    ALGORITHM = "algorithm"
    DATABASE = "database"
    PROGRAMMING = "programming"
    NETWORK = "network"

class TestSession(Base):
    """진단 테스트 세션"""
    __tablename__ = "test_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(ENUM(DiagnosisSubject), nullable=False)
    status = Column(ENUM(DiagnosisStatus), default=DiagnosisStatus.ACTIVE, nullable=False, index=True)
    
    # 시간 관리
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # 테스트 설정
    max_time_minutes = Column(Integer, default=60, nullable=True, comment="제한 시간 (분)")
    total_questions = Column(Integer, default=30, nullable=False)
    description = Column(Text, nullable=True)
    
    # 관계 설정
    user = relationship("User", back_populates="test_sessions")
    responses = relationship("TestResponse", back_populates="test_session", cascade="all, delete-orphan")
    results = relationship("DiagnosisResult", back_populates="test_session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TestSession(id={self.id}, user_id={self.user_id}, subject={self.subject}, status={self.status})>"

class TestResponse(Base):
    """진단 테스트 응답"""
    __tablename__ = "test_responses"

    id = Column(Integer, primary_key=True, index=True)
    test_session_id = Column(Integer, ForeignKey("test_sessions.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    
    # 응답 데이터
    user_answer = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=True)  # 채점 결과
    score = Column(Float, nullable=True, comment="부분 점수 (0.0-1.0)")
    
    # 시간 데이터
    time_spent_seconds = Column(Integer, nullable=True, comment="풀이 시간 (초)")
    answered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # 추가 정보
    confidence_level = Column(Integer, nullable=True, comment="확신도 (1-5)")
    attempt_count = Column(Integer, default=1, nullable=False)
    
    # 관계 설정
    test_session = relationship("TestSession", back_populates="responses")
    question = relationship("Question", back_populates="test_responses")

    def __repr__(self):
        return f"<TestResponse(id={self.id}, test_session_id={self.test_session_id}, question_id={self.question_id}, is_correct={self.is_correct})>"

class DiagnosisResult(Base):
    """진단 테스트 결과"""
    __tablename__ = "diagnosis_results"

    id = Column(Integer, primary_key=True, index=True)
    test_session_id = Column(Integer, ForeignKey("test_sessions.id"), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 핵심 지표
    learning_level = Column(Float, nullable=False, comment="학습 수준 지표 (0.0-1.0)", index=True)
    total_score = Column(Float, nullable=False, comment="총 획득 점수")
    max_possible_score = Column(Float, nullable=False, comment="최대 가능 점수")
    accuracy_rate = Column(Float, nullable=False, comment="정답률 (0.0-1.0)")
    
    # 통계 정보
    total_questions = Column(Integer, nullable=False)
    correct_answers = Column(Integer, nullable=False)
    total_time_spent = Column(Integer, nullable=True, comment="총 소요 시간 (초)")
    
    # 세부 분석
    difficulty_breakdown = Column(JSON, nullable=True, comment="난이도별 성과 분석")
    subject_breakdown = Column(JSON, nullable=True, comment="과목별 성과 분석")
    
    # 피드백
    feedback_message = Column(Text, nullable=True)
    recommended_next_steps = Column(JSON, nullable=True, comment="추천 다음 단계")
    
    # 비교 데이터
    percentile_rank = Column(Float, nullable=True, comment="백분위 순위 (0.0-100.0)")
    improvement_from_previous = Column(Float, nullable=True, comment="이전 대비 향상도")
    
    # 타임스탬프
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # 관계 설정
    test_session = relationship("TestSession", back_populates="results")
    user = relationship("User", back_populates="diagnosis_results")

    def __repr__(self):
        return f"<DiagnosisResult(id={self.id}, user_id={self.user_id}, learning_level={self.learning_level:.2f})>"

class LearningLevelHistory(Base):
    """학습 수준 변화 이력"""
    __tablename__ = "learning_level_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    diagnosis_result_id = Column(Integer, ForeignKey("diagnosis_results.id"), nullable=False, index=True)
    
    # 수준 데이터
    learning_level = Column(Float, nullable=False, comment="학습 수준 지표", index=True)
    subject = Column(ENUM(DiagnosisSubject), nullable=False, index=True)
    
    # 변화량
    previous_level = Column(Float, nullable=True, comment="이전 수준")
    level_change = Column(Float, nullable=True, comment="변화량")
    change_percentage = Column(Float, nullable=True, comment="변화율 (%)")
    
    # 컨텍스트 정보
    measurement_context = Column(JSON, nullable=True, comment="측정 컨텍스트")
    notes = Column(Text, nullable=True)
    
    # 타임스탬프
    measured_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # 관계 설정
    user = relationship("User", back_populates="learning_history")
    diagnosis_result = relationship("DiagnosisResult")

    def __repr__(self):
        return f"<LearningLevelHistory(id={self.id}, user_id={self.user_id}, level={self.learning_level:.2f}, measured_at={self.measured_at})>" 