"""
AI 기반 진단 → 학과별 전문 문제 → 개인 맞춤 학습 API 엔드포인트

프로젝트 핵심 목적에 최적화된 API:
- 진단 테스트와 문제 추천을 통합한 워크플로우
- 교수 검증 기반 학과별 전문 문제 제공
- 실시간 학습 상호작용 추적 및 피드백
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.services.adaptive_learning_service import adaptive_learning_service

router = APIRouter(prefix="/adaptive-learning", tags=["적응형 학습"])

# === Pydantic 모델들 ===

class DiagnosisRequest(BaseModel):
    subject: str = Field(..., description="진단할 과목")
    force_new_diagnosis: bool = Field(False, description="강제로 새 진단 실행")

class SpecializedProblemsRequest(BaseModel):
    subject: str = Field(..., description="과목")
    specialization_level: Optional[int] = Field(None, ge=1, le=5, description="전문성 수준 (1-5)")
    count: int = Field(10, ge=1, le=50, description="문제 개수")

class LearningInteractionRequest(BaseModel):
    question_id: int = Field(..., description="문제 ID")
    interaction_type: str = Field(..., pattern="^(view|attempt|skip|review|bookmark|hint_used)$")
    is_correct: Optional[bool] = Field(None, description="정답 여부")
    time_spent: Optional[int] = Field(None, ge=0, description="소요 시간(초)")
    confidence_level: Optional[int] = Field(None, ge=1, le=5, description="확신도 (1-5)")

class StudyPathRequest(BaseModel):
    subject: str = Field(..., description="과목")
    target_level: Optional[float] = Field(0.8, ge=0.0, le=1.0, description="목표 수준")

# === API 엔드포인트들 ===

@router.post("/diagnose-and-recommend")
async def diagnose_and_recommend(
    request: DiagnosisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🔍 핵심 API: 진단 테스트 + 맞춤 문제 추천 통합 워크플로우
    
    이 API가 프로젝트의 핵심 기능을 제공합니다:
    1. AI 진단으로 학습 수준 파악
    2. 진단 결과 기반 맞춤 문제 추천
    3. 개인 학습 프로파일 업데이트
    """
    try:
        result = await adaptive_learning_service.diagnose_and_recommend(
            db=db,
            user_id=current_user.id,
            subject=request.subject
        )
        
        return {
            "status": "success",
            "data": result,
            "message": f"{request.subject} 과목 진단 및 맞춤 추천이 완료되었습니다."
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"진단 및 추천 실패: {str(e)}"
        )

