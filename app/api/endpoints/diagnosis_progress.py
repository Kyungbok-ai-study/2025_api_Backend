"""
진단테스트 차수 진행 상황 관리 API
학생별로 어떤 차수를 완료했는지 추적하고 다음 가능한 차수를 제공
"""
import json
import os
from typing import List, Dict, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.models.student_diagnosis_progress import StudentDiagnosisProgress, DiagnosisRoundConfig
from app.models.user import User
from app.auth.dependencies import get_current_user

router = APIRouter()

# Pydantic 모델들
class DiagnosisProgressResponse(BaseModel):
    user_id: int
    department: str
    current_round: int
    max_available_round: int
    completed_rounds: List[int]
    total_tests_completed: int
    average_score: float
    completion_rate: float
    last_test_date: Optional[datetime]
    
    class Config:
        from_attributes = True

class RoundDetailResponse(BaseModel):
    round_number: int
    completed_at: Optional[str]
    score: Optional[float]
    attempts: int
    time_spent: int
    questions_correct: int
    questions_total: int
    level: str
    session_id: str

class DiagnosisRoundInfo(BaseModel):
    round_number: int
    title: str
    focus_area: str
    description: Optional[str]
    total_questions: int
    time_limit_minutes: int
    passing_score: float
    is_completed: bool
    is_available: bool
    score: Optional[float]
    completion_date: Optional[str]

class CompleteRoundRequest(BaseModel):
    round_number: int
    score: float
    time_spent: int
    questions_correct: int
    questions_total: int
    session_id: str
    level: str = "미분류"

@router.get("/progress/{department}", response_model=DiagnosisProgressResponse)
async def get_diagnosis_progress(
    department: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """학생의 특정 학과 진단테스트 진행 상황 조회"""
    
    # 지원되는 학과 확인
    supported_departments = ["물리치료학과", "작업치료학과"]
    if department not in supported_departments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"지원되지 않는 학과입니다. 지원 학과: {supported_departments}"
        )
    
    # 기존 진행 상황 조회
    progress = db.query(StudentDiagnosisProgress).filter(
        StudentDiagnosisProgress.user_id == current_user.id,
        StudentDiagnosisProgress.department == department
    ).first()
    
    # 첫 번째 접근인 경우 새로 생성
    if not progress:
        progress = StudentDiagnosisProgress(
            user_id=current_user.id,
            department=department,
            current_round=0,
            max_available_round=1,
            completed_rounds=[],
            total_tests_completed=0,
            average_score=0.0,
            total_study_time=0
        )
        db.add(progress)
        db.commit()
        db.refresh(progress)
    
    return DiagnosisProgressResponse(
        user_id=progress.user_id,
        department=progress.department,
        current_round=progress.current_round,
        max_available_round=progress.max_available_round,
        completed_rounds=progress.completed_rounds or [],
        total_tests_completed=progress.total_tests_completed,
        average_score=progress.average_score,
        completion_rate=progress.get_completion_rate(),
        last_test_date=progress.last_test_date
    )

@router.get("/rounds/{department}", response_model=List[DiagnosisRoundInfo])
async def get_available_rounds(
    department: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """학과별 진단테스트 차수 목록 및 상태 조회"""
    
    # 진행 상황 조회
    progress = db.query(StudentDiagnosisProgress).filter(
        StudentDiagnosisProgress.user_id == current_user.id,
        StudentDiagnosisProgress.department == department
    ).first()
    
    if not progress:
        # 새로운 진행 상황 생성
        progress = StudentDiagnosisProgress(
            user_id=current_user.id,
            department=department,
            current_round=0,
            max_available_round=1,
            completed_rounds=[],
            total_tests_completed=0,
            average_score=0.0,
            total_study_time=0
        )
        db.add(progress)
        db.commit()
        db.refresh(progress)
    
    # 진단테스트 설정 파일에서 정보 로드
    config_file = "config/diagnostic_tests_config.json"
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="진단테스트 설정 파일을 찾을 수 없습니다."
        )
    
    # 학과 정보 조회
    dept_config = config_data.get("diagnostic_tests", {}).get("departments", {}).get(department)
    if not dept_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"학과 '{department}' 설정을 찾을 수 없습니다."
        )
    
    rounds_info = []
    
    for round_str, test_info in dept_config.get("tests", {}).items():
        round_num = int(round_str)
        
        # 완료 여부 및 점수 확인
        is_completed = progress.is_round_completed(round_num)
        round_score = progress.get_round_score(round_num)
        completion_date = None
        
        if is_completed and progress.round_details:
            round_detail = progress.round_details.get(str(round_num), {})
            completion_date = round_detail.get("completed_at")
        
        rounds_info.append(DiagnosisRoundInfo(
            round_number=round_num,
            title=test_info.get("title", f"{department} {round_num}차"),
            focus_area=test_info.get("focus_area", "일반"),
            description=f"{test_info.get('focus_area', '일반')} 중심의 진단테스트",
            total_questions=test_info.get("questions_count", 30),
            time_limit_minutes=test_info.get("time_limit", 60),
            passing_score=test_info.get("scoring", {}).get("pass_score", 60),
            is_completed=is_completed,
            is_available=progress.can_take_round(round_num),
            score=round_score,
            completion_date=completion_date
        ))
    
    # 차수 순으로 정렬
    rounds_info.sort(key=lambda x: x.round_number)
    
    return rounds_info

