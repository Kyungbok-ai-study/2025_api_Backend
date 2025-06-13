#!/usr/bin/env python3
"""
평가위원 엑셀 파일에서 영역이름(유형) 정보 추출 및 매핑 서비스
"""
import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class EvaluatorTypeMapper:
    """평가위원 데이터에서 영역이름(유형) 정보 매핑"""
    
    def __init__(self):
        self.evaluator_data = {}
        self.type_patterns = {}
        self._load_evaluator_data()
    
    def _load_evaluator_data(self):
        """평가위원 엑셀 파일들에서 데이터 로드"""
        try:
            # 물리치료학과 데이터 로드
            pt_dir = Path("data/평가위원 수행결과/평가위원 수행결과_물리치료")
            if pt_dir.exists():
                self.evaluator_data["물리치료학과"] = self._process_department_files(pt_dir)
            
            # 작업치료학과 데이터 로드  
            ot_dir = Path("data/평가위원 수행결과/평가위원 수행결과_작업치료")
            if ot_dir.exists():
                self.evaluator_data["작업치료학과"] = self._process_department_files(ot_dir)
            
            # 유형 패턴 분석
            self._analyze_type_patterns()
            
            logger.info(f"✅ 평가위원 데이터 로드 완료: {len(self.evaluator_data)}개 학과")
            
        except Exception as e:
            logger.error(f"❌ 평가위원 데이터 로드 실패: {e}")
            self.evaluator_data = {}
    
    def _process_department_files(self, dept_dir: Path) -> Dict[str, Any]:
        """학과별 평가위원 파일들 처리"""
        dept_data = {
            "evaluators": {},
            "type_consensus": {},
            "year_coverage": []
        }
        
        for excel_file in dept_dir.glob("*.xlsx"):
            evaluator_name = self._extract_evaluator_name(excel_file.name)
            evaluator_data = self._process_evaluator_file(excel_file)
            
            if evaluator_data:
                dept_data["evaluators"][evaluator_name] = evaluator_data
                logger.info(f"   ✅ {evaluator_name}: {sum(len(year_data) for year_data in evaluator_data.values())}개 문제")
        
        # 연도별 합의 유형 계산
        dept_data["type_consensus"] = self._calculate_type_consensus(dept_data["evaluators"])
        dept_data["year_coverage"] = sorted(set().union(*[eval_data.keys() for eval_data in dept_data["evaluators"].values()]))
        
        return dept_data
    
    def _extract_evaluator_name(self, filename: str) -> str:
        """파일명에서 평가위원 이름 추출"""
        # "2. 신장훈_물치_마스터코딩지.xlsx" -> "신장훈"
        try:
            parts = filename.split("_")
            if len(parts) >= 2:
                name_part = parts[0].replace("2. ", "").strip()
                return name_part
            return filename.replace(".xlsx", "")
        except:
            return filename.replace(".xlsx", "")
    
    def _process_evaluator_file(self, file_path: Path) -> Dict[str, Dict[int, str]]:
        """단일 평가위원 파일 처리"""
        try:
            excel_file = pd.ExcelFile(file_path)
            evaluator_data = {}
            
            for sheet_name in excel_file.sheet_names:
                year = sheet_name.replace("년도", "")
                if year.isdigit():
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    
                    # 영역이름(유형) 데이터 추출
                    year_types = {}
                    for _, row in df.iterrows():
                        q_num = row.get('문제번호')
                        area_name = row.get('영역이름')
                        
                        if pd.notna(q_num) and pd.notna(area_name) and isinstance(q_num, (int, float)):
                            q_num = int(q_num)
                            if 1 <= q_num <= 30:  # 1~30번 문제만
                                year_types[q_num] = str(area_name).strip()
                    
                    if year_types:
                        evaluator_data[year] = year_types
            
            return evaluator_data
        except Exception as e:
            logger.error(f"❌ {file_path.name} 처리 실패: {e}")
            return {}
    
    def _calculate_type_consensus(self, evaluators_data: Dict[str, Dict[str, Dict[int, str]]]) -> Dict[str, Dict[int, str]]:
        """평가위원들 간의 유형 합의 계산"""
        consensus = {}
        
        # 모든 연도 수집
        all_years = set()
        for eval_data in evaluators_data.values():
            all_years.update(eval_data.keys())
        
        for year in all_years:
            year_consensus = {}
            
            # 해당 연도의 모든 문제 번호 수집
            all_questions = set()
            for eval_data in evaluators_data.values():
                if year in eval_data:
                    all_questions.update(eval_data[year].keys())
            
            # 각 문제별로 다수결 유형 계산
            for q_num in all_questions:
                type_votes = []
                for eval_data in evaluators_data.values():
                    if year in eval_data and q_num in eval_data[year]:
                        type_votes.append(eval_data[year][q_num])
                
                if type_votes:
                    # 가장 많이 나온 유형 선택
                    type_counts = {}
                    for vote in type_votes:
                        type_counts[vote] = type_counts.get(vote, 0) + 1
                    
                    consensus_type = max(type_counts.items(), key=lambda x: x[1])[0]
                    year_consensus[q_num] = consensus_type
            
            if year_consensus:
                consensus[year] = year_consensus
        
        return consensus
    
    def _analyze_type_patterns(self):
        """유형 패턴 분석"""
        self.type_patterns = {
            "물리치료학과": {},
            "작업치료학과": {}
        }
        
        for dept, dept_data in self.evaluator_data.items():
            if "type_consensus" in dept_data:
                all_types = set()
                for year_data in dept_data["type_consensus"].values():
                    all_types.update(year_data.values())
                
                self.type_patterns[dept] = {
                    "available_types": sorted(list(all_types)),
                    "type_count": len(all_types)
                }
        
        logger.info(f"📊 유형 패턴 분석 완료:")
        for dept, patterns in self.type_patterns.items():
            logger.info(f"   {dept}: {patterns['type_count']}개 유형 - {patterns['available_types'][:5]}...")
    
    def get_area_name_for_question(self, department: str, year: int, question_number: int) -> str:
        """특정 문제의 영역이름(유형) 반환 - 문제 위치 기반 일반 패턴 사용"""
        try:
            # 학과명 정규화
            if "물리치료" in department:
                dept_key = "물리치료학과"
            elif "작업치료" in department:
                dept_key = "작업치료학과"
            else:
                dept_key = department
            
            if dept_key not in self.evaluator_data:
                return "일반"
            
            # 📊 연도별 찾기보다는 문제 위치 기반 일반 패턴 사용
            return self._get_area_by_question_position(dept_key, question_number, year)
            
        except Exception as e:
            logger.warning(f"⚠️ 영역이름 조회 실패 ({department}, {year}, {question_number}): {e}")
            return "일반"
    
    def _get_area_by_question_position(self, dept_key: str, question_number: int, year: int = None) -> str:
        """문제 위치 기반 영역이름 예측 (연도 무관 일반 패턴)"""
        try:
            dept_data = self.evaluator_data[dept_key]
            
            # 1. 특정 연도가 있으면 해당 연도 우선 사용
            if year:
                year_str = str(year)
                if ("type_consensus" in dept_data and 
                    year_str in dept_data["type_consensus"] and
                    question_number in dept_data["type_consensus"][year_str]):
                    return dept_data["type_consensus"][year_str][question_number]
            
            # 2. 모든 연도의 해당 문제번호 데이터 수집
            position_patterns = []
            if "type_consensus" in dept_data:
                for year_data in dept_data["type_consensus"].values():
                    if question_number in year_data:
                        position_patterns.append(year_data[question_number])
            
            # 3. 가장 많이 나온 영역이름 반환 (다수결)
            if position_patterns:
                from collections import Counter
                most_common = Counter(position_patterns).most_common(1)[0][0]
                logger.debug(f"문제 {question_number}번 패턴: {position_patterns} → '{most_common}'")
                return most_common
            
            # 4. 패턴이 없으면 학과별 기본 영역 반환
            return self._get_default_area_by_position(dept_key, question_number)
            
        except Exception as e:
            logger.warning(f"⚠️ 위치 기반 영역이름 예측 실패: {e}")
            return self._get_default_area_by_position(dept_key, question_number)
    
    def _get_default_area_by_position(self, dept_key: str, question_number: int) -> str:
        """문제 위치에 따른 기본 영역이름 (학과별 일반적인 패턴)"""
        
        if dept_key == "물리치료학과":
            # 물리치료학과 일반적인 문제 배치 패턴
            if question_number <= 3:
                return "인체의 구분과 조직"
            elif question_number <= 8:
                return "뼈대계통"
            elif question_number <= 12:
                return "근육계통"
            elif question_number <= 16:
                return "순환계통"
            elif question_number <= 20:
                return "신경계통"
            else:
                return "신경계통"
                
        elif dept_key == "작업치료학과":
            # 작업치료학과 일반적인 문제 배치 패턴
            if question_number <= 2:
                return "인체의 체계"
            elif question_number <= 6:
                return "뼈대와 관절계(통)"
            elif question_number <= 10:
                return "근육계(통)"
            elif question_number <= 15:
                return "신경계(통)"
            elif question_number <= 20:
                return "심혈관계(통), 면역계(통)"
            elif question_number <= 25:
                return "신경계(통)의 기능"
            else:
                return "근육계(통)의 기능"
        
        return "일반"
    
    def get_available_types(self, department: str) -> List[str]:
        """학과별 사용 가능한 유형 목록 반환"""
        try:
            # 학과명 정규화
            if "물리치료" in department:
                dept_key = "물리치료학과"
            elif "작업치료" in department:
                dept_key = "작업치료학과"
            else:
                dept_key = department
            
            if dept_key in self.type_patterns:
                return self.type_patterns[dept_key]["available_types"]
            
            return ["일반"]
        except:
            return ["일반"]
    
    def enrich_questions_with_types(self, questions: List[Dict[str, Any]], department: str) -> List[Dict[str, Any]]:
        """문제 데이터에 영역이름(유형) 정보 보강"""
        enriched_questions = []
        
        for question in questions:
            enriched_question = question.copy()
            
            # 기본값들
            year = question.get("year", 2024)
            question_number = question.get("question_number", 1)
            
            # 영역이름 조회 및 설정
            area_name = self.get_area_name_for_question(department, year, question_number)
            enriched_question["area_name"] = area_name
            
            # 과목명도 학과명으로 설정
            enriched_question["subject"] = department
            
            enriched_questions.append(enriched_question)
            logger.debug(f"   문제 {question_number}: {area_name}")
        
        logger.info(f"✅ 문제 유형 보강 완료: {len(enriched_questions)}개 문제")
        return enriched_questions
    
    def save_enhanced_analysis(self, output_path: str = "data/enhanced_evaluator_analysis.json"):
        """강화된 평가위원 분석 결과 저장"""
        try:
            analysis_data = {
                "analysis_date": pd.Timestamp.now().isoformat(),
                "departments": self.evaluator_data,
                "type_patterns": self.type_patterns,
                "summary": {
                    "total_departments": len(self.evaluator_data),
                    "total_evaluators": sum(len(dept["evaluators"]) for dept in self.evaluator_data.values()),
                    "total_types": sum(len(patterns["available_types"]) for patterns in self.type_patterns.values())
                }
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 강화된 분석 결과 저장: {output_path}")
            return True
        except Exception as e:
            logger.error(f"❌ 분석 결과 저장 실패: {e}")
            return False

# 싱글톤 인스턴스
evaluator_type_mapper = EvaluatorTypeMapper() 