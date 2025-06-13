"""
AI 기반 진단 → 학과별 전문 문제 → 개인 맞춤 학습 통합 서비스

프로젝트 핵심 목적에 맞는 워크플로우:
1. AI 진단 테스트로 학습 수준 파악
2. 학과별 전문 문제 제공 (교수 검증)
3. 개인 맞춤 추천 시스템
4. 실시간 피드백 및 수준 조정
"""
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, text
from datetime import datetime, timedelta
import json
import logging

from app.models.user import User
from app.models.question import Question, DifficultyLevel
from app.models.diagnosis import TestSession, DiagnosisResult, DiagnosisSubject, DiagnosisStatus
from app.services.ai_service import ai_service
from app.services.diagnosis_service import diagnosis_service

logger = logging.getLogger(__name__)

class AdaptiveLearningService:
    """AI 기반 적응형 학습 서비스"""
    
    def __init__(self):
        self.logger = logger
        
    async def diagnose_and_recommend(
        self, 
        db: Session, 
        user_id: int, 
        subject: str
    ) -> Dict:
        """
        1단계: 진단 테스트 → 맞춤 문제 추천 통합 워크플로우
        """
        try:
            # 1. 최신 진단 결과 확인
            latest_diagnosis = self._get_latest_diagnosis(db, user_id, subject)
            
            if not latest_diagnosis or self._needs_new_diagnosis(latest_diagnosis):
                # 2. 새 진단 테스트 필요
                diagnosis_result = await self._create_adaptive_diagnosis(db, user_id, subject)
            else:
                diagnosis_result = latest_diagnosis
            
            # 3. 진단 결과 기반 맞춤 문제 추천
            recommended_problems = await self._recommend_adaptive_problems(
                db, user_id, subject, diagnosis_result
            )
            
            # 4. 학습 프로파일 업데이트
            await self._update_learning_profile(db, user_id, subject, diagnosis_result)
            
            return {
                "diagnosis": {
                    "learning_level": diagnosis_result.learning_level,
                    "accuracy_rate": diagnosis_result.accuracy_rate,
                    "weak_areas": diagnosis_result.difficulty_breakdown,
                    "conducted_at": diagnosis_result.calculated_at.isoformat()
                },
                "recommended_problems": recommended_problems,
                "learning_profile": await self._get_learning_profile(db, user_id, subject),
                "next_steps": self._generate_next_steps(diagnosis_result)
            }
            
        except Exception as e:
            self.logger.error(f"진단 및 추천 실패 (user_id={user_id}, subject={subject}): {str(e)}")
            raise
    
    async def get_specialized_problems(
        self,
        db: Session,
        user_id: int,
        subject: str,
        specialization_level: int = None,
        count: int = 10
    ) -> List[Dict]:
        """
        2단계: 학과별 전문 문제 제공 (교수 검증 우선)
        """
        try:
            # 사용자 진단 수준 확인
            user_level = await self._get_user_current_level(db, user_id, subject)
            
            # 전문성 수준 자동 조정
            if not specialization_level:
                specialization_level = self._calculate_appropriate_specialization(user_level)
            
            # 교수 검증된 전문 문제 우선 조회
            query = db.query(Question).filter(
                and_(
                    Question.subject_name == subject,
                    Question.approval_status == 'approved',
                    Question.professor_validation_level >= 2,  # 2차 검증 이상
                    Question.specialization_level == specialization_level,
                    Question.is_active == True
                )
            ).order_by(
                desc(Question.professor_validation_level),  # 검증 수준 높은 순
                desc(Question.correct_rate),                # 정답률 순
                func.random()                               # 랜덤 셔플
            ).limit(count)
            
            problems = query.all()
            
            # 부족한 경우 일반 승인 문제로 보완
            if len(problems) < count:
                additional_count = count - len(problems)
                additional_problems = db.query(Question).filter(
                    and_(
                        Question.subject_name == subject,
                        Question.approval_status == 'approved',
                        Question.specialization_level == specialization_level,
                        Question.id.notin_([p.id for p in problems])
                    )
                ).order_by(func.random()).limit(additional_count).all()
                
                problems.extend(additional_problems)
            
            # 상호작용 로그 기록
            await self._log_problem_interaction(
                db, user_id, [p.id for p in problems], "view", "professor_curated"
            )
            
            return [self._format_problem_response(p) for p in problems]
            
        except Exception as e:
            self.logger.error(f"전문 문제 조회 실패: {str(e)}")
            raise
    
    async def track_learning_interaction(
        self,
        db: Session,
        user_id: int,
        question_id: int,
        interaction_type: str,
        is_correct: Optional[bool] = None,
        time_spent: Optional[int] = None,
        confidence_level: Optional[int] = None
    ) -> Dict:
        """
        3단계: 학습 상호작용 추적 및 실시간 피드백
        """
        try:
            # 상호작용 로그 저장
            await self._log_detailed_interaction(
                db, user_id, question_id, interaction_type,
                is_correct, time_spent, confidence_level
            )
            
            # 즉시 학습 수준 조정
            if interaction_type == "attempt" and is_correct is not None:
                updated_level = await self._adjust_learning_level(
                    db, user_id, question_id, is_correct, time_spent
                )
                
                # 다음 추천 문제 미리 계산
                next_problems = await self._calculate_next_recommendations(
                    db, user_id, updated_level
                )
                
                return {
                    "feedback": self._generate_immediate_feedback(is_correct, time_spent),
                    "updated_level": updated_level,
                    "next_recommendations": next_problems,
                    "progress_summary": await self._get_progress_summary(db, user_id)
                }
            
            return {"status": "interaction_logged"}
            
        except Exception as e:
            self.logger.error(f"학습 상호작용 추적 실패: {str(e)}")
            raise
    
    async def get_personalized_study_path(
        self,
        db: Session,
        user_id: int,
        subject: str
    ) -> Dict:
        """
        4단계: 개인 맞춤 학습 경로 생성
        """
        try:
            # 학습 프로파일 조회
            profile = await self._get_learning_profile(db, user_id, subject)
            
            # 약점 영역 분석
            weak_areas = await self._analyze_weak_areas(db, user_id, subject)
            
            # 단계별 학습 경로 생성
            study_path = {
                "current_stage": self._determine_current_stage(profile),
                "weak_areas": weak_areas,
                "recommended_sequence": await self._generate_study_sequence(
                    db, user_id, subject, profile, weak_areas
                ),
                "estimated_duration": self._estimate_completion_time(profile, weak_areas),
                "milestones": self._create_learning_milestones(profile)
            }
            
            return study_path
            
        except Exception as e:
            self.logger.error(f"개인 맞춤 학습 경로 생성 실패: {str(e)}")
            raise
    
    # === 내부 헬퍼 메서드들 ===
    
    def _get_latest_diagnosis(self, db: Session, user_id: int, subject: str) -> Optional[DiagnosisResult]:
        """최신 진단 결과 조회"""
        return db.execute(text("""
            SELECT * FROM latest_diagnosis_results 
            WHERE user_id = :user_id AND subject = :subject
            LIMIT 1
        """), {"user_id": user_id, "subject": subject}).first()
    
    def _needs_new_diagnosis(self, diagnosis_result) -> bool:
        """새로운 진단이 필요한지 판단 (7일 이상 경과)"""
        if not diagnosis_result:
            return True
        return (datetime.now() - diagnosis_result.calculated_at).days >= 7
    
    async def _create_adaptive_diagnosis(self, db: Session, user_id: int, subject: str):
        """적응형 진단 테스트 생성 및 실행"""
        # 기존 diagnosis_service를 활용하되 적응형 로직 추가
        return await diagnosis_service.create_adaptive_test(db, user_id, subject)
    
    def _calculate_appropriate_specialization(self, user_level: float) -> int:
        """사용자 수준에 따른 적절한 전문성 레벨 계산"""
        if user_level < 0.3:
            return 1  # 기초
        elif user_level < 0.5:
            return 2  # 초급
        elif user_level < 0.7:
            return 3  # 중급
        elif user_level < 0.9:
            return 4  # 고급
        else:
            return 5  # 전문가
    
    async def _log_problem_interaction(
        self, db: Session, user_id: int, question_ids: List[int], 
        interaction_type: str, source: str
    ):
        """문제 상호작용 로그 기록"""
        try:
            for question_id in question_ids:
                db.execute(text("""
                    INSERT INTO learning_interactions 
                    (user_id, question_id, interaction_type, recommendation_source, created_at)
                    VALUES (:user_id, :question_id, :interaction_type, :source, NOW())
                """), {
                    "user_id": user_id,
                    "question_id": question_id,
                    "interaction_type": interaction_type,
                    "source": source
                })
            db.commit()
        except Exception as e:
            self.logger.error(f"상호작용 로그 기록 실패: {str(e)}")
    
    def _format_problem_response(self, problem: Question) -> Dict:
        """문제 응답 포맷팅"""
        return {
            "id": problem.id,
            "content": problem.content,
            "description": problem.description,
            "options": problem.choices,
            "difficulty": problem.difficulty.value if problem.difficulty else None,
            "subject": problem.subject_name,
            "specialization_level": getattr(problem, 'specialization_level', 1),
            "professor_validation_level": getattr(problem, 'professor_validation_level', 0),
            "practical_application": getattr(problem, 'practical_application', None)
        }
    
    async def _get_user_current_level(self, db: Session, user_id: int, subject: str) -> float:
        """사용자 현재 학습 수준 조회"""
        result = db.execute(text("""
            SELECT current_level FROM user_learning_profiles 
            WHERE user_id = :user_id AND subject = :subject
        """), {"user_id": user_id, "subject": subject}).first()
        
        return result.current_level if result else 0.0
    
    def _generate_next_steps(self, diagnosis_result) -> List[str]:
        """진단 결과 기반 다음 단계 추천"""
        steps = []
        
        if diagnosis_result.learning_level < 0.3:
            steps.append("기초 개념 학습부터 시작하세요")
            steps.append("이론 중심의 문제를 풀어보세요")
        elif diagnosis_result.learning_level < 0.7:
            steps.append("실무 적용 문제에 도전해보세요")
            steps.append("약점 영역을 집중적으로 보완하세요")
        else:
            steps.append("전문가 수준의 고급 문제에 도전하세요")
            steps.append("실무 프로젝트를 진행해보세요")
        
        return steps

# 전역 인스턴스
adaptive_learning_service = AdaptiveLearningService() 