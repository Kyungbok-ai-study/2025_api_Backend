"""
학생 대시보드 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.db.database import get_db
from app.auth.dependencies import get_current_user, get_current_student
from app.models.user import User
from app.schemas.dashboard import (
    StudentDashboardResponse, LearningProgressResponse, 
    StudyPlanResponse, RecommendationResponse,
    PerformanceAnalyticsResponse, LearningStreakResponse,
    AchievementResponse, QuickActionResponse
)
from app.services.dashboard_service import DashboardService

router = APIRouter()
dashboard_service = DashboardService()

@router.get("/overview", response_model=StudentDashboardResponse)
async def get_student_dashboard_overview(
    current_user: User = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """학생 대시보드 전체 개요"""
    try:
        return await dashboard_service.get_student_dashboard(
            db=db, 
            user_id=current_user.id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"대시보드 조회 실패: {str(e)}")

@router.get("/progress", response_model=LearningProgressResponse)
async def get_learning_progress(
    period_days: int = Query(30, description="조회 기간 (일)"),
    current_user: User = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """학습 진척도 상세 조회"""
    try:
        return await dashboard_service.get_learning_progress(
            db=db,
            user_id=current_user.id,
            period_days=period_days
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"학습 진척도 조회 실패: {str(e)}")

@router.get("/study-plan", response_model=StudyPlanResponse)
async def get_study_plan(
    current_user: User = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """개인 맞춤 학습 계획"""
    try:
        return await dashboard_service.get_personalized_study_plan(
            db=db,
            user_id=current_user.id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"학습 계획 조회 실패: {str(e)}")

@router.get("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    limit: int = Query(10, description="추천 항목 수"),
    current_user: User = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """맞춤형 학습 추천"""
    try:
        return await dashboard_service.get_learning_recommendations(
            db=db,
            user_id=current_user.id,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"추천 조회 실패: {str(e)}")

@router.get("/analytics", response_model=PerformanceAnalyticsResponse)
async def get_performance_analytics(
    period_days: int = Query(90, description="분석 기간 (일)"),
    current_user: User = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """성과 분석 (상세 통계)"""
    try:
        return await dashboard_service.get_performance_analytics(
            db=db,
            user_id=current_user.id,
            period_days=period_days
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"성과 분석 실패: {str(e)}")

@router.get("/streak", response_model=LearningStreakResponse)
async def get_learning_streak(
    current_user: User = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """학습 연속 기록"""
    try:
        return await dashboard_service.get_learning_streak(
            db=db,
            user_id=current_user.id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"학습 기록 조회 실패: {str(e)}")

@router.get("/achievements", response_model=List[AchievementResponse])
async def get_achievements(
    current_user: User = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """성취 및 배지"""
    try:
        return await dashboard_service.get_user_achievements(
            db=db,
            user_id=current_user.id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"성취 조회 실패: {str(e)}")

@router.get("/quick-actions", response_model=List[QuickActionResponse])
async def get_quick_actions(
    current_user: User = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """빠른 실행 액션들"""
    try:
        return await dashboard_service.get_quick_actions(
            db=db,
            user_id=current_user.id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"빠른 액션 조회 실패: {str(e)}")

@router.post("/goal/set")
async def set_learning_goal(
    goal_type: str,
    target_value: float,
    target_date: datetime,
    current_user: User = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """학습 목표 설정"""
    try:
        return await dashboard_service.set_learning_goal(
            db=db,
            user_id=current_user.id,
            goal_type=goal_type,
            target_value=target_value,
            target_date=target_date
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"목표 설정 실패: {str(e)}")

@router.get("/weekly-summary")
async def get_weekly_summary(
    current_user: User = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """주간 학습 요약"""
    try:
        return await dashboard_service.get_weekly_summary(
            db=db,
            user_id=current_user.id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"주간 요약 조회 실패: {str(e)}") 