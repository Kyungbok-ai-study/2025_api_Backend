"""
AI 문제 생성 및 관련 서비스
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import json
import random
import openai
from sqlalchemy import func, desc, and_
from datetime import timedelta
import asyncio

from app.models.question import Question, QuestionType, DifficultyLevel
from app.models.user import User
from app.schemas.problems import AIGeneratedProblemResponse, ProblemResponse
from app.core.config import get_settings
from app.models.diagnosis import DiagnosisResult, TestResponse
from app.schemas.question import QuestionResponse
from app.schemas.diagnosis import DiagnosisSubject

logger = logging.getLogger(__name__)
settings = get_settings()

class AIService:
    """AI 문제 생성 및 관련 서비스"""
    
    def __init__(self):
        self.model_name = settings.AI_MODEL_NAME
        self.max_tokens = settings.AI_MAX_TOKENS
        self.temperature = settings.AI_TEMPERATURE
    
    async def generate_problem(
        self,
        db: Session,
        user_id: int,
        subject: str,
        difficulty: int,
        problem_type: str,
        context: Optional[str] = None
    ) -> AIGeneratedProblemResponse:
        """
        AI 문제 생성 (EXAONE Deep 활용)
        - PDF 학습 데이터 기반 문제 생성
        - 실시간 문제 생성 및 검증
        """
        try:
            # 문제 생성 프롬프트 구성
            prompt = await self._build_generation_prompt(
                subject, difficulty, problem_type, context
            )
            
            # AI 모델 호출 (실제로는 EXAONE API 호출)
            generated_content = await self._call_ai_model(prompt)
            
            # 생성된 문제 파싱 및 검증
            problem_data = await self._parse_generated_problem(generated_content)
            
            # 품질 점수 계산
            quality_score = await self._calculate_quality_score(problem_data)
            
            # 데이터베이스에 저장 (임시 문제로)
            question_type_enum = QuestionType.MULTIPLE_CHOICE  # 기본값
            if problem_type == "multiple_choice":
                question_type_enum = QuestionType.MULTIPLE_CHOICE
            elif problem_type == "short_answer":
                question_type_enum = QuestionType.SHORT_ANSWER
            elif problem_type == "essay":
                question_type_enum = QuestionType.ESSAY
            elif problem_type == "true_false":
                question_type_enum = QuestionType.TRUE_FALSE
                
            # 난이도를 enum으로 변환
            difficulty_enum = DifficultyLevel.MEDIUM  # 기본값
            if difficulty == 1:
                difficulty_enum = DifficultyLevel.EASY
            elif difficulty == 2:
                difficulty_enum = DifficultyLevel.MEDIUM
            elif difficulty >= 3:
                difficulty_enum = DifficultyLevel.HARD
            
            problem = Question(
                content=problem_data["content"],
                question_type=question_type_enum,
                difficulty=difficulty_enum,
                subject_name=subject,  # subject 대신 subject_name 사용
                choices=problem_data.get("choices"),
                correct_answer=problem_data.get("correct_answer"),
                is_active=False,  # 검토 전까지 비활성
                question_metadata={  # metadata 대신 question_metadata 사용
                    "generated_by_ai": True,
                    "generation_context": context,
                    "quality_score": quality_score,
                    "generated_at": datetime.utcnow().isoformat()
                }
            )
            
            db.add(problem)
            db.commit()
            db.refresh(problem)
            
            # 응답 객체 생성
            problem_response = ProblemResponse(
                id=problem.id,
                title=f"AI 생성 문제 {problem.id}",
                content=problem.content,
                choices=problem.choices,
                problem_type=problem.question_type.value if problem.question_type else "multiple_choice",
                difficulty=self._difficulty_enum_to_int(problem.difficulty),
                subject=problem.subject_name or "일반",
                source="ai_generated",
                estimated_time=self._estimate_solve_time(difficulty, problem_type),
                tags=await self._generate_problem_tags(problem_data),
                hints=problem_data.get("hints", []),
                created_at=datetime.utcnow()
            )
            
            generation_info = {
                "model_used": self.model_name,
                "generation_prompt": prompt[:200] + "...",  # 일부만 저장
                "context_used": context,
                "difficulty_requested": difficulty,
                "problem_type_requested": problem_type
            }
            
            response = AIGeneratedProblemResponse(
                problem=problem_response,
                generation_info=generation_info,
                quality_score=quality_score,
                reviewed=False,
                generated_at=datetime.utcnow()
            )
            
            logger.info(f"AI 문제 생성 완료: user_id={user_id}, problem_id={problem.id}")
            return response
            
        except Exception as e:
            logger.error(f"AI 문제 생성 실패: {str(e)}")
            raise
    
    async def review_generated_problem(
        self,
        db: Session,
        problem_id: int,
        reviewer_id: int,
        approved: bool,
        feedback: Optional[str] = None
    ) -> bool:
        """
        생성된 문제 검토 및 승인
        """
        try:
            problem = db.query(Question).filter(Question.id == problem_id).first()
            if not problem:
                raise ValueError("문제를 찾을 수 없습니다.")
            
            if approved:
                problem.is_active = True
                problem.question_metadata = problem.question_metadata or {}
                problem.question_metadata.update({
                    "reviewed_by": reviewer_id,
                    "reviewed_at": datetime.utcnow().isoformat(),
                    "approval_status": "approved",
                    "reviewer_feedback": feedback
                })
            else:
                problem.question_metadata = problem.question_metadata or {}
                problem.question_metadata.update({
                    "reviewed_by": reviewer_id,
                    "reviewed_at": datetime.utcnow().isoformat(),
                    "approval_status": "rejected",
                    "rejection_reason": feedback
                })
            
            db.commit()
            
            logger.info(f"문제 검토 완료: problem_id={problem_id}, approved={approved}")
            return True
            
        except Exception as e:
            logger.error(f"문제 검토 실패: {str(e)}")
            raise
    
    async def get_pending_reviews(
        self,
        db: Session,
        reviewer_id: int,
        limit: int = 20
    ) -> List[ProblemResponse]:
        """
        검토 대기 중인 AI 생성 문제 목록
        """
        try:
            problems = db.query(Question).filter(
                Question.is_active == False,
                Question.question_metadata.op('->>')('generated_by_ai') == 'true'
            ).limit(limit).all()
            
            result = []
            for problem in problems:
                result.append(ProblemResponse(
                    id=problem.id,
                    title=f"검토 대기 문제 {problem.id}",
                    content=problem.content,
                    choices=problem.choices,
                    problem_type=problem.question_type.value if problem.question_type else "multiple_choice",
                    difficulty=self._difficulty_enum_to_int(problem.difficulty),
                    subject=problem.subject_name or "일반",
                    source="ai_generated",
                    estimated_time=0,
                    tags=[],
                    hints=[],
                    created_at=problem.created_at or datetime.utcnow()
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"검토 대기 목록 조회 실패: {str(e)}")
            raise
    
    async def enhance_problem_with_ai(
        self,
        db: Session,
        problem_id: int,
        enhancement_type: str = "explanation"
    ) -> Dict[str, Any]:
        """
        기존 문제를 AI로 개선
        - 해설 생성, 힌트 추가, 유사 문제 생성 등
        """
        try:
            problem = db.query(Question).filter(Question.id == problem_id).first()
            if not problem:
                raise ValueError("문제를 찾을 수 없습니다.")
            
            if enhancement_type == "explanation":
                # 해설 생성
                enhancement = await self._generate_explanation(problem)
            elif enhancement_type == "hints":
                # 힌트 생성
                enhancement = await self._generate_hints(problem)
            elif enhancement_type == "similar":
                # 유사 문제 생성
                enhancement = await self._generate_similar_problems(problem)
            else:
                raise ValueError(f"지원하지 않는 개선 유형: {enhancement_type}")
            
            # 메타데이터 업데이트
            problem.question_metadata = problem.question_metadata or {}
            problem.question_metadata[f"ai_{enhancement_type}"] = enhancement
            problem.question_metadata[f"{enhancement_type}_generated_at"] = datetime.utcnow().isoformat()
            
            db.commit()
            
            logger.info(f"문제 AI 개선 완료: problem_id={problem_id}, type={enhancement_type}")
            return enhancement
            
        except Exception as e:
            logger.error(f"문제 AI 개선 실패: {str(e)}")
            raise
    
    async def analyze_learning_pattern(
        self,
        db: Session,
        user_id: int,
        analysis_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """
        AI 기반 학습 패턴 분석
        """
        if not self.enabled:
            return self._generate_default_pattern_analysis()
            
        try:
            # 사용자 학습 이력 조회
            from app.models.diagnosis import TestResponse
            
            responses = db.query(TestResponse).join(
                TestResponse.test_session
            ).filter(
                TestResponse.test_session.has(user_id=user_id)
            ).order_by(TestResponse.answered_at.desc()).limit(100).all()
            
            if not responses:
                return {"message": "분석할 학습 이력이 부족합니다."}
            
            # AI 분석 수행
            analysis_prompt = await self._build_analysis_prompt(responses, analysis_type)
            analysis_result = await self._call_ai_model(analysis_prompt)
            
            # 분석 결과 파싱
            parsed_analysis = await self._parse_analysis_result(analysis_result)
            
            logger.info(f"학습 패턴 분석 완료: user_id={user_id}, type={analysis_type}")
            return parsed_analysis
            
        except Exception as e:
            logger.error(f"학습 패턴 분석 실패: {str(e)}")
            raise
    
    # Private 메서드들
    async def _build_generation_prompt(
        self,
        subject: str,
        difficulty: int,
        problem_type: str,
        context: Optional[str]
    ) -> str:
        """문제 생성용 프롬프트 구성"""
        difficulty_names = {1: "초급", 2: "쉬움", 3: "보통", 4: "어려움", 5: "전문가"}
        difficulty_name = difficulty_names.get(difficulty, "보통")
        
        prompt = f"""
