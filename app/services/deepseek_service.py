"""
로컬 DeepSeek 서비스
Ollama를 통한 로컬 DeepSeek 모델 실행
OpenAI + Gemini API를 로컬 DeepSeek으로 통합 대체
"""
import os
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import httpx
import base64
from pathlib import Path
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

logger = logging.getLogger(__name__)

class LocalDeepSeekService:
    """로컬 DeepSeek AI 서비스 (Ollama 기반)"""
    
    def __init__(self):
        # Ollama 서버 설정
        self.ollama_host = "http://localhost:11434"
        self.model_name = "deepseek-r1:8b"
        self.embedding_model = "nomic-embed-text"
        
        # HTTP 클라이언트 초기화
        self._client = None
        self._init_client()
        
        logger.info(f"✅ 로컬 DeepSeek 서비스 초기화 완료")
        logger.info(f"🔗 Ollama 서버: {self.ollama_host}")
        logger.info(f"🤖 사용 모델: {self.model_name}")
    
    def _init_client(self):
        """HTTP 클라이언트 초기화"""
        self._client = httpx.AsyncClient(
            base_url=self.ollama_host,
            headers={"Content-Type": "application/json"},
            timeout=120.0  # 로컬 모델은 더 오래 걸릴 수 있음
        )
    
    async def check_model_availability(self) -> bool:
        """모델 사용 가능성 확인"""
        try:
            response = await self._client.get("/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                available_models = [model["name"] for model in models]
                
                if self.model_name in available_models:
                    logger.info(f"✅ 모델 {self.model_name} 사용 가능")
                    return True
                else:
                    logger.warning(f"❌ 모델 {self.model_name} 없음. 사용 가능한 모델: {available_models}")
                    return False
            else:
                logger.error(f"❌ Ollama 서버 연결 실패: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 모델 확인 실패: {e}")
            return False
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        max_tokens: int = 2048,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ollama를 통한 채팅 완성
        OpenAI ChatCompletion과 동일한 인터페이스
        """
        if not self._client:
            raise ValueError("Ollama 클라이언트가 초기화되지 않았습니다.")
        
        try:
            # 메시지를 하나의 프롬프트로 결합 (Ollama 형식)
            prompt = self._messages_to_prompt(messages)
            
            payload = {
                "model": model or self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                }
            }
            
            response = await self._client.post("/api/generate", json=payload)
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "content": result.get("response", ""),
                "model": model or self.model_name,
                "done": result.get("done", True)
            }
            
        except Exception as e:
            logger.error(f"로컬 DeepSeek 채팅 완성 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": ""
            }
    
    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """OpenAI 메시지 형식을 단일 프롬프트로 변환"""
        prompt_parts = []
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"Human: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        prompt_parts.append("Assistant:")
        return "\n\n".join(prompt_parts)
    
    async def create_embeddings(
        self, 
        texts: Union[str, List[str]], 
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ollama를 통한 임베딩 생성
        OpenAI Embedding과 동일한 인터페이스
        """
        if not self._client:
            raise ValueError("Ollama 클라이언트가 초기화되지 않았습니다.")
        
        # 단일 텍스트를 리스트로 변환
        if isinstance(texts, str):
            texts = [texts]
        
        try:
            embeddings = []
            embedding_model = model or self.embedding_model
            
            for text in texts:
                payload = {
                    "model": embedding_model,
                    "prompt": text
                }
                
                response = await self._client.post("/api/embeddings", json=payload)
                response.raise_for_status()
                result = response.json()
                
                if "embedding" in result:
                    embeddings.append(result["embedding"])
                else:
                    logger.warning(f"임베딩 결과 없음: {text[:50]}...")
                    # 기본 임베딩 생성 (768 차원)
                    embeddings.append([0.0] * 768)
            
            return {
                "success": True,
                "embeddings": embeddings,
                "model": embedding_model
            }
            
        except Exception as e:
            logger.error(f"로컬 DeepSeek 임베딩 생성 오류: {e}")
            # 실패시 기본 임베딩 반환
            fallback_embeddings = [[0.0] * 768] * len(texts)
            return {
                "success": False,
                "error": str(e),
                "embeddings": fallback_embeddings
            }
    
    async def parse_document(
        self, 
        file_path: str, 
        content_type: str = "auto",
        max_pages: int = 50
    ) -> Dict[str, Any]:
        """
        문서 파싱 (Gemini 대체)
        텍스트 파일은 직접 처리, 이미지는 OCR 후 처리
        """
        try:
            file_extension = Path(file_path).suffix.lower()
            
            # 텍스트 파일 직접 처리
            if file_extension in ['.txt', '.md', '.json']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
                
                prompt = self._build_text_parse_prompt(content_type, text_content)
                messages = [{"role": "user", "content": prompt}]
                
            elif file_extension in ['.pdf', '.jpg', '.jpeg', '.png']:
                # 이미지/PDF는 OCR 후 텍스트 추출
                extracted_text = await self._extract_text_from_image_pdf(file_path)
                
                if not extracted_text:
                    return {
                        "success": False,
                        "error": "텍스트 추출 실패",
                        "data": []
                    }
                
                prompt = self._build_text_parse_prompt(content_type, extracted_text)
                messages = [{"role": "user", "content": prompt}]
                
            else:
                return {
                    "success": False,
                    "error": f"지원하지 않는 파일 형식: {file_extension}",
                    "data": []
                }
            
            # DeepSeek로 파싱 요청
            result = await self.chat_completion(
                messages=messages,
                temperature=0.1,  # 정확한 파싱을 위해 낮은 temperature
                max_tokens=4096
            )
            
            if result["success"]:
                # JSON 응답 파싱
                parsed_data = self._parse_structured_response(result["content"], content_type)
                return {
                    "success": True,
                    "type": content_type,
                    "data": parsed_data,
                    "source_file": file_path
                }
            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "data": []
                }
                
        except Exception as e:
            logger.error(f"문서 파싱 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": []
            }
    
    async def _extract_text_from_image_pdf(self, file_path: str) -> str:
        """이미지/PDF에서 텍스트 추출 (OCR)"""
        try:
            file_extension = Path(file_path).suffix.lower()
            
            if file_extension == '.pdf':
                # PDF 텍스트 추출
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        text = ""
                        for page in reader.pages:
                            text += page.extract_text() + "\n"
                    return text
                except ImportError:
                    logger.warning("PyPDF2가 설치되지 않음, OCR 시도")
                except:
                    logger.warning("PyPDF2 텍스트 추출 실패, OCR 시도")
            
            # 이미지 OCR (Tesseract 사용)
            try:
                import pytesseract
                from PIL import Image
                
                # PDF를 이미지로 변환 후 OCR
                if file_extension == '.pdf':
                    import pdf2image
                    pages = pdf2image.convert_from_path(file_path)
                    text = ""
                    for page in pages:
                        text += pytesseract.image_to_string(page, lang='kor+eng') + "\n"
                    return text
                else:
                    # 이미지 파일 직접 OCR
                    image = Image.open(file_path)
                    text = pytesseract.image_to_string(image, lang='kor+eng')
                    return text
                    
            except Exception as ocr_error:
                logger.error(f"OCR 처리 실패: {ocr_error}")
                return ""
                
        except Exception as e:
            logger.error(f"텍스트 추출 오류: {e}")
            return ""
    
    def _build_text_parse_prompt(self, content_type: str, text_content: str) -> str:
        """텍스트 파싱 프롬프트 생성"""
        
        base_schema = """
Question 데이터베이스 구조:
- question_number: 문제 번호 (1~22)
- content: 문제 내용
- description: 문제 설명/지문 (문자열 배열)
- options: {"1": "선택지1", "2": "선택지2", ...}
- correct_answer: 정답 (문자열)
- subject: 과목명
- area_name: 영역이름
- difficulty: "하", "중", "상"
- year: 연도

중요: 22번 문제까지만 파싱하세요.
"""
        
        if content_type == "questions":
            return f"""
다음 텍스트에서 시험 문제를 추출해주세요.

{base_schema}

JSON 형식으로 응답해주세요:
{{
    "type": "questions",
    "data": [
        {{
            "question_number": 1,
            "content": "문제 내용",
            "description": ["설명1", "설명2"],
            "options": {{"1": "선택지1", "2": "선택지2", "3": "선택지3", "4": "선택지4"}},
            "subject": "과목명",
            "area_name": "영역명",
            "year": 2024
        }}
    ]
}}

텍스트 내용:
{text_content}
"""
        elif content_type == "answers":
            return f"""
다음 텍스트에서 정답 정보를 추출해주세요.

JSON 형식으로 응답해주세요:
{{
    "type": "answers", 
    "data": [
        {{
            "question_number": 1,
            "correct_answer": "3",
            "year": 2024
        }}
    ]
}}

텍스트 내용:
{text_content}
"""
        else:  # auto
            return f"""
다음 텍스트를 분석하여 시험 문제인지 정답 파일인지 자동 판단하고 적절히 파싱해주세요.

{base_schema}

문제 파일인 경우:
{{
    "type": "questions",
    "data": [문제 데이터 배열]
}}

정답 파일인 경우:
{{
    "type": "answers",
    "data": [정답 데이터 배열]
}}

텍스트 내용:
{text_content}
"""
    
    def _parse_structured_response(self, response_text: str, content_type: str) -> List[Dict[str, Any]]:
        """구조화된 응답 파싱"""
        try:
            # JSON 추출
            text = response_text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                json_parts = text.split("```")
                for part in json_parts:
                    if part.strip().startswith('{') or part.strip().startswith('['):
                        text = part
                        break
            
            # JSON 파싱
            result = json.loads(text.strip())
            
            if isinstance(result, dict) and "data" in result:
                data = result["data"]
            elif isinstance(result, list):
                data = result
            else:
                data = [result]
            
            # 22번 제한 적용
            data = [item for item in data if item.get('question_number', 0) <= 22][:22]
            
            return data
            
        except Exception as e:
            logger.error(f"응답 파싱 오류: {e}")
            logger.error(f"파싱 시도 텍스트: {response_text[:500]}...")
            return []
    
    async def auto_map_difficulty_domain(
        self, 
        question_content: str, 
        department: str = "일반학과"
    ) -> Dict[str, Any]:
        """
        자동 난이도/분야 매핑 (Gemini 대체)
        """
        try:
            prompt = f"""
다음 문제의 난이도와 분야를 분석해주세요.

학과: {department}
문제: {question_content}

난이도 기준:
- 하: 기초개념, 단순암기
- 중: 응용, 이해, 분석
- 상: 종합분석, 고차원사고, 창의적 문제해결

JSON 형식으로 응답해주세요:
{{
    "difficulty": "하|중|상",
    "domain": "분야명",
    "confidence": 0.85,
    "reasoning": "분석 근거"
}}
"""
            
            messages = [{"role": "user", "content": prompt}]
            result = await self.chat_completion(messages, temperature=0.1)
            
            if result["success"]:
                try:
                    # JSON 추출 시도
                    content = result["content"]
                    if "```json" in content:
                        json_text = content.split("```json")[1].split("```")[0]
                    elif "{" in content and "}" in content:
                        start = content.find("{")
                        end = content.rfind("}") + 1
                        json_text = content[start:end]
                    else:
                        json_text = content
                    
                    parsed = json.loads(json_text.strip())
                    return parsed
                except:
                    # JSON 파싱 실패시 기본값
                    return {
                        "difficulty": "중",
                        "domain": "일반",
                        "confidence": 0.6,
                        "reasoning": "자동 분석 결과"
                    }
            else:
                return {
                    "difficulty": "중", 
                    "domain": "일반",
                    "confidence": 0.5,
                    "reasoning": "분석 실패로 기본값 적용"
                }
                
        except Exception as e:
            logger.error(f"자동 매핑 오류: {e}")
            return {
                "difficulty": "중",
                "domain": "일반", 
                "confidence": 0.3,
                "reasoning": f"오류 발생: {str(e)}"
            }
    
    async def generate_explanation(
        self, 
        question: str, 
        correct_answer: str,
        options: Dict[str, str],
        department: str = "일반학과"
    ) -> Dict[str, Any]:
        """
        AI 해설 생성 (Gemini 대체)
        """
        try:
            # 학과별 해설 스타일
            style_guide = {
                "간호학과": "환자 안전, 근거기반 간호, 임상적 적용에 중점",
                "물리치료학과": "기능 회복, 운동학적 원리, 치료 효과에 중점",
                "작업치료학과": "일상생활 참여, 의미있는 활동, 환경 적응에 중점"
            }
            
            style = style_guide.get(department, "체계적이고 논리적인 설명")
            
            prompt = f"""
다음 문제에 대한 상세한 해설을 작성해주세요.

문제: {question}
선택지: {json.dumps(options, ensure_ascii=False)}
정답: {correct_answer}번
학과: {department}

해설 작성 기준:
- {style}
- 정답 근거를 명확히 제시
- 오답 분석 포함
- 실무 적용 관점 추가
- 관련 학습 포인트 제시

JSON 형식으로 응답해주세요:
{{
    "explanation": "상세한 해설 내용",
    "confidence": 0.85,
    "key_points": ["핵심포인트1", "핵심포인트2"],
    "related_topics": ["관련주제1", "관련주제2"]
}}
"""
            
            messages = [{"role": "user", "content": prompt}]
            result = await self.chat_completion(messages, temperature=0.3)
            
            if result["success"]:
                try:
                    # JSON 추출 시도
                    content = result["content"]
                    if "```json" in content:
                        json_text = content.split("```json")[1].split("```")[0]
                    elif "{" in content and "}" in content:
                        start = content.find("{")
                        end = content.rfind("}") + 1
                        json_text = content[start:end]
                    else:
                        # JSON이 없으면 전체를 해설로 사용
                        return {
                            "success": True,
                            "explanation": content,
                            "confidence": 0.75,
                            "key_points": [],
                            "related_topics": []
                        }
                    
                    parsed = json.loads(json_text.strip())
                    return {
                        "success": True,
                        "explanation": parsed.get("explanation", content),
                        "confidence": parsed.get("confidence", 0.8),
                        "key_points": parsed.get("key_points", []),
                        "related_topics": parsed.get("related_topics", [])
                    }
                except:
                    return {
                        "success": True,
                        "explanation": result["content"],
                        "confidence": 0.75,
                        "key_points": [],
                        "related_topics": []
                    }
            else:
                return {
                    "success": False,
                    "error": result["error"]
                }
                
        except Exception as e:
            logger.error(f"해설 생성 오류: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_rag_question(
        self,
        topic: str,
        context: str,
        difficulty: str = "중",
        question_type: str = "multiple_choice"
    ) -> Dict[str, Any]:
        """
        RAG 기반 문제 생성 (OpenAI 대체)
        """
        try:
            prompt = f"""
다음 학습 자료를 바탕으로 {difficulty} 난이도의 {question_type} 문제를 생성해주세요.

학습 자료:
{context}

주제: {topic}
난이도: {difficulty}
문제 유형: {question_type}

요구사항:
- 학습 자료의 내용을 정확히 반영
- 객관식인 경우 4개의 선택지와 정답 포함
- 문제의 질이 높고 교육적 가치가 있을 것

JSON 형식으로 응답해주세요:
{{
    "content": "문제 내용",
    "options": {{"1": "선택지1", "2": "선택지2", "3": "선택지3", "4": "선택지4"}},
    "correct_answer": "정답 번호",
    "explanation": "해설",
    "confidence": 0.85,
    "difficulty": "{difficulty}",
    "subject": "{topic}"
}}
"""
            
            messages = [{"role": "user", "content": prompt}]
            result = await self.chat_completion(messages, temperature=0.4)
            
            if result["success"]:
                try:
                    # JSON 추출 시도
                    content = result["content"]
                    if "```json" in content:
                        json_text = content.split("```json")[1].split("```")[0]
                    elif "{" in content and "}" in content:
                        start = content.find("{")
                        end = content.rfind("}") + 1
                        json_text = content[start:end]
                    else:
                        json_text = content
                    
                    parsed = json.loads(json_text.strip())
                    return {
                        "success": True,
                        "question_data": parsed
                    }
                except:
                    return {
                        "success": False,
                        "error": "응답 파싱 실패"
                    }
            else:
                return {
                    "success": False,
                    "error": result["error"]
                }
                
        except Exception as e:
            logger.error(f"RAG 문제 생성 오류: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def close(self):
        """클라이언트 종료"""
        if self._client:
            await self._client.aclose()

    async def classify_content(
        self,
        content: str,
        department: str = "일반학과",
        subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        DeepSeek을 이용한 컨텐츠 분류
        - 난이도 (쉬움/보통/어려움)
        - 컨텐츠 유형 (이론/실무/사례/문제)  
        - 키워드 추출
        """
        try:
            # 학과별 분류 기준 설정
            classification_criteria = {
                "간호학과": {
                    "focus_areas": ["기본간호학", "성인간호학", "아동간호학", "모성간호학", "정신간호학", "지역사회간호학"],
                    "difficulty_indicators": {
                        "쉬움": ["기본 개념", "정의", "기초 이론", "간단한 절차"],
                        "보통": ["임상 적용", "간호 과정", "환자 사정", "중재 계획"],
                        "어려움": ["복합적 상황", "비판적 사고", "의사결정", "응급상황"]
                    },
                    "content_types": {
                        "이론": ["이론", "개념", "정의", "원리", "지식"],
                        "실무": ["술기", "절차", "방법", "프로토콜", "가이드라인"],
                        "사례": ["사례", "상황", "시나리오", "환자", "케이스"],
                        "문제": ["문제", "질문", "평가", "테스트", "퀴즈"]
                    }
                },
                "물리치료학과": {
                    "focus_areas": ["운동치료", "물리적 인자치료", "신경계물리치료", "근골격계물리치료", "호흡순환계물리치료"],
                    "difficulty_indicators": {
                        "쉬움": ["해부학 기초", "기본 운동", "간단한 측정"],
                        "보통": ["치료 계획", "운동 프로그램", "평가 방법"],
                        "어려움": ["복합 장애", "고급 치료법", "연구 분석"]
                    },
                    "content_types": {
                        "이론": ["해부학", "생리학", "병리학", "운동학"],
                        "실무": ["치료법", "운동법", "측정법", "기기 사용"],
                        "사례": ["환자 사례", "치료 사례", "재활 과정"],
                        "문제": ["평가", "진단", "문제 해결"]
                    }
                },
                "작업치료학과": {
                    "focus_areas": ["일상생활활동", "인지재활", "정신사회작업치료", "감각통합치료", "보조공학"],
                    "difficulty_indicators": {
                        "쉬움": ["기본 활동", "단순 평가", "일반적 개념"],
                        "보통": ["활동 분석", "치료 계획", "평가 도구"],
                        "어려움": ["복합 중재", "환경 수정", "고급 평가"]
                    },
                    "content_types": {
                        "이론": ["이론적 모델", "발달 이론", "학습 이론"],
                        "실무": ["활동 치료", "평가 방법", "중재 기법"],
                        "사례": ["치료 사례", "활동 분석", "중재 결과"],
                        "문제": ["평가 문제", "사례 분석", "의사결정"]
                    }
                }
            }
            
            # 기본 분류 기준 (일반학과용)
            criteria = classification_criteria.get(department, {
                "focus_areas": ["기초", "이론", "실습", "응용"],
                "difficulty_indicators": {
                    "쉬움": ["기본", "기초", "정의", "개념"],
                    "보통": ["응용", "실습", "분석", "적용"],
                    "어려움": ["종합", "평가", "창조", "비판"]
                },
                "content_types": {
                    "이론": ["이론", "개념", "원리"],
                    "실무": ["실습", "방법", "절차"],
                    "사례": ["사례", "예시", "상황"],
                    "문제": ["문제", "질문", "평가"]
                }
            })
            
            # DeepSeek 분류 프롬프트 생성
            classification_prompt = self._build_classification_prompt(
                content, department, subject, criteria
            )
            
            messages = [
                {
                    "role": "system",
                    "content": f"""당신은 {department} 전문 교육 컨텐츠 분류 전문가입니다. 
                    주어진 텍스트를 분석하여 난이도, 컨텐츠 유형, 핵심 키워드를 정확하게 분류해주세요."""
                },
                {
                    "role": "user", 
                    "content": classification_prompt
                }
            ]
            
            # DeepSeek 분류 실행
            response = await self.chat_completion(
                messages=messages,
                temperature=0.3,  # 일관성 있는 분류를 위해 낮은 temperature
                max_tokens=1024
            )
            
            if not response["success"]:
                # 실패시 기본 분류 반환
                return self._get_default_classification(content, department)
            
            # 응답 파싱
            classification_result = self._parse_classification_response(
                response["content"], department
            )
            
            logger.info(f"✅ DeepSeek 컨텐츠 분류 완료: {department}")
            return classification_result
            
        except Exception as e:
            logger.error(f"❌ DeepSeek 컨텐츠 분류 실패: {e}")
            # 오류시 기본 분류 반환
            return self._get_default_classification(content, department)
    
    def _build_classification_prompt(
        self, 
        content: str, 
        department: str, 
        subject: Optional[str],
        criteria: Dict[str, Any]
    ) -> str:
        """분류를 위한 프롬프트 생성"""
        
        focus_areas = ", ".join(criteria.get("focus_areas", []))
        subject_info = f" (과목: {subject})" if subject else ""
        
        prompt = f"""
다음 {department}{subject_info} 교육 컨텐츠를 분석하여 분류해주세요.

=== 분석할 컨텐츠 ===
{content[:2000]}  # 너무 긴 컨텐츠는 잘라서 처리

=== 분류 기준 ===
주요 영역: {focus_areas}

난이도:
- 쉬움: {', '.join(criteria['difficulty_indicators']['쉬움'])}
- 보통: {', '.join(criteria['difficulty_indicators']['보통'])}  
- 어려움: {', '.join(criteria['difficulty_indicators']['어려움'])}

컨텐츠 유형:
- 이론: {', '.join(criteria['content_types']['이론'])}
- 실무: {', '.join(criteria['content_types']['실무'])}
- 사례: {', '.join(criteria['content_types']['사례'])}
- 문제: {', '.join(criteria['content_types']['문제'])}

=== 요청 분류 형식 ===
다음 JSON 형식으로 정확히 분류해주세요:

{{
    "difficulty": "쉬움|보통|어려움",
    "content_type": "이론|실무|사례|문제", 
    "keywords": ["키워드1", "키워드2", "키워드3"],
    "confidence": 0.85,
    "reasoning": "분류 근거 설명"
}}

분석하여 JSON만 출력해주세요.
"""
        return prompt
    
    def _parse_classification_response(
        self, 
        response_text: str, 
        department: str
    ) -> Dict[str, Any]:
        """DeepSeek 분류 응답 파싱"""
        try:
            # JSON 추출 시도
            import re
            
            # JSON 블록 찾기
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                classification_data = json.loads(json_str)
                
                # 결과 검증 및 정규화
                result = {
                    "difficulty": self._normalize_difficulty(
                        classification_data.get("difficulty", "보통")
                    ),
                    "content_type": self._normalize_content_type(
                        classification_data.get("content_type", "이론")
                    ),
                    "keywords": self._normalize_keywords(
                        classification_data.get("keywords", [])
                    ),
                    "confidence": float(classification_data.get("confidence", 0.8)),
                    "reasoning": classification_data.get("reasoning", "자동 분류"),
                    "department": department,
                    "classified_at": datetime.now().isoformat()
                }
                
                return result
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"분류 응답 파싱 실패: {e}")
        
        # 파싱 실패시 기본값 반환
        return self._get_default_classification("", department)
    
    def _normalize_difficulty(self, difficulty: str) -> str:
        """난이도 정규화"""
        difficulty_map = {
            "쉬움": "쉬움", "easy": "쉬움", "1": "쉬움", "기초": "쉬움",
            "보통": "보통", "medium": "보통", "2": "보통", "중간": "보통", "중": "보통",
            "어려움": "어려움", "hard": "어려움", "3": "어려움", "고급": "어려움", "어려운": "어려움"
        }
        
        return difficulty_map.get(difficulty.lower().strip(), "보통")
    
    def _normalize_content_type(self, content_type: str) -> str:
        """컨텐츠 유형 정규화"""
        type_map = {
            "이론": "이론", "theory": "이론", "개념": "이론", "원리": "이론",
            "실무": "실무", "practice": "실무", "실습": "실무", "술기": "실무", "방법": "실무",
            "사례": "사례", "case": "사례", "예시": "사례", "상황": "사례", "시나리오": "사례",
            "문제": "문제", "problem": "문제", "질문": "문제", "평가": "문제", "퀴즈": "문제"
        }
        
        return type_map.get(content_type.lower().strip(), "이론")
    
    def _normalize_keywords(self, keywords: List[str]) -> List[str]:
        """키워드 정규화"""
        if not isinstance(keywords, list):
            return []
        
        # 키워드 정리 (중복 제거, 공백 제거, 길이 제한)
        normalized = []
        for keyword in keywords[:10]:  # 최대 10개
            if isinstance(keyword, str):
                clean_keyword = keyword.strip()
                if clean_keyword and len(clean_keyword) <= 50:
                    normalized.append(clean_keyword)
        
        return list(set(normalized))  # 중복 제거
    
    def _get_default_classification(self, content: str, department: str) -> Dict[str, Any]:
        """기본 분류 결과 반환"""
        # 간단한 키워드 기반 분류
        content_lower = content.lower()
        
        # 기본 난이도 판정
        if any(word in content_lower for word in ["기본", "기초", "정의", "개념"]):
            difficulty = "쉬움"
        elif any(word in content_lower for word in ["고급", "복합", "응급", "비판적"]):
            difficulty = "어려움"
        else:
            difficulty = "보통"
        
        # 기본 유형 판정
        if any(word in content_lower for word in ["사례", "환자", "상황", "케이스"]):
            content_type = "사례"
        elif any(word in content_lower for word in ["방법", "절차", "술기", "실습"]):
            content_type = "실무"
        elif any(word in content_lower for word in ["문제", "질문", "평가"]):
            content_type = "문제"
        else:
            content_type = "이론"
        
        return {
            "difficulty": difficulty,
            "content_type": content_type,
            "keywords": [],
            "confidence": 0.6,
            "reasoning": "기본 규칙 기반 분류",
            "department": department,
            "classified_at": datetime.now().isoformat()
        }

# 싱글톤 인스턴스
deepseek_service = LocalDeepSeekService() 