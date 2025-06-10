from qdrant_client import QdrantClient
import os

# 환경 설정에 따른 Qdrant 클라이언트 설정
# 1. 로컬 Qdrant (env.ini 설정)
try:
    local_client = QdrantClient(
        host="localhost",
        port=6333,
        https=False,
        prefer_grpc=False
    )
    print("=== 로컬 Qdrant 확인 (env.ini 설정) ===")
    print(f"호스트: localhost:6333")
    print(f"컬렉션: kb_learning_vectors")
    try:
        local_collections = local_client.get_collections()
        print(f"사용 가능한 컬렉션: {local_collections}")
        
        # kb_learning_vectors 컬렉션 확인
        if any(col.name == "kb_learning_vectors" for col in local_collections.collections):
            collection_info = local_client.get_collection("kb_learning_vectors")
            print(f"벡터 개수: {collection_info.points_count}")
            print(f"벡터 차원: {collection_info.config.params.vectors.size}")
            print(f"상태: {collection_info.status}")
            
            if collection_info.points_count > 0:
                # 일부 데이터 조회
                points, _ = local_client.scroll(
                    collection_name="kb_learning_vectors",
                    limit=5,
                    with_payload=True
                )
                
                print(f"\n📋 저장된 데이터 샘플:")
                for i, point in enumerate(points):
                    print(f"\n--- 포인트 {i+1} ---")
                    print(f"ID: {point.id}")
                    if point.payload:
                        print(f"타입: {point.payload.get('type', 'N/A')}")
                        print(f"문제 ID: {point.payload.get('question_id', 'N/A')}")
                        print(f"과목: {point.payload.get('subject', 'N/A')}")
                        print(f"학과: {point.payload.get('department', 'N/A')}")
            else:
                print("❌ 로컬 kb_learning_vectors 컬렉션에 데이터가 없습니다.")
        else:
            print("❌ kb_learning_vectors 컬렉션이 존재하지 않습니다.")
    except Exception as e:
        print(f"로컬 Qdrant 연결 실패: {e}")
except Exception as e:
    print(f"로컬 Qdrant 클라이언트 생성 실패: {e}")

print("\n" + "="*50)

# 2. 클라우드 Qdrant (기존 설정)
try:
    cloud_client = QdrantClient(
        url="https://c5af819b-eb1c-45b9-b5db-a5d458d03d9d.europe-west3-0.gcp.cloud.qdrant.io:6333", 
        api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.mtR5MB8F35kIuu2KCh5uA2dlO_SRBlb0mBMDdiyneWk",
    )
    
    print("=== 클라우드 Qdrant 확인 (기존 설정) ===")
    cloud_collections = cloud_client.get_collections()
    print(f"클라우드 컬렉션: {cloud_collections}")
    
    for collection in cloud_collections.collections:
        collection_name = collection.name
        print(f"\n--- 클라우드 컬렉션: {collection_name} ---")
        
        collection_info = cloud_client.get_collection(collection_name)
        print(f"벡터 개수: {collection_info.points_count}")
        print(f"벡터 차원: {collection_info.config.params.vectors.size}")
        print(f"상태: {collection_info.status}")
        
        if collection_info.points_count > 0:
            # 일부 데이터 조회
            points, _ = cloud_client.scroll(
                collection_name=collection_name,
                limit=3,
                with_payload=True
            )
            
            print(f"\n📋 저장된 데이터 샘플:")
            for i, point in enumerate(points):
                print(f"\n--- 포인트 {i+1} ---")
                print(f"ID: {point.id}")
                if point.payload:
                    print(f"타입: {point.payload.get('type', 'N/A')}")
                    print(f"메타데이터 키들: {list(point.payload.keys())}")
        else:
            print("❌ 클라우드 컬렉션에 데이터가 없습니다.")
            
except Exception as e:
    print(f"클라우드 Qdrant 연결 실패: {e}")

print("\n=== 확인 완료 ===")
print("\n💡 결론:")
print("- 로컬 Qdrant: kb_learning_vectors 컬렉션 사용 (RAG 통합 서비스 설정)")
print("- 클라우드 Qdrant: star_charts 컬렉션 사용 (별도 목적)")
print("- 승인된 문제는 로컬 kb_learning_vectors에 저장되어야 함")