다음 조건에 맞는 {subject} 문제를 생성해주세요:

- 난이도: {difficulty_name} (1-5 중 {difficulty})
- 문제 유형: {problem_type}
- 과목: {subject}
"""
        
        if context:
            prompt += f"- 추가 컨텍스트: {context}\n"
        
        prompt += """
응답 형식은 다음 JSON 구조를 따라주세요:
{
    "content": "문제 내용",
    "choices": ["선택지1", "선택지2", "선택지3", "선택지4"] (객관식인 경우),
    "correct_answer": "정답",
    "explanation": "해설",
    "hints": ["힌트1", "힌트2"],
    "tags": ["태그1", "태그2"]
}
"""
        return prompt
    
    async def _call_ai_model(self, prompt: str) -> str:
        """
        AI 모델 호출 (실제 구현에서는 EXAONE API 호출)
        현재는 모의 응답 반환
        """
        # 실제 환경에서는 EXAONE API 호출
        # 현재는 개발용 모의 응답
        mock_response = {
            "content": "다음 중 데이터베이스의 ACID 속성에 해당하지 않는 것은?",
            "choices": [
                "Atomicity (원자성)",
                "Consistency (일관성)", 
                "Isolation (독립성)",
                "Durability (지속성)"
            ],
            "correct_answer": "모든 선택지가 ACID 속성에 해당함",
            "explanation": "ACID는 데이터베이스 트랜잭션의 4가지 기본 속성입니다.",
            "hints": ["트랜잭션의 기본 속성을 생각해보세요", "4가지 영문 앞글자를 따서 만든 용어입니다"],
            "tags": ["데이터베이스", "트랜잭션", "ACID"]
        }
        
        return json.dumps(mock_response, ensure_ascii=False)
    
    async def _parse_generated_problem(self, generated_content: str) -> Dict[str, Any]:
        """생성된 문제 파싱"""
        try:
            problem_data = json.loads(generated_content)
            
            # 필수 필드 검증
            required_fields = ["content", "correct_answer"]
            for field in required_fields:
                if field not in problem_data:
                    raise ValueError(f"필수 필드 누락: {field}")
            
            return problem_data
            
        except json.JSONDecodeError:
            # JSON 파싱 실패시 기본 구조 반환
            logger.warning("AI 응답 JSON 파싱 실패, 기본 구조 사용")
            return {
                "content": generated_content[:500],
                "correct_answer": "AI 생성 오류",
                "explanation": "문제 생성 중 오류가 발생했습니다.",
                "hints": [],
                "tags": []
            }
    
    async def _calculate_quality_score(self, problem_data: Dict[str, Any]) -> float:
        """문제 품질 점수 계산"""
        score = 0.0
        
        # 내용 길이 점수 (20-500자 적정)
        content_length = len(problem_data.get("content", ""))
        if 20 <= content_length <= 500:
            score += 0.3
        elif content_length > 500:
            score += 0.1
        
        # 정답 존재 여부
        if problem_data.get("correct_answer"):
            score += 0.3
        
        # 해설 존재 여부
        if problem_data.get("explanation"):
            score += 0.2
        
        # 힌트 존재 여부
        if problem_data.get("hints"):
            score += 0.1
        
        # 태그 존재 여부
        if problem_data.get("tags"):
            score += 0.1
        
        return min(1.0, score)
    
    def _estimate_solve_time(self, difficulty: int, problem_type: str) -> int:
        """풀이 시간 추정 (분)"""
        base_time = {
            "multiple_choice": 2,
            "true_false": 1,
            "short_answer": 5,
            "essay": 15
        }.get(problem_type, 3)
        
        difficulty_multiplier = 1 + (difficulty - 1) * 0.5
        return int(base_time * difficulty_multiplier)
    
    async def _generate_problem_tags(self, problem_data: Dict[str, Any]) -> List[str]:
        """문제 태그 생성"""
        tags = problem_data.get("tags", [])
        
        # 기본 태그 추가
        content = problem_data.get("content", "").lower()
        
        if "데이터베이스" in content or "database" in content:
            tags.append("database")
        if "알고리즘" in content or "algorithm" in content:
            tags.append("algorithm")
        if "프로그래밍" in content or "programming" in content:
            tags.append("programming")
        
        return list(set(tags))  # 중복 제거
    
    async def _generate_explanation(self, problem: Question) -> Dict[str, Any]:
        """문제 해설 생성"""
        prompt = f"""
