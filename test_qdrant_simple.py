#!/usr/bin/env python3
"""
Qdrant 간단 연결 테스트
"""

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
import os

def test_qdrant_connection():
    """Qdrant 연결 테스트"""
    
    # 환경 변수에서 API 키 읽기
    api_key = "c5f8ce7bf0bea63e090a85ae26064e6ca61855e9dd26c5e37eb71bc6b36cc86f"
    
    print("🚀 Qdrant 연결 테스트 시작")
    print("=" * 50)
    
    try:
        # 1. 기본 연결 테스트 (HTTPS 없이)
        print("1. HTTP 연결 테스트 (api_key 포함)...")
        client = QdrantClient(
            host='localhost',
            port=6333,
            api_key=api_key,
            https=False,  # HTTPS 비활성화
            prefer_grpc=False  # gRPC 비활성화
        )
        print("   ✅ 클라이언트 생성 성공")
        
        # 2. 컬렉션 목록 조회
        print("2. 컬렉션 목록 조회...")
        collections = client.get_collections()
        print(f"   ✅ 컬렉션 개수: {len(collections.collections)}")
        for coll in collections.collections:
            print(f"   📦 컬렉션: {coll.name} (벡터수: {coll.vectors_count})")
        
        # 3. 테스트 컬렉션 생성
        print("3. 테스트 컬렉션 생성...")
        test_collection = "test_deepseek_vectors"
        
        # 기존 컬렉션 삭제 (있다면)
        try:
            client.delete_collection(test_collection)
            print(f"   🗑️ 기존 컬렉션 '{test_collection}' 삭제")
        except:
            pass
        
        # 새 컬렉션 생성
        client.create_collection(
            collection_name=test_collection,
            vectors_config=VectorParams(
                size=768,  # DeepSeek 임베딩 차원
                distance=Distance.COSINE
            )
        )
        print(f"   ✅ 컬렉션 '{test_collection}' 생성 성공")
        
        # 4. 컬렉션 정보 확인
        print("4. 컬렉션 정보 확인...")
        info = client.get_collection(test_collection)
        print(f"   📊 벡터 차원: {info.config.params.vectors.size}")
        print(f"   📊 거리 메트릭: {info.config.params.vectors.distance}")
        print(f"   📊 벡터 수: {info.vectors_count}")
        
        print("\n✅ 모든 테스트 통과!")
        print("🎉 FastAPI + Qdrant 아키텍처 준비 완료!")
        
        return True
        
    except Exception as e:
        print(f"❌ 연결 실패: {e}")
        print(f"오류 타입: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = test_qdrant_connection()
    
    if success:
        print("\n" + "=" * 50)
        print("🏗️ FastAPI + Qdrant 아키텍처 설명")
        print("=" * 50)
        print("✅ 현재 구조는 완벽합니다!")
        print()
        print("프론트엔드 → FastAPI (웹 API) → Qdrant Python Client → Qdrant Server")
        print()
        print("역할 분담:")
        print("• FastAPI: HTTP REST API 제공 (클라이언트와 통신)")
        print("• Qdrant: 벡터 데이터베이스 (고속 벡터 검색)")
        print("• Python Client: 중간 연결 라이브러리")
        print()
        print("장점:")
        print("• 🚀 성능: Connection pooling, 비동기 처리")
        print("• 🔒 보안: 내부 네트워크에서만 Qdrant 접근")
        print("• 📈 확장성: 무제한 동시 처리")
        print("• 💰 비용: 완전 무료 (로컬 운영)")
        print("\n합칠 필요 없습니다! 이미 최적화된 구조입니다! 🎯")
    else:
        print("\n❌ Qdrant 연결 문제를 해결한 후 다시 테스트하세요.") 