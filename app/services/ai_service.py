"""
AI 문제 생성 및 관련 서비스 - Exaone 기반
로컬 Exaone-deep:7.8b 모델 활용 문제 생성 및 분석
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models.question import Question
from ..models.problem_generation import ProblemGeneration 
from ..db.database import get_db
from .exaone_service import exaone_service

logger = logging.getLogger(__name__)

class AIService:
    """AI 문제 생성 및 관련 서비스 - Exaone 기반"""
    
    def __init__(self):
        self.exaone = exaone_service
        self.model_name = "exaone-deep:7.8b"
        
        logger.info("✅ AI 서비스 초기화 완료 (Exaone 기반)")

    async def generate_problem(
        self,
        topic: str,
        difficulty: str = "medium",
        department: str = "일반학과",
        problem_type: str = "multiple_choice",
        user_id: int = None,
        additional_context: str = None
    ) -> Dict[str, Any]:
        """
        AI 문제 생성 (Exaone 활용)
        
        Args:
            topic: 문제 주제
            difficulty: 난이도 (easy, medium, hard)
            department: 학과
            problem_type: 문제 유형
            user_id: 사용자 ID
            additional_context: 추가 컨텍스트
        """
        try:
            logger.info(f"🎯 AI 문제 생성 시작: {topic} ({difficulty})")
            
            # 컨텍스트 프롬프트 구성
            context_prompt = f"""
{additional_context if additional_context else ""}