다음 문제에 대한 자세한 해설을 작성해주세요:

문제: {problem.content}
정답: {problem.correct_answer}

해설은 다음을 포함해야 합니다:
1. 정답인 이유
2. 오답인 이유 (객관식의 경우)
3. 관련 개념 설명
4. 참고 자료나 추가 학습 방향
"""
        
        explanation_text = await self._call_ai_model(prompt)
        
        return {
            "explanation": explanation_text,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    async def _generate_hints(self, problem: Question) -> Dict[str, Any]:
        """문제 힌트 생성"""
        prompt = f"""
다음 문제에 대한 단계별 힌트 3개를 생성해주세요:

문제: {problem.content}

힌트는 다음 조건을 만족해야 합니다:
1. 첫 번째 힌트: 문제 해결의 방향 제시
2. 두 번째 힌트: 구체적인 접근 방법
3. 세 번째 힌트: 거의 정답에 가까운 힌트

JSON 형식으로 응답해주세요:
{{"hints": ["힌트1", "힌트2", "힌트3"]}}
"""
        
        hints_response = await self._call_ai_model(prompt)
        
        try:
            hints_data = json.loads(hints_response)
            return hints_data
        except:
            return {"hints": ["문제를 차근차근 읽어보세요", "핵심 개념을 떠올려보세요", "선택지를 하나씩 검토해보세요"]}
    
    async def _generate_similar_problems(self, problem: Question) -> Dict[str, Any]:
        """유사 문제 생성"""
        prompt = f"""
