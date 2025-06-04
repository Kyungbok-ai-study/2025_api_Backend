"""
진단 API 라우터
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.schemas.diagnosis import (
    DiagnosisTestCreate, DiagnosisTestResponse, DiagnosisResultCreate,
    DiagnosisResultResponse, LearningLevelResponse, DiagnosisSubject,
    # 새로운 스키마들
    MultiChoiceTestCreate, MultiChoiceTestResponse, MultiChoiceAnswerSubmit,
    MultiChoiceResultResponse, MultiChoiceHistoryResponse
)
from app.services.diagnosis_service import DiagnosisService
from app.services.multi_choice_service import MultiChoiceService

router = APIRouter()
diagnosis_service = DiagnosisService()
multi_choice_service = MultiChoiceService()

# 기존 엔드포인트들
@router.get("/subjects", response_model=List[str])
async def get_diagnosis_subjects():
    """진단 가능한 과목 목록 조회"""
    return [subject.value for subject in DiagnosisSubject]

@router.post("/start", response_model=DiagnosisTestResponse)
async def start_diagnosis_test(
    test_data: DiagnosisTestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """진단 테스트 시작 (30문항 형태)"""
    try:
        return await diagnosis_service.create_test_session(
            db=db,
            user_id=current_user.id,
            subject=test_data.subject.value
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"진단 테스트 생성 실패: {str(e)}"
        )

@router.post("/submit", response_model=DiagnosisResultResponse)
async def submit_diagnosis_test(
    result_data: DiagnosisResultCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """진단 테스트 답안 제출 (30문항 형태)"""
    try:
        return await diagnosis_service.submit_test_answers(
            db=db,
            user_id=current_user.id,
            test_session_id=result_data.test_session_id,
            answers=result_data.answers
        )
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
    """진단 테스트 결과 조회"""
    try:
        return await diagnosis_service.get_test_result(
            db=db,
            user_id=current_user.id,
            test_session_id=test_session_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"진단 결과 조회 실패: {str(e)}"
        )

@router.get("/history", response_model=List[DiagnosisTestResponse])
async def get_diagnosis_history(
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 진단 이력 조회"""
    try:
        return await diagnosis_service.get_user_diagnosis_history(
            db=db,
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"진단 이력 조회 실패: {str(e)}"
        )

# 새로운 엔드포인트들 - 다중 선택지 (1문제 30선택지)
@router.post("/multi-choice/create", response_model=MultiChoiceTestResponse)
async def create_multi_choice_test(
    test_data: MultiChoiceTestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """다중 선택지 진단 테스트 생성 (1문제 30선택지)"""
    try:
        return await multi_choice_service.create_multi_choice_test(
            db=db,
            user_id=current_user.id,
            test_data=test_data
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"다중 선택지 테스트 생성 실패: {str(e)}"
        )

@router.post("/multi-choice/submit", response_model=MultiChoiceResultResponse)
async def submit_multi_choice_answer(
    answer_data: MultiChoiceAnswerSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """다중 선택지 답안 제출 및 결과 분석"""
    try:
        return await multi_choice_service.submit_multi_choice_answer(
            db=db,
            user_id=current_user.id,
            answer_data=answer_data
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"다중 선택지 답안 제출 실패: {str(e)}"
        )

@router.get("/multi-choice/sample", response_model=MultiChoiceTestResponse)
async def get_sample_multi_choice_test(
    subject: DiagnosisSubject = DiagnosisSubject.COMPUTER_SCIENCE,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """샘플 다중 선택지 테스트 조회 (테스트용)"""
    try:
        # 샘플 데이터 생성
        sample_choices = [
            "cemputer", "mebuter", "compter", "conmputer", "computar",
            "compiter", "combuter", "compoter", "computee", "compuer",
            "computar", "computer", "computor", "computter", "computeer",
            "competer", "computerr", "conputer", "compuuter", "computre",
            "computar", "compuuter", "computar", "computor", "computre",
            "coumputer", "computar", "compuder", "computar", "compiter"
        ]
        
        sample_test_data = MultiChoiceTestCreate(
            subject=subject,
            question_content="다음 중 '컴퓨터'의 올바른 영어 스펠링은 무엇입니까?",
            choices=sample_choices,
            correct_choice_index=11,  # "computer"가 11번째 (0-based index)
            max_time_minutes=60,
            shuffle_choices=True,
            description="컴퓨터 스펠링 진단 테스트"
        )
        
        return await multi_choice_service.create_multi_choice_test(
            db=db,
            user_id=current_user.id,
            test_data=sample_test_data
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"샘플 테스트 생성 실패: {str(e)}"
        )

@router.get("/multi-choice/history", response_model=MultiChoiceHistoryResponse)
async def get_multi_choice_history(
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """다중 선택지 테스트 이력 조회"""
    try:
        # 임시로 빈 응답 반환 (실제 구현은 추후)
        return MultiChoiceHistoryResponse(
            test_sessions=[],
            total_sessions=0,
            average_performance={},
            improvement_trend={},
            skill_development={}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"다중 선택지 이력 조회 실패: {str(e)}"
        )

@router.post("/multi-choice/quick-test", response_model=MultiChoiceResultResponse)
async def quick_multi_choice_test(
    selected_choice_index: int,
    confidence_level: str = "medium",
    time_spent_seconds: int = 120,
    eliminated_choices: Optional[List[int]] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """빠른 다중 선택지 테스트 (개발/테스트용)"""
    try:
        # 먼저 샘플 테스트 생성
        sample_test = await get_sample_multi_choice_test(
            subject=DiagnosisSubject.COMPUTER_SCIENCE,
            current_user=current_user,
            db=db
        )
        
        # 샘플 선택지에서 선택된 내용 찾기
        if 0 <= selected_choice_index < len(sample_test.choices):
            selected_content = sample_test.choices[selected_choice_index]
        else:
            raise ValueError("유효하지 않은 선택지 인덱스입니다.")
        
        # 답안 제출 데이터 구성
        answer_data = MultiChoiceAnswerSubmit(
            test_session_id=sample_test.test_session_id,
            selected_choice_index=selected_choice_index,
            selected_choice_content=selected_content,
            eliminated_choices=eliminated_choices or [],
            confidence_level=confidence_level,
            time_spent_seconds=time_spent_seconds,
            choice_timeline=[
                {"timestamp": 0, "action": "test_start"},
                {"timestamp": time_spent_seconds - 10, "action": "selection_change", "choice": selected_choice_index},
                {"timestamp": time_spent_seconds, "action": "final_submit"}
            ]
        )
        
        # 답안 제출
        return await multi_choice_service.submit_multi_choice_answer(
            db=db,
            user_id=current_user.id,
            answer_data=answer_data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"빠른 테스트 실행 실패: {str(e)}"
        ) 