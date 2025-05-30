"""
진단 테스트 관련 서비스 로직
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import logging

from app.models.diagnosis import (
    TestSession, TestResponse, DiagnosisResult, LearningLevelHistory,
    DiagnosisStatus, DiagnosisSubject
)
from app.models.question import Question, DifficultyLevel
from app.schemas.diagnosis import (
    DiagnosisTestCreate, DiagnosisTestResponse, DiagnosisResultCreate,
    DiagnosisResultResponse, LearningLevelResponse, DiagnosisAnswerItem
)
from app.services.learning_calculator import LearningCalculator

logger = logging.getLogger(__name__)

class DiagnosisService:
    """진단 테스트 서비스"""
    
    def __init__(self):
        self.learning_calculator = LearningCalculator()
    
    async def create_test_session(
        self, 
        db: Session, 
        user_id: int, 
        subject: str
    ) -> DiagnosisTestResponse:
        """
        진단 테스트 세션 생성
        - 30문항의 고정 문제 선별
        - 난이도별 균등 분배
        """
        try:
            # 기존 활성 세션 확인
            existing_session = db.query(TestSession).filter(
                and_(
                    TestSession.user_id == user_id,
                    TestSession.status == DiagnosisStatus.ACTIVE,
                    TestSession.subject == DiagnosisSubject(subject)
                )
            ).first()
            
            if existing_session:
                # 기존 세션이 만료되지 않았다면 해당 세션 반환
                if existing_session.expires_at and existing_session.expires_at > datetime.now(timezone.utc):
                    return await self._build_test_response(db, existing_session)
                else:
                    # 만료된 세션은 EXPIRED로 변경
                    existing_session.status = DiagnosisStatus.EXPIRED
                    db.commit()
            
            # subject가 DiagnosisSubject enum으로 전달되는 경우 처리
            if hasattr(subject, 'value'):
                subject_str = subject.value
            else:
                subject_str = str(subject)
                
            # 진단용 문제 선별 (난이도별 균등 분배)
            diagnosis_questions = await self._select_diagnosis_questions(db, subject_str)
            
            if len(diagnosis_questions) < 30:
                raise ValueError(f"충분한 진단 문제가 없습니다. 현재 {len(diagnosis_questions)}개")
            
            # 새 테스트 세션 생성
            test_session = TestSession(
                user_id=user_id,
                subject=DiagnosisSubject(subject),
                status=DiagnosisStatus.ACTIVE,
                max_time_minutes=60,
                total_questions=30,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=2),  # 2시간 후 만료
                description=f"{subject} 진단 테스트"
            )
            
            db.add(test_session)
            db.commit()
            db.refresh(test_session)
            
            logger.info(f"진단 테스트 세션 생성: user_id={user_id}, session_id={test_session.id}")
            
            return await self._build_test_response(db, test_session, diagnosis_questions[:30])
            
        except Exception as e:
            logger.error(f"진단 테스트 세션 생성 실패: {str(e)}")
            db.rollback()
            raise
    
    async def submit_test_answers(
        self,
        db: Session,
        user_id: int,
        test_session_id: int,
        answers: List[DiagnosisAnswerItem]
    ) -> DiagnosisResultResponse:
        """
        진단 테스트 답안 제출 및 결과 계산
        """
        try:
            # 테스트 세션 검증
            test_session = db.query(TestSession).filter(
                and_(
                    TestSession.id == test_session_id,
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
            
            # 기존 응답 삭제 (재제출 경우)
            db.query(TestResponse).filter(
                TestResponse.test_session_id == test_session_id
            ).delete()
            
            # 답안 저장 및 채점
            test_responses = []
            total_score = 0.0
            max_possible_score = 0.0
            correct_count = 0
            
            for answer_item in answers:
                question = db.query(Question).filter(Question.id == answer_item.question_id).first()
                if not question:
                    continue
                
                # 답안 채점
                is_correct, score = await self._grade_answer(question, answer_item.answer)
                difficulty_score = self._get_difficulty_score(question.difficulty)
                
                # 응답 저장
                test_response = TestResponse(
                    test_session_id=test_session_id,
                    question_id=answer_item.question_id,
                    user_answer=answer_item.answer,
                    is_correct=is_correct,
                    score=score,
                    time_spent_seconds=answer_item.time_spent,
                    answered_at=datetime.now(timezone.utc)
                )
                
                db.add(test_response)
                test_responses.append(test_response)
                
                # 점수 계산 (산술식 적용)
                if is_correct:
                    total_score += difficulty_score
                    correct_count += 1
                max_possible_score += difficulty_score
            
            # 학습 수준 지표 계산
            learning_level = total_score / max_possible_score if max_possible_score > 0 else 0.0
            accuracy_rate = correct_count / len(answers) if len(answers) > 0 else 0.0
            
            # 세부 분석 계산
            calculation_details = await self._calculate_detailed_analysis(
                db, test_responses, total_score, max_possible_score, learning_level
            )
            
            # 피드백 생성
            feedback_message = await self._generate_feedback(learning_level, calculation_details)
            recommended_steps = await self._generate_recommendations(learning_level, calculation_details)
            
            # 진단 결과 저장
            diagnosis_result = DiagnosisResult(
                test_session_id=test_session_id,
                user_id=user_id,
                learning_level=learning_level,
                total_score=total_score,
                max_possible_score=max_possible_score,
                accuracy_rate=accuracy_rate,
                total_questions=len(answers),
                correct_answers=correct_count,
                total_time_spent=sum(ans.time_spent or 0 for ans in answers),
                difficulty_breakdown=calculation_details.difficulty_breakdown,
                subject_breakdown=calculation_details.subject_breakdown,
                feedback_message=feedback_message,
                recommended_next_steps=recommended_steps,
                calculated_at=datetime.now(timezone.utc)
            )
            
            db.add(diagnosis_result)
            
            # 테스트 세션 완료 처리
            test_session.status = DiagnosisStatus.COMPLETED
            test_session.completed_at = datetime.now(timezone.utc)
            
            # 먼저 커밋하여 diagnosis_result.id 생성
            db.commit()
            db.refresh(diagnosis_result)
            
            # 학습 수준 이력 저장 (diagnosis_result.id가 이제 사용 가능)
            await self._save_learning_history(db, user_id, diagnosis_result, test_session.subject)
            
            # 최종 커밋
            db.commit()
            
            logger.info(f"진단 테스트 완료: user_id={user_id}, learning_level={learning_level:.3f}")
            
            return DiagnosisResultResponse(
                test_session_id=test_session_id,
                user_id=user_id,
                learning_level=learning_level,
                total_questions=len(answers),
                correct_answers=correct_count,
                accuracy_rate=accuracy_rate,
                calculation_details=calculation_details,
                feedback_message=feedback_message,
                recommended_next_steps=recommended_steps,
                completed_at=diagnosis_result.calculated_at
            )
            
        except Exception as e:
            logger.error(f"진단 테스트 제출 실패: {str(e)}")
            db.rollback()
            raise
    
    async def get_test_result(
        self,
        db: Session,
        user_id: int,
        test_session_id: int
    ) -> LearningLevelResponse:
        """진단 테스트 결과 조회"""
        try:
            result = db.query(DiagnosisResult).filter(
                and_(
                    DiagnosisResult.test_session_id == test_session_id,
                    DiagnosisResult.user_id == user_id
                )
            ).first()
            
            if not result:
                raise ValueError("진단 결과를 찾을 수 없습니다.")
            
            # 이전 진단 결과 조회
            previous_result = db.query(DiagnosisResult).filter(
                and_(
                    DiagnosisResult.user_id == user_id,
                    DiagnosisResult.id < result.id
                )
            ).order_by(desc(DiagnosisResult.calculated_at)).first()
            
            # 강점/약점 분석
            strengths, weaknesses = await self._analyze_strengths_weaknesses(result)
            
            return LearningLevelResponse(
                current_level=result.learning_level,
                previous_level=previous_result.learning_level if previous_result else None,
                improvement=result.improvement_from_previous,
                percentile_rank=result.percentile_rank,
                strengths=strengths,
                weaknesses=weaknesses,
                recommendations=result.recommended_next_steps or [],
                last_updated=result.calculated_at
            )
            
        except Exception as e:
            logger.error(f"진단 결과 조회 실패: {str(e)}")
            raise
    
    async def get_user_diagnosis_history(
        self,
        db: Session,
        user_id: int,
        limit: int = 10,
        offset: int = 0
    ) -> List[DiagnosisTestResponse]:
        """사용자 진단 이력 조회"""
        try:
            sessions = db.query(TestSession).filter(
                TestSession.user_id == user_id
            ).order_by(desc(TestSession.created_at)).offset(offset).limit(limit).all()
            
            result = []
            for session in sessions:
                questions = db.query(Question).join(TestResponse).filter(
                    TestResponse.test_session_id == session.id
                ).all()
                
                result.append(await self._build_test_response(db, session, questions))
            
            return result
            
        except Exception as e:
            logger.error(f"진단 이력 조회 실패: {str(e)}")
            raise
    
    # Private 메서드들
    async def _select_diagnosis_questions(self, db: Session, subject: str) -> List[Question]:
        """진단용 문제 선별"""
        # 난이도별로 균등하게 문제 선별 (각 난이도별 6문제씩)
        questions = []
        difficulties = [DifficultyLevel.EASY, DifficultyLevel.MEDIUM, DifficultyLevel.HARD, DifficultyLevel.VERY_HARD]
        
        # 각 난이도별로 문제 선별
        for i, difficulty in enumerate(difficulties):
            difficulty_questions = db.query(Question).filter(
                and_(
                    Question.difficulty == difficulty,
                    Question.subject_name.ilike(f"%{subject}%"),
                    Question.is_active == True
                )
            ).order_by(func.random()).limit(6).all()
            
            questions.extend(difficulty_questions)
        
        # 만약 문제가 부족하면 추가로 더 가져오기
        if len(questions) < 30:
            additional_questions = db.query(Question).filter(
                and_(
                    Question.subject_name.ilike(f"%{subject}%"),
                    Question.is_active == True,
                    ~Question.id.in_([q.id for q in questions])
                )
            ).order_by(func.random()).limit(30 - len(questions)).all()
            
            questions.extend(additional_questions)
        
        return questions
    
    async def _grade_answer(self, question: Question, user_answer: str) -> tuple[bool, float]:
        """답안 채점"""
        if not question.correct_answer:
            return False, 0.0
        
        # 정답 비교 (대소문자 무시, 공백 제거)
        correct_answer = question.correct_answer.strip().lower()
        user_answer_clean = user_answer.strip().lower()
        
        if question.question_type == "multiple_choice":
            # 객관식: 정확히 일치해야 함
            is_correct = correct_answer == user_answer_clean
            return is_correct, 1.0 if is_correct else 0.0
        
        elif question.question_type == "true_false":
            # 참/거짓: 정확히 일치해야 함
            is_correct = correct_answer in user_answer_clean or user_answer_clean in correct_answer
            return is_correct, 1.0 if is_correct else 0.0
        
        else:
            # 주관식: 부분 점수 가능
            similarity = self._calculate_text_similarity(correct_answer, user_answer_clean)
            is_correct = similarity >= 0.8
            return is_correct, similarity
    
    def _get_difficulty_score(self, difficulty: int) -> float:
        """난이도별 점수 반환"""
        difficulty_scores = {1: 1.0, 2: 2.0, 3: 3.0, 4: 4.0, 5: 5.0}
        return difficulty_scores.get(difficulty, 1.0)
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """텍스트 유사도 계산 (간단한 구현)"""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if len(words1) == 0 and len(words2) == 0:
            return 1.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    async def _calculate_detailed_analysis(
        self, 
        db: Session, 
        test_responses: List[TestResponse],
        total_score: float,
        max_possible_score: float,
        learning_level: float
    ):
        """세부 분석 계산"""
        from app.schemas.diagnosis import LearningLevelCalculation
        
        # 난이도별 분석
        difficulty_breakdown = {}
        subject_breakdown = {}
        
        for response in test_responses:
            question = db.query(Question).filter(Question.id == response.question_id).first()
            if not question:
                continue
            
            difficulty_key = str(question.difficulty)
            subject_key = question.subject_name
            
            # 난이도별 집계
            if difficulty_key not in difficulty_breakdown:
                difficulty_breakdown[difficulty_key] = {
                    "total": 0, "correct": 0, "score": 0.0, "max_score": 0.0
                }
            
            difficulty_breakdown[difficulty_key]["total"] += 1
            difficulty_breakdown[difficulty_key]["max_score"] += self._get_difficulty_score(question.difficulty)
            
            if response.is_correct:
                difficulty_breakdown[difficulty_key]["correct"] += 1
                difficulty_breakdown[difficulty_key]["score"] += self._get_difficulty_score(question.difficulty)
            
            # 과목별 집계
            if subject_key not in subject_breakdown:
                subject_breakdown[subject_key] = {
                    "total": 0, "correct": 0, "score": 0.0, "max_score": 0.0
                }
            
            subject_breakdown[subject_key]["total"] += 1
            subject_breakdown[subject_key]["max_score"] += self._get_difficulty_score(question.difficulty)
            
            if response.is_correct:
                subject_breakdown[subject_key]["correct"] += 1
                subject_breakdown[subject_key]["score"] += self._get_difficulty_score(question.difficulty)
        
        return LearningLevelCalculation(
            total_score=total_score,
            max_possible_score=max_possible_score,
            learning_level=learning_level,
            difficulty_breakdown=difficulty_breakdown,
            subject_breakdown=subject_breakdown
        )
    
    async def _generate_feedback(self, learning_level: float, calculation_details) -> str:
        """피드백 메시지 생성"""
        if learning_level >= 0.8:
            return "뛰어난 실력입니다! 고급 문제에 도전해보세요."
        elif learning_level >= 0.6:
            return "양호한 수준입니다. 약점 영역을 집중적으로 학습하세요."
        elif learning_level >= 0.4:
            return "기초가 어느 정도 갖추어져 있습니다. 꾸준한 학습이 필요합니다."
        else:
            return "기초부터 차근차근 학습하시기 바랍니다."
    
    async def _generate_recommendations(self, learning_level: float, calculation_details) -> List[str]:
        """추천사항 생성"""
        recommendations = []
        
        if learning_level < 0.5:
            recommendations.append("기초 문제부터 시작하여 기본기를 탄탄히 하세요.")
        
        if learning_level >= 0.7:
            recommendations.append("고급 문제에 도전하여 실력을 더욱 향상시키세요.")
        
        # 약점 영역 기반 추천
        for subject, data in calculation_details.subject_breakdown.items():
            if data["max_score"] > 0:
                accuracy = data["score"] / data["max_score"]
                if accuracy < 0.5:
                    recommendations.append(f"{subject} 영역의 추가 학습이 필요합니다.")
        
        return recommendations
    
    async def _save_learning_history(
        self, 
        db: Session, 
        user_id: int, 
        diagnosis_result: DiagnosisResult,
        subject: DiagnosisSubject
    ):
        """학습 수준 이력 저장"""
        # 이전 기록 조회
        previous_history = db.query(LearningLevelHistory).filter(
            and_(
                LearningLevelHistory.user_id == user_id,
                LearningLevelHistory.subject == subject
            )
        ).order_by(desc(LearningLevelHistory.measured_at)).first()
        
        # 변화량 계산
        previous_level = previous_history.learning_level if previous_history else None
        level_change = None
        change_percentage = None
        
        if previous_level is not None:
            level_change = diagnosis_result.learning_level - previous_level
            change_percentage = (level_change / previous_level) * 100 if previous_level > 0 else 0
        
        # 이력 저장
        history = LearningLevelHistory(
            user_id=user_id,
            diagnosis_result_id=diagnosis_result.id,
            learning_level=diagnosis_result.learning_level,
            subject=subject,
            previous_level=previous_level,
            level_change=level_change,
            change_percentage=change_percentage,
            measured_at=datetime.now(timezone.utc)
        )
        
        db.add(history)
    
    async def _analyze_strengths_weaknesses(self, result: DiagnosisResult) -> tuple[List[str], List[str]]:
        """강점/약점 분석"""
        strengths = []
        weaknesses = []
        
        if result.difficulty_breakdown:
            for difficulty, data in result.difficulty_breakdown.items():
                if data["max_score"] > 0:
                    accuracy = data["score"] / data["max_score"]
                    if accuracy >= 0.8:
                        strengths.append(f"난이도 {difficulty} 문제")
                    elif accuracy < 0.5:
                        weaknesses.append(f"난이도 {difficulty} 문제")
        
        if result.subject_breakdown:
            for subject, data in result.subject_breakdown.items():
                if data["max_score"] > 0:
                    accuracy = data["score"] / data["max_score"]
                    if accuracy >= 0.8:
                        strengths.append(f"{subject} 영역")
                    elif accuracy < 0.5:
                        weaknesses.append(f"{subject} 영역")
        
        return strengths, weaknesses
    
    async def _build_test_response(
        self, 
        db: Session, 
        test_session: TestSession, 
        questions: Optional[List[Question]] = None
    ) -> DiagnosisTestResponse:
        """테스트 응답 객체 구성"""
        if questions is None:
            questions = db.query(Question).join(TestResponse).filter(
                TestResponse.test_session_id == test_session.id
            ).all()
        
        from app.schemas.diagnosis import DiagnosisQuestionResponse
        
        question_responses = []
        for i, question in enumerate(questions):
            question_responses.append(DiagnosisQuestionResponse(
                id=question.id,
                content=question.content,
                choices=question.choices,
                question_type=question.question_type,
                difficulty=str(question.difficulty),
                subject=question.subject_name,
                order_number=i + 1
            ))
        
        return DiagnosisTestResponse(
            id=test_session.id,
            user_id=test_session.user_id,
            subject=test_session.subject.value,
            status=test_session.status.value,
            questions=question_responses,
            created_at=test_session.created_at,
            expires_at=test_session.expires_at,
            max_time_minutes=test_session.max_time_minutes
        )

# 싱글톤 인스턴스
diagnosis_service = DiagnosisService() 