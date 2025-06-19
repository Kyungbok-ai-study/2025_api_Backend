"""
전체 학과 지원 통합 진단테스트 서비스
모든 학과에 대해 실제 작동하는 진단테스트 시스템
"""
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from datetime import datetime, timedelta
import os
from pathlib import Path

from app.models.unified_diagnosis import (
    DiagnosisTest,
    DiagnosisQuestion,
    DiagnosisSession,
    DiagnosisResponse,
    StudentDiagnosisHistory
)
from app.models.user import User
from app.models.enums import DiagnosisSubject, DEPARTMENT_TEST_FILE_MAPPING, DEPARTMENT_CATEGORIES

logger = logging.getLogger(__name__)

class UniversalDiagnosisService:
    """전체 학과 지원 통합 진단테스트 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.base_path = Path(__file__).parent.parent.parent / "data" / "departments"
        
    def get_supported_departments(self) -> Dict[str, List[str]]:
        """지원되는 전체 학과 목록 반환 (데이터 폴더 기반)"""
        supported_departments = {}
        
        # 데이터 폴더에서 실제 지원되는 학과 확인
        department_folders = {
            "medical": "의료계열",
            "nursing": "의료계열", 
            "business": "경영계열",
            "computer_science": "컴퓨터계열"
        }
        
        for folder_name, category in department_folders.items():
            folder_path = self.base_path / folder_name
            if folder_path.exists():
                if category not in supported_departments:
                    supported_departments[category] = []
                
                # 폴더 내 JSON 파일들을 확인하여 학과 추출
                for json_file in folder_path.glob("diagnostic_test_*.json"):
                    if json_file.name.startswith("diagnostic_test_") and not json_file.name.endswith("_round"):
                        department_name = self._extract_department_from_filename(json_file.name)
                        if department_name and department_name not in supported_departments[category]:
                            supported_departments[category].append(department_name)
        
        # 빈 카테고리 제거
        supported_departments = {k: v for k, v in supported_departments.items() if v}
        
        return supported_departments
    
    def get_department_subject(self, department_name: str) -> Optional[DiagnosisSubject]:
        """학과명을 DiagnosisSubject enum으로 변환"""
        department_mapping = {
            # 의료계열
            "의학과": DiagnosisSubject.MEDICINE,
            "간호학과": DiagnosisSubject.NURSING,
            "물리치료학과": DiagnosisSubject.PHYSICAL_THERAPY,
            "작업치료학과": DiagnosisSubject.OCCUPATIONAL_THERAPY,
            "치의학과": DiagnosisSubject.DENTISTRY,
            "약학과": DiagnosisSubject.PHARMACY,
            
            # 공학계열
            "기계공학과": DiagnosisSubject.MECHANICAL_ENGINEERING,
            "전기공학과": DiagnosisSubject.ELECTRICAL_ENGINEERING,
            "전자공학과": DiagnosisSubject.ELECTRONIC_ENGINEERING,
            "화학공학과": DiagnosisSubject.CHEMICAL_ENGINEERING,
            "토목공학과": DiagnosisSubject.CIVIL_ENGINEERING,
            "건축학과": DiagnosisSubject.ARCHITECTURE,
            
            # 컴퓨터계열
            "컴퓨터공학과": DiagnosisSubject.COMPUTER_SCIENCE,
            "소프트웨어공학과": DiagnosisSubject.SOFTWARE_ENGINEERING,
            "인공지능학과": DiagnosisSubject.ARTIFICIAL_INTELLIGENCE,
            "데이터사이언스학과": DiagnosisSubject.DATA_SCIENCE,
            "정보시스템학과": DiagnosisSubject.INFORMATION_SYSTEMS,
            
            # 자연과학계열
            "수학과": DiagnosisSubject.MATHEMATICS,
            "물리학과": DiagnosisSubject.PHYSICS,
            "화학과": DiagnosisSubject.CHEMISTRY,
            "생물학과": DiagnosisSubject.BIOLOGY,
            "통계학과": DiagnosisSubject.STATISTICS,
            
            # 사회과학계열
            "경제학과": DiagnosisSubject.ECONOMICS,
            "심리학과": DiagnosisSubject.PSYCHOLOGY,
            "사회학과": DiagnosisSubject.SOCIOLOGY,
            "정치학과": DiagnosisSubject.POLITICAL_SCIENCE,
            
            # 경영계열
            "경영학과": DiagnosisSubject.BUSINESS_ADMINISTRATION,
            "회계학과": DiagnosisSubject.ACCOUNTING,
            "금융학과": DiagnosisSubject.FINANCE,
            "마케팅학과": DiagnosisSubject.MARKETING,
            
            # 법학계열
            "법학과": DiagnosisSubject.LAW,
            
            # 교육계열
            "교육학과": DiagnosisSubject.EDUCATION,
            "초등교육과": DiagnosisSubject.ELEMENTARY_EDUCATION,
            
            # 예술계열
            "미술학과": DiagnosisSubject.FINE_ARTS,
            "음악학과": DiagnosisSubject.MUSIC,
            "디자인학과": DiagnosisSubject.DESIGN,
        }
        
        return department_mapping.get(department_name)
    
    def _extract_department_from_filename(self, filename: str) -> Optional[str]:
        """파일명에서 학과명 추출"""
        # diagnostic_test_medical.json -> 의학과
        # diagnostic_test_physics_therapy.json -> 물리치료학과
        department_mapping = {
            "medical": "의학과",
            "physics_therapy": "물리치료학과", 
            "occupational_therapy": "작업치료학과",
            "nursing": "간호학과",
            "business": "경영학과",
            "computer_science": "컴퓨터공학과"
        }
        
        # diagnostic_test_ 제거하고 .json 제거
        base_name = filename.replace("diagnostic_test_", "").replace(".json", "")
        return department_mapping.get(base_name)
    
    def load_department_test_data(self, department_name: str) -> Optional[Dict[str, Any]]:
        """데이터 폴더에서 학과별 테스트 데이터 로드"""
        try:
            # 학과명을 파일명으로 변환
            file_mapping = {
                "의학과": "medical/diagnostic_test_medical.json",
                "물리치료학과": "medical/diagnostic_test_physics_therapy.json",
                "작업치료학과": "medical/diagnostic_test_occupational_therapy.json", 
                "간호학과": "nursing/diagnostic_test_nursing.json",
                "경영학과": "business/diagnostic_test_business.json",
                "컴퓨터공학과": "computer_science/diagnostic_test_computer_science.json"
            }
            
            if department_name not in file_mapping:
                logger.warning(f"지원되지 않는 학과: {department_name}")
                return None
            
            file_path = self.base_path / file_mapping[department_name]
            
            if not file_path.exists():
                logger.warning(f"테스트 데이터 파일이 없습니다: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            logger.info(f"{department_name} 테스트 데이터 로드 완료")
            return data
            
        except Exception as e:
            logger.error(f"테스트 데이터 로드 실패 ({department_name}): {e}")
            return None
    
    def create_universal_test_data(self, department_name: str) -> Dict[str, Any]:
        """실제 데이터 파일 기반 진단테스트 데이터 생성"""
        
        # 데이터 폴더에서 실제 테스트 데이터 로드
        test_data = self.load_department_test_data(department_name)
        
        if test_data:
            # 실제 데이터 파일 사용
            return test_data
        else:
            # 데이터 파일이 없는 경우 기본 데이터 생성
            logger.warning(f"{department_name}의 데이터 파일이 없어 기본 데이터를 생성합니다.")
            return self._create_fallback_test_data(department_name)
    
    def _create_fallback_test_data(self, department_name: str) -> Dict[str, Any]:
        """데이터 파일이 없을 때 사용할 기본 테스트 데이터"""
        return {
            "test_info": {
                "title": f"{department_name} 수준 진단테스트",
                "description": f"{department_name} 기본 지식 진단",
                "total_questions": 10,
                "time_limit": 30,
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
                "source": "기본 교육과정 기반"
            },
            "scoring_criteria": {
                "total_score": 100,
                "score_per_question": 10.0,
                "difficulty_weights": {
                    "쉬움": 1.0,
                    "보통": 1.2,
                    "어려움": 1.5
                },
                "level_classification": {
                    "상급": {"min_score": 80, "description": "상급 수준"},
                    "중급": {"min_score": 65, "description": "중급 수준"},
                    "하급": {"min_score": 50, "description": "하급 수준"},
                    "미흡": {"min_score": 0, "description": "미흡 수준"}
                }
            },
            "questions": [
                {
                    "question_id": f"{department_name}_001",
                    "question_number": 1,
                    "content": f"{department_name}의 기본 개념에 대한 문제입니다.",
                    "options": {
                        "1": "선택지 1",
                        "2": "선택지 2", 
                        "3": "선택지 3",
                        "4": "선택지 4",
                        "5": "선택지 5"
                    },
                    "correct_answer": "1",
                    "subject": department_name,
                    "area_name": "기본개념",
                    "difficulty": 3,
                    "difficulty_level": "보통",
                    "question_type": "기본개념",
                    "points": 10.0
                }
            ]
        }
    
    def grade_test(self, test_data: Dict[str, Any], submitted_answers: Dict[str, str], user_id: int, department_name: str) -> Dict[str, Any]:
        """테스트 채점 및 결과 생성"""
        try:
            questions = test_data["questions"]
            scoring_criteria = test_data["scoring_criteria"]
            
            correct_count = 0
            wrong_count = 0
            total_score = 0
            question_results = []
            
            for question in questions:
                question_id = question["question_id"]
                correct_answer = question["correct_answer"]
                user_answer = submitted_answers.get(question_id, "")
                
                is_correct = user_answer == correct_answer
                if is_correct:
                    correct_count += 1
                    # 난이도별 가중치 적용
                    difficulty_weight = scoring_criteria["difficulty_weights"].get(
                        question.get("difficulty_level", "보통"), 1.0
                    )
                    score = scoring_criteria["score_per_question"] * difficulty_weight
                    total_score += score
                else:
                    wrong_count += 1
                
                question_results.append({
                    "question_id": question_id,
                    "question_number": question.get("question_number", 0),
                    "user_answer": user_answer,
                    "correct_answer": correct_answer,
                    "is_correct": is_correct,
                    "difficulty": question.get("difficulty_level", "보통")
                })
            
            # 등급 계산
            max_score = scoring_criteria["total_score"]
            percentage = (total_score / max_score) * 100
            
            grade = "미흡"
            for level, criteria in scoring_criteria["level_classification"].items():
                if percentage >= criteria["min_score"]:
                    grade = level
                    break
            
            # 결과 ID 생성
            import time
            result_id = f"{user_id}_{department_name}_{int(time.time())}"
            
            return {
                "result_id": result_id,
                "user_id": user_id,
                "department_name": department_name,
                "total_score": round(total_score, 1),
                "max_score": max_score,
                "percentage": round(percentage, 1),
                "grade": grade,
                "correct_answers": correct_count,
                "wrong_answers": wrong_count,
                "total_questions": len(questions),
                "question_results": question_results,
                "completed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"테스트 채점 실패: {e}")
            raise Exception(f"테스트 채점 중 오류가 발생했습니다: {str(e)}")
    
    def _generate_department_questions(self, subject: DiagnosisSubject) -> List[Dict[str, Any]]:
        """학과별 맞춤 문제 생성"""
        
        # 학과별 문제 템플릿
        question_templates = {
            DiagnosisSubject.COMPUTER_SCIENCE: self._get_computer_science_questions(),
            DiagnosisSubject.NURSING: self._get_nursing_questions(),
            DiagnosisSubject.BUSINESS_ADMINISTRATION: self._get_business_questions(),
            DiagnosisSubject.MECHANICAL_ENGINEERING: self._get_mechanical_engineering_questions(),
            DiagnosisSubject.MATHEMATICS: self._get_mathematics_questions(),
            DiagnosisSubject.PSYCHOLOGY: self._get_psychology_questions(),
            DiagnosisSubject.LAW: self._get_law_questions(),
            DiagnosisSubject.EDUCATION: self._get_education_questions(),
            DiagnosisSubject.FINE_ARTS: self._get_fine_arts_questions(),
        }
        
        # 해당 학과 문제가 없으면 기본 문제 생성
        if subject not in question_templates:
            return self._get_generic_questions(subject)
        
        return question_templates[subject]
    
    def _get_computer_science_questions(self) -> List[Dict[str, Any]]:
        """컴퓨터공학 문제"""
        return [
            {
                "question_id": "CS_001",
                "question_number": 1,
                "content": "다음 중 시간복잡도가 O(n log n)인 정렬 알고리즘은?",
                "options": {
                    "1": "버블 정렬(Bubble Sort)",
                    "2": "선택 정렬(Selection Sort)",
                    "3": "병합 정렬(Merge Sort)",
                    "4": "삽입 정렬(Insertion Sort)",
                    "5": "보기 정렬(Bogo Sort)"
                },
                "correct_answer": "3",
                "subject": "컴퓨터공학",
                "area_name": "알고리즘",
                "difficulty": 6,
                "difficulty_level": "보통",
                "question_type": "기본개념",
                "points": 4.0
            },
            {
                "question_id": "CS_002",
                "question_number": 2,
                "content": "데이터베이스에서 ACID 속성 중 'C'가 의미하는 것은?",
                "options": {
                    "1": "원자성(Atomicity)",
                    "2": "일관성(Consistency)",
                    "3": "격리성(Isolation)",
                    "4": "지속성(Durability)",
                    "5": "동시성(Concurrency)"
                },
                "correct_answer": "2",
                "subject": "컴퓨터공학",
                "area_name": "데이터베이스",
                "difficulty": 5,
                "difficulty_level": "보통",
                "question_type": "기본개념",
                "points": 4.0
            },
            {
                "question_id": "CS_003",
                "question_number": 3,
                "content": "객체지향 프로그래밍의 4대 특징이 아닌 것은?",
                "options": {
                    "1": "캡슐화(Encapsulation)",
                    "2": "상속(Inheritance)",
                    "3": "다형성(Polymorphism)",
                    "4": "추상화(Abstraction)",
                    "5": "컴파일(Compilation)"
                },
                "correct_answer": "5",
                "subject": "컴퓨터공학",
                "area_name": "객체지향프로그래밍",
                "difficulty": 4,
                "difficulty_level": "쉬움",
                "question_type": "기본개념",
                "points": 3.5
            },
            {
                "question_id": "CS_004",
                "question_number": 4,
                "content": "TCP와 UDP의 차이점으로 올바른 것은?",
                "options": {
                    "1": "TCP는 비연결형, UDP는 연결형 프로토콜이다",
                    "2": "TCP는 신뢰성을 보장하지 않고, UDP는 신뢰성을 보장한다",
                    "3": "TCP는 연결형이며 신뢰성을 보장하고, UDP는 비연결형이며 빠른 전송을 제공한다",
                    "4": "TCP와 UDP는 동일한 기능을 제공한다",
                    "5": "TCP는 응용계층, UDP는 전송계층 프로토콜이다"
                },
                "correct_answer": "3",
                "subject": "컴퓨터공학",
                "area_name": "네트워크",
                "difficulty": 6,
                "difficulty_level": "보통",
                "question_type": "응용",
                "points": 4.0
            },
            {
                "question_id": "CS_005",
                "question_number": 5,
                "content": "다음 중 메모리 관리 기법이 아닌 것은?",
                "options": {
                    "1": "페이징(Paging)",
                    "2": "세그멘테이션(Segmentation)",
                    "3": "가상 메모리(Virtual Memory)",
                    "4": "캐시 메모리(Cache Memory)",
                    "5": "스택 오버플로우(Stack Overflow)"
                },
                "correct_answer": "5",
                "subject": "컴퓨터공학",
                "area_name": "운영체제",
                "difficulty": 5,
                "difficulty_level": "보통",
                "question_type": "기본개념",
                "points": 4.0
            }
        ]
    
    def _get_nursing_questions(self) -> List[Dict[str, Any]]:
        """간호학 문제"""
        return [
            {
                "question_id": "NUR_001",
                "question_number": 1,
                "content": "정상 성인의 평균 심박수 범위는?",
                "options": {
                    "1": "40-60회/분",
                    "2": "60-100회/분",
                    "3": "100-120회/분",
                    "4": "120-140회/분",
                    "5": "140-160회/분"
                },
                "correct_answer": "2",
                "subject": "간호학",
                "area_name": "기초간호학",
                "difficulty": 4,
                "difficulty_level": "쉬움",
                "question_type": "기본개념",
                "points": 3.5
            },
            {
                "question_id": "NUR_002",
                "question_number": 2,
                "content": "무균술의 기본 원칙으로 옳지 않은 것은?",
                "options": {
                    "1": "멸균된 물품은 멸균된 것끼리만 접촉해야 한다",
                    "2": "멸균 영역은 시야에서 벗어나면 오염된 것으로 간주한다",
                    "3": "멸균 포장지의 가장자리는 비멸균 영역으로 간주한다",
                    "4": "멸균된 물품을 다룰 때는 일반 장갑을 착용한다",
                    "5": "의심스러우면 오염된 것으로 간주한다"
                },
                "correct_answer": "4",
                "subject": "간호학",
                "area_name": "감염관리",
                "difficulty": 6,
                "difficulty_level": "보통",
                "question_type": "응용",
                "points": 4.0
            },
            {
                "question_id": "NUR_003",
                "question_number": 3,
                "content": "당뇨병 환자의 인슐린 주사 부위로 적절하지 않은 곳은?",
                "options": {
                    "1": "복부",
                    "2": "대퇴부 외측",
                    "3": "상완부 외측",
                    "4": "둔부",
                    "5": "손목 내측"
                },
                "correct_answer": "5",
                "subject": "간호학",
                "area_name": "성인간호학",
                "difficulty": 5,
                "difficulty_level": "보통",
                "question_type": "응용",
                "points": 4.0
            }
        ]
    
    def _get_business_questions(self) -> List[Dict[str, Any]]:
        """경영학 문제"""
        return [
            {
                "question_id": "BUS_001",
                "question_number": 1,
                "content": "마케팅 믹스(Marketing Mix)의 4P에 해당하지 않는 것은?",
                "options": {
                    "1": "Product(제품)",
                    "2": "Price(가격)",
                    "3": "Place(유통)",
                    "4": "Promotion(촉진)",
                    "5": "Process(과정)"
                },
                "correct_answer": "5",
                "subject": "경영학",
                "area_name": "마케팅",
                "difficulty": 4,
                "difficulty_level": "쉬움",
                "question_type": "기본개념",
                "points": 3.5
            },
            {
                "question_id": "BUS_002",
                "question_number": 2,
                "content": "SWOT 분석에서 'T'가 의미하는 것은?",
                "options": {
                    "1": "강점(Strength)",
                    "2": "약점(Weakness)",
                    "3": "기회(Opportunity)",
                    "4": "위협(Threat)",
                    "5": "목표(Target)"
                },
                "correct_answer": "4",
                "subject": "경영학",
                "area_name": "경영전략",
                "difficulty": 3,
                "difficulty_level": "쉬움",
                "question_type": "기본개념",
                "points": 3.0
            }
        ]
    
    def _get_mechanical_engineering_questions(self) -> List[Dict[str, Any]]:
        """기계공학 문제"""
        return [
            {
                "question_id": "ME_001",
                "question_number": 1,
                "content": "열역학 제1법칙이 나타내는 것은?",
                "options": {
                    "1": "에너지 보존 법칙",
                    "2": "엔트로피 증가 법칙",
                    "3": "온도의 절대 영점",
                    "4": "이상기체 법칙",
                    "5": "열전도 법칙"
                },
                "correct_answer": "1",
                "subject": "기계공학",
                "area_name": "열역학",
                "difficulty": 5,
                "difficulty_level": "보통",
                "question_type": "기본개념",
                "points": 4.0
            }
        ]
    
    def _get_mathematics_questions(self) -> List[Dict[str, Any]]:
        """수학 문제"""
        return [
            {
                "question_id": "MATH_001",
                "question_number": 1,
                "content": "함수 f(x) = x² + 2x + 1의 최솟값은?",
                "options": {
                    "1": "-1",
                    "2": "0",
                    "3": "1",
                    "4": "2",
                    "5": "3"
                },
                "correct_answer": "2",
                "subject": "수학",
                "area_name": "미적분학",
                "difficulty": 5,
                "difficulty_level": "보통",
                "question_type": "계산",
                "points": 4.0
            }
        ]
    
    def _get_psychology_questions(self) -> List[Dict[str, Any]]:
        """심리학 문제"""
        return [
            {
                "question_id": "PSY_001",
                "question_number": 1,
                "content": "파블로프의 고전적 조건화 실험에서 사용된 동물은?",
                "options": {
                    "1": "고양이",
                    "2": "개",
                    "3": "쥐",
                    "4": "원숭이",
                    "5": "비둘기"
                },
                "correct_answer": "2",
                "subject": "심리학",
                "area_name": "학습심리학",
                "difficulty": 3,
                "difficulty_level": "쉬움",
                "question_type": "기본개념",
                "points": 3.0
            }
        ]
    
    def _get_law_questions(self) -> List[Dict[str, Any]]:
        """법학 문제"""
        return [
            {
                "question_id": "LAW_001",
                "question_number": 1,
                "content": "대한민국 헌법의 최고 이념은?",
                "options": {
                    "1": "자유민주주의",
                    "2": "사회주의",
                    "3": "공산주의",
                    "4": "무정부주의",
                    "5": "전체주의"
                },
                "correct_answer": "1",
                "subject": "법학",
                "area_name": "헌법",
                "difficulty": 4,
                "difficulty_level": "쉬움",
                "question_type": "기본개념",
                "points": 3.5
            }
        ]
    
    def _get_education_questions(self) -> List[Dict[str, Any]]:
        """교육학 문제"""
        return [
            {
                "question_id": "EDU_001",
                "question_number": 1,
                "content": "브루너(Bruner)의 학습이론에서 강조하는 것은?",
                "options": {
                    "1": "발견학습",
                    "2": "관찰학습",
                    "3": "조건반사학습",
                    "4": "시행착오학습",
                    "5": "잠재학습"
                },
                "correct_answer": "1",
                "subject": "교육학",
                "area_name": "교육심리학",
                "difficulty": 5,
                "difficulty_level": "보통",
                "question_type": "기본개념",
                "points": 4.0
            }
        ]
    
    def _get_fine_arts_questions(self) -> List[Dict[str, Any]]:
        """미술학 문제"""
        return [
            {
                "question_id": "ART_001",
                "question_number": 1,
                "content": "인상주의 화가가 아닌 사람은?",
                "options": {
                    "1": "모네(Monet)",
                    "2": "르누아르(Renoir)",
                    "3": "피카소(Picasso)",
                    "4": "드가(Degas)",
                    "5": "마네(Manet)"
                },
                "correct_answer": "3",
                "subject": "미술학",
                "area_name": "서양미술사",
                "difficulty": 5,
                "difficulty_level": "보통",
                "question_type": "기본개념",
                "points": 4.0
            }
        ]
    
    def _get_generic_questions(self, subject: DiagnosisSubject) -> List[Dict[str, Any]]:
        """기본 문제 템플릿"""
        return [
            {
                "question_id": f"{subject.name}_001",
                "question_number": 1,
                "content": f"{subject.value} 분야의 기본 개념에 대한 문제입니다.",
                "options": {
                    "1": "선택지 1",
                    "2": "선택지 2",
                    "3": "선택지 3",
                    "4": "선택지 4",
                    "5": "선택지 5"
                },
                "correct_answer": "1",
                "subject": subject.value,
                "area_name": "기초",
                "difficulty": 5,
                "difficulty_level": "보통",
                "question_type": "기본개념",
                "points": 4.0
            }
        ]
    
    async def get_or_create_diagnosis_test(
        self, 
        user_department: str, 
        round_number: int = 1
    ) -> Optional[DiagnosisTest]:
        """학과별 진단테스트 조회 또는 생성"""
        
        try:
            subject = self.get_department_subject(user_department)
            if not subject:
                logger.error(f"지원하지 않는 학과: {user_department}")
                return None
            
            # 기존 테스트 조회
            existing_test = self.db.query(DiagnosisTest).filter(
                and_(
                    DiagnosisTest.department == user_department,
                    DiagnosisTest.subject_area == subject.value,
                    DiagnosisTest.status == "active"
                )
            ).first()
            
            if existing_test:
                return existing_test
            
            # 새 테스트 생성
            test_data = self.create_universal_test_data(subject)
            
            new_test = DiagnosisTest(
                title=test_data["test_info"]["title"],
                description=test_data["test_info"]["description"],
                department=user_department,
                subject_area=subject.value,
                test_config={
                    "total_questions": test_data["test_info"]["total_questions"],
                    "time_limit_minutes": test_data["test_info"]["time_limit"],
                    "passing_score": 60,
                    "random_order": True,
                    "allow_retake": True,
                    "max_attempts": 3
                },
                scoring_criteria=test_data["scoring_criteria"],
                analysis_config={
                    "enable_bkt": True,
                    "enable_dkt": False,
                    "enable_irt": True,
                    "adaptive_testing": False,
                    "real_time_feedback": True
                },
                test_metadata={
                    "created_by": "universal_diagnosis_service",
                    "department_category": self._get_department_category(subject),
                    "version": "1.0"
                },
                status="active",
                is_published=True,
                publish_date=datetime.now(),
                total_questions=test_data["test_info"]["total_questions"]
            )
            
            self.db.add(new_test)
            self.db.flush()
            
            # 문제들 생성
            for question_data in test_data["questions"]:
                new_question = DiagnosisQuestion(
                    test_id=new_test.id,
                    question_number=question_data["question_number"],
                    content=question_data["content"],
                    question_type="multiple_choice",
                    options=question_data["options"],
                    correct_answer=question_data["correct_answer"],
                    difficulty_level=question_data["difficulty_level"],
                    subject_area=question_data.get("area_name", subject.value),
                    points=question_data.get("points", 4.0),
                    question_metadata={
                        "source": "universal_diagnosis_service",
                        "difficulty_score": question_data.get("difficulty", 5)
                    }
                )
                self.db.add(new_question)
            
            self.db.commit()
            logger.info(f"새 진단테스트 생성 완료: {user_department}")
            
            return new_test
            
        except Exception as e:
            logger.error(f"진단테스트 생성 실패: {e}")
            self.db.rollback()
            return None
    
    def _get_department_category(self, subject: DiagnosisSubject) -> str:
        """학과 카테고리 반환"""
        for category, subjects in DEPARTMENT_CATEGORIES.items():
            if subject in subjects:
                return category
        return "기타"

# 서비스 인스턴스
def get_universal_diagnosis_service(db: Session) -> UniversalDiagnosisService:
    return UniversalDiagnosisService(db) 