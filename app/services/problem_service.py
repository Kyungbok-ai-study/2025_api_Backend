"""
문제 추천 및 관리 서비스
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func, text, select
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging
import random

from app.models.question import Question, Subject, Tag, DifficultyLevel
from app.models.user import User
from app.models.diagnosis import TestResponse, DiagnosisResult
from app.schemas.problems import (
    ProblemResponse, ProblemSubmissionResponse, ProblemStatisticsResponse
)
from app.services.learning_calculator import LearningCalculator

logger = logging.getLogger(__name__)

class ProblemService:
    """문제 추천 및 관리 서비스"""
    
    def __init__(self):
        self.learning_calculator = LearningCalculator()
    
    async def get_recommended_problems(
        self,
        db: Session,
        user_id: int,
        subject: Optional[str] = None,
        difficulty_level: Optional[int] = None,
        limit: int = 10
    ) -> List[ProblemResponse]:
        """
        맞춤형 문제 추천
        - 학습 이력과 진단 결과 기반
        - pgvector를 활용한 유사도 검색
        """
        try:
            # 사용자의 최근 진단 결과 조회
            latest_diagnosis = db.query(DiagnosisResult).filter(
                DiagnosisResult.user_id == user_id
            ).order_by(desc(DiagnosisResult.calculated_at)).first()
            
            # 사용자 학습 수준에 따른 난이도 계산
            if latest_diagnosis and not difficulty_level:
                difficulty_level = await self._calculate_recommended_difficulty(
                    latest_diagnosis.learning_level
                )
            elif not difficulty_level:
                difficulty_level = 2  # 기본 난이도 (쉬움)
            
            # 이미 푼 문제 ID 조회
            solved_problem_ids = select(TestResponse.question_id).where(
                TestResponse.test_session_id.in_(
                    select(TestResponse.test_session_id).where(
                        TestResponse.test_session.has(user_id=user_id)
                    )
                )
            )
            
            # 문제 쿼리 구성
            query = db.query(Question).filter(
                and_(
                    Question.is_active == True,
                    ~Question.id.in_(solved_problem_ids)
                )
            )
            
            # 과목 필터링
            if subject:
                query = query.filter(
                    Question.subject_name.ilike(f"%{subject}%")
                )
            
            # 난이도 필터링 - enum과 integer 비교 대신 문자열 비교 사용
            difficulty_mapping = {
                1: DifficultyLevel.EASY,
                2: DifficultyLevel.MEDIUM, 
                3: DifficultyLevel.HARD,
                4: DifficultyLevel.VERY_HARD,
                5: DifficultyLevel.VERY_HARD
            }
            
            if difficulty_level in difficulty_mapping:
                target_difficulty = difficulty_mapping[difficulty_level]
                query = query.filter(Question.difficulty == target_difficulty)
            
            # pgvector 유사도 검색 (사용 가능한 경우)
            if latest_diagnosis and hasattr(Question, 'embedding'):
                # 사용자 관심 벡터 계산 (실제로는 더 복잡한 로직 필요)
                query = query.order_by(func.random())
            else:
                # 랜덤 정렬
                query = query.order_by(func.random())
            
            problems = query.limit(limit * 2).all()  # 여유분 확보
            
            # 다양성을 위한 후처리
            recommended_problems = await self._diversify_recommendations(
                problems, limit
            )
            
            # 응답 객체 변환
            result = []
            for problem in recommended_problems:
                result.append(ProblemResponse(
                    id=problem.id,
                    title=f"문제 {problem.id}",
                    content=problem.content,
                    choices=problem.choices,
                    problem_type=problem.question_type.value if problem.question_type else "multiple_choice",
                    difficulty=self._difficulty_enum_to_int(problem.difficulty),
                    subject=problem.subject_name or "일반",
                    source="database",
                    estimated_time=self._estimate_solve_time(problem),
                    tags=await self._get_problem_tags(db, problem.id),
                    hints=[],
                    created_at=problem.created_at or datetime.utcnow()
                ))
            
            logger.info(f"문제 추천 완료: user_id={user_id}, count={len(result)}")
            return result
            
        except Exception as e:
            logger.error(f"문제 추천 실패: {str(e)}")
            raise
    
    async def submit_answer(
        self,
        db: Session,
        user_id: int,
        problem_id: int,
        answer: str,
        time_spent: Optional[int] = None
    ) -> ProblemSubmissionResponse:
        """
        문제 답안 제출 및 채점
        """
        try:
            # 문제 조회
            problem = db.query(Question).filter(Question.id == problem_id).first()
            if not problem:
                raise ValueError("문제를 찾을 수 없습니다.")
            
            # 답안 채점
            is_correct, score = await self._grade_answer(problem, answer)
            
            # 사용자의 현재 학습 수준 조회
            current_diagnosis = db.query(DiagnosisResult).filter(
                DiagnosisResult.user_id == user_id
            ).order_by(desc(DiagnosisResult.calculated_at)).first()
            
            previous_level = current_diagnosis.learning_level if current_diagnosis else 0.5
            
            # 학습 수준 업데이트 계산
            new_level = await self._update_learning_level(
                db, user_id, problem, is_correct, previous_level
            )
            
            # 응답 생성
            response = ProblemSubmissionResponse(
                submission_id=0,  # 실제로는 submission 테이블에 저장하고 ID 반환
                problem_id=problem_id,
                user_id=user_id,
                is_correct=is_correct,
                score=score,
                correct_answer=problem.correct_answer or "정답 정보 없음",
                explanation=await self._generate_explanation(problem, is_correct),
                feedback=await self._generate_feedback(problem, is_correct, score),
                time_spent=time_spent,
                submitted_at=datetime.utcnow(),
                previous_level=previous_level,
                new_level=new_level,
                level_change=new_level - previous_level
            )
            
            logger.info(f"답안 제출 완료: user_id={user_id}, problem_id={problem_id}, correct={is_correct}")
            return response
            
        except Exception as e:
            logger.error(f"답안 제출 실패: {str(e)}")
            raise
    
    async def get_user_statistics(
        self,
        db: Session,
        user_id: int,
        period_days: int = 30
    ) -> ProblemStatisticsResponse:
        """
        사용자 문제 풀이 통계 조회
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=period_days)
            
            # 기간 내 풀이한 문제들 조회
            responses = db.query(TestResponse).join(
                TestResponse.test_session
            ).filter(
                and_(
                    TestResponse.test_session.has(user_id=user_id),
                    TestResponse.answered_at.between(start_date, end_date)
                )
            ).all()
            
            # 전체 통계 계산
            total_problems = len(responses)
            correct_count = sum(1 for r in responses if r.is_correct)
            total_time = sum(r.time_spent_seconds or 0 for r in responses)
            
            overall_accuracy = correct_count / total_problems if total_problems > 0 else 0.0
            
            # 과목별 통계
            subject_stats = await self._calculate_subject_stats(db, responses)
            
            # 난이도별 통계
            difficulty_stats = await self._calculate_difficulty_stats(db, responses)
            
            # 일별 성과
            daily_performance = await self._calculate_daily_performance(responses, period_days)
            
            return ProblemStatisticsResponse(
                user_id=user_id,
                period_days=period_days,
                total_problems_solved=total_problems,
                total_time_spent=total_time // 60,  # 분 단위
                overall_accuracy=overall_accuracy,
                subject_stats=subject_stats,
                difficulty_stats=difficulty_stats,
                daily_performance=daily_performance,
                improvement_areas=await self._identify_improvement_areas(subject_stats, difficulty_stats),
                achievements=await self._calculate_achievements(user_id, responses),
                generated_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"통계 조회 실패: {str(e)}")
            raise
    
    async def get_user_problem_history(
        self,
        db: Session,
        user_id: int,
        subject: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[ProblemSubmissionResponse]:
        """
        사용자 문제 풀이 이력 조회
        """
        try:
            query = db.query(TestResponse).join(
                TestResponse.test_session
            ).filter(
                TestResponse.test_session.has(user_id=user_id)
            )
            
            if subject:
                query = query.join(TestResponse.question).filter(
                    Question.subject.ilike(f"%{subject}%")
                )
            
            responses = query.order_by(
                desc(TestResponse.answered_at)
            ).offset(offset).limit(limit).all()
            
            result = []
            for response in responses:
                problem = response.question
                result.append(ProblemSubmissionResponse(
                    submission_id=response.id,
                    problem_id=response.question_id,
                    user_id=user_id,
                    is_correct=response.is_correct or False,
                    score=response.score or 0.0,
                    correct_answer=problem.correct_answer or "정답 정보 없음",
                    explanation=None,
                    feedback=None,
                    time_spent=response.time_spent_seconds,
                    submitted_at=response.answered_at,
                    previous_level=None,
                    new_level=None,
                    level_change=None
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"이력 조회 실패: {str(e)}")
            raise
    
    async def get_review_problems(
        self,
        db: Session,
        user_id: int,
        review_type: str = "incorrect"
    ) -> List[ProblemResponse]:
        """
        복습 문제 조회
        """
        try:
            if review_type == "incorrect":
                # 오답 문제
                question_ids = db.query(TestResponse.question_id).join(
                    TestResponse.test_session
                ).filter(
                    and_(
                        TestResponse.test_session.has(user_id=user_id),
                        TestResponse.is_correct == False
                    )
                ).distinct().limit(20).all()
            
            elif review_type == "difficult":
                # 어려운 문제 (난이도 4-5)
                question_ids = db.query(TestResponse.question_id).join(
                    TestResponse.question
                ).filter(
                    and_(
                        TestResponse.test_session.has(user_id=user_id),
                        Question.difficulty.in_([4, 5])
                    )
                ).distinct().limit(20).all()
            
            else:  # recent
                # 최근 문제
                question_ids = db.query(TestResponse.question_id).join(
                    TestResponse.test_session
                ).filter(
                    TestResponse.test_session.has(user_id=user_id)
                ).order_by(desc(TestResponse.answered_at)).limit(20).all()
            
            # 문제 조회 및 변환
            problems = db.query(Question).filter(
                Question.id.in_([qid[0] for qid in question_ids])
            ).all()
            
            result = []
            for problem in problems:
                result.append(ProblemResponse(
                    id=problem.id,
                    title=f"복습 문제 {problem.id}",
                    content=problem.content,
                    choices=problem.choices,
                    problem_type=problem.question_type.value if problem.question_type else "multiple_choice",
                    difficulty=self._difficulty_enum_to_int(problem.difficulty),
                    subject=problem.subject_name or "일반",
                    source="database",
                    estimated_time=self._estimate_solve_time(problem),
                    tags=await self._get_problem_tags(db, problem.id),
                    hints=[],
                    created_at=problem.created_at or datetime.utcnow()
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"복습 문제 조회 실패: {str(e)}")
            raise
    
    # Private 메서드들
    async def _calculate_recommended_difficulty(self, learning_level: float) -> int:
        """학습 수준에 따른 추천 난이도 계산"""
        if learning_level >= 0.8:
            return 5  # expert
        elif learning_level >= 0.6:
            return 4  # hard
        elif learning_level >= 0.4:
            return 3  # medium
        elif learning_level >= 0.2:
            return 2  # easy
        else:
            return 1  # beginner
    
    async def _diversify_recommendations(
        self, 
        problems: List[Question], 
        limit: int
    ) -> List[Question]:
        """추천 문제 다양성 확보"""
        if len(problems) <= limit:
            return problems
        
        # 과목별, 난이도별 분산
        diversified = []
        subjects_used = set()
        difficulties_used = set()
        
        for problem in problems:
            if len(diversified) >= limit:
                break
            
            subject = problem.subject_name or "기타"
            difficulty = problem.difficulty
            
            # 다양성 체크
            if subject not in subjects_used or difficulty not in difficulties_used:
                diversified.append(problem)
                subjects_used.add(subject)
                difficulties_used.add(difficulty)
        
        # 부족한 경우 나머지 추가
        remaining = [p for p in problems if p not in diversified]
        random.shuffle(remaining)
        diversified.extend(remaining[:limit - len(diversified)])
        
        return diversified[:limit]
    
    async def _grade_answer(self, problem: Question, user_answer: str) -> Tuple[bool, float]:
        """답안 채점"""
        if not problem.correct_answer:
            return False, 0.0
        
        correct_answer = problem.correct_answer.strip().lower()
        user_answer_clean = user_answer.strip().lower()
        
        if problem.question_type.value == "multiple_choice":
            is_correct = correct_answer == user_answer_clean
            return is_correct, 1.0 if is_correct else 0.0
        
        elif problem.question_type.value == "true_false":
            is_correct = correct_answer in user_answer_clean or user_answer_clean in correct_answer
            return is_correct, 1.0 if is_correct else 0.0
        
        else:
            # 주관식: 유사도 기반 부분 점수
            similarity = self._calculate_text_similarity(correct_answer, user_answer_clean)
            is_correct = similarity >= 0.8
            return is_correct, similarity
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """텍스트 유사도 계산"""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if len(words1) == 0 and len(words2) == 0:
            return 1.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    async def _update_learning_level(
        self,
        db: Session,
        user_id: int,
        problem: Question,
        is_correct: bool,
        current_level: float
    ) -> float:
        """학습 수준 업데이트"""
        # 간단한 증감 로직 (실제로는 더 복잡한 알고리즘 적용)
        difficulty_score = self._get_difficulty_score(problem.difficulty)
        
        if is_correct:
            # 정답시 약간 상승
            improvement = 0.01 * difficulty_score
            new_level = min(1.0, current_level + improvement)
        else:
            # 오답시 약간 하락
            decrease = 0.005 * difficulty_score
            new_level = max(0.0, current_level - decrease)
        
        return new_level
    
    def _get_difficulty_score(self, difficulty) -> float:
        """난이도 점수 반환"""
        if not difficulty:
            return 1.0
        
        difficulty_map = {
            "easy": 1.0,
            "medium": 2.0,
            "hard": 3.0,
            "very_hard": 4.0
        }
        
        difficulty_str = difficulty.value if hasattr(difficulty, 'value') else str(difficulty)
        return difficulty_map.get(difficulty_str, 1.0)
    
    def _estimate_solve_time(self, problem: Question) -> int:
        """문제 풀이 예상 시간 계산 (분)"""
        base_time = 2  # 기본 2분
        
        if problem.question_type and problem.question_type.value == "essay":
            base_time = 10
        elif problem.question_type and problem.question_type.value == "short_answer":
            base_time = 5
        
        # 난이도에 따른 시간 가중치
        difficulty_multiplier = self._get_difficulty_score(problem.difficulty)
        
        return int(base_time * difficulty_multiplier)
    
    async def _get_problem_tags(self, db: Session, problem_id: int) -> List[str]:
        """문제 태그 조회"""
        try:
            tags = db.query(Tag).join(
                Tag.questions
            ).filter(Question.id == problem_id).all()
            
            return [tag.name for tag in tags]
        except:
            return []
    
    async def _generate_explanation(self, problem: Question, is_correct: bool) -> Optional[str]:
        """문제 해설 생성"""
        if is_correct:
            return "정답입니다! 잘 하셨습니다."
        else:
            return f"정답은 '{problem.correct_answer}'입니다. 다시 한 번 생각해보세요."
    
    async def _generate_feedback(self, problem: Question, is_correct: bool, score: float) -> Optional[str]:
        """피드백 메시지 생성"""
        if is_correct:
            return "훌륭합니다! 계속해서 좋은 성과를 내고 있습니다."
        elif score > 0.5:
            return "아쉽지만 부분 점수를 얻었습니다. 조금 더 정확하게 답해보세요."
        else:
            return "다시 한 번 문제를 자세히 읽어보고 도전해보세요."
    
    async def _calculate_subject_stats(self, db: Session, responses: List[TestResponse]) -> Dict[str, Dict[str, Any]]:
        """과목별 통계 계산"""
        subject_stats = {}
        
        for response in responses:
            if response.question:
                subject = response.question.subject_name or "기타"
                
                if subject not in subject_stats:
                    subject_stats[subject] = {
                        "total": 0, "correct": 0, "accuracy": 0.0, "avg_time": 0
                    }
                
                subject_stats[subject]["total"] += 1
                if response.is_correct:
                    subject_stats[subject]["correct"] += 1
        
        # 정확도 계산
        for subject, stats in subject_stats.items():
            if stats["total"] > 0:
                stats["accuracy"] = stats["correct"] / stats["total"]
        
        return subject_stats
    
    async def _calculate_difficulty_stats(self, db: Session, responses: List[TestResponse]) -> Dict[str, Dict[str, Any]]:
        """난이도별 통계 계산"""
        difficulty_stats = {}
        
        for response in responses:
            if response.question and response.question.difficulty:
                difficulty = response.question.difficulty.value
                
                if difficulty not in difficulty_stats:
                    difficulty_stats[difficulty] = {
                        "total": 0, "correct": 0, "accuracy": 0.0
                    }
                
                difficulty_stats[difficulty]["total"] += 1
                if response.is_correct:
                    difficulty_stats[difficulty]["correct"] += 1
        
        # 정확도 계산
        for difficulty, stats in difficulty_stats.items():
            if stats["total"] > 0:
                stats["accuracy"] = stats["correct"] / stats["total"]
        
        return difficulty_stats
    
    async def _calculate_daily_performance(self, responses: List[TestResponse], period_days: int) -> List[Dict[str, Any]]:
        """일별 성과 계산"""
        daily_data = {}
        
        for response in responses:
            if response.answered_at:
                date_key = response.answered_at.date().isoformat()
                
                if date_key not in daily_data:
                    daily_data[date_key] = {"total": 0, "correct": 0, "accuracy": 0.0}
                
                daily_data[date_key]["total"] += 1
                if response.is_correct:
                    daily_data[date_key]["correct"] += 1
        
        # 정확도 계산 및 정렬
        result = []
        for date_str, data in sorted(daily_data.items()):
            data["accuracy"] = data["correct"] / data["total"] if data["total"] > 0 else 0.0
            data["date"] = date_str
            result.append(data)
        
        return result
    
    async def _identify_improvement_areas(
        self, 
        subject_stats: Dict[str, Dict[str, Any]], 
        difficulty_stats: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """개선 영역 식별"""
        areas = []
        
        # 과목별 약점 식별
        for subject, stats in subject_stats.items():
            if stats["accuracy"] < 0.6:
                areas.append(f"{subject} 영역 개선 필요")
        
        # 난이도별 약점 식별
        for difficulty, stats in difficulty_stats.items():
            if stats["accuracy"] < 0.5:
                areas.append(f"{difficulty} 난이도 문제 연습 필요")
        
        return areas
    
    async def _calculate_achievements(self, user_id: int, responses: List[TestResponse]) -> List[Dict[str, Any]]:
        """성취 내역 계산"""
        achievements = []
        
        total_problems = len(responses)
        correct_count = sum(1 for r in responses if r.is_correct)
        
        # 문제 풀이 수 기반 성취
        if total_problems >= 100:
            achievements.append({
                "type": "problem_solver",
                "title": "문제 해결사",
                "description": "100문제 이상 해결",
                "earned_at": datetime.utcnow().isoformat()
            })
        
        # 정확도 기반 성취
        if total_problems > 0:
            accuracy = correct_count / total_problems
            if accuracy >= 0.9:
                achievements.append({
                    "type": "high_accuracy",
                    "title": "정확성 마스터",
                    "description": "90% 이상 정확도 달성",
                    "earned_at": datetime.utcnow().isoformat()
                })
        
        return achievements

    def _difficulty_enum_to_int(self, difficulty):
        """난이도 enum을 int로 변환"""
        if not difficulty:
            return 1
        
        difficulty_map = {
            DifficultyLevel.EASY: 1,
            DifficultyLevel.MEDIUM: 2,
            DifficultyLevel.HARD: 3,
            DifficultyLevel.VERY_HARD: 4
        }
        return difficulty_map.get(difficulty, 1)

# 싱글톤 인스턴스
problem_service = ProblemService() 