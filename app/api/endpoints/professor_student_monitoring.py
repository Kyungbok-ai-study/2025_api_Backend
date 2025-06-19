"""
교수님의 학생 학습 모니터링 및 분석 API
실제 작동하는 학생 학습 추적 시스템
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta

from app.db.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.unified_diagnosis import DiagnosisSession, DiagnosisResponse
from app.models.professor_student_match import ProfessorStudentMatch, StudentDiagnosisAlert
from app.services.professor_student_service import professor_student_service
from app.services.diagnosis_progress_service import DiagnosisProgressService

router = APIRouter(prefix="/professor/student-monitoring", tags=["professor-student-monitoring"])
logger = logging.getLogger(__name__)

@router.get("/dashboard")
async def get_student_monitoring_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """교수님의 학생 모니터링 대시보드 - 실제 데이터"""
    
    if current_user.role != "professor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="교수 권한이 필요합니다"
        )
    
    try:
        # 실제 학생 모니터링 데이터 조회
        monitoring_data = await professor_student_service.get_student_monitoring_dashboard(
            db, current_user.id
        )
        
        # 추가 실시간 통계
        additional_stats = await get_real_time_student_stats(db, current_user.id)
        
        return {
            "success": True,
            "message": "학생 모니터링 대시보드 조회 성공",
            "professor_info": {
                "id": current_user.id,
                "name": current_user.name,
                "school": current_user.school,
                "department": current_user.department
            },
            "dashboard_data": monitoring_data,
            "real_time_stats": additional_stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"학생 모니터링 대시보드 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"대시보드 조회 실패: {str(e)}"
        )

@router.get("/students/{student_id}/detailed-analysis")
async def get_student_detailed_analysis(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """특정 학생의 상세 학습 분석"""
    
    if current_user.role != "professor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="교수 권한이 필요합니다"
        )
    
    try:
        # 학생 정보 조회
        student = db.query(User).filter(User.id == student_id).first()
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="학생 정보를 찾을 수 없습니다"
            )
        
        # 교수와 학생이 같은 학과인지 확인
        if current_user.department != student.department:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"본인 학과({current_user.department}) 학생만 모니터링할 수 있습니다."
            )
        
        # 학생의 진단테스트 세션들 조회
        diagnosis_sessions = db.query(DiagnosisSession).filter(
            DiagnosisSession.user_id == student_id
        ).order_by(DiagnosisSession.created_at.desc()).all()
        
        # 상세 분석 데이터 생성
        analysis_data = await generate_student_detailed_analysis(
            db, student, diagnosis_sessions
        )
        
        return {
            "success": True,
            "message": f"{student.name} 학생 상세 분석 완료",
            "student_info": {
                "id": student.id,
                "name": student.name,
                "school": student.school,
                "department": student.department,
                "email": student.email
            },
            "analysis_data": analysis_data,
            "professor_notes": {
                "concern_level": determine_concern_level(analysis_data),
                "recommendations": generate_recommendations(analysis_data),
                "last_updated": datetime.now().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"학생 상세 분석 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"학생 분석 실패: {str(e)}"
        )

@router.get("/students/{student_id}/diagnosis-history")
async def get_student_diagnosis_history(
    student_id: int,
    department: Optional[str] = Query(None, description="특정 학과 필터"),
    limit: int = Query(10, description="조회할 기록 수"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """학생의 진단테스트 이력 조회"""
    
    if current_user.role != "professor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="교수 권한이 필요합니다"
        )
    
    try:
        # 학생 정보 조회 및 학과 확인
        student = db.query(User).filter(User.id == student_id).first()
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="학생 정보를 찾을 수 없습니다"
            )
        
        # 교수와 학생이 같은 학과인지 확인
        if current_user.department != student.department:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"본인 학과({current_user.department}) 학생만 조회할 수 있습니다."
            )
        
        # 진단 진행 서비스를 통해 이력 조회
        progress_service = DiagnosisProgressService(db)
        history = await progress_service.get_user_diagnosis_history(
            user_id=student_id,
            department=department,
            limit=limit
        )
        
        return {
            "success": True,
            "message": "학생 진단테스트 이력 조회 성공",
            "student_id": student_id,
            "department_filter": department,
            "history": history,
            "total_records": len(history)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"학생 진단 이력 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"진단 이력 조회 실패: {str(e)}"
        )

@router.get("/students/{student_id}/learning-patterns")
async def get_student_learning_patterns(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """학생의 학습 패턴 분석"""
    
    if current_user.role != "professor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="교수 권한이 필요합니다"
        )
    
    try:
        # 매칭 확인
        match = db.query(ProfessorStudentMatch).filter(
            ProfessorStudentMatch.professor_id == current_user.id,
            ProfessorStudentMatch.student_id == student_id,
            ProfessorStudentMatch.match_status == "approved"
        ).first()
        
        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="매칭되지 않은 학생입니다"
            )
        
        # 학습 패턴 분석
        patterns = await analyze_student_learning_patterns(db, student_id)
        
        return {
            "success": True,
            "message": "학생 학습 패턴 분석 완료",
            "student_id": student_id,
            "learning_patterns": patterns,
            "analysis_date": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"학습 패턴 분석 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"학습 패턴 분석 실패: {str(e)}"
        )

@router.post("/students/{student_id}/add-note")
async def add_student_note(
    student_id: int,
    note_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """학생에 대한 교수 노트 추가"""
    
    if current_user.role != "professor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="교수 권한이 필요합니다"
        )
    
    try:
        # 매칭 확인
        match = db.query(ProfessorStudentMatch).filter(
            ProfessorStudentMatch.professor_id == current_user.id,
            ProfessorStudentMatch.student_id == student_id,
            ProfessorStudentMatch.match_status == "approved"
        ).first()
        
        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="매칭되지 않은 학생입니다"
            )
        
        # 알림 생성 (교수 노트)
        alert = StudentDiagnosisAlert(
            professor_id=current_user.id,
            student_id=student_id,
            alert_type="professor_note",
            alert_data={
                "note_content": note_data.get("content", ""),
                "concern_level": note_data.get("concern_level", "normal"),
                "tags": note_data.get("tags", []),
                "recommendations": note_data.get("recommendations", [])
            },
            priority="normal",
            is_read=True  # 교수가 작성한 것이므로 읽음 처리
        )
        
        db.add(alert)
        db.commit()
        
        return {
            "success": True,
            "message": "학생 노트가 추가되었습니다",
            "note_id": alert.id,
            "created_at": alert.created_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"학생 노트 추가 실패: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"노트 추가 실패: {str(e)}"
        )

@router.get("/department-statistics")
async def get_department_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """교수 학과의 전체 통계"""
    
    if current_user.role != "professor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="교수 권한이 필요합니다"
        )
    
    try:
        # 같은 학과 학생들의 통계
        department_stats = await get_department_wide_statistics(
            db, current_user.school, current_user.department
        )
        
        return {
            "success": True,
            "message": "학과 통계 조회 성공",
            "professor_department": current_user.department,
            "professor_school": current_user.school,
            "statistics": department_stats,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"학과 통계 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"학과 통계 조회 실패: {str(e)}"
        )

# ===== 헬퍼 함수들 =====

async def get_real_time_student_stats(db: Session, professor_id: int) -> Dict[str, Any]:
    """실시간 학생 통계 조회"""
    
    # 승인된 학생들 조회
    approved_students = db.query(ProfessorStudentMatch).filter(
        ProfessorStudentMatch.professor_id == professor_id,
        ProfessorStudentMatch.match_status == "approved"
    ).all()
    
    student_ids = [match.student_id for match in approved_students]
    
    if not student_ids:
        return {
            "total_students": 0,
            "active_today": 0,
            "night_active_students": 0,
            "average_score": 0,
            "recent_activities": []
        }
    
    # 오늘 활동한 학생 수
    today = datetime.now().date()
    active_today = db.query(DiagnosisSession).filter(
        DiagnosisSession.user_id.in_(student_ids),
        DiagnosisSession.created_at >= today
    ).distinct(DiagnosisSession.user_id).count()
    
    # 새벽 시간 (23시-6시) 활동 학생들
    night_sessions = db.query(DiagnosisSession).filter(
        DiagnosisSession.user_id.in_(student_ids),
        DiagnosisSession.created_at >= datetime.now() - timedelta(days=7)
    ).all()
    
    night_active_students = set()
    for session in night_sessions:
        hour = session.created_at.hour
        if hour >= 23 or hour <= 6:
            night_active_students.add(session.user_id)
    
    # 평균 점수 계산
    completed_sessions = db.query(DiagnosisSession).filter(
        DiagnosisSession.user_id.in_(student_ids),
        DiagnosisSession.status == "completed",
        DiagnosisSession.percentage_score.isnot(None)
    ).all()
    
    avg_score = 0
    if completed_sessions:
        avg_score = sum(s.percentage_score for s in completed_sessions) / len(completed_sessions)
    
    # 최근 활동들
    recent_activities = db.query(DiagnosisSession).filter(
        DiagnosisSession.user_id.in_(student_ids)
    ).order_by(DiagnosisSession.created_at.desc()).limit(10).all()
    
    return {
        "total_students": len(student_ids),
        "active_today": active_today,
        "night_active_students": len(night_active_students),
        "average_score": round(avg_score, 1),
        "recent_activities": [
            {
                "student_id": activity.user_id,
                "session_id": activity.id,
                "status": activity.status,
                "score": activity.percentage_score,
                "created_at": activity.created_at.isoformat()
            }
            for activity in recent_activities
        ]
    }

async def generate_student_detailed_analysis(
    db: Session, 
    student: User, 
    diagnosis_sessions: List[DiagnosisSession]
) -> Dict[str, Any]:
    """학생 상세 분석 데이터 생성"""
    
    if not diagnosis_sessions:
        return {
            "summary": "진단테스트 기록이 없습니다",
            "total_tests": 0,
            "average_score": 0,
            "learning_trends": [],
            "time_patterns": {},
            "subject_performance": {}
        }
    
    # 기본 통계
    completed_sessions = [s for s in diagnosis_sessions if s.status == "completed"]
    total_tests = len(diagnosis_sessions)
    avg_score = 0
    if completed_sessions:
        scores = [s.percentage_score for s in completed_sessions if s.percentage_score]
        avg_score = sum(scores) / len(scores) if scores else 0
    
    # 시간 패턴 분석
    time_patterns = analyze_time_patterns(diagnosis_sessions)
    
    # 학습 추세
    learning_trends = analyze_learning_trends(completed_sessions)
    
    # 과목별 성과
    subject_performance = analyze_subject_performance(diagnosis_sessions)
    
    return {
        "summary": f"총 {total_tests}회 진단테스트 실시, 평균 {avg_score:.1f}점",
        "total_tests": total_tests,
        "completed_tests": len(completed_sessions),
        "average_score": round(avg_score, 1),
        "best_score": max([s.percentage_score for s in completed_sessions if s.percentage_score], default=0),
        "recent_score": completed_sessions[0].percentage_score if completed_sessions else 0,
        "learning_trends": learning_trends,
        "time_patterns": time_patterns,
        "subject_performance": subject_performance,
        "activity_summary": {
            "last_activity": diagnosis_sessions[0].created_at.isoformat() if diagnosis_sessions else None,
            "most_active_time": time_patterns.get("most_active_hour", "정보 없음"),
            "night_activity_concern": time_patterns.get("night_activity_rate", 0) > 0.3
        }
    }

def analyze_time_patterns(sessions: List[DiagnosisSession]) -> Dict[str, Any]:
    """시간 패턴 분석"""
    
    if not sessions:
        return {}
    
    hour_counts = {}
    night_count = 0
    
    for session in sessions:
        hour = session.created_at.hour
        hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        if hour >= 23 or hour <= 6:
            night_count += 1
    
    most_active_hour = max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else 12
    night_activity_rate = night_count / len(sessions) if sessions else 0
    
    return {
        "most_active_hour": f"{most_active_hour}시",
        "night_activity_rate": round(night_activity_rate, 2),
        "hour_distribution": hour_counts,
        "night_sessions_count": night_count
    }

def analyze_learning_trends(sessions: List[DiagnosisSession]) -> List[Dict[str, Any]]:
    """학습 추세 분석"""
    
    if not sessions:
        return []
    
    # 최근 10개 세션의 점수 추이
    recent_sessions = sorted(sessions, key=lambda x: x.created_at)[-10:]
    trends = []
    
    for i, session in enumerate(recent_sessions):
        if session.percentage_score is not None:
            trends.append({
                "test_number": i + 1,
                "score": session.percentage_score,
                "date": session.created_at.strftime("%m/%d"),
                "department": getattr(session, 'department', '알 수 없음')
            })
    
    return trends

def analyze_subject_performance(sessions: List[DiagnosisSession]) -> Dict[str, Any]:
    """과목별 성과 분석"""
    
    subject_scores = {}
    
    for session in sessions:
        if session.status == "completed" and session.percentage_score:
            dept = getattr(session, 'department', '기타')
            if dept not in subject_scores:
                subject_scores[dept] = []
            subject_scores[dept].append(session.percentage_score)
    
    # 과목별 평균 계산
    subject_averages = {}
    for subject, scores in subject_scores.items():
        subject_averages[subject] = {
            "average_score": round(sum(scores) / len(scores), 1),
            "test_count": len(scores),
            "best_score": max(scores),
            "recent_score": scores[-1] if scores else 0
        }
    
    return subject_averages

def determine_concern_level(analysis_data: Dict[str, Any]) -> str:
    """관심 수준 결정"""
    
    avg_score = analysis_data.get("average_score", 0)
    night_activity = analysis_data.get("time_patterns", {}).get("night_activity_rate", 0)
    total_tests = analysis_data.get("total_tests", 0)
    
    # 점수가 낮거나, 새벽 활동이 많거나, 테스트 횟수가 적으면 관심 필요
    if avg_score < 60 or night_activity > 0.4 or total_tests < 3:
        return "high"
    elif avg_score < 75 or night_activity > 0.2:
        return "medium"
    else:
        return "low"

def generate_recommendations(analysis_data: Dict[str, Any]) -> List[str]:
    """추천 사항 생성"""
    
    recommendations = []
    
    avg_score = analysis_data.get("average_score", 0)
    night_activity = analysis_data.get("time_patterns", {}).get("night_activity_rate", 0)
    total_tests = analysis_data.get("total_tests", 0)
    
    if avg_score < 60:
        recommendations.append("기초 학습 보충이 필요합니다")
        recommendations.append("1:1 상담을 통한 학습 계획 수립을 권장합니다")
    
    if night_activity > 0.3:
        recommendations.append("새벽 시간 학습 패턴에 대한 상담이 필요합니다")
        recommendations.append("규칙적인 학습 시간 관리 지도를 권장합니다")
    
    if total_tests < 5:
        recommendations.append("더 많은 진단테스트 참여를 독려해주세요")
    
    if not recommendations:
        recommendations.append("현재 학습 상태가 양호합니다")
        recommendations.append("지속적인 학습 동기 부여를 제공해주세요")
    
    return recommendations

async def analyze_student_learning_patterns(db: Session, student_id: int) -> Dict[str, Any]:
    """학생 학습 패턴 상세 분석"""
    
    # 학생의 모든 진단테스트 세션 조회
    sessions = db.query(DiagnosisSession).filter(
        DiagnosisSession.user_id == student_id
    ).order_by(DiagnosisSession.created_at.desc()).all()
    
    if not sessions:
        return {
            "pattern_summary": "학습 데이터가 충분하지 않습니다",
            "time_patterns": {},
            "performance_patterns": {},
            "behavioral_insights": []
        }
    
    # 시간 패턴 분석
    time_patterns = analyze_detailed_time_patterns(sessions)
    
    # 성과 패턴 분석
    performance_patterns = analyze_performance_patterns(sessions)
    
    # 행동 패턴 인사이트
    behavioral_insights = generate_behavioral_insights(sessions, time_patterns, performance_patterns)
    
    return {
        "pattern_summary": f"{len(sessions)}개 세션 분석 완료",
        "time_patterns": time_patterns,
        "performance_patterns": performance_patterns,
        "behavioral_insights": behavioral_insights,
        "analysis_period": {
            "start_date": sessions[-1].created_at.isoformat() if sessions else None,
            "end_date": sessions[0].created_at.isoformat() if sessions else None,
            "total_sessions": len(sessions)
        }
    }

def analyze_detailed_time_patterns(sessions: List[DiagnosisSession]) -> Dict[str, Any]:
    """상세 시간 패턴 분석"""
    
    # 요일별 활동
    weekday_counts = {i: 0 for i in range(7)}  # 0=월요일, 6=일요일
    
    # 시간대별 활동
    hour_counts = {i: 0 for i in range(24)}
    
    # 연속 학습 패턴
    consecutive_days = 0
    max_consecutive = 0
    last_date = None
    
    for session in sorted(sessions, key=lambda x: x.created_at):
        # 요일 분석
        weekday = session.created_at.weekday()
        weekday_counts[weekday] += 1
        
        # 시간 분석
        hour = session.created_at.hour
        hour_counts[hour] += 1
        
        # 연속 학습일 분석
        current_date = session.created_at.date()
        if last_date and (current_date - last_date).days == 1:
            consecutive_days += 1
        else:
            max_consecutive = max(max_consecutive, consecutive_days)
            consecutive_days = 1
        last_date = current_date
    
    max_consecutive = max(max_consecutive, consecutive_days)
    
    # 가장 활발한 시간대
    peak_hour = max(hour_counts.items(), key=lambda x: x[1])[0]
    peak_weekday = max(weekday_counts.items(), key=lambda x: x[1])[0]
    
    weekday_names = ["월", "화", "수", "목", "금", "토", "일"]
    
    return {
        "peak_hour": f"{peak_hour}시",
        "peak_weekday": weekday_names[peak_weekday],
        "max_consecutive_days": max_consecutive,
        "night_activity_rate": sum(hour_counts[h] for h in [23, 0, 1, 2, 3, 4, 5, 6]) / len(sessions),
        "weekend_activity_rate": (weekday_counts[5] + weekday_counts[6]) / len(sessions),
        "hour_distribution": hour_counts,
        "weekday_distribution": {weekday_names[k]: v for k, v in weekday_counts.items()}
    }

def analyze_performance_patterns(sessions: List[DiagnosisSession]) -> Dict[str, Any]:
    """성과 패턴 분석"""
    
    completed_sessions = [s for s in sessions if s.status == "completed" and s.percentage_score is not None]
    
    if not completed_sessions:
        return {"insufficient_data": True}
    
    scores = [s.percentage_score for s in completed_sessions]
    
    # 성과 추이
    if len(scores) >= 3:
        recent_trend = "improving" if scores[0] > scores[-1] else "declining" if scores[0] < scores[-1] else "stable"
    else:
        recent_trend = "insufficient_data"
    
    # 일관성 분석 (표준편차)
    import statistics
    score_std = statistics.stdev(scores) if len(scores) > 1 else 0
    consistency = "high" if score_std < 10 else "medium" if score_std < 20 else "low"
    
    return {
        "average_score": round(sum(scores) / len(scores), 1),
        "best_score": max(scores),
        "worst_score": min(scores),
        "score_range": max(scores) - min(scores),
        "recent_trend": recent_trend,
        "consistency": consistency,
        "score_std": round(score_std, 1),
        "improvement_rate": calculate_improvement_rate(scores)
    }

def calculate_improvement_rate(scores: List[float]) -> float:
    """개선율 계산"""
    if len(scores) < 2:
        return 0
    
    # 첫 번째와 마지막 점수 비교
    first_score = scores[-1]  # 가장 오래된 점수
    last_score = scores[0]    # 가장 최근 점수
    
    if first_score == 0:
        return 0
    
    return round(((last_score - first_score) / first_score) * 100, 1)

def generate_behavioral_insights(
    sessions: List[DiagnosisSession], 
    time_patterns: Dict[str, Any], 
    performance_patterns: Dict[str, Any]
) -> List[str]:
    """행동 패턴 인사이트 생성"""
    
    insights = []
    
    # 시간 패턴 기반 인사이트
    night_rate = time_patterns.get("night_activity_rate", 0)
    if night_rate > 0.3:
        insights.append(f"새벽 시간대 학습 빈도가 높습니다 ({night_rate:.1%})")
    
    weekend_rate = time_patterns.get("weekend_activity_rate", 0)
    if weekend_rate > 0.4:
        insights.append(f"주말 학습 활동이 활발합니다 ({weekend_rate:.1%})")
    
    consecutive_days = time_patterns.get("max_consecutive_days", 0)
    if consecutive_days >= 7:
        insights.append(f"최대 {consecutive_days}일 연속 학습 기록이 있습니다")
    
    # 성과 패턴 기반 인사이트
    if not performance_patterns.get("insufficient_data"):
        trend = performance_patterns.get("recent_trend", "")
        if trend == "improving":
            insights.append("최근 성과가 향상되고 있습니다")
        elif trend == "declining":
            insights.append("최근 성과가 하락하는 경향을 보입니다")
        
        consistency = performance_patterns.get("consistency", "")
        if consistency == "high":
            insights.append("일관된 성과를 보이고 있습니다")
        elif consistency == "low":
            insights.append("성과 편차가 큰 편입니다")
    
    # 전체 활동 패턴
    total_sessions = len(sessions)
    if total_sessions >= 20:
        insights.append("매우 활발한 학습 활동을 보이고 있습니다")
    elif total_sessions >= 10:
        insights.append("꾸준한 학습 활동을 보이고 있습니다")
    elif total_sessions < 5:
        insights.append("더 많은 학습 활동 참여가 필요합니다")
    
    return insights if insights else ["분석할 수 있는 특별한 패턴이 발견되지 않았습니다"]

async def get_department_wide_statistics(
    db: Session, 
    school: str, 
    department: str
) -> Dict[str, Any]:
    """학과 전체 통계"""
    
    # 같은 학교, 같은 학과 학생들 조회
    department_students = db.query(User).filter(
        User.role == "student",
        User.school == school,
        User.department == department
    ).all()
    
    if not department_students:
        return {
            "total_students": 0,
            "active_students": 0,
            "average_score": 0,
            "test_participation_rate": 0
        }
    
    student_ids = [s.id for s in department_students]
    
    # 진단테스트 참여 학생 수
    participated_students = db.query(DiagnosisSession.user_id).filter(
        DiagnosisSession.user_id.in_(student_ids)
    ).distinct().count()
    
    # 평균 점수
    completed_sessions = db.query(DiagnosisSession).filter(
        DiagnosisSession.user_id.in_(student_ids),
        DiagnosisSession.status == "completed",
        DiagnosisSession.percentage_score.isnot(None)
    ).all()
    
    avg_score = 0
    if completed_sessions:
        avg_score = sum(s.percentage_score for s in completed_sessions) / len(completed_sessions)
    
    # 최근 한 달 활동 학생 수
    month_ago = datetime.now() - timedelta(days=30)
    active_students = db.query(DiagnosisSession.user_id).filter(
        DiagnosisSession.user_id.in_(student_ids),
        DiagnosisSession.created_at >= month_ago
    ).distinct().count()
    
    return {
        "school": school,
        "department": department,
        "total_students": len(department_students),
        "participated_students": participated_students,
        "active_students": active_students,
        "average_score": round(avg_score, 1),
        "test_participation_rate": round(participated_students / len(department_students) * 100, 1),
        "total_sessions": len(completed_sessions)
    } 