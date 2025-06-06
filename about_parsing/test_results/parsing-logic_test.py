"""
전체 데이터 파싱 및 매칭 테스트 (수정된 버전)
각 연도별 시트를 개별적으로 처리하여 올바른 매칭 구현
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime
import time

# 프로젝트 루트를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

print("🚀 전체 데이터 파싱 및 매칭 테스트 (수정 버전)")
print("="*70)

try:
    from app.services.question_parser import QuestionParser
    
    # 데이터 경로
    data_dir = Path("data/question_data/4개년도(49회-52회)물리치료국가고시 1교시 기출+답안")
    
    # 파일 경로 설정
    answer_file = data_dir / "물리치료 라벨링 결과.xlsx"
    
    # 연도별 문제 파일과 시트 매핑
    year_files = {
        2021: {
            "pdf": data_dir / "2021년도 제49회 물리치료사 국가시험 1교시 기출문제.pdf",
            "sheet": "2021 물리치료"
        },
        2022: {
            "pdf": data_dir / "2022년도 제50회 물리치료사 국가시험 1교시 기출문제.pdf", 
            "sheet": "2022 물리치료"
        },
        2023: {
            "pdf": data_dir / "2023년도 제51회 물리치료사 국가시험 1교시 기출문제.pdf",
            "sheet": "2023 물리치료"
        },
        2024: {
            "pdf": data_dir / "2024년도 제52회 물리치료사 국가시험 1교시 기출문제.pdf",
            "sheet": "2024 물리치료"
        }
    }
    
    print(f"✅ 파서 임포트 성공")
    
    # 파서 초기화
    parser = QuestionParser()
    print(f"✅ 파서 초기화 성공")
    
    # 결과 저장용
    all_results = {
        "metadata": {
            "test_timestamp": datetime.now().isoformat(),
            "total_files_processed": len(year_files),
            "parser_version": "new_schema_v1.1_fixed"
        },
        "years": {}
    }
    
    start_time = time.time()
    
    # 연도별 개별 처리
    total_questions = 0
    total_matched = 0
    
    for year, files in year_files.items():
        print(f"\n📝 {year}년도 처리 중...")
        print(f"PDF: {files['pdf'].name}")
        print(f"시트: {files['sheet']}")
        
        if not files['pdf'].exists():
            print(f"❌ PDF 파일이 존재하지 않습니다: {files['pdf']}")
            continue
        
        try:
            # 1. 해당 연도 문제 파싱
            question_result = parser.parse_any_file(str(files['pdf']), "questions")
            questions = question_result.get("data", [])
            
            print(f"✅ 문제 파싱 완료: {len(questions)}개 문제")
            total_questions += len(questions)
            
            if not questions:
                print(f"⚠️ 파싱된 문제가 없습니다.")
                continue
            
            # 2. 해당 연도 정답 파싱 (특정 시트만)
            import pandas as pd
            try:
                df = pd.read_excel(str(answer_file), sheet_name=files['sheet'])
                print(f"✅ 시트 '{files['sheet']}' 읽기 성공: {len(df)}행")
                
                # 데이터 정리 및 파싱
                # 첫 번째 행은 헤더이므로 스킵
                if len(df) > 1:
                    answer_data = []
                    for idx, row in df.iloc[1:].iterrows():  # 첫 번째 행 스킵
                        try:
                            # 컬럼 순서에 따라 데이터 추출
                            cols = list(row.values)
                            if len(cols) >= 4:
                                question_num = cols[2]  # 문제번호
                                correct_ans = cols[3]   # 정답
                                difficulty = cols[4] if len(cols) > 4 else "중"  # 난이도
                                
                                # 유효한 데이터만 추가
                                if question_num and str(question_num).strip() and question_num != '문제번호':
                                    answer_data.append({
                                        "question_number": int(float(question_num)) if str(question_num).replace('.', '').isdigit() else int(question_num),
                                        "correct_answer": str(correct_ans) if correct_ans else "",
                                        "subject": "물리치료 기초",
                                        "area_name": "",
                                        "difficulty": str(difficulty) if difficulty else "중",
                                        "year": year
                                    })
                        except Exception as e:
                            continue  # 잘못된 행은 스킵
                    
                    print(f"✅ 정답 파싱 완료: {len(answer_data)}개 정답")
                    
                    # 3. 문제-정답 매칭
                    if answer_data:
                        matched_data = parser.match_questions_with_answers(questions, answer_data)
                        print(f"✅ 매칭 완료: {len(matched_data)}개 완전한 문제")
                        total_matched += len(matched_data)
                    else:
                        print(f"⚠️ 파싱된 정답이 없어 매칭 불가")
                        matched_data = questions
                else:
                    print(f"⚠️ 시트에 데이터가 없습니다.")
                    matched_data = questions
                    answer_data = []
                    
            except Exception as e:
                print(f"❌ 시트 처리 실패: {e}")
                matched_data = questions
                answer_data = []
            
            # 4. 연도별 결과 저장
            all_results["years"][str(year)] = {
                "year": year,
                "file_name": files['pdf'].name,
                "sheet_name": files['sheet'],
                "questions_count": len(questions),
                "answers_count": len(answer_data) if 'answer_data' in locals() else 0,
                "matched_count": len(matched_data) if answer_data else 0,
                "questions": matched_data
            }
            
        except Exception as e:
            print(f"❌ {year}년도 처리 실패: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # 5. 최종 결과 저장
    print(f"\n💾 최종 결과 JSON 생성 중...")
    
    # 결과 디렉토리 생성
    results_dir = Path("test_results")
    results_dir.mkdir(exist_ok=True)
    
    # 전체 통계 추가
    all_results["metadata"]["statistics"] = {
        "total_questions_parsed": total_questions,
        "total_questions_matched": total_matched,
        "matching_rate": f"{(total_matched/total_questions*100):.1f}%" if total_questions > 0 else "0%",
        "years_processed": len(all_results["years"]),
        "processing_time": f"{time.time() - start_time:.2f}초"
    }
    
    # JSON 파일로 저장
    output_file = results_dir / f"final_parsing_result_fixed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 결과 저장 완료: {output_file}")
    
    # 6. 결과 요약 출력
    print(f"\n" + "="*70)
    print(f"📈 최종 테스트 결과 요약 (수정 버전)")
    print(f"="*70)
    
    print(f"\n📊 전체 통계:")
    print(f"  - 처리된 연도: {len(all_results['years'])}개")
    print(f"  - 총 문제 수: {total_questions}개")
    print(f"  - 총 매칭 수: {total_matched}개")
    print(f"  - 매칭 성공률: {(total_matched/total_questions*100):.1f}%" if total_questions > 0 else "0%")
    print(f"  - 처리 시간: {time.time() - start_time:.2f}초")
    
    print(f"\n📅 연도별 상세:")
    for year_key, year_data in all_results["years"].items():
        year = year_data["year"]
        questions = year_data["questions_count"] 
        matched = year_data["matched_count"]
        rate = f"{(matched/questions*100):.1f}%" if questions > 0 else "0%"
        print(f"  - {year}년: {questions}개 문제 → {matched}개 매칭 ({rate})")
    
    # 스키마 검증
    print(f"\n🔍 스키마 검증:")
    sample_year = list(all_results["years"].values())[0] if all_results["years"] else None
    if sample_year and sample_year["questions"]:
        sample_question = sample_year["questions"][0]
        required_fields = ["question_number", "content", "options", "correct_answer", "subject", "area_name", "difficulty", "year"]
        
        for field in required_fields:
            value = sample_question.get(field)
            status = "✅" if value is not None else "❌"
            print(f"  - {field}: {status} ({value})" if field in ["difficulty", "area_name"] else f"  - {field}: {status}")
    
    print(f"\n📁 결과 파일 위치:")
    print(f"  {output_file.absolute()}")
    
    print(f"\n🎉 전체 테스트 완료! 위 JSON 파일을 확인하세요.")
    
except Exception as e:
    print(f"❌ 전체 테스트 실패: {e}")
    import traceback
    traceback.print_exc() 