다음 문제와 유사한 문제 2개를 생성해주세요:

원본 문제: {problem.content}
원본 정답: {problem.correct_answer}

유사 문제는 다음 조건을 만족해야 합니다:
1. 같은 개념을 다루되 다른 상황이나 예시
2. 난이도는 비슷하게 유지
3. 문제 유형은 동일하게 유지

JSON 형식으로 응답해주세요:
{{"similar_problems": [
    {{"content": "문제1", "correct_answer": "정답1"}},
    {{"content": "문제2", "correct_answer": "정답2"}}
]}}
"""
        
        similar_response = await self._call_ai_model(prompt)
        
        try:
            similar_data = json.loads(similar_response)
            return similar_data
        except:
            return {"similar_problems": []}
    
    async def _build_analysis_prompt(self, responses: List, analysis_type: str) -> str:
        """학습 패턴 분석용 프롬프트 구성"""
        # 응답 데이터 요약
        correct_count = sum(1 for r in responses if r.is_correct)
        total_count = len(responses)
        accuracy = correct_count / total_count if total_count > 0 else 0
        
        prompt = f"""
다음 학습 이력을 분석하고 패턴을 찾아주세요:

전체 문제 수: {total_count}
정답 수: {correct_count}
정확도: {accuracy:.2%}

