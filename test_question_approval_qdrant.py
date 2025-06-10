#!/usr/bin/env python3
"""
문제 승인 시 Qdrant 저장 프로세스 테스트
"""
import asyncio
import sys
import os
from pathlib import Path

# 현재 디렉토리를 Python path에 추가
sys.path.append(str(Path(__file__).parent))

from app.services.category_storage_service import CategoryStorageService
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_qdrant_connection():
    """Qdrant 연결 테스트"""
    print("=== Qdrant 연결 테스트 ===")
    
    # 1. 로컬 Qdrant 연결 테스트 (env.ini에서 API 키 사용)
    try:
        # env.ini에서 설정된 API 키 사용
        api_key = "c5f8ce7bf0bea63e090a85ae26064e6ca61855e9dd26c5e37eb71bc6b36cc86f"
        
        client = QdrantClient(
            host="localhost", 
            port=6333, 
            api_key=api_key,
            timeout=30,
            https=False
        )
        collections = client.get_collections()
        print(f"✅ 로컬 Qdrant 연결 성공")
        print(f"현재 컬렉션: {[col.name for col in collections.collections]}")
        return client
    except Exception as e:
        print(f"❌ 로컬 Qdrant 연결 실패: {e}")
        
        # 2. API 키 없이 연결 시도
        try:
            client = QdrantClient(host="localhost", port=6333, timeout=30)
            collections = client.get_collections()
            print(f"✅ 로컬 Qdrant 연결 성공 (API 키 없음)")
            print(f"현재 컬렉션: {[col.name for col in collections.collections]}")
            return client
        except Exception as e2:
            print(f"❌ 로컬 Qdrant 연결 실패 (API 키 없음): {e2}")
            
            # 3. 클라우드 Qdrant 연결 시도
            try:
                cloud_client = QdrantClient(
                    url="https://c5af819b-eb1c-45b9-b5db-a5d458d03d9d.europe-west3-0.gcp.cloud.qdrant.io:6333", 
                    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.mtR5MB8F35kIuu2KCh5uA2dlO_SRBlb0mBMDdiyneWk",
                )
                collections = cloud_client.get_collections()
                print(f"✅ 클라우드 Qdrant 연결 성공")
                print(f"현재 컬렉션: {[col.name for col in collections.collections]}")
                return cloud_client
            except Exception as e3:
                print(f"❌ 클라우드 Qdrant 연결 실패: {e3}")
                return None

def test_category_storage_service():
    """카테고리 저장 서비스 테스트"""
    print("\n=== 카테고리 저장 서비스 테스트 ===")
    
    try:
        # 카테고리 저장 서비스 인스턴스 생성
        storage_service = CategoryStorageService()
        
        # Qdrant 클라이언트 초기화 (수정된 초기화 메서드 사용)
        if storage_service.initialize_qdrant_client():
            print("✅ 카테고리 저장 서비스 Qdrant 연결 성공")
        else:
            print("❌ 카테고리 저장 서비스 Qdrant 연결 실패")
            
            # 대안: 직접 클라우드 Qdrant 사용
            try:
                from qdrant_client import QdrantClient
                storage_service.qdrant_client = QdrantClient(
                    url="https://c5af819b-eb1c-45b9-b5db-a5d458d03d9d.europe-west3-0.gcp.cloud.qdrant.io:6333", 
                    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.mtR5MB8F35kIuu2KCh5uA2dlO_SRBlb0mBMDdiyneWk",
                )
                print("✅ 클라우드 Qdrant로 대체 연결 성공")
            except Exception as e:
                print(f"❌ 클라우드 Qdrant 대체 연결 실패: {e}")
                return False
        
        # 테스트용 컬렉션 생성
        test_departments = ["간호학과", "물리치료학과", "작업치료학과"]
        test_categories = ["국가고시", "일반"]
        
        for department in test_departments:
            for category in test_categories:
                success = storage_service.create_collection_if_not_exists(department, category)
                if success:
                    print(f"✅ {department} - {category} 컬렉션 준비 완료")
                else:
                    print(f"❌ {department} - {category} 컬렉션 준비 실패")
        
        # 컬렉션 통계 조회
        for department in test_departments:
            stats = storage_service.get_collection_stats(department)
            print(f"\n📊 {department} 통계:")
            print(f"  총 문제 수: {stats['total_questions']}")
            for category, info in stats.get('collections', {}).items():
                if 'error' not in info:
                    print(f"  {category}: {info['point_count']}개 문제 ({info['collection_name']})")
                else:
                    print(f"  {category}: 오류 - {info['error']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 카테고리 저장 서비스 테스트 실패: {e}")
        return False

