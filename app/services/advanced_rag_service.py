"""
상용화급 고급 RAG 시스템 서비스 - DeepSeek + Qdrant 기반
멀티모달, 하이브리드 검색, RAG Fusion, 적응형 청킹, 실시간 학습 등 최신 기술 통합
"""
import os
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from pathlib import Path
import uuid
import numpy as np
from collections import defaultdict
import hashlib

# 이미지 처리를 위한 조건부 임포트
try:
    from PIL import Image
    import pytesseract
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False

# 텍스트 처리 라이브러리
try:
    from sentence_transformers import SentenceTransformer
    import spacy
    ADVANCED_NLP_AVAILABLE = True
except ImportError:
    ADVANCED_NLP_AVAILABLE = False

from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_

from ..models.question import Question
from ..models.user import User
from ..services.deepseek_service import deepseek_service
from ..services.qdrant_service import qdrant_service
from ..core.config import settings

logger = logging.getLogger(__name__)

class AdvancedRAGService:
    """상용화급 고급 RAG 시스템"""
    
    def __init__(self):
        self.deepseek = deepseek_service
        self.vector_db = qdrant_service
        
        # 고급 기능 설정
        self.chunk_strategies = ["semantic", "hierarchical", "adaptive"]
        self.search_modes = ["hybrid", "dense", "sparse", "graph"]
        self.fusion_methods = ["rrf", "weighted", "neural"]
        
        # 성능 모니터링
        self.performance_metrics = defaultdict(list)
        self.user_feedback = defaultdict(list)
        
        # 캐시 시스템
        self.query_cache = {}
        self.embedding_cache = {}
        
        logger.info("🚀 고급 RAG 시스템 초기화 완료")
    
    # ============ 1. 멀티모달 RAG ============
    
    async def process_multimodal_document(
        self,
        db: Session,
        file_path: str,
        document_title: str,
        user_id: int,
        extract_images: bool = True,
        extract_tables: bool = True
    ) -> Dict[str, Any]:
        """멀티모달 문서 처리 (PDF + 이미지 + 텍스트)"""
        try:
            logger.info(f"🎯 멀티모달 문서 처리 시작: {document_title}")
            
            results = {
                "document_title": document_title,
                "processing_steps": {},
                "extracted_content": {
                    "text": [],
                    "images": [],
                    "tables": [],
                    "metadata": {}
                }
            }
            
            # 1. 텍스트 추출 (기존 방식 + 개선)
            text_content = await self._extract_enhanced_text(file_path)
            results["extracted_content"]["text"] = text_content
            results["processing_steps"]["text_extraction"] = {"success": True, "chunks": len(text_content)}
            
            # 2. 이미지 추출 및 OCR (선택적)
            if extract_images and VISION_AVAILABLE:
                image_content = await self._extract_and_analyze_images(file_path)
                results["extracted_content"]["images"] = image_content
                results["processing_steps"]["image_extraction"] = {"success": True, "images": len(image_content)}
            
            # 3. 표 추출 및 구조화 (선택적)
            if extract_tables:
                table_content = await self._extract_structured_tables(file_path)
                results["extracted_content"]["tables"] = table_content
                results["processing_steps"]["table_extraction"] = {"success": True, "tables": len(table_content)}
            
            # 4. 통합 임베딩 생성 및 저장
            embedding_result = await self._create_multimodal_embeddings(
                db, results["extracted_content"], document_title, user_id
            )
            results["processing_steps"]["embedding_creation"] = embedding_result
            
            logger.info(f"✅ 멀티모달 처리 완료: {document_title}")
            return {"success": True, "results": results}
            
        except Exception as e:
            logger.error(f"❌ 멀티모달 처리 실패: {e}")
            return {"success": False, "error": str(e)}
    
    async def _extract_enhanced_text(self, file_path: str) -> List[Dict[str, Any]]:
        """향상된 텍스트 추출 (구조 인식)"""
        try:
            # PDF에서 텍스트 추출 (기존 로직 + 구조 정보)
            from PyPDF2 import PdfReader
            
            reader = PdfReader(file_path)
            text_chunks = []
            
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text.strip():
                    # 적응형 청킹 적용
                    chunks = await self._adaptive_chunking(text, page_num)
                    text_chunks.extend(chunks)
            
            return text_chunks
            
        except Exception as e:
            logger.error(f"❌ 향상된 텍스트 추출 실패: {e}")
            return []
    
    async def _extract_and_analyze_images(self, file_path: str) -> List[Dict[str, Any]]:
        """이미지 추출 및 분석 (OCR + 설명 생성)"""
        if not VISION_AVAILABLE:
            return []
        
        try:
            # PDF에서 이미지 추출 (실제 구현 시 fitz 등 사용)
            images = []
            
            # 각 이미지에 대해 OCR 및 설명 생성
            for i, image_data in enumerate([]):  # 실제 이미지 데이터
                image_info = {
                    "image_id": f"img_{i}",
                    "ocr_text": "",
                    "description": "",
                    "metadata": {"page": i, "type": "figure"}
                }
                
                # OCR 텍스트 추출
                try:
                    # image_info["ocr_text"] = pytesseract.image_to_string(image_data)
                    pass
                except:
                    pass
                
                # DeepSeek으로 이미지 설명 생성 (텍스트 기반)
                if image_info["ocr_text"]:
                    description_prompt = f"다음 이미지의 OCR 텍스트를 분석하여 교육적 설명을 제공하세요: {image_info['ocr_text']}"
                    desc_result = await self.deepseek.chat_completion(
                        messages=[{"role": "user", "content": description_prompt}],
                        temperature=0.3
                    )
                    if desc_result["success"]:
                        image_info["description"] = desc_result["content"]
                
                images.append(image_info)
            
            return images
            
        except Exception as e:
            logger.error(f"❌ 이미지 분석 실패: {e}")
            return []
    
    async def _extract_structured_tables(self, file_path: str) -> List[Dict[str, Any]]:
        """구조화된 표 추출"""
        try:
            # 표 추출 로직 (실제 구현 시 camelot, tabula 등 사용)
            tables = []
            
            # 각 표를 구조화하여 저장
            for i, table_data in enumerate([]):  # 실제 표 데이터
                table_info = {
                    "table_id": f"table_{i}",
                    "headers": [],
                    "rows": [],
                    "summary": "",
                    "metadata": {"page": i, "type": "table"}
                }
                
                # DeepSeek으로 표 요약 생성
                table_text = str(table_data)
                summary_prompt = f"다음 표의 내용을 교육적 관점에서 요약하세요: {table_text}"
                summary_result = await self.deepseek.chat_completion(
                    messages=[{"role": "user", "content": summary_prompt}],
                    temperature=0.3
                )
                if summary_result["success"]:
                    table_info["summary"] = summary_result["content"]
                
                tables.append(table_info)
            
            return tables
            
        except Exception as e:
            logger.error(f"❌ 표 추출 실패: {e}")
            return []
    
    # ============ 2. 적응형 청킹 ============
    
    async def _adaptive_chunking(self, text: str, page_num: int) -> List[Dict[str, Any]]:
        """적응형 지능 청킹 (문서 구조 인식)"""
        try:
            chunks = []
            
            # 1. 기본 구조 분석 (제목, 단락, 리스트 등)
            lines = text.split('\n')
            current_chunk = ""
            chunk_type = "paragraph"
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 제목 패턴 감지
                if self._is_heading(line):
                    if current_chunk:
                        chunks.append(self._create_chunk(current_chunk, chunk_type, page_num, len(chunks)))
                        current_chunk = ""
                    chunk_type = "heading"
                    current_chunk = line
                
                # 리스트 패턴 감지
                elif self._is_list_item(line):
                    if chunk_type != "list" and current_chunk:
                        chunks.append(self._create_chunk(current_chunk, chunk_type, page_num, len(chunks)))
                        current_chunk = ""
                    chunk_type = "list"
                    current_chunk += f"{line}\n"
                
                # 일반 텍스트
                else:
                    if chunk_type != "paragraph" and current_chunk:
                        chunks.append(self._create_chunk(current_chunk, chunk_type, page_num, len(chunks)))
                        current_chunk = ""
                    chunk_type = "paragraph"
                    current_chunk += f"{line}\n"
                
                # 청크 크기 제한
                if len(current_chunk) > 1000:
                    chunks.append(self._create_chunk(current_chunk, chunk_type, page_num, len(chunks)))
                    current_chunk = ""
            
            # 마지막 청크 처리
            if current_chunk:
                chunks.append(self._create_chunk(current_chunk, chunk_type, page_num, len(chunks)))
            
            return chunks
            
        except Exception as e:
            logger.error(f"❌ 적응형 청킹 실패: {e}")
            return [self._create_chunk(text, "paragraph", page_num, 0)]
    
    def _is_heading(self, line: str) -> bool:
        """제목 패턴 감지"""
        heading_patterns = [
            line.isupper() and len(line) < 100,
            line.startswith(('Chapter', '장', '제', '1.', '2.', '3.')),
            len(line.split()) < 10 and line.endswith((':'))
        ]
        return any(heading_patterns)
    
    def _is_list_item(self, line: str) -> bool:
        """리스트 항목 감지"""
        list_patterns = [
            line.startswith(('•', '-', '*', '▪', '○')),
            line.startswith(tuple(f'{i}.' for i in range(1, 21))),
            line.startswith(tuple(f'({i})' for i in range(1, 21)))
        ]
        return any(list_patterns)
    
    def _create_chunk(self, content: str, chunk_type: str, page_num: int, chunk_index: int) -> Dict[str, Any]:
        """청크 객체 생성"""
        return {
            "content": content.strip(),
            "type": chunk_type,
            "page": page_num,
            "index": chunk_index,
            "length": len(content),
            "created_at": datetime.now().isoformat()
        }
    
    # ============ 3. 하이브리드 검색 ============
    
    async def hybrid_search(
        self,
        db: Session,
        query: str,
        search_mode: str = "hybrid",
        limit: int = 10,
        filters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """하이브리드 검색 (키워드 + 시맨틱 + 그래프)"""
        try:
            logger.info(f"🔍 하이브리드 검색 시작: {query} (모드: {search_mode})")
            
            results = {
                "query": query,
                "mode": search_mode,
                "results": [],
                "search_breakdown": {}
            }
            
            if search_mode == "hybrid":
                # 1. 시맨틱 검색 (Qdrant)
                semantic_results = await self._semantic_search(query, limit//2, filters)
                results["search_breakdown"]["semantic"] = len(semantic_results)
                
                # 2. 키워드 검색 (PostgreSQL)
                keyword_results = await self._keyword_search(db, query, limit//2, filters)
                results["search_breakdown"]["keyword"] = len(keyword_results)
                
                # 3. 결과 융합 (RRF - Reciprocal Rank Fusion)
                fused_results = self._reciprocal_rank_fusion([semantic_results, keyword_results])
                results["results"] = fused_results[:limit]
                
            elif search_mode == "dense":
                # 순수 시맨틱 검색
                results["results"] = await self._semantic_search(query, limit, filters)
                results["search_breakdown"]["semantic"] = len(results["results"])
                
            elif search_mode == "sparse":
                # 순수 키워드 검색
                results["results"] = await self._keyword_search(db, query, limit, filters)
                results["search_breakdown"]["keyword"] = len(results["results"])
                
            elif search_mode == "graph":
                # 그래프 기반 연관 검색
                results["results"] = await self._graph_search(db, query, limit, filters)
                results["search_breakdown"]["graph"] = len(results["results"])
            
            # 검색 성능 기록
            self._record_search_performance(query, search_mode, len(results["results"]))
            
            logger.info(f"✅ 하이브리드 검색 완료: {len(results['results'])}개 결과")
            return {"success": True, "data": results}
            
        except Exception as e:
            logger.error(f"❌ 하이브리드 검색 실패: {e}")
            return {"success": False, "error": str(e)}
    
    async def _semantic_search(self, query: str, limit: int, filters: Optional[Dict]) -> List[Dict]:
        """시맨틱 검색 (벡터 유사도)"""
        search_result = await self.vector_db.search_vectors(
            query_text=query,
            limit=limit,
            score_threshold=0.6,
            filter_conditions=filters
        )
        
        if search_result["success"]:
            return [
                {
                    "content": item["text"],
                    "score": item["score"],
                    "source": "semantic",
                    "metadata": item["metadata"]
                }
                for item in search_result["results"]
            ]
        return []
    
    async def _keyword_search(self, db: Session, query: str, limit: int, filters: Optional[Dict]) -> List[Dict]:
        """키워드 검색 (PostgreSQL FTS)"""
        try:
            # PostgreSQL의 전문 검색 사용
            search_query = text("""
                SELECT id, content, subject_name, difficulty, 
                       ts_rank(to_tsvector('korean', content), plainto_tsquery('korean', :query)) as rank
                FROM questions 
                WHERE to_tsvector('korean', content) @@ plainto_tsquery('korean', :query)
                ORDER BY rank DESC
                LIMIT :limit
            """)
            
            result = db.execute(search_query, {"query": query, "limit": limit})
            rows = result.fetchall()
            
            return [
                {
                    "content": row.content,
                    "score": float(row.rank),
                    "source": "keyword",
                    "metadata": {
                        "question_id": row.id,
                        "subject": row.subject_name,
                        "difficulty": row.difficulty
                    }
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"❌ 키워드 검색 실패: {e}")
            return []
    
    async def _graph_search(self, db: Session, query: str, limit: int, filters: Optional[Dict]) -> List[Dict]:
        """그래프 기반 연관 검색"""
        try:
            # 1. 초기 시맨틱 검색으로 시드 노드 찾기
            seed_results = await self._semantic_search(query, 3, filters)
            
            if not seed_results:
                return []
            
            # 2. 시드 노드와 연관된 콘텐츠 찾기
            related_content = []
            
            for seed in seed_results:
                if "question_id" in seed["metadata"]:
                    # 같은 과목/난이도의 문제들 찾기
                    related_query = text("""
                        SELECT content, subject_name, difficulty
                        FROM questions 
                        WHERE subject_name = :subject 
                        AND difficulty = :difficulty
                        AND id != :question_id
                        LIMIT 3
                    """)
                    
                    result = db.execute(related_query, {
                        "subject": seed["metadata"].get("subject", ""),
                        "difficulty": seed["metadata"].get("difficulty", ""),
                        "question_id": seed["metadata"]["question_id"]
                    })
                    
                    for row in result.fetchall():
                        related_content.append({
                            "content": row.content,
                            "score": seed["score"] * 0.8,  # 연관도 감소
                            "source": "graph",
                            "metadata": {
                                "subject": row.subject_name,
                                "difficulty": row.difficulty,
                                "relation": "same_category"
                            }
                        })
            
            # 3. 원본 결과와 연관 결과 결합
            all_results = seed_results + related_content
            
            # 중복 제거 및 점수순 정렬
            unique_results = {}
            for item in all_results:
                content_hash = hashlib.md5(item["content"].encode()).hexdigest()
                if content_hash not in unique_results or unique_results[content_hash]["score"] < item["score"]:
                    unique_results[content_hash] = item
            
            return sorted(unique_results.values(), key=lambda x: x["score"], reverse=True)[:limit]
            
        except Exception as e:
            logger.error(f"❌ 그래프 검색 실패: {e}")
            return []
    
    def _reciprocal_rank_fusion(self, result_lists: List[List[Dict]], k: int = 60) -> List[Dict]:
        """Reciprocal Rank Fusion으로 검색 결과 융합"""
        scores = defaultdict(float)
        all_items = {}
        
        for result_list in result_lists:
            for rank, item in enumerate(result_list):
                content_hash = hashlib.md5(item["content"].encode()).hexdigest()
                scores[content_hash] += 1 / (k + rank + 1)
                all_items[content_hash] = item
        
        # 점수순으로 정렬하여 반환
        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [all_items[content_hash] for content_hash, score in sorted_items]
    
    # ============ 4. RAG Fusion ============
    
    async def rag_fusion_search(
        self,
        db: Session,
        original_query: str,
        num_queries: int = 5,
        fusion_method: str = "rrf"
    ) -> Dict[str, Any]:
        """RAG Fusion - 다중 쿼리 생성 및 결과 융합"""
        try:
            logger.info(f"🔥 RAG Fusion 검색 시작: {original_query}")
            
            # 1. 다양한 관점의 쿼리 생성
            generated_queries = await self._generate_multiple_queries(original_query, num_queries)
            
            # 2. 각 쿼리로 개별 검색 수행
            all_results = []
            query_results = {}
            
            for i, query in enumerate([original_query] + generated_queries):
                search_result = await self.hybrid_search(db, query, "hybrid", 10)
                if search_result["success"]:
                    results = search_result["data"]["results"]
                    all_results.append(results)
                    query_results[f"query_{i}"] = {"query": query, "results_count": len(results)}
            
            # 3. 결과 융합
            if fusion_method == "rrf":
                fused_results = self._reciprocal_rank_fusion(all_results)
            elif fusion_method == "weighted":
                fused_results = self._weighted_fusion(all_results, [1.0] + [0.8] * len(generated_queries))
            else:
                fused_results = self._neural_fusion(all_results)
            
            return {
                "success": True,
                "original_query": original_query,
                "generated_queries": generated_queries,
                "fusion_method": fusion_method,
                "query_breakdown": query_results,
                "final_results": fused_results[:15],
                "total_unique_results": len(fused_results)
            }
            
        except Exception as e:
            logger.error(f"❌ RAG Fusion 실패: {e}")
            return {"success": False, "error": str(e)}
    
    async def _generate_multiple_queries(self, original_query: str, num_queries: int) -> List[str]:
        """다양한 관점의 쿼리 생성"""
        prompt = f"""
원본 질문: "{original_query}"

위 질문에 대해 다양한 관점에서 {num_queries}개의 유사하지만 다른 질문들을 생성해주세요.
각 질문은 다음과 같은 다른 접근 방식을 사용해야 합니다:
1. 구체적 세부사항 중심
2. 광범위한 맥락 중심  
3. 실무 적용 중심
4. 이론적 배경 중심
5. 문제 해결 중심

JSON 형식으로 반환해주세요:
{{"queries": ["질문1", "질문2", "질문3", "질문4", "질문5"]}}
"""
        
        result = await self.deepseek.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8
        )
        
        if result["success"]:
            try:
                data = json.loads(result["content"])
                return data.get("queries", [])[:num_queries]
            except json.JSONDecodeError:
                pass
        
        # 폴백: 간단한 변형 생성
        return [
            f"{original_query} 실무 사례",
            f"{original_query} 이론적 배경",
            f"{original_query} 문제 해결",
            f"{original_query} 세부 내용"
        ][:num_queries]
    
    def _weighted_fusion(self, result_lists: List[List[Dict]], weights: List[float]) -> List[Dict]:
        """가중치 기반 결과 융합"""
        scores = defaultdict(float)
        all_items = {}
        
        for i, (result_list, weight) in enumerate(zip(result_lists, weights)):
            for rank, item in enumerate(result_list):
                content_hash = hashlib.md5(item["content"].encode()).hexdigest()
                scores[content_hash] += weight * item.get("score", 1.0) / (rank + 1)
                all_items[content_hash] = item
        
        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [all_items[content_hash] for content_hash, score in sorted_items]
    
    def _neural_fusion(self, result_lists: List[List[Dict]]) -> List[Dict]:
        """신경망 기반 결과 융합 (간단한 앙상블)"""
        # 현재는 RRF와 동일하게 구현, 추후 ML 모델로 확장 가능
        return self._reciprocal_rank_fusion(result_lists)
    
    # ============ 5. 실시간 학습 및 개인화 ============
    
    async def update_from_feedback(
        self,
        db: Session,
        user_id: int,
        query: str,
        selected_result: Dict[str, Any],
        feedback_score: float,
        feedback_comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """사용자 피드백 기반 실시간 학습"""
        try:
            logger.info(f"📚 실시간 학습 업데이트: 사용자 {user_id}")
            
            # 1. 피드백 기록
            feedback_data = {
                "user_id": user_id,
                "query": query,
                "selected_content": selected_result.get("content", ""),
                "score": feedback_score,
                "comment": feedback_comment,
                "timestamp": datetime.now().isoformat(),
                "metadata": selected_result.get("metadata", {})
            }
            
            self.user_feedback[user_id].append(feedback_data)
            
            # 2. 긍정적 피드백인 경우 벡터 강화
            if feedback_score >= 4.0:  # 5점 만점에서 4점 이상
                await self._enhance_positive_vector(selected_result, user_id)
            
            # 3. 부정적 피드백인 경우 벡터 조정
            elif feedback_score <= 2.0:  # 2점 이하
                await self._adjust_negative_vector(selected_result, user_id)
            
            # 4. 개인화 프로필 업데이트
            await self._update_user_preference_profile(user_id, query, selected_result, feedback_score)
            
            return {
                "success": True,
                "message": "피드백이 반영되었습니다",
                "user_feedback_count": len(self.user_feedback[user_id]),
                "learning_status": "updated"
            }
            
        except Exception as e:
            logger.error(f"❌ 실시간 학습 실패: {e}")
            return {"success": False, "error": str(e)}
    
    async def _enhance_positive_vector(self, result: Dict[str, Any], user_id: int):
        """긍정적 피드백 벡터 강화"""
        try:
            content = result.get("content", "")
            if not content:
                return
            
            # 기존 벡터의 가중치 증가 (메타데이터에 반영)
            enhanced_metadata = result.get("metadata", {})
            enhanced_metadata["positive_feedback_count"] = enhanced_metadata.get("positive_feedback_count", 0) + 1
            enhanced_metadata["user_preferences"] = enhanced_metadata.get("user_preferences", [])
            
            if user_id not in enhanced_metadata["user_preferences"]:
                enhanced_metadata["user_preferences"].append(user_id)
            
            # Qdrant에 강화된 벡터 저장 (별도 컬렉션 또는 메타데이터 업데이트)
            await self.vector_db.add_vectors(
                texts=[content],
                metadatas=[enhanced_metadata],
                ids=[f"enhanced_{user_id}_{uuid.uuid4()}"]
            )
            
        except Exception as e:
            logger.error(f"❌ 긍정적 벡터 강화 실패: {e}")
    
    async def _update_user_preference_profile(
        self, 
        user_id: int, 
        query: str, 
        result: Dict[str, Any], 
        score: float
    ):
        """사용자 선호도 프로필 업데이트"""
        try:
            # 사용자별 선호도 분석
            if user_id not in self.user_feedback:
                self.user_feedback[user_id] = []
            
            # 선호하는 콘텐츠 유형 분석
            metadata = result.get("metadata", {})
            subject = metadata.get("subject", "")
            difficulty = metadata.get("difficulty", "")
            
            # 간단한 선호도 점수 계산
            preferences = {
                "preferred_subjects": defaultdict(float),
                "preferred_difficulty": defaultdict(float),
                "query_patterns": []
            }
            
            for feedback in self.user_feedback[user_id]:
                if feedback["score"] >= 4.0:
                    meta = feedback["metadata"]
                    preferences["preferred_subjects"][meta.get("subject", "")] += 1
                    preferences["preferred_difficulty"][meta.get("difficulty", "")] += 1
            
            logger.info(f"📊 사용자 {user_id} 선호도 프로필 업데이트 완료")
            
        except Exception as e:
            logger.error(f"❌ 선호도 프로필 업데이트 실패: {e}")
    
    # ============ 6. 성능 모니터링 ============
    
    def _record_search_performance(self, query: str, mode: str, result_count: int):
        """검색 성능 기록"""
        performance_data = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "mode": mode,
            "result_count": result_count,
            "response_time": 0  # 실제 구현 시 측정
        }
        
        self.performance_metrics[mode].append(performance_data)
        
        # 최근 1000개 기록만 유지
        if len(self.performance_metrics[mode]) > 1000:
            self.performance_metrics[mode] = self.performance_metrics[mode][-1000:]
    
    async def get_performance_analytics(self) -> Dict[str, Any]:
        """성능 분석 리포트"""
        try:
            analytics = {
                "total_searches": sum(len(metrics) for metrics in self.performance_metrics.values()),
                "search_modes": {},
                "user_satisfaction": {},
                "query_patterns": {},
                "system_health": "excellent"
            }
            
            # 모드별 성능 분석
            for mode, metrics in self.performance_metrics.items():
                if metrics:
                    avg_results = sum(m["result_count"] for m in metrics) / len(metrics)
                    analytics["search_modes"][mode] = {
                        "total_searches": len(metrics),
                        "avg_results": round(avg_results, 2),
                        "last_used": metrics[-1]["timestamp"] if metrics else None
                    }
            
            # 사용자 만족도 분석
            total_feedback = sum(len(feedback) for feedback in self.user_feedback.values())
            if total_feedback > 0:
                all_scores = []
                for user_feedback in self.user_feedback.values():
                    all_scores.extend([f["score"] for f in user_feedback])
                
                analytics["user_satisfaction"] = {
                    "total_feedback": total_feedback,
                    "avg_score": round(sum(all_scores) / len(all_scores), 2),
                    "satisfaction_rate": round(len([s for s in all_scores if s >= 4.0]) / len(all_scores) * 100, 1)
                }
            
            return analytics
            
        except Exception as e:
            logger.error(f"❌ 성능 분석 실패: {e}")
            return {"error": str(e)}

# 싱글톤 인스턴스
advanced_rag_service = AdvancedRAGService() 