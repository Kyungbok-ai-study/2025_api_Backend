#!/usr/bin/env python3
"""
PDF 파일 일괄 파싱 스크립트
물리치료학과 및 작업치료학과 국가시험 문제지 + 답안지 파싱
"""

import os
import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime
import logging

# Django 설정 (데이터베이스 연결용)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# FastAPI 앱 모듈들 import
from app.services.question_parser import question_parser
from app.services.question_review_service import QuestionReviewService
from app.db.database import SessionLocal
from app.models.user import User

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('batch_parse.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 파일 경로 정의
BASE_PATH = Path(r"C:\Users\jaewo\Desktop\2025\2025_backend\uploads\questions")
SAVE_PATH = Path(r"C:\Users\jaewo\Desktop\2025\2025_backend\data\save_parser")

# 파싱할 파일 목록 정의
PARSE_FILES = {
    "작업치료학과": {
        2020: {
            "questions": BASE_PATH / "._2020년도 제48회 작업치료사 국가시험 1교시.pdf",
            "answers": BASE_PATH / "._2020년도 제48회 작업치료사 국가시험 1~2교시 최종답안.pdf"
        },
        2021: {
            "questions": BASE_PATH / "._2021년도 제49회 작업치료사 국가시험 1교시.pdf", 
            "answers": BASE_PATH / "._2021년도 제49회 작업치료사 국가시험 1~2교시 최종답안.pdf"
        },
        2022: {
            "questions": BASE_PATH / "._2022 제50회 작업치료사 국가시험_1교시(홀수형).pdf",
            "answers": BASE_PATH / "._(가답안) 2022 제50회 작업치료사 국가시험 홀수형.pdf"
        },
        2023: {
            "questions": BASE_PATH / "2023년도 제51회 작업치료사 국가시험 1교시 기출문제.pdf",
            "answers": BASE_PATH / "2023년도 제51회 작업치료사 국가시험 1~2교시 최종답안.pdf"
        },
        2024: {
            "questions": BASE_PATH / "2024년도 제52회 작업치료사 국가시험 1교시 기출문제.pdf",
            "answers": BASE_PATH / "2024년도 제52회 작업치료사 국가시험 1~2교시 최종답안.pdf"
        }
    },
    "물리치료학과": {
        2021: {
            "questions": BASE_PATH / "2021년도 제49회 물리치료사 국가시험 1교시 기출문제.pdf",
            "answers": BASE_PATH / "2021년도 제49회 물리치료사 국가시험 1~2교시 최종답안.pdf"
        },
        2022: {
            "questions": BASE_PATH / "2022년도 제50회 물리치료사 국가시험 1교시 기출문제.pdf",
            "answers": BASE_PATH / "2022년도 제50회 물리치료사 국가시험 1~2교시 최종답안.pdf"
        },
        2023: {
            "questions": BASE_PATH / "2023년도 제51회 물리치료사 국가시험 1교시 기출문제.pdf",
            "answers": BASE_PATH / "2023년도 제51회 물리치료사 국가시험 1~2교시 최종답안.pdf"
        },
        2024: {
            "questions": BASE_PATH / "2024년도 제52회 물리치료사 국가시험 1교시 기출문제.pdf",
            "answers": BASE_PATH / "2024년도 제52회 물리치료사 국가시험 1~2교시 최종답안.pdf"
        }
    }
}

# 평가위원 분석 데이터 경로
EVALUATOR_DATA = {
    "물리치료학과": {
        "enhanced": Path(r"C:\Users\jaewo\Desktop\2025\2025_backend\data\enhanced_evaluator_analysis.json"),
        "detailed": Path(r"C:\Users\jaewo\Desktop\2025\2025_backend\data\detailed_evaluator_analysis.json")
    },
    "작업치료학과": {
        "enhanced": Path(r"C:\Users\jaewo\Desktop\2025\2025_backend\data\enhanced_evaluator_analysis_ot.json"),
        "detailed": Path(r"C:\Users\jaewo\Desktop\2025\2025_backend\data\detailed_evaluator_analysis_ot.json")
    }
}

class BatchPDFParser:
    """PDF 파일 일괄 파싱 클래스"""
    
    def __init__(self):
        self.question_review_service = QuestionReviewService()
        self.success_count = 0
        self.error_count = 0
        self.total_questions = 0
        
        # 저장 디렉토리 생성
        SAVE_PATH.mkdir(parents=True, exist_ok=True)
        
        logger.info("🚀 PDF 일괄 파싱 시작")
        logger.info(f"📁 저장 경로: {SAVE_PATH}")
    
    def create_progress_callback(self, department: str, year: int, file_type: str):
        """진행률 콜백 함수 생성"""
        def progress_callback(message: str, progress: float):
            logger.info(f"📊 [{department} {year}년 {file_type}] {progress:.1f}% - {message}")
        return progress_callback
    
    async def parse_single_file(self, file_path: Path, content_type: str, department: str, year: int) -> dict:
        """단일 파일 파싱"""
        if not file_path.exists():
            logger.error(f"❌ 파일 없음: {file_path}")
            return {"success": False, "error": "파일 없음"}
        
        try:
            logger.info(f"📄 파싱 시작: {file_path.name} ({content_type})")
            
            # 진행률 콜백 생성
            progress_callback = self.create_progress_callback(department, year, content_type)
            
            # QuestionParser로 파싱
            result = question_parser.parse_any_file(
                file_path=str(file_path),
                content_type=content_type,
                department=department,
                progress_callback=progress_callback
            )
            
            if result.get("error"):
                logger.error(f"❌ 파싱 실패: {result['error']}")
                return {"success": False, "error": result["error"]}
            
            data = result.get("data", [])
            
            # 연도 정보 추가/보정
            for item in data:
                if not item.get("year") or item.get("year") == 0:
                    item["year"] = year
                item["department"] = department
                item["source_type"] = "국가시험"
                item["exam_session"] = f"제{year-1972+48}회" if department == "작업치료학과" else f"제{year-1972+49}회"
            
            logger.info(f"✅ 파싱 완료: {len(data)}개 항목 ({content_type})")
            return {"success": True, "data": data, "count": len(data)}
            
        except Exception as e:
            logger.error(f"❌ 파싱 오류: {e}")
            return {"success": False, "error": str(e)}
    
    def match_questions_and_answers(self, questions_data: list, answers_data: list, department: str, year: int) -> list:
        """문제와 답안 매칭"""
        logger.info(f"🔗 문제-답안 매칭 시작: {department} {year}년 (문제 {len(questions_data)}개, 답안 {len(answers_data)}개)")
        
        # QuestionParser의 매칭 함수 사용
        matched_data = question_parser.match_questions_with_answers(questions_data, answers_data)
        
        # 매칭 통계
        matched_count = len([item for item in matched_data if item.get("correct_answer")])
        logger.info(f"📊 매칭 결과: 총 {len(matched_data)}개 중 {matched_count}개 정답 매칭")
        
        return matched_data
    
    def load_evaluator_difficulty_mapping(self, department: str, year: int) -> dict:
        """평가위원 난이도 매핑 데이터 로드"""
        try:
            enhanced_path = EVALUATOR_DATA[department]["enhanced"]
            detailed_path = EVALUATOR_DATA[department]["detailed"]
            
            difficulty_mapping = {}
            
            # Enhanced 데이터 로드
            if enhanced_path.exists():
                with open(enhanced_path, 'r', encoding='utf-8') as f:
                    enhanced_data = json.load(f)
                    
                # 연도별 데이터 추출
                year_key = str(year)
                if year_key in enhanced_data:
                    year_data = enhanced_data[year_key]
                    for q_num in range(1, 23):  # 1-22번 문제
                        q_key = str(q_num)
                        if q_key in year_data:
                            question_info = year_data[q_key]
                            difficulty_mapping[q_num] = {
                                "difficulty": question_info.get("consensus_difficulty", "중"),
                                "area_name": question_info.get("primary_area", "일반"),
                                "topic": question_info.get("topic", ""),
                                "evaluator_source": "enhanced"
                            }
            
            # Detailed 데이터로 보완
            if detailed_path.exists():
                with open(detailed_path, 'r', encoding='utf-8') as f:
                    detailed_data = json.load(f)
                    
                year_key = str(year)
                if year_key in detailed_data:
                    year_questions = detailed_data[year_key].get("questions", [])
                    for question in year_questions:
                        q_num = question.get("question_number")
                        if q_num and q_num not in difficulty_mapping:
                            difficulty_mapping[q_num] = {
                                "difficulty": question.get("difficulty", "중"),
                                "area_name": question.get("area", "일반"),
                                "topic": question.get("topic", ""),
                                "evaluator_source": "detailed"
                            }
            
            logger.info(f"📊 평가위원 매핑 로드: {department} {year}년 - {len(difficulty_mapping)}개 문제")
            return difficulty_mapping
            
        except Exception as e:
            logger.warning(f"⚠️ 평가위원 데이터 로드 실패: {e}")
            return {}
    
    def apply_evaluator_mapping(self, matched_data: list, department: str, year: int) -> list:
        """평가위원 매핑 적용"""
        difficulty_mapping = self.load_evaluator_difficulty_mapping(department, year)
        
        enhanced_count = 0
        for item in matched_data:
            q_num = item.get("question_number")
            if q_num and q_num in difficulty_mapping:
                mapping_info = difficulty_mapping[q_num]
                
                # 평가위원 데이터 우선 적용
                item["difficulty"] = mapping_info["difficulty"]
                item["area_name"] = mapping_info["area_name"]
                if mapping_info["topic"]:
                    item["topic"] = mapping_info["topic"]
                
                # 메타데이터에 평가위원 정보 추가
                if "metadata" not in item:
                    item["metadata"] = {}
                item["metadata"]["evaluator_source"] = mapping_info["evaluator_source"]
                item["metadata"]["evaluator_enhanced"] = True
                
                enhanced_count += 1
        
        logger.info(f"✨ 평가위원 매핑 적용: {enhanced_count}개 문제 강화됨")
        return matched_data
    
    def save_to_json(self, data: list, department: str, year: int) -> str:
        """JSON 파일로 저장"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_batch_{department}_{year}년_국가시험.json"
            file_path = SAVE_PATH / filename
            
            # 저장할 데이터 구조
            save_data = {
                "meta": {
                    "department": department,
                    "year": year,
                    "exam_type": "국가시험",
                    "parsed_at": datetime.now().isoformat(),
                    "total_questions": len(data),
                    "parsing_method": "batch_script",
                    "ai_analysis_included": True,
                    "evaluator_mapping_applied": True
                },
                "questions": data
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 JSON 저장 완료: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"❌ JSON 저장 실패: {e}")
            return ""
    
    async def process_department_year(self, department: str, year: int, file_info: dict):
        """특정 학과의 특정 연도 처리"""
        logger.info(f"\n🎯 처리 시작: {department} {year}년")
        
        try:
            # 1단계: 문제지 파싱
            questions_result = await self.parse_single_file(
                file_info["questions"], "questions", department, year
            )
            
            if not questions_result["success"]:
                logger.error(f"❌ 문제지 파싱 실패: {questions_result.get('error')}")
                self.error_count += 1
                return
            
            # 2단계: 답안지 파싱
            answers_result = await self.parse_single_file(
                file_info["answers"], "answers", department, year
            )
            
            if not answers_result["success"]:
                logger.error(f"❌ 답안지 파싱 실패: {answers_result.get('error')}")
                self.error_count += 1
                return
            
            # 3단계: 문제-답안 매칭
            questions_data = questions_result["data"]
            answers_data = answers_result["data"]
            
            matched_data = self.match_questions_and_answers(questions_data, answers_data, department, year)
            
            if not matched_data:
                logger.error(f"❌ 매칭 결과 없음")
                self.error_count += 1
                return
            
            # 4단계: 평가위원 매핑 적용
            enhanced_data = self.apply_evaluator_mapping(matched_data, department, year)
            
            # 5단계: JSON 저장
            json_path = self.save_to_json(enhanced_data, department, year)
            
            if json_path:
                self.success_count += 1
                self.total_questions += len(enhanced_data)
                logger.info(f"✅ 완료: {department} {year}년 - {len(enhanced_data)}개 문제")
            else:
                self.error_count += 1
                
        except Exception as e:
            logger.error(f"❌ 처리 실패: {department} {year}년 - {e}")
            self.error_count += 1
    
    async def run_batch_parsing(self):
        """일괄 파싱 실행"""
        logger.info(f"📋 처리 대상: {sum(len(years) for years in PARSE_FILES.values())}개 연도")
        
        # 모든 학과, 연도 순차 처리
        for department, years_data in PARSE_FILES.items():
            logger.info(f"\n🏥 학과 처리 시작: {department}")
            
            for year, file_info in years_data.items():
                await self.process_department_year(department, year, file_info)
                
                # 각 연도 처리 후 잠시 대기 (API 부하 방지)
                await asyncio.sleep(2)
        
        # 최종 결과
        logger.info(f"\n🎉 일괄 파싱 완료!")
        logger.info(f"✅ 성공: {self.success_count}개 연도")
        logger.info(f"❌ 실패: {self.error_count}개 연도") 
        logger.info(f"📊 총 문제: {self.total_questions}개")
        logger.info(f"💾 저장 위치: {SAVE_PATH}")

def verify_files():
    """파일 존재 여부 확인"""
    logger.info("📋 파일 존재 여부 확인 중...")
    
    missing_files = []
    total_files = 0
    
    for department, years_data in PARSE_FILES.items():
        for year, file_info in years_data.items():
            for file_type, file_path in file_info.items():
                total_files += 1
                if not file_path.exists():
                    missing_files.append(f"{department} {year}년 {file_type}: {file_path}")
    
    if missing_files:
        logger.error(f"❌ 누락된 파일 {len(missing_files)}개:")
        for missing in missing_files:
            logger.error(f"   - {missing}")
        return False
    
    logger.info(f"✅ 모든 파일 확인 완료: {total_files}개 파일")
    return True

def verify_evaluator_data():
    """평가위원 데이터 파일 확인"""
    logger.info("📊 평가위원 데이터 확인 중...")
    
    missing_data = []
    for department, data_paths in EVALUATOR_DATA.items():
        for data_type, file_path in data_paths.items():
            if not file_path.exists():
                missing_data.append(f"{department} {data_type}: {file_path}")
    
    if missing_data:
        logger.warning(f"⚠️ 누락된 평가위원 데이터 {len(missing_data)}개:")
        for missing in missing_data:
            logger.warning(f"   - {missing}")
        logger.warning("평가위원 매핑 없이 진행됩니다.")
    else:
        logger.info("✅ 평가위원 데이터 모두 확인됨")

async def main():
    """메인 함수"""
    logger.info("🚀 PDF 일괄 파싱 스크립트 시작")
    logger.info(f"📅 처리 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 파일 존재 여부 확인
    if not verify_files():
        logger.error("❌ 필수 파일이 누락되어 종료합니다.")
        return
    
    # 평가위원 데이터 확인
    verify_evaluator_data()
    
    # 일괄 파싱 실행
    parser = BatchPDFParser()
    await parser.run_batch_parsing()

if __name__ == "__main__":
    # 비동기 실행
    asyncio.run(main()) 