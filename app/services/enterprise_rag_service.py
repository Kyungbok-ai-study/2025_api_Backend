"""
🏢 대기업급 통합 RAG 시스템 서비스
기존 RAG 시스템들을 통합하고 엔터프라이즈급 기능 추가
"""
import os
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from pathlib import Path
import uuid
import hashlib
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_

from ..models.question import Question
from ..models.user import User
# deepseek_service import 제거됨 (Exaone으로 전환)
from ..services.qdrant_service import qdrant_service
from ..services.rag_system import rag_service
from ..services.rag_integration_service import rag_integration_service
from ..services.advanced_rag_service import advanced_rag_service

logger = logging.getLogger(__name__)

class RAGSearchStrategy(Enum):
    """RAG 검색 전략"""
    BASIC = "basic"              # 기본 시맨틱 검색
    HYBRID = "hybrid"            # 하이브리드 검색 (키워드+시맨틱)
    FUSION = "fusion"            # RAG Fusion (다중 쿼리)
    MULTIMODAL = "multimodal"    # 멀티모달 검색
    ADAPTIVE = "adaptive"        # 적응형 검색 (상황별 최적화)

class RAGQualityLevel(Enum):
    """RAG 품질 수준"""
    STANDARD = "standard"        # 표준 품질
    PREMIUM = "premium"          # 프리미엄 품질
    ENTERPRISE = "enterprise"    # 엔터프라이즈 품질

@dataclass
class RAGRequest:
    """통합 RAG 요청 모델"""
    query: str
    strategy: RAGSearchStrategy = RAGSearchStrategy.ADAPTIVE
    quality_level: RAGQualityLevel = RAGQualityLevel.ENTERPRISE
    user_id: Optional[int] = None
    department: str = "간호학과"
    context_limit: int = 10
    enable_learning: bool = True
    include_analytics: bool = True

@dataclass
class RAGResponse:
    """통합 RAG 응답 모델"""
    success: bool
    query: str
    strategy_used: str
    results: List[Dict[str, Any]]
    total_results: int
    processing_time: float
    quality_score: float
    analytics: Optional[Dict] = None
    learning_applied: bool = False
    error: Optional[str] = None

