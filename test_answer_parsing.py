#!/usr/bin/env python3
"""
답안지 파싱 테스트
"""
import asyncio
from app.services.question_parser import QuestionParser

async def test_answer_parsing():
    print("🔍 답안지 파싱 테스트 시작")
    
    # 실제 답안지 파일 경로 (가장 최근 업로드된 파일)
    answer_file = "uploads/questions/2024년도 제52회 물리치료사 국가시험 1~2교시 최종답안.pdf"
    
    try:
        # QuestionParser 초기화
        gemini_api_key = "AIzaSyAU_5m68cNAMIBn7m1uQPrYKNFR0oPO3QA"
        parser = QuestionParser(api_key=gemini_api_key)
        
        print(f"📄 답안지 파일 분석: {answer_file}")
        
        # 답안지로 파싱
        result = await parser.parse_any_file(answer_file, "answers")
        
        print(f"📊 파싱 결과:")
        print(f"  - 타입: {result.get('type')}")
        print(f"  - 데이터 개수: {len(result.get('data', []))}")
        
        # 처음 5개 답안 출력
        data = result.get('data', [])
        for i, item in enumerate(data[:5]):
            q_num = item.get('question_number', '?')
            answer = item.get('correct_answer', '없음')
            print(f"  - {q_num}번: {answer}")
        
        # 정답이 있는 문제 개수
        answered = len([d for d in data if d.get('correct_answer')])
        print(f"📈 정답이 있는 문제: {answered}개 / {len(data)}개")
        
        return data
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return []

if __name__ == "__main__":
    asyncio.run(test_answer_parsing()) 