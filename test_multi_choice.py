"""
1문제 30선택지 진단 테스트 테스트 스크립트
"""
import requests
import json
from datetime import datetime

# 서버 설정
BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api"

# 테스트 함수들
def test_server_health():
    """서버 상태 확인"""
    print("1. 서버 상태 확인")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            health_data = response.json()
            print(f"   ✅ 서버 상태: {health_data['status']}")
            return True
        else:
            print(f"   ❌ 서버 응답 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ 서버 연결 실패: {str(e)}")
        return False

def test_user_login():
    """테스트 사용자 로그인"""
    print("\n2. 테스트 사용자 인증")
    try:
        login_data = {
            "username": "test123",
            "password": "test123",
            "student_id": "2024001"  # 기존 등록된 사용자 ID
        }
        
        response = requests.post(f"{API_URL}/auth/login-direct", json=login_data)
        if response.status_code == 200:
            token_data = response.json()
            # user 객체에서 name 가져오기
            user_name = token_data.get('user', {}).get('name', token_data.get('user', {}).get('student_id', 'Unknown'))
            print(f"   ✅ 로그인 성공: {user_name}")
            return token_data['access_token']
        else:
            print(f"   ❌ 로그인 실패: {response.status_code}")
            print(f"      Response: {response.text}")
            return None
    except Exception as e:
        print(f"   ❌ 로그인 에러: {str(e)}")
        return None

def test_sample_multi_choice_test(token):
    """샘플 다중 선택지 테스트 생성"""
    print("\n3. 샘플 다중 선택지 테스트 생성")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{API_URL}/diagnosis/multi-choice/sample", headers=headers)
        if response.status_code == 200:
            test_data = response.json()
            print(f"   ✅ 다중 선택지 테스트 생성 성공: ID={test_data['test_session_id']}")
            print(f"   📝 문제: {test_data['question']['content']}")
            print(f"   🎯 선택지 개수: {len(test_data['choices'])}개")
            print(f"   ⏰ 제한 시간: {test_data['max_time_minutes']}분")
            
            # 첫 10개 선택지 출력
            print(f"\n   📋 선택지 샘플 (첫 10개):")
            for i, choice in enumerate(test_data['choices'][:10]):
                print(f"      {i+1:2d}. {choice}")
            print(f"      ... 총 {len(test_data['choices'])}개")
            
            return test_data
        else:
            print(f"   ❌ 테스트 생성 실패: Status {response.status_code}")
            print(f"      Response: {response.text}")
            return None
    except Exception as e:
        print(f"   ❌ 테스트 생성 에러: {str(e)}")
        return None

def test_submit_multi_choice_answer(token, test_data, selected_index=11, confidence="high"):
    """다중 선택지 답안 제출"""
    print(f"\n4. 다중 선택지 답안 제출 (선택: {selected_index+1}번)")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # 선택한 선택지 확인
        if 0 <= selected_index < len(test_data['choices']):
            selected_choice = test_data['choices'][selected_index]
            print(f"   🎯 선택한 답안: {selected_index+1}번 - '{selected_choice}'")
        else:
            print(f"   ❌ 유효하지 않은 선택지 인덱스: {selected_index}")
            return None
        
        # 답안 제출 데이터
        answer_data = {
            "test_session_id": test_data['test_session_id'],
            "selected_choice_index": selected_index,
            "selected_choice_content": selected_choice,
            "eliminated_choices": [0, 2, 4, 6, 8, 10],  # 몇 개 제거한 척
            "confidence_level": confidence,
            "time_spent_seconds": 150,
            "choice_timeline": [
                {"timestamp": 0, "action": "test_start"},
                {"timestamp": 30, "action": "elimination", "choices": [0, 2, 4]},
                {"timestamp": 60, "action": "elimination", "choices": [6, 8, 10]},
                {"timestamp": 120, "action": "selection_change", "choice": selected_index},
                {"timestamp": 150, "action": "final_submit"}
            ]
        }
        
        response = requests.post(f"{API_URL}/diagnosis/multi-choice/submit", json=answer_data, headers=headers)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ 답안 제출 성공!")
            print(f"   🎯 정답 여부: {'✅ 정답!' if result['is_correct'] else '❌ 오답'}")
            print(f"   📝 정답: {result['correct_choice']}")
            print(f"   ⏱️ 소요 시간: {result['time_spent_seconds']}초")
            print(f"   📊 확신도: {result['confidence_level']}")
            print(f"   🧠 학습 수준: {result['learning_level']:.3f}")
            
            # 전략 분석
            strategy = result['strategy_analysis']
            print(f"\n   🔍 선택 전략 분석:")
            print(f"      • 제거한 선택지: {strategy['elimination_count']}개")
            print(f"      • 제거 효과성: {strategy['elimination_effectiveness']:.3f}")
            print(f"      • 선택 변경: {strategy['choice_changes']}회")
            print(f"      • 전략 유형: {strategy['strategy_type']}")
            print(f"      • 의사결정 패턴: {strategy['decision_pattern']}")
            
            # 인지 능력 분석
            print(f"\n   🧠 인지 능력 분석:")
            for ability, score in result['cognitive_abilities'].items():
                print(f"      • {ability}: {score:.3f}")
            
            # 피드백
            print(f"\n   💬 피드백: {result['feedback_message']}")
            
            if result['recommended_skills']:
                print(f"   📚 추천 스킬: {', '.join(result['recommended_skills'])}")
            
            if result['improvement_areas']:
                print(f"   📈 개선 영역: {', '.join(result['improvement_areas'])}")
            
            return result
        else:
            print(f"   ❌ 답안 제출 실패: Status {response.status_code}")
            print(f"      Response: {response.text}")
            return None
    except Exception as e:
        print(f"   ❌ 답안 제출 에러: {str(e)}")
        return None

