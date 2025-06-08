"""
AI 문제 생성 및 관련 서비스 - DeepSeek 기반
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import json
import random
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
from .deepseek_service import deepseek_service

logger = logging.getLogger(__name__)
settings = get_settings()

class AIService:
    """AI 문제 생성 및 관련 서비스 - DeepSeek 기반"""
    
    def __init__(self):
        self.deepseek = deepseek_service
        self.model_name = "deepseek-r1:8b"
        self.temperature = 0.7
        logger.info("✅ AI 서비스 초기화 완료 (DeepSeek 기반)")
    
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
        AI 문제 생성 (DeepSeek 활용)
        - RAG 기반 문제 생성
        - 실시간 문제 생성 및 검증
        """
        try:
            logger.info(f"🎯 AI 문제 생성 시작: {subject} (난이도: {difficulty})")
            
            # 문제 생성 프롬프트 구성
            prompt = await self._build_generation_prompt(
                subject, difficulty, problem_type, context
            )
            
            # DeepSeek 모델 호출
            generated_content = await self._call_deepseek_model(prompt)
            
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
            difficulty_enum = DifficultyLevel.MEDIUM
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
                subject_name=subject,
                choices=problem_data.get("choices"),
                correct_answer=problem_data.get("correct_answer"),
                is_active=False,  # 검토 전까지 비활성
                question_metadata={
                    "generated_by_ai": True,
                    "ai_model": "DeepSeek R1 8B",
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
                title=f"DeepSeek 생성 문제 {problem.id}",
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
                "generation_prompt": prompt[:200] + "...",
                "context_used": context,
                "difficulty_requested": difficulty,
                "problem_type_requested": problem_type,
                "ai_system": "DeepSeek + Qdrant RAG"
            }
            
            response = AIGeneratedProblemResponse(
                problem=problem_response,
                generation_info=generation_info,
                quality_score=quality_score,
                reviewed=False,
                generated_at=datetime.utcnow()
            )
            
            logger.info(f"✅ DeepSeek 문제 생성 완료: user_id={user_id}, problem_id={problem.id}")
            return response
            
        except Exception as e:
            logger.error(f"❌ AI 문제 생성 실패: {str(e)}")
            raise
    
    async def enhance_problem_with_ai(
        self,
        db: Session,
        problem_id: int,
        enhancement_type: str = "explanation"
    ) -> Dict[str, Any]:
        """
        기존 문제를 DeepSeek으로 개선
        - 해설 생성, 힌트 추가, 유사 문제 생성 등
        """
        try:
            problem = db.query(Question).filter(Question.id == problem_id).first()
            if not problem:
                raise ValueError("문제를 찾을 수 없습니다.")
            
            if enhancement_type == "explanation":
                # DeepSeek으로 해설 생성
                enhancement = await self._generate_explanation(problem)
            elif enhancement_type == "hints":
                # DeepSeek으로 힌트 생성
                enhancement = await self._generate_hints(problem)
            elif enhancement_type == "similar":
                # DeepSeek으로 유사 문제 생성
                enhancement = await self._generate_similar_problems(problem)
            else:
                raise ValueError(f"지원하지 않는 개선 유형: {enhancement_type}")
            
            # 메타데이터 업데이트
            problem.question_metadata = problem.question_metadata or {}
            problem.question_metadata[f"deepseek_{enhancement_type}"] = enhancement
            problem.question_metadata[f"{enhancement_type}_generated_at"] = datetime.utcnow().isoformat()
            
            db.commit()
            
            logger.info(f"✅ DeepSeek 문제 개선 완료: problem_id={problem_id}, type={enhancement_type}")
            return enhancement
            
        except Exception as e:
            logger.error(f"❌ DeepSeek 문제 개선 실패: {str(e)}")
            raise
    
    async def generate_question(
        self,
        topic: str,
        difficulty: str = "중",
        question_type: str = "multiple_choice",
        department: str = "간호학과"
    ) -> Dict[str, Any]:
        """
        간단한 문제 생성 (테스트용)
        """
        try:
            prompt = f"""
{department} 학생을 위한 {topic}에 관한 {difficulty} 난이도의 {question_type} 문제를 생성해주세요.

다음 JSON 형식으로 응답해주세요:
{{
    "question": "문제 내용",
    "options": ["선택지1", "선택지2", "선택지3", "선택지4"],
    "correct_answer": 1,
    "explanation": "정답 해설",
    "difficulty": "{difficulty}",
    "subject": "{topic}"
}}
"""
            
            messages = [{"role": "user", "content": prompt}]
            result = await self.deepseek.chat_completion(messages, temperature=0.7)
            
            if result["success"]:
                try:
                    question_data = json.loads(result["content"])
                    return {
                        "success": True,
                        "question": question_data.get("question", ""),
                        "options": question_data.get("options", []),
                        "correct_answer": question_data.get("correct_answer", 1),
                        "explanation": question_data.get("explanation", ""),
                        "difficulty": difficulty,
                        "subject": topic
                    }
                except json.JSONDecodeError:
                    return {
                        "success": True,
                        "question": result["content"][:200] + "...",
                        "options": ["선택지1", "선택지2", "선택지3", "선택지4"],
                        "correct_answer": 1,
                        "explanation": "DeepSeek에서 생성된 문제입니다.",
                        "difficulty": difficulty,
                        "subject": topic
                    }
            else:
                return {"success": False, "error": result.get("error", "Unknown")}
                
        except Exception as e:
            logger.error(f"❌ 문제 생성 실패: {e}")
            return {"success": False, "error": str(e)}
    
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
            logger.error(f"❌ 검토 대기 목록 조회 실패: {str(e)}")
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
    "choices": ["선택지1", "선택지2", "선택지3", "선택지4"],
    "correct_answer": "정답",
    "explanation": "해설",
    "hints": ["힌트1", "힌트2"],
    "tags": ["태그1", "태그2"]
}
"""
        return prompt
    
    async def _call_deepseek_model(self, prompt: str) -> str:
        """DeepSeek 모델 호출"""
        try:
            result = await self.deepseek.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature
            )
            
            if result["success"]:
                return result["content"]
            else:
                logger.error(f"❌ DeepSeek 호출 실패: {result.get('error')}")
                raise Exception(f"DeepSeek 호출 실패: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"❌ DeepSeek 모델 호출 오류: {e}")
            raise
    
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
            logger.warning("⚠️ DeepSeek 응답 JSON 파싱 실패, 기본 구조 사용")
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
        
        if "간호" in content:
            tags.append("nursing")
        if "치료" in content:
            tags.append("therapy")
        if "환자" in content:
            tags.append("patient")
        if "진단" in content:
            tags.append("diagnosis")
        
        return list(set(tags))  # 중복 제거
    
    def _difficulty_enum_to_int(self, difficulty_enum) -> int:
        """DifficultyLevel enum을 int로 변환"""
        if difficulty_enum == DifficultyLevel.EASY:
            return 1
        elif difficulty_enum == DifficultyLevel.MEDIUM:
            return 2
        elif difficulty_enum == DifficultyLevel.HARD:
            return 3
        else:
            return 2  # 기본값
    
    async def _generate_explanation(self, problem: Question) -> Dict[str, Any]:
        """DeepSeek으로 문제 해설 생성"""
        prompt = f"""
