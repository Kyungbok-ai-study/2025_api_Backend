"""
Qdrant 벡터 데이터베이스 서비스
pgvector 대신 Qdrant를 사용한 고성능 벡터 검색
"""
import os
import logging
import uuid
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import asyncio
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    from qdrant_client.http.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

from .deepseek_service import deepseek_service
from ..core.config import settings

logger = logging.getLogger(__name__)

class QdrantService:
    """Qdrant 벡터 데이터베이스 서비스 - pgvector 완전 대체"""
    
    def __init__(self):
        self.host = settings.QDRANT_HOST
        self.port = settings.QDRANT_PORT
        self.api_key = settings.QDRANT_API_KEY
        self.collection_name = "kb_learning_vectors"
        
        self.client = None
        self.vector_dimension = settings.VECTOR_DIMENSION  # 768 (DeepSeek 기본)
        
        if QDRANT_AVAILABLE and settings.QDRANT_ENABLED:
            self._init_client()
        else:
            logger.warning("❌ Qdrant가 비활성화되었거나 클라이언트가 설치되지 않았습니다.")
    
    def _init_client(self):
        """Qdrant 클라이언트 초기화"""
        import warnings
        
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message="Api key is used with an insecure connection")
                
                # 클라우드 또는 로컬 연결
                if self.api_key:
                    self.client = QdrantClient(
                        host=self.host,
                        port=self.port,
                        api_key=self.api_key,
                        https=True
                    )
                    logger.info(f"✅ Qdrant 클라우드 연결 완료: {self.host}:{self.port}")
                else:
                    self.client = QdrantClient(
                        host=self.host, 
                        port=self.port,
                        https=False,
                        prefer_grpc=False
                    )
                    logger.info(f"✅ Qdrant 로컬 연결 완료: {self.host}:{self.port}")
                
                # 컬렉션 확인 및 생성
                self._ensure_collection()
            
        except Exception as e:
            logger.error(f"❌ Qdrant 클라이언트 초기화 실패: {e}")
            self.client = None
    
    def _ensure_collection(self):
        """컬렉션 존재 확인 및 생성"""
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"📦 Qdrant 컬렉션 생성: {self.collection_name}")
                
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_dimension,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ 컬렉션 생성 완료: {self.collection_name}")
            else:
                logger.info(f"✅ 기존 컬렉션 사용: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"❌ 컬렉션 설정 실패: {e}")
            self.client = None
    
    async def add_question_vector(
        self, 
        question_id: int,
        content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """문제를 벡터로 변환하여 Qdrant에 저장 (pgvector 대체)"""
        if not self.client:
            return {"success": False, "error": "Qdrant 클라이언트 없음"}
        
        try:
            # DeepSeek으로 임베딩 생성
            embedding_result = await deepseek_service.create_embeddings([content])
            
            if not embedding_result["success"]:
                return {"success": False, "error": "임베딩 생성 실패"}
            
            embedding = embedding_result["embeddings"][0]
            
            # Qdrant 벡터 ID 생성
            vector_id = f"question_{question_id}_{uuid.uuid4().hex[:8]}"
            
            # 메타데이터 준비
            payload = {
                "question_id": question_id,
                "content": content,
                "created_at": datetime.now().isoformat(),
                **metadata
            }
            
            # Qdrant에 벡터 저장
            point = PointStruct(
                id=vector_id,
                vector=embedding,
                payload=payload
            )
            
            operation_info = self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info(f"✅ 문제 {question_id} 벡터 저장 완료: {vector_id}")
            
            return {
                "success": True,
                "vector_id": vector_id,
                "question_id": question_id,
                "operation_id": operation_info.operation_id if hasattr(operation_info, 'operation_id') else None
            }
            
        except Exception as e:
            logger.error(f"❌ 문제 벡터 저장 실패 (ID: {question_id}): {e}")
            return {"success": False, "error": str(e)}
    
    async def search_similar_questions(
        self,
        query_text: str,
        difficulty: Optional[str] = None,
        subject: Optional[str] = None,
        department: Optional[str] = None,
        limit: int = 5,
        score_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """유사한 문제 검색 (pgvector 유사도 검색 대체)"""
        if not self.client:
            return {"success": False, "error": "Qdrant 클라이언트 없음"}
        
        try:
            # 쿼리 임베딩 생성
            embedding_result = await deepseek_service.create_embeddings([query_text])
            
            if not embedding_result["success"]:
                return {"success": False, "error": "쿼리 임베딩 생성 실패"}
            
            query_vector = embedding_result["embeddings"][0]
            
            # 필터 조건 설정
            filter_conditions = []
            
            if difficulty:
                filter_conditions.append(
                    models.FieldCondition(
                        key="difficulty",
                        match=models.MatchValue(value=difficulty)
                    )
                )
            
            if subject:
                filter_conditions.append(
                    models.FieldCondition(
                        key="subject",
                        match=models.MatchValue(value=subject)
                    )
                )
            
            if department:
                filter_conditions.append(
                    models.FieldCondition(
                        key="department",
                        match=models.MatchValue(value=department)
                    )
                )
            
            query_filter = None
            if filter_conditions:
                query_filter = models.Filter(must=filter_conditions)
            
            # 벡터 검색 실행
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=limit,
                score_threshold=score_threshold
            )
            
            # 결과 포맷팅
            results = []
            for scored_point in search_result:
                result = {
                    "question_id": scored_point.payload.get("question_id"),
                    "content": scored_point.payload.get("content"),
                    "score": scored_point.score,
                    "metadata": {
                        k: v for k, v in scored_point.payload.items() 
                        if k not in ["question_id", "content", "created_at"]
                    }
                }
                results.append(result)
            
            logger.info(f"✅ 유사 문제 검색 완료: {len(results)}개 결과")
            
            return {
                "success": True,
                "results": results,
                "query": query_text,
                "total_found": len(results)
            }
            
        except Exception as e:
            logger.error(f"❌ 유사 문제 검색 실패: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_question_vector(
        self,
        vector_id: str,
        question_id: int,
        content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """문제 벡터 업데이트"""
        if not self.client:
            return {"success": False, "error": "Qdrant 클라이언트 없음"}
        
        try:
            # 새로운 임베딩 생성
            embedding_result = await deepseek_service.create_embeddings([content])
            
            if not embedding_result["success"]:
                return {"success": False, "error": "임베딩 생성 실패"}
            
            embedding = embedding_result["embeddings"][0]
            
            # 메타데이터 준비
            payload = {
                "question_id": question_id,
                "content": content,
                "updated_at": datetime.now().isoformat(),
                **metadata
            }
            
            # 벡터 업데이트
            point = PointStruct(
                id=vector_id,
                vector=embedding,
                payload=payload
            )
            
            operation_info = self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info(f"✅ 문제 벡터 업데이트 완료: {vector_id}")
            
            return {
                "success": True,
                "vector_id": vector_id,
                "question_id": question_id
            }
            
        except Exception as e:
            logger.error(f"❌ 문제 벡터 업데이트 실패: {e}")
            return {"success": False, "error": str(e)}
    
    def delete_question_vector(self, vector_id: str) -> Dict[str, Any]:
        """문제 벡터 삭제"""
        if not self.client:
            return {"success": False, "error": "Qdrant 클라이언트 없음"}
        
        try:
            operation_info = self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=[vector_id]
                )
            )
            
            logger.info(f"✅ 문제 벡터 삭제 완료: {vector_id}")
            
            return {
                "success": True,
                "deleted_vector_id": vector_id
            }
            
        except Exception as e:
            logger.error(f"❌ 문제 벡터 삭제 실패: {e}")
            return {"success": False, "error": str(e)}
    
    def get_collection_info(self) -> Dict[str, Any]:
        """컬렉션 정보 조회"""
        if not self.client:
            return {"success": False, "error": "Qdrant 클라이언트 없음"}
        
        try:
            collection_info = self.client.get_collection(self.collection_name)
            
            return {
                "success": True,
                "collection_name": self.collection_name,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "points_count": collection_info.points_count,
                "segments_count": collection_info.segments_count,
                "config": {
                    "vector_size": collection_info.config.params.vectors.size,
                    "distance": collection_info.config.params.vectors.distance.value
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 컬렉션 정보 조회 실패: {e}")
            return {"success": False, "error": str(e)}

# 전역 인스턴스
qdrant_service = QdrantService() 