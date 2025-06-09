"""
문제 및 답변 데이터 모델

파싱된 문제, 답변, 정답, 유형 등을 저장하기 위한 SQLAlchemy 모델
pgvector 확장을 사용하여 텍스트 임베딩 저장 기능 포함
"""
import enum
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
# User import는 관계 설정에서 문자열로 처리하여 순환 import 방지

# Question-Tag 관계 테이블 정의
question_tags = Table(
    'question_tags',
    Base.metadata,
    Column('question_id', Integer, ForeignKey('questions.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True),
    Column('created_at', DateTime, default=datetime.utcnow)
)


class QuestionType(str, enum.Enum):
    """문제 유형 Enum"""
    MULTIPLE_CHOICE = "multiple_choice"  # 객관식
    SHORT_ANSWER = "short_answer"        # 주관식
    TRUE_FALSE = "true_false"            # O/X
    MATCHING = "matching"                # 짝 맞추기
    ORDERING = "ordering"                # 순서 맞추기
    FILL_IN_BLANK = "fill_in_blank"      # 빈칸 채우기
    ESSAY = "essay"                      # 서술형
    OTHER = "other"                      # 기타


class DifficultyLevel(str, enum.Enum):
    """문제 난이도 Enum"""
    LOW = "하"
    MEDIUM = "중"
    HIGH = "상"


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
    
    # 관계 설정 (Question과의 관계 제거됨)
    
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
    
    # 관계 설정 (Question과의 관계 제거됨)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Question(Base):
    """문제 모델 - 간소화된 스키마"""
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    question_number = Column(Integer, nullable=False)  # 문제 번호 (1~22)
    question_type = Column(Enum(QuestionType), nullable=False, default=QuestionType.MULTIPLE_CHOICE)  # 문제 유형
    content = Column(Text, nullable=False)  # 문제 내용
    description = Column(MutableList.as_mutable(ARRAY(String)), nullable=True)  # 문제 설명/지문 (리스트)
    options = Column(JSONB, nullable=True)  # 선택지 {"1": "선택지1", "2": "선택지2", ...}
    correct_answer = Column(String(10), nullable=True)  # 정답 (예: "3")
    subject = Column("subject_name", String(100), nullable=True)  # 과목명 (테이블의 subject_name 컬럼과 매핑)
    area_name = Column(String(100), nullable=True)  # 영역이름
    difficulty = Column(String(10), nullable=True)  # 난이도: 하, 중, 상 (직접 문자열 저장)
    year = Column(Integer, nullable=True)  # 연도
    
    # 승인 및 수정 이력 관리
    approval_status = Column(String(20), default="pending")  # pending, approved, rejected
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # 승인자 ID
    approved_at = Column(DateTime, nullable=True)  # 승인 시간
    last_modified_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # 마지막 수정자 ID (생성자 겸용)
    last_modified_at = Column(DateTime, nullable=True)  # 마지막 수정 시간
    is_active = Column(Boolean, nullable=False, default=True)  # 활성화 상태
    
    # AI 해설 및 RAG 통합 관련
    ai_explanation = Column(Text, nullable=True)  # AI가 생성한 상세 해설
    explanation_confidence = Column(Float, nullable=True)  # AI 해설 신뢰도 (0.0 ~ 1.0)
    vector_db_indexed = Column(Boolean, default=False)  # 벡터 DB 인덱싱 여부
    rag_indexed = Column(Boolean, default=False)  # RAG 시스템 인덱싱 여부
    llm_training_added = Column(Boolean, default=False)  # LLM 학습 데이터 추가 여부
    integration_completed_at = Column(DateTime, nullable=True)  # 통합 처리 완료 시간
    
    # 파일 출처 정보
    source_file_path = Column(String(500), nullable=True)  # 원본 파일 경로
    parsed_data_path = Column(String(500), nullable=True)  # 파싱된 JSON 파일 경로
    file_title = Column(String(200), nullable=True)  # 사용자가 입력한 파일 제목
    file_category = Column(String(100), nullable=True)  # 파일 카테고리
    
    # 임베딩 벡터 (pgvector 사용)
    if PGVECTOR_AVAILABLE:
        embedding = Column(Vector(1536), nullable=True)  # OpenAI ada-002 임베딩 차원
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 설정 (레거시 호환성을 위해 유지)
    answer_options = relationship("AnswerOption", back_populates="question", cascade="all, delete-orphan")
    correct_answers = relationship("CorrectAnswer", back_populates="question", cascade="all, delete-orphan")
    explanations = relationship("Explanation", back_populates="question", cascade="all, delete-orphan")
    
    # 진단 테스트 관계 설정
    test_responses = relationship("TestResponse", back_populates="question", cascade="all, delete-orphan")


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
        UniqueConstraint("test_set_id", "question_id", name="uq_test_question"),
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


# 임베딩 생성 및 저장을 위한 함수 정의
def create_embedding(text: str, model: str = "text-embedding-ada-002") -> List[float]:
    """
    텍스트에 대한 임베딩 생성
    
    Args:
        text (str): 임베딩할 텍스트
        model (str): 사용할 OpenAI 임베딩 모델
        
    Returns:
        List[float]: 임베딩 벡터
    """
    try:
        # OpenAI 클라이언트 가져오기
        import openai
        from openai import OpenAI
        
        client = OpenAI()
        
        # OpenAI API를 호출하여 임베딩 생성
        response = client.embeddings.create(
            model=model,
            input=text
        )
        
        # 임베딩 벡터 반환
        return response.data[0].embedding
    
    except ImportError:
        print("경고: OpenAI 모듈이 설치되지 않았습니다. 'pip install openai'로 설치해주세요.")
        return []
    except Exception as e:
        print(f"임베딩 생성 오류: {str(e)}")
        return [] 