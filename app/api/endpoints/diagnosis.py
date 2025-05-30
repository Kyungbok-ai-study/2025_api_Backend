"""
진단 테스트 관련 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.schemas.diagnosis import (
    DiagnosisTestCreate,
    DiagnosisTestResponse,
    DiagnosisResultCreate,
    DiagnosisResultResponse,
    LearningLevelResponse
)
from app.services.diagnosis_service import diagnosis_service
from app.auth.dependencies import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/start", response_model=DiagnosisTestResponse)
async def start_diagnosis_test(
    test_data: DiagnosisTestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    진단 테스트 시작
    - 30문항의 고정 문제 제공
    - 학생의 초기 학습 수준 진단
    """
    try:
        test_session = await diagnosis_service.create_test_session(
            db=db, 
            user_id=current_user.id,
            subject=test_data.subject
        )
        return test_session
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"진단 테스트 생성 실패: {str(e)}"
        )

@router.post("/submit", response_model=DiagnosisResultResponse)
async def submit_diagnosis_answers(
    result_data: DiagnosisResultCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    진단 테스트 답안 제출 및 결과 계산
    - 산술식을 통한 학습 수준 계산
    - 개별 피드백 제공
    """
    try:
        result = await diagnosis_service.submit_test_answers(
            db=db,
            user_id=current_user.id,
            test_session_id=result_data.test_session_id,
            answers=result_data.answers
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"진단 테스트 제출 실패: {str(e)}"
        )

@router.get("/result/{test_session_id}", response_model=LearningLevelResponse)
async def get_diagnosis_result(
    test_session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    진단 테스트 결과 조회
    - 학습 수준 지표 확인
    - 강점/약점 분석 결과
    """
    try:
        result = await diagnosis_service.get_test_result(
            db=db,
            user_id=current_user.id,
            test_session_id=test_session_id
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"진단 결과를 찾을 수 없습니다: {str(e)}"
        )

@router.get("/history", response_model=List[DiagnosisTestResponse])
async def get_diagnosis_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10,
    offset: int = 0
):
    """
    진단 테스트 이력 조회
    - 사용자의 모든 진단 테스트 기록
    - 시간별 학습 수준 변화 추이
    """
    try:
        history = await diagnosis_service.get_user_diagnosis_history(
            db=db,
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )
        return history
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"진단 이력 조회 실패: {str(e)}"
        )

@router.get("/subjects")
async def get_diagnosis_subjects():
    """
    진단 테스트 사용 가능한 과목 목록 조회
    """
    try:
        from app.models.diagnosis import DiagnosisSubject
        subjects = [
            {"value": subject.value, "name": subject.value.replace("_", " ").title()}
            for subject in DiagnosisSubject
        ]
        return {"subjects": subjects}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"과목 목록 조회 실패: {str(e)}"
        ) 