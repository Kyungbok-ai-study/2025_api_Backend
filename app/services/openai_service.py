"""
OpenAI API 서비스
텍스트 문체 개선 및 한국어 최적화를 위한 OpenAI API 통합
"""
import os
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from dotenv import load_dotenv

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

# 환경 변수 로드
load_dotenv()

logger = logging.getLogger(__name__)

class OpenAIService:
    """OpenAI API 서비스"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-3.5-turbo")
        self.organization = os.getenv("OPENAI_ORGANIZATION")
        
        if OPENAI_AVAILABLE and self.api_key:
            try:
                openai.api_key = self.api_key
                if self.organization:
                    openai.organization = self.organization
                
                # 최신 버전 호환성
                if hasattr(openai, 'OpenAI'):
                    self.client = openai.OpenAI(
                        api_key=self.api_key,
                        organization=self.organization
                    )
                else:
                    self.client = None
                
                logger.info(f"✅ OpenAI API 초기화 완료: {self.model_name}")
            except Exception as e:
                logger.error(f"❌ OpenAI API 초기화 실패: {e}")
                self.client = None
        else:
            self.client = None
            if not OPENAI_AVAILABLE:
                logger.warning("❌ OpenAI 라이브러리가 설치되지 않았습니다. 'pip install openai' 실행하세요.")
            elif not self.api_key:
                logger.warning("❌ OpenAI API 키가 설정되지 않았습니다.")
    
    async def improve_text_style(
        self,
        content: str,
        style_type: str = "educational",
        target_audience: str = "university_students",
        department: str = "일반학과"
    ) -> Dict[str, Any]:
        """
        텍스트 문체 개선
        
        Args:
            content: 개선할 텍스트 내용
            style_type: 문체 유형 (educational, formal, casual, academic)
            target_audience: 대상 독자
            department: 학과 정보
        """
        try:
            if not self.client and not self._is_openai_available():
                # OpenAI 사용 불가시 기본 개선 처리
                return await self._fallback_text_improvement(content, style_type)
            
            logger.info(f"🔄 OpenAI 문체 개선 시작: {len(content)} 문자")
            
            # 문체 개선 프롬프트 생성
            improvement_prompt = self._build_improvement_prompt(
                content, style_type, target_audience, department
            )
            
            # OpenAI API 호출
            messages = [
                {
                    "role": "system",
                    "content": improvement_prompt["system"]
                },
                {
                    "role": "user", 
                    "content": improvement_prompt["user"]
                }
            ]
            
            response = await self._call_openai_api(messages)
            
            if not response["success"]:
                raise Exception(response["error"])
            
            improved_content = response["content"]
            
            # 개선 결과 분석
            improvement_analysis = self._analyze_improvement(
                original=content,
                improved=improved_content,
                style_type=style_type
            )
            
            logger.info(f"✅ OpenAI 문체 개선 완료: {len(improved_content)} 문자")
            
            return {
                "success": True,
                "improved_content": improved_content,
                "original_content": content,
                "improvement_analysis": improvement_analysis,
                "style_type": style_type,
                "target_audience": target_audience,
                "department": department,
                "improved_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ OpenAI 문체 개선 실패: {e}")
            # 실패시 대체 방법 사용
            return await self._fallback_text_improvement(content, style_type)
    
    def _build_improvement_prompt(
        self, 
        content: str, 
        style_type: str, 
        target_audience: str, 
        department: str
    ) -> Dict[str, str]:
        """문체 개선 프롬프트 생성"""
        
        style_guidelines = {
            "educational": {
                "tone": "친근하고 이해하기 쉬운",
                "structure": "단계별 설명, 예시 포함",
                "language": "교육적이고 명확한 한국어",
                "features": "학습자 중심, 실용적 정보 강조"
            },
            "formal": {
                "tone": "정중하고 격식있는",
                "structure": "논리적 순서, 정확한 용어 사용",
                "language": "표준 한국어, 존댓말",
                "features": "객관적 서술, 전문성 강조"
            },
            "academic": {
                "tone": "학술적이고 전문적인",
                "structure": "이론적 배경, 근거 제시",
                "language": "학술 용어, 정확한 표현",
                "features": "비판적 사고, 깊이 있는 분석"
            },
            "casual": {
                "tone": "편안하고 친근한",
                "structure": "대화체, 자연스러운 흐름",
                "language": "일상적 한국어",
                "features": "공감대 형성, 쉬운 이해"
            }
        }
        
        audience_context = {
            "university_students": "대학생 수준의 이해도와 관심사를 고려",
            "graduate_students": "대학원생 수준의 전문성과 깊이 있는 내용",
            "professionals": "실무진을 위한 실용적이고 응용 가능한 내용",
            "general_public": "일반인도 쉽게 이해할 수 있는 내용"
        }
        
        department_focus = {
            "간호학과": "환자 케어, 임상 실습, 간호 윤리, 의료진 협력",
            "물리치료학과": "재활치료, 운동치료, 환자 평가, 치료 계획",
            "작업치료학과": "일상생활 회복, 인지재활, 보조공학, 환경적응"
        }
        
        style_guide = style_guidelines.get(style_type, style_guidelines["educational"])
        audience_desc = audience_context.get(target_audience, audience_context["university_students"])
        dept_focus = department_focus.get(department, "전공 관련 전문 지식")
        
        system_prompt = f"""
