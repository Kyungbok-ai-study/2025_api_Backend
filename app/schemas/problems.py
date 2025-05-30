"""
문제 추천 및 AI 생성 관련 스키마
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

class ProblemType(str, Enum):
    """문제 유형"""
    MULTIPLE_CHOICE = "multiple_choice"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    CODE = "code"
    TRUE_FALSE = "true_false"

class ProblemSource(str, Enum):
    """문제 출처"""
    DATABASE = "database"           # 기존 문제 DB
    AI_GENERATED = "ai_generated"   # AI 생성 문제
    PDF_EXTRACTED = "pdf_extracted" # PDF 추출 문제

# Request 스키마
class ProblemRecommendationRequest(BaseModel):
    """문제 추천 요청"""
    subject: Optional[str] = None
    difficulty_range: Optional[List[int]] = Field(None, min_items=2, max_items=2, description="난이도 범위 [최소, 최대]")
    problem_types: Optional[List[ProblemType]] = Field(None, description="문제 유형 필터")
    exclude_solved: bool = Field(True, description="이미 푼 문제 제외")
    limit: int = Field(10, ge=1, le=50, description="추천 문제 개수")

    @validator('difficulty_range')
    def validate_difficulty_range(cls, v):
        if v and (v[0] < 1 or v[1] > 5 or v[0] > v[1]):
            raise ValueError('난이도 범위는 1-5 사이의 값으로 [최소, 최대] 형태여야 합니다')
        return v

class AIGeneratedProblemRequest(BaseModel):
    """AI 문제 생성 요청"""
    subject: str = Field(..., min_length=1, max_length=100)
    difficulty: int = Field(..., ge=1, le=5, description="난이도 (1-5)")
    problem_type: ProblemType
    context: Optional[str] = Field(None, max_length=2000, description="문제 생성 컨텍스트")
    keywords: Optional[List[str]] = Field(None, max_items=10, description="키워드")
    reference_materials: Optional[List[str]] = Field(None, description="참조 자료")

class ProblemSubmissionRequest(BaseModel):
    """문제 답안 제출 요청"""
    problem_id: int = Field(..., gt=0)
    answer: Union[str, List[str]] = Field(..., description="답안 (단답형: 문자열, 다답형: 문자열 리스트)")
    time_spent: Optional[int] = Field(None, ge=0, description="풀이 시간 (초)")
    confidence_level: Optional[int] = Field(None, ge=1, le=5, description="확신도 (1-5)")

# Response 스키마
class ProblemResponse(BaseModel):
    """문제 응답"""
    id: int
    title: str
    content: str
    choices: Optional[List[str]] = None
    problem_type: str
    difficulty: int
    subject: str
    source: str
    estimated_time: Optional[int] = Field(None, description="예상 풀이 시간 (분)")
    tags: Optional[List[str]] = Field(default_factory=list)
    hints: Optional[List[str]] = Field(default_factory=list)
    created_at: datetime
    vector_embedding: Optional[List[float]] = Field(None, exclude=True, description="벡터 임베딩 (API 응답에서 제외)")

    class Config:
        from_attributes = True

class AIGeneratedProblemResponse(BaseModel):
    """AI 생성 문제 응답"""
    problem: ProblemResponse
    generation_info: Dict[str, Any] = Field(..., description="생성 정보")
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="품질 점수")
    reviewed: bool = Field(False, description="교수 검토 여부")
    generated_at: datetime

    class Config:
        from_attributes = True

class ProblemSubmissionResponse(BaseModel):
    """문제 답안 제출 응답"""
    submission_id: int
    problem_id: int
    user_id: int
    is_correct: bool
    score: float = Field(..., ge=0.0, le=1.0, description="점수 (0.0-1.0)")
    correct_answer: Union[str, List[str]]
    explanation: Optional[str] = None
    feedback: Optional[str] = None
    time_spent: Optional[int] = None
    submitted_at: datetime
    
    # 학습 수준 업데이트 정보
    previous_level: Optional[float] = Field(None, description="이전 학습 수준")
    new_level: Optional[float] = Field(None, description="새로운 학습 수준")
    level_change: Optional[float] = Field(None, description="수준 변화량")

    class Config:
        from_attributes = True

class ProblemStatisticsResponse(BaseModel):
    """문제 풀이 통계 응답"""
    user_id: int
    period_days: int
    
    # 전체 통계
    total_problems_solved: int
    total_time_spent: int = Field(..., description="총 소요 시간 (분)")
    overall_accuracy: float = Field(..., ge=0.0, le=1.0)
    
    # 과목별 통계
    subject_stats: Dict[str, Dict[str, Any]] = Field(..., description="과목별 통계")
    
    # 난이도별 통계  
    difficulty_stats: Dict[str, Dict[str, Any]] = Field(..., description="난이도별 통계")
    
    # 시간별 성과 (학습 곡선)
    daily_performance: List[Dict[str, Any]] = Field(..., description="일별 성과")
    
    # 개선 영역
    improvement_areas: List[str] = Field(default_factory=list)
    
    # 성취 내역
    achievements: List[Dict[str, Any]] = Field(default_factory=list)
    
    generated_at: datetime

    class Config:
        from_attributes = True

class RecommendationMetrics(BaseModel):
    """추천 시스템 메트릭"""
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="관련성 점수")
    difficulty_match: float = Field(..., ge=0.0, le=1.0, description="난이도 적합도")
    learning_path_alignment: float = Field(..., ge=0.0, le=1.0, description="학습 경로 적합도")
    novelty_score: float = Field(..., ge=0.0, le=1.0, description="새로움 점수")

class ProblemRecommendationResponse(BaseModel):
    """문제 추천 응답 (메트릭 포함)"""
    problems: List[ProblemResponse]
    recommendation_metrics: RecommendationMetrics
    total_available: int = Field(..., description="사용 가능한 전체 문제 수")
    recommendation_reason: str = Field(..., description="추천 이유")
    generated_at: datetime

    class Config:
        from_attributes = True 