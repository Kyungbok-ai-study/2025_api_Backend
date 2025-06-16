"""
진단 API 라우터
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import uuid

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

@router.get("/result/{test_session_id}/detailed")
async def get_detailed_analysis(
    test_session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """상세한 학습 분석 데이터 조회 (클릭 패턴, 개념별 이해도, 시각화 데이터 포함)"""
    try:
        return await diagnosis_service.get_detailed_analysis(
            db=db,
            user_id=current_user.id,
            test_session_id=test_session_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"상세 분석 조회 실패: {str(e)}"
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


# === 새로운 1차 진단테스트 시스템 APIs ===
from app.models.diagnosis import (
    DiagnosticSession, DiagnosticAnswer, DiagnosticAIAnalysis, 
    DiagnosticStatistics, SessionStatus, AnalysisType
)

# 새로운 요청/응답 모델들
class SessionStartRequest(BaseModel):
    test_type: str = Field(..., description="테스트 타입")
    department: str = Field(..., description="학과명")
    total_questions: int = Field(..., description="총 문제 수")
    time_limit_minutes: int = Field(..., description="제한 시간(분)")
    round_number: Optional[int] = Field(None, description="진단테스트 회차 (자동 계산됨)")

class SessionStartResponse(BaseModel):
    session_id: str
    round_number: int
    message: str
    started_at: datetime
    expires_at: datetime

class AnswerSubmitRequest(BaseModel):
    session_id: str = Field(..., description="세션 ID")
    question_id: str = Field(..., description="문제 ID")
    question_number: int = Field(..., description="문제 번호")
    selected_answer: str = Field(..., description="선택한 답")
    correct_answer: str = Field(..., description="정답")
    is_correct: bool = Field(..., description="정답 여부")
    time_spent_ms: int = Field(..., description="풀이 시간(밀리초)")
    difficulty_level: Optional[str] = Field(None, description="난이도")
    domain: Optional[str] = Field(None, description="영역")
    question_type: Optional[str] = Field(None, description="문제 유형")

class AnswerSubmitResponse(BaseModel):
    message: str
    question_number: int
    is_correct: bool
    statistics_updated: bool

class DetailedResult(BaseModel):
    question_id: str
    question_number: int
    selected_answer: Optional[str]
    correct_answer: str
    is_correct: bool
    time_spent_ms: int
    difficulty_level: Optional[str]
    domain: Optional[str]
    question_type: Optional[str]

class SessionCompleteRequest(BaseModel):
    session_id: str = Field(..., description="세션 ID")
    total_score: float = Field(..., description="총 점수")
    correct_answers: int = Field(..., description="정답 수")
    wrong_answers: int = Field(..., description="오답 수")
    total_time_ms: int = Field(..., description="총 소요 시간(밀리초)")
    detailed_results: List[DetailedResult] = Field(..., description="상세 결과")
    request_ai_analysis: bool = Field(True, description="AI 분석 요청 여부")

class AIAnalysisResult(BaseModel):
    type_analysis: Dict[str, float]
    difficulty_analysis: Dict[str, float]
    time_analysis: Dict[str, Any]
    peer_comparison: Dict[str, Any]
    weak_areas: List[str]
    recommendations: List[str]
    confidence_score: float
    problem_analysis: Optional[Dict[str, Any]] = None  # 문제별 AI 해설

class SessionCompleteResponse(BaseModel):
    message: str
    session_id: str
    final_score: float
    completion_time: datetime
    ai_analysis: Optional[AIAnalysisResult]


# 실제 데이터베이스 기반 AI 분석 함수
async def real_data_ai_analysis(
    session_id: str,
    user_id: int,
    detailed_results: List[DetailedResult],
    total_score: float,
    total_time_ms: int,
    test_type: str,
    department: str,
    db: Session
) -> AIAnalysisResult:
    """실제 데이터베이스 데이터를 기반으로 한 AI 분석"""
    
    # 1. 개인 분석: 유형별/난이도별 분석
    type_scores = {}
    domain_scores = {}
    difficulty_scores = {}
    
    for result in detailed_results:
        # 유형별 정답률
        if result.question_type:
            if result.question_type not in type_scores:
                type_scores[result.question_type] = {'correct': 0, 'total': 0}
            type_scores[result.question_type]['total'] += 1
            if result.is_correct:
                type_scores[result.question_type]['correct'] += 1
        
        # 영역별 정답률
        if result.domain:
            if result.domain not in domain_scores:
                domain_scores[result.domain] = {'correct': 0, 'total': 0}
            domain_scores[result.domain]['total'] += 1
            if result.is_correct:
                domain_scores[result.domain]['correct'] += 1
        
        # 난이도별 정답률
        if result.difficulty_level:
            if result.difficulty_level not in difficulty_scores:
                difficulty_scores[result.difficulty_level] = {'correct': 0, 'total': 0}
            difficulty_scores[result.difficulty_level]['total'] += 1
            if result.is_correct:
                difficulty_scores[result.difficulty_level]['correct'] += 1
    
    # 백분율로 변환
    type_analysis = {
        k: round((v['correct'] / v['total']) * 100, 1) 
        for k, v in type_scores.items()
    }
    
    difficulty_analysis = {
        k: round((v['correct'] / v['total']) * 100, 1) 
        for k, v in difficulty_scores.items()
    }
    
    # 2. 동료 비교 분석 (실제 데이터베이스 기반)
    peer_comparison = await get_peer_comparison_analysis(
        user_id, total_score, total_time_ms, test_type, department, db
    )
    
    # 3. 개별 문제 분석 및 AI 해설 생성 (실제 통계 데이터 기반)
    problem_analysis = await get_problem_difficulty_analysis(
        detailed_results, test_type, department, db
    )
    
    # 4. 시간 분석 (실제 데이터와 비교)
    time_analysis = await get_time_analysis(
        total_time_ms, len(detailed_results), test_type, department, db
    )
    
    # 5. 약한 영역 찾기 (실제 데이터 기반)
    weak_areas = []
    for area, score in type_analysis.items():
        if score < 60:  # 60% 미만은 약한 영역
            weak_areas.append(area)
    
    # 6. 개인화된 권장사항 생성
    recommendations = await generate_personalized_recommendations(
        total_score, type_analysis, weak_areas, time_analysis, peer_comparison
    )
    
    return AIAnalysisResult(
        type_analysis=type_analysis,
        difficulty_analysis=difficulty_analysis,
        time_analysis=time_analysis,
        peer_comparison=peer_comparison,
        weak_areas=weak_areas,
        recommendations=recommendations,
        confidence_score=0.92,  # 실제 데이터 기반이므로 더 높은 신뢰도
        problem_analysis=problem_analysis  # 문제별 AI 해설 추가
    )


async def get_peer_comparison_analysis(
    user_id: int, 
    total_score: float, 
    total_time_ms: int, 
    test_type: str, 
    department: str, 
    db: Session
) -> Dict[str, Any]:
    """동료 비교 분석 (실제 데이터베이스 기반)"""
    
    # 같은 학과, 같은 테스트 타입의 완료된 세션들 가져오기
    peer_sessions = db.query(DiagnosticSession).filter(
        and_(
            DiagnosticSession.test_type == test_type,
            DiagnosticSession.department == department,
            DiagnosticSession.status == SessionStatus.COMPLETED,
            DiagnosticSession.user_id != user_id,  # 본인 제외
            DiagnosticSession.total_score.isnot(None)
        )
    ).all()
    
    if not peer_sessions:
        # 동료 데이터가 없는 경우 기본값 반환
        return {
            "percentile": 50,
            "department_average": total_score,
            "ranking": "평가 불가 (비교 데이터 부족)",
            "total_peers": 0,
            "better_than_peers": 0
        }
    
    # 점수 분석
    peer_scores = [session.total_score for session in peer_sessions]
    peer_times = [session.total_time_ms for session in peer_sessions if session.total_time_ms]
    
    # 통계 계산
    avg_score = sum(peer_scores) / len(peer_scores)
    avg_time = sum(peer_times) / len(peer_times) if peer_times else total_time_ms
    
    # 백분위 계산
    better_than_count = sum(1 for score in peer_scores if total_score > score)
    percentile = round((better_than_count / len(peer_scores)) * 100, 1)
    
    # 순위 계산
    ranking = "상위 10%" if percentile >= 90 else \
              "상위 25%" if percentile >= 75 else \
              "상위 50%" if percentile >= 50 else \
              "하위 50%"
    
    return {
        "percentile": percentile,
        "department_average": round(avg_score, 1),
        "department_avg_time": round(avg_time / 1000, 1),  # 초 단위
        "ranking": ranking,
        "total_peers": len(peer_sessions),
        "better_than_peers": better_than_count,
        "score_vs_avg": round(total_score - avg_score, 1),
        "time_vs_avg": round((total_time_ms - avg_time) / 1000, 1)  # 초 단위
    }


async def get_problem_difficulty_analysis(
    detailed_results: List[DetailedResult], 
    test_type: str, 
    department: str, 
    db: Session
) -> Dict[str, Any]:
    """문제별 난이도 분석 및 AI 해설 생성 (실제 통계 데이터 기반)"""
    
    problem_stats = {}
    
    for result in detailed_results:
        # 해당 문제의 통계 데이터 가져오기
        stat = db.query(DiagnosticStatistics).filter(
            and_(
                DiagnosticStatistics.question_id == result.question_id,
                DiagnosticStatistics.test_type == test_type,
                DiagnosticStatistics.department == department
            )
        ).first()
        
        if stat:
            # 실제 통계 데이터 기반
            problem_accuracy = (stat.correct_attempts / stat.total_attempts * 100) if stat.total_attempts > 0 else 0
            problem_avg_time = stat.avg_time_ms / 1000  # 초 단위
            
            # AI 해설 생성
            ai_explanation = generate_ai_explanation(
                result.question_id,
                result.question_number,
                result.selected_answer,
                result.correct_answer,
                result.is_correct,
                result.domain,
                result.question_type,
                problem_accuracy,
                stat.difficulty_rating
            )
            
            problem_stats[result.question_id] = {
                "question_number": result.question_number,
                "user_correct": result.is_correct,
                "user_time": result.time_spent_ms / 1000,
                "overall_accuracy": round(problem_accuracy, 1),
                "avg_time": round(problem_avg_time, 1),
                "difficulty_rating": stat.difficulty_rating,
                "total_attempts": stat.total_attempts,
                "user_vs_avg_time": round((result.time_spent_ms - stat.avg_time_ms) / 1000, 1),
                "ai_explanation": ai_explanation,  # AI 해설 추가
                "selected_answer": result.selected_answer,
                "correct_answer": result.correct_answer,
                "domain": result.domain,
                "question_type": result.question_type
            }
    
    return problem_stats


def generate_ai_explanation(
    question_id: str,
    question_number: int,
    selected_answer: str,
    correct_answer: str,
    is_correct: bool,
    domain: str,
    question_type: str,
    overall_accuracy: float,
    difficulty_rating: float
) -> Dict[str, str]:
    """문제별 AI 해설 생성"""
    
    # 난이도 텍스트 변환
    difficulty_text = {
        1.0: "쉬운",
        2.0: "보통",
        3.0: "어려운", 
        4.0: "매우 어려운"
    }.get(difficulty_rating, "보통")
    
    # 정답/오답에 따른 기본 메시지
    if is_correct:
        result_message = f"🎉 정답입니다! {correct_answer}번을 선택하셨네요."
        feedback_type = "정답 분석"
    else:
        result_message = f"❌ 아쉽게도 틀렸습니다. 선택하신 {selected_answer}번이 아닌 {correct_answer}번이 정답입니다."
        feedback_type = "오답 분석"
    
    # 도메인별 특화 조언
    domain_advice = {
        "신경계": "신경계 문제는 해부학적 구조와 기능을 연결해서 이해하는 것이 중요합니다.",
        "근골격계": "근골격계는 근육의 기시점과 정지점, 그리고 움직임의 방향을 정확히 파악해야 합니다.",
        "심폐순환계": "심폐순환계는 생리학적 기전과 병리학적 변화를 함께 고려해야 합니다.",
        "기타": "이 영역은 기본 개념의 정확한 이해가 필요합니다."
    }.get(domain, "기본 개념을 정확히 이해하고 응용하는 것이 중요합니다.")
    
    # 유형별 학습 조언
    type_advice = {
        "기본개념": "기본 개념은 모든 학습의 기초입니다. 교과서의 정의를 정확히 암기하고 이해하세요.",
        "종합판단": "종합 판단 문제는 여러 개념을 연결해서 사고하는 능력을 요구합니다.",
        "응용문제": "응용 문제는 실제 임상 상황을 가정한 문제입니다. 이론과 실제를 연결해서 생각해보세요."
    }.get(question_type, "문제 유형에 맞는 접근법을 사용하세요.")
    
    # 난이도별 조언
    if difficulty_rating >= 3.0:
        difficulty_advice = f"이 문제는 {difficulty_text} 문제로, 전체 학생 중 {overall_accuracy:.1f}%만 맞췄습니다. " + \
                          ("훌륭한 실력입니다!" if is_correct else "충분히 틀릴 수 있는 어려운 문제입니다.")
    elif difficulty_rating >= 2.0:
        difficulty_advice = f"이 문제는 {difficulty_text} 난이도로, {overall_accuracy:.1f}%의 정답률을 보입니다. " + \
                          ("적절한 수준의 문제를 잘 해결하셨네요!" if is_correct else "조금 더 공부하면 충분히 맞출 수 있습니다.")
    else:
        difficulty_advice = f"이 문제는 {difficulty_text} 문제로, {overall_accuracy:.1f}%의 높은 정답률을 보입니다. " + \
                          ("기본기가 탄탄하네요!" if is_correct else "기본 개념을 다시 한 번 점검해보세요.")
    
    # 학습 방향 제시
    if is_correct:
        learning_direction = f"✅ {domain} 영역의 {question_type} 문제를 잘 해결하고 있습니다. 이 수준을 유지하세요!"
    else:
        learning_direction = f"📚 {domain} 영역의 {question_type} 문제에 대한 추가 학습이 필요합니다. " + \
                           "관련 교재의 해당 단원을 다시 복습해보세요."
    
    # 문제 해결 팁
    solving_tip = "💡 이런 유형의 문제를 만났을 때는 " + \
                  "문제를 천천히 읽고, 핵심 키워드를 찾아 관련 개념을 떠올린 후, " + \
                  "각 선택지를 차근차근 검토하는 것이 좋습니다."
    
    return {
        "result_message": result_message,
        "feedback_type": feedback_type,
        "difficulty_analysis": difficulty_advice,
        "domain_advice": domain_advice,
        "type_advice": type_advice,
        "learning_direction": learning_direction,
        "solving_tip": solving_tip,
        "summary": f"문제 {question_number}번: {feedback_type} | {domain} | {question_type} | 난이도: {difficulty_text}"
    }


async def get_time_analysis(
    total_time_ms: int, 
    total_questions: int, 
    test_type: str, 
    department: str, 
    db: Session
) -> Dict[str, Any]:
    """시간 분석 (실제 데이터와 비교)"""
    
    # 같은 테스트의 다른 세션들 시간 데이터 가져오기
    peer_sessions = db.query(DiagnosticSession).filter(
        and_(
            DiagnosticSession.test_type == test_type,
            DiagnosticSession.department == department,
            DiagnosticSession.status == SessionStatus.COMPLETED,
            DiagnosticSession.total_time_ms.isnot(None)
        )
    ).all()
    
    avg_time_per_question = total_time_ms / total_questions
    
    if peer_sessions:
        peer_times = [session.total_time_ms for session in peer_sessions]
        avg_peer_time = sum(peer_times) / len(peer_times)
        avg_peer_time_per_question = avg_peer_time / total_questions
        
        # 시간 효율성 평가
        time_efficiency = "매우 빠름" if avg_time_per_question < avg_peer_time_per_question * 0.7 else \
                         "빠름" if avg_time_per_question < avg_peer_time_per_question * 0.9 else \
                         "보통" if avg_time_per_question < avg_peer_time_per_question * 1.1 else \
                         "느림" if avg_time_per_question < avg_peer_time_per_question * 1.3 else \
                         "매우 느림"
    else:
        avg_peer_time_per_question = avg_time_per_question
        time_efficiency = "보통"
    
    return {
        "total_time_ms": total_time_ms,
        "total_time_seconds": round(total_time_ms / 1000, 1),
        "avg_time_per_question": round(avg_time_per_question / 1000, 1),  # 초 단위
        "peer_avg_time_per_question": round(avg_peer_time_per_question / 1000, 1),  # 초 단위
        "time_efficiency": time_efficiency,
        "time_percentile": calculate_time_percentile(total_time_ms, [s.total_time_ms for s in peer_sessions])
    }


def calculate_time_percentile(user_time: int, peer_times: List[int]) -> float:
    """시간 백분위 계산 (빠를수록 높은 백분위)"""
    if not peer_times:
        return 50.0
    
    faster_count = sum(1 for time in peer_times if user_time < time)
    return round((faster_count / len(peer_times)) * 100, 1)


async def generate_personalized_recommendations(
    total_score: float,
    type_analysis: Dict[str, float],
    weak_areas: List[str],
    time_analysis: Dict[str, Any],
    peer_comparison: Dict[str, Any]
) -> List[str]:
    """개인화된 권장사항 생성"""
    
    recommendations = []
    
    # 점수 기반 권장사항
    if total_score >= 90:
        recommendations.append("🎉 탁월한 성과입니다! 현재 수준을 유지하며 더 어려운 문제에 도전해보세요.")
    elif total_score >= 80:
        recommendations.append("👍 우수한 성과입니다. 약한 영역을 보완하면 더욱 향상될 것입니다.")
    elif total_score >= 70:
        recommendations.append("📚 양호한 수준입니다. 꾸준한 학습으로 더 높은 성취를 이룰 수 있습니다.")
    elif total_score >= 60:
        recommendations.append("⚠️ 기본 수준입니다. 체계적인 복습이 필요합니다.")
    else:
        recommendations.append("기초 개념부터 차근차근 다시 학습하는 것을 권장합니다.")
    
    # 약한 영역 기반 권장사항
    if weak_areas:
        if len(weak_areas) == 1:
            recommendations.append(f"🎯 {weak_areas[0]} 영역에 집중적인 학습이 필요합니다.")
        else:
            recommendations.append(f"🎯 {', '.join(weak_areas[:2])} 영역의 집중 학습을 권장합니다.")
    
    # 시간 효율성 기반 권장사항
    if time_analysis["time_efficiency"] == "매우 느림":
        recommendations.append("⏱️ 문제 해결 속도 향상이 필요합니다. 시간 제한을 두고 연습해보세요.")
    elif time_analysis["time_efficiency"] == "매우 빠름":
        recommendations.append("⚡ 빠른 문제 해결 능력을 보여주셨습니다. 정확도를 더욱 높여보세요.")
    
    # 동료 비교 기반 권장사항
    if peer_comparison["percentile"] >= 80:
        recommendations.append(f"🏆 학과 동료들 중 상위 {100-peer_comparison['percentile']:.0f}%에 해당하는 우수한 성과입니다.")
    elif peer_comparison["percentile"] <= 20:
        recommendations.append("💪 동료들과 비교하여 더 많은 노력이 필요합니다. 체계적인 학습 계획을 세워보세요.")
    
    # 최소 1개 권장사항 보장
    if not recommendations:
        recommendations.append("📈 꾸준한 학습으로 더 나은 성과를 이룰 수 있습니다.")
    
    return recommendations


@router.post("/sessions/start", response_model=SessionStartResponse)
async def start_diagnostic_session(
    request: SessionStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """진단테스트 세션 시작 - 자동으로 다음 회차 계산"""
    try:
        # 🎯 사용자의 진단테스트 완료 상태 확인
        user_completed_first = getattr(current_user, 'diagnostic_test_completed', False)
        
        # 🎯 사용자의 최근 진단테스트 회차 조회 (완료된 것만)
        latest_session = db.query(DiagnosticSession).filter(
            and_(
                DiagnosticSession.user_id == current_user.id,
                DiagnosticSession.test_type == request.test_type,
                DiagnosticSession.department == request.department,
                DiagnosticSession.status == SessionStatus.COMPLETED
            )
        ).order_by(DiagnosticSession.round_number.desc()).first()
        
        # 다음 회차 계산 (1차~10차)
        if not user_completed_first:
            # 🎯 1차 진단테스트를 완료하지 않았다면 항상 1차
            next_round = 1
            print(f"🎯 1차 진단테스트 미완료 - 1차로 시작")
        elif latest_session:
            # 1차 완료 후 다음 회차 계산
            next_round = min(latest_session.round_number + 1, 10)  # 최대 10차까지
            print(f"🎯 최근 완료 회차: {latest_session.round_number}차 → 다음: {next_round}차")
        else:
            # 1차 완료했지만 세션이 없는 경우 (데이터 불일치)
            next_round = 1
            print(f"🎯 1차 완료 상태이지만 세션 없음 - 1차로 시작")
        
        # 세션 ID 생성 (UUID 기반)
        session_id = f"diag_{uuid.uuid4().hex[:12]}"
        
        # 현재 진행 중인 세션이 있는지 확인
        existing_session = db.query(DiagnosticSession).filter(
            and_(
                DiagnosticSession.user_id == current_user.id,
                DiagnosticSession.status == SessionStatus.IN_PROGRESS
            )
        ).first()
        
        if existing_session:
            # 기존 세션을 중단으로 표시
            existing_session.status = SessionStatus.ABANDONED
            existing_session.updated_at = datetime.utcnow()
        
        # 새 세션 생성
        new_session = DiagnosticSession(
            session_id=session_id,
            user_id=current_user.id,
            test_type=request.test_type,
            department=request.department,
            round_number=next_round,  # 🎯 자동 계산된 회차
            total_questions=request.total_questions,
            time_limit_minutes=request.time_limit_minutes,
            started_at=datetime.utcnow(),
            status=SessionStatus.IN_PROGRESS
        )
        
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        
        # 만료 시간 계산
        expires_at = new_session.started_at + timedelta(minutes=request.time_limit_minutes)
        
        return SessionStartResponse(
            session_id=session_id,
            round_number=next_round,  # 🎯 계산된 회차 반환
            message=f"{next_round}차 진단테스트 세션이 성공적으로 시작되었습니다.",
            started_at=new_session.started_at,
            expires_at=expires_at
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"세션 시작 실패: {str(e)}")


@router.post("/sessions/answer", response_model=AnswerSubmitResponse)
async def submit_answer(
    request: AnswerSubmitRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """문제 답변을 제출하고 실시간으로 저장합니다."""
    try:
        # 세션 유효성 검증
        session = db.query(DiagnosticSession).filter(
            and_(
                DiagnosticSession.session_id == request.session_id,
                DiagnosticSession.user_id == current_user.id,
                DiagnosticSession.status == SessionStatus.IN_PROGRESS
            )
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="유효하지 않은 세션입니다.")
        
        # 세션 만료 확인
        expires_at = session.started_at + timedelta(minutes=session.time_limit_minutes)
        if datetime.utcnow() > expires_at:
            session.status = SessionStatus.EXPIRED
            db.commit()
            raise HTTPException(status_code=410, detail="테스트 시간이 만료되었습니다.")
        
        # 중복 답변 확인
        existing_answer = db.query(DiagnosticAnswer).filter(
            and_(
                DiagnosticAnswer.session_id == request.session_id,
                DiagnosticAnswer.question_id == request.question_id
            )
        ).first()
        
        if existing_answer:
            # 기존 답변 업데이트
            existing_answer.selected_answer = request.selected_answer
            existing_answer.is_correct = request.is_correct
            existing_answer.time_spent_ms = request.time_spent_ms
            existing_answer.answered_at = datetime.utcnow()
        else:
            # 새 답변 생성
            new_answer = DiagnosticAnswer(
                session_id=request.session_id,
                question_id=request.question_id,
                question_number=request.question_number,
                selected_answer=request.selected_answer,
                correct_answer=request.correct_answer,
                is_correct=request.is_correct,
                time_spent_ms=request.time_spent_ms,
                difficulty_level=request.difficulty_level,
                domain=request.domain,
                question_type=request.question_type
            )
            db.add(new_answer)
        
        db.commit()
        
        # 백그라운드에서 통계 업데이트
        background_tasks.add_task(
            update_question_statistics,
            db,
            session.test_type,
            session.department,
            request.question_id,
            request.is_correct,
            request.time_spent_ms
        )
        
        return AnswerSubmitResponse(
            message="답변이 성공적으로 저장되었습니다.",
            question_number=request.question_number,
            is_correct=request.is_correct,
            statistics_updated=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"답변 저장 실패: {str(e)}")


@router.post("/sessions/complete", response_model=SessionCompleteResponse)
async def complete_diagnostic_session(
    request: SessionCompleteRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """진단테스트를 완료하고 AI 분석을 수행합니다."""
    try:
        # 세션 유효성 검증
        session = db.query(DiagnosticSession).filter(
            and_(
                DiagnosticSession.session_id == request.session_id,
                DiagnosticSession.user_id == current_user.id
            )
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="유효하지 않은 세션입니다.")
        
        # 세션 완료 처리
        session.completed_at = datetime.utcnow()
        session.total_score = request.total_score
        session.correct_answers = request.correct_answers
        session.wrong_answers = request.wrong_answers
        session.total_time_ms = request.total_time_ms
        session.status = SessionStatus.COMPLETED
        session.updated_at = datetime.utcnow()
        
        # 🎯 사용자의 진단테스트 완료 상태 업데이트 (1차 완료 시)
        print(f"🔍 진단테스트 완료 체크: round_number={session.round_number}, current_completed={getattr(current_user, 'diagnostic_test_completed', False)}")
        
        if session.round_number == 1 and not getattr(current_user, 'diagnostic_test_completed', False):
            print(f"✅ 1차 진단테스트 완료 - 사용자 상태 업데이트 시작")
            
            # JSONB 필드에 진단테스트 완료 정보 저장
            current_user.set_diagnostic_test_info(
                completed=True,
                completed_at=datetime.utcnow().isoformat(),
                latest_score=request.total_score,
                test_count=1
            )
            current_user.updated_at = datetime.utcnow()
            
            print(f"📝 사용자 diagnosis_info 업데이트: {current_user.diagnosis_info}")
            print(f"🎯 diagnostic_test_completed: {current_user.diagnostic_test_completed}")
        else:
            print(f"⚠️ 1차 진단테스트 완료 조건 불충족 또는 이미 완료됨")
        
        db.commit()
        
        # 🔔 교수 알림 발송
        try:
            from app.services.diagnosis_alert_hook import diagnosis_alert_hook
            
            diagnosis_result = {
                "test_id": session.session_id,
                "test_type": session.test_type or "진단테스트",
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "score": float(request.total_score),
                "total_questions": session.total_questions,
                "correct_answers": request.correct_answers,
                "time_taken": session.total_time_ms,
                "department": session.department,
                "round_number": session.round_number,
                "performance_summary": {
                    "accuracy": round((request.correct_answers / session.total_questions) * 100, 1) if session.total_questions > 0 else 0,
                    "total_time_seconds": round(session.total_time_ms / 1000, 1) if session.total_time_ms else 0,
                    "average_time_per_question": round((session.total_time_ms / session.total_questions) / 1000, 1) if session.total_questions > 0 and session.total_time_ms else 0
                }
            }
            
            alert_result = await diagnosis_alert_hook.on_diagnosis_completed(
                db, current_user.id, diagnosis_result
            )
            
            if alert_result["success"]:
                print(f"📧 교수 알림 발송 완료: {alert_result['alerts_created']}개")
            else:
                print(f"❌ 교수 알림 발송 실패: {alert_result.get('error')}")
                
        except Exception as e:
            print(f"⚠️ 교수 알림 발송 중 오류 (진단테스트는 정상 완료): {e}")
        
        # AI 분석 수행 (실제 데이터베이스 기반)
        ai_analysis_result = None
        if request.request_ai_analysis:
            try:
                # 실제 데이터베이스 기반 AI 분석 수행
                ai_analysis_result = await real_data_ai_analysis(
                    session_id=request.session_id,
                    user_id=current_user.id,
                    detailed_results=request.detailed_results,
                    total_score=request.total_score,
                    total_time_ms=request.total_time_ms,
                    test_type=session.test_type,
                    department=session.department,
                    db=db
                )
                
                # AI 분석 결과 저장
                ai_analysis_record = DiagnosticAIAnalysis(
                    session_id=request.session_id,
                    analysis_type=AnalysisType.COMPREHENSIVE,
                    analysis_data=ai_analysis_result.dict(),
                    weak_areas=ai_analysis_result.weak_areas,
                    recommendations=ai_analysis_result.recommendations,
                    peer_comparison=ai_analysis_result.peer_comparison,
                    confidence_score=ai_analysis_result.confidence_score,
                    ai_model_version="real-data-v1.0"  # 실제 데이터 기반 분석임을 표시
                )
                
                db.add(ai_analysis_record)
                db.commit()
                
            except Exception as ai_error:
                print(f"AI 분석 실패: {ai_error}")
                # AI 분석 실패해도 테스트 완료는 성공으로 처리
                ai_analysis_result = None
        
        return SessionCompleteResponse(
            message="진단테스트가 성공적으로 완료되었습니다.",
            session_id=request.session_id,
            final_score=request.total_score,
            completion_time=session.completed_at,
            ai_analysis=ai_analysis_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"테스트 완료 처리 실패: {str(e)}")


# 유틸리티 함수
def update_question_statistics(
    db: Session,
    test_type: str,
    department: str,
    question_id: str,
    is_correct: bool,
    time_spent_ms: int
):
    """문제별 통계를 업데이트합니다. (백그라운드 태스크)"""
    try:
        # 기존 통계 조회
        stat = db.query(DiagnosticStatistics).filter(
            and_(
                DiagnosticStatistics.test_type == test_type,
                DiagnosticStatistics.department == department,
                DiagnosticStatistics.question_id == question_id
            )
        ).first()
        
        if stat:
            # 기존 통계 업데이트
            stat.total_attempts += 1
            if is_correct:
                stat.correct_attempts += 1
            
            # 평균 시간 계산 (이동 평균)
            stat.avg_time_ms = round(
                (stat.avg_time_ms * (stat.total_attempts - 1) + time_spent_ms) / stat.total_attempts
            )
            
            # 실제 난이도 평가 (정답률 기반)
            accuracy_rate = stat.correct_attempts / stat.total_attempts
            if accuracy_rate >= 0.8:
                stat.difficulty_rating = 1.0  # 쉬움
            elif accuracy_rate >= 0.6:
                stat.difficulty_rating = 2.0  # 보통
            elif accuracy_rate >= 0.4:
                stat.difficulty_rating = 3.0  # 어려움
            else:
                stat.difficulty_rating = 4.0  # 매우 어려움
            
            stat.last_updated = datetime.utcnow()
        else:
            # 새 통계 생성
            new_stat = DiagnosticStatistics(
                test_type=test_type,
                department=department,
                question_id=question_id,
                total_attempts=1,
                correct_attempts=1 if is_correct else 0,
                avg_time_ms=time_spent_ms,
                difficulty_rating=2.0,  # 기본값: 보통
                last_updated=datetime.utcnow()
            )
            db.add(new_stat)
        
        db.commit()
        
    except Exception as e:
        print(f"통계 업데이트 실패: {e}")
        db.rollback()


# === 🎯 진단테스트 이력 관리 APIs ===

class DiagnosticHistoryResponse(BaseModel):
    """진단테스트 이력 응답 모델"""
    session_id: str
    round_number: int
    test_type: str
    department: str
    total_score: Optional[float]
    correct_answers: Optional[int]
    total_questions: int
    completion_rate: float  # 완료율
    started_at: datetime
    completed_at: Optional[datetime]
    total_time_ms: Optional[int]
    status: str
    ai_analysis_available: bool  # AI 분석 데이터 존재 여부

class DiagnosticHistoryListResponse(BaseModel):
    """진단테스트 이력 목록 응답"""
    histories: List[DiagnosticHistoryResponse]
    total_count: int
    completed_rounds: List[int]  # 완료된 회차 목록
    next_round: int  # 다음 진행할 회차
    progress_summary: Dict[str, Any]  # 진행 상황 요약


@router.get("/sessions/history", response_model=DiagnosticHistoryListResponse)
async def get_diagnostic_history(
    test_type: Optional[str] = None,
    department: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """🎯 사용자의 진단테스트 이력 조회 (학습분석 페이지용)"""
    try:
        # 기본 쿼리 구성
        query = db.query(DiagnosticSession).filter(
            DiagnosticSession.user_id == current_user.id
        )
        
        # 필터 적용
        if test_type:
            query = query.filter(DiagnosticSession.test_type == test_type)
        if department:
            query = query.filter(DiagnosticSession.department == department)
        
        # 전체 개수 조회
        total_count = query.count()
        
        # 페이징 적용하여 세션 목록 조회
        sessions = query.order_by(
            DiagnosticSession.round_number.desc(),
            DiagnosticSession.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        # 응답 데이터 구성
        histories = []
        for session in sessions:
            # AI 분석 데이터 존재 여부 확인
            ai_analysis_exists = db.query(DiagnosticAIAnalysis).filter(
                DiagnosticAIAnalysis.session_id == session.session_id
            ).first() is not None
            
            # 완료율 계산
            if session.status == SessionStatus.COMPLETED:
                completion_rate = 100.0
            elif session.status == SessionStatus.IN_PROGRESS:
                # 답변한 문제 수 기준으로 완료율 계산
                answered_count = db.query(DiagnosticAnswer).filter(
                    DiagnosticAnswer.session_id == session.session_id
                ).count()
                completion_rate = (answered_count / session.total_questions) * 100
            else:
                completion_rate = 0.0
            
            histories.append(DiagnosticHistoryResponse(
                session_id=session.session_id,
                round_number=session.round_number,
                test_type=session.test_type,
                department=session.department,
                total_score=session.total_score,
                correct_answers=session.correct_answers,
                total_questions=session.total_questions,
                completion_rate=round(completion_rate, 1),
                started_at=session.started_at,
                completed_at=session.completed_at,
                total_time_ms=session.total_time_ms,
                status=session.status,
                ai_analysis_available=ai_analysis_exists
            ))
        
        # 완료된 회차 목록 계산
        completed_sessions = db.query(DiagnosticSession).filter(
            and_(
                DiagnosticSession.user_id == current_user.id,
                DiagnosticSession.status == SessionStatus.COMPLETED
            )
        ).all()
        
        completed_rounds = sorted(list(set([s.round_number for s in completed_sessions])))
        
        # 다음 회차 계산
        if completed_rounds:
            next_round = min(max(completed_rounds) + 1, 10)
        else:
            next_round = 1
        
        # 진행 상황 요약
        progress_summary = {
            "total_completed": len(completed_rounds),
            "total_possible": 10,
            "completion_percentage": (len(completed_rounds) / 10) * 100,
            "latest_score": completed_sessions[-1].total_score if completed_sessions else None,
            "average_score": sum([s.total_score for s in completed_sessions if s.total_score]) / len(completed_sessions) if completed_sessions else None,
            "improvement_trend": "상승" if len(completed_sessions) >= 2 and completed_sessions[-1].total_score > completed_sessions[-2].total_score else "유지"
        }
        
        return DiagnosticHistoryListResponse(
            histories=histories,
            total_count=total_count,
            completed_rounds=completed_rounds,
            next_round=next_round,
            progress_summary=progress_summary
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"진단테스트 이력 조회 실패: {str(e)}"
        )


@router.get("/sessions/{session_id}/analysis")
async def get_session_analysis(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """🎯 특정 세션의 상세 분석 데이터 조회 (학습분석 페이지용)"""
    try:
        # 세션 유효성 검증
        session = db.query(DiagnosticSession).filter(
            and_(
                DiagnosticSession.session_id == session_id,
                DiagnosticSession.user_id == current_user.id
            )
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        # AI 분석 데이터 조회
        ai_analysis = db.query(DiagnosticAIAnalysis).filter(
            DiagnosticAIAnalysis.session_id == session_id
        ).first()
        
        # 답변 데이터 조회
        answers = db.query(DiagnosticAnswer).filter(
            DiagnosticAnswer.session_id == session_id
        ).order_by(DiagnosticAnswer.question_number).all()
        
        # 응답 데이터 구성
        analysis_data = {
            "session_info": {
                "session_id": session.session_id,
                "round_number": session.round_number,
                "test_type": session.test_type,
                "department": session.department,
                "total_score": session.total_score,
                "correct_answers": session.correct_answers,
                "total_questions": session.total_questions,
                "total_time_ms": session.total_time_ms,
                "started_at": session.started_at,
                "completed_at": session.completed_at,
                "status": session.status
            },
            "ai_analysis": ai_analysis.analysis_data if ai_analysis else None,
            "detailed_answers": [
                {
                    "question_id": answer.question_id,
                    "question_number": answer.question_number,
                    "selected_answer": answer.selected_answer,
                    "correct_answer": answer.correct_answer,
                    "is_correct": answer.is_correct,
                    "time_spent_ms": answer.time_spent_ms,
                    "difficulty_level": answer.difficulty_level,
                    "domain": answer.domain,
                    "question_type": answer.question_type
                }
                for answer in answers
            ]
        }
        
        return analysis_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"세션 분석 조회 실패: {str(e)}"
        ) 