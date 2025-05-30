import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api"

def test_api(method, endpoint, headers=None, json_data=None, params=None):
    """API 테스트 헬퍼 함수"""
    url = f"{API_URL}{endpoint}"
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=json_data, params=params)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=json_data, params=params)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, params=params)
        
        print(f"  {method} {endpoint}: {response.status_code}")
        if response.status_code >= 400:
            print(f"    ERROR: {response.text[:200]}...")
        elif response.status_code < 300:
            print(f"    SUCCESS: {response.text[:100]}...")
        return response
    except Exception as e:
        print(f"  {method} {endpoint}: EXCEPTION - {str(e)}")
        return None

def main():
    print("=" * 60)
    print("CampusON API 종합 테스트")
    print("=" * 60)
    
    # 1. 기본 헬스체크
    print("\n1. 기본 API 테스트")
    test_api("GET", "/../health")
    test_api("GET", "/../")
    
    # 2. 인증 API 테스트
    print("\n2. 인증 API 테스트")
    
    # 로그인
    login_data = {
        'student_id': 'test123',
        'password': 'testpass123'
    }
    login_response = test_api("POST", "/auth/login-direct", json_data=login_data)
    
    access_token = None
    if login_response and login_response.status_code == 200:
        token_data = login_response.json()
        access_token = token_data.get('access_token')
    
    if access_token:
        headers = {'Authorization': f'Bearer {access_token}'}
        print(f"    토큰 획득 성공: {access_token[:50]}...")
        
        # 인증된 사용자 정보 조회
        test_api("GET", "/auth/me", headers=headers)
    else:
        print("    로그인 실패 - 토큰이 필요한 API 테스트 불가")
        headers = {}
    
    # 3. 대시보드 API 테스트
    print("\n3. 대시보드 API 테스트")
    if headers:
        test_api("GET", "/dashboard/student", headers=headers)
        test_api("GET", "/dashboard/progress", headers=headers)
        test_api("GET", "/dashboard/analytics", headers=headers)
        test_api("GET", "/dashboard/recommendations", headers=headers)
        test_api("GET", "/dashboard/study-plan", headers=headers)
        test_api("GET", "/dashboard/goal", headers=headers)
        
        # 목표 설정 테스트
        goal_data = {
            'target_level': 0.8,
            'target_date': '2025-12-31T00:00:00'
        }
        test_api("POST", "/dashboard/goal", headers=headers, params=goal_data)
    
    # 4. 진단 테스트 API
    print("\n4. 진단 테스트 API 테스트")
    if headers:
        test_api("GET", "/diagnosis/subjects", headers=headers)
        test_api("GET", "/diagnosis/history", headers=headers)
        
        # 진단 테스트 시작
        start_data = {'subject': 'computer_science'}
        test_api("POST", "/diagnosis/start", headers=headers, json_data=start_data)
    
    # 5. 문제 API 테스트
    print("\n5. 문제 API 테스트")
    if headers:
        test_api("GET", "/problems/recommended", headers=headers)
        test_api("GET", "/problems/subjects", headers=headers)
        
        # AI 문제 생성 테스트
        generate_data = {
            'subject': '데이터베이스',
            'difficulty': 2,
            'problem_type': 'multiple_choice',
            'context': '데이터베이스 기초 개념에 대한 문제입니다.'
        }
        test_api("POST", "/problems/generate", headers=headers, json_data=generate_data)
    
    # 6. 공개 API 테스트 (인증 불필요)
    print("\n6. 공개 API 테스트")
    test_api("GET", "/problems/subjects")  # 인증 없이 테스트
    
    print("\n" + "=" * 60)
    print("API 테스트 완료")
    print("=" * 60)

if __name__ == "__main__":
    main() 