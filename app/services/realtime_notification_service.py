"""
실시간 알림 서비스 (iOS 알람 시스템 스타일)
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.models.user import User
from app.models.professor_student_match import StudentDiagnosisAlert

logger = logging.getLogger(__name__)

class RealtimeNotificationService:
    """실시간 알림 서비스"""
    
    def __init__(self):
        # 활성 교수 세션 관리
        self.active_professor_sessions = {}
        
    async def notify_diagnosis_completed(
        self,
        db: Session,
        student_id: int,
        diagnosis_data: Dict[str, Any],
        professor_ids: List[int]
    ) -> Dict[str, Any]:
        """학생 진단테스트 완료 시 교수에게 실시간 알림"""
        
        try:
            # 학생 정보 조회
            student = db.query(User).filter(User.id == student_id).first()
            if not student:
                return {"success": False, "error": "학생을 찾을 수 없습니다"}
            
            # 알림 메시지 생성
            notification = {
                "type": "diagnosis_completed",
                "title": "📊 진단테스트 완료",
                "message": f"{student.name} 학생이 진단테스트를 완료했습니다",
                "student_info": {
                    "id": student.id,
                    "name": student.name,
                    "department": student.department,
                    "school": student.school
                },
                "diagnosis_summary": {
                    "test_type": diagnosis_data.get("test_type", "종합진단"),
                    "score": diagnosis_data.get("score", 0),
                    "total_questions": diagnosis_data.get("total_questions", 0),
                    "correct_answers": diagnosis_data.get("correct_answers", 0),
                    "completion_time": diagnosis_data.get("completed_at", datetime.now().isoformat())
                },
                "actions": [
                    {
                        "label": "상세 분석 보기",
                        "action": "view_detail",
                        "url": f"/professor/student-analysis/{student_id}"
                    },
                    {
                        "label": "알림 해제",
                        "action": "dismiss",
                        "url": f"/professor/mark-alert-read"
                    }
                ],
                "priority": "high",
                "created_at": datetime.now().isoformat(),
                "auto_dismiss": False
            }
            
            # 각 교수에게 알림 전송
            notifications_sent = 0
            for professor_id in professor_ids:
                success = await self._send_notification_to_professor(
                    professor_id, notification
                )
                if success:
                    notifications_sent += 1
            
            logger.info(f"🔔 진단테스트 완료 알림 전송 완료: {notifications_sent}명의 교수")
            
            return {
                "success": True,
                "notifications_sent": notifications_sent,
                "notification": notification
            }
            
        except Exception as e:
            logger.error(f"실시간 알림 전송 실패: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_notification_to_professor(
        self,
        professor_id: int,
        notification: Dict[str, Any]
    ) -> bool:
        """특정 교수에게 알림 전송"""
        
        try:
            # 교수 세션이 활성 상태인지 확인
            if professor_id in self.active_professor_sessions:
                session_info = self.active_professor_sessions[professor_id]
                session_info["notifications"].append(notification)
                session_info["unread_count"] += 1
                session_info["last_notification"] = datetime.now().isoformat()
                
                logger.info(f"🔔 교수 {professor_id}에게 실시간 알림 전송")
                return True
            else:
                # 오프라인 교수는 로그인 시 확인할 수 있도록 저장
                logger.info(f"📱 교수 {professor_id} 오프라인 - 로그인 시 알림 표시 예정")
                return True
                
        except Exception as e:
            logger.error(f"교수 {professor_id} 알림 전송 실패: {e}")
            return False
    
    async def register_professor_session(
        self,
        professor_id: int,
        session_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """교수 로그인 시 세션 등록"""
        
        session_info = {
            "professor_id": professor_id,
            "login_time": datetime.now().isoformat(),
            "notifications": [],
            "unread_count": 0,
            "last_activity": datetime.now().isoformat(),
            "session_data": session_data or {}
        }
        
        self.active_professor_sessions[professor_id] = session_info
        
        logger.info(f"👨‍🏫 교수 {professor_id} 세션 등록 완료")
        
        return {
            "success": True,
            "session_id": professor_id,
            "message": "세션이 등록되었습니다"
        }
    
    async def get_professor_notifications(
        self,
        db: Session,
        professor_id: int,
        include_offline: bool = True
    ) -> Dict[str, Any]:
        """교수의 알림 목록 조회 (실시간 + 오프라인)"""
        
        try:
            notifications = []
            unread_count = 0
            
            # 1. 실시간 알림 (세션에 저장된 것들)
            if professor_id in self.active_professor_sessions:
                session = self.active_professor_sessions[professor_id]
                notifications.extend(session["notifications"])
                unread_count = session["unread_count"]
            
            # 2. 오프라인 알림 (DB에 저장된 것들)
            if include_offline:
                db_alerts = db.query(StudentDiagnosisAlert, User).join(
                    User, StudentDiagnosisAlert.student_id == User.id
                ).filter(
                    and_(
                        StudentDiagnosisAlert.professor_id == professor_id,
                        StudentDiagnosisAlert.alert_status == "new"
                    )
                ).order_by(desc(StudentDiagnosisAlert.created_at)).limit(20).all()
                
                for alert, student in db_alerts:
                    offline_notification = {
                        "type": "diagnosis_completed",
                        "alert_id": alert.id,
                        "title": "📊 진단테스트 완료",
                        "message": f"{student.name} 학생이 진단테스트를 완료했습니다",
                        "student_info": {
                            "id": student.id,
                            "name": student.name,
                            "department": student.department,
                            "school": student.school
                        },
                        "diagnosis_summary": alert.diagnosis_info,
                        "created_at": alert.created_at.isoformat(),
                        "is_offline": True,
                        "priority": "normal"
                    }
                    notifications.append(offline_notification)
                    unread_count += 1
            
            return {
                "success": True,
                "notifications": notifications,
                "total_count": len(notifications),
                "unread_count": unread_count,
                "last_update": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"교수 알림 조회 실패: {e}")
            return {"success": False, "error": str(e)}
    
    async def mark_notifications_as_read(
        self,
        professor_id: int,
        notification_ids: List[str] = None
    ) -> Dict[str, Any]:
        """알림을 읽음으로 표시"""
        
        try:
            if professor_id in self.active_professor_sessions:
                session = self.active_professor_sessions[professor_id]
                
                if notification_ids:
                    # 특정 알림만 읽음 처리
                    for notification in session["notifications"]:
                        if notification.get("id") in notification_ids:
                            notification["read"] = True
                else:
                    # 모든 알림 읽음 처리
                    for notification in session["notifications"]:
                        notification["read"] = True
                
                session["unread_count"] = len([
                    n for n in session["notifications"] 
                    if not n.get("read", False)
                ])
                
                return {"success": True, "message": "알림이 읽음으로 표시되었습니다"}
            
            return {"success": False, "error": "활성 세션을 찾을 수 없습니다"}
            
        except Exception as e:
            logger.error(f"알림 읽음 처리 실패: {e}")
            return {"success": False, "error": str(e)}
    
    async def unregister_professor_session(self, professor_id: int) -> Dict[str, Any]:
        """교수 로그아웃 시 세션 해제"""
        
        if professor_id in self.active_professor_sessions:
            del self.active_professor_sessions[professor_id]
            logger.info(f"👨‍🏫 교수 {professor_id} 세션 해제 완료")
        
        return {"success": True, "message": "세션이 해제되었습니다"}

# 전역 인스턴스
realtime_notification_service = RealtimeNotificationService() 