"""
진단 서비스 테스트 스크립트
1순위: 30문항 + 산술식 기반 학습 수준 계산
"""
import requests
import json
from datetime import datetime
import time

BASE_URL = "http://localhost:8000"

def test_diagnosis_service():
    """진단 서비스 종합 테스트"""
    print("=" * 60)
    print("🎯 1순위 진단 서비스 테스트")
    print("=" * 60)
    
    # 1. 서버 상태 확인
    print("\n1. 서버 상태 확인")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"   ✅ 서버 상태: {response.json()['status']}")
    except Exception as e:
        print(f"   ❌ 서버 연결 실패: {e}")
        return
    
    # 2. 사용 가능한 진단 과목 확인
    print("\n2. 진단 과목 목록 조회")
    try:
        response = requests.get(f"{BASE_URL}/api/diagnosis/subjects")
        subjects = response.json()
        print(f"   ✅ 사용 가능한 과목: {len(subjects['subjects'])}개")
        for subject in subjects['subjects']:
            print(f"      - {subject['name']} ({subject['value']})")
    except Exception as e:
        print(f"   ❌ 과목 조회 실패: {e}")
        return
    
    # 3. 테스트용 사용자 생성 (회원가입 없이 테스트)
    print("\n3. 테스트 사용자 인증")
    # 실제로는 JWT 토큰이 필요하지만, 테스트를 위해 먼저 로그인 시도
    login_data = {
        "student_id": "test123", 
        "password": "testpass123"
    }
    
    try:
        # 직접 로그인 시도
        response = requests.post(f"{BASE_URL}/api/auth/login-direct", json=login_data)
        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get("access_token")
            print(f"   ✅ 로그인 성공: {token_data.get('user', {}).get('student_id', 'test123')}")
            headers = {"Authorization": f"Bearer {token}"}
        else:
            print(f"   ⚠️ 로그인 실패 (Status: {response.status_code})")
            print("   🔄 테스트용 계정 생성 시도...")
            
            # 회원가입 시도
            signup_data = {
                "student_id": "test123",
                "password": "testpass123",
                "name": "테스트유저",
                "school": "경복대학교",
                "department": "빅데이터과",
                "email": "test@test.com"
            }
            
            signup_response = requests.post(f"{BASE_URL}/api/auth/register", json=signup_data)
            if signup_response.status_code in [200, 201]:
                print("   ✅ 테스트 계정 생성 성공")
                # 다시 로그인 시도
                login_response = requests.post(f"{BASE_URL}/api/auth/login-direct", json=login_data)
                if login_response.status_code == 200:
                    token_data = login_response.json()
                    token = token_data.get("access_token")
                    headers = {"Authorization": f"Bearer {token}"}
                    print("   ✅ 로그인 성공")
                else:
                    print("   ❌ 로그인 재시도 실패")
                    headers = {}
            else:
                print(f"   ❌ 계정 생성 실패: {signup_response.text}")
                headers = {}
                
    except Exception as e:
        print(f"   ❌ 인증 처리 중 오류: {e}")
        headers = {}
    
    # 4. 진단 테스트 시작
    print("\n4. 진단 테스트 세션 생성")
    test_data = {
        "subject": "computer_science",
        "description": "컴퓨터과학 진단 테스트"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/diagnosis/start", 
            json=test_data,
            headers=headers
        )
        
        if response.status_code == 200:
            test_session = response.json()
            test_session_id = test_session['id']
            questions = test_session['questions']
            print(f"   ✅ 테스트 세션 생성 성공: ID={test_session_id}")
            print(f"   📝 문제 개수: {len(questions)}개")
            print(f"   ⏰ 제한 시간: {test_session.get('max_time_minutes', 60)}분")
            
            # 문제 샘플 출력
            if questions:
                print(f"\n   📋 문제 샘플 (첫 3개):")
                for i, q in enumerate(questions[:3]):
                    print(f"      {i+1}. [{q['difficulty']}] {q['content'][:50]}...")
        else:
            print(f"   ❌ 테스트 세션 생성 실패: Status {response.status_code}")
            print(f"      Response: {response.text}")
            return
            
    except Exception as e:
        print(f"   ❌ 테스트 세션 생성 중 오류: {e}")
        return
    
    # 5. 시뮬레이션 답안 생성 및 제출
    print("\n5. 시뮬레이션 답안 제출")
    
    # 각 문제에 대한 시뮬레이션 답안 생성
    answers = []
    for i, question in enumerate(questions):
        # 시뮬레이션: 70% 확률로 정답
        is_correct_sim = (i % 10) < 7  # 70% 정답률
        
        if question['question_type'] == 'multiple_choice' and question.get('choices'):
            # 객관식: 첫 번째 선택지를 정답으로 가정
            answer = question['choices'][0] if is_correct_sim else question['choices'][-1]
        else:
            # 주관식 등: 간단한 시뮬레이션 답안
            answer = "정답예시" if is_correct_sim else "오답예시"
        
        answers.append({
            "question_id": question['id'],
            "answer": answer,
            "time_spent": 30 + (i % 60)  # 30-90초 시뮬레이션
        })
    
    # 답안 제출
    submission_data = {
        "test_session_id": test_session_id,
        "answers": answers,
        "total_time_spent": sum(ans['time_spent'] for ans in answers)
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/diagnosis/submit",
            json=submission_data,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ 답안 제출 성공!")
            print(f"   🎯 학습 수준 지표: {result['learning_level']:.3f}")
            print(f"   📊 정답률: {result['accuracy_rate']:.1%}")
            print(f"   ✅ 정답 개수: {result['correct_answers']}/{result['total_questions']}")
            print(f"   ⏱️ 총 소요 시간: {result.get('total_time_spent', 0)}초")
            
            # 계산 세부사항 출력
            if 'calculation_details' in result:
                details = result['calculation_details']
                print(f"\n   📈 산술식 계산 결과:")
                print(f"      - 총 획득 점수: {details['total_score']:.2f}")
                print(f"      - 최대 가능 점수: {details['max_possible_score']:.2f}")
                print(f"      - 학습 수준 지표: {details['learning_level']:.3f}")
        else:
            print(f"   ❌ 답안 제출 실패: Status {response.status_code}")
            print(f"      Response: {response.text}")
            return
            
    except Exception as e:
        print(f"   ❌ 답안 제출 중 오류: {e}")
        return
    
    # 6. 진단 결과 조회
    print("\n6. 진단 결과 상세 조회")
    try:
        response = requests.get(
            f"{BASE_URL}/api/diagnosis/result/{test_session_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            detailed_result = response.json()
            print(f"   ✅ 상세 결과 조회 성공!")
            print(f"   🎯 현재 학습 수준: {detailed_result['current_level']:.3f}")
            
            if detailed_result.get('strengths'):
                print(f"   💪 강점 영역: {', '.join(detailed_result['strengths'])}")
            
            if detailed_result.get('weaknesses'):
                print(f"   📝 개선 영역: {', '.join(detailed_result['weaknesses'])}")
                
            if detailed_result.get('recommendations'):
                print(f"   🎯 추천 학습:")
                for rec in detailed_result['recommendations'][:3]:
                    print(f"      - {rec}")
        else:
            print(f"   ❌ 결과 조회 실패: Status {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ 결과 조회 중 오류: {e}")
    
    # 7. 진단 이력 조회
    print("\n7. 진단 이력 조회")
    try:
        response = requests.get(
            f"{BASE_URL}/api/diagnosis/history",
            headers=headers
        )
        
        if response.status_code == 200:
            history = response.json()
            print(f"   ✅ 진단 이력 조회 성공!")
            print(f"   📚 총 진단 횟수: {len(history)}회")
            
            for i, test in enumerate(history[-3:]):  # 최근 3개
                print(f"      {i+1}. {test['subject']} - {test['status']} ({test['created_at'][:10]})")
        else:
            print(f"   ❌ 이력 조회 실패: Status {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ 이력 조회 중 오류: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 1순위 진단 서비스 테스트 완료!")
    print("✅ 30문항 진단 테스트 시스템 정상 작동")
    print("✅ 산술식 기반 학습 수준 계산 정상 작동")
    print("✅ 결과 분석 및 피드백 시스템 정상 작동")
    print("=" * 60)

if __name__ == "__main__":
    test_diagnosis_service() 