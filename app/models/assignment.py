"""
과제 관리 관련 데이터베이스 모델
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Float, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.db.database import Base

class AssignmentStatus(enum.Enum):
    """과제 상태"""
    DRAFT = "draft"          # 초안
    PUBLISHED = "published"  # 게시됨
    CLOSED = "closed"        # 마감됨
    GRADED = "graded"        # 채점완료

class AssignmentType(enum.Enum):
    """과제 유형"""
    HOMEWORK = "homework"    # 숙제
    PROJECT = "project"      # 프로젝트
    QUIZ = "quiz"           # 퀴즈
    EXAM = "exam"           # 시험

class Assignment(Base):
    """과제 모델"""
    __tablename__ = "assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # 과제 설정
    assignment_type = Column(Enum(AssignmentType), nullable=False, default=AssignmentType.HOMEWORK)
    status = Column(Enum(AssignmentStatus), nullable=False, default=AssignmentStatus.DRAFT)
    
    # 교수 정보
    professor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    professor_school = Column(String(100), nullable=False)
    professor_department = Column(String(100), nullable=False)
    
    # 과목 정보
    subject_name = Column(String(100), nullable=False)
    
    # 시간 설정
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    published_at = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    
    # 점수 설정
    max_score = Column(Float, default=100.0, nullable=False)
    
    # 추가 설정
    allow_late_submission = Column(Boolean, default=False, nullable=False)
    instructions = Column(Text, nullable=True)
    attachment_urls = Column(JSON, nullable=True)  # 첨부파일 URL 목록
    
    # 관계 설정
    professor = relationship("User", foreign_keys=[professor_id])
    submissions = relationship("AssignmentSubmission", back_populates="assignment", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Assignment(id={self.id}, title={self.title}, professor_id={self.professor_id})>"

class AssignmentSubmission(Base):
    """과제 제출 모델"""
    __tablename__ = "assignment_submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 제출 내용
    submission_text = Column(Text, nullable=True)
    attachment_urls = Column(JSON, nullable=True)  # 제출 첨부파일 URL 목록
    
    # 제출 시간
    submitted_at = Column(DateTime, server_default=func.now(), nullable=False)
    is_late = Column(Boolean, default=False, nullable=False)
    
    # 채점 정보
    score = Column(Float, nullable=True)
    feedback = Column(Text, nullable=True)
    graded_at = Column(DateTime, nullable=True)
    graded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # 관계 설정
    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("User", foreign_keys=[student_id])
    grader = relationship("User", foreign_keys=[graded_by])
    
    def __repr__(self):
        return f"<AssignmentSubmission(id={self.id}, assignment_id={self.assignment_id}, student_id={self.student_id})>"

class ProblemBank(Base):
    """문제 은행 모델"""
    __tablename__ = "problem_bank"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    
    # 문제 유형
    problem_type = Column(String(50), nullable=False)  # 'multiple_choice', 'short_answer', 'essay', etc.
    subject = Column(String(100), nullable=False)
    difficulty = Column(Integer, default=1, nullable=False)  # 1(쉬움) ~ 5(어려움)
    
    # 정답 정보
    correct_answer = Column(Text, nullable=True)
    choices = Column(JSON, nullable=True)  # 객관식 선택지
    explanation = Column(Text, nullable=True)
    
    # 작성자 정보
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    school = Column(String(100), nullable=False)
    department = Column(String(100), nullable=False)
    
    # 시간 정보
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 사용 통계
    usage_count = Column(Integer, default=0, nullable=False)
    
    # 관계 설정
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<ProblemBank(id={self.id}, title={self.title}, created_by={self.created_by})>" 