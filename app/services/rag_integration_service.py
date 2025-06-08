#!/usr/bin/env python3
"""
RAG 통합 서비스 - DeepSeek + Qdrant 기반
문제 승인 시 벡터 DB 저장, AI 해설 생성, RAG 인덱싱 등 통합 처리
"""

import json
import logging
import hashlib
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
import asyncio

from ..models.question import Question
from ..core.config import settings
from .deepseek_service import deepseek_service
from .qdrant_service import qdrant_service

logger = logging.getLogger(__name__)

class RAGIntegrationService:
    """RAG 통합 서비스 - DeepSeek + Qdrant 기반"""
    
    def __init__(self):
        # 데이터 디렉토리 설정
        self.vector_db_path = Path("data/vector_db")
        self.vector_db_path.mkdir(parents=True, exist_ok=True)
        
        self.rag_index_path = Path("data/rag_index")
        self.rag_index_path.mkdir(parents=True, exist_ok=True)
        
        self.training_data_path = Path("data/training_data")
        self.training_data_path.mkdir(parents=True, exist_ok=True)
        
        # DeepSeek과 Qdrant 서비스 사용
        self.deepseek = deepseek_service
        self.vector_db = qdrant_service
        
        logger.info("✅ RAG 통합 서비스 초기화 완료 (DeepSeek + Qdrant)")
    
    async def process_approved_question(
        self, 
        question: Question, 
        approval_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        승인된 문제 통합 처리
        1. Qdrant 벡터 DB 저장
        2. DeepSeek 해설 생성
        3. RAG 인덱싱
        4. 학습 데이터 추가
        """
        try:
            logger.info(f"🎯 승인된 문제 통합 처리 시작: 문제 {question.id}")
            
            processing_results = {
                "question_id": question.id,
                "processing_steps": {},
                "success": True,
                "processing_time": datetime.now().isoformat()
            }
            
            # 1. Qdrant 벡터 DB 저장
            logger.info("📊 1단계: Qdrant 벡터 DB 저장")
            vector_result = await self._store_question_vector(question, approval_metadata)
            processing_results["processing_steps"]["vector_storage"] = vector_result
            
            if not vector_result["success"]:
                logger.warning(f"⚠️ 벡터 저장 실패: {vector_result.get('error')}")
            
            # 2. DeepSeek AI 해설 생성
            logger.info("🤖 2단계: DeepSeek 해설 생성")
            department = approval_metadata.get("department", "간호학과")
            explanation_result = await self._generate_ai_explanation(question, department)
            processing_results["processing_steps"]["ai_explanation"] = explanation_result
            
            # 3. RAG 인덱싱
            logger.info("🔍 3단계: RAG 인덱싱")
            indexing_result = await self._update_rag_index(question, explanation_result)
            processing_results["processing_steps"]["rag_indexing"] = indexing_result
            
            # 4. 학습 데이터 추가
            logger.info("📚 4단계: 학습 데이터 추가")
            training_result = await self._add_to_training_data(question, explanation_result)
            processing_results["processing_steps"]["training_data"] = training_result
            
            # 5. 처리 완료 메타데이터 업데이트
            await self._update_question_metadata(question, processing_results)
            
            logger.info(f"✅ 문제 {question.id} 통합 처리 완료")
            return processing_results
            
        except Exception as e:
            logger.error(f"❌ 문제 통합 처리 실패: {e}")
            return {
                "question_id": question.id,
                "success": False,
                "error": str(e),
                "processing_time": datetime.now().isoformat()
            }
    
    async def _store_question_vector(
        self, 
        question: Question, 
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        1. Qdrant 벡터 DB 저장
        문제와 관련된 정보를 벡터화하여 저장
        """
        try:
            logger.info(f"📊 문제 벡터 저장 시작: 문제 {question.id}")
            
            # 벡터화할 텍스트 준비
            vector_text = f"{question.content}\n정답: {question.correct_answer}"
            if question.choices:
                choices_text = "\n".join([f"{i+1}. {choice}" for i, choice in enumerate(question.choices)])
                vector_text += f"\n선택지:\n{choices_text}"
            
            # 메타데이터 준비
            vector_metadata = {
                "question_id": question.id,
                "type": "approved_question",
                "subject": question.subject_name or "일반",
                "difficulty": question.difficulty.value if question.difficulty else "중",
                "department": metadata.get("department", "일반"),
                "question_type": question.question_type.value if question.question_type else "multiple_choice",
                "approved_at": datetime.now().isoformat(),
                "source": "approved_question"
            }
            
            # Qdrant에 벡터 저장
            result = await self.vector_db.add_question_vector(
                question_id=question.id,
                content=vector_text,
                metadata=vector_metadata
            )
            
            if result["success"]:
                logger.info(f"✅ 문제 {question.id} 벡터 저장 완료")
                return {
                    "success": True,
                    "vector_id": result.get("ids", [f"question_{question.id}"])[0],
                    "storage_method": "Qdrant"
                }
            else:
                logger.error(f"❌ 문제 {question.id} 벡터 저장 실패")
                return {
                    "success": False,
                    "error": result.get("error", "Qdrant 저장 실패")
                }
                
        except Exception as e:
            logger.error(f"❌ 벡터 저장 중 오류: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _generate_ai_explanation(
        self, 
        question: Question, 
        department: str
    ) -> Dict[str, Any]:
        """
        2. DeepSeek AI 해설 생성
        문제와 정답에 대한 상세한 해설을 AI가 생성
        """
        try:
            logger.info(f"🤖 DeepSeek 해설 생성 시작: 문제 {question.id}")
            
            # 학과별 해설 스타일 설정
            explanation_styles = {
                "간호학과": {
                    "focus": "환자 안전, 근거기반 간호, 임상적 적용",
                    "tone": "체계적이고 실무 중심적",
                    "format": "이론 → 임상적용 → 간호중재"
                },
                "물리치료학과": {
                    "focus": "기능 회복, 운동학적 원리, 치료 효과",
                    "tone": "과학적이고 기능 중심적",
                    "format": "해부학적 기초 → 치료 원리 → 실무 적용"
                },
                "작업치료학과": {
                    "focus": "일상생활 참여, 의미있는 활동, 환경 적응",
                    "tone": "통합적이고 활동 중심적",
                    "format": "이론적 배경 → 평가 → 중재 계획"
                }
            }
            
            style = explanation_styles.get(department, explanation_styles["간호학과"])
            
            # DeepSeek 해설 생성 프롬프트
            prompt = self._build_explanation_prompt(question, style, department)
            
            # DeepSeek API 호출
            result = await self.deepseek.generate_explanation(
                question=question.content,
                correct_answer=question.correct_answer,
                options=dict(enumerate(question.choices, 1)) if question.choices else {},
                department=department
            )
            
            if result["success"]:
                confidence = 0.85 + (len(result["explanation"]) / 1000) * 0.1  # 길이 기반 신뢰도
                confidence = min(confidence, 0.95)
                
                logger.info(f"✅ DeepSeek 해설 생성 완료: 문제 {question.id}")
                
                return {
                    "success": True,
                    "explanation": result["explanation"],
                    "confidence": confidence,
                    "department_style": department,
                    "generated_by": "DeepSeek R1 8B",
                    "generated_at": datetime.now().isoformat()
                }
            else:
                logger.error(f"❌ DeepSeek 해설 생성 실패: {result.get('error')}")
                # Fallback 해설 생성
                fallback_explanation = self._generate_fallback_explanation(question, department)
                
                return {
                    "success": True,
                    "explanation": fallback_explanation,
                    "confidence": 0.60,
                    "department_style": department,
                    "generated_by": "Fallback System",
                    "generated_at": datetime.now().isoformat(),
                    "note": "DeepSeek 실패로 인한 대체 해설"
                }
                
        except Exception as e:
            logger.error(f"❌ AI 해설 생성 중 오류: {e}")
            fallback_explanation = self._generate_fallback_explanation(question, department)
            
            return {
                "success": False,
                "explanation": fallback_explanation,
                "confidence": 0.50,
                "error": str(e),
                "generated_by": "Error Recovery System"
            }
    
    def _build_explanation_prompt(
        self, 
        question: Question, 
        style: Dict[str, str], 
        department: str
    ) -> str:
        """DeepSeek 해설 생성용 프롬프트 구성"""
        
        choices_text = ""
        if question.choices:
            choices_text = "\n선택지:\n" + "\n".join([
                f"{i+1}. {choice}" for i, choice in enumerate(question.choices)
            ])
        
        prompt = f"""
다음 {department} 문제에 대한 상세한 해설을 작성해주세요.

문제: {question.content}
{choices_text}
정답: {question.correct_answer}

해설 작성 가이드라인:
- 초점: {style['focus']}
- 톤: {style['tone']}
- 구성: {style['format']}

해설에 포함해야 할 내용:
1. 정답인 이유 (핵심 개념 설명)
2. 오답 분석 (각 선택지별 설명)
3. {department.replace('학과', '')} 실무 관점에서의 적용
4. 관련 이론 및 근거
5. 추가 학습 권장사항

JSON 형식으로 응답해주세요:
{{
    "explanation": "상세한 해설 내용"
}}
"""
        return prompt
    
    def _generate_fallback_explanation(
        self, 
        question: Question, 
        department: str
    ) -> str:
        """대체 해설 생성 (DeepSeek 실패 시)"""
        
        return f"""
[{department} 관점 해설]

**정답 근거:**
{question.correct_answer}번이 정답인 이유는 {question.subject_name or '해당 주제'} 영역에서 핵심적인 개념을 정확히 반영하기 때문입니다.

**문제 분석:**
이 문제는 {question.difficulty.value if question.difficulty else '중급'} 난이도로 분류되며, {department.replace('학과', '')} 전공 지식의 기본적인 이해를 요구합니다.

**실무 적용:**
이 개념은 실제 {department.replace('학과', '')} 현장에서 중요한 의사결정 기준이 되며, 
임상 실무나 관련 업무에서 자주 활용되는 지식입니다.

**학습 포인트:**
- {question.subject_name or '해당 주제'}의 기본 원리 이해
- 상황별 적용 능력 향상
- 근거 기반 판단력 개발

**추가 학습:**
이 문제와 관련된 심화 학습을 위해 {question.subject_name or '관련 분야'}의 
최신 연구와 임상 가이드라인을 참고하시기 바랍니다.

※ 시스템 생성 해설입니다. 더 정확한 해설이 필요한 경우 담당 교수님께 문의하세요.
        """.strip()
    
    async def _update_rag_index(
        self, 
        question: Question, 
        explanation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        3. RAG 인덱싱 업데이트
        생성된 해설과 함께 RAG 검색 인덱스에 추가
        """
        try:
            logger.info(f"🔍 RAG 인덱싱 시작: 문제 {question.id}")
            
            # RAG 인덱스용 텍스트 구성
            rag_text = f"""
문제: {question.content}
정답: {question.correct_answer}
해설: {explanation_result.get('explanation', '해설 없음')}
과목: {question.subject_name or '일반'}
난이도: {question.difficulty.value if question.difficulty else '중'}
"""
            
            # RAG 메타데이터
            rag_metadata = {
                "question_id": question.id,
                "type": "rag_content",
                "has_explanation": bool(explanation_result.get("explanation")),
                "explanation_quality": explanation_result.get("confidence", 0.0),
                "subject": question.subject_name or "일반",
                "difficulty": question.difficulty.value if question.difficulty else "중",
                "indexed_at": datetime.now().isoformat()
            }
            
            # Qdrant에 RAG 전용 벡터 추가
            result = await self.vector_db.add_vectors(
                texts=[rag_text],
                metadatas=[rag_metadata],
                ids=[f"rag_{question.id}"]
            )
            
            if result["success"]:
                logger.info(f"✅ RAG 인덱싱 완료: 문제 {question.id}")
                return {
                    "success": True,
                    "indexed_content_length": len(rag_text),
                    "rag_vector_id": f"rag_{question.id}"
                }
            else:
                logger.error(f"❌ RAG 인덱싱 실패: {result.get('error')}")
                return {
                    "success": False,
                    "error": result.get("error", "RAG 인덱싱 실패")
                }
                
        except Exception as e:
            logger.error(f"❌ RAG 인덱싱 중 오류: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _add_to_training_data(
        self, 
        question: Question, 
        explanation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        4. DeepSeek 학습 데이터 추가
        승인된 문제와 해설을 향후 모델 파인튜닝용 데이터로 저장
        """
        try:
            logger.info(f"📚 학습 데이터 추가 시작: 문제 {question.id}")
            
            # 학습 데이터 포맷 구성
            training_sample = {
                "id": f"question_{question.id}",
                "instruction": "다음 문제에 대한 정답과 해설을 제공하세요.",
                "input": f"문제: {question.content}\n선택지: {question.choices if question.choices else '주관식'}",
                "output": f"정답: {question.correct_answer}\n해설: {explanation_result.get('explanation', '해설 없음')}",
                "metadata": {
                    "subject": question.subject_name,
                    "difficulty": question.difficulty.value if question.difficulty else "중",
                    "question_type": question.question_type.value if question.question_type else "multiple_choice",
                    "approved_at": datetime.now().isoformat(),
                    "explanation_confidence": explanation_result.get("confidence", 0.0)
                }
            }
            
            # 학습 데이터 파일에 저장
            training_file = self.training_data_path / f"approved_questions_{datetime.now().strftime('%Y%m')}.jsonl"
            
            with open(training_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(training_sample, ensure_ascii=False) + "\n")
            
            logger.info(f"✅ 학습 데이터 추가 완료: 문제 {question.id}")
            
            return {
                "success": True,
                "training_file": str(training_file),
                "sample_id": training_sample["id"]
            }
            
        except Exception as e:
            logger.error(f"❌ 학습 데이터 추가 중 오류: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _update_question_metadata(
        self, 
        question: Question, 
        processing_results: Dict[str, Any]
    ) -> None:
        """문제 메타데이터 업데이트"""
        try:
            if not question.question_metadata:
                question.question_metadata = {}
            
            question.question_metadata["rag_processing"] = {
                "processed_at": datetime.now().isoformat(),
                "processing_results": processing_results,
                "system_version": "DeepSeek + Qdrant v1.0"
            }
            
            logger.info(f"✅ 문제 {question.id} 메타데이터 업데이트 완료")
            
        except Exception as e:
            logger.error(f"❌ 메타데이터 업데이트 실패: {e}")
    
    async def search_similar_content(
        self, 
        query: str, 
        content_type: str = "all",
        limit: int = 5
    ) -> Dict[str, Any]:
        """유사 콘텐츠 검색 (Qdrant 기반)"""
        try:
            # 콘텐츠 타입별 필터
            filter_conditions = {}
            if content_type == "questions":
                filter_conditions["type"] = "approved_question"
            elif content_type == "rag":
                filter_conditions["type"] = "rag_content"
            
            # Qdrant에서 유사 콘텐츠 검색
            search_result = await self.vector_db.search_vectors(
                query_text=query,
                limit=limit,
                score_threshold=0.7,
                filter_conditions=filter_conditions if filter_conditions else None
            )
            
            if search_result["success"]:
                logger.info(f"🔍 유사 콘텐츠 검색 완료: {len(search_result['results'])}개 결과")
                return {
                    "success": True,
                    "results": search_result["results"],
                    "query": query,
                    "content_type": content_type,
                    "search_method": "Qdrant Vector Search"
                }
            else:
                return {
                    "success": False,
                    "error": search_result.get("error"),
                    "query": query
                }
                
        except Exception as e:
            logger.error(f"❌ 유사 콘텐츠 검색 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """RAG 통합 시스템 상태 조회"""
        try:
            # Qdrant 상태 확인
            qdrant_status = self.vector_db.get_collection_info()
            
            # DeepSeek 상태 확인 (간단한 테스트)
            deepseek_test = await self.deepseek.chat_completion(
                messages=[{"role": "user", "content": "테스트"}],
                temperature=0.1
            )
            
            status = {
                "system_name": "RAG Integration Service",
                "version": "DeepSeek + Qdrant v1.0",
                "status": "operational",
                "components": {
                    "deepseek": {
                        "status": "connected" if deepseek_test["success"] else "error",
                        "model": "deepseek-r1:8b"
                    },
                    "qdrant": {
                        "status": "connected" if qdrant_status["success"] else "error",
                        "collection": qdrant_status.get("collection_name", "unknown"),
                        "vectors_count": qdrant_status.get("points_count", 0)
                    }
                },
                "data_paths": {
                    "vector_db": str(self.vector_db_path),
                    "rag_index": str(self.rag_index_path),
                    "training_data": str(self.training_data_path)
                },
                "last_checked": datetime.now().isoformat()
            }
            
            return status
            
        except Exception as e:
            logger.error(f"❌ 시스템 상태 조회 실패: {e}")
            return {
                "system_name": "RAG Integration Service",
                "status": "error",
                "error": str(e),
                "last_checked": datetime.now().isoformat()
            }

# 싱글톤 인스턴스
rag_integration_service = RAGIntegrationService() 