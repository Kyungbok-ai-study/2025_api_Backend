"""
진단 테스트 관련 데이터베이스 모델 (Legacy - 마이그레이션 예정)

⚠️ 주의: 이 파일은 통합 진단 시스템(unified_diagnosis.py)으로 마이그레이션 예정입니다.
새로운 개발은 unified_diagnosis.py를 사용하세요.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, JSON, ARRAY, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ENUM

from app.db.database import Base
from app.models.enums import DiagnosisStatus, QuestionType, DiagnosisSubject

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
    user = relationship("User")
    responses = relationship("TestResponse", back_populates="test_session", cascade="all, delete-orphan")
    results = relationship("DiagnosisResult", back_populates="test_session", cascade="all, delete-orphan")
    # 새로운 관계 추가
    multi_choice_sessions = relationship("MultiChoiceTestSession", back_populates="test_session", cascade="all, delete-orphan")

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

# 새로운 모델들 - 1문제 30선택지 형태
class MultiChoiceTestSession(Base):
    """다중 선택지 진단 테스트 세션 (1문제 30선택지)"""
    __tablename__ = "multi_choice_test_sessions"

    id = Column(Integer, primary_key=True, index=True)
    test_session_id = Column(Integer, ForeignKey("test_sessions.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    
    # 30개 선택지 데이터
    choices = Column(ARRAY(String), nullable=False, comment="30개 선택지 목록")
    correct_choice_index = Column(Integer, nullable=False, comment="정답 선택지 인덱스 (0-29)")
    
    # 설정
    max_choices = Column(Integer, default=30, nullable=False)
    shuffle_choices = Column(Boolean, default=True, nullable=False)
    
    # 메타데이터
    choice_metadata = Column(JSON, nullable=True, comment="선택지 메타데이터")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # 관계 설정
    test_session = relationship("TestSession", back_populates="multi_choice_sessions")
    question = relationship("Question")
    responses = relationship("MultiChoiceTestResponse", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MultiChoiceTestSession(id={self.id}, question_id={self.question_id}, choices_count={len(self.choices) if self.choices else 0})>"

class MultiChoiceTestResponse(Base):
    """다중 선택지 테스트 응답"""
    __tablename__ = "multi_choice_test_responses"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("multi_choice_test_sessions.id"), nullable=False, index=True)
    
    # 응답 데이터
    selected_choice_index = Column(Integer, nullable=False, comment="선택한 선택지 인덱스 (0-29)")
    selected_choice_content = Column(Text, nullable=False, comment="선택한 선택지 내용")
    is_correct = Column(Boolean, nullable=False)
    
    # 선택 과정 분석 데이터
    eliminated_choices = Column(ARRAY(Integer), nullable=True, comment="제거한 선택지 인덱스 목록")
    confidence_level = Column(String(10), default="medium", nullable=False, comment="확신도 (low/medium/high)")
    choice_changes = Column(Integer, default=0, nullable=False, comment="선택 변경 횟수")
    
    # 시간 데이터
    time_spent_seconds = Column(Integer, nullable=False, comment="총 소요 시간 (초)")
    choice_timeline = Column(JSON, nullable=True, comment="선택 과정 타임라인")
    
    # 전략 분석
    elimination_strategy = Column(JSON, nullable=True, comment="제거 전략 분석")
    decision_pattern = Column(String(50), nullable=True, comment="의사결정 패턴")
    
    answered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # 관계 설정
    session = relationship("MultiChoiceTestSession", back_populates="responses")

    def __repr__(self):
        return f"<MultiChoiceTestResponse(id={self.id}, selected_choice={self.selected_choice_index}, is_correct={self.is_correct})>"

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
    
    # 새로운 분석 필드 - 다중 선택지 전용
    choice_strategy_analysis = Column(JSON, nullable=True, comment="선택 전략 분석")
    elimination_effectiveness = Column(Float, nullable=True, comment="제거 전략 효과성 (0.0-1.0)")
    decision_confidence_score = Column(Float, nullable=True, comment="의사결정 확신도 점수")
    cognitive_load_analysis = Column(JSON, nullable=True, comment="인지 부하 분석")
    
    # 피드백
    feedback_message = Column(Text, nullable=True)
    recommended_next_steps = Column(JSON, nullable=True, comment="추천 다음 단계")
    
    # 비교 데이터
    percentile_rank = Column(Float, nullable=True, comment="백분위 순위 (0.0-100.0)")
    improvement_from_previous = Column(Float, nullable=True, comment="이전 대비 향상도")
    
    # AI 분석 데이터 (DeepSeek 분석 결과 저장) - 임시로 주석 처리 (DB 컬럼 없음)
    # analysis_data = Column(JSON, nullable=True, comment="AI 분석 결과 및 상세 데이터")
    
    # 타임스탬프
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # 관계 설정
    test_session = relationship("TestSession", back_populates="results")
    user = relationship("User")

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
    user = relationship("User")
    diagnosis_result = relationship("DiagnosisResult")

    def __repr__(self):
        return f"<LearningLevelHistory(id={self.id}, user_id={self.user_id}, level={self.learning_level:.2f}, measured_at={self.measured_at})>"

class DiagnosticSession(Base):
    """진단테스트 세션 모델"""
    __tablename__ = "diagnostic_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(50), unique=True, nullable=False, comment='세션 고유 ID')
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment='사용자 ID')
    test_type = Column(String(50), nullable=False, comment='테스트 타입')
    department = Column(String(50), nullable=False, comment='학과명')
    round_number = Column(Integer, nullable=False, default=1, comment='진단테스트 회차 (1-10차)')
    total_questions = Column(Integer, nullable=False, comment='총 문제 수')
    time_limit_minutes = Column(Integer, nullable=False, comment='제한 시간(분)')
    started_at = Column(DateTime, nullable=False, comment='시작 시간')
    completed_at = Column(DateTime, nullable=True, comment='완료 시간')
    total_score = Column(Float, nullable=True, comment='총 점수')
    correct_answers = Column(Integer, nullable=True, comment='정답 수')
    wrong_answers = Column(Integer, nullable=True, comment='오답 수')
    total_time_ms = Column(BigInteger, nullable=True, comment='총 소요 시간(밀리초)')
    status = Column(String(20), nullable=False, default='in_progress', comment='상태')
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 관계 설정
    answers = relationship("DiagnosticAnswer", back_populates="session", cascade="all, delete-orphan")
    ai_analysis = relationship("DiagnosticAIAnalysis", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<DiagnosticSession(session_id='{self.session_id}', round={self.round_number}, test_type='{self.test_type}', status='{self.status}')>"

class DiagnosticAnswer(Base):
    """진단테스트 답변 모델 (각 문제별 상세 정보)"""
    __tablename__ = "diagnostic_answers"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(50), ForeignKey('diagnostic_sessions.session_id'), nullable=False, comment='세션 ID')
    question_id = Column(String(50), nullable=False, comment='문제 ID')
    question_number = Column(Integer, nullable=False, comment='문제 번호')
    selected_answer = Column(String(10), nullable=True, comment='선택한 답')
    correct_answer = Column(String(10), nullable=False, comment='정답')
    is_correct = Column(Boolean, nullable=False, comment='정답 여부')
    time_spent_ms = Column(BigInteger, nullable=False, comment='풀이 시간(밀리초)')
    difficulty_level = Column(String(20), nullable=True, comment='난이도')
    domain = Column(String(50), nullable=True, comment='영역')
    question_type = Column(String(30), nullable=True, comment='문제 유형')
    answered_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    # 관계 설정
    session = relationship("DiagnosticSession", back_populates="answers")
    
    def __repr__(self):
        return f"<DiagnosticAnswer(question_id='{self.question_id}', is_correct={self.is_correct})>"

class DiagnosticAIAnalysis(Base):
    """AI 분석 결과 모델"""
    __tablename__ = "diagnostic_ai_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(50), ForeignKey('diagnostic_sessions.session_id'), nullable=False, comment='세션 ID')
    analysis_type = Column(String(30), nullable=False, comment='분석 타입')
    analysis_data = Column(JSON, nullable=False, comment='분석 결과 JSON 데이터')
    weak_areas = Column(JSON, nullable=True, comment='약한 영역 분석')
    recommendations = Column(JSON, nullable=True, comment='개선 권장사항')
    peer_comparison = Column(JSON, nullable=True, comment='다른 학생들과의 비교')
    confidence_score = Column(Float, nullable=True, comment='분석 신뢰도 점수')
    ai_model_version = Column(String(20), nullable=True, comment='사용된 AI 모델 버전')
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    # 관계 설정
    session = relationship("DiagnosticSession", back_populates="ai_analysis")
    
    def __repr__(self):
        return f"<DiagnosticAIAnalysis(session_id='{self.session_id}', analysis_type='{self.analysis_type}')>"

class DiagnosticStatistics(Base):
    """진단테스트 통계 모델 (다른 학생들과 비교용)"""
    __tablename__ = "diagnostic_statistics"
    
    id = Column(Integer, primary_key=True, index=True)
    test_type = Column(String(50), nullable=False, comment='테스트 타입')
    department = Column(String(50), nullable=False, comment='학과명')
    question_id = Column(String(50), nullable=False, comment='문제 ID')
    total_attempts = Column(Integer, nullable=False, default=0, comment='총 시도 횟수')
    correct_attempts = Column(Integer, nullable=False, default=0, comment='정답 횟수')
    avg_time_ms = Column(BigInteger, nullable=False, default=0, comment='평균 풀이 시간')
    difficulty_rating = Column(Float, nullable=True, comment='실제 난이도 평가')
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<DiagnosticStatistics(test_type='{self.test_type}', question_id='{self.question_id}')>"

# 진단테스트 세션 상태 열거형
class SessionStatus:
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    EXPIRED = "expired"

# 분석 타입 열거형
class AnalysisType:
    COMPREHENSIVE = "comprehensive"
    TIME_ANALYSIS = "time_analysis"
    TYPE_ANALYSIS = "type_analysis"
    DIFFICULTY_ANALYSIS = "difficulty_analysis"
    PEER_COMPARISON = "peer_comparison" 