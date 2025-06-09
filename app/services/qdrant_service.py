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

logger = logging.getLogger(__name__)

class QdrantService:
    """Qdrant 벡터 데이터베이스 서비스"""
    
    def __init__(self):
        self.host = os.getenv("QDRANT_HOST", "localhost")
        self.port = int(os.getenv("QDRANT_PORT", "6333"))
        self.collection_name = os.getenv("QDRANT_COLLECTION_NAME", "kb_learning_vectors")
        self.api_key = os.getenv("QDRANT_API_KEY")
        
        self.client = None
        self.vector_dimension = 768  # DeepSeek 임베딩 차원
        
        if QDRANT_AVAILABLE:
            self._init_client()
        else:
            logger.warning("❌ Qdrant 클라이언트가 설치되지 않았습니다. 'pip install qdrant-client' 실행하세요.")
    
    def _init_client(self):
        """Qdrant 클라이언트 초기화"""
        import warnings
        
        try:
            # SSL 관련 경고 임시 억제
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message="Api key is used with an insecure connection")
                
                # API 키가 있으면 사용, 없으면 기본 연결
                if self.api_key and self.api_key.strip():
                    self.client = QdrantClient(
                        host=self.host, 
                        port=self.port,
                        api_key=self.api_key,
                        https=False,  # 로컬 Docker는 HTTP 사용
                        prefer_grpc=False  # gRPC 비활성화
                    )
                    logger.info(f"✅ Qdrant 클라이언트 초기화 완료 (API 키 사용): {self.host}:{self.port}")
                else:
                    self.client = QdrantClient(
                        host=self.host, 
                        port=self.port,
                        https=False,  # 로컬 Docker는 HTTP 사용
                        prefer_grpc=False  # gRPC 비활성화
                    )
                    logger.info(f"✅ Qdrant 클라이언트 초기화 완료: {self.host}:{self.port}")
            
            # 컬렉션 생성 (없는 경우)
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
    
    async def add_vectors(
        self, 
        texts: List[str], 
        metadatas: List[Dict[str, Any]], 
        ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """벡터 추가"""
        if not self.client:
            return {"success": False, "error": "Qdrant 클라이언트 없음"}
        
        try:
            # DeepSeek으로 임베딩 생성
            embedding_result = await deepseek_service.create_embeddings(texts)
            
            if not embedding_result["success"]:
                return {"success": False, "error": "임베딩 생성 실패"}
            
            embeddings = embedding_result["embeddings"]
            
            # ID 생성 (없는 경우)
            if not ids:
                ids = [str(uuid.uuid4()) for _ in texts]
            
            # Qdrant 포인트 생성
            points = []
            for i, (text, embedding, metadata, point_id) in enumerate(zip(texts, embeddings, metadatas, ids)):
                # 메타데이터에 텍스트 추가
                payload = {
                    "text": text,
                    "created_at": datetime.now().isoformat(),
                    **metadata
                }
                
                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                )
                points.append(point)
            
            # 벡터 업로드
            operation_info = self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"✅ {len(points)}개 벡터 추가 완료")
            
            return {
                "success": True,
                "added_count": len(points),
                "ids": ids,
                "operation_id": operation_info.operation_id if hasattr(operation_info, 'operation_id') else None
            }
            
        except Exception as e:
            logger.error(f"❌ 벡터 추가 실패: {e}")
            return {"success": False, "error": str(e)}
    
    async def search_vectors(
        self, 
        query_text: str, 
        limit: int = 5,
        score_threshold: float = 0.7,
        filter_conditions: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """벡터 검색"""
        if not self.client:
            return {"success": False, "error": "Qdrant 클라이언트 없음"}
        
        try:
            # 쿼리 임베딩 생성
            embedding_result = await deepseek_service.create_embeddings([query_text])
            
            if not embedding_result["success"]:
                return {"success": False, "error": "쿼리 임베딩 생성 실패"}
            
            query_vector = embedding_result["embeddings"][0]
            
            # 필터 조건 설정
            query_filter = None
            if filter_conditions:
                query_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value)
                        )
                        for key, value in filter_conditions.items()
                    ]
                )
            
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
                    "id": scored_point.id,
                    "score": scored_point.score,
                    "text": scored_point.payload.get("text", ""),
                    "metadata": {k: v for k, v in scored_point.payload.items() if k != "text"}
                }
                results.append(result)
            
            logger.info(f"✅ 벡터 검색 완료: {len(results)}개 결과")
            
            return {
                "success": True,
                "results": results,
                "query": query_text,
                "total_count": len(results)
            }
            
        except Exception as e:
            logger.error(f"❌ 벡터 검색 실패: {e}")
            return {"success": False, "error": str(e)}
    
    def delete_vectors(self, ids: List[str]) -> Dict[str, Any]:
        """벡터 삭제"""
        if not self.client:
            return {"success": False, "error": "Qdrant 클라이언트 없음"}
        
        try:
            operation_info = self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=ids
                )
            )
            
            logger.info(f"✅ {len(ids)}개 벡터 삭제 완료")
            
            return {
                "success": True,
                "deleted_count": len(ids),
                "operation_id": operation_info.operation_id if hasattr(operation_info, 'operation_id') else None
            }
            
        except Exception as e:
            logger.error(f"❌ 벡터 삭제 실패: {e}")
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
                "points_count": collection_info.points_count,
                "segments_count": collection_info.segments_count,
                "status": collection_info.status
            }
            
        except Exception as e:
            logger.error(f"❌ 컬렉션 정보 조회 실패: {e}")
            return {"success": False, "error": str(e)}
    
    async def add_question_vector(
        self, 
        question_id: int,
        content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """문제 벡터 추가 (특화 메서드)"""
        
        enhanced_metadata = {
            "question_id": question_id,
            "type": "question",
            "subject": metadata.get("subject", ""),
            "difficulty": metadata.get("difficulty", "중"),
            "department": metadata.get("department", ""),
            "year": metadata.get("year", datetime.now().year),
            **metadata
        }
        
        return await self.add_vectors(
            texts=[content],
            metadatas=[enhanced_metadata],
            ids=[f"question_{question_id}"]
        )
    
    async def search_similar_questions(
        self,
        query_text: str,
        difficulty: Optional[str] = None,
        subject: Optional[str] = None,
        department: Optional[str] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """유사 문제 검색 (특화 메서드)"""
        
        filter_conditions = {"type": "question"}
        
        if difficulty:
            filter_conditions["difficulty"] = difficulty
        if subject:
            filter_conditions["subject"] = subject
        if department:
            filter_conditions["department"] = department
        
        return await self.search_vectors(
            query_text=query_text,
            limit=limit,
            score_threshold=0.6,
            filter_conditions=filter_conditions
        )

# 싱글톤 인스턴스
qdrant_service = QdrantService() 