주제: {topic}
학과: {department}
난이도: {difficulty}
유형: {problem_type}
"""
            
            # Exaone 모델 호출
            generated_content = await self._call_exaone_model(context_prompt)
            
            if not generated_content:
                raise Exception("Exaone 모델에서 응답을 받지 못했습니다.")
            
            # 생성된 내용 파싱
            problem_data = self._parse_generated_content(generated_content)
            
            # 데이터베이스에 저장
            db = next(get_db())
            try:
                problem = ProblemGeneration(
                    user_id=user_id,
                    topic=topic,
                    difficulty=difficulty,
                    department=department,
                    problem_type=problem_type,
                    generated_content=problem_data,
                    raw_ai_response=generated_content,
                    ai_model=self.model_name,
                    generation_timestamp=datetime.utcnow(),
                    status="completed"
                )
                
                db.add(problem)
                db.commit()
                db.refresh(problem)
                
                # 생성된 문제를 Question으로도 저장
                question = Question(
                    year=datetime.now().year,
                    question_number=problem.id,
                    question_content=problem_data.get("question", ""),
                    choices=problem_data.get("options", {}),
                    correct_answer=problem_data.get("correct_answer", ""),
                    explanation=problem_data.get("explanation", ""),
                    difficulty=difficulty,
                    subject_name=topic,
                    department=department,
                    area_name=department,
                    chapter_name=topic,
                    question_metadata={
                        "ai_model": "Exaone Deep 7.8B",
                        "generated_at": datetime.now().isoformat(),
                        "generation_context": context_prompt
                    },
                    created_by=user_id,
                    last_modified_by=user_id,
                    is_generated=True,
                    approval_status="pending",
                    title=f"Exaone 생성 문제 {problem.id}",
                    file_category="AI_GENERATED"
                )
                
                db.add(question)
                db.commit()
                
                result = {
                    "success": True,
                    "problem_id": problem.id,
                    "question_id": question.id,
                    "generated_content": problem_data,
                    "metadata": {
                        "topic": topic,
                        "difficulty": difficulty,
                        "department": department,
                        "problem_type": problem_type,
                        "ai_system": "Exaone + Qdrant RAG"
                    }
                }
                
            finally:
                db.close()
            
            logger.info(f"✅ Exaone 문제 생성 완료: user_id={user_id}, problem_id={problem.id}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ AI 문제 생성 실패: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "metadata": {
                    "topic": topic,
                    "difficulty": difficulty,
                    "department": department,
                    "ai_system": "Exaone + Qdrant RAG"
                }
            }

    async def enhance_existing_problem(
        self,
        problem_id: int,
        enhancement_type: str = "explanation"
    ) -> Dict[str, Any]:
        """
        기존 문제를 Exaone으로 개선
        
        Args:
            problem_id: 문제 ID
            enhancement_type: 개선 유형 (explanation, hint, similar)
        """
        try:
            db = next(get_db())
            problem = db.query(Question).filter(Question.id == problem_id).first()
            
            if not problem:
                return {"success": False, "error": "문제를 찾을 수 없습니다."}
            
            # Exaone으로 해설 생성
            if enhancement_type == "explanation":
                enhancement = await self._generate_explanation(problem)
            # Exaone으로 힌트 생성
            elif enhancement_type == "hint":
                enhancement = await self._generate_hint(problem)
            # Exaone으로 유사 문제 생성
            elif enhancement_type == "similar":
                enhancement = await self._generate_similar_problem(problem)
            else:
                return {"success": False, "error": "지원하지 않는 개선 유형입니다."}
            
            # 메타데이터에 개선 내용 추가
            if not problem.question_metadata:
                problem.question_metadata = {}
            
            problem.question_metadata[f"exaone_{enhancement_type}"] = enhancement
            problem.question_metadata["enhanced_at"] = datetime.now().isoformat()
            
            db.commit()
            
            logger.info(f"✅ Exaone 문제 개선 완료: problem_id={problem_id}, type={enhancement_type}")
            
            return {
                "success": True,
                "problem_id": problem_id,
                "enhancement_type": enhancement_type,
                "enhancement": enhancement
            }
            
        except Exception as e:
            logger.error(f"❌ Exaone 문제 개선 실패: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def batch_generate_problems(
        self,
        topics: List[str],
        difficulty: str = "medium",
        department: str = "일반학과",
        user_id: int = None,
        max_concurrent: int = 3
    ) -> Dict[str, Any]:
        """여러 주제에 대한 일괄 문제 생성"""
        try:
            logger.info(f"🔄 일괄 문제 생성 시작: {len(topics)}개 주제")
            
            # 세마포어를 사용하여 동시 생성 수 제한
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def generate_single_problem(topic: str):
                async with semaphore:
                    return await self.generate_problem(
                        topic=topic,
                        difficulty=difficulty,
                        department=department,
                        user_id=user_id
                    )
            
            # 모든 주제에 대해 병렬 생성
            tasks = [generate_single_problem(topic) for topic in topics]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 결과 정리
            successful = 0
            failed = 0
            detailed_results = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed += 1
                    detailed_results.append({
                        "topic": topics[i],
                        "success": False,
                        "error": str(result)
                    })
                else:
                    if result.get("success", False):
                        successful += 1
                    else:
                        failed += 1
                    detailed_results.append(result)
            
            return {
                "success": True,
                "total_topics": len(topics),
                "successful_generations": successful,
                "failed_generations": failed,
                "results": detailed_results,
                "generated_by": "Exaone Deep 7.8B"
            }
            
        except Exception as e:
            logger.error(f"❌ 일괄 문제 생성 실패: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _call_exaone_model(self, prompt: str) -> str:
        """Exaone 모델 호출"""
        try:
            messages = [{"role": "user", "content": prompt}]
            result = await self.exaone.chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=2048
            )
            
            if result["success"]:
                return result["content"]
            else:
                logger.error(f"❌ Exaone 호출 실패: {result.get('error')}")
                raise Exception(f"Exaone 호출 실패: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"❌ Exaone 모델 호출 오류: {e}")
            raise

    def _parse_generated_content(self, content: str) -> Dict[str, Any]:
        """생성된 내용 파싱"""
        try:
            # JSON 형태로 파싱 시도
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                parsed_data = json.loads(json_match.group())
                return parsed_data
            
            # JSON 파싱 실패시 기본 구조 반환
            return {
                "question": content.split('\n')[0] if content else "생성된 문제",
                "options": {"1": "선택지1", "2": "선택지2", "3": "선택지3", "4": "선택지4"},
                "correct_answer": "1",
                "explanation": "Exaone에서 생성된 문제입니다.",
                "generated_by": "Exaone Deep 7.8B"
            }
            
        except Exception as e:
            logger.warning("⚠️ Exaone 응답 JSON 파싱 실패, 기본 구조 사용")
            return {
                "question": content[:200] if content else "파싱 실패",
                "options": {"1": "선택지1", "2": "선택지2", "3": "선택지3", "4": "선택지4"},
                "correct_answer": "1",
                "explanation": "생성된 내용을 파싱하는데 실패했습니다.",
                "raw_content": content,
                "generated_by": "Exaone Deep 7.8B"
            }

    async def _generate_explanation(self, problem: Question) -> Dict[str, Any]:
        """Exaone으로 문제 해설 생성"""
        try:
            prompt = f"""
