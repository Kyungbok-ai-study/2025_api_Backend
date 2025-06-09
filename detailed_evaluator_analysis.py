"""
평가위원별 상세 분석 시스템
각 평가위원의 개별 년도별 22문제 난이도와 유형 분석
"""
import pandas as pd
import json
import os
from pathlib import Path
import re
from collections import defaultdict

class DetailedEvaluatorAnalysis:
    """평가위원별 상세 분석"""
    
    def __init__(self):
        self.data_dir = Path("data/평가위원 수행결과")
        self.evaluators = {
            "물리치료": [],
            "작업치료": []
        }
        self.detailed_analysis = {}
        
    def extract_evaluator_names(self):
        """평가위원 이름 추출"""
        departments = {"물리치료": "평가위원 수행결과_물리치료", "작업치료": "평가위원 수행결과_작업치료"}
        
        for dept, folder in departments.items():
            dept_dir = self.data_dir / folder
            if dept_dir.exists():
                for excel_file in dept_dir.glob("*.xlsx"):
                    # 파일명에서 평가위원 이름 정확히 추출
                    file_name = excel_file.name
                    print(f"파일명 분석: {file_name}")
                    
                    # "2. 이름_학과_마스터코딩지.xlsx" 형태에서 이름 추출
                    match = re.match(r'2\.\s*([^_]+)_', file_name)
                    if match:
                        evaluator_name = match.group(1).strip()
                        self.evaluators[dept].append({
                            "name": evaluator_name,
                            "file_path": excel_file,
                            "department": dept
                        })
                        print(f"  -> 추출된 이름: {evaluator_name}")
                    else:
                        print(f"  -> 이름 추출 실패")
        
        print(f"\n📋 추출된 평가위원:")
        for dept, evaluators in self.evaluators.items():
            print(f"  {dept}학과: {len(evaluators)}명")
            for eval_info in evaluators:
                print(f"    - {eval_info['name']}")
    
    def analyze_individual_evaluator(self, evaluator_info):
        """개별 평가위원 상세 분석"""
        name = evaluator_info["name"]
        file_path = evaluator_info["file_path"]
        department = evaluator_info["department"]
        
        print(f"\n👨‍🏫 {name} ({department}학과) 분석 중...")
        
        try:
            excel_file = pd.ExcelFile(file_path)
            
            evaluator_data = {
                "name": name,
                "department": department,
                "file_name": file_path.name,
                "years_analysis": {},
                "overall_stats": {
                    "total_questions": 0,
                    "difficulty_distribution": {},
                    "question_type_distribution": {},
                    "subject_distribution": {}
                }
            }
            
            # 각 년도별 분석
            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    
                    # 년도 추출
                    year_match = re.search(r'(\d{4})', sheet_name)
                    year = year_match.group(1) if year_match else sheet_name
                    
                    print(f"  📅 {year}년도: {len(df)}문제")
                    
                    # 년도별 상세 분석
                    year_analysis = self.analyze_year_data(df, year, department)
                    evaluator_data["years_analysis"][year] = year_analysis
                    
                    # 전체 통계에 합산
                    self.merge_stats(evaluator_data["overall_stats"], year_analysis)
                    
                except Exception as e:
                    print(f"    ❌ {sheet_name} 분석 실패: {e}")
                    continue
            
            return evaluator_data
            
        except Exception as e:
            print(f"  ❌ 파일 분석 실패: {e}")
            return None
    
    def analyze_year_data(self, df, year, department):
        """년도별 데이터 상세 분석"""
        # 컬럼명 정리
        df.columns = [str(col).strip() for col in df.columns]
        
        analysis = {
            "year": year,
            "total_questions": len(df),
            "questions": [],
            "difficulty_stats": {},
            "question_type_stats": {},
            "subject_stats": {},
            "difficulty_by_question": {}
        }
        
        # 각 문제별 분석
        for idx, row in df.iterrows():
            try:
                question_data = {
                    "question_number": self.safe_get(row, ["문제번호", "번호"]),
                    "difficulty": self.safe_get(row, ["난이도"]),
                    "subject": self.safe_get(row, ["과목"]),
                    "answer": self.safe_get(row, ["답안"]),
                    "field_name": self.safe_get(row, ["분야이름"]),
                    "area_name": self.safe_get(row, ["영역이름"])
                }
                
                # 유효한 데이터만 추가
                if question_data["question_number"] and question_data["difficulty"]:
                    analysis["questions"].append(question_data)
                    
                    # 통계 업데이트
                    q_num = str(question_data["question_number"]).strip()
                    difficulty = str(question_data["difficulty"]).strip()
                    subject = str(question_data["subject"]).strip() if question_data["subject"] else "미분류"
                    
                    # 문제번호별 난이도 매핑
                    analysis["difficulty_by_question"][q_num] = difficulty
                    
                    # 난이도 통계
                    analysis["difficulty_stats"][difficulty] = analysis["difficulty_stats"].get(difficulty, 0) + 1
                    
                    # 과목 통계
                    analysis["subject_stats"][subject] = analysis["subject_stats"].get(subject, 0) + 1
                    
            except Exception as e:
                continue
        
        # 22문제 기준으로 정렬 및 검증
        valid_questions = [q for q in analysis["questions"] if q["question_number"]]
        valid_questions.sort(key=lambda x: int(str(x["question_number"]).strip()))
        
        analysis["questions"] = valid_questions[:22]  # 최대 22문제까지
        analysis["actual_question_count"] = len(analysis["questions"])
        
        return analysis
    
    def safe_get(self, row, column_names):
        """안전하게 컬럼 값 가져오기"""
        for col_name in column_names:
            if col_name in row and pd.notna(row[col_name]):
                return str(row[col_name]).strip()
        return None
    
    def merge_stats(self, overall_stats, year_stats):
        """전체 통계에 년도별 통계 합산"""
        overall_stats["total_questions"] += year_stats["actual_question_count"]
        
        # 난이도 분포 합산
        for difficulty, count in year_stats["difficulty_stats"].items():
            overall_stats["difficulty_distribution"][difficulty] = overall_stats["difficulty_distribution"].get(difficulty, 0) + count
        
        # 과목 분포 합산
        for subject, count in year_stats["subject_stats"].items():
            overall_stats["subject_distribution"][subject] = overall_stats["subject_distribution"].get(subject, 0) + count
    
    def analyze_all_evaluators(self):
        """모든 평가위원 분석"""
        print("🔍 전체 평가위원 상세 분석 시작...\n")
        
        # 평가위원 이름 추출
        self.extract_evaluator_names()
        
        # 각 평가위원별 분석
        for dept, evaluators in self.evaluators.items():
            print(f"\n🏥 {dept}학과 평가위원 분석:")
            self.detailed_analysis[dept] = {}
            
            for evaluator_info in evaluators:
                analysis_result = self.analyze_individual_evaluator(evaluator_info)
                if analysis_result:
                    self.detailed_analysis[dept][evaluator_info["name"]] = analysis_result
    
    def generate_detailed_report(self):
        """상세 보고서 생성"""
        report = {
            "analysis_date": pd.Timestamp.now().isoformat(),
            "departments": {},
            "summary": {
                "total_evaluators": 0,
                "total_questions_analyzed": 0,
                "difficulty_patterns": {},
                "department_comparison": {}
            }
        }
        
        for dept, evaluators in self.detailed_analysis.items():
            dept_report = {
                "evaluators_count": len(evaluators),
                "evaluators": {},
                "department_stats": {
                    "total_questions": 0,
                    "difficulty_distribution": {},
                    "subject_distribution": {},
                    "year_coverage": set()
                }
            }
            
            for name, data in evaluators.items():
                evaluator_report = {
                    "name": name,
                    "total_questions": data["overall_stats"]["total_questions"],
                    "years_covered": list(data["years_analysis"].keys()),
                    "difficulty_distribution": data["overall_stats"]["difficulty_distribution"],
                    "subject_distribution": data["overall_stats"]["subject_distribution"],
                    "years_detail": {}
                }
                
                # 년도별 상세 정보
                for year, year_data in data["years_analysis"].items():
                    evaluator_report["years_detail"][year] = {
                        "question_count": year_data["actual_question_count"],
                        "difficulty_by_question": year_data["difficulty_by_question"],
                        "difficulty_stats": year_data["difficulty_stats"],
                        "subject_stats": year_data["subject_stats"]
                    }
                    
                    dept_report["department_stats"]["year_coverage"].add(year)
                
                dept_report["evaluators"][name] = evaluator_report
                dept_report["department_stats"]["total_questions"] += evaluator_report["total_questions"]
                
                # 학과 전체 통계 합산
                for difficulty, count in evaluator_report["difficulty_distribution"].items():
                    dept_report["department_stats"]["difficulty_distribution"][difficulty] = \
                        dept_report["department_stats"]["difficulty_distribution"].get(difficulty, 0) + count
                
                for subject, count in evaluator_report["subject_distribution"].items():
                    dept_report["department_stats"]["subject_distribution"][subject] = \
                        dept_report["department_stats"]["subject_distribution"].get(subject, 0) + count
            
            dept_report["department_stats"]["year_coverage"] = list(dept_report["department_stats"]["year_coverage"])
            report["departments"][dept] = dept_report
            report["summary"]["total_evaluators"] += dept_report["evaluators_count"]
            report["summary"]["total_questions_analyzed"] += dept_report["department_stats"]["total_questions"]
        
        return report
    
    def save_detailed_analysis(self, output_path="data/detailed_evaluator_analysis.json"):
        """상세 분석 결과 저장"""
        report = self.generate_detailed_report()
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 상세 분석 결과 저장: {output_path}")
        return output_path
    
    def print_detailed_summary(self):
        """상세 요약 출력"""
        report = self.generate_detailed_report()
        
        print("\n" + "="*80)
        print("📊 평가위원별 상세 분석 요약")
        print("="*80)
        
        summary = report["summary"]
        print(f"📈 전체 요약:")
        print(f"   - 총 평가위원 수: {summary['total_evaluators']}명")
        print(f"   - 총 분석 문제 수: {summary['total_questions_analyzed']}개")
        
        for dept, dept_data in report["departments"].items():
            print(f"\n🏥 {dept}학과 ({dept_data['evaluators_count']}명):")
            print(f"   📋 학과 전체 통계:")
            print(f"      - 총 문제 수: {dept_data['department_stats']['total_questions']}개")
            print(f"      - 분석 년도: {', '.join(dept_data['department_stats']['year_coverage'])}")
            print(f"      - 난이도 분포: {dept_data['department_stats']['difficulty_distribution']}")
            
            print(f"   👨‍🏫 평가위원별 상세:")
            for name, eval_data in dept_data["evaluators"].items():
                print(f"      • {name}:")
                print(f"        - 분석 문제: {eval_data['total_questions']}개")
                print(f"        - 분석 년도: {', '.join(eval_data['years_covered'])}")
                print(f"        - 난이도 분포: {eval_data['difficulty_distribution']}")
                
                # 년도별 22문제 난이도 패턴
                for year, year_detail in eval_data['years_detail'].items():
                    if year_detail["difficulty_by_question"]:
                        print(f"        - {year}년도 문제별 난이도:")
                        questions_by_difficulty = {}
                        for q_num, difficulty in year_detail["difficulty_by_question"].items():
                            if difficulty not in questions_by_difficulty:
                                questions_by_difficulty[difficulty] = []
                            questions_by_difficulty[difficulty].append(q_num)
                        
                        for difficulty, questions in questions_by_difficulty.items():
                            q_list = sorted(questions, key=lambda x: int(x))[:22]  # 최대 22문제
                            print(f"          {difficulty}: {', '.join(q_list)}번 문제")

def main():
    """메인 실행 함수"""
    analyzer = DetailedEvaluatorAnalysis()
    
    # 전체 분석 실행
    analyzer.analyze_all_evaluators()
    
    # 상세 요약 출력
    analyzer.print_detailed_summary()
    
    # 결과 저장
    analyzer.save_detailed_analysis()
    
    print("\n✅ 평가위원별 상세 분석 완료!")

if __name__ == "__main__":
    main() 