def test_quick_multi_choice(token, choice_index=11, confidence="high"):
    """빠른 다중 선택지 테스트"""
    print(f"\n5. 빠른 다중 선택지 테스트 (선택: {choice_index+1}번)")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        params = {
            "selected_choice_index": choice_index,
            "confidence_level": confidence,
            "time_spent_seconds": 120,
            "eliminated_choices": [0, 1, 2, 3, 4]  # 처음 5개 제거
        }
        
        response = requests.post(f"{API_URL}/diagnosis/multi-choice/quick-test", params=params, headers=headers)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ 빠른 테스트 성공!")
            print(f"   🎯 결과: {'✅ 정답!' if result['is_correct'] else '❌ 오답'}")
            print(f"   🧠 학습 수준: {result['learning_level']:.3f}")
            print(f"   📊 의사결정 품질: {result['decision_quality']:.3f}")
            return result
        else:
            print(f"   ❌ 빠른 테스트 실패: Status {response.status_code}")
            print(f"      Response: {response.text}")
            return None
    except Exception as e:
        print(f"   ❌ 빠른 테스트 에러: {str(e)}")
        return None

def test_different_strategies(token):
    """다양한 전략으로 테스트"""
    print("\n6. 다양한 전략으로 테스트")
    
    strategies = [
        {"choice": 11, "confidence": "high", "desc": "정답 + 높은 확신"},
        {"choice": 5, "confidence": "low", "desc": "오답 + 낮은 확신"},
        {"choice": 11, "confidence": "low", "desc": "정답 + 낮은 확신"},
        {"choice": 20, "confidence": "high", "desc": "오답 + 높은 확신"}
    ]
    
    results = []
    for i, strategy in enumerate(strategies):
        print(f"\n   📊 전략 {i+1}: {strategy['desc']}")
        result = test_quick_multi_choice(token, strategy['choice'], strategy['confidence'])
        if result:
            results.append({
                "strategy": strategy['desc'],
                "learning_level": result['learning_level'],
                "is_correct": result['is_correct'],
                "decision_quality": result['decision_quality']
            })
    
    if results:
        print(f"\n   📈 전략별 결과 비교:")
        for result in results:
            status = "✅" if result['is_correct'] else "❌"
            print(f"      {status} {result['strategy']}: 학습수준={result['learning_level']:.3f}, 의사결정품질={result['decision_quality']:.3f}")

def main():
    """메인 테스트 실행"""
    print("=" * 60)
    print("🎯 1문제 30선택지 진단 테스트")
    print("=" * 60)
    
    # 1. 서버 상태 확인
    if not test_server_health():
        return
    
    # 2. 사용자 로그인
    token = test_user_login()
    if not token:
        return
    
    # 3. 샘플 테스트 생성
    test_data = test_sample_multi_choice_test(token)
    if not test_data:
        return
    
    # 4. 답안 제출 (정답 선택)
    result = test_submit_multi_choice_answer(token, test_data, selected_index=11, confidence="high")
    
    # 5. 다양한 전략 테스트
    test_different_strategies(token)
    
    print("\n" + "=" * 60)
    print("🎉 1문제 30선택지 진단 테스트 완료!")
    print("=" * 60)

if __name__ == "__main__":
    main() 