@router.post("/specialized-problems")
async def get_specialized_problems(
    request: SpecializedProblemsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🎓 학과별 전문 문제 제공 (교수 검증 우선)
    
    특징:
    - 교수 2차 검증 이상 문제 우선 제공
    - 사용자 수준에 맞는 전문성 레벨 자동 조정
    - 실무 적용도가 높은 문제 위주
    """
    try:
        problems = await adaptive_learning_service.get_specialized_problems(
            db=db,
            user_id=current_user.id,
            subject=request.subject,
            specialization_level=request.specialization_level,
            count=request.count
        )
        
        return {
            "status": "success",
            "data": {
                "problems": problems,
                "total_count": len(problems),
                "subject": request.subject,
                "specialization_level": request.specialization_level
            },
            "message": f"{request.subject} 전문 문제 {len(problems)}개를 제공합니다."
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"전문 문제 조회 실패: {str(e)}"
        )

@router.post("/track-interaction")
async def track_learning_interaction(
    request: LearningInteractionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    📊 학습 상호작용 추적 및 실시간 피드백
    
    기능:
    - 모든 학습 상호작용 로그 기록
    - 즉시 학습 수준 조정
    - 다음 추천 문제 미리 계산
    - 실시간 피드백 제공
    """
    try:
        result = await adaptive_learning_service.track_learning_interaction(
            db=db,
            user_id=current_user.id,
            question_id=request.question_id,
            interaction_type=request.interaction_type,
            is_correct=request.is_correct,
            time_spent=request.time_spent,
            confidence_level=request.confidence_level
        )
        
        return {
            "status": "success",
            "data": result,
            "message": "학습 상호작용이 기록되었습니다."
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"상호작용 추적 실패: {str(e)}"
        )

@router.post("/personalized-study-path")
async def get_personalized_study_path(
    request: StudyPathRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🛤️ 개인 맞춤 학습 경로 생성
    
    특징:
    - 진단 결과 기반 단계별 학습 경로
    - 약점 영역 집중 보완 계획
    - 예상 완주 시간 및 마일스톤 제공
    """
    try:
        study_path = await adaptive_learning_service.get_personalized_study_path(
            db=db,
            user_id=current_user.id,
            subject=request.subject
        )
        
        return {
            "status": "success",
            "data": study_path,
            "message": f"{request.subject} 과목 개인 맞춤 학습 경로가 생성되었습니다."
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"학습 경로 생성 실패: {str(e)}"
        )

# === 보조 API들 ===

@router.get("/learning-profile/{subject}")
async def get_learning_profile(
    subject: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """학습 프로파일 조회"""
    try:
        result = db.execute(text("""
            SELECT * FROM user_learning_profiles 
            WHERE user_id = :user_id AND subject = :subject
        """), {"user_id": current_user.id, "subject": subject}).first()
        
        if not result:
            # 기본 프로파일 생성
            db.execute(text("""
                INSERT INTO user_learning_profiles (user_id, subject, current_level)
                VALUES (:user_id, :subject, 0.0)
            """), {"user_id": current_user.id, "subject": subject})
            db.commit()
            
            result = {
                "user_id": current_user.id,
                "subject": subject,
                "current_level": 0.0,
                "target_level": 0.8,
                "total_problems_solved": 0,
                "correct_rate": 0.0
            }
        
        return {"status": "success", "data": dict(result)}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"학습 프로파일 조회 실패: {str(e)}"
        )

@router.get("/subjects")
async def get_available_subjects(
    db: Session = Depends(get_db)
):
    """
    사용 가능한 과목 목록 조회 (진단 + 전문 문제 제공 가능)
    """
    try:
        # 진단 과목과 문제 과목을 통합
        diagnosis_subjects = [subject.value for subject in DiagnosisSubject]
        
        question_subjects = db.execute(text("""
            SELECT DISTINCT subject_name FROM questions 
            WHERE subject_name IS NOT NULL AND approval_status = 'approved'
            ORDER BY subject_name
        """)).fetchall()
        
        question_subject_list = [row[0] for row in question_subjects]
        
        # 통합 과목 목록
        all_subjects = list(set(diagnosis_subjects + question_subject_list))
        all_subjects.sort()
        
        return {
            "status": "success",
            "data": {
                "subjects": all_subjects,
                "diagnosis_subjects": diagnosis_subjects,
                "problem_subjects": question_subject_list
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"과목 목록 조회 실패: {str(e)}"
        )

@router.get("/interaction-history")
async def get_interaction_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    subject: Optional[str] = Query(None, description="과목 필터"),
    days: int = Query(30, ge=1, le=365, description="조회 기간 (일)")
):
    """학습 상호작용 이력 조회"""
    try:
        query = """
            SELECT li.*, q.subject_name, q.content
            FROM learning_interactions li
            LEFT JOIN questions q ON li.question_id = q.id
            WHERE li.user_id = :user_id 
            AND li.created_at >= NOW() - INTERVAL '%s days'
        """ % days
        
        params = {"user_id": current_user.id}
        
        if subject:
            query += " AND (li.question_subject = :subject OR q.subject_name = :subject)"
            params["subject"] = subject
            
        query += " ORDER BY li.created_at DESC LIMIT 100"
        
        interactions = db.execute(text(query), params).fetchall()
        
        return {
            "status": "success",
            "data": {
                "interactions": [dict(row) for row in interactions],
                "total_count": len(interactions),
                "period_days": days,
                "subject_filter": subject
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"상호작용 이력 조회 실패: {str(e)}"
        ) 