@router.post("/complete")
async def complete_diagnosis_round(
    request: CompleteRoundRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """진단테스트 차수 완료 처리"""
    
    # 세션 ID에서 학과 정보 추출 (예: DIAG_PT_R1_001 -> 물리치료학과)
    department_mapping = {
        "PT": "물리치료학과",
        "OT": "작업치료학과"
    }
    
    # 세션 ID 파싱
    try:
        parts = request.session_id.split("_")
        if len(parts) >= 2:
            dept_code = parts[1] if parts[0] == "DIAG" else parts[0]
            department = department_mapping.get(dept_code)
            
            if not department:
                raise ValueError("학과 코드를 인식할 수 없습니다.")
        else:
            raise ValueError("잘못된 세션 ID 형식입니다.")
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="잘못된 세션 ID 형식입니다."
        )
    
    # 진행 상황 조회 또는 생성
    progress = db.query(StudentDiagnosisProgress).filter(
        StudentDiagnosisProgress.user_id == current_user.id,
        StudentDiagnosisProgress.department == department
    ).first()
    
    if not progress:
        progress = StudentDiagnosisProgress(
            user_id=current_user.id,
            department=department,
            current_round=0,
            max_available_round=1,
            completed_rounds=[],
            total_tests_completed=0,
            average_score=0.0,
            total_study_time=0
        )
        db.add(progress)
    
    # 해당 차수를 볼 수 있는지 확인
    if not progress.can_take_round(request.round_number):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{request.round_number}차 테스트를 아직 볼 수 없습니다. 현재 가능한 최대 차수: {progress.max_available_round}"
        )
    
    # 세션 데이터 구성
    session_data = {
        "time_spent": request.time_spent,
        "questions_correct": request.questions_correct,
        "questions_total": request.questions_total,
        "level": request.level,
        "session_id": request.session_id
    }
    
    # 차수 완료 처리
    progress.complete_round(request.round_number, request.score, session_data)
    
    db.commit()
    db.refresh(progress)
    
    return {
        "success": True,
        "message": f"{department} {request.round_number}차 테스트가 완료되었습니다.",
        "current_round": progress.current_round,
        "next_available_round": progress.get_next_available_round(),
        "score": request.score,
        "level": request.level
    }

@router.get("/round-details/{department}/{round_number}")
async def get_round_details(
    department: str,
    round_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """특정 차수의 상세 결과 조회"""
    
    progress = db.query(StudentDiagnosisProgress).filter(
        StudentDiagnosisProgress.user_id == current_user.id,
        StudentDiagnosisProgress.department == department
    ).first()
    
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="진행 상황을 찾을 수 없습니다."
        )
    
    if not progress.is_round_completed(round_number):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{round_number}차 테스트가 완료되지 않았습니다."
        )
    
    round_detail = progress.round_details.get(str(round_number), {})
    
    return RoundDetailResponse(
        round_number=round_number,
        completed_at=round_detail.get("completed_at"),
        score=round_detail.get("score", 0.0),
        attempts=round_detail.get("attempts", 0),
        time_spent=round_detail.get("time_spent", 0),
        questions_correct=round_detail.get("questions_correct", 0),
        questions_total=round_detail.get("questions_total", 30),
        level=round_detail.get("level", "미분류"),
        session_id=round_detail.get("session_id", "")
    )

@router.get("/test-data/{department}/{round_number}")
async def get_test_data(
    department: str,
    round_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """특정 차수의 테스트 데이터 조회"""
    
    # 진행 상황 확인
    progress = db.query(StudentDiagnosisProgress).filter(
        StudentDiagnosisProgress.user_id == current_user.id,
        StudentDiagnosisProgress.department == department
    ).first()
    
    if not progress:
        # 새로운 진행 상황 생성
        progress = StudentDiagnosisProgress(
            user_id=current_user.id,
            department=department,
            current_round=0,
            max_available_round=1,
            completed_rounds=[],
            total_tests_completed=0,
            average_score=0.0,
            total_study_time=0
        )
        db.add(progress)
        db.commit()
        db.refresh(progress)
    
    # 해당 차수를 볼 수 있는지 확인
    if not progress.can_take_round(round_number):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{round_number}차 테스트를 아직 볼 수 없습니다. 현재 가능한 최대 차수: {progress.max_available_round}"
        )
    
    # 테스트 파일 경로 구성
    department_mapping = {
        "물리치료학과": "physics_therapy",
        "작업치료학과": "occupational_therapy"
    }
    
    dept_code = department_mapping.get(department)
    if not dept_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="지원되지 않는 학과입니다."
        )
    
    test_file_path = f"data/departments/medical/diagnostic_test_{dept_code}_round{round_number}.json"
    
    if not os.path.exists(test_file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{department} {round_number}차 테스트 파일을 찾을 수 없습니다."
        )
    
    try:
        with open(test_file_path, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        
        return test_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"테스트 데이터 로드 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/statistics/{department}")
async def get_department_statistics(
    department: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """학과별 진단테스트 통계 조회"""
    
    progress = db.query(StudentDiagnosisProgress).filter(
        StudentDiagnosisProgress.user_id == current_user.id,
        StudentDiagnosisProgress.department == department
    ).first()
    
    if not progress:
        return {
            "department": department,
            "total_rounds": 10,
            "completed_rounds": 0,
            "completion_rate": 0.0,
            "average_score": 0.0,
            "total_study_time": 0,
            "best_score": 0.0,
            "recent_activity": None
        }
    
    # 최고 점수 계산
    best_score = 0.0
    if progress.round_details:
        scores = [details.get("score", 0) for details in progress.round_details.values()]
        best_score = max(scores) if scores else 0.0
    
    return {
        "department": department,
        "total_rounds": 10,
        "completed_rounds": progress.total_tests_completed,
        "completion_rate": progress.get_completion_rate(),
        "average_score": progress.average_score,
        "total_study_time": progress.total_study_time,
        "best_score": best_score,
        "last_test_date": progress.last_test_date.isoformat() if progress.last_test_date else None,
        "learning_pattern": progress.learning_pattern
    } 