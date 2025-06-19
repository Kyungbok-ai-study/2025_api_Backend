"""
Gemini API 서비스
PDF 문서 파싱 및 컨텐츠 분석을 위한 Gemini API 통합
"""
import os
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import base64
import asyncio
from dotenv import load_dotenv

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

# 환경 변수 로드
load_dotenv()

logger = logging.getLogger(__name__)

class GeminiService:
    """Google Gemini API 서비스"""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")
        
        if GEMINI_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_name)
                logger.info(f"✅ Gemini API 초기화 완료: {self.model_name}")
            except Exception as e:
                logger.error(f"❌ Gemini API 초기화 실패: {e}")
                self.model = None
        else:
            self.model = None
            if not GEMINI_AVAILABLE:
                logger.warning("❌ Gemini API 라이브러리가 설치되지 않았습니다. 'pip install google-generativeai' 실행하세요.")
            elif not self.api_key:
                logger.warning("❌ Gemini API 키가 설정되지 않았습니다.")
    
    async def parse_pdf_document(
        self,
        file_path: str,
        department: str = "일반학과",
        extraction_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """
        Gemini API를 이용한 PDF 문서 파싱
        
        Args:
            file_path: PDF 파일 경로
            department: 학과 정보
            extraction_type: 추출 유형 (comprehensive, summary, questions)
        """
        try:
            if not self.model:
                # Gemini 사용 불가시 대체 파싱 방법 사용
                return await self._fallback_pdf_parsing(file_path, department)
            
            logger.info(f"🔍 Gemini PDF 파싱 시작: {file_path}")
            
            # PDF를 이미지로 변환하여 Gemini에 전송
            pdf_images = await self._convert_pdf_to_images(file_path)
            
            if not pdf_images:
                raise Exception("PDF를 이미지로 변환할 수 없습니다.")
            
            # 학과별 파싱 프롬프트 생성
            parsing_prompt = self._build_parsing_prompt(department, extraction_type)
            
            # Gemini API 호출
            content_parts = [parsing_prompt]
            
            # 이미지들 추가 (최대 10페이지)
            for i, image_data in enumerate(pdf_images[:10]):
                content_parts.append({
                    "mime_type": "image/png",
                    "data": image_data
                })
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                content_parts
            )
            
            if not response or not response.text:
                raise Exception("Gemini API 응답이 비어있습니다.")
            
            # 파싱 결과 처리
            parsing_result = self._process_gemini_response(
                response.text, file_path, department
            )
            
            logger.info(f"✅ Gemini PDF 파싱 완료: {len(parsing_result['content'])} 문자")
            
            return {
                "success": True,
                "content": parsing_result["content"],
                "metadata": parsing_result["metadata"],
                "pages_processed": len(pdf_images),
                "extraction_type": extraction_type,
                "department": department,
                "parsed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Gemini PDF 파싱 실패: {e}")
            # 실패시 대체 방법 사용
            return await self._fallback_pdf_parsing(file_path, department)
    
    def _build_parsing_prompt(self, department: str, extraction_type: str) -> str:
        """학과별 파싱 프롬프트 생성"""
        
        department_context = {
            "간호학과": {
                "focus": "간호학 교육 내용, 환자 케어, 임상 실습, 간호 이론",
                "key_concepts": "간호과정, 환자안전, 감염관리, 약물관리, 건강사정",
                "terminology": "간호진단, 간호중재, 간호평가, 환자교육, 의료진 협력"
            },
            "물리치료학과": {
                "focus": "재활치료, 운동치료, 물리적 인자치료, 기능 회복",
                "key_concepts": "운동학, 해부학, 치료계획, 기능평가, 재활프로그램",
                "terminology": "ROM, MMT, ADL, 보행훈련, 전기치료, 도수치료"
            },
            "작업치료학과": {
                "focus": "일상생활활동, 인지재활, 정신사회 치료, 보조공학",
                "key_concepts": "활동분석, 환경수정, 보조기구, 감각통합, 인지재활",
                "terminology": "ADL, IADL, 인지평가, 작업분석, 환경적응, 보조공학"
            }
        }
        
        context = department_context.get(department, {
            "focus": "일반 교육 내용",
            "key_concepts": "기본 개념, 이론, 실습",
            "terminology": "전문 용어"
        })
        
        if extraction_type == "comprehensive":
            prompt = f"""
당신은 {department} 전문 교육자료 분석 전문가입니다.

다음 PDF 문서를 {department} 관점에서 종합적으로 분석하여 텍스트를 추출해주세요.

=== 분석 초점 ===
- 주요 영역: {context['focus']}
- 핵심 개념: {context['key_concepts']}
- 전문 용어: {context['terminology']}

=== 추출 요구사항 ===
1. 모든 텍스트 내용을 정확히 추출
2. 구조와 계층을 유지 (제목, 본문, 목록 등)
3. 표, 그래프, 다이어그램의 내용도 텍스트로 설명
4. {department} 전문 용어는 정확히 보존
5. 페이지 번호나 헤더/푸터는 제외

=== 출력 형식 ===
제목과 본문을 구분하여 자연스러운 텍스트로 출력해주세요.
중요한 개념이나 용어는 강조 표시해주세요.

텍스트만 출력하고 추가 설명은 하지 마세요.
"""
        
        elif extraction_type == "summary":
            prompt = f"""
당신은 {department} 전문가입니다.

다음 PDF 문서의 핵심 내용을 {department} 관점에서 요약해주세요.

=== 요약 기준 ===
- 주요 개념과 이론
- 실습/임상 관련 내용
- 중요한 절차나 프로토콜
- 핵심 용어 정의

=== 출력 형식 ===
1. 문서 개요
2. 주요 내용 (항목별)
3. 핵심 개념
4. 실무 적용 사항
"""
        
        else:  # questions
            prompt = f"""
당신은 {department} 교육 전문가입니다.

다음 PDF 문서에서 학습 문제로 활용할 수 있는 내용을 추출해주세요.

=== 추출 기준 ===
- 문제 출제 가능한 개념
- 사례 연구 자료
- 평가 가능한 지식
- 실습 관련 내용

모든 텍스트를 추출하되, 문제 출제에 적합한 부분을 중심으로 정리해주세요.
"""
        
        return prompt
    
    async def _convert_pdf_to_images(self, file_path: str) -> List[str]:
        """PDF를 이미지로 변환 (통합 파서 사용)"""
        try:
            from app.services.question_parser import QuestionParser
            parser = QuestionParser()
            return parser._convert_pdf_to_images_unified(file_path, max_pages=10)
        except Exception as e:
            logger.error(f"통합 PDF 이미지 변환 실패: {e}")
            return []
    
    def _process_gemini_response(
        self, 
        response_text: str, 
        file_path: str, 
        department: str
    ) -> Dict[str, Any]:
        """Gemini 응답 처리"""
        
        # 응답 텍스트 정리
        content = response_text.strip()
        
        # 메타데이터 추출
        metadata = {
            "source_file": Path(file_path).name,
            "department": department,
            "content_length": len(content),
            "word_count": len(content.split()),
            "extracted_at": datetime.now().isoformat(),
            "parser": "Gemini API"
        }
        
        # 간단한 구조 분석
        lines = content.split('\n')
        sections = []
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 제목으로 보이는 라인 감지
            if (len(line) < 100 and 
                (line.isupper() or 
                 any(marker in line for marker in ['제', '장', '절', '항']) or
                 line.endswith(':'))):
                
                if current_section:
                    sections.append(current_section)
                
                current_section = {
                    "title": line,
                    "content": [],
                    "type": "section"
                }
            else:
                if current_section:
                    current_section["content"].append(line)
                else:
                    # 첫 번째 섹션
                    current_section = {
                        "title": "본문",
                        "content": [line],
                        "type": "content"
                    }
        
        if current_section:
            sections.append(current_section)
        
        metadata["sections"] = len(sections)
        metadata["structure"] = [{"title": s["title"], "lines": len(s["content"])} for s in sections]
        
        return {
            "content": content,
            "metadata": metadata,
            "sections": sections
        }
    
    async def _fallback_pdf_parsing(
        self, 
        file_path: str, 
        department: str
    ) -> Dict[str, Any]:
        """Gemini 사용 불가시 대체 PDF 파싱 (통합 파서 사용)"""
        try:
            logger.info(f"📄 대체 PDF 파싱 방법 사용: {file_path}")
            
            from app.services.question_parser import QuestionParser
            parser = QuestionParser()
            content = parser._extract_pdf_text_fallback(file_path)
            
            if not content.strip():
                raise Exception("PDF에서 텍스트를 추출할 수 없습니다.")
            
            return {
                "success": True,
                "content": content.strip(),
                "metadata": {
                    "source_file": Path(file_path).name,
                    "department": department,
                    "content_length": len(content),
                    "parser": "통합 파서 (fallback)",
                    "extracted_at": datetime.now().isoformat()
                },
                "extraction_type": "fallback",
                "department": department,
                "parsed_at": datetime.now().isoformat()
            }
                
        except Exception as e:
            logger.error(f"❌ 대체 PDF 파싱 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": "",
                "metadata": {},
                "extraction_type": "failed",
                "department": department,
                "parsed_at": datetime.now().isoformat()
            }
    
    async def analyze_content_structure(
        self,
        content: str,
        department: str
    ) -> Dict[str, Any]:
        """컨텐츠 구조 분석"""
        try:
            if not self.model:
                return self._basic_structure_analysis(content)
            
            prompt = f"""
다음 {department} 교육 컨텐츠의 구조를 분석해주세요.

=== 분석할 컨텐츠 ===
{content[:3000]}...

=== 분석 요구사항 ===
1. 주요 섹션 구분
2. 이론/실습/사례 등 컨텐츠 유형 분류
3. 난이도 수준 평가
4. 핵심 키워드 추출

JSON 형식으로 결과를 제공해주세요:
{{
    "sections": [...],
    "content_types": [...],
    "difficulty_level": "...",
    "keywords": [...],
    "summary": "..."
}}
"""
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            
            # JSON 파싱 시도
            import re
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                # 통합 AI JSON 파서 사용
                from app.services.question_parser import QuestionParser
                result = QuestionParser.parse_ai_json_response(
                    json_match.group(),
                    fallback_data={"error": "JSON 파싱 실패"}
                )
                
                if "error" not in result:
                    return result
                else:
                    return json.loads(json_match.group())
            
        except Exception as e:
            logger.warning(f"Gemini 구조 분석 실패: {e}")
        
        # 기본 분석으로 대체
        return self._basic_structure_analysis(content)
    
    def _basic_structure_analysis(self, content: str) -> Dict[str, Any]:
        """기본 구조 분석"""
        lines = content.split('\n')
        sections = []
        keywords = []
        
        # 간단한 키워드 추출
        import re
        words = re.findall(r'\b[가-힣]{2,}\b', content)
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # 빈도 기준으로 키워드 선정
        keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        keywords = [word for word, freq in keywords if freq > 1]
        
        return {
            "sections": [{"title": "전체 내용", "lines": len(lines)}],
            "content_types": ["이론"],
            "difficulty_level": "보통",
            "keywords": keywords,
            "summary": f"{len(content)} 문자의 교육 컨텐츠"
        }

# 싱글톤 인스턴스
gemini_service = GeminiService() 