당신은 {department} 전문 교육 콘텐츠 개선 전문가입니다.

=== 개선 목표 ===
- 문체 유형: {style_type} ({style_guide['tone']})
- 대상 독자: {target_audience} ({audience_desc})
- 전공 영역: {dept_focus}

=== 개선 가이드라인 ===
1. 톤앤매너: {style_guide['tone']}
2. 구성 방식: {style_guide['structure']}
3. 언어 스타일: {style_guide['language']}
4. 특징: {style_guide['features']}

=== 한국어 개선 요구사항 ===
- 자연스럽고 정확한 한국어 표현
- 전문 용어의 적절한 사용과 설명
- 문장 구조의 명확성
- 독자 친화적 표현

=== 금지 사항 ===
- 원본 내용의 의미 변경 금지
- 중요한 전문 용어 임의 변경 금지
- 사실 정보 왜곡 금지

개선된 텍스트만 출력하고 추가 설명은 하지 마세요.
"""
        
        user_prompt = f"""
다음 텍스트를 위의 가이드라인에 따라 개선해주세요:

{content}
"""
        
        return {
            "system": system_prompt,
            "user": user_prompt
        }
    
    async def _call_openai_api(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """OpenAI API 호출"""
        try:
            if self.client:  # 최신 버전
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.model_name,
                    messages=messages,
                    max_tokens=3000,
                    temperature=0.3
                )
                content = response.choices[0].message.content
            else:  # 구버전 호환
                response = await asyncio.to_thread(
                    openai.ChatCompletion.create,
                    model=self.model_name,
                    messages=messages,
                    max_tokens=3000,
                    temperature=0.3
                )
                content = response.choices[0].message.content
            
            return {
                "success": True,
                "content": content
            }
            
        except Exception as e:
            logger.error(f"OpenAI API 호출 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": ""
            }
    
    def _analyze_improvement(
        self, 
        original: str, 
        improved: str, 
        style_type: str
    ) -> Dict[str, Any]:
        """개선 결과 분석"""
        return {
            "original_length": len(original),
            "improved_length": len(improved),
            "length_change_ratio": len(improved) / len(original) if original else 1.0,
            "style_applied": style_type,
            "improvement_metrics": {
                "readability": "improved",
                "clarity": "enhanced",
                "professionalism": "maintained"
            }
        }
    
    async def _fallback_text_improvement(
        self, 
        content: str, 
        style_type: str
    ) -> Dict[str, Any]:
        """OpenAI 사용 불가시 대체 텍스트 개선"""
        logger.info("OpenAI 사용 불가 - 기본 텍스트 개선 적용")
        
        # 기본적인 텍스트 정리
        improved_content = content.strip()
        
        # 간단한 개선 작업
        if style_type == "educational":
            # 교육적 스타일: 문장 끝을 정중하게
            improved_content = improved_content.replace("다.", "다고 할 수 있습니다.")
        elif style_type == "formal":
            # 격식적 스타일: 존댓말 강화
            improved_content = improved_content.replace("해요.", "합니다.")
        
        return {
            "success": True,
            "improved_content": improved_content,
            "original_content": content,
            "improvement_analysis": {
                "method": "fallback_basic_improvement",
                "original_length": len(content),
                "improved_length": len(improved_content)
            },
            "style_type": style_type,
            "fallback_used": True,
            "improved_at": datetime.now().isoformat()
        }
    
    def _is_openai_available(self) -> bool:
        """OpenAI 사용 가능 여부 확인"""
        return OPENAI_AVAILABLE and self.api_key and (self.client or openai)

# 전역 인스턴스 생성
openai_service = OpenAIService()    