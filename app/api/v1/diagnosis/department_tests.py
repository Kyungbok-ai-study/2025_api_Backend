"""
학과별 진단테스트 사용자 API

사용자의 학과에 따른 맞춤형 진단테스트 제공
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.db.database import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.services.department_diagnosis_service import (
    DepartmentDiagnosisService,
    get_user_available_tests,
    get_user_recommended_tests,
    start_user_diagnosis_session
)
from app.models.unified_diagnosis import DiagnosisTest, DiagnosisSession

router = APIRouter()

@router.get("/my-tests")
async def get_my_available_tests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    내가 이용할 수 있는 진단테스트 목록 조회
    
    **사용자의 학과에 따라 맞춤형 테스트 목록을 제공합니다:**
    - 소속 학과 전용 테스트
    - 전체 학과 대상 테스트  
    - 관련 과목 영역 테스트
    """
    try:
        available_tests = get_user_available_tests(db, current_user)
        
        # 사용자 학과 정보
        user_department = current_user.profile_info.get('department', '미분류') if current_user.profile_info else '미분류'
        
        return {
            "status": "success",
            "user_department": user_department,
            "total_available": len(available_tests),
            "tests": available_tests,
            "message": f"{user_department} 학과 학생을 위한 맞춤형 진단테스트 목록입니다."
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"사용 가능한 테스트 조회 실패: {str(e)}"
        )

@router.get("/recommended")
async def get_recommended_tests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    나를 위한 추천 진단테스트
    
    **개인별 맞춤 추천:**
    - 미완료 테스트 (최우선)
    - 학과 필수 테스트
    - 실력 향상 추천 테스트
    - 도전 과제 테스트
    """
    try:
        recommended_tests = get_user_recommended_tests(db, current_user)
        
        # 추천 이유별로 그룹화
        recommendations_by_reason = {}
        for test in recommended_tests:
            reason = test.get("recommendation_reason", "일반 추천")
            if reason not in recommendations_by_reason:
                recommendations_by_reason[reason] = []
            recommendations_by_reason[reason].append(test)
        
        return {
            "status": "success",
            "total_recommendations": len(recommended_tests),
            "recommendations": recommended_tests,
            "grouped_by_reason": recommendations_by_reason,
            "message": "개인 학습 이력을 바탕으로 한 맞춤형 추천입니다."
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"추천 테스트 조회 실패: {str(e)}"
        )

@router.get("/departments/{department}")
async def get_department_specific_tests(
    department: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    특정 학과의 진단테스트 목록 조회
    
    **다른 학과의 테스트도 참고용으로 조회 가능**
    """
    try:
        service = DepartmentDiagnosisService(db)
        department_tests = service.get_department_specific_tests(department)
        
        # 사용자의 접근 권한 확인
        user_department = current_user.profile_info.get('department', '미분류') if current_user.profile_info else '미분류'
        is_own_department = user_department == department
        
        return {
            "status": "success",
            "department": department,
            "is_own_department": is_own_department,
            "test_count": len(department_tests),
            "tests": department_tests,
            "access_note": "본인 학과가 아닌 경우 참고용으로만 조회됩니다." if not is_own_department else None
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"학과별 테스트 조회 실패: {str(e)}"
        )

