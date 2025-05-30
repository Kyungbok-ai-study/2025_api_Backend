"""
교수 대시보드 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.db.database import get_db
from app.auth.dependencies import get_current_professor
from app.models.user import User
from app.schemas.professor import (
    ProfessorDashboardResponse, ClassAnalyticsResponse,
    StudentProgressSummary, AssignmentResponse, 
    ClassPerformanceResponse, LearningInsightsResponse
)
from app.services.professor_service import ProfessorService

router = APIRouter()
professor_service = ProfessorService()

@router.get("/dashboard", response_model=ProfessorDashboardResponse)
async def get_professor_dashboard(
    current_user: User = Depends(get_current_professor),
    db: Session = Depends(get_db)
):
    """교수 대시보드 전체 개요"""
    try:
        return await professor_service.get_professor_dashboard(
            db=db,
            professor_id=current_user.id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"교수 대시보드 조회 실패: {str(e)}")

@router.get("/classes", response_model=List[ClassAnalyticsResponse])
async def get_class_analytics(
    semester: Optional[str] = Query(None, description="학기 (예: 2024-1)"),
    current_user: User = Depends(get_current_professor),
    db: Session = Depends(get_db)
):
    """담당 수업 분석"""
    try:
        return await professor_service.get_class_analytics(
            db=db,
            professor_id=current_user.id,
            semester=semester
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"수업 분석 조회 실패: {str(e)}")

@router.get("/students/progress", response_model=List[StudentProgressSummary])
async def get_students_progress(
    class_id: Optional[int] = Query(None, description="특정 수업 ID"),
    limit: int = Query(50, description="조회할 학생 수"),
    current_user: User = Depends(get_current_professor),
    db: Session = Depends(get_db)
):
    """학생 진도 현황"""
    try:
        return await professor_service.get_students_progress(
            db=db,
            professor_id=current_user.id,
            class_id=class_id,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"학생 진도 조회 실패: {str(e)}")

@router.post("/assignment", response_model=AssignmentResponse)
async def create_assignment(
    class_id: int,
    title: str,
    description: str,
    due_date: datetime,
    difficulty_level: int = Query(..., ge=1, le=5),
    current_user: User = Depends(get_current_professor),
    db: Session = Depends(get_db)
):
    """과제 생성"""
    try:
        return await professor_service.create_assignment(
            db=db,
            professor_id=current_user.id,
            class_id=class_id,
            title=title,
            description=description,
            due_date=due_date,
            difficulty_level=difficulty_level
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"과제 생성 실패: {str(e)}")

@router.get("/performance/class/{class_id}", response_model=ClassPerformanceResponse)
async def get_class_performance(
    class_id: int,
    period_days: int = Query(30, description="분석 기간 (일)"),
    current_user: User = Depends(get_current_professor),
    db: Session = Depends(get_db)
):
    """수업별 성과 분석"""
    try:
        return await professor_service.get_class_performance(
            db=db,
            professor_id=current_user.id,
            class_id=class_id,
            period_days=period_days
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"수업 성과 분석 실패: {str(e)}")

@router.get("/insights", response_model=LearningInsightsResponse)
async def get_learning_insights(
    current_user: User = Depends(get_current_professor),
    db: Session = Depends(get_db)
):
    """학습 인사이트 (AI 분석)"""
    try:
        return await professor_service.get_learning_insights(
            db=db,
            professor_id=current_user.id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"학습 인사이트 조회 실패: {str(e)}")

@router.get("/student/{student_id}/detail")
async def get_student_detail(
    student_id: int,
    current_user: User = Depends(get_current_professor),
    db: Session = Depends(get_db)
):
    """특정 학생 상세 분석"""
    try:
        return await professor_service.get_student_detail_analysis(
            db=db,
            professor_id=current_user.id,
            student_id=student_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"학생 상세 분석 실패: {str(e)}")

@router.post("/feedback/student/{student_id}")
async def send_student_feedback(
    student_id: int,
    feedback_message: str,
    feedback_type: str = Query(..., regex="^(encouragement|guidance|warning)$"),
    current_user: User = Depends(get_current_professor),
    db: Session = Depends(get_db)
):
    """학생 피드백 전송"""
    try:
        return await professor_service.send_student_feedback(
            db=db,
            professor_id=current_user.id,
            student_id=student_id,
            feedback_message=feedback_message,
            feedback_type=feedback_type
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"피드백 전송 실패: {str(e)}")

@router.get("/reports/weekly")
async def get_weekly_report(
    current_user: User = Depends(get_current_professor),
    db: Session = Depends(get_db)
):
    """주간 수업 리포트"""
    try:
        return await professor_service.generate_weekly_report(
            db=db,
            professor_id=current_user.id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"주간 리포트 생성 실패: {str(e)}")

@router.get("/curriculum/recommendations")
async def get_curriculum_recommendations(
    subject: str = Query(..., description="과목명"),
    current_user: User = Depends(get_current_professor),
    db: Session = Depends(get_db)
):
    """커리큘럼 개선 추천"""
    try:
        return await professor_service.get_curriculum_recommendations(
            db=db,
            professor_id=current_user.id,
            subject=subject
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"커리큘럼 추천 실패: {str(e)}") 