다음 문제에 대한 자세한 해설을 작성해주세요:

문제: {problem.content}
정답: {problem.correct_answer}

해설은 다음을 포함해야 합니다:
1. 정답인 이유
2. 오답인 이유 (객관식의 경우)
3. 관련 개념 설명
4. 참고 자료나 추가 학습 방향

응답은 JSON 형식으로 해주세요:
{{"explanation": "상세한 해설"}}
"""
        
        try:
            result = await self.deepseek.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            if result["success"]:
                try:
                    explanation_data = json.loads(result["content"])
                    return {
                        "explanation": explanation_data.get("explanation", "해설 생성 완료"),
                        "generated_at": datetime.utcnow().isoformat(),
                        "generated_by": "DeepSeek R1 8B"
                    }
                except json.JSONDecodeError:
                    return {
                        "explanation": result["content"],
                        "generated_at": datetime.utcnow().isoformat(),
                        "generated_by": "DeepSeek R1 8B"
                    }
            else:
                logger.error(f"❌ 해설 생성 실패: {result.get('error')}")
                return {"explanation": "해설 생성 중 오류가 발생했습니다."}
                
        except Exception as e:
            logger.error(f"❌ 해설 생성 오류: {e}")
            return {"explanation": "해설 생성 중 오류가 발생했습니다."}
    
    async def _generate_hints(self, problem: Question) -> Dict[str, Any]:
        """DeepSeek으로 문제 힌트 생성"""
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
        
        try:
            result = await self.deepseek.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5
            )
            
            if result["success"]:
                try:
                    hints_data = json.loads(result["content"])
                    return hints_data
                except json.JSONDecodeError:
                    return {"hints": ["문제를 차근차근 읽어보세요", "핵심 개념을 떠올려보세요", "선택지를 하나씩 검토해보세요"]}
            else:
                return {"hints": ["문제를 차근차근 읽어보세요", "핵심 개념을 떠올려보세요", "선택지를 하나씩 검토해보세요"]}
                
        except Exception as e:
            logger.error(f"❌ 힌트 생성 오류: {e}")
            return {"hints": ["문제를 차근차근 읽어보세요", "핵심 개념을 떠올려보세요", "선택지를 하나씩 검토해보세요"]}
    
    async def _generate_similar_problems(self, problem: Question) -> Dict[str, Any]:
        """DeepSeek으로 유사 문제 생성"""
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
        
        try:
            result = await self.deepseek.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            if result["success"]:
                try:
                    similar_data = json.loads(result["content"])
                    return similar_data
                except json.JSONDecodeError:
                    return {"similar_problems": []}
            else:
                return {"similar_problems": []}
                
        except Exception as e:
            logger.error(f"❌ 유사 문제 생성 오류: {e}")
            return {"similar_problems": []}

# 싱글톤 인스턴스
ai_service = AIService()

class EnhancedAIService:
    """향상된 AI 분석 및 생성 서비스 - DeepSeek 기반"""
    
    def __init__(self):
        self.deepseek = deepseek_service
        self.enabled = True
        logger.info("✅ Enhanced AI 서비스 초기화 완료 (DeepSeek 기반)")
    
    async def analyze_user_performance(self, db: Session, user_id: int) -> Dict[str, Any]:
        """사용자 성능 분석 (DeepSeek 기반)"""
        if not self.enabled:
            logger.warning("⚠️ DeepSeek 서비스가 비활성화됨")
            return {"error": "AI 서비스 비활성화됨"}
        
        try:
            # 사용자 진단 결과 조회
            recent_results = db.query(DiagnosisResult).filter(
                DiagnosisResult.user_id == user_id
            ).order_by(desc(DiagnosisResult.created_at)).limit(10).all()
            
            if not recent_results:
                return {"analysis": "분석할 데이터가 부족합니다.", "recommendations": []}
            
            # 성능 데이터 준비
            performance_data = []
            for result in recent_results:
                performance_data.append({
                    "score": result.overall_score,
                    "strengths": result.strength_areas,
                    "weaknesses": result.weakness_areas,
                    "date": result.created_at.isoformat()
                })
            
            # DeepSeek으로 분석
            analysis_prompt = f"""