다음 문제에 대한 상세한 해설을 작성해주세요.

문제: {problem.question_content}
선택지: {problem.choices}
정답: {problem.correct_answer}
학과: {problem.department}

해설 요구사항:
1. 정답인 이유 명확히 설명
2. 오답 선택지들이 틀린 이유
3. 관련 개념이나 이론 설명
4. 실무 적용 예시 (가능한 경우)

해설만 작성해주세요.
"""
            
            messages = [{"role": "user", "content": prompt}]
            result = await self.exaone.chat_completion(messages, temperature=0.5)
            
            if result["success"]:
                return {
                    "explanation": result["content"],
                    "type": "detailed_explanation",
                    "generated_by": "Exaone Deep 7.8B"
                }
            else:
                return {
                    "explanation": "해설 생성에 실패했습니다.",
                    "type": "error",
                    "generated_by": "Exaone Deep 7.8B"
                }
                
        except Exception as e:
            logger.error(f"해설 생성 오류: {e}")
            return {
                "explanation": "해설 생성 중 오류가 발생했습니다.",
                "error": str(e),
                "generated_by": "Exaone Deep 7.8B"
            }

    async def _generate_hint(self, problem: Question) -> Dict[str, Any]:
        """Exaone으로 문제 힌트 생성"""
        try:
            prompt = f"""
다음 문제를 푸는데 도움이 되는 힌트를 3개 제공해주세요.

문제: {problem.question_content}
학과: {problem.department}

힌트 요구사항:
1. 너무 직접적이지 않으면서도 도움이 되는 수준
2. 단계별로 사고할 수 있도록 안내
3. 관련 개념이나 원리 암시

힌트만 작성해주세요.
"""
            
            messages = [{"role": "user", "content": prompt}]
            result = await self.exaone.chat_completion(messages, temperature=0.6)
            
            return {
                "hints": result["content"] if result["success"] else "힌트 생성 실패",
                "type": "progressive_hints",
                "generated_by": "Exaone Deep 7.8B"
            }
            
        except Exception as e:
            logger.error(f"힌트 생성 오류: {e}")
            return {"hints": "힌트 생성 실패", "error": str(e)}

    async def _generate_similar_problem(self, problem: Question) -> Dict[str, Any]:
        """Exaone으로 유사 문제 생성"""
        try:
            prompt = f"""
다음 문제와 유사한 새로운 문제를 생성해주세요.

원본 문제: {problem.question_content}
학과: {problem.department}
난이도: {problem.difficulty}

요구사항:
1. 같은 개념을 다루지만 다른 상황이나 사례
2. 비슷한 난이도 유지
3. 4개의 선택지와 정답 포함

JSON 형식으로 답변해주세요.
"""
            
            messages = [{"role": "user", "content": prompt}]
            result = await self.exaone.chat_completion(messages, temperature=0.7)
            
            return {
                "similar_problem": result["content"] if result["success"] else "유사 문제 생성 실패",
                "type": "similar_question",
                "generated_by": "Exaone Deep 7.8B"
            }
            
        except Exception as e:
            logger.error(f"유사 문제 생성 오류: {e}")
            return {"similar_problem": "유사 문제 생성 실패", "error": str(e)}


class EnhancedAIService:
    """향상된 AI 분석 및 생성 서비스 - Exaone 기반"""
    
    def __init__(self):
        self.exaone = exaone_service
        
        logger.info("✅ Enhanced AI 서비스 초기화 완료 (Exaone 기반)")

    async def analyze_user_performance(self, user_id: int, db: Session) -> Dict[str, Any]:
        """사용자 성능 분석 (Exaone 기반)"""
        if not self.exaone:
            logger.warning("⚠️ Exaone 서비스가 비활성화됨")
            return {"success": False, "error": "Exaone 서비스 비활성화"}
        
        try:
            # 사용자의 최근 문제 풀이 데이터 수집
            from ..models.student_answer import StudentAnswer
            
            recent_answers = db.query(StudentAnswer).filter(
                StudentAnswer.student_id == user_id
            ).order_by(StudentAnswer.answered_at.desc()).limit(100).all()
            
            if not recent_answers:
                return {
                    "success": True,
                    "analysis": "분석할 데이터가 부족합니다.",
                    "recommendations": ["더 많은 문제를 풀어보세요."]
                }
            
            # 성능 데이터 구성
            performance_data = {
                "total_attempts": len(recent_answers),
                "correct_answers": sum(1 for a in recent_answers if a.is_correct),
                "subjects": {},
                "difficulty_performance": {}
            }
            
            # Exaone으로 분석
            analysis_prompt = f"""
