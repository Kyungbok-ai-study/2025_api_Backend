"""
대시보드 관련 서비스 로직
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func, text, Date, Integer
from sqlalchemy.sql import cast
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, date
import logging

from app.models.user import User
from app.models.diagnosis import DiagnosisResult, TestResponse, LearningLevelHistory
from app.models.question import Question
from app.schemas.dashboard import (
    StudentDashboardResponse, LearningProgressResponse, PerformanceAnalyticsResponse,
    RecommendationSummaryResponse, WeeklyStudyPlanResponse, LearningMetrics,
    RecentActivity, LearningTrendPoint, SubjectProgress, StrengthWeaknessItem,
    LearningPattern, RecommendationItem, StudyPlanItem, StudyPlanPriority
)
from app.services.learning_calculator import LearningCalculator

logger = logging.getLogger(__name__)

class DashboardService:
    """대시보드 서비스"""
    
    def __init__(self):
        self.learning_calculator = LearningCalculator()
    
    async def get_student_dashboard(
        self,
        db: Session,
        user_id: int
    ) -> StudentDashboardResponse:
        """
        학생 대시보드 메인 데이터
        """
        try:
            # 사용자 정보 조회
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("사용자를 찾을 수 없습니다.")
            
            # 학습 지표 계산
            learning_metrics = await self._calculate_learning_metrics(db, user_id)
            
            # 최근 활동 조회
            recent_activities = await self._get_recent_activities(db, user_id)
            
            # 추천 문제 수 조회
            recommended_count = await self._get_recommended_problems_count(db, user_id)
            
            # 다가오는 목표 조회
            upcoming_goals = await self._get_upcoming_goals(db, user_id)
            
            return StudentDashboardResponse(
                user_id=user_id,
                user_name=user.name,
                learning_metrics=learning_metrics,
                recent_activities=recent_activities,
                recommended_problems_count=recommended_count,
                upcoming_goals=upcoming_goals,
                last_updated=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"학생 대시보드 조회 실패: {str(e)}")
            raise
    
    async def get_learning_progress(
        self,
        db: Session,
        user_id: int,
        period_days: int = 30
    ) -> LearningProgressResponse:
        """
        학습 진행 상황 조회
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=period_days)
            
            # 학습 추세 데이터 조회
            learning_trend = await self._calculate_learning_trend(db, user_id, start_date, end_date)
            
            # 과목별 진행 상황
            subject_progress = await self._calculate_subject_progress(db, user_id)
            
            # 전체 진행률 계산
            overall_progress = await self._calculate_overall_progress(db, user_id)
            
            # 현재 목표 조회
            current_goal = await self._get_current_goal(db, user_id)
            goal_achievement_rate = await self._calculate_goal_achievement_rate(db, user_id, current_goal)
            
            return LearningProgressResponse(
                user_id=user_id,
                period_days=period_days,
                overall_progress=overall_progress,
                learning_trend=learning_trend,
                subject_progress=subject_progress,
                current_goal=current_goal,
                goal_achievement_rate=goal_achievement_rate,
                generated_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"학습 진행 상황 조회 실패: {str(e)}")
            raise
    
    async def get_performance_analytics(
        self,
        db: Session,
        user_id: int,
        analysis_type: str = "comprehensive"
    ) -> PerformanceAnalyticsResponse:
        """
        성과 분석 데이터
        """
        try:
            # 강점/약점 분석
            strengths, weaknesses = await self._analyze_strengths_weaknesses(db, user_id)
            
            # 학습 패턴 분석
            learning_patterns = await self._analyze_learning_patterns(db, user_id)
            
            # 개선 추천사항
            improvements = await self._generate_improvement_recommendations(db, user_id, weaknesses)
            
            # 동급생 대비 비교 (모의 데이터)
            peer_comparison = await self._get_peer_comparison(db, user_id)
            
            return PerformanceAnalyticsResponse(
                user_id=user_id,
                analysis_type=analysis_type,
                strengths=strengths,
                weaknesses=weaknesses,
                learning_patterns=learning_patterns,
                improvement_recommendations=improvements,
                peer_comparison=peer_comparison,
                generated_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"성과 분석 조회 실패: {str(e)}")
            raise
    
    async def get_recommendation_summary(
        self,
        db: Session,
        user_id: int
    ) -> RecommendationSummaryResponse:
        """
        추천 시스템 요약
        """
        try:
            # 현재 추천 문제 수
            total_recommended = await self._get_recommended_problems_count(db, user_id)
            new_recommendations = await self._get_new_recommendations_count(db, user_id)
            
            # 개인 맞춤 추천
            personalized_recommendations = await self._get_personalized_recommendations(db, user_id)
            
            # 학습 경로 제안
            learning_path = await self._suggest_learning_path(db, user_id)
            next_milestone = await self._get_next_milestone(db, user_id)
            
            # 추천 정확도 (모의 데이터)
            recommendation_accuracy = await self._calculate_recommendation_accuracy(db, user_id)
            
            return RecommendationSummaryResponse(
                user_id=user_id,
                total_recommended_problems=total_recommended,
                new_recommendations=new_recommendations,
                personalized_recommendations=personalized_recommendations,
                suggested_learning_path=learning_path,
                next_milestone=next_milestone,
                recommendation_accuracy=recommendation_accuracy,
                generated_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"추천 요약 조회 실패: {str(e)}")
            raise
    
    async def generate_weekly_study_plan(
        self,
        db: Session,
        user_id: int,
        target_date: datetime
    ) -> WeeklyStudyPlanResponse:
        """
        주간 학습 계획 생성
        """
        try:
            # 주차 계산
            week_start = target_date - timedelta(days=target_date.weekday())
            week_end = week_start + timedelta(days=6)
            
            # 사용자 학습 수준 조회
            latest_diagnosis = db.query(DiagnosisResult).filter(
                DiagnosisResult.user_id == user_id
            ).order_by(desc(DiagnosisResult.calculated_at)).first()
            
            # 약점 영역 파악
            weak_subjects = await self._identify_weak_subjects(db, user_id)
            
            # 학습 계획 생성
            study_items = await self._generate_study_items(db, user_id, weak_subjects, latest_diagnosis)
            
            # 시간 배분 계산
            total_time, daily_distribution = await self._calculate_time_distribution(study_items)
            
            # 주간 목표 설정
            weekly_goals = await self._generate_weekly_goals(db, user_id, weak_subjects)
            success_criteria = await self._generate_success_criteria(study_items)
            
            # 개인 맞춤 조정
            adaptations = await self._generate_adaptations(db, user_id)
            
            return WeeklyStudyPlanResponse(
                user_id=user_id,
                week_start_date=week_start.date(),
                week_end_date=week_end.date(),
                study_items=study_items,
                total_estimated_time=total_time,
                daily_time_distribution=daily_distribution,
                weekly_goals=weekly_goals,
                success_criteria=success_criteria,
                adaptations=adaptations,
                generated_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"주간 학습 계획 생성 실패: {str(e)}")
            raise
    
    async def get_current_goal(
        self,
        db: Session,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        현재 학습 목표 조회
        """
        try:
            # 실제로는 학습 목표 테이블에서 조회
            # 현재는 모의 데이터 반환
            current_diagnosis = db.query(DiagnosisResult).filter(
                DiagnosisResult.user_id == user_id
            ).order_by(desc(DiagnosisResult.calculated_at)).first()
            
            if not current_diagnosis:
                return None
                
            # 기본 목표 설정 (모의)
            return {
                "target_level": 0.8,
                "target_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                "current_level": current_diagnosis.learning_level,
                "progress_percentage": (current_diagnosis.learning_level / 0.8) * 100,
                "status": "active",
                "created_at": current_diagnosis.calculated_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"현재 목표 조회 실패: {str(e)}")
            return None

    async def update_learning_goal(
        self,
        db: Session,
        user_id: int,
        target_level: float,
        target_date: datetime
    ) -> Dict[str, Any]:
        """
        학습 목표 설정/수정
        """
        try:
            # 현재 학습 수준 조회
            current_diagnosis = db.query(DiagnosisResult).filter(
                DiagnosisResult.user_id == user_id
            ).order_by(desc(DiagnosisResult.calculated_at)).first()
            
            current_level = current_diagnosis.learning_level if current_diagnosis else 0.5
            
            # 목표 달성 가능성 분석
            days_remaining = (target_date - datetime.utcnow()).days
            required_improvement = target_level - current_level
            
            # 일일 필요 학습량 계산
            daily_effort = max(30, int(required_improvement * 300))  # 분 단위
            
            # 성공 확률 계산
            success_probability = await self._calculate_success_probability(
                current_level, target_level, days_remaining
            )
            
            # 예상 완료일 계산
            estimated_completion = await self._estimate_completion_date(
                current_level, target_level, daily_effort
            )
            
            # 목표 저장 (실제로는 별도 테이블에 저장)
            goal_data = {
                "user_id": user_id,
                "target_level": target_level,
                "target_date": target_date,
                "current_level": current_level,
                "created_at": datetime.utcnow(),
                "status": "active"
            }
            
            from app.schemas.dashboard import LearningGoal, GoalUpdateResponse
            
            goal = LearningGoal(
                target_level=target_level,
                target_date=target_date,
                current_progress=(current_level / target_level) * 100 if target_level > 0 else 0,
                milestones=await self._generate_milestones(current_level, target_level, target_date)
            )
            
            response = GoalUpdateResponse(
                message="학습 목표가 설정되었습니다.",
                goal=goal,
                estimated_completion_date=estimated_completion,
                required_daily_effort=daily_effort,
                success_probability=success_probability
            )
            
            logger.info(f"학습 목표 설정 완료: user_id={user_id}, target_level={target_level}")
            return response
            
        except Exception as e:
            logger.error(f"학습 목표 설정 실패: {str(e)}")
            raise
    
    # Private 메서드들
    async def _calculate_learning_metrics(self, db: Session, user_id: int) -> LearningMetrics:
        """학습 지표 계산"""
        # 현재 학습 수준
        latest_diagnosis = db.query(DiagnosisResult).filter(
            DiagnosisResult.user_id == user_id
        ).order_by(desc(DiagnosisResult.calculated_at)).first()
        
        current_level = latest_diagnosis.learning_level if latest_diagnosis else 0.0
        
        # 주간 진행률 (모의 계산)
        weekly_progress = 15.5  # %
        
        # 오늘 푼 문제 수
        today = datetime.utcnow().date()
        problems_today = db.query(TestResponse).join(
            TestResponse.test_session
        ).filter(
            and_(
                TestResponse.test_session.has(user_id=user_id),
                func.cast(TestResponse.answered_at, Date) == today
            )
        ).count()
        
        # 이번 주 푼 문제 수
        week_start = today - timedelta(days=today.weekday())
        problems_this_week = db.query(TestResponse).join(
            TestResponse.test_session
        ).filter(
            and_(
                TestResponse.test_session.has(user_id=user_id),
                func.cast(TestResponse.answered_at, Date) >= week_start
            )
        ).count()
        
        # 정답률 계산
        total_responses = db.query(TestResponse).join(
            TestResponse.test_session
        ).filter(TestResponse.test_session.has(user_id=user_id)).count()
        
        correct_responses = db.query(TestResponse).join(
            TestResponse.test_session
        ).filter(
            and_(
                TestResponse.test_session.has(user_id=user_id),
                TestResponse.is_correct == True
            )
        ).count()
        
        accuracy_rate = correct_responses / total_responses if total_responses > 0 else 0.0
        
        # 연속 학습 일수 (모의 데이터)
        study_streak = 7
        
        return LearningMetrics(
            current_level=current_level,
            weekly_progress=weekly_progress,
            problems_solved_today=problems_today,
            problems_solved_this_week=problems_this_week,
            accuracy_rate=accuracy_rate,
            study_streak_days=study_streak
        )
    
    async def _get_recent_activities(self, db: Session, user_id: int, limit: int = 5) -> List[RecentActivity]:
        """최근 활동 조회"""
        activities = []
        
        # 최근 진단 테스트
        recent_diagnoses = db.query(DiagnosisResult).filter(
            DiagnosisResult.user_id == user_id
        ).order_by(desc(DiagnosisResult.calculated_at)).limit(2).all()
        
        for diagnosis in recent_diagnoses:
            activities.append(RecentActivity(
                activity_type="diagnosis_test",
                description=f"진단 테스트 완료 (학습 수준: {diagnosis.learning_level:.2f})",
                timestamp=diagnosis.calculated_at,
                result={
                    "learning_level": diagnosis.learning_level,
                    "accuracy_rate": diagnosis.accuracy_rate
                }
            ))
        
        # 최근 문제 풀이
        recent_responses = db.query(TestResponse).join(
            TestResponse.test_session
        ).filter(
            TestResponse.test_session.has(user_id=user_id)
        ).order_by(desc(TestResponse.answered_at)).limit(3).all()
        
        for response in recent_responses:
            activities.append(RecentActivity(
                activity_type="problem_solved",
                description=f"문제 해결 ({'정답' if response.is_correct else '오답'})",
                timestamp=response.answered_at,
                result={
                    "is_correct": response.is_correct,
                    "time_spent": response.time_spent_seconds
                }
            ))
        
        # 시간순 정렬
        activities.sort(key=lambda x: x.timestamp, reverse=True)
        return activities[:limit]
    
    async def _get_recommended_problems_count(self, db: Session, user_id: int) -> int:
        """추천 문제 수 조회"""
        # 실제로는 추천 알고리즘을 통해 계산
        # 현재는 사용자 수준에 따른 모의 데이터
        latest_diagnosis = db.query(DiagnosisResult).filter(
            DiagnosisResult.user_id == user_id
        ).order_by(desc(DiagnosisResult.calculated_at)).first()
        
        if latest_diagnosis:
            # 학습 수준에 따라 추천 문제 수 조정
            base_count = 20
            level_multiplier = 1 + latest_diagnosis.learning_level
            return int(base_count * level_multiplier)
        
        return 15  # 기본값
    
    async def _get_upcoming_goals(self, db: Session, user_id: int) -> List[str]:
        """다가오는 목표 조회"""
        # 실제로는 목표 테이블에서 조회
        return [
            "데이터베이스 기초 완성",
            "알고리즘 중급 수준 도달",
            "이번 주 20문제 해결"
        ]
    
    async def _calculate_learning_trend(
        self, 
        db: Session, 
        user_id: int, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[LearningTrendPoint]:
        """학습 추세 계산"""
        trend_points = []
        
        # 기간 내 학습 이력 조회
        history = db.query(LearningLevelHistory).filter(
            and_(
                LearningLevelHistory.user_id == user_id,
                LearningLevelHistory.measured_at.between(start_date, end_date)
            )
        ).order_by(LearningLevelHistory.measured_at).all()
        
        # 일별 데이터 집계
        daily_data = {}
        for record in history:
            date_key = record.measured_at.date()
            if date_key not in daily_data:
                daily_data[date_key] = {
                    "learning_level": record.learning_level,
                    "problems_solved": 0,
                    "accuracy_rate": 0.0,
                    "time_spent": 0
                }
        
        # 일별 문제 풀이 데이터 추가
        daily_responses = db.query(
            func.cast(TestResponse.answered_at, Date).label('date'),
            func.count(TestResponse.id).label('problems_solved'),
            func.avg(cast(TestResponse.is_correct, Integer)).label('accuracy_rate'),
            func.sum(TestResponse.time_spent_seconds).label('time_spent')
        ).join(TestResponse.test_session).filter(
            and_(
                TestResponse.test_session.has(user_id=user_id),
                TestResponse.answered_at.between(start_date, end_date)
            )
        ).group_by(func.cast(TestResponse.answered_at, Date)).all()
        
        for row in daily_responses:
            if row.date in daily_data:
                daily_data[row.date].update({
                    "problems_solved": row.problems_solved or 0,
                    "accuracy_rate": float(row.accuracy_rate or 0.0),
                    "time_spent": int((row.time_spent or 0) / 60)  # 분 단위
                })
        
        # LearningTrendPoint 객체 생성
        for date_key, data in sorted(daily_data.items()):
            trend_points.append(LearningTrendPoint(
                date=date_key,
                learning_level=data["learning_level"],
                problems_solved=data["problems_solved"],
                accuracy_rate=data["accuracy_rate"],
                time_spent_minutes=data["time_spent"]
            ))
        
        return trend_points
    
    async def _calculate_subject_progress(self, db: Session, user_id: int) -> List[SubjectProgress]:
        """과목별 진행 상황 계산"""
        # 과목별 학습 데이터 집계
        subject_stats = db.query(
            Question.subject_name,
            func.count(TestResponse.id).label('total_responses'),
            func.avg(cast(TestResponse.is_correct, Integer)).label('accuracy_rate'),
            func.max(TestResponse.answered_at).label('last_activity')
        ).join(TestResponse).join(TestResponse.test_session).filter(
            TestResponse.test_session.has(user_id=user_id)
        ).group_by(Question.subject_name).all()
        
        progress_list = []
        for row in subject_stats:
            subject_name = row.subject_name or "일반"
            accuracy = float(row.accuracy_rate or 0.0)
            
            # 현재 수준 계산 (정확도 기반)
            current_level = min(1.0, accuracy * 1.2)  # 약간의 보정
            
            # 목표 수준 (기본 0.8)
            target_level = 0.8
            
            # 진행률 계산
            progress_percentage = min(100.0, (current_level / target_level) * 100)
            
            progress_list.append(SubjectProgress(
                subject=subject_name,
                current_level=current_level,
                target_level=target_level,
                progress_percentage=progress_percentage,
                problems_solved=row.total_responses or 0,
                last_activity=row.last_activity
            ))
        
        return progress_list
    
    async def _calculate_overall_progress(self, db: Session, user_id: int) -> float:
        """전체 진행률 계산"""
        latest_diagnosis = db.query(DiagnosisResult).filter(
            DiagnosisResult.user_id == user_id
        ).order_by(desc(DiagnosisResult.calculated_at)).first()
        
        if latest_diagnosis:
            # 학습 수준을 백분율로 변환
            return latest_diagnosis.learning_level * 100
        
        return 0.0
    
    async def _get_current_goal(self, db: Session, user_id: int) -> Optional[Dict[str, Any]]:
        """현재 목표 조회"""
        # 실제로는 목표 테이블에서 조회
        return {
            "target_level": 0.8,
            "target_date": "2024-06-30",
            "description": "데이터베이스 전문가 수준 달성"
        }
    
    async def _calculate_goal_achievement_rate(
        self, 
        db: Session, 
        user_id: int, 
        current_goal: Optional[Dict[str, Any]]
    ) -> Optional[float]:
        """목표 달성률 계산"""
        if not current_goal:
            return None
        
        latest_diagnosis = db.query(DiagnosisResult).filter(
            DiagnosisResult.user_id == user_id
        ).order_by(desc(DiagnosisResult.calculated_at)).first()
        
        if latest_diagnosis and current_goal.get("target_level"):
            current_level = latest_diagnosis.learning_level
            target_level = current_goal["target_level"]
            return min(100.0, (current_level / target_level) * 100)
        
        return 0.0
    
    async def _analyze_strengths_weaknesses(
        self, 
        db: Session, 
        user_id: int
    ) -> tuple[List[StrengthWeaknessItem], List[StrengthWeaknessItem]]:
        """강점/약점 분석"""
        strengths = []
        weaknesses = []
        
        # 과목별 성과 분석
        subject_performance = db.query(
            Question.subject_name,
            func.avg(cast(TestResponse.is_correct, Integer)).label('accuracy'),
            func.count(TestResponse.id).label('total_responses')
        ).join(TestResponse).join(TestResponse.test_session).filter(
            TestResponse.test_session.has(user_id=user_id)
        ).group_by(Question.subject_name).all()
        
        for row in subject_performance:
            subject_name = row.subject_name or "일반"
            accuracy = float(row.accuracy or 0.0)
            total = row.total_responses or 0
            
            if accuracy >= 0.8 and total >= 5:
                strengths.append(StrengthWeaknessItem(
                    category=subject_name,
                    score=accuracy,
                    description=f"{subject_name} 영역에서 우수한 성과",
                    evidence=[f"정확도 {accuracy:.1%}", f"{total}문제 해결"]
                ))
            elif accuracy < 0.5 and total >= 3:
                weaknesses.append(StrengthWeaknessItem(
                    category=subject_name,
                    score=accuracy,
                    description=f"{subject_name} 영역 개선 필요",
                    evidence=[f"정확도 {accuracy:.1%}", f"추가 학습 권장"]
                ))
        
        return strengths, weaknesses
    
    async def _analyze_learning_patterns(self, db: Session, user_id: int) -> List[LearningPattern]:
        """학습 패턴 분석"""
        patterns = []
        
        # 시간대별 학습 패턴
        time_pattern = db.query(
            func.extract('hour', TestResponse.answered_at).label('hour'),
            func.count(TestResponse.id).label('count'),
            func.avg(cast(TestResponse.is_correct, Integer)).label('accuracy')
        ).join(TestResponse.test_session).filter(
            TestResponse.test_session.has(user_id=user_id)
        ).group_by(func.extract('hour', TestResponse.answered_at)).all()
        
        if time_pattern:
            # 가장 활발한 시간대 찾기
            most_active_hour = max(time_pattern, key=lambda x: x.count)
            
            patterns.append(LearningPattern(
                pattern_type="time_preference",
                description=f"{int(most_active_hour.hour)}시경에 가장 활발한 학습",
                frequency="daily",
                impact="positive",
                recommendation="이 시간대에 어려운 문제를 집중적으로 해결하세요"
            ))
        
        # 연속 학습 패턴 (모의 데이터)
        patterns.append(LearningPattern(
            pattern_type="consistency",
            description="꾸준한 일일 학습 습관",
            frequency="daily",
            impact="positive",
            recommendation="현재 학습 습관을 유지하세요"
        ))
        
        return patterns
    
    async def _generate_improvement_recommendations(
        self, 
        db: Session, 
        user_id: int, 
        weaknesses: List[StrengthWeaknessItem]
    ) -> List[str]:
        """개선 추천사항 생성"""
        recommendations = []
        
        for weakness in weaknesses:
            if weakness.score < 0.3:
                recommendations.append(f"{weakness.category} 기초 개념부터 다시 학습하세요")
            elif weakness.score < 0.6:
                recommendations.append(f"{weakness.category} 연습 문제를 더 많이 풀어보세요")
            else:
                recommendations.append(f"{weakness.category} 심화 문제에 도전해보세요")
        
        if not recommendations:
            recommendations = [
                "전반적으로 우수한 성과를 보이고 있습니다",
                "새로운 영역에 도전해보세요",
                "고급 문제로 실력을 더욱 향상시키세요"
            ]
        
        return recommendations
    
    async def _get_peer_comparison(self, db: Session, user_id: int) -> Optional[Dict[str, Any]]:
        """동급생 대비 성과 (모의 데이터)"""
        return {
            "percentile": 75,
            "average_accuracy": 0.68,
            "user_accuracy": 0.73,
            "ranking": "상위 25%"
        }
    
    async def _get_new_recommendations_count(self, db: Session, user_id: int) -> int:
        """새로운 추천 문제 수"""
        # 실제로는 마지막 로그인 이후 생성된 추천 수
        return 5
    
    async def _get_personalized_recommendations(self, db: Session, user_id: int) -> List[RecommendationItem]:
        """개인 맞춤 추천"""
        recommendations = []
        
        # 약점 기반 추천
        latest_diagnosis = db.query(DiagnosisResult).filter(
            DiagnosisResult.user_id == user_id
        ).order_by(desc(DiagnosisResult.calculated_at)).first()
        
        if latest_diagnosis and latest_diagnosis.learning_level < 0.6:
            recommendations.append(RecommendationItem(
                type="review",
                title="기초 개념 복습",
                description="기본기를 탄탄히 하기 위한 복습 문제",
                priority="high",
                estimated_time=30,
                difficulty=2
            ))
        
        recommendations.extend([
            RecommendationItem(
                type="practice",
                title="오답 문제 재도전",
                description="이전에 틀린 문제들을 다시 풀어보세요",
                priority="medium",
                estimated_time=20,
                difficulty=3
            ),
            RecommendationItem(
                type="challenge",
                title="새로운 유형 도전",
                description="아직 시도하지 않은 문제 유형",
                priority="low",
                estimated_time=25,
                difficulty=4
            )
        ])
        
        return recommendations
    
    async def _suggest_learning_path(self, db: Session, user_id: int) -> List[str]:
        """학습 경로 제안"""
        return [
            "1단계: 데이터베이스 기초 개념 정리",
            "2단계: SQL 기본 문법 연습",
            "3단계: 정규화와 설계 이해",
            "4단계: 고급 쿼리 작성법",
            "5단계: 성능 최적화 기법"
        ]
    
    async def _get_next_milestone(self, db: Session, user_id: int) -> Optional[str]:
        """다음 마일스톤"""
        latest_diagnosis = db.query(DiagnosisResult).filter(
            DiagnosisResult.user_id == user_id
        ).order_by(desc(DiagnosisResult.calculated_at)).first()
        
        if latest_diagnosis:
            level = latest_diagnosis.learning_level
            if level < 0.3:
                return "기초 수준 달성 (30%)"
            elif level < 0.6:
                return "중급 수준 달성 (60%)"
            elif level < 0.8:
                return "고급 수준 달성 (80%)"
            else:
                return "전문가 수준 달성 (95%)"
        
        return "첫 진단 테스트 완료"
    
    async def _calculate_recommendation_accuracy(self, db: Session, user_id: int) -> Optional[float]:
        """추천 정확도 계산"""
        # 실제로는 추천된 문제의 정답률과 예상 정답률 비교
        return 0.78  # 모의 데이터
    
    async def _identify_weak_subjects(self, db: Session, user_id: int) -> List[str]:
        """약점 과목 식별"""
        subject_performance = db.query(
            Question.subject_name,
            func.avg(cast(TestResponse.is_correct, Integer)).label('accuracy')
        ).join(TestResponse).join(TestResponse.test_session).filter(
            TestResponse.test_session.has(user_id=user_id)
        ).group_by(Question.subject_name).all()
        
        weak_subjects = []
        for row in subject_performance:
            if row.accuracy and row.accuracy < 0.6:
                weak_subjects.append(row.subject_name or "일반")
        
        return weak_subjects or ["데이터베이스"]  # 기본값
    
    async def _generate_study_items(
        self, 
        db: Session, 
        user_id: int, 
        weak_subjects: List[str], 
        latest_diagnosis: Optional[DiagnosisResult]
    ) -> List[StudyPlanItem]:
        """학습 계획 항목 생성"""
        study_items = []
        
        # 약점 과목 기반 학습 계획
        for i, subject in enumerate(weak_subjects[:3]):  # 최대 3개 과목
            difficulty = 2 if latest_diagnosis and latest_diagnosis.learning_level < 0.5 else 3
            
            study_items.append(StudyPlanItem(
                id=f"study_{i+1}",
                title=f"{subject} 기초 문제 풀이",
                description=f"{subject} 영역의 기본 개념 문제 해결",
                subject=subject,
                priority=StudyPlanPriority.HIGH if i == 0 else StudyPlanPriority.MEDIUM,
                estimated_duration=30,
                difficulty=difficulty,
                prerequisites=[],
                learning_objectives=[f"{subject} 기본 개념 이해", "정확도 70% 이상 달성"],
                recommended_day=i + 1  # 월, 화, 수
            ))
        
        # 복습 계획
        study_items.append(StudyPlanItem(
            id="review_1",
            title="오답 노트 정리",
            description="이전에 틀린 문제들 다시 정리하고 이해하기",
            subject="전체",
            priority=StudyPlanPriority.MEDIUM,
            estimated_duration=20,
            difficulty=2,
            prerequisites=[],
            learning_objectives=["오답 원인 분석", "실수 방지 전략 수립"],
            recommended_day=5  # 금
        ))
        
        return study_items
    
    async def _calculate_time_distribution(
        self, 
        study_items: List[StudyPlanItem]
    ) -> tuple[int, Dict[str, int]]:
        """시간 배분 계산"""
        total_time = sum(item.estimated_duration for item in study_items)
        
        # 요일별 시간 배분
        daily_distribution = {}
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        for item in study_items:
            day_name = weekdays[item.recommended_day - 1]
            if day_name not in daily_distribution:
                daily_distribution[day_name] = 0
            daily_distribution[day_name] += item.estimated_duration
        
        return total_time, daily_distribution
    
    async def _generate_weekly_goals(self, db: Session, user_id: int, weak_subjects: List[str]) -> List[str]:
        """주간 목표 생성"""
        goals = []
        
        if weak_subjects:
            goals.append(f"{weak_subjects[0]} 영역 70% 이상 정확도 달성")
        
        goals.extend([
            "일일 최소 10문제 해결",
            "오답 노트 작성 및 정리",
            "학습 계획 준수율 80% 이상"
        ])
        
        return goals
    
    async def _generate_success_criteria(self, study_items: List[StudyPlanItem]) -> List[str]:
        """성공 기준 생성"""
        return [
            "계획된 학습 시간의 80% 이상 달성",
            "각 과목별 목표 정확도 달성",
            "주간 목표 완료",
            "꾸준한 일일 학습 실천"
        ]
    
    async def _generate_adaptations(self, db: Session, user_id: int) -> List[str]:
        """개인 맞춤 조정사항"""
        return [
            "오전 시간대 집중 학습 권장",
            "어려운 문제는 힌트 활용 적극 권장",
            "15분 학습 후 5분 휴식 패턴 적용"
        ]
    
    async def _calculate_success_probability(
        self, 
        current_level: float, 
        target_level: float, 
        days_remaining: int
    ) -> float:
        """목표 달성 성공 확률 계산"""
        required_improvement = target_level - current_level
        
        # 간단한 모델: 일일 개선률 0.01 가정
        expected_improvement = days_remaining * 0.01
        
        if expected_improvement >= required_improvement:
            return min(0.95, 0.7 + (expected_improvement / required_improvement) * 0.25)
        else:
            return max(0.1, 0.7 * (expected_improvement / required_improvement))
    
    async def _estimate_completion_date(
        self, 
        current_level: float, 
        target_level: float, 
        daily_effort: int
    ) -> datetime:
        """예상 완료일 계산"""
        required_improvement = target_level - current_level
        
        # 일일 노력에 따른 개선률 (분당 0.0005 개선 가정)
        daily_improvement_rate = (daily_effort / 60) * 0.0005
        
        days_needed = required_improvement / daily_improvement_rate if daily_improvement_rate > 0 else 365
        days_needed = min(365, max(1, days_needed))  # 1일~365일 제한
        
        return datetime.utcnow() + timedelta(days=int(days_needed))
    
    async def _generate_milestones(
        self, 
        current_level: float, 
        target_level: float, 
        target_date: datetime
    ) -> List[Dict[str, Any]]:
        """마일스톤 생성"""
        milestones = []
        
        improvement_needed = target_level - current_level
        days_remaining = (target_date - datetime.utcnow()).days
        
        if days_remaining > 0:
            # 25%, 50%, 75%, 100% 지점 마일스톤
            for percent in [0.25, 0.5, 0.75, 1.0]:
                milestone_level = current_level + (improvement_needed * percent)
                milestone_date = datetime.utcnow() + timedelta(days=int(days_remaining * percent))
                
                milestones.append({
                    "target_level": round(milestone_level, 2),
                    "target_date": milestone_date.isoformat(),
                    "description": f"{int(percent * 100)}% 목표 달성",
                    "completed": False
                })
        
        return milestones

# 싱글톤 인스턴스
dashboard_service = DashboardService() 