"""
대시보드 관련 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.db.database import get_db
from app.schemas.dashboard import (
    StudentDashboardResponse,
    LearningProgressResponse,
    PerformanceAnalyticsResponse,
    RecommendationSummaryResponse,
    WeeklyStudyPlanResponse,
    GoalUpdateResponse
)
from app.services.dashboard_service import dashboard_service
from app.auth.dependencies import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("/student", response_model=StudentDashboardResponse)
async def get_student_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    학생 대시보드 메인 데이터
    - 학습 수준 지표
    - 최근 활동 요약
    - 추천 문제 현황
    """
    try:
        dashboard_data = await dashboard_service.get_student_dashboard(
            db=db,
            user_id=current_user.id
        )
        return dashboard_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"대시보드 조회 실패: {str(e)}"
        )

@router.get("/progress", response_model=LearningProgressResponse)
async def get_learning_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    period_days: int = Query(30, ge=7, le=365, description="조회 기간 (일)")
):
    """
    학습 진행 상황 조회
    - 시간별 학습 수준 변화
    - 과목별 성취도
    - 목표 대비 진행률
    """
    try:
        progress_data = await dashboard_service.get_learning_progress(
            db=db,
            user_id=current_user.id,
            period_days=period_days
        )
        return progress_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"학습 진행 상황 조회 실패: {str(e)}"
        )

@router.get("/analytics", response_model=PerformanceAnalyticsResponse)
async def get_performance_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    analysis_type: str = Query("comprehensive", regex="^(comprehensive|strength|weakness|trend)$")
):
    """
    성과 분석 데이터
    - 강점/약점 분석
    - 학습 패턴 분석
    - 개선 추천사항
    """
    try:
        analytics_data = await dashboard_service.get_performance_analytics(
            db=db,
            user_id=current_user.id,
            analysis_type=analysis_type
        )
        return analytics_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"성과 분석 조회 실패: {str(e)}"
        )

@router.get("/recommendations", response_model=RecommendationSummaryResponse)
async def get_recommendation_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    추천 시스템 요약
    - AI 추천 문제 현황
    - 맞춤형 학습 경로
    - 다음 학습 단계 제안
    """
    try:
        recommendations = await dashboard_service.get_recommendation_summary(
            db=db,
            user_id=current_user.id
        )
        return recommendations
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"추천 요약 조회 실패: {str(e)}"
        )

@router.get("/study-plan", response_model=WeeklyStudyPlanResponse)
async def get_weekly_study_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    target_date: Optional[datetime] = Query(None, description="목표 주차 (기본값: 현재 주)")
):
    """
    주간 학습 계획
    - AI 기반 맞춤형 학습 계획
    - 우선순위별 학습 항목
    - 예상 소요 시간
    """
    try:
        if target_date is None:
            target_date = datetime.now()
            
        study_plan = await dashboard_service.generate_weekly_study_plan(
            db=db,
            user_id=current_user.id,
            target_date=target_date
        )
        return study_plan
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"학습 계획 생성 실패: {str(e)}"
        )

@router.get("/goal")
async def get_learning_goal(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    현재 학습 목표 조회
    """
    try:
        goal = await dashboard_service.get_current_goal(
            db=db,
            user_id=current_user.id
        )
        return {"current_goal": goal}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"학습 목표 조회 실패: {str(e)}"
        )

@router.post("/goal", response_model=GoalUpdateResponse)
async def update_learning_goal(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    target_level: float = Query(..., ge=0.0, le=1.0, description="목표 학습 수준 (0.0-1.0)"),
    target_date: datetime = Query(..., description="목표 달성 일자")
):
    """
    학습 목표 설정/수정
    - 개인별 학습 목표 관리
    - 목표 대비 진행률 추적
    """
    try:
        result = await dashboard_service.update_learning_goal(
            db=db,
            user_id=current_user.id,
            target_level=target_level,
            target_date=target_date
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"학습 목표 설정 실패: {str(e)}"
        ) 