"""
다중 선택지 진단 테스트 서비스 (1문제 30선택지)
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
import logging
import random

from app.models.diagnosis import (
    TestSession, MultiChoiceTestSession, MultiChoiceTestResponse, 
    DiagnosisResult, LearningLevelHistory, DiagnosisStatus, DiagnosisSubject
)
from app.models.question import Question
from app.schemas.diagnosis import (
    MultiChoiceTestCreate, MultiChoiceAnswerSubmit, MultiChoiceTestResponse,
    MultiChoiceResultResponse, ChoiceStrategyAnalysis, ConfidenceLevel,
    QuestionItem
)

logger = logging.getLogger(__name__)

class MultiChoiceService:
    """다중 선택지 진단 테스트 서비스"""
    
    def __init__(self):
        pass
    
    async def create_multi_choice_test(
        self, 
        db: Session, 
        user_id: int, 
        test_data: MultiChoiceTestCreate
    ) -> MultiChoiceTestResponse:
        """
        다중 선택지 진단 테스트 생성
        - 1개 문제 + 30개 선택지
        - 정답 1개가 포함된 선택지 목록
        """
        try:
            # 기존 활성 세션 확인
            existing_session = db.query(TestSession).filter(
                and_(
                    TestSession.user_id == user_id,
                    TestSession.status == DiagnosisStatus.ACTIVE,
                    TestSession.subject == test_data.subject
                )
            ).first()
            
            if existing_session:
                # 기존 세션이 만료되지 않았다면 해당 세션 반환
                if existing_session.expires_at and existing_session.expires_at > datetime.now(timezone.utc):
                    return await self._build_multi_choice_response(db, existing_session)
                else:
                    # 만료된 세션은 EXPIRED로 변경
                    existing_session.status = DiagnosisStatus.EXPIRED
                    db.commit()
            
            # 새 테스트 세션 생성
            test_session = TestSession(
                user_id=user_id,
                subject=test_data.subject,
                status=DiagnosisStatus.ACTIVE,
                max_time_minutes=test_data.max_time_minutes,
                total_questions=1,  # 1문제만
                expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
                description=test_data.description or f"{test_data.subject.value} 다중 선택지 진단 테스트"
            )
            
            db.add(test_session)
            db.commit()
            db.refresh(test_session)
            
            # 문제 생성 (임시로 저장)
            question = Question(
                content=test_data.question_content,
                question_type="multi_choice_selection",
                subject_name=test_data.subject.value,
                is_active=True,
                choices=test_data.choices,
                correct_answer=test_data.choices[test_data.correct_choice_index],
                created_by_id=user_id
            )
            
            db.add(question)
            db.commit()
            db.refresh(question)
            
            # 선택지 섞기 (옵션)
            choices = test_data.choices.copy()
            correct_index = test_data.correct_choice_index
            
            if test_data.shuffle_choices:
                # 선택지와 정답 인덱스를 함께 섞기
                choice_pairs = [(i, choice) for i, choice in enumerate(choices)]
                random.shuffle(choice_pairs)
                
                choices = [pair[1] for pair in choice_pairs]
                # 새로운 정답 인덱스 찾기
                for new_idx, (old_idx, _) in enumerate(choice_pairs):
                    if old_idx == correct_index:
                        correct_index = new_idx
                        break
            
            # 다중 선택지 세션 생성
            multi_choice_session = MultiChoiceTestSession(
                test_session_id=test_session.id,
                question_id=question.id,
                choices=choices,
                correct_choice_index=correct_index,
                max_choices=30,
                shuffle_choices=test_data.shuffle_choices,
                choice_metadata={
                    "original_order": test_data.choices,
                    "original_correct_index": test_data.correct_choice_index,
                    "shuffle_applied": test_data.shuffle_choices
                }
            )
            
            db.add(multi_choice_session)
            db.commit()
            db.refresh(multi_choice_session)
            
            logger.info(f"다중 선택지 테스트 생성: user_id={user_id}, session_id={test_session.id}")
            
            return await self._build_multi_choice_response(db, test_session)
            
        except Exception as e:
            logger.error(f"다중 선택지 테스트 생성 실패: {str(e)}")
            db.rollback()
            raise
    
    async def submit_multi_choice_answer(
        self,
        db: Session,
        user_id: int,
        answer_data: MultiChoiceAnswerSubmit
    ) -> MultiChoiceResultResponse:
        """
        다중 선택지 답안 제출 및 결과 계산
        """
        try:
            # 테스트 세션 검증
            test_session = db.query(TestSession).filter(
                and_(
                    TestSession.id == answer_data.test_session_id,
                    TestSession.user_id == user_id,
                    TestSession.status == DiagnosisStatus.ACTIVE
                )
            ).first()
            
            if not test_session:
                raise ValueError("유효하지 않은 테스트 세션입니다.")
            
            if test_session.expires_at and test_session.expires_at < datetime.now(timezone.utc):
                test_session.status = DiagnosisStatus.EXPIRED
                db.commit()
                raise ValueError("테스트 시간이 만료되었습니다.")
            
            # 다중 선택지 세션 조회
            multi_session = db.query(MultiChoiceTestSession).filter(
                MultiChoiceTestSession.test_session_id == answer_data.test_session_id
            ).first()
            
            if not multi_session:
                raise ValueError("다중 선택지 세션을 찾을 수 없습니다.")
            
            # 답안 채점
            is_correct = answer_data.selected_choice_index == multi_session.correct_choice_index
            correct_choice = multi_session.choices[multi_session.correct_choice_index]
            
            # 전략 분석
            strategy_analysis = await self._analyze_choice_strategy(
                answer_data, multi_session, is_correct
            )
            
            # 응답 저장
            response = MultiChoiceTestResponse(
                session_id=multi_session.id,
                selected_choice_index=answer_data.selected_choice_index,
                selected_choice_content=answer_data.selected_choice_content,
                is_correct=is_correct,
                eliminated_choices=answer_data.eliminated_choices or [],
                confidence_level=answer_data.confidence_level.value,
                choice_changes=len([event for event in answer_data.choice_timeline 
                                    if event.get('action') == 'selection_change']),
                time_spent_seconds=answer_data.time_spent_seconds,
                choice_timeline=answer_data.choice_timeline,
                elimination_strategy=strategy_analysis.dict(),
                decision_pattern=strategy_analysis.strategy_type
            )
            
            db.add(response)
            
            # 학습 수준 계산
            learning_level = await self._calculate_learning_level(
                is_correct, strategy_analysis, answer_data.time_spent_seconds
            )
            
            # 인지 능력 분석
            cognitive_abilities = await self._analyze_cognitive_abilities(
                strategy_analysis, answer_data.time_spent_seconds, is_correct
            )
            
            # 진단 결과 저장
            diagnosis_result = DiagnosisResult(
                test_session_id=test_session.id,
                user_id=user_id,
                learning_level=learning_level,
                total_score=1.0 if is_correct else 0.0,
                max_possible_score=1.0,
                accuracy_rate=1.0 if is_correct else 0.0,
                total_questions=1,
                correct_answers=1 if is_correct else 0,
                total_time_spent=answer_data.time_spent_seconds,
                choice_strategy_analysis=strategy_analysis.dict(),
                elimination_effectiveness=strategy_analysis.elimination_effectiveness,
                decision_confidence_score=self._map_confidence_to_score(answer_data.confidence_level),
                cognitive_load_analysis={
                    "cognitive_abilities": cognitive_abilities,
                    "time_efficiency": self._calculate_time_efficiency(answer_data.time_spent_seconds),
                    "decision_complexity": strategy_analysis.cognitive_load_score
                }
            )
            
            db.add(diagnosis_result)
            
            # 테스트 세션 완료 처리
            test_session.status = DiagnosisStatus.COMPLETED
            test_session.completed_at = datetime.now(timezone.utc)
            
            # 커밋하여 diagnosis_result.id 생성
            db.commit()
            db.refresh(diagnosis_result)
            
            # 학습 수준 이력 저장
            await self._save_learning_history(db, user_id, diagnosis_result, test_session.subject)
            
            # 최종 커밋
            db.commit()
            
            # 피드백 생성
            feedback_message = await self._generate_feedback(
                is_correct, learning_level, strategy_analysis, cognitive_abilities
            )
            
            recommended_skills = await self._generate_skill_recommendations(
                learning_level, strategy_analysis, cognitive_abilities
            )
            
            improvement_areas = await self._identify_improvement_areas(
                is_correct, strategy_analysis, cognitive_abilities
            )
            
            # 문제 정보 조회
            question = db.query(Question).filter(Question.id == multi_session.question_id).first()
            
            logger.info(f"다중 선택지 테스트 완료: user_id={user_id}, correct={is_correct}, level={learning_level:.3f}")
            
            return MultiChoiceResultResponse(
                test_session_id=test_session.id,
                user_id=user_id,
                question_content=question.content,
                selected_choice=answer_data.selected_choice_content,
                correct_choice=correct_choice,
                is_correct=is_correct,
                time_spent_seconds=answer_data.time_spent_seconds,
                confidence_level=answer_data.confidence_level,
                strategy_analysis=strategy_analysis,
                learning_level=learning_level,
                cognitive_abilities=cognitive_abilities,
                decision_quality=await self._calculate_decision_quality(strategy_analysis, is_correct),
                feedback_message=feedback_message,
                recommended_skills=recommended_skills,
                improvement_areas=improvement_areas,
                completed_at=diagnosis_result.calculated_at
            )
            
        except Exception as e:
            logger.error(f"다중 선택지 답안 제출 실패: {str(e)}")
            db.rollback()
            raise
    
    # Private 메서드들
    async def _build_multi_choice_response(self, db: Session, test_session: TestSession) -> MultiChoiceTestResponse:
        """다중 선택지 테스트 응답 구성"""
        multi_session = db.query(MultiChoiceTestSession).filter(
            MultiChoiceTestSession.test_session_id == test_session.id
        ).first()
        
        if not multi_session:
            raise ValueError("다중 선택지 세션을 찾을 수 없습니다.")
        
        question = db.query(Question).filter(Question.id == multi_session.question_id).first()
        
        question_item = QuestionItem(
            id=question.id,
            content=question.content,
            question_type=question.question_type,
            difficulty="mixed",  # 30개 선택지에 다양한 난이도 포함
            choices=multi_session.choices,
            correct_answer=multi_session.choices[multi_session.correct_choice_index]
        )
        
        return MultiChoiceTestResponse(
            test_session_id=test_session.id,
            user_id=test_session.user_id,
            question=question_item,
            choices=multi_session.choices,
            max_time_minutes=test_session.max_time_minutes,
            expires_at=test_session.expires_at,
            created_at=test_session.created_at
        )
    
    async def _analyze_choice_strategy(
        self, 
        answer_data: MultiChoiceAnswerSubmit, 
        multi_session: MultiChoiceTestSession,
        is_correct: bool
    ) -> ChoiceStrategyAnalysis:
        """선택 전략 분석"""
        eliminated_count = len(answer_data.eliminated_choices) if answer_data.eliminated_choices else 0
        
        # 제거 효과성 계산
        elimination_effectiveness = 0.0
        if eliminated_count > 0:
            # 정답을 제거하지 않았고, 오답을 많이 제거했으면 효과적
            correct_eliminated = multi_session.correct_choice_index in (answer_data.eliminated_choices or [])
            if not correct_eliminated:
                elimination_effectiveness = min(eliminated_count / 29, 1.0)  # 최대 29개 오답 제거 가능
            else:
                elimination_effectiveness = 0.0  # 정답을 제거했으면 비효과적
        
        # 선택 변경 횟수
        choice_changes = len([event for event in (answer_data.choice_timeline or []) 
                             if event.get('action') == 'selection_change'])
        
        # 의사결정 패턴 분석
        decision_pattern = self._determine_decision_pattern(
            eliminated_count, choice_changes, answer_data.time_spent_seconds, is_correct
        )
        
        # 인지 부하 점수 (시간, 변경 횟수, 제거 수를 종합)
        cognitive_load_score = self._calculate_cognitive_load(
            answer_data.time_spent_seconds, choice_changes, eliminated_count
        )
        
        # 전략 유형 결정
        strategy_type = self._determine_strategy_type(
            eliminated_count, choice_changes, answer_data.time_spent_seconds
        )
        
        return ChoiceStrategyAnalysis(
            elimination_count=eliminated_count,
            elimination_effectiveness=elimination_effectiveness,
            choice_changes=choice_changes,
            decision_pattern=decision_pattern,
            cognitive_load_score=cognitive_load_score,
            strategy_type=strategy_type
        )
    
    def _determine_decision_pattern(self, eliminated_count: int, choice_changes: int, time_spent: int, is_correct: bool) -> str:
        """의사결정 패턴 결정"""
        if eliminated_count >= 20 and choice_changes <= 2:
            return "systematic_elimination"
        elif choice_changes >= 5:
            return "uncertain_exploration"
        elif time_spent < 60 and choice_changes <= 1:
            return "quick_intuitive"
        elif eliminated_count >= 10 and is_correct:
            return "strategic_narrowing"
        elif eliminated_count < 5 and choice_changes >= 3:
            return "random_searching"
        else:
            return "balanced_approach"
    
    def _calculate_cognitive_load(self, time_spent: int, choice_changes: int, eliminated_count: int) -> float:
        """인지 부하 점수 계산 (0.0-1.0, 높을수록 부하가 큼)"""
        # 시간 요소 (300초 = 5분을 기준으로 정규화)
        time_factor = min(time_spent / 300, 1.0)
        
        # 변경 요소 (10번 이상 변경하면 높은 부하)
        change_factor = min(choice_changes / 10, 1.0)
        
        # 제거 요소 (제거를 많이 할수록 부하 증가, 하지만 전략적일 수 있음)
        elimination_factor = min(eliminated_count / 25, 1.0) * 0.5  # 가중치 낮게
        
        return (time_factor * 0.5 + change_factor * 0.3 + elimination_factor * 0.2)
    
    def _determine_strategy_type(self, eliminated_count: int, choice_changes: int, time_spent: int) -> str:
        """전략 유형 결정"""
        if eliminated_count >= 15 and choice_changes <= 3:
            return "systematic"
        elif choice_changes >= 4 or (eliminated_count < 5 and choice_changes >= 2):
            return "random"
        else:
            return "intuitive"
    
    async def _calculate_learning_level(self, is_correct: bool, strategy: ChoiceStrategyAnalysis, time_spent: int) -> float:
        """학습 수준 계산"""
        base_score = 1.0 if is_correct else 0.0
        
        # 전략 보너스/페널티
        strategy_bonus = 0.0
        if is_correct:
            # 효율적인 전략 사용 시 보너스
            if strategy.elimination_effectiveness > 0.7:
                strategy_bonus += 0.1
            if strategy.strategy_type == "systematic":
                strategy_bonus += 0.05
            if time_spent < 180:  # 3분 이내 해결
                strategy_bonus += 0.05
        else:
            # 틀렸어도 좋은 전략 사용 시 부분 점수
            if strategy.elimination_effectiveness > 0.5:
                strategy_bonus += 0.2
            if strategy.strategy_type == "systematic":
                strategy_bonus += 0.1
        
        return min(base_score + strategy_bonus, 1.0)
    
    async def _analyze_cognitive_abilities(self, strategy: ChoiceStrategyAnalysis, time_spent: int, is_correct: bool) -> Dict[str, float]:
        """인지 능력 분석"""
        return {
            "pattern_recognition": 0.8 if is_correct else 0.4 + (strategy.elimination_effectiveness * 0.4),
            "logical_reasoning": strategy.elimination_effectiveness,
            "decision_making": 1.0 - strategy.cognitive_load_score,
            "attention_control": 1.0 - min(strategy.choice_changes / 10, 1.0),
            "time_management": max(0.0, 1.0 - (time_spent - 120) / 300) if time_spent > 120 else 1.0,
            "strategic_thinking": 0.9 if strategy.strategy_type == "systematic" else 0.5
        }
    
    def _map_confidence_to_score(self, confidence: ConfidenceLevel) -> float:
        """확신도를 점수로 매핑"""
        mapping = {
            ConfidenceLevel.LOW: 0.3,
            ConfidenceLevel.MEDIUM: 0.6,
            ConfidenceLevel.HIGH: 0.9
        }
        return mapping.get(confidence, 0.6)
    
    def _calculate_time_efficiency(self, time_spent: int) -> float:
        """시간 효율성 계산"""
        optimal_time = 180  # 3분을 최적 시간으로 설정
        if time_spent <= optimal_time:
            return 1.0
        else:
            return max(0.0, 1.0 - (time_spent - optimal_time) / 600)  # 10분까지 선형 감소
    
    async def _calculate_decision_quality(self, strategy: ChoiceStrategyAnalysis, is_correct: bool) -> float:
        """의사결정 품질 계산"""
        accuracy_score = 1.0 if is_correct else 0.0
        strategy_score = strategy.elimination_effectiveness
        confidence_score = 1.0 - strategy.cognitive_load_score
        
        return (accuracy_score * 0.5 + strategy_score * 0.3 + confidence_score * 0.2)
    
    async def _generate_feedback(self, is_correct: bool, learning_level: float, strategy: ChoiceStrategyAnalysis, cognitive_abilities: Dict[str, float]) -> str:
        """개별화된 피드백 생성"""
        if is_correct:
            if learning_level >= 0.9:
                return f"완벽합니다! 체계적인 {strategy.strategy_type} 전략으로 효율적으로 정답을 찾으셨네요. 특히 {strategy.elimination_count}개의 선택지를 제거하는 전략적 사고가 인상적입니다."
            elif learning_level >= 0.7:
                return f"좋은 결과입니다! {strategy.strategy_type} 접근법이 효과적이었습니다. 조금 더 체계적인 제거 전략을 사용하면 더욱 효율적일 것 같습니다."
            else:
                return f"정답을 맞히셨지만, 더 효율적인 문제 해결 전략을 개발할 수 있을 것 같습니다. 선택지 제거 기법을 활용해보세요."
        else:
            if strategy.elimination_effectiveness > 0.5:
                return f"정답은 틀렸지만 {strategy.elimination_count}개 선택지를 제거하는 등 좋은 전략적 사고를 보여주셨습니다. 패턴 인식 능력을 더 기르면 도움이 될 것 같습니다."
            else:
                return f"이번에는 아쉬웠지만 좋은 학습 기회입니다. 체계적인 선택지 제거 전략과 논리적 추론 방법을 연습해보시길 권합니다."
    
    async def _generate_skill_recommendations(self, learning_level: float, strategy: ChoiceStrategyAnalysis, cognitive_abilities: Dict[str, float]) -> List[str]:
        """스킬 추천 생성"""
        recommendations = []
        
        if cognitive_abilities.get("pattern_recognition", 0) < 0.6:
            recommendations.append("패턴 인식 훈련")
        
        if strategy.elimination_effectiveness < 0.5:
            recommendations.append("선택지 제거 전략 학습")
        
        if cognitive_abilities.get("logical_reasoning", 0) < 0.6:
            recommendations.append("논리적 추론 연습")
        
        if strategy.cognitive_load_score > 0.7:
            recommendations.append("의사결정 효율성 개선")
        
        if cognitive_abilities.get("time_management", 0) < 0.6:
            recommendations.append("시간 관리 기술")
        
        if not recommendations:
            recommendations.append("고급 문제 해결 기법")
        
        return recommendations
    
    async def _identify_improvement_areas(self, is_correct: bool, strategy: ChoiceStrategyAnalysis, cognitive_abilities: Dict[str, float]) -> List[str]:
        """개선 영역 식별"""
        areas = []
        
        if not is_correct:
            areas.append("정확성")
        
        if strategy.elimination_effectiveness < 0.7:
            areas.append("전략적 사고")
        
        if strategy.cognitive_load_score > 0.6:
            areas.append("인지 효율성")
        
        if cognitive_abilities.get("decision_making", 0) < 0.7:
            areas.append("의사결정 능력")
        
        return areas or ["지속적 발전"]
    
    async def _save_learning_history(self, db: Session, user_id: int, diagnosis_result: DiagnosisResult, subject: DiagnosisSubject):
        """학습 수준 이력 저장"""
        # 이전 수준 조회
        previous_history = db.query(LearningLevelHistory).filter(
            and_(
                LearningLevelHistory.user_id == user_id,
                LearningLevelHistory.subject == subject
            )
        ).order_by(LearningLevelHistory.measured_at.desc()).first()
        
        previous_level = previous_history.learning_level if previous_history else None
        level_change = diagnosis_result.learning_level - previous_level if previous_level else None
        change_percentage = (level_change / previous_level * 100) if previous_level and previous_level > 0 else None
        
        history = LearningLevelHistory(
            user_id=user_id,
            diagnosis_result_id=diagnosis_result.id,
            learning_level=diagnosis_result.learning_level,
            subject=subject,
            previous_level=previous_level,
            level_change=level_change,
            change_percentage=change_percentage,
            measurement_context={
                "test_type": "multi_choice_selection",
                "choice_strategy": diagnosis_result.choice_strategy_analysis,
                "elimination_effectiveness": diagnosis_result.elimination_effectiveness
            }
        )
        
        db.add(history) 