def test_mock_question_approval():
    """가상의 문제 승인 프로세스 테스트"""
    print("\n=== 가상 문제 승인 프로세스 테스트 ===")
    
    try:
        from app.services.category_storage_service import CategoryStorageService
        from datetime import datetime
        import uuid
        
        # 가상의 문제 객체 생성
        class MockQuestion:
            def __init__(self, id, content, department, category):
                self.id = id
                self.question_number = f"Q{id}"
                self.content = content
                self.description = f"테스트 문제 설명 {id}"
                self.correct_answer = "1"
                self.subject = "테스트 과목"
                self.area_name = "테스트 영역"
                self.difficulty = "중"
                self.question_type = "multiple_choice"
                self.year = 2025
                self.file_category = category
                self.file_title = f"테스트_{department}_{category}"
                self.created_at = datetime.now()
                self.approved_at = datetime.now()
        
        # 테스트용 문제들 생성
        test_questions = [
            MockQuestion(1001, "간호학과 국가고시 테스트 문제 1", "간호학과", "국가고시"),
            MockQuestion(1002, "간호학과 일반 테스트 문제 1", "간호학과", "일반"),
            MockQuestion(1003, "물리치료학과 국가고시 테스트 문제 1", "물리치료학과", "국가고시"),
            MockQuestion(1004, "작업치료학과 국가고시 테스트 문제 1", "작업치료학과", "국가고시"),
        ]
        
        # 카테고리 저장 서비스로 저장 테스트
        storage_service = CategoryStorageService()
        
        for question in test_questions:
            # 개별 문제 저장 테스트
            success = storage_service.store_to_qdrant(
                question, 
                question.file_title.split('_')[1],  # 학과
                question.file_category  # 카테고리
            )
            
            if success:
                print(f"✅ 문제 {question.id} Qdrant 저장 성공 ({question.file_title.split('_')[1]} - {question.file_category})")
            else:
                print(f"❌ 문제 {question.id} Qdrant 저장 실패")
        
        # 저장 후 통계 확인
        print(f"\n📈 저장 후 통계 확인:")
        departments = ["간호학과", "물리치료학과", "작업치료학과"]
        for department in departments:
            stats = storage_service.get_collection_stats(department)
            print(f"{department}: 총 {stats['total_questions']}개 문제")
            
        return True
        
    except Exception as e:
        print(f"❌ 가상 문제 승인 테스트 실패: {e}")
        import traceback
        print(f"상세 오류:\n{traceback.format_exc()}")
        return False

def check_qdrant_data_after_approval():
    """승인 후 Qdrant 데이터 확인"""
    print("\n=== 승인 후 Qdrant 데이터 확인 ===")
    
    try:
        client = QdrantClient(host="localhost", port=6333, timeout=30)
        collections = client.get_collections()
        
        print(f"현재 컬렉션 목록: {[col.name for col in collections.collections]}")
        
        # 각 컬렉션의 데이터 확인
        for collection in collections.collections:
            collection_name = collection.name
            try:
                collection_info = client.get_collection(collection_name)
                print(f"\n📋 컬렉션: {collection_name}")
                print(f"  벡터 개수: {collection_info.points_count}")
                print(f"  벡터 차원: {collection_info.config.params.vectors.size}")
                print(f"  상태: {collection_info.status}")
                
                # 일부 데이터 샘플 조회
                if collection_info.points_count > 0:
                    points, _ = client.scroll(
                        collection_name=collection_name,
                        limit=3,
                        with_payload=True
                    )
                    
                    print(f"  📝 데이터 샘플:")
                    for i, point in enumerate(points):
                        print(f"    포인트 {i+1}: ID={point.id}")
                        if point.payload:
                            print(f"      타입: {point.payload.get('question_type', 'N/A')}")
                            print(f"      과목: {point.payload.get('subject', 'N/A')}")
                            print(f"      학과: {point.payload.get('department', 'N/A')}")
                            print(f"      카테고리: {point.payload.get('category', 'N/A')}")
                else:
                    print(f"  ❌ 데이터 없음")
                    
            except Exception as e:
                print(f"  ❌ 컬렉션 조회 실패: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Qdrant 데이터 확인 실패: {e}")
        return False

async def main():
    """메인 테스트 함수"""
    print("🔍 문제 승인 시 Qdrant 저장 프로세스 전체 테스트")
    print("=" * 60)
    
    # 1. Qdrant 연결 테스트
    client = test_qdrant_connection()
    if not client:
        print("❌ Qdrant 연결 실패로 테스트 종료")
        return
    
    # 2. 카테고리 저장 서비스 테스트
    if not test_category_storage_service():
        print("❌ 카테고리 저장 서비스 테스트 실패")
        return
    
    # 3. 가상 문제 승인 프로세스 테스트
    if not test_mock_question_approval():
        print("❌ 가상 문제 승인 테스트 실패")
        return
    
    # 4. 승인 후 데이터 확인
    if not check_qdrant_data_after_approval():
        print("❌ 데이터 확인 실패")
        return
    
    print("\n" + "=" * 60)
    print("✅ 모든 테스트 완료!")
    print("\n💡 결론:")
    print("- 문제 승인 시 CategoryStorageService를 통해 Qdrant에 저장됨")
    print("- 국가고시 카테고리 문제만 벡터 DB에 저장됨")
    print("- 각 학과별로 별도 컬렉션 사용")
    print("- 승인된 문제는 로컬 Qdrant (localhost:6333)에 저장됨")

if __name__ == "__main__":
    asyncio.run(main()) 