"""
교수 대시보드 서비스
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

from app.models.user import User
from app.models.diagnosis import DiagnosisResult
from app.schemas.professor import (
    ProfessorDashboardResponse, ClassAnalyticsResponse,
    StudentProgressSummary, AssignmentResponse,
    ClassPerformanceResponse, LearningInsightsResponse
)

logger = logging.getLogger(__name__)

class ProfessorService:
    """교수 대시보드 서비스"""
    
    async def get_professor_dashboard(self, db: Session, professor_id: int) -> ProfessorDashboardResponse:
        """교수 대시보드 데이터"""
        try:
            professor = db.query(User).filter(User.id == professor_id).first()
            
            # 모의 데이터로 대시보드 구성
            return ProfessorDashboardResponse(
                professor_name=professor.name if professor else "교수님",
                total_classes=3,
                total_students=85,
                recent_activities=[
                    {"type": "submission", "count": 12, "date": datetime.now().isoformat()},
                    {"type": "new_student", "count": 2, "date": (datetime.now() - timedelta(days=1)).isoformat()}
                ],
                performance_summary={
                    "average_score": 78.5,
                    "completion_rate": 0.82,
                    "improvement_trend": "+5.2%"
                },
                pending_tasks=[
                    "과제 채점 대기: 15건",
                    "학생 상담 예정: 3건",
                    "성적 입력 마감: 2일 남음"
                ]
            )
        except Exception as e:
            logger.error(f"교수 대시보드 조회 실패: {str(e)}")
            raise
    
    async def get_class_analytics(self, db: Session, professor_id: int, semester: Optional[str] = None) -> List[ClassAnalyticsResponse]:
        """수업 분석"""
        # 모의 데이터
        return [
            ClassAnalyticsResponse(
                class_id=1,
                class_name="데이터베이스 개론",
                student_count=28,
                average_performance=0.75,
                completion_rate=0.89,
                difficulty_distribution={"easy": 5, "medium": 15, "hard": 8},
                recent_submissions=12
            ),
            ClassAnalyticsResponse(
                class_id=2,
                class_name="알고리즘",
                student_count=32,
                average_performance=0.68,
                completion_rate=0.78,
                difficulty_distribution={"easy": 3, "medium": 18, "hard": 11},
                recent_submissions=8
            )
        ]
    
    async def get_students_progress(self, db: Session, professor_id: int, class_id: Optional[int] = None, limit: int = 50) -> List[StudentProgressSummary]:
        """학생 진도 현황"""
        students = db.query(User).filter(User.role == "student").limit(limit).all()
        
        progress_list = []
        for student in students:
            # 최근 진단 결과 조회
            latest_result = db.query(DiagnosisResult).filter(
                DiagnosisResult.user_id == student.id
            ).order_by(desc(DiagnosisResult.calculated_at)).first()
            
            learning_level = latest_result.learning_level if latest_result else 0.0
            
            progress_list.append(StudentProgressSummary(
                student_id=student.id,
                student_name=student.name,
                learning_level=learning_level,
                completion_percentage=min(learning_level * 100, 100),
                last_activity=latest_result.calculated_at if latest_result else datetime.now() - timedelta(days=30),
                risk_level="high" if learning_level < 0.4 else "medium" if learning_level < 0.7 else "low"
            ))
        
        return progress_list
    
    async def create_assignment(self, db: Session, professor_id: int, class_id: int, title: str, description: str, due_date: datetime, difficulty_level: int) -> AssignmentResponse:
        """과제 생성"""
        # 실제로는 Assignment 모델에 저장
        return AssignmentResponse(
            assignment_id=1001,
            title=title,
            description=description,
            due_date=due_date,
            difficulty_level=difficulty_level,
            created_at=datetime.now()
        )
    
    async def get_class_performance(self, db: Session, professor_id: int, class_id: int, period_days: int) -> ClassPerformanceResponse:
        """수업별 성과 분석"""
        return ClassPerformanceResponse(
            class_id=class_id,
            performance_metrics={
                "average_score": 76.8,
                "median_score": 78.0,
                "pass_rate": 0.85,
                "improvement_rate": 0.12
            },
            student_distribution={
                "excellent": 8,
                "good": 15,
                "average": 12,
                "needs_improvement": 5
            },
            improvement_trends={
                "weekly_improvement": [0.05, 0.08, 0.12, 0.15],
                "subject_strengths": ["기본개념", "실습"],
                "subject_weaknesses": ["고급이론", "응용문제"]
            },
            recommendations=[
                "약점 영역에 대한 추가 설명 필요",
                "실습 시간 확대 고려",
                "상위권 학생들을 위한 심화 과제 제공"
            ]
        )
    
    async def get_learning_insights(self, db: Session, professor_id: int) -> LearningInsightsResponse:
        """학습 인사이트"""
        return LearningInsightsResponse(
            insights=[
                {
                    "type": "performance_pattern",
                    "title": "학습 성과 패턴 분석",
                    "description": "오후 시간대 학습 효과가 20% 높음",
                    "confidence": 0.85
                },
                {
                    "type": "difficulty_analysis",
                    "title": "난이도별 성취도",
                    "description": "중급 문제에서 가장 큰 학습 효과",
                    "confidence": 0.78
                }
            ],
            trend_analysis={
                "overall_trend": "improving",
                "trend_percentage": 8.5,
                "key_factors": ["지속적 연습", "피드백 반영"]
            },
            predictions={
                "next_month_performance": 0.82,
                "completion_probability": 0.89,
                "risk_students": 5
            },
            actionable_recommendations=[
                "위험군 학생 개별 상담 실시",
                "중급 문제 비중 확대",
                "오후 시간대 수업 집중도 향상 방안 모색"
            ]
        )
    
    async def get_student_detail_analysis(self, db: Session, professor_id: int, student_id: int) -> Dict[str, Any]:
        """학생 상세 분석"""
        student = db.query(User).filter(User.id == student_id).first()
        if not student:
            raise ValueError("학생을 찾을 수 없습니다")
        
        # 학습 기록 분석
        results = db.query(DiagnosisResult).filter(
            DiagnosisResult.user_id == student_id
        ).order_by(desc(DiagnosisResult.calculated_at)).limit(10).all()
        
        return {
            "student_info": {
                "id": student.id,
                "name": student.name,
                "email": student.email,
                "department": student.department
            },
            "learning_progress": [
                {
                    "date": result.calculated_at.isoformat(),
                    "level": result.learning_level,
                    "accuracy": result.accuracy_rate
                } for result in results
            ],
            "strengths": ["데이터베이스 설계", "SQL 기본"],
            "weaknesses": ["복잡 쿼리", "성능 최적화"],
            "recommendations": [
                "고급 SQL 문법 집중 학습",
                "실무 프로젝트 참여 권장"
            ]
        }
    
    async def send_student_feedback(self, db: Session, professor_id: int, student_id: int, feedback_message: str, feedback_type: str) -> Dict[str, Any]:
        """학생 피드백 전송"""
        # 실제로는 피드백 테이블에 저장하고 알림 발송
        return {
            "success": True,
            "feedback_id": 12345,
            "sent_at": datetime.now().isoformat(),
            "message": "피드백이 성공적으로 전송되었습니다"
        }
    
    async def generate_weekly_report(self, db: Session, professor_id: int) -> Dict[str, Any]:
        """주간 리포트 생성"""
        return {
            "week_period": f"{datetime.now().strftime('%Y-%m-%d')} ~ {(datetime.now() + timedelta(days=6)).strftime('%Y-%m-%d')}",
            "summary": {
                "total_submissions": 45,
                "average_score": 78.2,
                "completion_rate": 0.87,
                "new_registrations": 3
            },
            "highlights": [
                "전체 평균 점수 5% 향상",
                "과제 제출률 90% 달성",
                "상위 10% 학생 성과 우수"
            ],
            "concerns": [
                "하위 20% 학생 추가 지원 필요",
                "특정 단원 이해도 부족"
            ],
            "next_week_plan": [
                "약점 단원 보충 수업",
                "우수 학생 멘토링 프로그램",
                "개별 상담 진행"
            ]
        }
    
    async def get_curriculum_recommendations(self, db: Session, professor_id: int, subject: str) -> Dict[str, Any]:
        """커리큘럼 개선 추천"""
        return {
            "subject": subject,
            "current_analysis": {
                "coverage": 0.85,
                "difficulty_balance": 0.78,
                "student_satisfaction": 0.82
            },
            "recommendations": [
                {
                    "category": "content_addition",
                    "title": "최신 기술 트렌드 반영",
                    "description": "NoSQL, 빅데이터 관련 내용 추가",
                    "priority": "high"
                },
                {
                    "category": "difficulty_adjustment",
                    "title": "난이도 조정",
                    "description": "초급 단계 내용 확충",
                    "priority": "medium"
                }
            ],
            "implementation_plan": {
                "phase1": "기존 내용 보완 (4주)",
                "phase2": "신규 내용 추가 (6주)",
                "phase3": "전체 검토 및 조정 (2주)"
            }
        } 