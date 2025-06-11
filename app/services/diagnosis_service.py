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
from app.models.diagnostic_test import DiagnosticTest, DiagnosticQuestion
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
    
    async def get_detailed_analysis(
        self,
        db: Session,
        user_id: int,
        test_session_id: int
    ) -> Dict[str, Any]:
        """상세한 학습 분석 데이터 제공"""
        try:
            # 기본 진단 결과 조회
            result = db.query(DiagnosisResult).filter(
                and_(
                    DiagnosisResult.test_session_id == test_session_id,
                    DiagnosisResult.user_id == user_id
                )
            ).first()
            
            if not result:
                raise ValueError("진단 결과를 찾을 수 없습니다.")
            
            # 테스트 응답 상세 데이터 조회
            test_responses = db.query(TestResponse).filter(
                TestResponse.test_session_id == test_session_id
            ).order_by(TestResponse.answered_at).all()
            
            # 클릭 패턴 분석
            click_pattern_analysis = await self._analyze_click_patterns(test_responses)
            
            # 문항별 상세 로그 분석
            question_analysis = await self._analyze_question_logs(db, test_responses)
            
            # 개념별 이해도 추정
            concept_understanding = await self._estimate_concept_understanding(db, test_responses)
            
            # 시간 패턴 분석
            time_pattern_analysis = await self._analyze_time_patterns(test_responses)
            
            # 난이도별 성과 분석
            difficulty_performance = await self._analyze_difficulty_performance(test_responses)
            
            # 학습 위치 인식을 위한 상대적 분석
            relative_position = await self._calculate_relative_position(db, result, user_id)
            
            return {
                "basic_result": {
                    "learning_level": result.learning_level,
                    "total_score": result.total_score,
                    "max_possible_score": result.max_possible_score,
                    "accuracy_rate": result.accuracy_rate,
                    "total_questions": result.total_questions,
                    "correct_answers": result.correct_answers,
                    "total_time_spent": result.total_time_spent
                },
                "click_pattern_analysis": click_pattern_analysis,
                "question_analysis": question_analysis,
                "concept_understanding": concept_understanding,
                "time_pattern_analysis": time_pattern_analysis,
                "difficulty_performance": difficulty_performance,
                "relative_position": relative_position,
                "visual_data": {
                    "learning_radar": await self._generate_learning_radar_data(concept_understanding),
                    "performance_trend": await self._generate_performance_trend_data(test_responses),
                    "knowledge_map": await self._generate_knowledge_map_data(concept_understanding)
                }
            }
            
        except Exception as e:
            logger.error(f"상세 분석 조회 실패: {str(e)}")
            raise

    # Private 메서드들
    async def _select_diagnosis_questions(self, db: Session, subject: str) -> List[Question]:
        """진단용 문제 선별"""
        
        # 물리치료학과의 경우 우리가 만든 진단테스트 데이터 사용
        if subject == "physical_therapy":
            return await self._get_physical_therapy_questions(db)
        
        # 기존 로직: 다른 과목들
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
    
    async def _get_physical_therapy_questions(self, db: Session) -> List[Question]:
        """물리치료학과 진단테스트 문제 가져오기"""
        try:
            # 물리치료학과 진단테스트 조회
            diagnostic_test = db.query(DiagnosticTest).filter(
                and_(
                    DiagnosticTest.department == "물리치료학과",
                    DiagnosticTest.is_active == True
                )
            ).first()
            
            if not diagnostic_test:
                raise ValueError("물리치료학과 진단테스트가 존재하지 않습니다.")
            
            # 진단테스트 문제들 조회
            diagnostic_questions = db.query(DiagnosticQuestion).filter(
                DiagnosticQuestion.test_id == diagnostic_test.id
            ).order_by(DiagnosticQuestion.question_number).all()
            
            # DiagnosticQuestion을 Question 형식으로 변환
            converted_questions = []
            for dq in diagnostic_questions:
                # 난이도 매핑
                difficulty_mapping = {
                    "쉬움": 1,
                    "보통": 2, 
                    "어려움": 4
                }
                difficulty = difficulty_mapping.get(dq.difficulty_level, 2)
                
                # 선택지를 리스트로 변환
                choices = []
                if dq.options:
                    choices = [f"{key}. {value}" for key, value in dq.options.items()]
                
                # Question 객체 생성 (가상의 Question 객체)
                question = type('Question', (), {
                    'id': dq.id,
                    'content': dq.content,
                    'question_type': 'multiple_choice',
                    'difficulty': difficulty,
                    'subject_name': dq.domain or '물리치료학과',
                    'correct_answer': dq.correct_answer,
                    'choices': choices,
                    'is_active': True,
                    'area_name': dq.area_name,
                    'year': dq.year
                })()
                
                converted_questions.append(question)
            
            logger.info(f"물리치료학과 진단테스트 문제 {len(converted_questions)}개 로드 완료")
            return converted_questions
            
        except Exception as e:
            logger.error(f"물리치료학과 문제 로드 실패: {str(e)}")
            raise
    
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
            subject_breakdown=subject_breakdown,
            calculation_formula=f"학습수준 = {total_score:.1f}/{max_possible_score:.1f} = {learning_level:.3f}"
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
            # 새 세션의 경우 TestResponse가 없으므로 전체 물리치료 문제에서 선별
            logger.warning(f"세션 {test_session.id}에 대한 questions가 없음. 문제 재선별 중...")
            questions = await self._select_diagnosis_questions(db, test_session.subject.value)
            questions = questions[:30]  # 30문제로 제한
        
        from app.schemas.diagnosis import QuestionItem
        
        question_responses = []
        for question in questions:
            question_responses.append(QuestionItem(
                id=question.id,
                content=question.content,
                question_type=question.question_type,
                difficulty=str(question.difficulty),
                choices=question.choices
            ))
        
        logger.info(f"테스트 응답 구성 완료: {len(question_responses)}개 문제")
        
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

    async def _analyze_click_patterns(self, test_responses: List[TestResponse]) -> Dict[str, Any]:
        """클릭 패턴 분석"""
        if not test_responses:
            return {}
        
        # 응답 시간 패턴 분석
        response_times = [r.time_spent_seconds or 0 for r in test_responses]
        avg_response_time = sum(response_times) / len(response_times)
        
        # 빠른 응답 vs 신중한 응답 패턴
        quick_responses = [t for t in response_times if t < avg_response_time * 0.5]
        thoughtful_responses = [t for t in response_times if t > avg_response_time * 1.5]
        
        # 정답률과 응답 시간의 상관관계
        quick_accuracy = 0
        thoughtful_accuracy = 0
        
        for i, response in enumerate(test_responses):
            response_time = response.time_spent_seconds or 0
            if response_time < avg_response_time * 0.5:
                if response.is_correct:
                    quick_accuracy += 1
            elif response_time > avg_response_time * 1.5:
                if response.is_correct:
                    thoughtful_accuracy += 1
        
        quick_accuracy_rate = quick_accuracy / len(quick_responses) if quick_responses else 0
        thoughtful_accuracy_rate = thoughtful_accuracy / len(thoughtful_responses) if thoughtful_responses else 0
        
        return {
            "avg_response_time": round(avg_response_time, 2),
            "quick_response_count": len(quick_responses),
            "thoughtful_response_count": len(thoughtful_responses),
            "quick_accuracy_rate": round(quick_accuracy_rate, 3),
            "thoughtful_accuracy_rate": round(thoughtful_accuracy_rate, 3),
            "response_pattern": "impulsive" if len(quick_responses) > len(thoughtful_responses) else "careful",
            "time_consistency": self._calculate_time_consistency(response_times)
        }

    async def _analyze_question_logs(self, db: Session, test_responses: List[TestResponse]) -> List[Dict[str, Any]]:
        """문항별 상세 로그 분석"""
        question_logs = []
        
        for response in test_responses:
            question = db.query(Question).filter(Question.id == response.question_id).first()
            if not question:
                continue
            
            # 문항별 상세 정보
            question_data = {
                "question_id": response.question_id,
                "question_content": question.content[:100] + "..." if len(question.content) > 100 else question.content,
                "subject_area": getattr(question, 'area_name', question.subject_name),
                "difficulty": question.difficulty,
                "user_answer": response.user_answer,
                "correct_answer": question.correct_answer,
                "is_correct": response.is_correct,
                "score": response.score,
                "time_spent": response.time_spent_seconds,
                "answered_at": response.answered_at.isoformat() if response.answered_at else None,
                "difficulty_score": self._get_difficulty_score(question.difficulty),
                "concept_tags": await self._extract_concept_tags(question)
            }
            
            question_logs.append(question_data)
        
        return sorted(question_logs, key=lambda x: x.get('answered_at', ''))

    async def _estimate_concept_understanding(self, db: Session, test_responses: List[TestResponse]) -> Dict[str, Dict[str, Any]]:
        """개념별 이해도 추정"""
        concept_scores = {}
        
        for response in test_responses:
            question = db.query(Question).filter(Question.id == response.question_id).first()
            if not question:
                continue
            
            # 개념 태그 추출
            concepts = await self._extract_concept_tags(question)
            
            for concept in concepts:
                if concept not in concept_scores:
                    concept_scores[concept] = {
                        "total_questions": 0,
                        "correct_answers": 0,
                        "total_score": 0.0,
                        "max_score": 0.0,
                        "avg_time": 0.0,
                        "questions": []
                    }
                
                difficulty_score = self._get_difficulty_score(question.difficulty)
                concept_scores[concept]["total_questions"] += 1
                concept_scores[concept]["correct_answers"] += 1 if response.is_correct else 0
                concept_scores[concept]["total_score"] += response.score * difficulty_score
                concept_scores[concept]["max_score"] += difficulty_score
                concept_scores[concept]["avg_time"] += response.time_spent_seconds or 0
                concept_scores[concept]["questions"].append({
                    "question_id": response.question_id,
                    "is_correct": response.is_correct,
                    "difficulty": question.difficulty
                })
        
        # 개념별 이해도 계산
        for concept in concept_scores:
            data = concept_scores[concept]
            data["understanding_rate"] = data["total_score"] / data["max_score"] if data["max_score"] > 0 else 0
            data["accuracy_rate"] = data["correct_answers"] / data["total_questions"] if data["total_questions"] > 0 else 0
            data["avg_time"] = data["avg_time"] / data["total_questions"] if data["total_questions"] > 0 else 0
            data["mastery_level"] = self._determine_mastery_level(data["understanding_rate"], data["accuracy_rate"])
        
        return concept_scores

    async def _analyze_time_patterns(self, test_responses: List[TestResponse]) -> Dict[str, Any]:
        """시간 패턴 분석"""
        if not test_responses:
            return {}
        
        response_times = [r.time_spent_seconds or 0 for r in test_responses]
        
        return {
            "total_time": sum(response_times),
            "avg_time_per_question": sum(response_times) / len(response_times),
            "min_time": min(response_times),
            "max_time": max(response_times),
            "time_variance": self._calculate_variance(response_times),
            "time_trend": self._analyze_time_trend(response_times),
            "fatigue_indicator": self._detect_fatigue_pattern(response_times)
        }

    async def _analyze_difficulty_performance(self, test_responses: List[TestResponse]) -> Dict[str, Dict[str, Any]]:
        """난이도별 성과 분석"""
        difficulty_performance = {}
        
        # 난이도별 그룹화
        for response in test_responses:
            question = db.query(Question).filter(Question.id == response.question_id).first()
            difficulty = question.difficulty if question else 'unknown'
            
            if difficulty not in difficulty_performance:
                difficulty_performance[difficulty] = {
                    "total": 0,
                    "correct": 0,
                    "total_time": 0,
                    "total_score": 0.0
                }
            
            perf = difficulty_performance[difficulty]
            perf["total"] += 1
            perf["correct"] += 1 if response.is_correct else 0
            perf["total_time"] += response.time_spent_seconds or 0
            perf["total_score"] += response.score or 0
        
        # 성과 지표 계산
        for difficulty in difficulty_performance:
            perf = difficulty_performance[difficulty]
            perf["accuracy_rate"] = perf["correct"] / perf["total"] if perf["total"] > 0 else 0
            perf["avg_time"] = perf["total_time"] / perf["total"] if perf["total"] > 0 else 0
            perf["avg_score"] = perf["total_score"] / perf["total"] if perf["total"] > 0 else 0
        
        return difficulty_performance

    async def _calculate_relative_position(self, db: Session, result: DiagnosisResult, user_id: int) -> Dict[str, Any]:
        """학습자의 상대적 위치 계산"""
        # 전체 사용자 대비 백분위 계산
        total_users = db.query(DiagnosisResult).filter(
            DiagnosisResult.user_id != user_id
        ).count()
        
        better_users = db.query(DiagnosisResult).filter(
            and_(
                DiagnosisResult.user_id != user_id,
                DiagnosisResult.learning_level > result.learning_level
            )
        ).count()
        
        percentile = ((total_users - better_users) / total_users * 100) if total_users > 0 else 50
        
        # 학습 수준 등급 결정
        level_grade = self._determine_level_grade(result.learning_level)
        
        return {
            "percentile": round(percentile, 1),
            "level_grade": level_grade,
            "total_participants": total_users + 1,
            "rank": better_users + 1,
            "improvement_potential": self._calculate_improvement_potential(result.learning_level),
            "peer_comparison": await self._get_peer_comparison_data(db, result, user_id)
        }

    async def _generate_learning_radar_data(self, concept_understanding: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """학습 레이더 차트 데이터 생성"""
        categories = []
        scores = []
        max_scores = []
        
        for concept, data in concept_understanding.items():
            categories.append(concept)
            scores.append(data["understanding_rate"] * 100)
            max_scores.append(100)
        
        return {
            "categories": categories,
            "datasets": [
                {
                    "label": "현재 이해도",
                    "data": scores,
                    "backgroundColor": "rgba(54, 162, 235, 0.2)",
                    "borderColor": "rgba(54, 162, 235, 1)",
                    "borderWidth": 2
                }
            ]
        }

    async def _generate_performance_trend_data(self, test_responses: List[TestResponse]) -> Dict[str, Any]:
        """성과 트렌드 데이터 생성"""
        labels = []
        accuracy_data = []
        time_data = []
        
        # 10문제씩 그룹으로 나누어 트렌드 분석
        group_size = 10
        for i in range(0, len(test_responses), group_size):
            group = test_responses[i:i+group_size]
            group_num = i // group_size + 1
            
            accuracy = sum(1 for r in group if r.is_correct) / len(group) * 100
            avg_time = sum(r.time_spent_seconds or 0 for r in group) / len(group)
            
            labels.append(f"문제 {i+1}-{min(i+group_size, len(test_responses))}")
            accuracy_data.append(round(accuracy, 1))
            time_data.append(round(avg_time, 1))
        
        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "정답률 (%)",
                    "data": accuracy_data,
                    "backgroundColor": "rgba(75, 192, 192, 0.2)",
                    "borderColor": "rgba(75, 192, 192, 1)",
                    "yAxisID": "y"
                },
                {
                    "label": "평균 소요시간 (초)",
                    "data": time_data,
                    "backgroundColor": "rgba(255, 99, 132, 0.2)",
                    "borderColor": "rgba(255, 99, 132, 1)",
                    "yAxisID": "y1"
                }
            ]
        }

    async def _generate_knowledge_map_data(self, concept_understanding: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """지식 맵 데이터 생성"""
        nodes = []
        edges = []
        
        for concept, data in concept_understanding.items():
            mastery_level = data["mastery_level"]
            color = {
                "expert": "#4CAF50",
                "proficient": "#2196F3", 
                "developing": "#FF9800",
                "beginner": "#F44336"
            }.get(mastery_level, "#9E9E9E")
            
            nodes.append({
                "id": concept,
                "label": concept,
                "value": data["understanding_rate"] * 100,
                "color": color,
                "mastery": mastery_level,
                "questions": data["total_questions"],
                "accuracy": data["accuracy_rate"]
            })
        
        return {
            "nodes": nodes,
            "edges": edges
        }

    # Helper methods
    def _calculate_time_consistency(self, times: List[float]) -> float:
        """시간 일관성 계산"""
        if len(times) < 2:
            return 1.0
        
        avg = sum(times) / len(times)
        variance = sum((t - avg) ** 2 for t in times) / len(times)
        coefficient_of_variation = (variance ** 0.5) / avg if avg > 0 else 0
        
        return max(0, 1 - coefficient_of_variation)

    async def _extract_concept_tags(self, question) -> List[str]:
        """문제에서 개념 태그 추출"""
        # 기본적으로 subject_name 사용
        tags = [question.subject_name]
        
        # area_name이 있으면 추가
        if hasattr(question, 'area_name') and question.area_name:
            tags.append(question.area_name)
        
        # 물리치료 특화 개념 추출
        content = question.content.lower()
        concepts = {
            "해부학": ["근육", "뼈", "관절", "신경", "혈관", "해부"],
            "생리학": ["기능", "대사", "호흡", "순환", "생리"],
            "운동학": ["운동", "동작", "보행", "자세", "kinematic"],
            "병리학": ["질환", "병변", "증상", "진단", "병리"],
            "치료학": ["치료", "재활", "운동치료", "물리치료", "intervention"]
        }
        
        for concept, keywords in concepts.items():
            if any(keyword in content for keyword in keywords):
                tags.append(concept)
        
        return list(set(tags))

    def _determine_mastery_level(self, understanding_rate: float, accuracy_rate: float) -> str:
        """숙련도 수준 결정"""
        combined_score = (understanding_rate + accuracy_rate) / 2
        
        if combined_score >= 0.9:
            return "expert"
        elif combined_score >= 0.7:
            return "proficient"
        elif combined_score >= 0.5:
            return "developing"
        else:
            return "beginner"

    def _calculate_variance(self, values: List[float]) -> float:
        """분산 계산"""
        if len(values) < 2:
            return 0
        
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)

    def _analyze_time_trend(self, times: List[float]) -> str:
        """시간 트렌드 분석"""
        if len(times) < 3:
            return "insufficient_data"
        
        # 전반부와 후반부 비교
        first_half = times[:len(times)//2]
        second_half = times[len(times)//2:]
        
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        
        if avg_second > avg_first * 1.2:
            return "slowing_down"
        elif avg_second < avg_first * 0.8:
            return "speeding_up"
        else:
            return "consistent"

    def _detect_fatigue_pattern(self, times: List[float]) -> Dict[str, Any]:
        """피로도 패턴 감지"""
        if len(times) < 5:
            return {"detected": False, "confidence": 0}
        
        # 마지막 5문제의 평균 시간과 처음 5문제 비교
        initial_avg = sum(times[:5]) / 5
        final_avg = sum(times[-5:]) / 5
        
        fatigue_ratio = final_avg / initial_avg if initial_avg > 0 else 1
        
        return {
            "detected": fatigue_ratio > 1.3,
            "confidence": min(fatigue_ratio - 1, 1) if fatigue_ratio > 1 else 0,
            "initial_avg_time": round(initial_avg, 2),
            "final_avg_time": round(final_avg, 2)
        }

    def _determine_level_grade(self, learning_level: float) -> str:
        """학습 수준 등급 결정"""
        if learning_level >= 0.9:
            return "A+"
        elif learning_level >= 0.8:
            return "A"
        elif learning_level >= 0.7:
            return "B+"
        elif learning_level >= 0.6:
            return "B"
        elif learning_level >= 0.5:
            return "C+"
        elif learning_level >= 0.4:
            return "C"
        else:
            return "D"

    def _calculate_improvement_potential(self, current_level: float) -> Dict[str, Any]:
        """개선 잠재력 계산"""
        max_possible = 1.0
        current_gap = max_possible - current_level
        
        return {
            "current_level": round(current_level, 3),
            "max_possible": max_possible,
            "improvement_gap": round(current_gap, 3),
            "potential_percentage": round(current_gap * 100, 1),
            "next_target": round(min(current_level + 0.1, max_possible), 3)
        }

    async def _get_peer_comparison_data(self, db: Session, result: DiagnosisResult, user_id: int) -> Dict[str, Any]:
        """동료 비교 데이터"""
        # 비슷한 수준의 학습자들 데이터 (±10% 범위)
        similar_level_results = db.query(DiagnosisResult).filter(
            and_(
                DiagnosisResult.user_id != user_id,
                DiagnosisResult.learning_level.between(
                    result.learning_level - 0.1,
                    result.learning_level + 0.1
                )
            )
        ).limit(50).all()
        
        if not similar_level_results:
            return {"similar_peers": 0}
        
        avg_accuracy = sum(r.accuracy_rate for r in similar_level_results) / len(similar_level_results)
        avg_time = sum(r.total_time_spent for r in similar_level_results) / len(similar_level_results)
        
        return {
            "similar_peers": len(similar_level_results),
            "peer_avg_accuracy": round(avg_accuracy, 3),
            "peer_avg_time": round(avg_time, 1),
            "your_accuracy": round(result.accuracy_rate, 3),
            "your_time": result.total_time_spent,
            "accuracy_compared_to_peers": "above" if result.accuracy_rate > avg_accuracy else "below",
            "time_compared_to_peers": "faster" if result.total_time_spent < avg_time else "slower"
        }

# 싱글톤 인스턴스
diagnosis_service = DiagnosisService() 