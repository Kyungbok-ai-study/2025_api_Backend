#!/usr/bin/env python3
"""
문제 유형 자동 배정 통합 테스트
파서 시스템에서 엑셀 파일 처리 시 문제 유형이 자동으로 배정되는지 테스트
"""

import asyncio
import sys
import os
from pathlib import Path
import json

# 현재 디렉토리를 Python path에 추가
sys.path.append(str(Path(__file__).parent))

async def test_question_type_integration():
    """문제 유형 자동 배정 통합 테스트"""
    
    print("🚀 문제 유형 자동 배정 통합 테스트 시작")
    print("=" * 60)
    
    try:
        # QuestionParser 초기화
        from app.services.question_parser import QuestionParser
        
        # Gemini API 키 설정
        gemini_api_key = "AIzaSyAU_5m68cNAMIBn7m1uQPrYKNFR0oPO3QA"
        parser = QuestionParser(api_key=gemini_api_key)
        
        print("✅ QuestionParser 초기화 완료")
        
        # 1. 교수님 평가 데이터 디렉토리 확인
        evaluation_dir = Path("data/평가위원 수행결과")
        if not evaluation_dir.exists():
            print(f"❌ 평가 데이터 디렉토리가 없습니다: {evaluation_dir}")
            return
        
        print(f"📂 평가 데이터 디렉토리: {evaluation_dir}")
        
        # 2. 첫 번째 엑셀 파일 찾기
        excel_files = []
        for dept_dir in evaluation_dir.iterdir():
            if dept_dir.is_dir():
                for excel_file in dept_dir.glob("*.xlsx"):
                    excel_files.append(excel_file)
                    
        if not excel_files:
            print("❌ 테스트할 엑셀 파일이 없습니다.")
            return
        
        test_file = excel_files[0]
        print(f"📄 테스트 파일: {test_file}")
        
        # 3. 학과 정보 추출
        department = "일반"
        if "물리치료" in str(test_file):
            department = "물리치료학과"
        elif "작업치료" in str(test_file):
            department = "작업치료학과"
        
        print(f"🏥 학과: {department}")
        
        # 4. 파서로 엑셀 파일 처리 (문제 유형 자동 배정 포함)
        print(f"\n🔍 엑셀 파일 파싱 시작...")
        
        result = await parser.parse_any_file(
            str(test_file), 
            content_type="questions"
        )
        
        if result.get("error"):
            print(f"❌ 파싱 실패: {result['error']}")
            return
        
        parsed_data = result.get("data", [])
        print(f"✅ 파싱 완료: {len(parsed_data)}개 문제")
        
        # 5. 문제 유형 배정 결과 분석
        print(f"\n📊 문제 유형 배정 결과 분석:")
        print("-" * 40)
        
        type_counts = {}
        type_examples = {}
        
        for i, question in enumerate(parsed_data[:5]):  # 처음 5개만 상세 분석
            qnum = question.get('question_number', i+1)
            qtype = question.get('question_type', 'unknown')
            type_name = question.get('type_name', qtype)
            
            # content 안전하게 처리
            raw_content = question.get('content', '') or ''
            content = raw_content[:100] + "..." if len(raw_content) > 100 else raw_content
            
            # 카운트 집계
            if qtype not in type_counts:
                type_counts[qtype] = 0
                type_examples[qtype] = []
            type_counts[qtype] += 1
            
            if len(type_examples[qtype]) < 2:  # 각 유형별 최대 2개 예시
                type_examples[qtype].append({
                    "number": qnum,
                    "content": content
                })
            
            print(f"문제 {qnum}: {type_name} ({qtype})")
            print(f"   내용: {content}")
            print()
        
        # 전체 문제 유형 통계
        print("📈 전체 문제 유형 분포:")
        print("-" * 40)
        
        total_questions = len(parsed_data)
        for qtype, count in type_counts.items():
            from app.services.question_type_mapper import question_type_mapper
            type_name = question_type_mapper.question_types.get(qtype, {}).get('name', qtype)
            percentage = (count / total_questions) * 100 if total_questions > 0 else 0
            print(f"- {type_name}: {count}개 ({percentage:.1f}%)")
            
            # 예시 출력
            for example in type_examples.get(qtype, []):
                print(f"  예시 {example['number']}: {example['content']}")
        
        # 6. 문제 유형 매핑 요약 정보 출력
        print(f"\n🎯 문제 유형 매핑 시스템 현황:")
        print("-" * 40)
        
        from app.services.question_type_mapper import question_type_mapper
        summary = question_type_mapper.get_type_mapping_summary()
        
        print(f"- 전체 처리 파일: {summary['total_files']}개")
        print(f"- 전체 문제 수: {summary['total_questions']}개")
        print(f"- 신뢰도 분석:")
        conf_analysis = summary.get('confidence_analysis', {})
        print(f"  · 고신뢰도 (≥80%): {conf_analysis.get('high_confidence', 0)}개")
        print(f"  · 중신뢰도 (50-80%): {conf_analysis.get('medium_confidence', 0)}개")
        print(f"  · 저신뢰도 (<50%): {conf_analysis.get('low_confidence', 0)}개")
        
        print(f"\n✅ 문제 유형 자동 배정 통합 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

async def main():
    await test_question_type_integration()

if __name__ == "__main__":
    asyncio.run(main()) 