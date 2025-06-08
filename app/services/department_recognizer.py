# -*- coding: utf-8 -*-
"""
학과 자동 인식 서비스

기능:
1. 파일명에서 학과 정보 자동 추출
2. 전국 모든 대학 학과 데이터 활용
3. AI 기반 학과 매칭
"""
import re
import logging
from typing import Optional, Dict, List, Tuple
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)

class DepartmentRecognizer:
    """학과 자동 인식 서비스"""
    
    def __init__(self):
        self.departments_data = None
        self.department_keywords = {}
        self._load_departments_data()
        self._build_keyword_index()
    
    def _load_departments_data(self):
        """전국 대학 학과 데이터 로드"""
        try:
            # 한국대학교육협의회 데이터 경로
            data_dir = Path(__file__).parent.parent.parent.parent / "data"
            univ_data_file = data_dir / "한국대학교육협의회_대학별학과정보_20250108.csv"
            
            if univ_data_file.exists():
                # 여러 인코딩 시도
                encodings = ['utf-8', 'utf-8-sig', 'cp949', 'euc-kr']
                
                for encoding in encodings:
                    try:
                        df = pd.read_csv(univ_data_file, encoding=encoding)
                        
                        # 기존/변경 학과만 필터링 (폐과 제외)
                        df = df[df['학과상태명'].isin(['기존', '변경'])]
                        
                        # 필요한 컬럼만 선택
                        df = df[['학교명', '학과명', '단과대학명', '학위과정명']].copy()
                        df.columns = ['school_name', 'department_name', 'college_name', 'degree_course']
                        
                        # 결측값 처리 및 중복 제거
                        df = df.fillna('')
                        df = df.drop_duplicates(subset=['school_name', 'department_name'])
                        
                        self.departments_data = df
                        logger.info(f"✅ 전국 대학 학과 데이터 로드 완료: {len(df)}개 학과")
                        return
                        
                    except Exception as e:
                        logger.debug(f"인코딩 {encoding} 실패: {e}")
                        continue
            
            # 데이터 파일이 없으면 기본 데이터 사용
            self._load_default_departments()
            
        except Exception as e:
            logger.error(f"학과 데이터 로드 실패: {e}")
            self._load_default_departments()
    
    def _load_default_departments(self):
        """기본 학과 데이터 로드"""
        departments_data = [
            # 의료보건 계열
            {"school_name": "전국대학", "department_name": "의학과", "college_name": "의과대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "간호학과", "college_name": "간호대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "치의학과", "college_name": "치과대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "약학과", "college_name": "약학대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "한의학과", "college_name": "한의과대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "수의학과", "college_name": "수의과대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "물리치료학과", "college_name": "보건대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "작업치료학과", "college_name": "보건대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "임상병리학과", "college_name": "보건대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "방사선학과", "college_name": "보건대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "치위생학과", "college_name": "보건대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "응급구조학과", "college_name": "보건대학", "degree_course": "학사"},
            
            # 공학 계열
            {"school_name": "전국대학", "department_name": "컴퓨터공학과", "college_name": "공과대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "컴퓨터소프트웨어학과", "college_name": "공과대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "전기전자공학과", "college_name": "공과대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "기계공학과", "college_name": "공과대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "건축학과", "college_name": "공과대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "화학공학과", "college_name": "공과대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "산업공학과", "college_name": "공과대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "환경공학과", "college_name": "공과대학", "degree_course": "학사"},
            
            # 사회과학 계열
            {"school_name": "전국대학", "department_name": "경영학과", "college_name": "경영대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "경제학과", "college_name": "사회과학대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "법학과", "college_name": "법과대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "행정학과", "college_name": "사회과학대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "심리학과", "college_name": "사회과학대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "사회복지학과", "college_name": "사회과학대학", "degree_course": "학사"},
            
            # 교육 계열
            {"school_name": "전국대학", "department_name": "유아교육과", "college_name": "교육대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "초등교육과", "college_name": "교육대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "국어교육과", "college_name": "교육대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "영어교육과", "college_name": "교육대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "수학교육과", "college_name": "교육대학", "degree_course": "학사"},
            
            # 자연과학 계열
            {"school_name": "전국대학", "department_name": "수학과", "college_name": "자연과학대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "물리학과", "college_name": "자연과학대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "화학과", "college_name": "자연과학대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "생물학과", "college_name": "자연과학대학", "degree_course": "학사"},
            
            # 예술체육 계열
            {"school_name": "전국대학", "department_name": "미술학과", "college_name": "예술대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "음악학과", "college_name": "예술대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "체육학과", "college_name": "체육대학", "degree_course": "학사"},
            
            # 기타 인기 학과들
            {"school_name": "전국대학", "department_name": "호텔관광경영과", "college_name": "경영대학", "degree_course": "학사"},
            {"school_name": "전국대학", "department_name": "뷰티케어과", "college_name": "예술대학", "degree_course": "전문학사"},
            {"school_name": "전국대학", "department_name": "항공서비스과", "college_name": "공과대학", "degree_course": "전문학사"},
        ]
        
        self.departments_data = pd.DataFrame(departments_data)
        logger.info(f"✅ 기본 학과 데이터 로드 완료: {len(departments_data)}개 학과")
    
    def _build_keyword_index(self):
        """학과별 키워드 인덱스 구축"""
        if self.departments_data is None:
            return
        
        # 학과별 키워드 매핑
        keyword_mappings = {
            # 의료보건 계열
            "의학": ["의대", "의과", "의학", "의사", "doctor", "medical"],
            "간호": ["간호", "nurse", "nursing"],
            "치의학": ["치대", "치과", "치의학", "dental", "dentist"],
            "약학": ["약대", "약학", "pharmacy", "약사"],
            "한의학": ["한의대", "한의학", "korean medicine", "한의사"],
            "수의학": ["수의대", "수의학", "veterinary", "수의사"],
            "물리치료": ["물리치료", "physical therapy", "PT", "재활", "물치"],
            "작업치료": ["작업치료", "occupational therapy", "OT", "작치"],
            "임상병리": ["임상병리", "clinical pathology", "검사", "진단"],
            "방사선": ["방사선", "radiology", "영상", "엑스레이"],
            "치위생": ["치위생", "dental hygiene", "치과위생"],
            "응급구조": ["응급구조", "emergency", "구급", "응급의학"],
            
            # 공학 계열
            "컴퓨터": ["컴퓨터", "computer", "전산", "소프트웨어", "software", "IT", "프로그래밍"],
            "전기전자": ["전기", "전자", "전기전자", "electric", "electronic", "전자공학"],
            "기계": ["기계", "mechanical", "기계공학"],
            "건축": ["건축", "architecture", "건설"],
            "화학공학": ["화학공학", "chemical engineering"],
            "산업공학": ["산업공학", "industrial engineering"],
            "환경공학": ["환경공학", "environmental engineering"],
            
            # 사회과학 계열
            "경영": ["경영", "business", "경영학", "management"],
            "경제": ["경제", "economics", "경제학"],
            "법학": ["법학", "law", "법과", "법률"],
            "행정": ["행정", "public administration", "공공"],
            "심리": ["심리", "psychology", "상담"],
            "사회복지": ["사회복지", "social welfare", "복지"],
            
            # 교육 계열
            "교육": ["교육", "education", "교대"],
            "유아교육": ["유아교육", "early childhood education"],
            
            # 자연과학 계열
            "수학": ["수학", "mathematics", "math"],
            "물리": ["물리", "physics"],
            "화학": ["화학", "chemistry"],
            "생물": ["생물", "biology", "생명과학"],
            
            # 예술체육 계열
            "미술": ["미술", "art", "예술", "디자인"],
            "음악": ["음악", "music"],
            "체육": ["체육", "sports", "운동", "스포츠"],
            
            # 기타
            "관광": ["관광", "tourism", "호텔", "hotel"],
            "뷰티": ["뷰티", "beauty", "미용", "헤어", "네일"],
            "항공": ["항공", "aviation", "항공서비스", "승무원"],
        }
        
        # 실제 학과명과 키워드 매핑
        for _, row in self.departments_data.iterrows():
            dept_name = row['department_name']
            college_name = row['college_name']
            
            # 학과명에서 핵심 키워드 추출
            for keyword_base, keyword_list in keyword_mappings.items():
                for keyword in keyword_list:
                    if keyword in dept_name.lower() or keyword in college_name.lower():
                        if keyword_base not in self.department_keywords:
                            self.department_keywords[keyword_base] = []
                        self.department_keywords[keyword_base].append(dept_name)
        
        logger.info(f"✅ 학과 키워드 인덱스 구축 완료: {len(self.department_keywords)}개 키워드 그룹")
    
    def extract_department_from_filename(self, filename: str) -> Optional[Dict[str, str]]:
        """
        파일명에서 학과 정보 추출
        
        Args:
            filename: 파일명
            
        Returns:
            학과 정보 딕셔너리 또는 None
        """
        
        logger.info(f"🔍 파일명에서 학과 추출 시도: {filename}")
        
        # 기존 하드코딩된 학과들도 포함
        hardcoded_patterns = [
            (r'물리치료사', '물리치료학과'),
            (r'작업치료사', '작업치료학과'),
            (r'간호사', '간호학과'),
            (r'의사', '의학과'),
            (r'치과의사', '치의학과'),
            (r'약사', '약학과'),
            (r'한의사', '한의학과'),
            (r'수의사', '수의학과'),
        ]
        
        # 하드코딩된 패턴 먼저 확인
        for pattern, dept_name in hardcoded_patterns:
            if re.search(pattern, filename):
                dept_info = self._get_department_info(dept_name)
                if dept_info:
                    logger.info(f"✅ 하드코딩 패턴으로 학과 인식: {dept_name}")
                    return dept_info
        
        # 키워드 기반 매칭
        filename_lower = filename.lower()
        
        for keyword_base, dept_list in self.department_keywords.items():
            # 키워드 매칭
            if keyword_base in filename_lower:
                # 가장 일반적인 학과명 선택
                target_dept = dept_list[0] if dept_list else None
                if target_dept:
                    dept_info = self._get_department_info(target_dept)
                    if dept_info:
                        logger.info(f"✅ 키워드 '{keyword_base}'로 학과 인식: {target_dept}")
                        return dept_info
        
        # 직접 학과명 매칭
        if self.departments_data is not None:
            for _, row in self.departments_data.iterrows():
                dept_name = row['department_name']
                # 학과명의 핵심 부분 추출 (예: "물리치료학과" -> "물리치료")
                core_name = dept_name.replace('과', '').replace('학과', '').replace('부', '')
                
                if core_name in filename:
                    dept_info = {
                        'department_name': dept_name,
                        'college_name': row.get('college_name', ''),
                        'degree_course': row.get('degree_course', '학사')
                    }
                    logger.info(f"✅ 직접 매칭으로 학과 인식: {dept_name}")
                    return dept_info
        
        logger.warning(f"❌ 파일명에서 학과 추출 실패: {filename}")
        return None
    
    def _get_department_info(self, department_name: str) -> Optional[Dict[str, str]]:
        """학과명으로 학과 정보 조회"""
        if self.departments_data is None:
            return None
        
        # 정확한 학과명 매칭
        matching_rows = self.departments_data[
            self.departments_data['department_name'] == department_name
        ]
        
        if not matching_rows.empty:
            row = matching_rows.iloc[0]
            return {
                'department_name': row['department_name'],
                'college_name': row.get('college_name', ''),
                'degree_course': row.get('degree_course', '학사')
            }
        
        # 부분 매칭
        matching_rows = self.departments_data[
            self.departments_data['department_name'].str.contains(department_name, na=False)
        ]
        
        if not matching_rows.empty:
            row = matching_rows.iloc[0]
            return {
                'department_name': row['department_name'],
                'college_name': row.get('college_name', ''),
                'degree_course': row.get('degree_course', '학사')
            }
        
        return None
    
    def get_all_departments(self) -> List[Dict[str, str]]:
        """모든 지원 학과 목록 반환"""
        if self.departments_data is None:
            return []
        
        departments = []
        for _, row in self.departments_data.iterrows():
            departments.append({
                'department_name': row['department_name'],
                'college_name': row.get('college_name', ''),
                'degree_course': row.get('degree_course', '학사'),
                'school_name': row.get('school_name', '')
            })
        
        return departments
    
    def search_departments(self, query: str) -> List[Dict[str, str]]:
        """학과명 검색"""
        if self.departments_data is None:
            return []
        
        query_lower = query.lower()
        matching_departments = []
        
        for _, row in self.departments_data.iterrows():
            dept_name = row['department_name']
            if query_lower in dept_name.lower():
                matching_departments.append({
                    'department_name': dept_name,
                    'college_name': row.get('college_name', ''),
                    'degree_course': row.get('degree_course', '학사'),
                    'school_name': row.get('school_name', '')
                })
        
        return matching_departments[:50]  # 상위 50개만 반환

# 전역 인스턴스
department_recognizer = DepartmentRecognizer() 