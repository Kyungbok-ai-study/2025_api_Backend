"""
로컬 Exaone 서비스
Ollama를 통한 로컬 Exaone 모델 실행
DeepSeek + OpenAI 기능을 통합 대체
"""

import json
import logging
import httpx
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import time
import uuid
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class LocalExaoneService:
    """로컬 Exaone AI 서비스 (Ollama 기반)"""
    
    def __init__(self):
        # Ollama 설정
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model_name = "exaone-deep:7.8b"
        self.embedding_model = "mxbai-embed-large"
        
        # HTTP 클라이언트
        self.client = httpx.AsyncClient(timeout=300.0)
        
        # 캐시 및 통계
        self.conversation_cache = {}
        self.performance_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0,
            "cache_hits": 0
        }
        
        logger.info(f"✅ 로컬 Exaone 서비스 초기화 완료")

    async def check_model_availability(self) -> bool:
        """모델 사용 가능성 확인"""
        try:
            response = await self.client.get(f"{self.ollama_host}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                available_models = [model["name"] for model in models]
                
                if self.model_name in available_models:
                    logger.info(f"✅ Exaone 모델 사용 가능: {self.model_name}")
                    return True
                else:
                    logger.warning(f"❌ Exaone 모델 없음: {self.model_name}")
                    logger.info(f"사용 가능한 모델: {available_models}")
                    return False
            return False
        except Exception as e:
            logger.error(f"모델 확인 실패: {e}")
            return False

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Exaone 채팅 완성 (OpenAI ChatCompletion과 동일한 인터페이스)
        """
        start_time = time.time()
        self.performance_stats["total_requests"] += 1
        
        try:
            # 메시지를 단일 프롬프트로 변환
            prompt = self._convert_messages_to_prompt(messages)
            
            # 캐시 확인
            cache_key = f"{hash(prompt)}_{temperature}_{max_tokens}"
            if cache_key in self.conversation_cache:
                self.performance_stats["cache_hits"] += 1
                logger.info("💾 캐시에서 응답 반환")
                return self.conversation_cache[cache_key]
            
            # Ollama API 호출
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens or 2048,
                    "top_k": 40,
                    "top_p": 0.9
                }
            }
            
            response = await self.client.post(
                f"{self.ollama_host}/api/generate",
                json=payload,
                timeout=300.0
            )
            
            if response.status_code == 200:
                result_data = response.json()
                content = result_data.get("response", "").strip()
                
                # 응답 시간 계산
                response_time = time.time() - start_time
                
                result = {
                    "success": True,
                    "content": content,
                    "model": self.model_name,
                    "response_time": response_time,
                    "tokens_used": len(content.split()),
                    "timestamp": datetime.now().isoformat()
                }
                
                # 캐시에 저장
                self.conversation_cache[cache_key] = result
                
                # 통계 업데이트
                self.performance_stats["successful_requests"] += 1
                self._update_average_response_time(response_time)
                
                logger.info(f"✅ Exaone 채팅 완성 성공 ({response_time:.2f}초)")
                return result
            else:
                raise Exception(f"Ollama API 오류: {response.status_code}")
                
        except Exception as e:
            self.performance_stats["failed_requests"] += 1
            logger.error(f"로컬 Exaone 채팅 완성 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "model": self.model_name,
                "timestamp": datetime.now().isoformat()
            }

    def _convert_messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """OpenAI 메시지 형식을 단일 프롬프트로 변환"""
        prompt_parts = []
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "system":
                prompt_parts.append(f"[시스템 지시사항]\n{content}\n\n")
            elif role == "user":
                prompt_parts.append(f"[사용자 질문]\n{content}\n\n")
            elif role == "assistant":
                prompt_parts.append(f"[이전 답변]\n{content}\n\n")
        
        prompt_parts.append("[AI 답변]")
        return "".join(prompt_parts)

    async def create_embeddings(
        self,
        texts: Union[str, List[str]],
        normalize: bool = True
    ) -> Dict[str, Any]:
        """
        텍스트 임베딩 생성 (OpenAI Embedding과 동일한 인터페이스)
        """
        try:
            if isinstance(texts, str):
                texts = [texts]
            
            embeddings = []
            
            for text in texts:
                payload = {
                    "model": self.embedding_model,
                    "prompt": text
                }
                
                response = await self.client.post(
                    f"{self.ollama_host}/api/embeddings",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    embedding = result.get("embedding", [])
                    
                    if normalize and embedding:
                        # 벡터 정규화
                        import numpy as np
                        embedding = np.array(embedding)
                        norm = np.linalg.norm(embedding)
                        if norm > 0:
                            embedding = embedding / norm
                        embedding = embedding.tolist()
                    
                    embeddings.append(embedding)
                else:
                    logger.error(f"임베딩 생성 실패: {response.status_code}")
                    embeddings.append([])
            
            return {
                "success": True,
                "embeddings": embeddings,
                "model": self.embedding_model,
                "total_tokens": sum(len(text.split()) for text in texts)
            }
            
        except Exception as e:
            logger.error(f"로컬 Exaone 임베딩 생성 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "embeddings": []
            }

    # === AI 문제 생성 기능 ===
    
    async def generate_question(
        self,
        topic: str,
        difficulty: str = "medium",
        department: str = "일반학과",
        question_type: str = "multiple_choice"
    ) -> Dict[str, Any]:
        """AI 문제 생성"""
        prompt = f"""
당신은 {department} 전문 교육자입니다.

다음 조건에 맞는 문제를 생성해주세요:
- 주제: {topic}
- 난이도: {difficulty}
- 문제 유형: {question_type}

출력 형식:
{{
    "question": "문제 내용",
    "options": {{
        "1": "선택지 1",
        "2": "선택지 2", 
        "3": "선택지 3",
        "4": "선택지 4"
    }},
    "correct_answer": "정답 번호",
    "explanation": "해설",
    "difficulty": "{difficulty}",
    "subject": "{topic}",
    "department": "{department}"
}}

JSON 형식으로만 답변해주세요.
"""
        
        messages = [{"role": "user", "content": prompt}]
        result = await self.chat_completion(messages, temperature=0.7)
        
        if result["success"]:
            try:
                content = result["content"]
                # JSON 파싱 시도
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    question_data = json.loads(json_match.group())
                    return {
                        "success": True,
                        "question": question_data,
                        "generated_by": "Exaone Deep 7.8B"
                    }
            except Exception as e:
                logger.warning(f"JSON 파싱 실패: {e}")
        
        return {
            "success": False,
            "error": "문제 생성 실패",
            "raw_response": result.get("content", "")
        }

    # === 난이도 분석 기능 ===
    
    async def analyze_difficulty(
        self, 
        question_content: str, 
        department: str = "일반학과"
    ) -> Dict[str, Any]:
        """문제 난이도 분석"""
        prompt = f"""
당신은 {department} 교육 전문가입니다.

다음 문제의 난이도를 분석해주세요:

{question_content}

다음 기준으로 분석해주세요:
1. 지식 수준 (기초/응용/심화)
2. 사고 과정 복잡도
3. 전문 용어 수준
4. 문제 해결 단계

JSON 형식으로 답변:
{{
    "difficulty_level": "하/중/상",
    "difficulty_score": 1-10점,
    "analysis": {{
        "knowledge_level": "분석 내용",
        "complexity": "분석 내용",
        "terminology": "분석 내용",
        "problem_solving": "분석 내용"
    }},
    "recommendation": "교수자를 위한 추천 사항"
}}
"""
        
        messages = [{"role": "user", "content": prompt}]
        result = await self.chat_completion(messages, temperature=0.3)
        
        if result["success"]:
            try:
                content = result["content"]
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    analysis_data = json.loads(json_match.group())
                    return {
                        "success": True,
                        "analysis": analysis_data,
                        "analyzed_by": "Exaone Deep 7.8B"
                    }
            except Exception as e:
                logger.warning(f"분석 결과 파싱 실패: {e}")
        
        return {
            "success": False,
            "error": "난이도 분석 실패",
            "raw_response": result.get("content", "")
        }

    # === 텍스트 개선 기능 (OpenAI 대체) ===
    
    async def improve_text_style(
        self,
        text: str,
        target_style: str = "educational",
        department: str = "일반학과"
    ) -> Dict[str, Any]:
        """텍스트 문체 개선"""
        prompt = f"""
당신은 {department} 전문 교육 콘텐츠 편집자입니다.

다음 텍스트를 {target_style} 스타일로 개선해주세요:

원본 텍스트:
{text}

개선 요구사항:
1. 자연스러운 한국어 문체
2. 교육적 표현으로 다듬기
3. 전문 용어 적절히 사용
4. 이해하기 쉬운 구조

개선된 텍스트만 출력해주세요.
"""
        
        messages = [{"role": "user", "content": prompt}]
        result = await self.chat_completion(messages, temperature=0.5)
        
        if result["success"]:
            return {
                "success": True,
                "improved_content": result["content"],
                "original_content": text,
                "improved_by": "Exaone Deep 7.8B"
            }
        
        return {
            "success": False,
            "error": "텍스트 개선 실패",
            "original_content": text
        }

    # === 콘텐츠 분류 기능 ===
    
    async def classify_content(
        self,
        content: str,
        classification_type: str = "department"
    ) -> Dict[str, Any]:
        """콘텐츠 분류"""
        if classification_type == "department":
            categories = ["간호학과", "물리치료학과", "작업치료학과", "기타"]
        else:
            categories = ["이론", "실습", "사례연구", "평가"]
        
        prompt = f"""
다음 콘텐츠를 적절한 카테고리로 분류해주세요.

콘텐츠:
{content[:1000]}...

분류 카테고리: {', '.join(categories)}

JSON 형식으로 답변:
{{
    "category": "분류 결과",
    "confidence": 0.0-1.0,
    "reasoning": "분류 근거"
}}
"""
        
        messages = [{"role": "user", "content": prompt}]
        result = await self.chat_completion(messages, temperature=0.3)
        
        if result["success"]:
            try:
                content = result["content"]
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    classification_data = json.loads(json_match.group())
                    return {
                        "success": True,
                        "classification": classification_data,
                        "classified_by": "Exaone Deep 7.8B"
                    }
            except Exception as e:
                logger.warning(f"분류 결과 파싱 실패: {e}")
        
        return {
            "success": False,
            "error": "콘텐츠 분류 실패"
        }

    # === 학습 및 지식 테스트 기능 ===
    
    async def learn_from_content(
        self,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """콘텐츠 학습"""
        # 실제로는 벡터 DB에 저장하거나 파인튜닝 데이터로 활용
        try:
            # 콘텐츠 요약 생성
            summary_prompt = f"""
다음 교육 콘텐츠의 핵심 내용을 요약해주세요:

{content[:2000]}...

3-5줄로 요약해주세요.
"""
            
            messages = [{"role": "user", "content": summary_prompt}]
            result = await self.chat_completion(messages, temperature=0.3)
            
            if result["success"]:
                # 학습 기록 저장 (실제 구현에서는 DB나 파일로)
                learning_record = {
                    "content_id": str(uuid.uuid4()),
                    "summary": result["content"],
                    "original_length": len(content),
                    "learned_at": datetime.now().isoformat(),
                    "metadata": metadata or {}
                }
                
                return {
                    "success": True,
                    "learning_record": learning_record,
                    "message": "콘텐츠 학습 완료"
                }
        
        except Exception as e:
            logger.error(f"콘텐츠 학습 실패: {e}")
        
        return {
            "success": False,
            "error": "콘텐츠 학습 실패"
        }

    async def test_knowledge(
        self,
        test_question: str,
        context: str = ""
    ) -> Dict[str, Any]:
        """학습된 지식 테스트"""
        prompt = f"""
당신은 교육 전문 AI입니다.

{f"참고 맥락: {context}" if context else ""}

질문: {test_question}

학습한 내용을 바탕으로 정확하고 교육적인 답변을 제공해주세요.
"""
        
        messages = [{"role": "user", "content": prompt}]
        result = await self.chat_completion(messages, temperature=0.4)
        
        if result["success"]:
            return {
                "success": True,
                "answer": result["content"],
                "test_question": test_question,
                "answered_by": "Exaone Deep 7.8B"
            }
        
        return {
            "success": False,
            "error": "지식 테스트 실패"
        }

    # === 유틸리티 메서드 ===
    
    def _update_average_response_time(self, response_time: float):
        """평균 응답 시간 업데이트"""
        total_requests = self.performance_stats["successful_requests"]
        current_avg = self.performance_stats["average_response_time"]
        
        # 이동 평균 계산
        new_avg = ((current_avg * (total_requests - 1)) + response_time) / total_requests
        self.performance_stats["average_response_time"] = new_avg

    async def get_performance_stats(self) -> Dict[str, Any]:
        """성능 통계 조회"""
        return {
            **self.performance_stats,
            "cache_size": len(self.conversation_cache),
            "model_info": {
                "model_name": self.model_name,
                "embedding_model": self.embedding_model,
                "ollama_host": self.ollama_host
            },
            "timestamp": datetime.now().isoformat()
        }

    async def clear_cache(self):
        """캐시 정리"""
        self.conversation_cache.clear()
        logger.info("💾 Exaone 서비스 캐시 정리 완료")

    async def health_check(self) -> Dict[str, Any]:
        """서비스 상태 확인"""
        try:
            # 간단한 테스트 요청
            test_messages = [{"role": "user", "content": "안녕하세요"}]
            result = await self.chat_completion(test_messages, temperature=0.1)
            
            return {
                "status": "healthy" if result["success"] else "unhealthy",
                "model_available": await self.check_model_availability(),
                "response_test": result["success"],
                "performance_stats": await self.get_performance_stats(),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# 싱글톤 인스턴스
exaone_service = LocalExaoneService() 