다음 학습자의 성능 데이터를 분석해주세요:

총 시도: {performance_data['total_attempts']}
정답률: {performance_data['correct_answers'] / len(recent_answers) * 100:.1f}%

분석 요청사항:
1. 강점과 약점 분석
2. 학습 패턴 파악
3. 개선 방향 제안
4. 맞춤형 학습 전략

분석 결과를 제공해주세요.
"""
            
            messages = [{"role": "user", "content": analysis_prompt}]
            result = await self.exaone.chat_completion(messages, temperature=0.4)
            
            return {
                "success": True,
                "user_id": user_id,
                "performance_data": performance_data,
                "ai_analysis": result["content"] if result["success"] else "분석 실패",
                "recommendations": ["Exaone 기반 맞춤형 학습을 계속 진행하세요."],
                "analyzed_by": "Exaone Deep 7.8B",
                "analysis_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"성능 분석 실패: {e}")
            return {"success": False, "error": str(e)}

    async def generate_adaptive_questions(
        self, 
        user_performance: Dict[str, Any], 
        topic: str,
        department: str = "일반학과"
    ) -> Dict[str, Any]:
        """적응형 문제 생성 (Exaone 기반)"""
        try:
            # 사용자 성능에 따른 난이도 조정
            accuracy = user_performance.get("accuracy", 0.7)
            
            # Exaone으로 적응형 문제 생성
            adaptive_prompt = f"""
학습자 성능 기반 맞춤형 문제를 생성해주세요.

학습자 정보:
- 정답률: {accuracy * 100:.1f}%
- 주제: {topic}
- 학과: {department}

요구사항:
1. 학습자 수준에 맞는 적절한 난이도
2. 약점 보완을 위한 문제 구성
3. 단계적 학습을 위한 문제 설계

JSON 형식으로 문제를 생성해주세요.
"""
            
            messages = [{"role": "user", "content": adaptive_prompt}]
            result = await self.exaone.chat_completion(messages, temperature=0.6)
            
            if result["success"]:
                question = self._parse_adaptive_question(result["content"])
                question["generated_by"] = "Exaone Deep 7.8B"
                question["adaptation_basis"] = user_performance
                
                return {
                    "success": True,
                    "adaptive_question": question,
                    "adaptation_info": {
                        "user_accuracy": accuracy,
                        "adapted_difficulty": self._calculate_adaptive_difficulty(accuracy),
                        "focus_areas": ["개념 이해", "응용 능력"]
                    }
                }
            
        except Exception as e:
            logger.error(f"적응형 문제 생성 실패: {e}")
        
        return {"success": False, "error": "적응형 문제 생성 실패"}

    def _parse_adaptive_question(self, content: str) -> Dict[str, Any]:
        """적응형 문제 파싱"""
        try:
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {
            "question": content[:200] if content else "적응형 문제",
            "options": {"1": "선택지1", "2": "선택지2", "3": "선택지3", "4": "선택지4"},
            "correct_answer": "1",
            "explanation": "적응형 문제입니다."
        }

    def _calculate_adaptive_difficulty(self, accuracy: float) -> str:
        """정확도 기반 적응형 난이도 계산"""
        if accuracy >= 0.8:
            return "상"
        elif accuracy >= 0.6:
            return "중"
        else:
            return "하"

# 서비스 인스턴스
ai_service = AIService()
enhanced_ai_service = EnhancedAIService() 