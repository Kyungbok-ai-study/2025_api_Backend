"""
정리된 교수 API 엔드포인트
중복 제거 및 핵심 기능만 유지
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from app.db.database import get_db
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.services.professor_student_service import professor_student_service
from app.services.realtime_notification_service import realtime_notification_service

router = APIRouter()
logger = logging.getLogger(__name__)

# ==================== 기본 정보 ====================

@router.get("/dashboard")
async def get_professor_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """교수 대시보드 - 모든 기본 정보 포함"""
    
    if current_user.role != "professor":
        raise HTTPException(status_code=403, detail="교수 권한이 필요합니다")
    
    try:
        # 학생 모니터링 데이터
        monitoring_data = await professor_student_service.get_student_monitoring_dashboard(
            db, current_user.id
        )
        
        # 실시간 알림
        notifications = await realtime_notification_service.get_professor_notifications(
            db, current_user.id
        )
        
        return {
            "success": True,
            "professor_info": {
                "id": current_user.id,
                "name": current_user.name,
                "school": current_user.school,
                "department": current_user.department
            },
            "monitoring": monitoring_data,
            "notifications": notifications,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"대시보드 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"대시보드 조회 실패: {str(e)}")

@router.get("/profile")
async def get_professor_profile(
    current_user: User = Depends(get_current_user)
):
    """교수 프로필 정보"""
    
    if current_user.role != "professor":
        raise HTTPException(status_code=403, detail="교수 권한이 필요합니다")
    
    return {
        "success": True,
        "profile": {
            "id": current_user.id,
            "name": current_user.name,
            "school": current_user.school,
            "department": current_user.department,
            "email": getattr(current_user, 'email', None),
            "profile_info": current_user.profile_info or {},
            "created_at": current_user.created_at.isoformat()
        }
    }

# ==================== 학생 관리 ====================

@router.get("/students")
async def get_my_students(
    status: str = "all",  # all, pending, approved, rejected
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """내 학생 목록 조회"""
    
    if current_user.role != "professor":
        raise HTTPException(status_code=403, detail="교수 권한이 필요합니다")
    
    try:
        status_filter = None if status == "all" else status
        students = await professor_student_service.get_professor_student_matches(
            db, current_user.id, status_filter
        )
        
        return {
            "success": True,
            "students": students,
            "total_count": len(students),
            "status_filter": status
        }
        
    except Exception as e:
        logger.error(f"학생 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"학생 목록 조회 실패: {str(e)}")

@router.post("/students/auto-match")
async def auto_match_students(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """학교-학과 기반 학생 자동 매칭"""
    
    if current_user.role != "professor":
        raise HTTPException(status_code=403, detail="교수 권한이 필요합니다")
    
    try:
        result = await professor_student_service.auto_match_students_to_professors(db)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "success": True,
            "message": "학생 자동 매칭이 완료되었습니다",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"자동 매칭 실패: {e}")
        raise HTTPException(status_code=500, detail=f"자동 매칭 실패: {str(e)}")

@router.post("/students/{match_id}/approve")
async def approve_student_match(
    match_id: int,
    approval_data: dict,  # {"approved": true/false, "reason": "승인 이유"}
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """학생 매칭 승인/거부"""
    
    if current_user.role != "professor":
        raise HTTPException(status_code=403, detail="교수 권한이 필요합니다")
    
    try:
        approved = approval_data.get("approved", True)
        reason = approval_data.get("reason", "")
        
        result = await professor_student_service.approve_student_match(
            db, current_user.id, match_id, approved, reason
        )
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"학생 매칭 승인/거부 실패: {e}")
        raise HTTPException(status_code=500, detail=f"매칭 처리 실패: {str(e)}")

@router.get("/students/{student_id}/analysis")
async def get_student_analysis(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """학생 상세 분석 - 진단테스트 결과 및 AI 분석"""
    
    if current_user.role != "professor":
        raise HTTPException(status_code=403, detail="교수 권한이 필요합니다")
    
    try:
        # 해당 학생이 내 학생인지 확인
        student_matches = await professor_student_service.get_professor_student_matches(
            db, current_user.id, "approved"
        )
        
        my_student = next((s for s in student_matches if s["student_id"] == student_id), None)
        if not my_student:
            raise HTTPException(status_code=403, detail="접근 권한이 없는 학생입니다")
        
        # 학생 정보 조회
        student = db.query(User).filter(User.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다")
        
        # 실제 진단테스트 세션들 조회
        try:
            from app.models.unified_diagnosis import DiagnosisSession
            from app.routers.diagnosis import DiagnosticSession, DiagnosticAIAnalysis
            from sqlalchemy import desc
            import json
            
            # 통합 진단 시스템 세션들
            unified_sessions = db.query(DiagnosisSession).filter(
                DiagnosisSession.user_id == student_id
            ).order_by(desc(DiagnosisSession.created_at)).limit(20).all()
            
            # 기존 진단 시스템 세션들
            legacy_sessions = db.query(DiagnosticSession).filter(
                DiagnosticSession.user_id == student_id
            ).order_by(desc(DiagnosticSession.started_at)).limit(20).all()
            
            # 진단테스트 결과 통합
            diagnosis_results = []
            
            # 통합 진단 결과 추가
            for session in unified_sessions:
                if session.status == "completed" and session.percentage_score:
                    diagnosis_results.append({
                        "session_id": session.id,
                        "test_type": "통합진단테스트",
                        "started_at": session.created_at.isoformat(),
                        "completed_at": session.updated_at.isoformat() if session.updated_at else session.created_at.isoformat(),
                        "score": session.percentage_score,
                        "total_questions": session.total_questions or 30,
                        "correct_answers": round((session.percentage_score / 100) * (session.total_questions or 30)),
                        "time_taken_seconds": session.total_time_spent or 0,
                        "department": session.department or student.department,
                        "difficulty_level": session.difficulty_level or "중급",
                        "system_type": "unified"
                    })
            
            # 기존 시스템 결과 추가
            for session in legacy_sessions:
                if session.status == 'completed' and session.final_score:
                    diagnosis_results.append({
                        "session_id": session.id,
                        "test_type": session.test_type or "진단테스트",
                        "started_at": session.started_at.isoformat() if session.started_at else None,
                        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                        "score": session.total_score,
                        "total_questions": session.total_questions or 30,
                        "correct_answers": session.correct_answers or 0,
                        "time_taken_seconds": round(session.total_time_ms / 1000) if session.total_time_ms else 0,
                        "department": session.department or student.department,
                        "difficulty_level": "중급",
                        "system_type": "legacy"
                    })
            
            # 점수순으로 정렬 (최신순)
            diagnosis_results.sort(key=lambda x: x["completed_at"] or x["started_at"], reverse=True)
            
            # AI 분석 조회
            ai_analyses = []
            for session in legacy_sessions[:5]:  # 최근 5개 세션의 AI 분석
                analysis = db.query(DiagnosticAIAnalysis).filter(
                    DiagnosticAIAnalysis.session_id == session.id
                ).first()
                
                if analysis:
                    try:
                        analysis_data = json.loads(analysis.analysis_data)
                        ai_analyses.append({
                            "session_id": session.id,
                            "confidence_score": analysis.confidence_score,
                            "created_at": analysis.created_at.isoformat(),
                            "analysis": analysis_data
                        })
                    except:
                        pass
            
            # 학습 패턴 분석
            learning_patterns = {
                "total_tests": len(diagnosis_results),
                "average_score": sum(r["score"] for r in diagnosis_results) / len(diagnosis_results) if diagnosis_results else 0,
                "best_score": max((r["score"] for r in diagnosis_results), default=0),
                "latest_score": diagnosis_results[0]["score"] if diagnosis_results else 0,
                "score_trend": "improving" if len(diagnosis_results) >= 2 and diagnosis_results[0]["score"] > diagnosis_results[1]["score"] else "stable",
                "active_days": len(set(r["completed_at"][:10] for r in diagnosis_results if r["completed_at"])),
                "total_study_time": sum(r["time_taken_seconds"] for r in diagnosis_results),
                "avg_time_per_test": sum(r["time_taken_seconds"] for r in diagnosis_results) / len(diagnosis_results) if diagnosis_results else 0
            }
            
            # 새벽 활동 분석
            night_tests = []
            for result in diagnosis_results:
                if result["completed_at"]:
                    try:
                        from datetime import datetime
                        completed_time = datetime.fromisoformat(result["completed_at"].replace('Z', '+00:00'))
                        if 0 <= completed_time.hour <= 6:
                            night_tests.append(result)
                    except:
                        pass
            
            learning_patterns["night_tests"] = len(night_tests)
            learning_patterns["night_activity_concern"] = len(night_tests) >= 7
            
            # 강점/약점 분석
            strengths = []
            weaknesses = []
            
            if learning_patterns["average_score"] >= 80:
                strengths.append("높은 평균 점수 유지")
            if learning_patterns["score_trend"] == "improving":
                strengths.append("지속적인 성적 향상")
            if learning_patterns["active_days"] >= 5:
                strengths.append("꾸준한 학습 참여")
                
            if learning_patterns["average_score"] < 60:
                weaknesses.append("평균 점수 개선 필요")
            if learning_patterns["night_activity_concern"]:
                weaknesses.append("새벽 시간대 과도한 학습")
            if learning_patterns["total_tests"] < 3:
                weaknesses.append("진단테스트 참여 부족")
            
            return {
                "success": True,
                "student_info": {
                    "id": student.id,
                    "name": student.name,
                    "school": student.school,
                    "department": student.department,
                    "user_id": student.user_id,
                    "email": student.email,
                    "is_active": student.is_active,
                    "created_at": student.created_at.isoformat()
                },
                "diagnosis_results": diagnosis_results[:15],  # 최근 15개
                "ai_analyses": ai_analyses,
                "learning_patterns": learning_patterns,
                "performance_insights": {
                    "strengths": strengths,
                    "weaknesses": weaknesses,
                    "recommendations": [
                        "꾸준한 진단테스트 참여로 학습 상태 점검",
                        "취약 영역 집중 학습",
                        "적절한 학습 시간 관리" if learning_patterns["night_activity_concern"] else "현재 학습 패턴 유지"
                    ]
                },
                "match_info": my_student,
                "professor_notes": {
                    "last_reviewed": datetime.now().isoformat(),
                    "concern_level": "high" if learning_patterns["night_activity_concern"] else ("medium" if learning_patterns["average_score"] < 70 else "low"),
                    "requires_attention": learning_patterns["night_activity_concern"] or learning_patterns["average_score"] < 60
                }
            }
            
        except Exception as e:
            logger.error(f"진단테스트 데이터 조회 실패: {e}")
            # 실패시 기본 정보만 반환
            return {
                "success": True,
                "student_info": {
                    "id": student.id,
                    "name": student.name,
                    "school": student.school,
                    "department": student.department,
                    "user_id": student.user_id,
                    "email": student.email,
                    "is_active": student.is_active,
                    "created_at": student.created_at.isoformat()
                },
                "diagnosis_results": [],
                "ai_analyses": [],
                "learning_patterns": {
                    "total_tests": 0,
                    "average_score": 0,
                    "night_tests": 0
                },
                "performance_insights": {
                    "strengths": [],
                    "weaknesses": ["진단테스트 데이터 없음"],
                    "recommendations": ["진단테스트 참여 권장"]
                },
                "match_info": my_student,
                "error": "진단테스트 데이터를 불러올 수 없습니다"
            }
        
    except Exception as e:
        logger.error(f"학생 분석 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"학생 분석 실패: {str(e)}")

# ==================== 학습 모니터링 ====================

@router.get("/monitoring")
async def get_learning_monitoring(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """학습 모니터링 페이지 데이터"""
    
    if current_user.role != "professor":
        raise HTTPException(status_code=403, detail="교수 권한이 필요합니다")
    
    try:
        # 세션 등록
        await realtime_notification_service.register_professor_session(
            current_user.id, {"page": "learning_monitoring"}
        )
        
        # 모니터링 데이터
        monitoring_data = await professor_student_service.get_student_monitoring_dashboard(
            db, current_user.id
        )
        
        # 최신 알림들
        latest_alerts = await professor_student_service.get_diagnosis_alerts(
            db, current_user.id, "new"
        )
        
        # 실시간 알림
        realtime_notifications = await realtime_notification_service.get_professor_notifications(
            db, current_user.id
        )
        
        # 학생별 활동 요약
        approved_students = monitoring_data.get("students", [])
        student_activity_summary = []
        
        for student in approved_students:
            student_alerts = [
                alert for alert in latest_alerts 
                if alert["student_id"] == student["student_id"]
            ]
            
            latest_test = student_alerts[0] if student_alerts else None
            
            student_activity_summary.append({
                "student_id": student["student_id"],
                "student_name": student["student_name"],
                "school": student["student_school"],
                "department": student["student_department"],
                "last_diagnosis_test": latest_test,
                "activity_status": "active" if latest_test else "inactive",
                "concern_level": "normal",
                "recent_score": latest_test["diagnosis_info"]["score"] if latest_test else None,
                "test_count": len(student_alerts),
                "match_status": student["match_status"],
                "diagnosis_stats": student.get("diagnosis_stats", {})
            })
        
        return {
            "success": True,
            "page_title": "학습 모니터링",
            "professor_info": {
                "id": current_user.id,
                "name": current_user.name,
                "department": current_user.department,
                "school": current_user.school
            },
            "monitoring_summary": {
                "total_students": len(approved_students),
                "active_students": len([s for s in student_activity_summary if s["activity_status"] == "active"]),
                "new_alerts": len(latest_alerts),
                "pending_matches": len(monitoring_data.get("pending_matches", [])),
                "realtime_unread": realtime_notifications.get("unread_count", 0)
            },
            "student_activities": student_activity_summary,
            "recent_alerts": latest_alerts[:10],
            "pending_matches": monitoring_data.get("pending_matches", []),
            "ios_style_alerts": [
                {
                    "id": f"alert_{alert['alert_id']}",
                    "title": "📊 진단테스트 완료",
                    "message": f"{alert['student_name']} 학생이 진단테스트를 완료했습니다",
                    "student_name": alert['student_name'],
                    "score": alert['diagnosis_info'].get('score', 0),
                    "test_type": alert['diagnosis_info'].get('test_type', '종합진단'),
                    "created_at": alert['created_at'],
                    "action_url": f"/professor/students/{alert['student_id']}/analysis",
                    "priority": "high" if alert['diagnosis_info'].get('score', 0) < 70 else "normal"
                }
                for alert in latest_alerts[:5]
            ],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"학습 모니터링 데이터 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"데이터 조회 실패: {str(e)}")

# ==================== 알림 관리 ====================

@router.get("/alerts")
async def get_diagnosis_alerts(
    status: str = "all",  # all, new, read, archived
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """진단테스트 알림 조회"""
    
    if current_user.role != "professor":
        raise HTTPException(status_code=403, detail="교수 권한이 필요합니다")
    
    try:
        status_filter = None if status == "all" else status
        alerts = await professor_student_service.get_diagnosis_alerts(
            db, current_user.id, status_filter
        )
        
        new_count = len([a for a in alerts if a["alert_status"] == "new"])
        
        return {
            "success": True,
            "alerts": alerts,
            "total_count": len(alerts),
            "new_count": new_count,
            "unread_count": new_count,  # 프론트엔드 호환성
            "status_filter": status
        }
        
    except Exception as e:
        logger.error(f"알림 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"알림 조회 실패: {str(e)}")

@router.post("/alerts/mark-all-read")
async def mark_all_alerts_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """모든 알림을 읽음으로 표시"""
    
    if current_user.role != "professor":
        raise HTTPException(status_code=403, detail="교수 권한이 필요합니다")
    
    try:
        # 실시간 알림 읽음 처리
        realtime_result = await realtime_notification_service.mark_notifications_as_read(
            current_user.id
        )
        
        # DB 알림도 읽음 처리
        from app.models.professor_student_match import StudentDiagnosisAlert
        db.query(StudentDiagnosisAlert).filter(
            StudentDiagnosisAlert.professor_id == current_user.id,
            StudentDiagnosisAlert.alert_status == "new"
        ).update({"alert_status": "read"})
        db.commit()
        
        return {
            "success": True,
            "message": "모든 알림이 읽음으로 처리되었습니다",
            "realtime_result": realtime_result
        }
        
    except Exception as e:
        logger.error(f"알림 처리 실패: {e}")
        raise HTTPException(status_code=500, detail=f"알림 처리 실패: {str(e)}")

@router.post("/alerts/{alert_id}/read")
async def mark_alert_read(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """특정 알림 읽음 처리"""
    
    if current_user.role != "professor":
        raise HTTPException(status_code=403, detail="교수 권한이 필요합니다")
    
    try:
        result = await professor_student_service.mark_alert_as_read(
            db, current_user.id, alert_id
        )
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"알림 읽음 처리 실패: {e}")
        raise HTTPException(status_code=500, detail=f"알림 처리 실패: {str(e)}")

# ==================== 문제 관리 (통합) ====================

@router.post("/problems/generate")
async def generate_problems(
    request: dict,  # {"type": "ai|rag", "subject": "", "difficulty": "", "count": 5}
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """문제 생성 (모든 AI 방식 통합)"""
    
    if current_user.role != "professor":
        raise HTTPException(status_code=403, detail="교수 권한이 필요합니다")
    
    try:
        generation_type = request.get("type", "ai")  # ai, rag
        subject = request.get("subject", "")
        difficulty = request.get("difficulty", "중")
        count = request.get("count", 5)
        
        # TODO: 실제 문제 생성 로직 구현
        problems = []
        for i in range(count):
            problems.append({
                "id": f"prob_{i+1}",
                "question": f"{subject} 관련 {difficulty} 난이도 문제 {i+1}",
                "type": "multiple_choice",
                "choices": ["선택1", "선택2", "선택3", "선택4"],
                "correct_answer": "선택1",
                "explanation": f"문제 {i+1} 해설",
                "difficulty": difficulty,
                "generated_by": generation_type
            })
        
        return {
            "success": True,
            "problems": problems,
            "generation_info": {
                "type": generation_type,
                "subject": subject,
                "difficulty": difficulty,
                "count": len(problems),
                "generated_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"문제 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"문제 생성 실패: {str(e)}")

@router.get("/problems")
async def get_my_problems(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """내가 생성한 문제 목록"""
    
    if current_user.role != "professor":
        raise HTTPException(status_code=403, detail="교수 권한이 필요합니다")
    
    # TODO: 실제 문제 조회 로직
    return {
        "success": True,
        "problems": [],
        "total_count": 0
    }

# ==================== 세션 관리 ====================

@router.post("/session/start")
async def start_professor_session(
    current_user: User = Depends(get_current_user)
):
    """교수 세션 시작 (로그인 시 호출)"""
    
    if current_user.role != "professor":
        raise HTTPException(status_code=403, detail="교수 권한이 필요합니다")
    
    try:
        result = await realtime_notification_service.register_professor_session(
            current_user.id,
            {
                "login_time": datetime.now().isoformat(),
                "professor_name": current_user.name,
                "department": current_user.department
            }
        )
        
        return {
            "success": True,
            "professor_id": current_user.id,
            "message": "세션이 시작되었습니다. 실시간 알림을 받을 수 있습니다.",
            **result
        }
        
    except Exception as e:
        logger.error(f"세션 시작 실패: {e}")
        raise HTTPException(status_code=500, detail=f"세션 시작 실패: {str(e)}")

@router.post("/session/end")
async def end_professor_session(
    current_user: User = Depends(get_current_user)
):
    """교수 세션 종료 (로그아웃 시 호출)"""
    
    if current_user.role != "professor":
        raise HTTPException(status_code=403, detail="교수 권한이 필요합니다")
    
    try:
        result = await realtime_notification_service.unregister_professor_session(
            current_user.id
        )
        
        return {
            "success": True,
            "professor_id": current_user.id,
            "message": "세션이 종료되었습니다.",
            **result
        }
        
    except Exception as e:
        logger.error(f"세션 종료 실패: {e}")
        raise HTTPException(status_code=500, detail=f"세션 종료 실패: {str(e)}")

# ==================== 테스트용 (개발 환경만) ====================

@router.post("/test/simulate-diagnosis")
async def simulate_diagnosis_test(
    data: dict,  # {"student_id": 1, "score": 85, "test_type": "종합진단"}
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """진단테스트 완료 시뮬레이션 (개발용)"""
    
    if current_user.role != "professor":
        raise HTTPException(status_code=403, detail="교수 권한이 필요합니다")
    
    try:
        from app.services.diagnosis_alert_hook import diagnosis_alert_hook
        
        student_id = data.get("student_id")
        if not student_id:
            raise HTTPException(status_code=400, detail="student_id가 필요합니다")
        
        # 시뮬레이션 데이터
        diagnosis_result = {
            "test_type": data.get("test_type", "종합진단테스트"),
            "score": data.get("score", 85.5),
            "total_questions": data.get("total_questions", 50),
            "correct_answers": data.get("correct_answers", 42),
            "time_taken": data.get("time_taken", 1800),
            "difficulty_areas": data.get("difficulty_areas", ["해부학", "생리학"]),
            "performance_summary": data.get("performance_summary", {
                "strong_areas": ["간호학 기초"],
                "weak_areas": ["해부학"],
                "recommendation": "해부학 추가 학습 필요"
            })
        }
        
        # 알림 생성
        alert_result = await diagnosis_alert_hook.on_diagnosis_completed(
            db, student_id, diagnosis_result
        )
        
        return {
            "success": True,
            "message": "진단테스트 완료 알림이 시뮬레이션되었습니다",
            "student_id": student_id,
            "alert_result": alert_result,
            "diagnosis_data": diagnosis_result
        }
        
    except Exception as e:
        logger.error(f"시뮬레이션 실패: {e}")
        raise HTTPException(status_code=500, detail=f"시뮬레이션 실패: {str(e)}") 