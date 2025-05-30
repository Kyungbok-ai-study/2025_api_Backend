"""
교수 대시보드 스키마
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Optional, Any

class ProfessorDashboardResponse(BaseModel):
    """교수 대시보드 응답"""
    professor_name: str
    total_classes: int
    total_students: int
    recent_activities: List[Dict[str, Any]]
    performance_summary: Dict[str, Any]
    pending_tasks: List[str]
    
class ClassAnalyticsResponse(BaseModel):
    """수업 분석 응답"""
    class_id: int
    class_name: str
    student_count: int
    average_performance: float
    completion_rate: float
    difficulty_distribution: Dict[str, int]
    recent_submissions: int
    
class StudentProgressSummary(BaseModel):
    """학생 진도 요약"""
    student_id: int
    student_name: str
    learning_level: float
    completion_percentage: float
    last_activity: datetime
    risk_level: str  # low, medium, high
    
class AssignmentResponse(BaseModel):
    """과제 응답"""
    assignment_id: int
    title: str
    description: str
    due_date: datetime
    difficulty_level: int
    created_at: datetime
    
class ClassPerformanceResponse(BaseModel):
    """수업 성과 응답"""
    class_id: int
    performance_metrics: Dict[str, float]
    student_distribution: Dict[str, int]
    improvement_trends: Dict[str, Any]
    recommendations: List[str]
    
class LearningInsightsResponse(BaseModel):
    """학습 인사이트 응답"""
    insights: List[Dict[str, Any]]
    trend_analysis: Dict[str, Any]
    predictions: Dict[str, Any]
    actionable_recommendations: List[str] 