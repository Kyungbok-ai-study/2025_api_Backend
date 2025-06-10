#!/usr/bin/env python3
"""
딥시크 AI 분석기 테스트
"""
from app.services.ai_difficulty_analyzer import DifficultyAnalyzer

def test_deepseek():
    print("🤖 딥시크 분석기 테스트 시작")
    
    # 분석기 초기화
    analyzer = DifficultyAnalyzer()
    
    # 테스트 문제
    question = "근육의 수축 형태 중 등장성 수축에 대한 설명으로 옳은 것은? 1. 근육의 길이는 변하지 않는다 2. 근육의 장력이 일정하다 3. 관절의 움직임이 없다 4. 근육의 혈류가 차단된다"
    
    print(f"📝 분석할 문제: {question[:50]}...")
    
    # AI 분석 실행
    result = analyzer.analyze_question_auto(question, 1, "물리치료")
    
    print("\n✅ 딥시크 분석 결과:")
    print(f"  난이도: {result.get('difficulty', '없음')}")
    print(f"  문제유형: {result.get('question_type', '없음')}")
    print(f"  분석근거: {result.get('ai_reasoning', '없음')}")
    print(f"  위치기반예측: {result.get('position_based', '없음')}")
    print(f"  AI추천: {result.get('ai_suggested', '없음')}")
    print(f"  신뢰도: {result.get('confidence', '없음')}")
    
    return result

if __name__ == "__main__":
    test_deepseek() 