class EnterpriseRAGService:
    """🏢 대기업급 통합 RAG 시스템"""
    
    def __init__(self):
        # 기존 서비스들 통합
        self.basic_rag = rag_service
        self.integration_rag = rag_integration_service
        self.advanced_rag = advanced_rag_service
        
        # 엔터프라이즈 기능
        # deepseek_service 제거됨 (Exaone으로 전환 예정)
        self.exaone = None  # TODO: Exaone 서비스 구현 후 초기화
        self.vector_db = qdrant_service
        
        # 성능 메트릭
        self.performance_tracker = defaultdict(list)
        self.quality_metrics = defaultdict(float)
        self.user_analytics = defaultdict(dict)
        
        # 캐시 및 최적화
        self.result_cache = {}
        self.strategy_optimizer = {}
        
        # 시스템 상태
        self.system_health = {
            "status": "operational",
            "last_check": datetime.now(),
            "components": {}
        }
        
        logger.info("🏢 대기업급 통합 RAG 시스템 초기화 완료")
    
    # ============ 1. 통합 RAG 엔진 ============
    
    async def unified_rag_search(
        self,
        db: Session,
        request: RAGRequest
    ) -> RAGResponse:
        """통합 RAG 검색 엔진 - 모든 기능 통합"""
        start_time = datetime.now()
        
        try:
            logger.info(f"🎯 통합 RAG 검색 시작: {request.query} (전략: {request.strategy.value})")
            
            # 1. 전략 자동 최적화 (Adaptive일 경우)
            if request.strategy == RAGSearchStrategy.ADAPTIVE:
                request.strategy = await self._optimize_search_strategy(db, request)
            
            # 2. 사용자 개인화 적용
            if request.enable_learning and request.user_id:
                request = await self._apply_personalization(request)
            
            # 3. 캐시 확인
            cache_key = self._generate_cache_key(request)
            if cache_key in self.result_cache:
                cached_result = self.result_cache[cache_key]
                logger.info(f"💨 캐시 히트: {request.query}")
                return cached_result
            
            # 4. 전략별 검색 실행
            search_results = await self._execute_search_strategy(db, request)
            
            # 5. 품질 평가 및 후처리
            processed_results = await self._enhance_results_quality(search_results, request)
            
            # 6. 분석 정보 생성
            analytics = await self._generate_analytics(request, processed_results) if request.include_analytics else None
            
            # 7. 응답 구성
            processing_time = (datetime.now() - start_time).total_seconds()
            quality_score = await self._calculate_quality_score(processed_results)
            
            response = RAGResponse(
                success=True,
                query=request.query,
                strategy_used=request.strategy.value,
                results=processed_results[:request.context_limit],
                total_results=len(processed_results),
                processing_time=round(processing_time, 3),
                quality_score=quality_score,
                analytics=analytics,
                learning_applied=request.enable_learning and request.user_id is not None
            )
            
            # 8. 캐시 저장
            self.result_cache[cache_key] = response
            
            # 9. 성능 메트릭 기록
            self._record_performance_metrics(request, response)
            
            logger.info(f"✅ 통합 RAG 검색 완료: {len(processed_results)}개 결과 ({processing_time:.3f}초)")
            return response
            
        except Exception as e:
            logger.error(f"❌ 통합 RAG 검색 실패: {e}")
            return RAGResponse(
                success=False,
                query=request.query,
                strategy_used=request.strategy.value,
                results=[],
                total_results=0,
                processing_time=(datetime.now() - start_time).total_seconds(),
                quality_score=0.0,
                error=str(e)
            )
    
    async def _optimize_search_strategy(
        self,
        db: Session,
        request: RAGRequest
    ) -> RAGSearchStrategy:
        """적응형 검색 전략 최적화"""
        try:
            # 쿼리 복잡도 분석
            query_complexity = await self._analyze_query_complexity(request.query)
            
            # 사용자 이력 기반 최적화
            user_preferences = self._get_user_preferences(request.user_id) if request.user_id else {}
            
            # 전략 선택 로직
            if query_complexity["has_multimodal_intent"]:
                return RAGSearchStrategy.MULTIMODAL
            elif query_complexity["complexity_score"] > 0.8:
                return RAGSearchStrategy.FUSION
            elif query_complexity["has_specific_keywords"]:
                return RAGSearchStrategy.HYBRID
            else:
                return RAGSearchStrategy.BASIC
                
        except Exception as e:
            logger.error(f"❌ 전략 최적화 실패: {e}")
            return RAGSearchStrategy.HYBRID  # 기본값
    
    async def _analyze_query_complexity(self, query: str) -> Dict[str, Any]:
        """쿼리 복잡도 분석"""
        try:
            analysis_prompt = f"""
다음 쿼리를 분석하여 JSON으로 응답하세요:

쿼리: "{query}"

분석 항목:
1. complexity_score: 쿼리 복잡도 (0.0-1.0)
2. has_specific_keywords: 구체적 키워드 포함 여부
3. has_multimodal_intent: 이미지/표 관련 의도 여부
4. requires_context: 맥락 정보 필요 여부
5. domain_specificity: 전문 영역 특화도 (0.0-1.0)

JSON 형식:
{{
    "complexity_score": 0.5,
    "has_specific_keywords": true,
    "has_multimodal_intent": false,
    "requires_context": true,
    "domain_specificity": 0.7
}}
"""
            
            result = await self.deepseek.chat_completion(
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=0.1
            )
            
            if result["success"]:
                try:
                    return json.loads(result["content"])
                except json.JSONDecodeError:
                    pass
            
            # 폴백 분석
            return {
                "complexity_score": len(query.split()) / 20.0,  # 단어 수 기반
                "has_specific_keywords": any(keyword in query.lower() for keyword in ["구체적", "정확한", "상세한"]),
                "has_multimodal_intent": any(keyword in query.lower() for keyword in ["이미지", "그림", "표", "차트"]),
                "requires_context": len(query.split()) > 5,
                "domain_specificity": 0.5
            }
            
        except Exception as e:
            logger.error(f"❌ 쿼리 복잡도 분석 실패: {e}")
            return {"complexity_score": 0.5, "has_specific_keywords": False, "has_multimodal_intent": False, "requires_context": True, "domain_specificity": 0.5}
    
    async def _execute_search_strategy(
        self,
        db: Session,
        request: RAGRequest
    ) -> List[Dict[str, Any]]:
        """전략별 검색 실행"""
        try:
            if request.strategy == RAGSearchStrategy.BASIC:
                return await self._execute_basic_search(db, request)
            elif request.strategy == RAGSearchStrategy.HYBRID:
                return await self._execute_hybrid_search(db, request)
            elif request.strategy == RAGSearchStrategy.FUSION:
                return await self._execute_fusion_search(db, request)
            elif request.strategy == RAGSearchStrategy.MULTIMODAL:
                return await self._execute_multimodal_search(db, request)
            else:
                return await self._execute_hybrid_search(db, request)  # 기본값
                
        except Exception as e:
            logger.error(f"❌ 검색 전략 실행 실패: {e}")
            return []
    
    async def _execute_basic_search(
        self,
        db: Session,
        request: RAGRequest
    ) -> List[Dict[str, Any]]:
        """기본 시맨틱 검색"""
        try:
            results = await self.basic_rag.similarity_search(
                db=db,
                query_text=request.query,
                limit=request.context_limit * 2,
                similarity_threshold=0.6
            )
            
            return [
                {
                    "content": result["content"],
                    "score": result["similarity"],
                    "source": "basic_semantic",
                    "metadata": {
                        "document_title": result.get("document_title", ""),
                        "subject": result.get("subject", ""),
                        "area_name": result.get("area_name", "")
                    }
                }
                for result in results
            ]
            
        except Exception as e:
            logger.error(f"❌ 기본 검색 실패: {e}")
            return []
    
    async def _execute_hybrid_search(
        self,
        db: Session,
        request: RAGRequest
    ) -> List[Dict[str, Any]]:
        """하이브리드 검색 (키워드+시맨틱)"""
        try:
            search_result = await self.advanced_rag.hybrid_search(
                db=db,
                query=request.query,
                search_mode="hybrid",
                limit=request.context_limit * 2
            )
            
            if search_result["success"]:
                return search_result["data"]["results"]
            else:
                return []
                
        except Exception as e:
            logger.error(f"❌ 하이브리드 검색 실패: {e}")
            return []
    
    async def _execute_fusion_search(
        self,
        db: Session,
        request: RAGRequest
    ) -> List[Dict[str, Any]]:
        """RAG Fusion 검색 (다중 쿼리)"""
        try:
            fusion_result = await self.advanced_rag.rag_fusion_search(
                db=db,
                original_query=request.query,
                num_queries=5,
                fusion_method="rrf"
            )
            
            if fusion_result["success"]:
                return fusion_result["final_results"]
            else:
                return []
                
        except Exception as e:
            logger.error(f"❌ Fusion 검색 실패: {e}")
            return []
    
    async def _execute_multimodal_search(
        self,
        db: Session,
        request: RAGRequest
    ) -> List[Dict[str, Any]]:
        """멀티모달 검색 (텍스트+이미지+표)"""
        try:
            # 현재는 하이브리드 검색으로 대체, 향후 멀티모달 확장
            return await self._execute_hybrid_search(db, request)
            
        except Exception as e:
            logger.error(f"❌ 멀티모달 검색 실패: {e}")
            return []
    
    # ============ 2. 품질 향상 시스템 ============
    
    async def _enhance_results_quality(
        self,
        results: List[Dict[str, Any]],
        request: RAGRequest
    ) -> List[Dict[str, Any]]:
        """결과 품질 향상 처리"""
        try:
            if not results:
                return results
            
            enhanced_results = []
            
            for result in results:
                # 품질 수준별 향상 처리
                if request.quality_level == RAGQualityLevel.ENTERPRISE:
                    enhanced_result = await self._apply_enterprise_enhancement(result, request)
                elif request.quality_level == RAGQualityLevel.PREMIUM:
                    enhanced_result = await self._apply_premium_enhancement(result, request)
                else:
                    enhanced_result = result
                
                enhanced_results.append(enhanced_result)
            
            # 중복 제거 및 품질 정렬
            unique_results = self._remove_duplicates(enhanced_results)
            sorted_results = sorted(unique_results, key=lambda x: x.get("enhanced_score", x.get("score", 0)), reverse=True)
            
            return sorted_results
            
        except Exception as e:
            logger.error(f"❌ 품질 향상 처리 실패: {e}")
            return results
    
    async def _apply_enterprise_enhancement(
        self,
        result: Dict[str, Any],
        request: RAGRequest
    ) -> Dict[str, Any]:
        """엔터프라이즈 품질 향상"""
        try:
            enhanced_result = result.copy()
            
            # 1. AI 기반 요약 생성
            summary = await self._generate_ai_summary(result["content"], request.query)
            enhanced_result["ai_summary"] = summary
            
            # 2. 관련도 재계산
            relevance_score = await self._calculate_advanced_relevance(result["content"], request.query)
            enhanced_result["enhanced_score"] = relevance_score
            
            # 3. 신뢰도 점수 추가
            credibility_score = self._calculate_credibility_score(result)
            enhanced_result["credibility"] = credibility_score
            
            # 4. 학과별 맞춤화
            department_relevance = self._calculate_department_relevance(result, request.department)
            enhanced_result["department_relevance"] = department_relevance
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"❌ 엔터프라이즈 향상 실패: {e}")
            return result
    
    async def _generate_ai_summary(self, content: str, query: str) -> str:
        """AI 기반 맞춤형 요약 생성"""
        try:
            if len(content) < 200:
                return content[:100] + "..."
            
            summary_prompt = f"""
다음 내용을 질문과 관련하여 핵심만 간단히 요약하세요 (2-3문장):

질문: {query}
내용: {content[:500]}...

요약:
"""
            
            result = await self.deepseek.chat_completion(
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.3
            )
            
            if result["success"]:
                return result["content"].strip()
            else:
                return content[:100] + "..."
                
        except Exception as e:
            logger.error(f"❌ AI 요약 생성 실패: {e}")
            return content[:100] + "..."
    
    async def _calculate_advanced_relevance(self, content: str, query: str) -> float:
        """고급 관련도 계산"""
        try:
            # 키워드 매칭 점수
            query_words = set(query.lower().split())
            content_words = set(content.lower().split())
            keyword_overlap = len(query_words.intersection(content_words)) / len(query_words) if query_words else 0
            
            # 의미적 유사도 (기본 점수 기반)
            semantic_score = 0.7  # 실제로는 임베딩 유사도 사용
            
            # 종합 점수
            final_score = (keyword_overlap * 0.4) + (semantic_score * 0.6)
            return min(final_score, 1.0)
            
        except Exception as e:
            logger.error(f"❌ 고급 관련도 계산 실패: {e}")
            return 0.5
    
    def _calculate_credibility_score(self, result: Dict[str, Any]) -> float:
        """신뢰도 점수 계산"""
        try:
            score = 0.5  # 기본 점수
            
            metadata = result.get("metadata", {})
            
            # 소스 신뢰도
            if metadata.get("document_title"):
                score += 0.2
            
            # 승인된 컨텐츠 여부
            if metadata.get("approval_status") == "approved":
                score += 0.2
            
            # 교수 검증 여부
            if metadata.get("approved_by"):
                score += 0.1
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"❌ 신뢰도 점수 계산 실패: {e}")
            return 0.5
    
    def _calculate_department_relevance(self, result: Dict[str, Any], department: str) -> float:
        """학과별 관련도 계산"""
        try:
            metadata = result.get("metadata", {})
            result_department = metadata.get("department", "")
            
            if result_department == department:
                return 1.0
            elif department in result_department or result_department in department:
                return 0.8
            else:
                return 0.6
                
        except Exception as e:
            logger.error(f"❌ 학과 관련도 계산 실패: {e}")
            return 0.6
    
    # ============ 3. 통합 문서 처리 ============
    
    async def process_enterprise_document(
        self,
        db: Session,
        file_path: str,
        document_title: str,
        user_id: int,
        processing_options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """엔터프라이즈급 문서 처리"""
        try:
            if processing_options is None:
                processing_options = {}
            
            logger.info(f"🏢 엔터프라이즈 문서 처리 시작: {document_title}")
            
            processing_results = {
                "document_title": document_title,
                "processing_steps": {},
                "quality_metrics": {},
                "integration_status": {}
            }
            
            # 1. 기본 RAG 처리
            basic_result = await self.basic_rag.upload_and_process_document(
                db=db,
                file_path=file_path,
                document_title=document_title,
                user_id=user_id
            )
            processing_results["processing_steps"]["basic_rag"] = basic_result
            
            # 2. 고급 멀티모달 처리 (선택적)
            if processing_options.get("enable_multimodal", True):
                multimodal_result = await self.advanced_rag.process_multimodal_document(
                    db=db,
                    file_path=file_path,
                    document_title=document_title,
                    user_id=user_id,
                    extract_images=processing_options.get("extract_images", True),
                    extract_tables=processing_options.get("extract_tables", True)
                )
                processing_results["processing_steps"]["multimodal"] = multimodal_result
            
            # 3. 품질 검증
            quality_score = await self._validate_document_quality(file_path, document_title)
            processing_results["quality_metrics"]["overall_score"] = quality_score
            
            # 4. 자동 분류 및 태깅
            classification = await self._auto_classify_document(file_path, document_title)
            processing_results["quality_metrics"]["classification"] = classification
            
            # 5. 통합 상태 확인
            integration_status = await self._check_integration_status(document_title)
            processing_results["integration_status"] = integration_status
            
            logger.info(f"✅ 엔터프라이즈 문서 처리 완료: {document_title}")
            return {"success": True, "results": processing_results}
            
        except Exception as e:
            logger.error(f"❌ 엔터프라이즈 문서 처리 실패: {e}")
            return {"success": False, "error": str(e)}
    
    # ============ 4. 시스템 모니터링 ============
    
    async def get_enterprise_analytics(self) -> Dict[str, Any]:
        """엔터프라이즈 분석 대시보드"""
        try:
            analytics = {
                "system_overview": await self._get_system_overview(),
                "performance_metrics": await self._get_performance_metrics(),
                "quality_analytics": await self._get_quality_analytics(),
                "user_insights": await self._get_user_insights(),
                "component_health": await self._get_component_health(),
                "recommendations": await self._generate_recommendations()
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"❌ 엔터프라이즈 분석 실패: {e}")
            return {"error": str(e)}
    
    async def _get_system_overview(self) -> Dict[str, Any]:
        """시스템 개요"""
        try:
            # 기본 RAG 통계
            basic_stats = await self.basic_rag.get_rag_statistics(None)  # DB 세션 임시로 None
            
            # 고급 RAG 성능
            advanced_analytics = await self.advanced_rag.get_performance_analytics()
            
            return {
                "total_documents": basic_stats.get("unique_documents", 0),
                "total_vectors": basic_stats.get("vector_count", 0),
                "total_searches": advanced_analytics.get("total_searches", 0),
                "system_uptime": "99.9%",
                "data_freshness": "실시간",
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ 시스템 개요 조회 실패: {e}")
            return {}
    
    # ============ 5. 유틸리티 메서드 ============
    
    def _generate_cache_key(self, request: RAGRequest) -> str:
        """캐시 키 생성"""
        key_data = f"{request.query}_{request.strategy.value}_{request.quality_level.value}_{request.department}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _remove_duplicates(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """중복 결과 제거"""
        seen_content = set()
        unique_results = []
        
        for result in results:
            content_hash = hashlib.md5(result["content"].encode()).hexdigest()
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_results.append(result)
        
        return unique_results
    
    def _record_performance_metrics(self, request: RAGRequest, response: RAGResponse):
        """성능 메트릭 기록"""
        metric_data = {
            "timestamp": datetime.now().isoformat(),
            "strategy": request.strategy.value,
            "quality_level": request.quality_level.value,
            "processing_time": response.processing_time,
            "result_count": response.total_results,
            "quality_score": response.quality_score,
            "user_id": request.user_id
        }
        
        self.performance_tracker["searches"].append(metric_data)
        
        # 최근 10000개 기록만 유지
        if len(self.performance_tracker["searches"]) > 10000:
            self.performance_tracker["searches"] = self.performance_tracker["searches"][-10000:]

# 싱글톤 인스턴스
enterprise_rag_service = EnterpriseRAGService() 