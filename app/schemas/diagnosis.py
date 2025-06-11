"""
진단 테스트 관련 스키마
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
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
    PHYSICAL_THERAPY = "physical_therapy"  # 물리치료학과 추가

class Difficulty(str, Enum):
    """문제 난이도"""
    BEGINNER = "beginner"      # 1점
    EASY = "easy"              # 2점  
    MEDIUM = "medium"          # 3점
    HARD = "hard"              # 4점
    EXPERT = "expert"          # 5점

class ConfidenceLevel(str, Enum):
    """확신도 수준"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

# Request 스키마
class DiagnosisTestCreate(BaseModel):
    """진단 테스트 생성 요청"""
    subject: DiagnosisSubject
    description: Optional[str] = Field(None, max_length=500)
    max_time_minutes: Optional[int] = 60

class DiagnosisAnswerItem(BaseModel):
    """진단 테스트 답안 항목"""
    question_id: int = Field(..., gt=0)
    answer: str = Field(..., min_length=1, max_length=1000)
    time_spent: Optional[int] = Field(None, ge=0, description="풀이 시간 (초)")
    confidence_level: Optional[int] = None

class QuestionItem(BaseModel):
    """문제 정보"""
    id: int
    content: str
    question_type: str
    difficulty: Optional[str] = None
    choices: Optional[List[str]] = None
    correct_answer: Optional[str] = None

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
    questions: List[QuestionItem]
    created_at: datetime
    expires_at: Optional[datetime]
    max_time_minutes: int

    class Config:
        from_attributes = True

class LearningLevelCalculation(BaseModel):
    """학습 수준 계산 세부사항"""
    total_score: float = Field(..., description="총 획득 점수")
    max_possible_score: float = Field(..., description="최대 가능 점수")
    learning_level: float = Field(..., ge=0.0, le=1.0, description="학습 수준 지표 (0.0-1.0)")
    difficulty_breakdown: Dict[str, Dict[str, Any]] = Field(..., description="난이도별 성과")
    subject_breakdown: Dict[str, Dict[str, Any]] = Field(..., description="과목별 성과")
    calculation_formula: str

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

# 새로운 스키마들 - 1문제 30선택지 형태
class MultiChoiceTestCreate(BaseModel):
    """다중 선택지 테스트 생성 요청"""
    subject: DiagnosisSubject
    question_content: str
    choices: List[str] = Field(..., min_items=30, max_items=30, description="정확히 30개의 선택지")
    correct_choice_index: int = Field(..., ge=0, le=29, description="정답 선택지 인덱스 (0-29)")
    max_time_minutes: Optional[int] = 60
    shuffle_choices: Optional[bool] = True
    description: Optional[str] = None

    @validator('choices')
    def validate_choices_count(cls, v):
        if len(v) != 30:
            raise ValueError('정확히 30개의 선택지가 필요합니다')
        return v

    @validator('correct_choice_index')
    def validate_correct_index(cls, v, values):
        if 'choices' in values and v >= len(values['choices']):
            raise ValueError('정답 인덱스가 선택지 범위를 벗어났습니다')
        return v

class MultiChoiceAnswerSubmit(BaseModel):
    """다중 선택지 답안 제출"""
    test_session_id: int
    selected_choice_index: int = Field(..., ge=0, le=29, description="선택한 선택지 인덱스")
    selected_choice_content: str
    eliminated_choices: Optional[List[int]] = Field(default=[], description="제거한 선택지 인덱스 목록")
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    time_spent_seconds: int = Field(..., gt=0, description="소요 시간 (초)")
    choice_timeline: Optional[List[Dict[str, Any]]] = Field(default=[], description="선택 과정 타임라인")

    @validator('eliminated_choices')
    def validate_eliminated_choices(cls, v):
        if v and any(choice < 0 or choice > 29 for choice in v):
            raise ValueError('제거된 선택지 인덱스가 유효하지 않습니다 (0-29 범위)')
        return v

class MultiChoiceTestSession(BaseModel):
    """다중 선택지 테스트 세션 정보"""
    id: int
    test_session_id: int
    question: QuestionItem
    choices: List[str]
    correct_choice_index: int
    max_choices: int
    shuffle_choices: bool
    created_at: datetime

    class Config:
        from_attributes = True

class MultiChoiceTestResponse(BaseModel):
    """다중 선택지 테스트 응답"""
    test_session_id: int
    user_id: int
    question: QuestionItem
    choices: List[str]
    max_time_minutes: int
    expires_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ChoiceStrategyAnalysis(BaseModel):
    """선택 전략 분석"""
    elimination_count: int = Field(description="제거한 선택지 수")
    elimination_effectiveness: float = Field(ge=0, le=1, description="제거 효과성 (0.0-1.0)")
    choice_changes: int = Field(description="선택 변경 횟수")
    decision_pattern: str = Field(description="의사결정 패턴")
    cognitive_load_score: float = Field(ge=0, le=1, description="인지 부하 점수")
    strategy_type: str = Field(description="전략 유형 (systematic/random/intuitive)")

class MultiChoiceResultResponse(BaseModel):
    """다중 선택지 테스트 결과"""
    test_session_id: int
    user_id: int
    question_content: str
    selected_choice: str
    correct_choice: str
    is_correct: bool
    
    # 기본 정보
    time_spent_seconds: int
    confidence_level: ConfidenceLevel
    
    # 전략 분석
    strategy_analysis: ChoiceStrategyAnalysis
    
    # 학습 수준 분석
    learning_level: float = Field(ge=0, le=1, description="학습 수준 지표")
    cognitive_abilities: Dict[str, float] = Field(description="인지 능력 분석")
    decision_quality: float = Field(ge=0, le=1, description="의사결정 품질")
    
    # 피드백
    feedback_message: str
    recommended_skills: List[str]
    improvement_areas: List[str]
    
    completed_at: datetime

    class Config:
        from_attributes = True

class MultiChoiceHistoryResponse(BaseModel):
    """다중 선택지 테스트 이력"""
    test_sessions: List[MultiChoiceTestResponse]
    total_sessions: int
    average_performance: Dict[str, float]
    improvement_trend: Dict[str, Any]
    skill_development: Dict[str, List[float]]

    class Config:
        from_attributes = True

# 확장된 진단 결과 스키마
class EnhancedDiagnosisResult(BaseModel):
    """확장된 진단 결과 (다중 선택지 포함)"""
    # 기본 정보
    test_session_id: int
    user_id: int
    test_type: str = Field(description="테스트 유형 (traditional/multi_choice)")
    
    # 성과 지표
    learning_level: float
    accuracy_rate: float
    time_efficiency: float
    
    # 다중 선택지 전용 분석
    choice_strategy_score: Optional[float] = None
    elimination_effectiveness: Optional[float] = None
    decision_confidence_score: Optional[float] = None
    cognitive_load_analysis: Optional[Dict[str, Any]] = None
    
    # 비교 분석
    percentile_rank: Optional[float] = None
    peer_comparison: Optional[Dict[str, Any]] = None
    
    # 개별화된 피드백
    personalized_feedback: str
    skill_recommendations: List[str]
    next_level_goals: List[str]
    
    completed_at: datetime

    class Config:
        from_attributes = True 