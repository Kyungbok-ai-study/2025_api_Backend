"""
대시보드 관련 스키마
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum

class AnalysisType(str, Enum):
    """분석 유형"""
    COMPREHENSIVE = "comprehensive"
    STRENGTH = "strength"
    WEAKNESS = "weakness" 
    TREND = "trend"

class StudyPlanPriority(str, Enum):
    """학습 계획 우선순위"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

# Response 스키마
class LearningMetrics(BaseModel):
    """학습 지표"""
    current_level: float = Field(..., ge=0.0, le=1.0, description="현재 학습 수준")
    weekly_progress: float = Field(..., description="주간 진행률")
    problems_solved_today: int = Field(..., ge=0)
    problems_solved_this_week: int = Field(..., ge=0)
    accuracy_rate: float = Field(..., ge=0.0, le=1.0, description="정답률")
    study_streak_days: int = Field(..., ge=0, description="연속 학습 일수")

class RecentActivity(BaseModel):
    """최근 활동"""
    activity_type: str = Field(..., description="활동 유형")
    description: str = Field(..., description="활동 설명")
    timestamp: datetime
    result: Optional[Dict[str, Any]] = None

class StudentDashboardResponse(BaseModel):
    """학생 대시보드 메인 응답"""
    user_id: int
    user_name: str
    learning_metrics: LearningMetrics
    recent_activities: List[RecentActivity] = Field(..., max_items=10)
    recommended_problems_count: int = Field(..., ge=0)
    upcoming_goals: List[str] = Field(default_factory=list)
    last_updated: datetime

    class Config:
        from_attributes = True

class LearningTrendPoint(BaseModel):
    """학습 추세 포인트"""
    date: date
    learning_level: float = Field(..., ge=0.0, le=1.0)
    problems_solved: int = Field(..., ge=0)
    accuracy_rate: float = Field(..., ge=0.0, le=1.0)
    time_spent_minutes: int = Field(..., ge=0)

class SubjectProgress(BaseModel):
    """과목별 진행 상황"""
    subject: str
    current_level: float = Field(..., ge=0.0, le=1.0)
    target_level: Optional[float] = Field(None, ge=0.0, le=1.0)
    progress_percentage: float = Field(..., ge=0.0, le=100.0)
    problems_solved: int = Field(..., ge=0)
    last_activity: Optional[datetime] = None

class LearningProgressResponse(BaseModel):
    """학습 진행 상황 응답"""
    user_id: int
    period_days: int
    overall_progress: float = Field(..., ge=0.0, le=100.0, description="전체 진행률 (%)")
    learning_trend: List[LearningTrendPoint] = Field(..., description="학습 추세")
    subject_progress: List[SubjectProgress] = Field(..., description="과목별 진행 상황")
    
    # 목표 관련
    current_goal: Optional[Dict[str, Any]] = None
    goal_achievement_rate: Optional[float] = Field(None, ge=0.0, le=100.0)
    
    generated_at: datetime

    class Config:
        from_attributes = True

class StrengthWeaknessItem(BaseModel):
    """강점/약점 항목"""
    category: str = Field(..., description="분야/카테고리")
    score: float = Field(..., ge=0.0, le=1.0, description="점수")
    description: str = Field(..., description="설명")
    evidence: List[str] = Field(default_factory=list, description="근거")

class LearningPattern(BaseModel):
    """학습 패턴"""
    pattern_type: str = Field(..., description="패턴 유형")
    description: str = Field(..., description="패턴 설명")
    frequency: str = Field(..., description="빈도")
    impact: str = Field(..., description="영향도")
    recommendation: str = Field(..., description="개선 방안")

class PerformanceAnalyticsResponse(BaseModel):
    """성과 분석 응답"""
    user_id: int
    analysis_type: str
    
    # 강점/약점 분석
    strengths: List[StrengthWeaknessItem] = Field(default_factory=list)
    weaknesses: List[StrengthWeaknessItem] = Field(default_factory=list)
    
    # 학습 패턴
    learning_patterns: List[LearningPattern] = Field(default_factory=list)
    
    # 개선 추천사항
    improvement_recommendations: List[str] = Field(default_factory=list)
    
    # 비교 데이터 (동급생 대비)
    peer_comparison: Optional[Dict[str, Any]] = None
    
    generated_at: datetime

    class Config:
        from_attributes = True

class RecommendationItem(BaseModel):
    """추천 항목"""
    type: str = Field(..., description="추천 유형")
    title: str = Field(..., description="제목")
    description: str = Field(..., description="설명")
    priority: str = Field(..., description="우선순위")
    estimated_time: Optional[int] = Field(None, description="예상 소요 시간 (분)")
    difficulty: Optional[int] = Field(None, ge=1, le=5)

class RecommendationSummaryResponse(BaseModel):
    """추천 시스템 요약 응답"""
    user_id: int
    
    # 현재 추천 상태
    total_recommended_problems: int = Field(..., ge=0)
    new_recommendations: int = Field(..., ge=0)
    
    # 맞춤형 추천
    personalized_recommendations: List[RecommendationItem] = Field(..., max_items=20)
    
    # 학습 경로
    suggested_learning_path: List[str] = Field(default_factory=list)
    next_milestone: Optional[str] = None
    
    # AI 추천 정확도
    recommendation_accuracy: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    generated_at: datetime

    class Config:
        from_attributes = True

class StudyPlanItem(BaseModel):
    """학습 계획 항목"""
    id: str = Field(..., description="계획 ID")
    title: str = Field(..., description="학습 항목")
    description: str = Field(..., description="상세 설명")
    subject: str = Field(..., description="과목")
    priority: StudyPlanPriority
    estimated_duration: int = Field(..., gt=0, description="예상 소요 시간 (분)")
    difficulty: int = Field(..., ge=1, le=5)
    prerequisites: List[str] = Field(default_factory=list, description="사전 요구사항")
    learning_objectives: List[str] = Field(default_factory=list, description="학습 목표")
    recommended_day: int = Field(..., ge=1, le=7, description="추천 요일 (1=월요일)")

class WeeklyStudyPlanResponse(BaseModel):
    """주간 학습 계획 응답"""
    user_id: int
    week_start_date: date
    week_end_date: date
    
    # 학습 계획
    study_items: List[StudyPlanItem] = Field(..., description="학습 항목들")
    
    # 시간 배분
    total_estimated_time: int = Field(..., description="총 예상 시간 (분)")
    daily_time_distribution: Dict[str, int] = Field(..., description="일별 시간 배분")
    
    # 목표 설정
    weekly_goals: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)
    
    # 적응형 조정
    adaptations: List[str] = Field(default_factory=list, description="개인 맞춤 조정사항")
    
    generated_at: datetime

    class Config:
        from_attributes = True

class LearningGoal(BaseModel):
    """학습 목표"""
    target_level: float = Field(..., ge=0.0, le=1.0)
    target_date: datetime
    current_progress: float = Field(..., ge=0.0, le=100.0)
    milestones: List[Dict[str, Any]] = Field(default_factory=list)

class GoalUpdateResponse(BaseModel):
    """학습 목표 업데이트 응답"""
    message: str = Field(..., description="응답 메시지")
    goal: LearningGoal
    estimated_completion_date: datetime
    required_daily_effort: int = Field(..., description="일일 필요 학습량 (분)")
    success_probability: float = Field(..., ge=0.0, le=1.0, description="성공 확률")
    
    class Config:
        from_attributes = True 