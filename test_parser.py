#!/usr/bin/env python3
"""
PDF 파싱 기능 테스트 스크립트
"""
import os
import sys
import json
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent))

from app.services.question_parser import QuestionParser

def test_pdf_parsing():
    """PDF 파싱 테스트"""
    print("PDF 파싱 테스트 시작")
    
    # 테스트할 파일들
    test_files = [
        "uploads/questions/TEST_20250609_021530_0_2021년도 제49회 물리치료사 국가시험 1교시 기출문제.pdf",
        "uploads/questions/TEST_20250609_021530_1_2021년도 제49회 물리치료사 국가시험 1~2교시 최종답안.pdf"
    ]
    
    parser = QuestionParser()
    
    for file_path in test_files:
        if not os.path.exists(file_path):
            print(f"파일 없음: {file_path}")
            continue
            
        print(f"\n파싱 테스트: {Path(file_path).name}")
        
        # 파일 타입 결정
        if "기출문제" in file_path or "1교시" in file_path:
            content_type = "questions"
            print("   문제지로 인식")
        else:
            content_type = "answers"
            print("   정답지로 인식")
        
        try:
            # 파싱 실행 (새 파서는 동기 방식)
            result = parser.parse_any_file(file_path, content_type)
            
            print(f"   결과: {result.get('type', 'unknown')} 타입")
            data = result.get('data', [])
            print(f"   파싱된 데이터 개수: {len(data)}")
            
            if data:
                # 첫 번째 항목 상세 출력
                first_item = data[0]
                print(f"   첫 번째 항목:")
                print(f"     - 문제번호: {first_item.get('question_number')}")
                print(f"     - 내용: {first_item.get('content', 'None')[:100]}...")
                print(f"     - 선택지: {bool(first_item.get('options'))}")
                print(f"     - 정답: {first_item.get('correct_answer', 'None')}")
                
                # 5개 항목까지 요약 출력
                print(f"   처음 5개 항목 요약:")
                for i, item in enumerate(data[:5]):
                    content_preview = item.get('content', '')
                    if content_preview:
                        content_preview = content_preview[:50] + "..." if len(content_preview) > 50 else content_preview
                    else:
                        content_preview = "내용 없음"
                    
                    print(f"     {i+1}. 문제{item.get('question_number', '?')}: {content_preview}")
                    print(f"        정답: {item.get('correct_answer', 'None')}, 선택지: {len(item.get('options', {}))}")
            else:
                print("   파싱된 데이터 없음")
                if 'error' in result:
                    print(f"   오류: {result['error']}")
                    
        except Exception as e:
            print(f"   파싱 실패: {e}")
            import traceback
            print(f"   스택 트레이스: {traceback.format_exc()}")

if __name__ == "__main__":
    test_pdf_parsing() 