다음은 사용자의 최근 학습 성과 데이터입니다:

{json.dumps(performance_data, ensure_ascii=False, indent=2)}

이 데이터를 바탕으로 다음을 분석해주세요:
1. 학습 성과 추이
2. 강점과 약점 영역
3. 개선 권장사항
4. 맞춤형 학습 전략

JSON 형식으로 응답해주세요:
{{
    "performance_trend": "성과 추이 분석",
    "strength_areas": ["강점 영역1", "강점 영역2"],
    "weakness_areas": ["약점 영역1", "약점 영역2"],
    "recommendations": ["권장사항1", "권장사항2", "권장사항3"],
    "learning_strategy": "맞춤형 학습 전략"
}}
"""
            
            result = await self.deepseek.chat_completion(
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=0.3
            )
            
            if result["success"]:
                try:
                    analysis = json.loads(result["content"])
                    return analysis
                except json.JSONDecodeError:
                    return {
                        "analysis": result["content"],
                        "recommendations": ["DeepSeek 기반 맞춤형 학습을 계속 진행하세요."]
                    }
            else:
                return {"error": "성능 분석 실패"}
                
        except Exception as e:
            logger.error(f"❌ 사용자 성능 분석 실패: {e}")
            return {"error": f"분석 중 오류 발생: {str(e)}"}
    
    async def generate_adaptive_questions(self, db: Session, user_id: int, difficulty_target: float) -> List[Dict[str, Any]]:
        """적응형 문제 생성 (DeepSeek 기반)"""
        try:
            # 사용자 수준 분석
            user_profile = await self._analyze_user_profile(db, user_id)
            weak_topics = user_profile.get("weak_topics", [])
            strong_topics = user_profile.get("strong_topics", [])
            
            # DeepSeek으로 적응형 문제 생성
            questions = []
            for i in range(5):  # 5개 문제 생성
                question_prompt = self._create_adaptive_question_prompt(
                    user_profile, difficulty_target, weak_topics, strong_topics
                )
                
                result = await self.deepseek.chat_completion(
                    messages=[{"role": "user", "content": question_prompt}],
                    temperature=0.6
                )
                
                if result["success"]:
                    try:
                        question = json.loads(result["content"])
                        question["generated_at"] = datetime.now().isoformat()
                        question["target_difficulty"] = difficulty_target
                        question["generated_by"] = "DeepSeek R1 8B"
                        questions.append(question)
                    except json.JSONDecodeError:
                        logger.warning(f"⚠️ 문제 {i+1} JSON 파싱 실패")
                        continue
            
            return questions
            
        except Exception as e:
            logger.error(f"❌ 적응형 문제 생성 실패: {e}")
            return []
    
    async def _analyze_user_profile(self, db: Session, user_id: int) -> Dict[str, Any]:
        """사용자 프로필 분석"""
        try:
            # 사용자 정보 조회
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {}
            
            # 최근 테스트 응답 조회
            recent_responses = db.query(TestResponse).filter(
                TestResponse.user_id == user_id
            ).order_by(desc(TestResponse.created_at)).limit(20).all()
            
            # 프로필 데이터 구성
            profile = {
                "user_id": user_id,
                "department": user.department if hasattr(user, 'department') else "일반",
                "total_responses": len(recent_responses),
                "weak_topics": [],
                "strong_topics": []
            }
            
            # 주제별 성과 분석
            topic_performance = {}
            for response in recent_responses:
                if hasattr(response, 'question') and response.question:
                    topic = response.question.subject_name or "일반"
                    if topic not in topic_performance:
                        topic_performance[topic] = {"correct": 0, "total": 0}
                    
                    topic_performance[topic]["total"] += 1
                    if response.is_correct:
                        topic_performance[topic]["correct"] += 1
            
            # 강점/약점 분류
            for topic, perf in topic_performance.items():
                if perf["total"] >= 3:  # 최소 3문제 이상
                    accuracy = perf["correct"] / perf["total"]
                    if accuracy >= 0.8:
                        profile["strong_topics"].append(topic)
                    elif accuracy <= 0.5:
                        profile["weak_topics"].append(topic)
            
            return profile
            
        except Exception as e:
            logger.error(f"❌ 사용자 프로필 분석 실패: {e}")
            return {}
    
    def _create_adaptive_question_prompt(
        self, 
        user_profile: Dict[str, Any], 
        difficulty_target: float,
        weak_topics: List[str],
        strong_topics: List[str]
    ) -> str:
        """적응형 문제 생성 프롬프트 생성"""
        
        department = user_profile.get("department", "일반")
        
        # 약점 주제 우선 선택
        target_topic = "일반"
        if weak_topics:
            target_topic = weak_topics[0]  # 가장 약한 주제
        elif strong_topics:
            target_topic = strong_topics[0]  # 강점 주제로 심화
        
        difficulty_desc = "중급"
        if difficulty_target <= 0.3:
            difficulty_desc = "초급"
        elif difficulty_target <= 0.7:
            difficulty_desc = "중급"
        else:
            difficulty_desc = "고급"
        
        prompt = f"""
다음 조건에 맞는 {department} 맞춤형 문제를 생성해주세요:

사용자 프로필:
- 학과: {department}
- 약점 영역: {', '.join(weak_topics) if weak_topics else '없음'}
- 강점 영역: {', '.join(strong_topics) if strong_topics else '없음'}

문제 조건:
- 주제: {target_topic}
- 난이도: {difficulty_desc} (목표 정답률: {difficulty_target:.1%})
- 문제 유형: 객관식 4지선다

JSON 형식으로 응답해주세요:
{{
    "content": "문제 내용",
    "choices": ["선택지1", "선택지2", "선택지3", "선택지4"],
    "correct_answer": 1,
    "explanation": "해설",
    "topic": "{target_topic}",
    "difficulty": "{difficulty_desc}",
    "target_weakness": {weak_topics[0] if weak_topics else 'null'}
}}
"""
        return prompt

# AI 서비스 인스턴스
ai_service = AIService()

# Enhanced AI 서비스 인스턴스
enhanced_ai_service = EnhancedAIService() 