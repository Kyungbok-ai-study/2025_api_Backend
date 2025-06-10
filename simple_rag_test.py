#!/usr/bin/env python3
"""
기존 RAG 시스템 간단 테스트
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_server():
    """서버 기본 상태 확인"""
    print("🌐 서버 기본 상태 확인")
    print("=" * 30)
    
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            data = response.json()
            print("✅ 서버 연결 성공")
            print(f"📦 프로젝트: {data.get('project', 'N/A')}")
            print(f"🔢 버전: {data.get('version', 'N/A')}")
            print(f"📄 문서: {data.get('docs', 'N/A')}")
            print(f"💚 상태: {data.get('status', 'N/A')}")
            return True
        else:
            print(f"❌ 서버 연결 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 서버 연결 오류: {e}")
        return False

def test_api_endpoints():
    """API 엔드포인트 테스트"""
    print("\n🔍 API 엔드포인트 테스트")
    print("=" * 30)
    
    # 테스트할 엔드포인트들
    endpoints = [
        "/health",
        "/docs", 
        "/openapi.json",
        "/rag/statistics",
        "/advanced-rag/system-status",
        "/enterprise-rag/system-status"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}")
            if response.status_code == 200:
                print(f"✅ {endpoint}: 성공")
            elif response.status_code == 401:
                print(f"🔒 {endpoint}: 인증 필요")
            elif response.status_code == 404:
                print(f"❌ {endpoint}: 없음")
            else:
                print(f"⚠️ {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint}: 연결 오류")

def check_available_paths():
    """사용 가능한 API 경로 확인"""
    print("\n📋 사용 가능한 API 경로 확인")
    print("=" * 30)
    
    try:
        response = requests.get(f"{BASE_URL}/openapi.json")
        if response.status_code == 200:
            data = response.json()
            paths = list(data.get('paths', {}).keys())
            print(f"총 {len(paths)}개 경로 발견:")
            
            # RAG 관련 경로만 필터링
            rag_paths = [p for p in paths if 'rag' in p.lower()]
            if rag_paths:
                print("\n🤖 RAG 관련 경로:")
                for path in rag_paths:
                    print(f"  {path}")
            else:
                print("❌ RAG 관련 경로 없음")
                
            # 일반 경로 일부 표시
            print(f"\n📝 기타 경로 (처음 10개):")
            for path in paths[:10]:
                print(f"  {path}")
                
        else:
            print("❌ OpenAPI 스키마 로드 실패")
            
    except Exception as e:
        print(f"❌ API 경로 확인 오류: {e}")

def test_rag_without_auth():
    """인증 없이 RAG 기능 테스트"""
    print("\n🧪 RAG 기능 테스트 (인증 없음)")
    print("=" * 30)
    
    # 테스트 쿼리
    test_query = "간호학과 학습 내용"
    
    # 기본 RAG 테스트
    try:
        payload = {"query": test_query}
        response = requests.post(f"{BASE_URL}/rag/search", json=payload)
        print(f"기본 RAG 검색: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  결과: {len(data.get('results', []))}개")
        elif response.status_code == 401:
            print("  인증이 필요한 엔드포인트")
        elif response.status_code == 404:
            print("  엔드포인트 없음")
            
    except Exception as e:
        print(f"  오류: {e}")

def main():
    """메인 테스트 함수"""
    print("🏢 RAG 시스템 현황 간단 테스트")
    print("=" * 50)
    
    # 1. 서버 상태 확인
    if not test_server():
        print("❌ 서버 연결 실패로 테스트 중단")
        return
    
    # 2. API 엔드포인트 테스트
    test_api_endpoints()
    
    # 3. 사용 가능한 경로 확인
    check_available_paths()
    
    # 4. RAG 기능 테스트
    test_rag_without_auth()
    
    print("\n" + "=" * 50)
    print("🎯 테스트 완료!")
    print("\n💡 현재 상황:")
    print("• 서버는 정상 실행 중")
    print("• 일부 RAG 엔드포인트는 인증 필요")
    print("• 새로운 엔터프라이즈 RAG는 등록 확인 필요")

if __name__ == "__main__":
    main() 