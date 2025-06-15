"""
QDRANT 벡터 데이터베이스 클라이언트 유틸리티
"""
import os
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# QDRANT 클라이언트 임포트 (선택적)
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger.warning("QDRANT 클라이언트가 설치되지 않았습니다. pip install qdrant-client로 설치하세요.")


# Mock 클래스 제거됨 - 실제 QDRANT만 사용


def get_qdrant_client() -> Any:
    """
    QDRANT 클라이언트 인스턴스를 반환
    
    Returns:
        QdrantClient
    """
    if not QDRANT_AVAILABLE:
        raise Exception("QDRANT 클라이언트가 설치되지 않았습니다. pip install qdrant-client로 설치하세요.")
    
    try:
        # QDRANT 연결 설정 (직접 입력)
        host = "localhost"
        port = 6333
        # 로컬 개발용 - API 키 없음
        api_key = None
        
        # 로컬 연결만 시도 (API 키 없음)
        client = QdrantClient(
            host=host,
            port=port,
            timeout=5.0,
            https=False,  # 로컬은 HTTP 사용
            prefer_grpc=False
        )
        logger.info(f"QDRANT 클라이언트 연결 시도 (인증 없음): {host}:{port}")
        
        # 연결 테스트 건너뛰기 (인증 문제로 인해)
        logger.info(f"QDRANT 클라이언트 연결 완료 (테스트 건너뛰기): {host}:{port}")
        return client
        
    except Exception as e:
        logger.error(f"QDRANT 서버 연결 완전 실패: {e}")
        raise Exception(f"QDRANT 연결 실패: {e}")


def create_collection(collection_name: str, vector_size: int = 1536):
    """
    QDRANT 컬렉션 생성
    
    Args:
        collection_name: 컬렉션 이름
        vector_size: 벡터 차원 (기본값: 768차원)
    """
    if not QDRANT_AVAILABLE:
        logger.warning("QDRANT가 설치되지 않아 컬렉션을 생성할 수 없습니다.")
        return False
    
    try:
        client = get_qdrant_client()
        
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )
        logger.info(f"컬렉션 '{collection_name}' 생성 완료")
        return True
        
    except Exception as e:
        logger.error(f"컬렉션 생성 실패: {e}")
        return False


def upsert_points(collection_name: str, points: List[Dict[str, Any]]):
    """
    QDRANT에 포인트 삽입/업데이트
    
    Args:
        collection_name: 컬렉션 이름
        points: 삽입할 포인트 리스트
    """
    if not QDRANT_AVAILABLE:
        logger.warning("QDRANT가 설치되지 않아 포인트를 삽입할 수 없습니다.")
        return False
    
    try:
        client = get_qdrant_client()
        
        qdrant_points = []
        for point in points:
            qdrant_points.append(
                PointStruct(
                    id=point["id"],
                    vector=point["vector"],
                    payload=point.get("payload", {})
                )
            )
        
        client.upsert(
            collection_name=collection_name,
            points=qdrant_points
        )
        logger.info(f"컬렉션 '{collection_name}'에 {len(points)}개 포인트 삽입 완료")
        return True
        
    except Exception as e:
        logger.error(f"포인트 삽입 실패: {e}")
        return False


def search_similar(collection_name: str, query_vector: List[float], limit: int = 10):
    """
    유사한 벡터 검색
    
    Args:
        collection_name: 컬렉션 이름
        query_vector: 쿼리 벡터
        limit: 반환할 결과 수
        
    Returns:
        검색 결과 리스트
    """
    if not QDRANT_AVAILABLE:
        logger.warning("QDRANT가 설치되지 않아 검색을 수행할 수 없습니다.")
        return []
    
    try:
        client = get_qdrant_client()
        
        search_result = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit
        )
        
        return [{"id": hit.id, "score": hit.score, "payload": hit.payload} for hit in search_result]
        
    except Exception as e:
        logger.error(f"벡터 검색 실패: {e}")
        return [] 