분석 유형: {analysis_type}

분석 결과를 다음 JSON 형식으로 제공해주세요:
{{
    "strengths": ["강점1", "강점2"],
    "weaknesses": ["약점1", "약점2"],
    "learning_pattern": "학습 패턴 설명",
    "recommendations": ["추천1", "추천2", "추천3"],
    "improvement_priority": "개선 우선순위"
}}
"""
        return prompt
    
    async def _parse_analysis_result(self, analysis_result: str) -> Dict[str, Any]:
        """분석 결과 파싱"""
        try:
            analysis_data = json.loads(analysis_result)
            return analysis_data
        except:
            # 파싱 실패시 기본 분석 결과
            return {
                "strengths": ["꾸준한 학습 참여"],
                "weaknesses": ["개선이 필요한 영역이 있습니다"],
                "learning_pattern": "분석 중 오류가 발생했습니다",
                "recommendations": ["기초 개념 복습", "꾸준한 연습"],
                "improvement_priority": "기본기 강화"
            }
    
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
ai_service = AIService()

class EnhancedAIService:
    """향상된 AI 분석 및 생성 서비스"""
    
    def __init__(self):
        try:
            if hasattr(settings, 'AI_API_KEY') and settings.AI_API_KEY:
                self.client = openai.AsyncOpenAI(api_key=settings.AI_API_KEY)
                self.model = "gpt-4o-mini"
                self.enabled = True
            else:
                self.client = None
                self.model = None
                self.enabled = False
                logger.warning("AI API 키가 설정되지 않았습니다. AI 기능이 비활성화됩니다.")
        except Exception as e:
            logger.error(f"AI 서비스 초기화 실패: {str(e)}")
            self.client = None
            self.model = None
            self.enabled = False
        
    async def analyze_learning_pattern(self, db: Session, user_id: int) -> Dict[str, Any]:
        """학습 패턴 AI 분석"""
        if not self.enabled:
            return self._generate_default_pattern_analysis()
            
        try:
            # 사용자의 최근 학습 데이터 수집
            recent_results = db.query(DiagnosisResult).filter(
                DiagnosisResult.user_id == user_id
            ).order_by(desc(DiagnosisResult.calculated_at)).limit(10).all()
            
            if not recent_results:
                return self._generate_default_pattern_analysis()
            
            # AI에게 분석 요청
            analysis_prompt = self._create_pattern_analysis_prompt(recent_results)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 교육 데이터 분석 전문가입니다. 학습자의 패턴을 분석하고 개선 방안을 제시해주세요."},
                    {"role": "user", "content": analysis_prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            analysis = json.loads(response.choices[0].message.content)
            
            # 분석 결과에 메타데이터 추가
            analysis["analysis_date"] = datetime.now().isoformat()
            analysis["data_points"] = len(recent_results)
            analysis["confidence_score"] = self._calculate_analysis_confidence(recent_results)
            
            return analysis
            
        except Exception as e:
            logger.error(f"학습 패턴 분석 실패: {str(e)}")
            return self._generate_default_pattern_analysis()
    
    async def generate_personalized_study_path(self, db: Session, user_id: int) -> Dict[str, Any]:
        """개인 맞춤형 학습 경로 생성"""
        try:
            # 사용자 분석 데이터 수집
            pattern_analysis = await self.analyze_learning_pattern(db, user_id)
            weak_areas = await self._identify_weak_areas(db, user_id)
            learning_goals = await self._get_user_learning_goals(db, user_id)
            
            # AI에게 학습 경로 생성 요청
            path_prompt = self._create_study_path_prompt(pattern_analysis, weak_areas, learning_goals)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 개인 맞춤 학습 코치입니다. 학습자의 현재 수준과 목표에 맞는 단계별 학습 경로를 설계해주세요."},
                    {"role": "user", "content": path_prompt}
                ],
                max_tokens=1500,
                temperature=0.4
            )
            
            study_path = json.loads(response.choices[0].message.content)
            
            # 경로에 실행 가능한 액션 추가
            study_path["actionable_steps"] = await self._generate_actionable_steps(db, study_path)
            study_path["estimated_completion"] = self._calculate_completion_time(study_path)
            
            return study_path
            
        except Exception as e:
            logger.error(f"개인 맞춤 학습 경로 생성 실패: {str(e)}")
            return self._generate_default_study_path()
    
    async def predict_performance(self, db: Session, user_id: int, subject: str) -> Dict[str, Any]:
        """성과 예측 모델"""
        try:
            # 과거 성과 데이터 수집
            historical_data = await self._collect_historical_performance(db, user_id, subject)
            
            if len(historical_data) < 3:
                return {"prediction": "insufficient_data", "confidence": 0.0}
            
            # AI 예측 모델
            prediction_prompt = self._create_prediction_prompt(historical_data, subject)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 학습 성과 예측 전문가입니다. 과거 데이터를 바탕으로 미래 성과를 예측해주세요."},
                    {"role": "user", "content": prediction_prompt}
                ],
                max_tokens=800,
                temperature=0.2
            )
            
            prediction = json.loads(response.choices[0].message.content)
            
            # 예측 신뢰도 계산
            prediction["confidence"] = self._calculate_prediction_confidence(historical_data)
            prediction["prediction_date"] = datetime.now().isoformat()
            
            return prediction
            
        except Exception as e:
            logger.error(f"성과 예측 실패: {str(e)}")
            return {"prediction": "error", "confidence": 0.0, "error": str(e)}
    
    async def generate_adaptive_questions(self, db: Session, user_id: int, difficulty_target: float) -> List[Dict[str, Any]]:
        """적응형 문제 생성"""
        try:
            # 사용자 수준 분석
            user_profile = await self._analyze_user_profile(db, user_id)
            weak_topics = user_profile.get("weak_topics", [])
            strong_topics = user_profile.get("strong_topics", [])
            
            # AI 문제 생성
            questions = []
            for i in range(5):  # 5개 문제 생성
                question_prompt = self._create_adaptive_question_prompt(
                    user_profile, difficulty_target, weak_topics, strong_topics
                )
                
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "당신은 교육 문제 출제 전문가입니다. 학습자 수준에 맞는 적응형 문제를 생성해주세요."},
                        {"role": "user", "content": question_prompt}
                    ],
                    max_tokens=600,
                    temperature=0.6
                )
                
                question = json.loads(response.choices[0].message.content)
                question["generated_at"] = datetime.now().isoformat()
                question["target_difficulty"] = difficulty_target
                questions.append(question)
            
            return questions
            
        except Exception as e:
            logger.error(f"적응형 문제 생성 실패: {str(e)}")
            return []
    
    async def analyze_mistake_patterns(self, db: Session, user_id: int) -> Dict[str, Any]:
        """실수 패턴 분석"""
        try:
            # 틀린 문제들 분석
            wrong_responses = db.query(TestResponse).join(DiagnosisResult).filter(
                and_(
                    DiagnosisResult.user_id == user_id,
                    TestResponse.is_correct == False
                )
            ).limit(50).all()
            
            if not wrong_responses:
                return {"patterns": [], "analysis": "insufficient_data"}
            
            # AI 패턴 분석
            mistake_prompt = self._create_mistake_analysis_prompt(wrong_responses)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 학습 오류 분석 전문가입니다. 학습자의 실수 패턴을 분석하고 개선 방안을 제시해주세요."},
                    {"role": "user", "content": mistake_prompt}
                ],
                max_tokens=1200,
                temperature=0.3
            )
            
            analysis = json.loads(response.choices[0].message.content)
            analysis["analyzed_mistakes"] = len(wrong_responses)
            analysis["analysis_date"] = datetime.now().isoformat()
            
            return analysis
            
        except Exception as e:
            logger.error(f"실수 패턴 분석 실패: {str(e)}")
            return {"patterns": [], "analysis": "error", "error": str(e)}
    
    async def generate_motivational_feedback(self, db: Session, user_id: int, recent_performance: Dict) -> str:
        """동기부여 피드백 생성"""
        try:
            # 사용자 정보 및 최근 성과 수집
            user = db.query(User).filter(User.id == user_id).first()
            progress_trend = await self._calculate_progress_trend(db, user_id)
            
            feedback_prompt = f"""
            사용자 정보:
            - 이름: {user.name if user else '학습자'}
            - 최근 성과: {recent_performance}
            - 진행 추세: {progress_trend}
            
            개인화된 동기부여 메시지를 생성해주세요. 긍정적이고 구체적이며 실행 가능한 조언을 포함해주세요.
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 경험 많은 학습 코치입니다. 학습자를 격려하고 동기를 부여하는 개인화된 메시지를 작성해주세요."},
                    {"role": "user", "content": feedback_prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"동기부여 피드백 생성 실패: {str(e)}")
            return "계속해서 좋은 성과를 내고 계시네요! 꾸준한 학습으로 더 큰 발전을 이뤄보세요."
    
    # Private helper methods
    def _create_pattern_analysis_prompt(self, results: List[DiagnosisResult]) -> str:
        """패턴 분석용 프롬프트 생성"""
        data_summary = []
        for result in results:
            data_summary.append({
                "date": result.calculated_at.isoformat(),
                "learning_level": result.learning_level,
                "accuracy": result.accuracy_rate,
                "time_spent": result.total_time_spent,
                "difficulty_breakdown": result.difficulty_breakdown
            })
        
        return f"""
        다음 학습 데이터를 분석하여 패턴을 찾고 개선 방안을 제시해주세요:
        
        데이터: {json.dumps(data_summary, ensure_ascii=False)}
        
        다음 형태의 JSON으로 응답해주세요:
        {{
            "learning_patterns": ["패턴1", "패턴2"],
            "strengths": ["강점1", "강점2"],
            "weaknesses": ["약점1", "약점2"],
            "improvement_suggestions": ["제안1", "제안2"],
            "trend_analysis": "전반적인 추세 분석"
        }}
        """
    
    def _create_study_path_prompt(self, pattern_analysis: Dict, weak_areas: List, goals: Dict) -> str:
        """학습 경로 생성용 프롬프트"""
        return f"""
        다음 정보를 바탕으로 개인 맞춤 학습 경로를 설계해주세요:
        
        학습 패턴 분석: {json.dumps(pattern_analysis, ensure_ascii=False)}
        약점 영역: {weak_areas}
        학습 목표: {json.dumps(goals, ensure_ascii=False)}
        
        다음 형태의 JSON으로 응답해주세요:
        {{
            "path_title": "학습 경로 제목",
            "total_duration_weeks": 4,
            "weekly_plans": [
                {{
                    "week": 1,
                    "focus_areas": ["영역1", "영역2"],
                    "learning_objectives": ["목표1", "목표2"],
                    "recommended_activities": ["활동1", "활동2"],
                    "estimated_hours": 10
                }}
            ],
            "milestones": ["중간목표1", "중간목표2"],
            "success_metrics": ["평가지표1", "평가지표2"]
        }}
        """
    
    def _generate_default_pattern_analysis(self) -> Dict[str, Any]:
        """기본 패턴 분석"""
        return {
            "learning_patterns": ["데이터 부족으로 패턴 분석 불가"],
            "strengths": ["꾸준한 학습 참여"],
            "weaknesses": ["더 많은 데이터 필요"],
            "improvement_suggestions": ["지속적인 학습으로 데이터 축적"],
            "trend_analysis": "초기 단계",
            "confidence_score": 0.1
        }
    
    async def _identify_weak_areas(self, db: Session, user_id: int) -> List[str]:
        """약점 영역 식별"""
        results = db.query(DiagnosisResult).filter(
            DiagnosisResult.user_id == user_id
        ).order_by(desc(DiagnosisResult.calculated_at)).limit(5).all()
        
        weak_areas = []
        for result in results:
            if result.difficulty_breakdown:
                for difficulty, data in result.difficulty_breakdown.items():
                    if data.get("score", 0) / max(data.get("max_score", 1), 1) < 0.6:
                        weak_areas.append(f"{difficulty} 수준")
        
        return list(set(weak_areas))
    
    async def _get_user_learning_goals(self, db: Session, user_id: int) -> Dict[str, Any]:
        """사용자 학습 목표 조회"""
        # 실제 구현에서는 사용자 목표 테이블에서 조회
        return {
            "target_level": 0.8,
            "target_date": (datetime.now() + timedelta(days=30)).isoformat(),
            "priority_subjects": ["데이터베이스", "알고리즘"]
        }

# 싱글톤 인스턴스
enhanced_ai_service = EnhancedAIService() 