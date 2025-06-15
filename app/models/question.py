"""
문제 및 답변 데이터 모델 - 최적화된 버전

파싱된 문제, 답변, 정답, 유형 등을 저장하기 위한 SQLAlchemy 모델
JSONB 필드를 활용한 메타데이터 통합으로 컬럼 수 50% 감소
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime, Enum, JSON, Float, UniqueConstraint, Table
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.mutable import MutableList, MutableDict

# pgvector 가져오기
try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False
    print("경고: pgvector 모듈이 설치되지 않았습니다. 'pip install pgvector'로 설치해주세요.")

from app.db.database import Base
from app.models.enums import QuestionType, DifficultyLevel, QuestionStatus

# Question-Tag 관계 테이블 정의
question_tags = Table(
    'question_tags',
    Base.metadata,
    Column('question_id', Integer, ForeignKey('questions.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True),
    Column('created_at', DateTime, default=datetime.utcnow)
)

class Subject(Base):
    """과목/주제 모델"""
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    
    # 관계 설정
    children = relationship("Subject", backref="parent", remote_side=[id])
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Tag(Base):
    """태그 모델"""
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

class Source(Base):
    """문제 출처 모델"""
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String(255), nullable=True)
    type = Column(String(50), nullable=True)  # 예: 교재, 시험, 강의자료
    year = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Question(Base):
    """최적화된 문제 모델 - 30개 컬럼에서 15개 컬럼으로 최적화"""
    __tablename__ = "questions"

    # 기본 식별자
    id = Column(Integer, primary_key=True, index=True)
    question_number = Column(Integer, nullable=False, index=True)
    question_type = Column(Enum(QuestionType), nullable=False, default=QuestionType.MULTIPLE_CHOICE)
    
    # 핵심 내용
    content = Column(Text, nullable=False)
    description = Column(ARRAY(String), nullable=True)  # 문제 설명/지문
    options = Column(JSONB, nullable=True)  # 선택지 {"1": "선택지1", "2": "선택지2"}
    correct_answer = Column(String(10), nullable=True)
    
    # 분류 정보 (통합)
    classification = Column(JSONB, nullable=True)  # {
    #     "subject": "간호학",
    #     "area": "기본간호", 
    #     "difficulty": "중",
    #     "year": 2024
    # }
    
    # 메타데이터 (통합)
    question_metadata = Column(JSONB, nullable=True)  # {
    #     "keywords": ["혈압", "측정"],
    #     "learning_objectives": ["혈압측정 방법 이해"],
    #     "estimated_time": 120,
    #     "points": 5.0
    # }
    
    # 상태 관리 (통합)
    status_info = Column(JSONB, nullable=True)  # {
    #     "approval_status": "approved",
    #     "approved_by": 123,
    #     "approved_at": "2024-01-01T00:00:00",
    #     "is_active": true,
    #     "last_modified_by": 456,
    #     "last_modified_at": "2024-01-01T00:00:00"
    # }
    
    # AI 및 RAG 통합 정보 (통합)
    ai_integration = Column(JSONB, nullable=True)  # {
    #     "ai_explanation": "상세 해설 내용",
    #     "explanation_confidence": 0.95,
    #     "vector_db_indexed": true,
    #     "rag_indexed": true,
    #     "llm_training_added": true,
    #     "integration_completed_at": "2024-01-01T00:00:00"
    # }
    
    # 파일 출처 정보 (통합)
    source_info = Column(JSONB, nullable=True)  # {
    #     "file_path": "uploads/exam_2024.pdf",
    #     "parsed_data_path": "data/parsed/exam_2024.json",
    #     "file_title": "2024년 기출문제",
    #     "file_category": "국가고시"
    # }
    
    # 임베딩 벡터 (최적화된 차원)
    if PGVECTOR_AVAILABLE:
        embedding = Column(Vector(768), nullable=True)  # 768차원으로 축소 (효율성 개선)
    
    # 기본 타임스탬프 (필수)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 관계 설정 (기존 호환성 유지)
    answer_options = relationship("AnswerOption", back_populates="question", cascade="all, delete-orphan")
    correct_answers = relationship("CorrectAnswer", back_populates="question", cascade="all, delete-orphan")
    explanations = relationship("Explanation", back_populates="question", cascade="all, delete-orphan")
    test_responses = relationship("TestResponse", back_populates="question", cascade="all, delete-orphan")

    
    def __repr__(self):
        return f"<Question(id={self.id}, number={self.question_number}, type={self.question_type})>"
    
    # 편의 메서드들 (기존 호환성)
    
    @property
    def subject(self):
        """과목명 반환"""
        return self.classification.get("subject") if self.classification else None
    
    @property
    def area_name(self):
        """영역명 반환"""
        return self.classification.get("area") if self.classification else None
    
    @property
    def difficulty(self):
        """난이도 반환"""
        return self.classification.get("difficulty") if self.classification else None
    
    @property
    def year(self):
        """연도 반환"""
        return self.classification.get("year") if self.classification else None
    
    @property
    def approval_status(self):
        """승인 상태 반환"""
        return self.status_info.get("approval_status", "pending") if self.status_info else "pending"
    
    @property
    def approved_by(self):
        """승인자 반환"""
        return self.status_info.get("approved_by") if self.status_info else None
    
    @property
    def approved_at(self):
        """승인 시간 반환"""
        return self.status_info.get("approved_at") if self.status_info else None
    
    @property
    def last_modified_by(self):
        """마지막 수정자 반환"""
        return self.status_info.get("last_modified_by") if self.status_info else None
    
    @property
    def last_modified_at(self):
        """마지막 수정 시간 반환"""
        return self.status_info.get("last_modified_at") if self.status_info else None
    
    @property
    def is_active(self):
        """활성화 상태 반환"""
        return self.status_info.get("is_active", True) if self.status_info else True
    
    @property
    def ai_explanation(self):
        """AI 해설 반환"""
        return self.ai_integration.get("ai_explanation") if self.ai_integration else None
    
    @property
    def explanation_confidence(self):
        """AI 해설 신뢰도 반환"""
        return self.ai_integration.get("explanation_confidence") if self.ai_integration else None
    
    @property
    def vector_db_indexed(self):
        """벡터 DB 인덱싱 여부 반환"""
        return self.ai_integration.get("vector_db_indexed", False) if self.ai_integration else False
    
    @property
    def rag_indexed(self):
        """RAG 인덱싱 여부 반환"""
        return self.ai_integration.get("rag_indexed", False) if self.ai_integration else False
    
    @property
    def llm_training_added(self):
        """LLM 학습 데이터 추가 여부 반환"""
        return self.ai_integration.get("llm_training_added", False) if self.ai_integration else False
    
    @property
    def source_file_path(self):
        """원본 파일 경로 반환"""
        return self.source_info.get("file_path") if self.source_info else None
    
    @property
    def parsed_data_path(self):
        """파싱된 데이터 경로 반환"""
        return self.source_info.get("parsed_data_path") if self.source_info else None
    
    @property
    def file_title(self):
        """파일 제목 반환"""
        return self.source_info.get("file_title") if self.source_info else None
    
    @property
    def file_category(self):
        """파일 카테고리 반환"""
        return self.source_info.get("file_category") if self.source_info else None
    
    # 설정 메서드들
    
    def set_classification(self, subject=None, area=None, difficulty=None, year=None):
        """분류 정보 설정"""
        if not self.classification:
            self.classification = {}
        
        if subject is not None:
            self.classification["subject"] = subject
        if area is not None:
            self.classification["area"] = area
        if difficulty is not None:
            self.classification["difficulty"] = difficulty
        if year is not None:
            self.classification["year"] = year
    
    def set_status_info(self, approval_status=None, approved_by=None, approved_at=None,
                       is_active=None, last_modified_by=None, last_modified_at=None):
        """상태 정보 설정"""
        if not self.status_info:
            self.status_info = {}
        
        if approval_status is not None:
            self.status_info["approval_status"] = approval_status
        if approved_by is not None:
            self.status_info["approved_by"] = approved_by
        if approved_at is not None:
            self.status_info["approved_at"] = approved_at
        if is_active is not None:
            self.status_info["is_active"] = is_active
        if last_modified_by is not None:
            self.status_info["last_modified_by"] = last_modified_by
        if last_modified_at is not None:
            self.status_info["last_modified_at"] = last_modified_at
    
    def set_ai_integration(self, ai_explanation=None, explanation_confidence=None,
                          vector_db_indexed=None, rag_indexed=None, llm_training_added=None,
                          integration_completed_at=None):
        """AI 통합 정보 설정"""
        if not self.ai_integration:
            self.ai_integration = {}
        
        if ai_explanation is not None:
            self.ai_integration["ai_explanation"] = ai_explanation
        if explanation_confidence is not None:
            self.ai_integration["explanation_confidence"] = explanation_confidence
        if vector_db_indexed is not None:
            self.ai_integration["vector_db_indexed"] = vector_db_indexed
        if rag_indexed is not None:
            self.ai_integration["rag_indexed"] = rag_indexed
        if llm_training_added is not None:
            self.ai_integration["llm_training_added"] = llm_training_added
        if integration_completed_at is not None:
            self.ai_integration["integration_completed_at"] = integration_completed_at
    
    def set_source_info(self, file_path=None, parsed_data_path=None, 
                       file_title=None, file_category=None):
        """파일 출처 정보 설정"""
        if not self.source_info:
            self.source_info = {}
        
        if file_path is not None:
            self.source_info["file_path"] = file_path
        if parsed_data_path is not None:
            self.source_info["parsed_data_path"] = parsed_data_path
        if file_title is not None:
            self.source_info["file_title"] = file_title
        if file_category is not None:
            self.source_info["file_category"] = file_category
    
    def set_metadata(self, keywords=None, learning_objectives=None, 
                    estimated_time=None, points=None):
        """메타데이터 설정"""
        if not self.question_metadata:
            self.question_metadata = {}
        
        if keywords is not None:
            self.question_metadata["keywords"] = keywords
        if learning_objectives is not None:
            self.question_metadata["learning_objectives"] = learning_objectives
        if estimated_time is not None:
            self.question_metadata["estimated_time"] = estimated_time
        if points is not None:
            self.question_metadata["points"] = points

# 나머지 모델들은 기존과 동일하게 유지하되 Question과의 관계만 유지

class AnswerOption(Base):
    """답변 선택지 모델 (객관식 문제용)"""
    __tablename__ = "answer_options"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    option_text = Column(Text, nullable=False)
    option_label = Column(String(10), nullable=True)  # 예: A, B, C, D, E
    display_order = Column(Integer, nullable=True)
    
    # 관계 설정
    question = relationship("Question", back_populates="answer_options")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CorrectAnswer(Base):
    """정답 모델"""
    __tablename__ = "correct_answers"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    answer_option_id = Column(Integer, ForeignKey("answer_options.id"), nullable=True)  # 객관식에 대한 참조
    answer_text = Column(Text, nullable=True)  # 주관식 답변 또는 O/X, 순서, 매칭 등에 대한 답변
    
    # 관계 설정
    question = relationship("Question", back_populates="correct_answers")
    answer_option = relationship("AnswerOption")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Explanation(Base):
    """문제 해설 모델"""
    __tablename__ = "explanations"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    content = Column(Text, nullable=False)
    
    # 관계 설정
    question = relationship("Question", back_populates="explanations")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# TestSet, TestQuestion, TestAttempt, UserAnswer 모델들도 기존과 동일하게 유지
# (공간상 생략하지만 실제로는 모두 포함)

class TestSet(Base):
    """테스트 세트 모델 (문제 묶음)"""
    __tablename__ = "test_sets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    time_limit_minutes = Column(Integer, nullable=True)  # 타임 리밋 (분 단위)
    is_random_order = Column(Boolean, default=False)
    is_published = Column(Boolean, default=False)
    
    # 메타데이터
    test_metadata = Column(JSONB, nullable=True)
    
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 설정
    subject = relationship("Subject")
    questions = relationship("TestQuestion", back_populates="test_set")
    attempts = relationship("TestAttempt", back_populates="test_set")
    created_by = relationship("User", foreign_keys=[created_by_id])

class TestQuestion(Base):
    """테스트 세트 내의 문제 항목 모델"""
    __tablename__ = "test_questions"

    id = Column(Integer, primary_key=True, index=True)
    test_set_id = Column(Integer, ForeignKey("test_sets.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    display_order = Column(Integer, nullable=True)
    points = Column(Float, default=1.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 설정
    test_set = relationship("TestSet", back_populates="questions")
    question = relationship("Question")
    
    # 테스트 내 질문 중복 방지
    __table_args__ = (
        UniqueConstraint('test_set_id', 'question_id', name='uq_test_question'),
    )

class TestAttempt(Base):
    """사용자 테스트 시도 모델"""
    __tablename__ = "test_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    test_set_id = Column(Integer, ForeignKey("test_sets.id"), nullable=False)
    
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    total_time_seconds = Column(Integer, nullable=True)
    
    score = Column(Float, nullable=True)
    max_score = Column(Float, nullable=True)
    correct_count = Column(Integer, nullable=True)
    question_count = Column(Integer, nullable=True)
    
    # 메타데이터 및 상태 저장
    status = Column(String(20), default="in_progress")  # in_progress, completed, abandoned
    attempt_metadata = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 설정
    user = relationship("User")
    test_set = relationship("TestSet", back_populates="attempts")
    answers = relationship("UserAnswer", back_populates="test_attempt", cascade="all, delete-orphan")

class UserAnswer(Base):
    """사용자 답변 모델"""
    __tablename__ = "user_answers"

    id = Column(Integer, primary_key=True, index=True)
    test_attempt_id = Column(Integer, ForeignKey("test_attempts.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    answer_option_id = Column(Integer, ForeignKey("answer_options.id"), nullable=True)
    answer_text = Column(Text, nullable=True)
    
    is_correct = Column(Boolean, nullable=True)
    points_earned = Column(Float, nullable=True)
    time_spent_seconds = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 설정
    test_attempt = relationship("TestAttempt", back_populates="answers")
    question = relationship("Question")
    answer_option = relationship("AnswerOption")