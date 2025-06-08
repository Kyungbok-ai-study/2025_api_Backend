"""
문제 추천 및 AI 문제 생성 관련 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.schemas.problems import (
    ProblemRecommendationRequest,
    ProblemResponse,
    AIGeneratedProblemRequest,
    AIGeneratedProblemResponse,
    ProblemSubmissionRequest,
    ProblemSubmissionResponse,
    ProblemStatisticsResponse
)
from app.services.problem_service import problem_service
from app.services.ai_service import ai_service
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.question import Subject

router = APIRouter()

@router.get("/recommended", response_model=List[ProblemResponse])
async def get_recommended_problems(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    subject: Optional[str] = Query(None, description="과목명"),
    difficulty_level: Optional[int] = Query(None, ge=1, le=5, description="난이도 (1-5)"),
    limit: int = Query(10, ge=1, le=50, description="문제 개수")
):
    """
    맞춤형 문제 추천
    - 학습 이력과 진단 결과 기반 AI 추천
    - pgvector를 활용한 유사도 검색
    """
    try:
        problems = await problem_service.get_recommended_problems(
            db=db,
            user_id=current_user.id,
            subject=subject,
            difficulty_level=difficulty_level,
            limit=limit
        )
        return problems
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"문제 추천 실패: {str(e)}"
        )

@router.get("/subjects")
async def get_available_subjects(
    db: Session = Depends(get_db)
):
    """
    사용 가능한 과목 목록 조회 (공개 API)
    """
    try:
        subjects = db.query(Subject.name).distinct().all()
        subject_list = [subject[0] for subject in subjects if subject[0]]
        
        # 기본 과목들 추가
        default_subjects = ["데이터베이스", "알고리즘", "프로그래밍", "네트워크", "자료구조"]
        for subject in default_subjects:
            if subject not in subject_list:
                subject_list.append(subject)
                
        return {"subjects": subject_list}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"과목 목록 조회 실패: {str(e)}"
        )

@router.post("/generate", response_model=AIGeneratedProblemResponse)
async def generate_ai_problem(
    request: AIGeneratedProblemRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AI 문제 생성 (EXAONE Deep 활용)
    - PDF 학습 데이터 기반 문제 생성
    - 실시간 문제 생성 및 검증
    """
    try:
        generated_problem = await ai_service.generate_problem(
            db=db,
            user_id=current_user.id,
            subject=request.subject,
            difficulty=request.difficulty,
            problem_type=request.problem_type,
            context=request.context
        )
        return generated_problem
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI 문제 생성 실패: {str(e)}"
        )

@router.post("/submit", response_model=ProblemSubmissionResponse)
async def submit_problem_answer(
    submission: ProblemSubmissionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    문제 답안 제출 및 채점
    - 정답률 계산 및 학습 이력 업데이트
    - 학습 수준 지표 재계산
    """
    try:
        result = await problem_service.submit_answer(
            db=db,
            user_id=current_user.id,
            problem_id=submission.problem_id,
            answer=submission.answer,
            time_spent=submission.time_spent
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"답안 제출 실패: {str(e)}"
        )

@router.get("/statistics", response_model=ProblemStatisticsResponse)
async def get_problem_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    period_days: int = Query(30, ge=1, le=365, description="통계 기간 (일)")
):
    """
    문제 풀이 통계 조회
    - 정답률, 풀이 시간, 난이도별 성과
    - 학습 성장 곡선 데이터
    """
    try:
        statistics = await problem_service.get_user_statistics(
            db=db,
            user_id=current_user.id,
            period_days=period_days
        )
        return statistics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"통계 조회 실패: {str(e)}"
        )

@router.get("/history", response_model=List[ProblemSubmissionResponse])
async def get_problem_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    subject: Optional[str] = Query(None, description="과목 필터"),
    limit: int = Query(20, ge=1, le=100, description="조회 개수"),
    offset: int = Query(0, ge=0, description="시작 위치")
):
    """
    문제 풀이 이력 조회
    - 과목별, 날짜별 필터링 지원
    - 오답 문제 재학습 기능 지원
    """
    try:
        history = await problem_service.get_user_problem_history(
            db=db,
            user_id=current_user.id,
            subject=subject,
            limit=limit,
            offset=offset
        )
        return history
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"이력 조회 실패: {str(e)}"
        )

@router.get("/review", response_model=List[ProblemResponse])
async def get_review_problems(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    review_type: str = Query("incorrect", pattern="^(incorrect|difficult|recent)$", description="복습 유형")
):
    """
    복습 문제 조회
    - 오답 문제, 어려운 문제, 최근 문제 등
    - 반복 학습 지원
    """
    try:
        review_problems = await problem_service.get_review_problems(
            db=db,
            user_id=current_user.id,
            review_type=review_type
        )
        return review_problems
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"복습 문제 조회 실패: {str(e)}"
        ) 