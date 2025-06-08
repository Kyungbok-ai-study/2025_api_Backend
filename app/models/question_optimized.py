"""
최적화된 Question 모델 - 30개 컬럼을 15-20개로 최적화
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Float, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.ext.mutable import MutableList, MutableDict
from datetime import datetime
import enum

# pgvector 지원 확인
try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False

from app.db.database import Base

class QuestionType(enum.Enum):
    """문제 유형"""
    MULTIPLE_CHOICE = "multiple_choice"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    TRUE_FALSE = "true_false"
    FILL_BLANK = "fill_blank"

class QuestionStatus(enum.Enum):
    """문제 상태"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"

class QuestionOptimized(Base):
    """최적화된 문제 모델 - 컬럼 수 50% 감소"""
    __tablename__ = "questions_optimized"

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
    classification = Column(JSONB, nullable=True)  # {"subject": "간호학", "area": "기본간호", "difficulty": "중"}
    
    # 메타데이터 (통합)
    question_metadata = Column(JSONB, nullable=True)  # {
    #     "year": 2024,
    #     "source": "기출문제",
    #     "keywords": ["혈압", "측정"],
    #     "learning_objectives": ["혈압측정 방법 이해"]
    # }
    
    # 상태 관리 (통합)
    status_info = Column(JSONB, nullable=True)  # {
    #     "approval_status": "approved",
    #     "approved_by": 123,
    #     "approved_at": "2024-01-01T00:00:00",
    #     "is_active": true
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
    
    # 마지막 수정 정보 (통합)
    modification_info = Column(JSONB, nullable=True)  # {
    #     "last_modified_by": 456,
    #     "last_modified_at": "2024-01-01T00:00:00",
    #     "modification_history": [...]
    # }
    
    # 임베딩 벡터 (필요시)
    if PGVECTOR_AVAILABLE:
        embedding = Column(Vector(768), nullable=True)  # 768차원으로 축소 (OpenAI 최신 모델)
    
    # 기본 타임스탬프 (필수)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 관계 설정 (기존 호환성 유지)
    answer_options = relationship("AnswerOption", back_populates="question", cascade="all, delete-orphan")
    correct_answers = relationship("CorrectAnswer", back_populates="question", cascade="all, delete-orphan")
    explanations = relationship("Explanation", back_populates="question", cascade="all, delete-orphan")
    test_responses = relationship("TestResponse", back_populates="question", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<QuestionOptimized(id={self.id}, number={self.question_number}, type={self.question_type})>"
    
    # 편의 메서드들
    
    @property
    def subject(self):
        """과목명 반환"""
        return self.classification.get("subject") if self.classification else None
    
    @property
    def difficulty(self):
        """난이도 반환"""
        return self.classification.get("difficulty") if self.classification else None
    
    @property
    def approval_status(self):
        """승인 상태 반환"""
        return self.status_info.get("approval_status", "pending") if self.status_info else "pending"
    
    @property
    def is_active(self):
        """활성화 상태 반환"""
        return self.status_info.get("is_active", True) if self.status_info else True
    
    @property
    def ai_explanation(self):
        """AI 해설 반환"""
        return self.ai_integration.get("ai_explanation") if self.ai_integration else None
    
    @property
    def is_rag_ready(self):
        """RAG 준비 상태 확인"""
        if not self.ai_integration:
            return False
        return (
            self.ai_integration.get("vector_db_indexed", False) and
            self.ai_integration.get("rag_indexed", False)
        )
    
    def set_classification(self, subject=None, area=None, difficulty=None):
        """분류 정보 설정"""
        if not self.classification:
            self.classification = {}
        
        if subject:
            self.classification["subject"] = subject
        if area:
            self.classification["area"] = area
        if difficulty:
            self.classification["difficulty"] = difficulty
    
    def set_ai_integration_status(self, **kwargs):
        """AI 통합 상태 업데이트"""
        if not self.ai_integration:
            self.ai_integration = {}
        
        for key, value in kwargs.items():
            self.ai_integration[key] = value
    
    def set_approval_status(self, status, approved_by=None):
        """승인 상태 설정"""
        if not self.status_info:
            self.status_info = {}
        
        self.status_info["approval_status"] = status
        if approved_by:
            self.status_info["approved_by"] = approved_by
            self.status_info["approved_at"] = datetime.utcnow().isoformat()

# 마이그레이션 도우미 함수
def migrate_from_old_question(old_question):
    """기존 Question 모델에서 새로운 최적화 모델로 데이터 이전"""
    
    new_question = QuestionOptimized(
        id=old_question.id,
        question_number=old_question.question_number,
        question_type=old_question.question_type,
        content=old_question.content,
        description=old_question.description,
        options=old_question.options,
        correct_answer=old_question.correct_answer,
        created_at=old_question.created_at,
        updated_at=old_question.updated_at
    )
    
    # 분류 정보 통합
    new_question.classification = {
        "subject": getattr(old_question, 'subject', None),
        "area": getattr(old_question, 'area_name', None),
        "difficulty": getattr(old_question, 'difficulty', None)
    }
    
    # 메타데이터 통합
    new_question.question_metadata = {
        "year": getattr(old_question, 'year', None),
        "source": "migrated_data"
    }
    
    # 상태 정보 통합
    new_question.status_info = {
        "approval_status": getattr(old_question, 'approval_status', 'pending'),
        "approved_by": getattr(old_question, 'approved_by', None),
        "approved_at": getattr(old_question, 'approved_at', None),
        "is_active": getattr(old_question, 'is_active', True)
    }
    
    # AI 통합 정보 통합
    new_question.ai_integration = {
        "ai_explanation": getattr(old_question, 'ai_explanation', None),
        "explanation_confidence": getattr(old_question, 'explanation_confidence', None),
        "vector_db_indexed": getattr(old_question, 'vector_db_indexed', False),
        "rag_indexed": getattr(old_question, 'rag_indexed', False),
        "llm_training_added": getattr(old_question, 'llm_training_added', False),
        "integration_completed_at": getattr(old_question, 'integration_completed_at', None)
    }
    
    # 소스 정보 통합
    new_question.source_info = {
        "file_path": getattr(old_question, 'source_file_path', None),
        "parsed_data_path": getattr(old_question, 'parsed_data_path', None),
        "file_title": getattr(old_question, 'file_title', None),
        "file_category": getattr(old_question, 'file_category', None)
    }
    
    # 수정 정보 통합
    new_question.modification_info = {
        "last_modified_by": getattr(old_question, 'last_modified_by', None),
        "last_modified_at": getattr(old_question, 'last_modified_at', None)
    }
    
    # 임베딩 복사
    if PGVECTOR_AVAILABLE and hasattr(old_question, 'embedding'):
        new_question.embedding = old_question.embedding
    
    return new_question 