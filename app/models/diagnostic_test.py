"""
진단테스트 데이터베이스 모델
물리치료학과 학생 수준 진단을 위한 30문제 시스템
"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class DiagnosticTest(Base):
    """진단테스트 메인 정보"""
    __tablename__ = "diagnostic_tests"
    
    id = Column(Integer, primary_key=True, index=True)
    department = Column(String(100), nullable=False, index=True)  # 학과명 (물리치료학과)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    total_questions = Column(Integer, nullable=False)
    time_limit = Column(Integer, default=60)  # 분
    version = Column(String(20), default="1.0")
    is_active = Column(Boolean, default=True)
    
    # 점수 기준
    scoring_criteria = Column(JSON)  # 점수 기준 및 레벨 분류
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 관계
    questions = relationship("DiagnosticQuestion", back_populates="test", cascade="all, delete-orphan")
    submissions = relationship("DiagnosticSubmission", back_populates="test")

class DiagnosticQuestion(Base):
    """진단테스트 문제"""
    __tablename__ = "diagnostic_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("diagnostic_tests.id"), nullable=False)
    
    question_id = Column(String(20), unique=True, index=True)  # DIAG_001
    question_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    options = Column(JSON)  # 선택지
    correct_answer = Column(String(10), nullable=False)
    
    # 과목 정보
    subject = Column(String(100))
    area_name = Column(String(100))
    year = Column(Integer)
    original_question_number = Column(Integer)
    
    # AI 분석 결과
    difficulty = Column(Integer)  # 1-10
    difficulty_level = Column(String(20))  # 쉬움/보통/어려움
    question_type = Column(String(50))  # 기본개념/응용/실무/종합판단
    domain = Column(String(50))  # 신경계/근골격계/심폐 등
    diagnostic_suitability = Column(Integer)  # 1-10
    discrimination_power = Column(Integer)  # 1-10
    
    # 진단테스트용 메타데이터
    points = Column(Float, default=0.0)
    
    # 원본 정보
    source_info = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 관계
    test = relationship("DiagnosticTest", back_populates="questions")
    responses = relationship("DiagnosticResponse", back_populates="question")

class DiagnosticSubmission(Base):
    """진단테스트 제출 (학생별)"""
    __tablename__ = "diagnostic_submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("diagnostic_tests.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 제출 정보
    status = Column(String(20), default="in_progress")  # in_progress, completed, expired
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True))
    
    # 점수 정보
    total_score = Column(Float, default=0.0)
    correct_count = Column(Integer, default=0)
    wrong_count = Column(Integer, default=0)
    unanswered_count = Column(Integer, default=0)
    
    # 진단 결과
    level_classification = Column(String(20))  # 상급/중급/하급/미흡
    diagnostic_result = Column(JSON)  # 상세 진단 결과
    
    # BKT/DKT 분석 결과
    bkt_analysis = Column(JSON)  # Bayesian Knowledge Tracing 결과
    dkt_analysis = Column(JSON)  # Deep Knowledge Tracing 결과
    rnn_analysis = Column(JSON)  # RNN/LSTM 분석 결과
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 관계
    test = relationship("DiagnosticTest", back_populates="submissions")
    user = relationship("User")
    responses = relationship("DiagnosticResponse", back_populates="submission")

class DiagnosticResponse(Base):
    """진단테스트 문제별 응답"""
    __tablename__ = "diagnostic_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("diagnostic_submissions.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("diagnostic_questions.id"), nullable=False)
    
    # 응답 정보
    user_answer = Column(String(10))  # 학생이 선택한 답
    is_correct = Column(Boolean)
    response_time = Column(Float)  # 응답 시간 (초)
    
    # 분석용 데이터
    confidence_level = Column(Float)  # 확신도 (BKT용)
    knowledge_state = Column(Float)  # 지식 상태 (DKT용)
    
    answered_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 관계
    submission = relationship("DiagnosticSubmission", back_populates="responses")
    question = relationship("DiagnosticQuestion", back_populates="responses")

class StudentDiagnosticHistory(Base):
    """학생 진단 이력 (BKT/DKT 시계열 분석용)"""
    __tablename__ = "student_diagnostic_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    department = Column(String(100), nullable=False)
    
    # 시계열 데이터
    knowledge_states = Column(JSON)  # 지식 상태 변화
    learning_progression = Column(JSON)  # 학습 진행도
    skill_mastery = Column(JSON)  # 기술별 숙련도
    
    # 예측 모델 결과
    predicted_performance = Column(JSON)  # 성과 예측
    recommended_actions = Column(JSON)  # 추천 학습 행동
    
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    
    # 관계
    user = relationship("User") 