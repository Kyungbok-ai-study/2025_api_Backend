# -*- coding: utf-8 -*-
"""
AI 자동 매핑 서비스 (간단 버전)
"""
import asyncio
import logging
from typing import Dict, Any
import google.generativeai as genai

logger = logging.getLogger(__name__)

class AIAutoMapper:
    """AI 자동 매핑 서비스"""
    
    def __init__(self):
        self.gemini_model = None
        self._initialize_ai()
    
    def _initialize_ai(self):
        """AI 모델 초기화"""
        try:
            import os
            from dotenv import load_dotenv
            
            # .env 파일 로드
            load_dotenv()
            
            # 환경변수에서 API 키 읽기
            api_key = os.getenv("GEMINI_API_KEY")
            model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash-latest")
            
            if not api_key:
                logger.warning("❌ GEMINI_API_KEY가 환경변수에 설정되지 않았습니다.")
                self.gemini_model = None
                return
            
            genai.configure(api_key=api_key)
            self.gemini_model = genai.GenerativeModel(model_name)
            logger.info(f"✅ Gemini 모델 초기화 완료: {model_name}")
            
        except Exception as e:
            logger.error(f"❌ AI 모델 초기화 실패: {e}")
            self.gemini_model = None
    
    async def auto_map_difficulty_and_domain(
        self, 
        question_content: str, 
        department: str = "일반학과",
        use_google_search: bool = False
    ) -> Dict[str, Any]:
        """
        자동 난이도/유형 매핑
        """
        logger.info(f"🤖 AI 자동 매핑 시작: {department}")
        
        if not self.gemini_model:
            return {
                'difficulty': '중',
                'domain': '일반',
                'confidence': 0.3,
                'reasoning': 'AI 모델 초기화 실패',
                'method': 'fallback'
            }
        
        try:
            prompt = f"""
다음 문제의 난이도와 분야를 분석해주세요.

학과: {department}
문제: {question_content}

난이도를 하/중/상 중 하나로, 분야를 적절한 이름으로 분류해주세요.

응답 형식:
난이도: 하|중|상
분야: 분야명
근거: 분류 근거
"""
            
            response = await asyncio.to_thread(
                self.gemini_model.generate_content,
                prompt
            )
            
            response_text = response.text
            
            # 응답 파싱
            difficulty = "중"
            domain = "일반"
            
            if "난이도:" in response_text:
                lines = response_text.split('\n')
                for line in lines:
                    if '난이도:' in line:
                        if "하" in line:
                            difficulty = "하"
                        elif "상" in line:
                            difficulty = "상"
                        else:
                            difficulty = "중"
                    elif '분야:' in line:
                        domain_text = line.replace("분야:", "").strip()
                        if domain_text:
                            domain = domain_text
            
            return {
                'difficulty': difficulty,
                'domain': domain,
                'confidence': 0.8,
                'reasoning': f'AI 분석: {response_text[:100]}...',
                'method': 'ai'
            }
            
        except Exception as e:
            logger.error(f"❌ AI 매핑 실패: {e}")
            return {
                'difficulty': '중',
                'domain': '일반',
                'confidence': 0.5,
                'reasoning': f'AI 매핑 실패: {str(e)}',
                'method': 'fallback'
            }

# 전역 인스턴스
ai_auto_mapper = AIAutoMapper()
