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
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    VERY_HARD = "very_hard"


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
    questions = relationship("Question", back_populates="subject_rel")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Tag(Base):
    """태그 모델"""
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    
    # 관계 설정
    questions = relationship("Question", secondary=question_tags, back_populates="tags")
    
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
    
    # 관계 설정
    questions = relationship("Question", back_populates="source")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Question(Base):
    """문제 모델"""
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    question_type = Column(Enum(QuestionType), nullable=False)
    difficulty = Column(Enum(DifficultyLevel), nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    
    # 메타데이터
    question_metadata = Column(JSONB, nullable=True)
    
    # 이미지 URL 목록 (이미지가 포함된 문제의 경우)
    image_urls = Column(MutableList.as_mutable(ARRAY(String)), nullable=True)
    
    # 텍스트 임베딩 (pgvector)
    if PGVECTOR_AVAILABLE:
        embedding = Column(Vector(1536), nullable=True)  # OpenAI 1536 차원 임베딩
    
    # 진단 테스트 관련 필드
    is_active = Column(Boolean, default=True, nullable=False)  # 문제 활성화 상태
    subject_name = Column(String(100), nullable=True)  # 과목명 (진단용)
    choices = Column(ARRAY(String), nullable=True)  # 객관식 선택지 (간단 버전)
    correct_answer = Column(Text, nullable=True)  # 정답 (간단 버전)
    
    # 문자열 참조로 순환 import 방지
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # 질문 복제 정보 추적
    original_id = Column(Integer, ForeignKey("questions.id"), nullable=True)
    is_duplicate = Column(Boolean, default=False)
    duplicate_count = Column(Integer, default=0)
    
    # 통계
    usage_count = Column(Integer, default=0)
    correct_rate = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 설정
    subject_rel = relationship("Subject", back_populates="questions")
    source = relationship("Source", back_populates="questions")
    options = relationship("AnswerOption", back_populates="question", cascade="all, delete-orphan")
    correct_answers = relationship("CorrectAnswer", back_populates="question", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=question_tags, back_populates="questions")
    explanations = relationship("Explanation", back_populates="question", cascade="all, delete-orphan")
    
    # 진단 테스트 관련 관계
    test_responses = relationship("TestResponse", back_populates="question")
    
    # 문자열 참조로 User 관계 설정
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])


class AnswerOption(Base):
    """답변 선택지 모델 (객관식 문제용)"""
    __tablename__ = "answer_options"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    option_text = Column(Text, nullable=False)
    option_label = Column(String(10), nullable=True)  # 예: A, B, C, D, E
    display_order = Column(Integer, nullable=True)
    
    # 관계 설정
    question = relationship("Question", back_populates="options")
    
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