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
    current_level: float = Field(..., ge=0.0, le=1.0, description="현재 학습 수준")
    progress_trend: List[Dict[str, Any]] = Field(..., description="학습 진행 추세")
    subject_breakdown: Dict[str, float] = Field(..., description="과목별 성과")
    weekly_goals: Dict[str, Any] = Field(..., description="주간 목표")
    achievements_this_period: List[str] = Field(..., description="기간 내 성취")
    
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
    overall_metrics: Dict[str, float] = Field(..., description="전체 지표")
    strength_analysis: List[str] = Field(..., description="강점 분석")
    weakness_analysis: List[str] = Field(..., description="약점 분석")
    improvement_suggestions: List[str] = Field(..., description="개선 제안")
    comparative_analysis: Dict[str, Any] = Field(..., description="비교 분석")
    time_series_data: List[Dict[str, Any]] = Field(..., description="시계열 데이터")

class RecommendationItem(BaseModel):
    """추천 항목"""
    type: str = Field(..., description="추천 유형")
    title: str = Field(..., description="제목")
    description: str = Field(..., description="설명")
    priority: str = Field(..., description="우선순위")
    estimated_time: Optional[int] = Field(None, description="예상 소요 시간 (분)")
    difficulty: Optional[int] = Field(None, ge=1, le=5)
    
    class Config:
        from_attributes = True

class RecommendationResponse(BaseModel):
    """추천 응답"""
    personalized_items: List[RecommendationItem] = Field(..., description="개인 맞춤 추천")
    trending_topics: List[str] = Field(..., description="인기 주제")
    skill_gap_recommendations: List[RecommendationItem] = Field(..., description="스킬 갭 기반 추천")
    adaptive_path: Dict[str, Any] = Field(..., description="적응형 학습 경로")

class RecommendationSummaryResponse(BaseModel):
    """추천 요약 응답"""
    total_recommendations: int = Field(..., description="총 추천 수")
    high_priority_count: int = Field(..., description="고우선순위 추천 수")
    categories: Dict[str, int] = Field(..., description="카테고리별 추천 수")
    personalization_score: float = Field(..., ge=0.0, le=1.0, description="개인화 점수")
    last_updated: datetime = Field(..., description="마지막 업데이트 시간")
    
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
    
    class Config:
        from_attributes = True

class StudyPlanResponse(BaseModel):
    """학습 계획 응답"""
    plan_title: str = Field(..., description="계획 제목")
    total_duration_hours: float = Field(..., description="총 소요 시간")
    study_items: List[StudyPlanItem] = Field(..., description="학습 항목들")
    weekly_schedule: Dict[str, List[str]] = Field(..., description="주간 일정")
    milestones: List[Dict[str, Any]] = Field(..., description="마일스톤")

class WeeklyStudyPlanResponse(BaseModel):
    """주간 학습 계획 응답"""
    week_number: int = Field(..., description="주차")
    start_date: date = Field(..., description="시작 날짜")
    end_date: date = Field(..., description="종료 날짜")
    daily_plans: Dict[str, List[StudyPlanItem]] = Field(..., description="일별 학습 계획")
    total_weekly_hours: float = Field(..., description="주간 총 학습 시간")
    focus_areas: List[str] = Field(..., description="집중 영역")
    completion_rate: float = Field(..., ge=0.0, le=100.0, description="완료율")
    
    class Config:
        from_attributes = True

class LearningStreakResponse(BaseModel):
    """학습 연속 기록 응답"""
    current_streak: int = Field(..., description="현재 연속 기록 (일)")
    longest_streak: int = Field(..., description="최장 연속 기록 (일)")
    streak_calendar: Dict[str, bool] = Field(..., description="학습 달력")
    streak_milestones: List[Dict[str, Any]] = Field(..., description="연속 기록 마일스톤")
    motivation_message: str = Field(..., description="동기부여 메시지")

class AchievementResponse(BaseModel):
    """성취 응답"""
    achievement_id: str = Field(..., description="성취 ID")
    title: str = Field(..., description="성취 제목")
    description: str = Field(..., description="성취 설명")
    icon: str = Field(..., description="아이콘")
    earned_at: Optional[datetime] = Field(None, description="획득 시간")
    progress: float = Field(..., ge=0.0, le=1.0, description="진행도")
    category: str = Field(..., description="카테고리")
    rarity: str = Field(..., description="희귀도")

class QuickActionResponse(BaseModel):
    """빠른 액션 응답"""
    action_id: str = Field(..., description="액션 ID")
    title: str = Field(..., description="액션 제목")
    description: str = Field(..., description="액션 설명")
    icon: str = Field(..., description="아이콘")
    endpoint: str = Field(..., description="API 엔드포인트")
    estimated_time: int = Field(..., description="예상 소요 시간")
    priority: int = Field(..., ge=1, le=5, description="우선순위")

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