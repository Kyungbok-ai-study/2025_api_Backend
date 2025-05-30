"""
진단 테스트 관련 스키마
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class DiagnosisSubject(str, Enum):
    """진단 테스트 과목"""
    COMPUTER_SCIENCE = "computer_science"
    DATA_STRUCTURE = "data_structure"
    ALGORITHM = "algorithm"
    DATABASE = "database"
    PROGRAMMING = "programming"
    NETWORK = "network"

class Difficulty(str, Enum):
    """문제 난이도"""
    BEGINNER = "beginner"      # 1점
    EASY = "easy"              # 2점  
    MEDIUM = "medium"          # 3점
    HARD = "hard"              # 4점
    EXPERT = "expert"          # 5점

# Request 스키마
class DiagnosisTestCreate(BaseModel):
    """진단 테스트 생성 요청"""
    subject: DiagnosisSubject
    description: Optional[str] = Field(None, max_length=500)

class DiagnosisAnswerItem(BaseModel):
    """진단 테스트 답안 항목"""
    question_id: int = Field(..., gt=0)
    answer: str = Field(..., min_length=1, max_length=1000)
    time_spent: Optional[int] = Field(None, ge=0, description="풀이 시간 (초)")

class DiagnosisResultCreate(BaseModel):
    """진단 테스트 결과 제출"""
    test_session_id: int = Field(..., gt=0)
    answers: List[DiagnosisAnswerItem] = Field(..., min_items=1, max_items=50)
    total_time_spent: Optional[int] = Field(None, ge=0, description="총 소요 시간 (초)")

    @validator('answers')
    def validate_answers(cls, v):
        if len(v) != len(set(item.question_id for item in v)):
            raise ValueError('중복된 문제 ID가 있습니다')
        return v

# Response 스키마
class DiagnosisQuestionResponse(BaseModel):
    """진단 테스트 문제 응답"""
    id: int
    content: str
    choices: Optional[List[str]] = None
    question_type: str
    difficulty: str
    subject: str
    order_number: int

class DiagnosisTestResponse(BaseModel):
    """진단 테스트 세션 응답"""
    id: int
    user_id: int
    subject: str
    status: str  # "active", "completed", "expired"
    questions: List[DiagnosisQuestionResponse]
    created_at: datetime
    expires_at: Optional[datetime]
    max_time_minutes: Optional[int] = Field(None, description="제한 시간 (분)")

    class Config:
        from_attributes = True

class LearningLevelCalculation(BaseModel):
    """학습 수준 계산 세부사항"""
    total_score: float = Field(..., description="총 획득 점수")
    max_possible_score: float = Field(..., description="최대 가능 점수")
    learning_level: float = Field(..., ge=0.0, le=1.0, description="학습 수준 지표 (0.0-1.0)")
    difficulty_breakdown: Dict[str, Dict[str, Any]] = Field(..., description="난이도별 성과")
    subject_breakdown: Dict[str, Dict[str, Any]] = Field(..., description="과목별 성과")

class DiagnosisResultResponse(BaseModel):
    """진단 테스트 결과 응답"""
    test_session_id: int
    user_id: int
    learning_level: float = Field(..., ge=0.0, le=1.0)
    total_questions: int
    correct_answers: int
    accuracy_rate: float = Field(..., ge=0.0, le=1.0)
    calculation_details: LearningLevelCalculation
    feedback_message: str
    recommended_next_steps: List[str]
    completed_at: datetime

    class Config:
        from_attributes = True

class LearningLevelResponse(BaseModel):
    """학습 수준 지표 응답"""
    current_level: float = Field(..., ge=0.0, le=1.0, description="현재 학습 수준")
    previous_level: Optional[float] = Field(None, ge=0.0, le=1.0, description="이전 진단 수준")
    improvement: Optional[float] = Field(None, description="향상도")
    percentile_rank: Optional[float] = Field(None, ge=0.0, le=100.0, description="백분위 순위")
    strengths: List[str] = Field(default_factory=list, description="강점 영역")
    weaknesses: List[str] = Field(default_factory=list, description="약점 영역")
    recommendations: List[str] = Field(default_factory=list, description="학습 추천사항")
    last_updated: datetime

    class Config:
        from_attributes = True 