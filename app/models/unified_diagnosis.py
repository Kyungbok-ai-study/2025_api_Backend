"""
통합 진단 시스템 모델
diagnostic_tests와 test_sessions 시스템을 통합하여 모든 학과를 지원하는 최적화된 진단 시스템
"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

from app.db.database import Base
from app.models.enums import DiagnosisStatus, DiagnosisSubject, Department, QuestionType

class DiagnosisTest(Base):
    """통합 진단테스트 시스템 - 모든 학과 지원"""
    __tablename__ = "diagnosis_tests"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 기본 정보
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    department = Column(String(100), nullable=False, index=True)  # 학과명
    subject_area = Column(String(100), nullable=False, index=True)  # 과목 영역
    
    # 테스트 설정
    test_config = Column(JSONB, nullable=True)  # {
    #     "total_questions": 30,
    #     "time_limit_minutes": 60,
    #     "passing_score": 70,
    #     "random_order": true,
    #     "allow_retake": false,
    #     "max_attempts": 3
    # }
    
    # 점수 및 분류 기준
    scoring_criteria = Column(JSONB, nullable=True)  # {
    #     "levels": {
    #         "excellent": {"min": 90, "max": 100, "label": "우수"},
    #         "good": {"min": 80, "max": 89, "label": "양호"},
    #         "average": {"min": 70, "max": 79, "label": "보통"},
    #         "poor": {"min": 60, "max": 69, "label": "미흡"},
    #         "fail": {"min": 0, "max": 59, "label": "부족"}
    #     },
    #     "weights": {"correctness": 0.7, "speed": 0.2, "consistency": 0.1}
    # }
    
    # 분석 설정
    analysis_config = Column(JSONB, nullable=True)  # {
    #     "enable_bkt": true,      # Bayesian Knowledge Tracing
    #     "enable_dkt": true,      # Deep Knowledge Tracing  
    #     "enable_irt": true,      # Item Response Theory
    #     "adaptive_testing": false,
    #     "real_time_feedback": true
    # }
    
    # 메타데이터
    test_metadata = Column(JSONB, nullable=True)  # {
    #     "version": "2.0",
    #     "difficulty_distribution": {"easy": 0.3, "medium": 0.5, "hard": 0.2},
    #     "topic_coverage": ["기초이론", "응용", "실무"],
    #     "learning_objectives": ["목표1", "목표2"],
    #     "prerequisites": ["선수과목1"]
    # }
    
    # 상태 관리
    status = Column(String(20), default="draft", index=True)  # draft, active, inactive, archived
    is_published = Column(Boolean, default=False, nullable=False)
    publish_date = Column(DateTime(timezone=True), nullable=True)
    expire_date = Column(DateTime(timezone=True), nullable=True)
    
    # 작성자 정보
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=False)
    
    # 관계 설정
    questions = relationship("DiagnosisQuestion", back_populates="test", cascade="all, delete-orphan")
    sessions = relationship("DiagnosisSession", back_populates="test", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<DiagnosisTest(id={self.id}, title={self.title}, department={self.department})>"
    
    @property
    def total_questions(self):
        """총 문제 수 반환"""
        return self.test_config.get("total_questions", 30) if self.test_config else 30
    
    @property
    def time_limit_minutes(self):
        """제한 시간 반환"""
        return self.test_config.get("time_limit_minutes", 60) if self.test_config else 60
    
    @property
    def version(self):
        """버전 반환"""
        return self.test_metadata.get("version", "1.0") if self.test_metadata else "1.0"

class DiagnosisQuestion(Base):
    """통합 진단테스트 문제"""
    __tablename__ = "diagnosis_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("diagnosis_tests.id"), nullable=False, index=True)
    
    # 기본 정보
    question_id = Column(String(50), unique=True, index=True)  # DIAG_CS_001, DIAG_PT_001 등
    question_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    question_type = Column(String(50), default="multiple_choice")  # multiple_choice, true_false, essay 등
    
    # 선택지 및 정답
    options = Column(JSONB, nullable=True)  # {"1": "선택지1", "2": "선택지2", ...}
    correct_answer = Column(String(20), nullable=False)
    explanation = Column(Text, nullable=True)  # 해설
    
    # 분류 정보 (통합)
    classification = Column(JSONB, nullable=True)  # {
    #     "subject": "데이터베이스",
    #     "area": "관계형 모델", 
    #     "difficulty": "중",
    #     "bloom_taxonomy": "분석",
    #     "domain": "이론",
    #     "keywords": ["관계형", "스키마", "정규화"]
    # }
    
    # 문제 특성 (통합)
    question_properties = Column(JSONB, nullable=True)  # {
    #     "estimated_time": 120,    # 예상 소요 시간 (초)
    #     "points": 5.0,           # 배점
    #     "difficulty_score": 7,    # 1-10 난이도
    #     "discrimination_power": 8, # 변별력
    #     "diagnostic_value": 9     # 진단 가치
    # }
    
    # AI 분석 결과 (통합)
    ai_analysis = Column(JSONB, nullable=True)  # {
    #     "auto_generated": false,
    #     "similarity_check": {"score": 0.2, "similar_questions": []},
    #     "difficulty_prediction": 7.2,
    #     "topic_classification": ["데이터베이스", "SQL"],
    #     "quality_score": 8.5
    # }
    
    # 출처 정보
    source_info = Column(JSONB, nullable=True)  # {
    #     "source_type": "textbook",
    #     "source_name": "데이터베이스 시스템",
    #     "chapter": "3장",
    #     "page": 45,
    #     "year": 2024,
    #     "author": "김교수"
    # }
    
    # 순서 및 상태
    display_order = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # 관계 설정
    test = relationship("DiagnosisTest", back_populates="questions")
    responses = relationship("DiagnosisResponse", back_populates="question", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<DiagnosisQuestion(id={self.id}, question_id={self.question_id})>"

class DiagnosisSession(Base):
    """통합 진단 세션 (TestSession + DiagnosticSubmission 통합)"""
    __tablename__ = "diagnosis_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("diagnosis_tests.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 세션 정보
    session_token = Column(String(100), unique=True, index=True)  # 고유 세션 토큰
    attempt_number = Column(Integer, default=1, nullable=False)  # 시도 횟수
    
    # 상태 관리
    status = Column(String(20), default="not_started", index=True)  
    # not_started, in_progress, completed, expired, abandoned
    
    # 시간 관리
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    total_time_spent = Column(Integer, nullable=True)  # 총 소요 시간 (초)
    
    # 점수 및 결과
    raw_score = Column(Float, default=0.0)  # 원점수
    percentage_score = Column(Float, default=0.0)  # 백분율 점수
    scaled_score = Column(Float, nullable=True)  # 표준화 점수
    
    # 응답 통계
    response_stats = Column(JSONB, nullable=True)  # {
    #     "total_questions": 30,
    #     "answered": 25,
    #     "correct": 20,
    #     "incorrect": 5,
    #     "skipped": 5,
    #     "average_time_per_question": 45.2
    # }
    
    # 진단 결과
    diagnosis_result = Column(JSONB, nullable=True)  # {
    #     "overall_level": "good",
    #     "level_score": 82.5,
    #     "strengths": ["데이터베이스 설계", "SQL 기초"],
    #     "weaknesses": ["고급 SQL", "성능 최적화"],
    #     "recommendations": ["추천 학습 경로"],
    #     "competency_map": {"theory": 85, "practice": 75, "application": 80}
    # }
    
    # 고급 분석 결과 (통합)
    advanced_analysis = Column(JSONB, nullable=True)  # {
    #     "bkt_analysis": {...},    # Bayesian Knowledge Tracing
    #     "dkt_analysis": {...},    # Deep Knowledge Tracing
    #     "irt_analysis": {...},    # Item Response Theory
    #     "learning_path": {...},   # 개인화 학습 경로
    #     "peer_comparison": {...}  # 동료 비교
    # }
    
    # 메타데이터
    session_metadata = Column(JSONB, nullable=True)  # {
    #     "browser": "Chrome 120",
    #     "device": "desktop",
    #     "ip_address": "123.456.789.0",
    #     "location": "서울",
    #     "environment": "normal"
    # }
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=False)
    
    # 관계 설정
    test = relationship("DiagnosisTest", back_populates="sessions")
    user = relationship("User")
    responses = relationship("DiagnosisResponse", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<DiagnosisSession(id={self.id}, user_id={self.user_id}, status={self.status})>"

class DiagnosisResponse(Base):
    """통합 진단 응답 (TestResponse + DiagnosticResponse 통합)"""
    __tablename__ = "diagnosis_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("diagnosis_sessions.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("diagnosis_questions.id"), nullable=False, index=True)
    
    # 응답 정보
    user_answer = Column(String(500), nullable=True)  # 사용자 답변
    is_correct = Column(Boolean, nullable=True)  # 정답 여부
    points_earned = Column(Float, default=0.0)  # 획득 점수
    
    # 시간 분석
    response_time = Column(Float, nullable=True)  # 응답 시간 (초)
    first_response_time = Column(Float, nullable=True)  # 첫 응답까지 시간
    total_view_time = Column(Float, nullable=True)  # 총 문제 보기 시간
    
    # 응답 행동 분석
    response_behavior = Column(JSONB, nullable=True)  # {
    #     "answer_changes": 2,        # 답변 변경 횟수
    #     "confidence_level": "high", # 확신도
    #     "elimination_pattern": ["A", "B"], # 제거한 선택지
    #     "hesitation_time": 15.2,    # 망설임 시간
    #     "focus_lost_count": 1       # 화면 이탈 횟수
    # }
    
    # 인지 상태 분석 (고급)
    cognitive_analysis = Column(JSONB, nullable=True)  # {
    #     "knowledge_state": 0.75,      # BKT 지식 상태
    #     "learning_gain": 0.1,         # 학습 효과
    #     "difficulty_perceived": 7,     # 인지된 난이도
    #     "mental_effort": 6,            # 인지 부하
    #     "strategy_used": "elimination" # 사용된 전략
    # }
    
    # 메타데이터
    response_metadata = Column(JSONB, nullable=True)  # {
    #     "sequence_number": 5,
    #     "question_version": "1.2",
    #     "randomized_options": true,
    #     "hint_used": false,
    #     "help_accessed": false
    # }
    
    answered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # 관계 설정
    session = relationship("DiagnosisSession", back_populates="responses")
    question = relationship("DiagnosisQuestion", back_populates="responses")
    
    def __repr__(self):
        return f"<DiagnosisResponse(id={self.id}, session_id={self.session_id}, is_correct={self.is_correct})>"

class StudentDiagnosisHistory(Base):
    """학생 진단 이력 (시계열 분석 및 학습 추적)"""
    __tablename__ = "student_diagnosis_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    department = Column(String(100), nullable=False, index=True)
    subject_area = Column(String(100), nullable=False, index=True)
    
    # 시계열 데이터 (통합)
    learning_progression = Column(JSONB, nullable=True)  # {
    #     "timestamps": ["2024-01-01", "2024-01-15", ...],
    #     "knowledge_levels": [0.3, 0.5, 0.7, ...],
    #     "skill_mastery": {...},
    #     "competency_growth": {...},
    #     "learning_velocity": 0.05
    # }
    
    # 예측 모델 결과 (통합)
    predictions = Column(JSONB, nullable=True)  # {
    #     "next_performance": {"score": 85, "confidence": 0.8},
    #     "mastery_timeline": {"estimated_days": 30},
    #     "risk_factors": ["time_management", "concept_gaps"],
    #     "success_probability": 0.75
    # }
    
    # 개인화 추천 (통합)
    recommendations = Column(JSONB, nullable=True)  # {
    #     "immediate_actions": ["복습: 데이터베이스 정규화"],
    #     "learning_path": ["기초 강화", "심화 학습"],
    #     "study_strategies": ["스페이싱 학습", "능동적 복습"],
    #     "resources": ["추천 교재", "온라인 강의"],
    #     "timeline": {"short_term": "1주", "long_term": "1개월"}
    # }
    
    # 성과 통계
    performance_stats = Column(JSONB, nullable=True)  # {
    #     "total_attempts": 5,
    #     "best_score": 92.5,
    #     "average_score": 78.3,
    #     "improvement_rate": 0.15,
    #     "consistency_score": 0.8,
    #     "peer_ranking": "top_25%"
    # }
    
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # 관계 설정
    user = relationship("User")
    
    def __repr__(self):
        return f"<StudentDiagnosisHistory(id={self.id}, user_id={self.user_id}, department={self.department})>" 