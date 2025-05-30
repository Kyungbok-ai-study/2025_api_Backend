"""
테스트 사용자 생성 스크립트
"""
import requests
import json

def create_test_user():
    """테스트 사용자 생성"""
    url = "http://localhost:8000/api/auth/register"
    
    user_data = {
        "school": "경복대학교",
        "student_id": "2024001",
        "name": "테스트사용자",
        "email": "test@test.com",
        "password": "test123",
        "department": "컴퓨터공학과",
        "role": "student"
    }
    
    print("테스트 사용자 등록 중...")
    print(f"학번: {user_data['student_id']}")
    print(f"이름: {user_data['name']}")
    
    response = requests.post(url, json=user_data)
    
    if response.status_code == 200:
        print("✅ 사용자 등록 성공!")
        print(f"응답: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"❌ 사용자 등록 실패: {response.status_code}")
        print(f"에러: {response.text}")
        
        # 이미 존재하는 경우 로그인 테스트
        if "이미 등록된" in response.text:
            print("\n로그인 테스트...")
            login_url = "http://localhost:8000/api/auth/login-direct"
            login_data = {
                "student_id": user_data["student_id"],
                "password": user_data["password"]
            }
            login_response = requests.post(login_url, json=login_data)
            if login_response.status_code == 200:
                print("✅ 로그인 성공! 기존 사용자가 존재합니다.")
            else:
                print(f"❌ 로그인도 실패: {login_response.status_code}")
                print(f"에러: {login_response.text}")

if __name__ == "__main__":
    create_test_user() 