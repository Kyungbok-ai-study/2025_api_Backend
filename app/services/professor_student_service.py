"""
교수-학생 매칭 및 모니터링 서비스
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from datetime import datetime, timedelta

from app.models.user import User
from app.models.professor_student_match import (
    ProfessorStudentMatch, 
    StudentDiagnosisAlert, 
    StudentMonitoringLog
)

logger = logging.getLogger(__name__)

class ProfessorStudentService:
    """교수-학생 매칭 및 모니터링 서비스"""
    
    def __init__(self):
        pass
    
    async def auto_match_students_to_professors(self, db: Session) -> Dict[str, int]:
        """학교-학과 기반 자동 매칭"""
        
        logger.info("🎯 교수-학생 자동 매칭 시작")
        
        try:
            # 모든 교수와 학생 조회
            professors = db.query(User).filter(User.role == "professor").all()
            students = db.query(User).filter(User.role == "student").all()
            
            matched_count = 0
            
            for professor in professors:
                prof_school = professor.school
                prof_dept = professor.department
                
                if not prof_school or not prof_dept:
                    continue
                
                # 같은 학교-학과 학생들 찾기
                matching_students = [
                    s for s in students 
                    if s.school == prof_school and s.department == prof_dept
                ]
                
                for student in matching_students:
                    # 이미 매칭된 경우 스킵
                    existing_match = db.query(ProfessorStudentMatch).filter(
                        and_(
                            ProfessorStudentMatch.professor_id == professor.id,
                            ProfessorStudentMatch.student_id == student.id
                        )
                    ).first()
                    
                    if existing_match:
                        continue
                    
                    # 새로운 매칭 생성
                    new_match = ProfessorStudentMatch(
                        professor_id=professor.id,
                        student_id=student.id,
                        match_status="pending",
                        match_method="school_department",
                        match_info={
                            "school": prof_school,
                            "department": prof_dept,
                            "auto_matched": True,
                            "confidence_score": 0.95
                        }
                    )
                    
                    db.add(new_match)
                    matched_count += 1
            
            db.commit()
            
            logger.info(f"✅ 자동 매칭 완료: {matched_count}개")
            
            return {
                "total_professors": len(professors),
                "total_students": len(students),
                "new_matches": matched_count
            }
            
        except Exception as e:
            logger.error(f"자동 매칭 실패: {e}")
            db.rollback()
            return {"error": str(e)}
    
    async def get_professor_student_matches(
        self, 
        db: Session, 
        professor_id: int,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """교수의 학생 매칭 목록 조회"""
        
        query = db.query(ProfessorStudentMatch, User).join(
            User, ProfessorStudentMatch.student_id == User.id
        ).filter(ProfessorStudentMatch.professor_id == professor_id)
        
        if status_filter:
            query = query.filter(ProfessorStudentMatch.match_status == status_filter)
        
        matches = query.all()
        
        result = []
        for match, student in matches:
            result.append({
                "match_id": match.id,
                "student_id": student.id,
                "student_name": student.name,
                "student_school": student.school,
                "student_department": student.department,
                "student_info": student.profile_info or {},
                "match_status": match.match_status,
                "match_method": match.match_method,
                "match_info": match.match_info or {},
                "created_at": match.created_at.isoformat(),
                "last_diagnosis_test": student.diagnosis_info,
                "is_active": student.is_active
            })
        
        return result
    
    async def approve_student_match(
        self, 
        db: Session, 
        professor_id: int, 
        match_id: int,
        approved: bool,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """교수가 학생 매칭 승인/거부"""
        
        match = db.query(ProfessorStudentMatch).filter(
            and_(
                ProfessorStudentMatch.id == match_id,
                ProfessorStudentMatch.professor_id == professor_id
            )
        ).first()
        
        if not match:
            return {"success": False, "error": "매칭을 찾을 수 없습니다"}
        
        # 상태 업데이트
        match.match_status = "approved" if approved else "rejected"
        match.professor_decision = {
            "approved": approved,
            "decision_at": datetime.now().isoformat(),
            "reason": reason or ("승인" if approved else "거부")
        }
        
        db.commit()
        
        return {
            "success": True,
            "match_id": match_id,
            "new_status": match.match_status,
            "message": f"학생 매칭이 {'승인' if approved else '거부'}되었습니다"
        }
    
    async def create_diagnosis_alert(
        self,
        db: Session,
        student_id: int,
        diagnosis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """학생 진단테스트 완료 시 교수에게 알림 생성"""
        
        try:
            # 해당 학생의 승인된 교수들 찾기
            approved_matches = db.query(ProfessorStudentMatch).filter(
                and_(
                    ProfessorStudentMatch.student_id == student_id,
                    ProfessorStudentMatch.match_status == "approved"
                )
            ).all()
            
            alerts_created = 0
            
            for match in approved_matches:
                # 알림 생성
                alert = StudentDiagnosisAlert(
                    student_id=student_id,
                    professor_id=match.professor_id,
                    diagnosis_info=diagnosis_data,
                    alert_status="new"
                )
                
                db.add(alert)
                alerts_created += 1
            
            db.commit()
            
            return {
                "success": True,
                "alerts_created": alerts_created,
                "message": f"{alerts_created}명의 교수에게 알림이 전송되었습니다"
            }
            
        except Exception as e:
            logger.error(f"진단테스트 알림 생성 실패: {e}")
            db.rollback()
            return {"success": False, "error": str(e)}
    
    async def get_diagnosis_alerts(
        self,
        db: Session,
        professor_id: int,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """교수의 진단테스트 알림 목록 조회"""
        
        query = db.query(StudentDiagnosisAlert, User).join(
            User, StudentDiagnosisAlert.student_id == User.id
        ).filter(StudentDiagnosisAlert.professor_id == professor_id)
        
        if status_filter:
            query = query.filter(StudentDiagnosisAlert.alert_status == status_filter)
        
        query = query.order_by(desc(StudentDiagnosisAlert.created_at))
        
        alerts = query.all()
        
        result = []
        for alert, student in alerts:
            result.append({
                "alert_id": alert.id,
                "student_id": student.id,
                "student_name": student.name,
                "student_department": student.department,
                "diagnosis_info": alert.diagnosis_info,
                "alert_status": alert.alert_status,
                "created_at": alert.created_at.isoformat(),
                "professor_viewed_at": alert.professor_viewed_at.isoformat() if alert.professor_viewed_at else None,
                "professor_notes": alert.professor_notes
            })
        
        return result
    
    async def mark_alert_as_read(
        self,
        db: Session,
        professor_id: int,
        alert_id: int
    ) -> Dict[str, Any]:
        """알림을 읽음으로 표시"""
        
        alert = db.query(StudentDiagnosisAlert).filter(
            and_(
                StudentDiagnosisAlert.id == alert_id,
                StudentDiagnosisAlert.professor_id == professor_id
            )
        ).first()
        
        if not alert:
            return {"success": False, "error": "알림을 찾을 수 없습니다"}
        
        alert.alert_status = "read"
        alert.professor_viewed_at = datetime.now()
        
        db.commit()
        
        return {"success": True, "message": "알림이 읽음으로 표시되었습니다"}
    
    async def get_student_monitoring_dashboard(
        self,
        db: Session,
        professor_id: int
    ) -> Dict[str, Any]:
        """교수용 통합 학생 모니터링 대시보드 (실제 진단테스트 데이터 포함)"""
        
        try:
            from app.models.unified_diagnosis import DiagnosisSession, DiagnosisTest
            from sqlalchemy import func, desc
            
            # 승인된 학생들 + 실제 진단테스트 활동 데이터
            approved_students_raw = await self.get_professor_student_matches(
                db, professor_id, "approved"
            )
            
            # 각 학생의 실제 진단테스트 활동 데이터 추가
            approved_students = []
            active_count = 0
            
            for student in approved_students_raw:
                student_id = student["student_id"]
                
                # 실제 DB에서 진단테스트 세션 조회
                try:
                    # 총 진단테스트 수
                    total_sessions = db.query(DiagnosisSession).filter(
                        DiagnosisSession.user_id == student_id
                    ).count()
                    
                    # 최근 24시간 진단테스트 수
                    recent_24h = db.query(DiagnosisSession).filter(
                        DiagnosisSession.user_id == student_id,
                        DiagnosisSession.created_at >= datetime.now() - timedelta(hours=24)
                    ).count()
                    
                    # 최근 진단테스트 (최대 10개)
                    recent_sessions = db.query(DiagnosisSession).filter(
                        DiagnosisSession.user_id == student_id
                    ).order_by(desc(DiagnosisSession.created_at)).limit(10).all()
                    
                    # 최신 진단테스트 정보
                    latest_session = recent_sessions[0] if recent_sessions else None
                    
                    # 완료된 테스트들의 평균 점수
                    completed_sessions = [s for s in recent_sessions if s.status == "completed" and s.percentage_score]
                    avg_score = 0
                    if completed_sessions:
                        avg_score = sum(s.percentage_score for s in completed_sessions) / len(completed_sessions)
                    
                    # 새벽 시간대 (00:00-06:00) 테스트 수
                    night_sessions = 0
                    for session in recent_sessions:
                        if session.created_at and 0 <= session.created_at.hour <= 6:
                            night_sessions += 1
                    
                    # 활동 상태 판단
                    activity_status = "inactive"
                    if recent_24h >= 3:
                        activity_status = "active"
                    elif recent_24h >= 1:
                        activity_status = "moderate"
                    
                    if activity_status in ["active", "moderate"]:
                        active_count += 1
                    
                    # 학생 정보에 실제 진단테스트 데이터 추가
                    enhanced_student = {
                        **student,
                        "test_count": total_sessions,
                        "recent_score": latest_session.percentage_score if latest_session and latest_session.percentage_score else None,
                        "activity_status": activity_status,
                        "last_diagnosis_test": {
                            "session_id": latest_session.id if latest_session else None,
                            "created_at": latest_session.created_at.isoformat() if latest_session else None,
                            "score": latest_session.percentage_score if latest_session else None,
                            "status": latest_session.status if latest_session else None,
                            "time_spent": latest_session.total_time_spent if latest_session else None
                        } if latest_session else None,
                        "diagnosis_stats": {
                            "total_tests": total_sessions,
                            "recent_24h": recent_24h,
                            "night_tests": night_sessions,  # 새벽 테스트 수
                            "avg_score": round(avg_score, 1) if avg_score else 0,
                            "completed_tests": len(completed_sessions)
                        }
                    }
                    
                    approved_students.append(enhanced_student)
                    
                    # 새벽에 7번 이상 테스트한 경우 로그 출력
                    if night_sessions >= 7:
                        logger.warning(f"🌙 학생 {student['student_name']}({student['student_department']})이 새벽에 {night_sessions}회 진단테스트를 수행했습니다!")
                        
                except Exception as e:
                    logger.error(f"학생 {student_id} 진단테스트 데이터 조회 실패: {e}")
                    # 실패시 기본 데이터로 추가
                    enhanced_student = {
                        **student,
                        "test_count": 0,
                        "recent_score": None,
                        "activity_status": "inactive",
                        "last_diagnosis_test": None,
                        "diagnosis_stats": {
                            "total_tests": 0,
                            "recent_24h": 0,
                            "night_tests": 0,
                            "avg_score": 0,
                            "completed_tests": 0
                        }
                    }
                    approved_students.append(enhanced_student)
            
            # 대기 중인 매칭
            pending_matches = await self.get_professor_student_matches(
                db, professor_id, "pending"
            )
            
            # 새로운 진단테스트 알림
            new_alerts = await self.get_diagnosis_alerts(
                db, professor_id, "new"
            )
            
            # 최근 7일간 활동
            week_ago = datetime.now() - timedelta(days=7)
            recent_activities = db.query(StudentMonitoringLog).filter(
                and_(
                    StudentMonitoringLog.professor_id == professor_id,
                    StudentMonitoringLog.created_at >= week_ago
                )
            ).order_by(desc(StudentMonitoringLog.created_at)).limit(20).all()
            
            return {
                "summary": {
                    "total_students": len(approved_students),
                    "active_students": active_count,  # 실제 활성 학생 수
                    "pending_matches": len(pending_matches),
                    "new_alerts": len(new_alerts),
                    "recent_activities": len(recent_activities)
                },
                "students": approved_students,  # 실제 진단테스트 데이터 포함
                "pending_matches": pending_matches,
                "alerts": new_alerts[:5],  # 최근 5개만
                "recent_activities": [
                    {
                        "id": log.id,
                        "student_id": log.student_id,
                        "activity_type": log.activity_type,
                        "activity_data": log.activity_data,
                        "created_at": log.created_at.isoformat()
                    }
                    for log in recent_activities
                ]
            }
        
        except Exception as e:
            logger.error(f"학생 모니터링 대시보드 조회 실패: {e}")
            # 실패시 기본 데이터 반환
            return {
                "summary": {
                    "total_students": 0,
                    "active_students": 0,
                    "pending_matches": 0,
                    "new_alerts": 0,
                    "recent_activities": 0
                },
                "students": [],
                "pending_matches": [],
                "alerts": [],
                "recent_activities": []
            }

# 전역 인스턴스
professor_student_service = ProfessorStudentService() 