"""
진단테스트 시스템 설정 및 관리 스크립트
물리치료학과(1차~10차), 작업치료학과(1차~10차) 진단테스트 설정
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DiagnosticTestManager:
    """진단테스트 관리 클래스"""
    
    def __init__(self):
        self.data_dir = "data/departments/medical"
        self.departments = {
            "물리치료학과": {
                "code": "PT",
                "file_prefix": "diagnostic_test_physics_therapy",
                "rounds": list(range(1, 11)),  # 1차~10차
                "description": "물리치료사 국가고시 기반 진단테스트"
            },
            "작업치료학과": {
                "code": "OT", 
                "file_prefix": "diagnostic_test_occupational_therapy",
                "rounds": list(range(1, 11)),  # 1차~10차
                "description": "작업치료사 국가고시 기반 진단테스트"
            }
        }
        
        # 각 학과별 차수별 전문 영역 정의
        self.focus_areas = {
            "물리치료학과": {
                1: "물리치료학 기초",
                2: "운동치료학", 
                3: "신경계 물리치료",
                4: "근골격계 물리치료",
                5: "심폐 물리치료",
                6: "소아 물리치료",
                7: "노인 물리치료",
                8: "스포츠 물리치료",
                9: "정형외과 물리치료",
                10: "종합 평가"
            },
            "작업치료학과": {
                1: "작업치료학 기초",
                2: "일상생활활동(ADL)",
                3: "인지재활치료",
                4: "작업수행분석",
                5: "정신사회작업치료",
                6: "소아작업치료",
                7: "신체장애작업치료",
                8: "감각통합치료",
                9: "보조공학",
                10: "종합 평가"
            }
        }
        
        self.test_registry = {}
        self.config_data = {}
    
    def load_test_file(self, file_path: str) -> Optional[Dict]:
        """진단테스트 파일 로드"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"파일을 찾을 수 없습니다: {file_path}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {file_path} - {e}")
            return None
        except Exception as e:
            logger.error(f"파일 로드 오류: {file_path} - {e}")
            return None
    
    def scan_available_tests(self):
        """사용 가능한 진단테스트 파일 스캔"""
        logger.info("🔍 진단테스트 파일 스캔 시작...")
        
        available_tests = {}
        
        for dept_name, dept_info in self.departments.items():
            available_tests[dept_name] = {}
            
            for round_num in dept_info["rounds"]:
                filename = f"{dept_info['file_prefix']}_round{round_num}.json"
                filepath = os.path.join(self.data_dir, filename)
                
                if os.path.exists(filepath):
                    test_data = self.load_test_file(filepath)
                    if test_data:
                        available_tests[dept_name][round_num] = {
                            "file_path": filepath,
                            "title": test_data.get("test_info", {}).get("title", f"{dept_name} {round_num}차"),
                            "focus_area": self.focus_areas.get(dept_name, {}).get(round_num, "일반"),
                            "questions_count": test_data.get("test_info", {}).get("total_questions", 0),
                            "time_limit": test_data.get("test_info", {}).get("time_limit", 60),
                            "created_at": test_data.get("test_info", {}).get("created_at", ""),
                            "version": test_data.get("test_info", {}).get("version", "1.0")
                        }
                        logger.info(f"  ✅ {dept_name} {round_num}차 - {self.focus_areas.get(dept_name, {}).get(round_num, '일반')}")
                    else:
                        logger.warning(f"  ❌ {dept_name} {round_num}차 - 파일 로드 실패")
                else:
                    logger.warning(f"  ❌ {dept_name} {round_num}차 - 파일 없음: {filename}")
        
        self.test_registry = available_tests
        return available_tests
    
    def generate_test_config(self):
        """진단테스트 설정 데이터 생성"""
        logger.info("⚙️ 진단테스트 설정 데이터 생성 시작...")
        
        config = {
            "diagnostic_tests": {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "departments": {}
            }
        }
        
        for dept_name, tests in self.test_registry.items():
            dept_info = self.departments[dept_name]
            
            config["diagnostic_tests"]["departments"][dept_name] = {
                "code": dept_info["code"],
                "description": dept_info["description"],
                "total_rounds": len(tests),
                "available_rounds": list(tests.keys()),
                "tests": {}
            }
            
            for round_num, test_info in tests.items():
                config["diagnostic_tests"]["departments"][dept_name]["tests"][str(round_num)] = {
                    "round": round_num,
                    "title": test_info["title"],
                    "focus_area": test_info["focus_area"],
                    "file_path": test_info["file_path"],
                    "questions_count": test_info["questions_count"],
                    "time_limit": test_info["time_limit"],
                    "difficulty_levels": ["쉬움", "보통", "어려움"],
                    "scoring": {
                        "total_score": 100,
                        "score_per_question": 3.3,
                        "pass_score": 60
                    },
                    "status": "active",
                    "created_at": test_info["created_at"],
                    "version": test_info["version"]
                }
        
        self.config_data = config
        return config
    
    def save_config_file(self, output_path: str = "config/diagnostic_tests_config.json"):
        """설정 파일 저장"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 설정 파일 저장 완료: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 설정 파일 저장 실패: {e}")
            return False
    
    def generate_summary_report(self):
        """진단테스트 현황 요약 보고서 생성"""
        logger.info("📊 진단테스트 현황 요약 보고서 생성...")
        
        report = {
            "diagnostic_tests_summary": {
                "generated_at": datetime.now().isoformat(),
                "total_departments": len(self.test_registry),
                "departments": []
            }
        }
        
        total_tests = 0
        total_questions = 0
        
        for dept_name, tests in self.test_registry.items():
            dept_summary = {
                "department": dept_name,
                "code": self.departments[dept_name]["code"],
                "total_rounds": len(tests),
                "available_rounds": sorted(tests.keys()),
                "tests_detail": []
            }
            
            dept_questions = 0
            
            for round_num in sorted(tests.keys()):
                test_info = tests[round_num]
                dept_summary["tests_detail"].append({
                    "round": round_num,
                    "focus_area": test_info["focus_area"],
                    "questions": test_info["questions_count"],
                    "time_limit": test_info["time_limit"],
                    "status": "활성"
                })
                dept_questions += test_info["questions_count"]
            
            dept_summary["total_questions"] = dept_questions
            report["diagnostic_tests_summary"]["departments"].append(dept_summary)
            
            total_tests += len(tests)
            total_questions += dept_questions
        
        report["diagnostic_tests_summary"]["total_tests"] = total_tests
        report["diagnostic_tests_summary"]["total_questions"] = total_questions
        
        return report
    
    def save_summary_report(self, report_data: Dict, output_path: str = "reports/diagnostic_tests_summary.json"):
        """요약 보고서 저장"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 요약 보고서 저장 완료: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 요약 보고서 저장 실패: {e}")
            return False
    
    def print_summary(self):
        """콘솔에 요약 정보 출력"""
        print("\n" + "="*60)
        print("🏥 진단테스트 시스템 설정 완료")
        print("="*60)
        
        total_tests = 0
        total_questions = 0
        
        for dept_name, tests in self.test_registry.items():
            print(f"\n📚 {dept_name} ({self.departments[dept_name]['code']})")
            print(f"   총 {len(tests)}개 차수")
            
            dept_questions = 0
            for round_num in sorted(tests.keys()):
                test_info = tests[round_num]
                focus_area = test_info["focus_area"]
                questions = test_info["questions_count"]
                
                print(f"   {round_num:2d}차: {focus_area:<20} ({questions}문제)")
                dept_questions += questions
            
            print(f"   소계: {dept_questions}문제")
            total_tests += len(tests)
            total_questions += dept_questions
        
        print(f"\n📊 전체 현황")
        print(f"   총 학과: {len(self.test_registry)}개")
        print(f"   총 테스트: {total_tests}개")
        print(f"   총 문제: {total_questions}개")
        print("="*60)
    
    def setup_all_tests(self):
        """모든 진단테스트 설정 및 구성"""
        logger.info("🚀 진단테스트 시스템 설정 시작")
        
        # 1. 사용 가능한 테스트 파일 스캔
        available_tests = self.scan_available_tests()
        
        if not available_tests:
            logger.error("❌ 사용 가능한 진단테스트 파일이 없습니다.")
            return False
        
        # 2. 설정 데이터 생성
        config_data = self.generate_test_config()
        
        # 3. 설정 파일 저장
        if not self.save_config_file():
            logger.error("❌ 설정 파일 저장 실패")
            return False
        
        # 4. 요약 보고서 생성 및 저장
        summary_report = self.generate_summary_report()
        if not self.save_summary_report(summary_report):
            logger.error("❌ 요약 보고서 저장 실패")
            return False
        
        # 5. 콘솔 요약 출력
        self.print_summary()
        
        logger.info("✅ 진단테스트 시스템 설정 완료")
        return True
    
    def validate_test_integrity(self):
        """진단테스트 파일 무결성 검사"""
        logger.info("🔍 진단테스트 무결성 검사 시작...")
        
        validation_results = {
            "total_checked": 0,
            "valid_tests": 0,
            "invalid_tests": 0,
            "issues": []
        }
        
        for dept_name, tests in self.test_registry.items():
            for round_num, test_info in tests.items():
                validation_results["total_checked"] += 1
                
                # 파일 로드 및 구조 검사
                test_data = self.load_test_file(test_info["file_path"])
                
                if not test_data:
                    validation_results["invalid_tests"] += 1
                    validation_results["issues"].append(f"{dept_name} {round_num}차: 파일 로드 실패")
                    continue
                
                # 필수 필드 검사
                required_fields = ["test_info", "scoring_criteria", "questions"]
                missing_fields = [field for field in required_fields if field not in test_data]
                
                if missing_fields:
                    validation_results["invalid_tests"] += 1
                    validation_results["issues"].append(f"{dept_name} {round_num}차: 필수 필드 누락 - {missing_fields}")
                    continue
                
                # 문제 개수 검사
                questions = test_data.get("questions", [])
                expected_count = test_data.get("test_info", {}).get("total_questions", 30)
                
                if len(questions) != expected_count:
                    validation_results["invalid_tests"] += 1
                    validation_results["issues"].append(f"{dept_name} {round_num}차: 문제 개수 불일치 - 예상 {expected_count}, 실제 {len(questions)}")
                    continue
                
                validation_results["valid_tests"] += 1
        
        # 검사 결과 출력
        print(f"\n🔍 무결성 검사 결과:")
        print(f"   총 검사: {validation_results['total_checked']}개")
        print(f"   정상: {validation_results['valid_tests']}개")
        print(f"   문제: {validation_results['invalid_tests']}개")
        
        if validation_results["issues"]:
            print(f"\n❌ 발견된 문제:")
            for issue in validation_results["issues"]:
                print(f"   - {issue}")
        else:
            print(f"\n✅ 모든 진단테스트가 정상입니다.")
        
        return validation_results

def main():
    """메인 실행 함수"""
    print("🏥 진단테스트 시스템 설정 도구")
    print("=" * 50)
    
    manager = DiagnosticTestManager()
    
    # 진단테스트 시스템 설정
    success = manager.setup_all_tests()
    
    if success:
        print("\n🔧 추가 검사 수행...")
        
        # 무결성 검사
        validation_results = manager.validate_test_integrity()
        
        if validation_results["invalid_tests"] == 0:
            print("\n🎉 진단테스트 시스템 설정 및 검증 완료!")
            print("\n📁 생성된 파일:")
            print("   - config/diagnostic_tests_config.json")
            print("   - reports/diagnostic_tests_summary.json")
        else:
            print(f"\n⚠️ 일부 테스트에 문제가 있습니다. 위의 문제를 해결해주세요.")
    else:
        print("\n❌ 진단테스트 시스템 설정 실패")

if __name__ == "__main__":
    main() 