@router.post("/tests/{test_id}/start")
async def start_diagnosis_test(
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    진단테스트 시작
    
    **학과별 접근 권한 검증 후 세션 생성**
    """
    try:
        session_info = start_user_diagnosis_session(db, current_user, test_id)
        
        return {
            "status": "success",
            "session": session_info,
            "message": "진단테스트 세션이 생성되었습니다.",
            "instructions": {
                "time_limit": f"{session_info.get('time_limit_minutes', 60)}분",
                "total_questions": f"{session_info.get('total_questions', 0)}문제",
                "attempt_number": f"{session_info.get('attempt_number', 1)}번째 시도",
                "notes": [
                    "제한 시간 내에 모든 문제를 푸시기 바랍니다.",
                    "중간에 나가면 진행상황이 저장됩니다.",
                    "최대 시도 횟수를 확인하세요."
                ]
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"진단테스트 시작 실패: {str(e)}"
        )

@router.get("/sessions/{session_id}")
async def get_diagnosis_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """진단 세션 정보 조회"""
    try:
        session = db.query(DiagnosisSession).filter(
            DiagnosisSession.id == session_id,
            DiagnosisSession.user_id == current_user.id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        # 세션 상세 정보 구성
        session_info = {
            "session_id": session.id,
            "test_id": session.test_id,
            "test_title": session.test.title if session.test else None,
            "department": session.test.department if session.test else None,
            "subject_area": session.test.subject_area if session.test else None,
            "status": session.status,
            "attempt_number": session.attempt_number,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
            "time_remaining": self._calculate_remaining_time(session),
            "progress": {
                "total_questions": session.test.total_questions if session.test else 0,
                "answered_questions": len(session.responses) if session.responses else 0,
                "percentage": self._calculate_progress_percentage(session)
            },
            "scores": {
                "raw_score": session.raw_score,
                "percentage_score": session.percentage_score,
                "scaled_score": session.scaled_score
            } if session.status == "completed" else None
        }
        
        return {
            "status": "success",
            "session": session_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"세션 조회 실패: {str(e)}"
        )

@router.get("/my-history")
async def get_my_diagnosis_history(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, regex="^(completed|in_progress|not_started|expired|abandoned)$"),
    department: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    내 진단테스트 이력 조회
    
    **필터 옵션:**
    - status: 세션 상태별 필터링
    - department: 학과별 필터링  
    - limit/offset: 페이징
    """
    try:
        # 기본 쿼리
        query = db.query(DiagnosisSession).filter(
            DiagnosisSession.user_id == current_user.id
        )
        
        # 상태 필터
        if status:
            query = query.filter(DiagnosisSession.status == status)
        
        # 학과 필터
        if department:
            query = query.join(DiagnosisTest).filter(
                DiagnosisTest.department == department
            )
        
        # 총 개수
        total_count = query.count()
        
        # 페이징 및 정렬
        sessions = query.order_by(
            DiagnosisSession.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        # 이력 정보 구성
        history_list = []
        for session in sessions:
            history_item = {
                "session_id": session.id,
                "test_title": session.test.title if session.test else "Unknown Test",
                "department": session.test.department if session.test else None,
                "subject_area": session.test.subject_area if session.test else None,
                "status": session.status,
                "attempt_number": session.attempt_number,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "percentage_score": session.percentage_score,
                "time_spent": session.total_time_spent,
                "questions_answered": len(session.responses) if session.responses else 0
            }
            history_list.append(history_item)
        
        # 통계 정보
        stats = self._calculate_user_stats(current_user.id, db)
        
        return {
            "status": "success",
            "total_count": total_count,
            "page_info": {
                "limit": limit,
                "offset": offset,
                "has_next": (offset + limit) < total_count
            },
            "history": history_list,
            "statistics": stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"진단 이력 조회 실패: {str(e)}"
        )

@router.get("/my-performance")
async def get_my_performance_analysis(
    days: int = Query(30, ge=7, le=365, description="분석 기간 (일)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    내 성과 분석
    
    **개인 성과 지표:**
    - 점수 추이
    - 학과별/과목별 성과
    - 시간별 학습 패턴
    - 강약점 분석
    """
    try:
        from datetime import timedelta
        
        # 분석 기간 설정
        start_date = datetime.now() - timedelta(days=days)
        
        # 사용자의 세션 데이터
        sessions = db.query(DiagnosisSession).filter(
            DiagnosisSession.user_id == current_user.id,
            DiagnosisSession.created_at >= start_date,
            DiagnosisSession.status == "completed"
        ).order_by(DiagnosisSession.created_at).all()
        
        if not sessions:
            return {
                "status": "success",
                "message": "분석 기간 내 완료된 진단테스트가 없습니다.",
                "analysis_period": f"{days}일",
                "sessions_analyzed": 0
            }
        
        # 성과 분석
        performance_analysis = {
            "analysis_period": f"{days}일",
            "sessions_analyzed": len(sessions),
            "overall_performance": self._analyze_overall_performance(sessions),
            "subject_performance": self._analyze_subject_performance_user(sessions),
            "time_trends": self._analyze_time_trends_user(sessions),
            "department_comparison": self._get_department_comparison_for_user(current_user, db),
            "strengths_weaknesses": self._identify_strengths_weaknesses(sessions),
            "recommendations": self._generate_personal_recommendations(sessions, current_user, db)
        }
        
        return {
            "status": "success",
            "performance_analysis": performance_analysis,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"성과 분석 실패: {str(e)}"
        )

# 유틸리티 함수들
def _calculate_remaining_time(session: DiagnosisSession) -> Optional[str]:
    """남은 시간 계산"""
    if not session.expires_at or session.status in ["completed", "expired", "abandoned"]:
        return None
    
    remaining = session.expires_at - datetime.now()
    if remaining.total_seconds() <= 0:
        return "만료됨"
    
    minutes = int(remaining.total_seconds() // 60)
    seconds = int(remaining.total_seconds() % 60)
    
    if minutes > 0:
        return f"{minutes}분 {seconds}초"
    else:
        return f"{seconds}초"

def _calculate_progress_percentage(session: DiagnosisSession) -> float:
    """진행률 계산"""
    if not session.test or not session.responses:
        return 0.0
    
    total_questions = session.test.total_questions
    answered_questions = len(session.responses)
    
    if total_questions == 0:
        return 0.0
    
    return round((answered_questions / total_questions) * 100, 1)

def _calculate_user_stats(user_id: int, db: Session) -> Dict[str, Any]:
    """사용자 통계 계산"""
    try:
        # 전체 세션 통계
        all_sessions = db.query(DiagnosisSession).filter(
            DiagnosisSession.user_id == user_id
        ).all()
        
        completed_sessions = [s for s in all_sessions if s.status == "completed"]
        
        if not completed_sessions:
            return {
                "total_attempts": len(all_sessions),
                "completed_tests": 0,
                "average_score": 0,
                "best_score": 0,
                "completion_rate": 0
            }
        
        scores = [s.percentage_score for s in completed_sessions if s.percentage_score is not None]
        
        return {
            "total_attempts": len(all_sessions),
            "completed_tests": len(completed_sessions),
            "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "best_score": max(scores) if scores else 0,
            "completion_rate": round(len(completed_sessions) / len(all_sessions) * 100, 1) if all_sessions else 0,
            "departments_tested": len(set([s.test.department for s in completed_sessions if s.test])),
            "subjects_tested": len(set([s.test.subject_area for s in completed_sessions if s.test]))
        }
        
    except Exception:
        return {}

def _analyze_overall_performance(sessions: List[DiagnosisSession]) -> Dict[str, Any]:
    """전체 성과 분석"""
    scores = [s.percentage_score for s in sessions if s.percentage_score is not None]
    
    if not scores:
        return {}
    
    return {
        "average_score": round(sum(scores) / len(scores), 1),
        "best_score": max(scores),
        "worst_score": min(scores),
        "score_range": max(scores) - min(scores),
        "improvement_trend": _calculate_improvement_trend(scores),
        "consistency": _calculate_consistency(scores)
    }

def _analyze_subject_performance_user(sessions: List[DiagnosisSession]) -> Dict[str, Any]:
    """과목별 성과 분석"""
    subject_stats = {}
    
    for session in sessions:
        if not session.test or session.percentage_score is None:
            continue
        
        subject = session.test.subject_area
        if subject not in subject_stats:
            subject_stats[subject] = {
                "scores": [],
                "attempts": 0
            }
        
        subject_stats[subject]["scores"].append(session.percentage_score)
        subject_stats[subject]["attempts"] += 1
    
    # 평균 계산
    for subject, stats in subject_stats.items():
        scores = stats["scores"]
        stats["average_score"] = round(sum(scores) / len(scores), 1)
        stats["best_score"] = max(scores)
        stats["attempts"] = len(scores)
        del stats["scores"]  # 개별 점수는 제거
    
    return subject_stats

def _analyze_time_trends_user(sessions: List[DiagnosisSession]) -> Dict[str, Any]:
    """시간별 추이 분석"""
    if len(sessions) < 2:
        return {}
    
    # 날짜별 점수 그룹화
    daily_scores = {}
    for session in sessions:
        if session.percentage_score is None or not session.completed_at:
            continue
        
        date_key = session.completed_at.date().isoformat()
        if date_key not in daily_scores:
            daily_scores[date_key] = []
        daily_scores[date_key].append(session.percentage_score)
    
    # 일별 평균 계산
    daily_averages = {}
    for date, scores in daily_scores.items():
        daily_averages[date] = round(sum(scores) / len(scores), 1)
    
    return {
        "daily_averages": daily_averages,
        "trend_direction": _determine_trend_direction(list(daily_averages.values())),
        "most_active_period": _find_most_active_period(daily_scores)
    }

def _get_department_comparison_for_user(user: User, db: Session) -> Dict[str, Any]:
    """학과 내 비교"""
    try:
        user_department = user.profile_info.get('department', '미분류') if user.profile_info else '미분류'
        
        # 같은 학과 학생들의 평균 성과
        dept_users = db.query(User).filter(
            User.profile_info['department'].astext == user_department
        ).all()
        
        if len(dept_users) <= 1:
            return {"message": "비교할 수 있는 같은 학과 학생이 없습니다."}
        
        dept_user_ids = [u.id for u in dept_users if u.id != user.id]
        
        dept_sessions = db.query(DiagnosisSession).filter(
            DiagnosisSession.user_id.in_(dept_user_ids),
            DiagnosisSession.status == "completed"
        ).all()
        
        if not dept_sessions:
            return {"message": "학과 내 비교 데이터가 없습니다."}
        
        dept_scores = [s.percentage_score for s in dept_sessions if s.percentage_score is not None]
        dept_average = sum(dept_scores) / len(dept_scores) if dept_scores else 0
        
        # 사용자 평균
        user_sessions = db.query(DiagnosisSession).filter(
            DiagnosisSession.user_id == user.id,
            DiagnosisSession.status == "completed"
        ).all()
        
        user_scores = [s.percentage_score for s in user_sessions if s.percentage_score is not None]
        user_average = sum(user_scores) / len(user_scores) if user_scores else 0
        
        return {
            "user_average": round(user_average, 1),
            "department_average": round(dept_average, 1),
            "comparison": "평균 이상" if user_average > dept_average else "평균 이하",
            "percentile": _calculate_percentile(user_average, dept_scores)
        }
        
    except Exception:
        return {"message": "학과 비교 데이터를 가져올 수 없습니다."}

def _identify_strengths_weaknesses(sessions: List[DiagnosisSession]) -> Dict[str, Any]:
    """강약점 분석"""
    subject_performance = _analyze_subject_performance_user(sessions)
    
    if not subject_performance:
        return {}
    
    # 성과 순으로 정렬
    sorted_subjects = sorted(
        subject_performance.items(),
        key=lambda x: x[1]["average_score"],
        reverse=True
    )
    
    strengths = sorted_subjects[:2]  # 상위 2개
    weaknesses = sorted_subjects[-2:]  # 하위 2개
    
    return {
        "strengths": [{"subject": subj, "score": data["average_score"]} for subj, data in strengths],
        "weaknesses": [{"subject": subj, "score": data["average_score"]} for subj, data in reversed(weaknesses)]
    }

def _generate_personal_recommendations(sessions: List[DiagnosisSession], user: User, db: Session) -> List[str]:
    """개인 맞춤 추천사항"""
    recommendations = []
    
    # 점수 기반 추천
    scores = [s.percentage_score for s in sessions if s.percentage_score is not None]
    if scores:
        avg_score = sum(scores) / len(scores)
        
        if avg_score < 60:
            recommendations.append("기초 개념 복습이 필요합니다.")
        elif avg_score < 80:
            recommendations.append("핵심 개념 정리와 응용 문제 연습을 권장합니다.")
        else:
            recommendations.append("심화 학습과 도전 과제에 도전해보세요.")
    
    # 일관성 기반 추천
    if scores and _calculate_consistency(scores) < 0.8:
        recommendations.append("꾸준한 학습으로 일관성을 높이세요.")
    
    # 과목별 추천
    subject_performance = _analyze_subject_performance_user(sessions)
    weak_subjects = [subj for subj, data in subject_performance.items() if data["average_score"] < 70]
    
    if weak_subjects:
        recommendations.append(f"다음 과목 집중 학습 권장: {', '.join(weak_subjects)}")
    
    return recommendations

# 헬퍼 함수들
def _calculate_improvement_trend(scores: List[float]) -> str:
    """개선 추세 계산"""
    if len(scores) < 2:
        return "분석 불가"
    
    first_half = scores[:len(scores)//2]
    second_half = scores[len(scores)//2:]
    
    first_avg = sum(first_half) / len(first_half)
    second_avg = sum(second_half) / len(second_half)
    
    diff = second_avg - first_avg
    
    if diff > 5:
        return "상승"
    elif diff < -5:
        return "하락"
    else:
        return "안정"

def _calculate_consistency(scores: List[float]) -> float:
    """일관성 점수 계산 (0-1)"""
    if len(scores) < 2:
        return 1.0
    
    import statistics
    
    mean = statistics.mean(scores)
    stdev = statistics.stdev(scores)
    
    # 변동계수의 역수로 일관성 계산
    cv = stdev / mean if mean > 0 else 1
    consistency = max(0, 1 - cv)
    
    return round(consistency, 2)

def _determine_trend_direction(values: List[float]) -> str:
    """추세 방향 결정"""
    if len(values) < 2:
        return "분석 불가"
    
    increasing = sum(1 for i in range(1, len(values)) if values[i] > values[i-1])
    decreasing = sum(1 for i in range(1, len(values)) if values[i] < values[i-1])
    
    if increasing > decreasing:
        return "상승"
    elif decreasing > increasing:
        return "하락"
    else:
        return "안정"

def _find_most_active_period(daily_scores: Dict[str, List[float]]) -> str:
    """가장 활발한 시기 찾기"""
    if not daily_scores:
        return "데이터 없음"
    
    most_active_date = max(daily_scores.keys(), key=lambda x: len(daily_scores[x]))
    return most_active_date

def _calculate_percentile(user_score: float, all_scores: List[float]) -> int:
    """백분위 계산"""
    if not all_scores:
        return 50
    
    below_count = sum(1 for score in all_scores if score < user_score)
    percentile = int((below_count / len(all_scores)) * 100)
    
    return percentile 