#!/usr/bin/env python3
"""
AI 기반 문제 분석 시스템
Gemini AI가 직접 문제 내용을 분석하여 난이도, 유형, 분석 근거를 제공
"""

import logging
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
import google.generativeai as genai

logger = logging.getLogger(__name__)

class AIQuestionAnalyzer:
    """AI 기반 문제 분석기"""
    
    def __init__(self, api_key: str = None):
        # Gemini API 설정
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-pro')
        else:
            logger.warning("Gemini API 키가 없어 AI 분석을 사용할 수 없습니다.")
            self.model = None
        
        # 문제 유형 정의 (AI가 사용할 표준 분류)
        self.question_types = {
            "객관식": {
                "code": "multiple_choice",
                "description": "5지선다 또는 다지선다형 문제",
                "examples": ["다음 중 옳은 것은?", "가장 적절한 것은?"]
            },
            "단답형": {
                "code": "short_answer", 
                "description": "간단한 답안을 요구하는 문제",
                "examples": ["무엇인가?", "몇 개인가?", "언제인가?"]
            },
            "논술형": {
                "code": "essay",
                "description": "장문의 서술을 요구하는 문제", 
                "examples": ["설명하시오", "논술하시오", "분석하시오"]
            },
            "계산형": {
                "code": "calculation",
                "description": "수식이나 계산을 요구하는 문제",
                "examples": ["계산하시오", "구하시오", "몇 %인가?"]
            },
            "참/거짓": {
                "code": "true_false",
                "description": "옳고 그름을 판단하는 문제",
                "examples": ["참/거짓", "O/X", "맞으면 O, 틀리면 X"]
            },
            "빈칸채우기": {
                "code": "fill_blank",
                "description": "빈칸을 채우는 문제",
                "examples": ["빈칸에 들어갈", "( )에 알맞은", "_____"]
            },
            "배열/순서": {
                "code": "ordering",
                "description": "순서를 맞추는 문제",
                "examples": ["순서대로 나열", "단계별로", "순서는?"]
            },
            "매칭/연결": {
                "code": "matching",
                "description": "항목을 연결하는 문제",
                "examples": ["연결하시오", "짝지으시오", "매칭하시오"]
            }
        }
        
        # 난이도 기준 (AI가 사용할 평가 기준)
        self.difficulty_criteria = {
            "상": {
                "description": "매우 어려움 - 전문적 지식과 깊은 이해 필요",
                "characteristics": [
                    "복합적 개념 연결 필요",
                    "임상적 판단력 요구",
                    "고차원적 사고 필요",
                    "전문가 수준의 지식 요구"
                ]
            },
            "중": {
                "description": "보통 - 기본적 이해와 적용 능력 필요", 
                "characteristics": [
                    "기본 개념의 응용",
                    "일반적인 전공 지식",
                    "표준적인 절차 이해",
                    "기본적 분석 능력"
                ]
            },
            "하": {
                "description": "쉬움 - 기초적 암기와 이해 수준",
                "characteristics": [
                    "단순 암기 내용",
                    "기초적 개념 이해",
                    "명확한 정답 존재",
                    "직관적으로 이해 가능"
                ]
            }
        }
        
    async def analyze_question(
        self, 
        question_data: Dict[str, Any],
        department: str = "일반",
        subject: str = None
    ) -> Dict[str, Any]:
        """
        AI가 문제를 분석하여 유형, 난이도, 분석 근거 제공
        
        Args:
            question_data: 문제 데이터
            department: 학과 정보
            subject: 과목 정보
            
        Returns:
            AI 분석 결과
        """
        
        if not self.model:
            return self._get_fallback_analysis(question_data)
        
        try:
            # 문제 정보 추출
            question_content = question_data.get('content', '')
            question_options = question_data.get('options', {})
            correct_answer = question_data.get('correct_answer', '')
            question_number = question_data.get('question_number', 0)
            
            # AI 분석 프롬프트 생성
            analysis_prompt = self._create_analysis_prompt(
                question_content, question_options, correct_answer,
                department, subject, question_number
            )
            
            # Gemini AI로 분석 요청
            response = self.model.generate_content([analysis_prompt])
            
            if response and response.text:
                # AI 응답 파싱
                analysis_result = self._parse_ai_response(response.text)
                
                # 분석 결과 검증 및 보완
                validated_result = self._validate_analysis_result(
                    analysis_result, question_data
                )
                
                logger.info(f"문제 {question_number} AI 분석 완료: {validated_result.get('ai_question_type')} / {validated_result.get('ai_difficulty')}")
                
                return validated_result
            else:
                logger.warning(f"문제 {question_number} AI 응답 없음, 폴백 사용")
                return self._get_fallback_analysis(question_data)
                
        except Exception as e:
            logger.error(f"문제 {question_data.get('question_number', 0)} AI 분석 실패: {e}")
            return self._get_fallback_analysis(question_data)
    
    def _create_analysis_prompt(
        self, 
        content: str, 
        options: Dict, 
        answer: str,
        department: str,
        subject: str,
        question_number: int
    ) -> str:
        """AI 분석용 프롬프트 생성"""
        
        # 선택지 문자열 생성
        options_text = ""
        if options and isinstance(options, dict):
            for num, option in options.items():
                options_text += f"{num}. {option}\n"
        
        # 과목별 특성 정보
        subject_context = ""
        if subject:
            subject_context = f"과목: {subject}\n"
        if department != "일반":
            subject_context += f"학과: {department}\n"
        
        prompt = f"""
다음 문제를 전문적으로 분석하여 JSON 형태로 답변해주세요.

{subject_context}
문제 번호: {question_number}

【문제 내용】
{content}

【선택지】
{options_text}

【정답】
{answer}

다음 기준으로 분석해주세요:

1. **문제 유형 분류:**
   - 객관식: 5지선다 또는 다지선다형
   - 단답형: 간단한 답안 서술
   - 논술형: 장문 서술 요구
   - 계산형: 수식이나 계산 필요
   - 참/거짓: O/X 판단
   - 빈칸채우기: 빈칸을 채우는 문제
   - 배열/순서: 순서 맞추기
   - 매칭/연결: 항목 연결

2. **난이도 평가:**
   - 상(매우 어려움): 전문적 지식, 복합적 사고, 임상 판단력 필요
   - 중(보통): 기본 개념 응용, 일반적 전공 지식 필요
   - 하(쉬움): 기초 암기, 단순 개념 이해 수준

3. **분석 근거:** 
   왜 그렇게 판단했는지 구체적 근거 제시

4. **신뢰도:**
   - high: 매우 확실함 (90% 이상)
   - medium: 어느 정도 확실함 (70-90%)
   - low: 불확실함 (70% 미만)

**반드시 다음 JSON 형태로만 응답하세요:**

```json
{{
  "ai_question_type": "객관식",
  "ai_difficulty": "중", 
  "ai_confidence": "high",
  "ai_reasoning": "구체적인 분석 근거를 200자 이내로 설명",
  "ai_analysis_complete": true,
  "content_keywords": ["주요", "키워드", "목록"],
  "cognitive_level": "이해/적용/분석/종합/평가 중 하나"
}}
```

JSON 외의 다른 설명은 하지 마세요.
"""
        
        return prompt
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """AI 응답 파싱"""
        
        try:
            # JSON 블록 추출
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # JSON 블록이 없으면 전체 텍스트에서 JSON 찾기
                json_str = response_text
            
            # JSON 파싱
            parsed_data = json.loads(json_str)
            
            return parsed_data
            
        except json.JSONDecodeError as e:
            logger.warning(f"AI 응답 JSON 파싱 실패: {e}")
            logger.warning(f"원본 응답: {response_text[:200]}...")
            
            # 간단한 텍스트 파싱 시도
            return self._parse_text_response(response_text)
    
    def _parse_text_response(self, response_text: str) -> Dict[str, Any]:
        """텍스트 응답에서 정보 추출"""
        
        # 기본값 설정
        result = {
            "ai_question_type": "객관식",
            "ai_difficulty": "중",
            "ai_confidence": "medium",
            "ai_reasoning": "AI 응답 파싱 중 오류 발생",
            "ai_analysis_complete": False,
            "content_keywords": [],
            "cognitive_level": "이해"
        }
        
        # 간단한 패턴 매칭으로 정보 추출
        try:
            # 문제 유형 추출
            for qtype in self.question_types.keys():
                if qtype in response_text:
                    result["ai_question_type"] = qtype
                    break
            
            # 난이도 추출
            if "상" in response_text and "난이도" in response_text:
                result["ai_difficulty"] = "상"
            elif "하" in response_text and "난이도" in response_text:
                result["ai_difficulty"] = "하"
            else:
                result["ai_difficulty"] = "중"
            
            # 신뢰도 추출
            if "high" in response_text.lower():
                result["ai_confidence"] = "high"
            elif "low" in response_text.lower():
                result["ai_confidence"] = "low"
            else:
                result["ai_confidence"] = "medium"
            
            # 응답 일부를 reasoning으로 사용
            result["ai_reasoning"] = response_text[:150] + "..." if len(response_text) > 150 else response_text
            
        except Exception as e:
            logger.warning(f"텍스트 응답 파싱 실패: {e}")
        
        return result
    
    def _map_to_db_enum(self, ai_type: str) -> str:
        """AI 분석 결과를 데이터베이스 enum 값으로 매핑"""
        type_mapping = {
            "객관식": "multiple_choice",
            "단답형": "short_answer", 
            "논술형": "essay",
            "계산형": "short_answer",  # 계산형은 단답형으로 매핑
            "참/거짓": "true_false",
            "빈칸채우기": "fill_in_blank",
            "배열/순서": "ordering",
            "매칭/연결": "matching"
        }
        return type_mapping.get(ai_type, "multiple_choice")

    def _validate_analysis_result(
        self, 
        analysis_result: Dict[str, Any], 
        question_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """분석 결과 검증 및 보완"""
        
        # 필수 필드 확인 및 기본값 설정
        validated = {
            "ai_question_type": analysis_result.get("ai_question_type", "객관식"),
            "ai_difficulty": analysis_result.get("ai_difficulty", "중"),
            "ai_confidence": analysis_result.get("ai_confidence", "medium"),
            "ai_reasoning": analysis_result.get("ai_reasoning", "AI 분석 결과"),
            "ai_analysis_complete": True,
            "content_keywords": analysis_result.get("content_keywords", []),
            "cognitive_level": analysis_result.get("cognitive_level", "이해"),
            "updated_at": datetime.now().isoformat()
        }
        
        # 문제 유형 검증
        if validated["ai_question_type"] not in self.question_types:
            # 선택지 존재 여부로 기본 판단
            if question_data.get('options'):
                validated["ai_question_type"] = "객관식"
            else:
                validated["ai_question_type"] = "단답형"
        
        # 난이도 검증
        if validated["ai_difficulty"] not in ["상", "중", "하"]:
            validated["ai_difficulty"] = "중"
        
        # 신뢰도 검증
        if validated["ai_confidence"] not in ["high", "medium", "low"]:
            validated["ai_confidence"] = "medium"
        
        # reasoning 길이 제한
        if len(validated["ai_reasoning"]) > 300:
            validated["ai_reasoning"] = validated["ai_reasoning"][:297] + "..."
        
        # 데이터베이스 저장용 enum 값 추가
        validated["db_question_type"] = self._map_to_db_enum(validated["ai_question_type"])
        
        return validated
    
    def _get_fallback_analysis(self, question_data: Dict[str, Any]) -> Dict[str, Any]:
        """AI 분석 실패 시 폴백 분석"""
        
        # 기본적인 규칙 기반 분석
        content = question_data.get('content', '')
        options = question_data.get('options', {})
        
        # 문제 유형 추정
        if options and len(options) >= 4:
            question_type = "객관식"
        elif any(keyword in content for keyword in ["설명하시오", "논술하시오", "분석하시오"]):
            question_type = "논술형" 
        elif any(keyword in content for keyword in ["계산하시오", "구하시오", "%"]):
            question_type = "계산형"
        elif "빈칸" in content or "_" in content:
            question_type = "빈칸채우기"
        else:
            question_type = "단답형"
        
        # 기본 난이도 (중간값)
        difficulty = "중"
        
        # 데이터베이스 enum 값 매핑
        db_type = self._map_to_db_enum(question_type)
        
        return {
            "ai_question_type": question_type,
            "ai_difficulty": difficulty,
            "ai_confidence": "low",
            "ai_reasoning": "AI 분석 불가능으로 기본 규칙 적용",
            "ai_analysis_complete": False,
            "content_keywords": [],
            "cognitive_level": "이해",
            "updated_at": datetime.now().isoformat(),
            "db_question_type": db_type
        }
    
    async def batch_analyze_questions(
        self, 
        questions_data: List[Dict[str, Any]],
        department: str = "일반",
        subject: str = None
    ) -> List[Dict[str, Any]]:
        """여러 문제 일괄 분석"""
        
        logger.info(f"🤖 AI 일괄 분석 시작: {len(questions_data)}개 문제")
        
        analyzed_questions = []
        
        for i, question in enumerate(questions_data):
            logger.info(f"   분석 중... {i+1}/{len(questions_data)}")
            
            # 각 문제별 AI 분석
            ai_analysis = await self.analyze_question(
                question, department, subject
            )
            
            # 원본 데이터에 AI 분석 결과 추가
            enhanced_question = {**question, **ai_analysis}
            analyzed_questions.append(enhanced_question)
        
        logger.info(f"✅ AI 일괄 분석 완료: {len(analyzed_questions)}개 문제")
        
        # 분석 요약 출력
        self._print_analysis_summary(analyzed_questions)
        
        return analyzed_questions
    
    def _print_analysis_summary(self, analyzed_questions: List[Dict[str, Any]]):
        """분석 결과 요약 출력"""
        
        # 문제 유형 통계
        type_counts = {}
        difficulty_counts = {}
        confidence_counts = {}
        
        for q in analyzed_questions:
            # 유형 통계
            qtype = q.get('ai_question_type', 'unknown')
            type_counts[qtype] = type_counts.get(qtype, 0) + 1
            
            # 난이도 통계  
            difficulty = q.get('ai_difficulty', 'unknown')
            difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1
            
            # 신뢰도 통계
            confidence = q.get('ai_confidence', 'unknown')
            confidence_counts[confidence] = confidence_counts.get(confidence, 0) + 1
        
        logger.info("📊 AI 분석 결과 요약:")
        logger.info(f"   문제 유형: {type_counts}")
        logger.info(f"   난이도 분포: {difficulty_counts}")
        logger.info(f"   신뢰도 분포: {confidence_counts}")

# 싱글톤 인스턴스
ai_question_analyzer = None

def get_ai_analyzer(api_key: str = None) -> AIQuestionAnalyzer:
    """AI 분석기 싱글톤 인스턴스 반환"""
    global ai_question_analyzer
    if ai_question_analyzer is None or api_key:
        ai_question_analyzer = AIQuestionAnalyzer(api_key)
    return ai_question_analyzer 