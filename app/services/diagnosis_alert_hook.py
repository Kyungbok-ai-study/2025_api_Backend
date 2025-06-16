"""
진단테스트 완료 시 교수 알림 자동 발송 훅
"""
import logging
from typing import Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from app.services.professor_student_service import professor_student_service
from app.services.realtime_notification_service import realtime_notification_service

logger = logging.getLogger(__name__)

class DiagnosisAlertHook:
    """진단테스트 완료 시 자동 알림 발송"""
    
    @staticmethod
    async def on_diagnosis_completed(
        db: Session,
        student_id: int,
        diagnosis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        진단테스트 완료 시 호출되는 훅
        
        Args:
            db: 데이터베이스 세션
            student_id: 학생 ID
            diagnosis_result: 진단테스트 결과 데이터
        """
        
        logger.info(f"📊 학생 {student_id} 진단테스트 완료 - 교수 알림 발송 시작")
        
        try:
            # 진단테스트 데이터 구성
            diagnosis_data = {
                "test_id": diagnosis_result.get("test_id", f"diag_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
                "test_type": diagnosis_result.get("test_type", "종합진단"),
                "started_at": diagnosis_result.get("started_at", datetime.now().isoformat()),
                "completed_at": diagnosis_result.get("completed_at", datetime.now().isoformat()),
                "score": diagnosis_result.get("score", 0),
                "total_questions": diagnosis_result.get("total_questions", 0),
                "correct_answers": diagnosis_result.get("correct_answers", 0),
                "time_taken": diagnosis_result.get("time_taken", 0),
                "difficulty_areas": diagnosis_result.get("difficulty_areas", []),
                "performance_summary": diagnosis_result.get("performance_summary", {})
            }
            
            # 1. 교수 DB 알림 생성
            alert_result = await professor_student_service.create_diagnosis_alert(
                db, student_id, diagnosis_data
            )
            
            if alert_result["success"]:
                logger.info(f"✅ DB 알림 저장 완료: {alert_result['alerts_created']}개")
                
                # 2. 실시간 알림 전송 (iOS 알람 스타일)
                from app.models.professor_student_match import ProfessorStudentMatch
                professor_matches = db.query(ProfessorStudentMatch).filter(
                    ProfessorStudentMatch.student_id == student_id,
                    ProfessorStudentMatch.match_status == "approved"
                ).all()
                
                professor_ids = [match.professor_id for match in professor_matches]
                
                if professor_ids:
                    realtime_result = await realtime_notification_service.notify_diagnosis_completed(
                        db, student_id, diagnosis_data, professor_ids
                    )
                    
                    if realtime_result["success"]:
                        logger.info(f"🔔 실시간 알림 전송 완료: {realtime_result['notifications_sent']}개")
                
            else:
                logger.error(f"❌ 교수 알림 발송 실패: {alert_result.get('error')}")
            
            return alert_result
            
        except Exception as e:
            logger.error(f"진단테스트 알림 훅 실행 실패: {e}")
            return {"success": False, "error": str(e)}

# 전역 인스턴스
diagnosis_alert_hook = DiagnosisAlertHook() 