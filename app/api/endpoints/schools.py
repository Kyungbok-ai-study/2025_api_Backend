"""
학교 정보 API 엔드포인트
CSV 파일을 활용한 학교 및 학과 정보 제공
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import pandas as pd
import os
from pathlib import Path
from pydantic import BaseModel
import re

router = APIRouter()

# 데이터 파일 경로
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"

class SchoolInfo(BaseModel):
    school_name: str
    school_code: str
    area_name: str
    school_type: str

class DepartmentInfo(BaseModel):
    department_name: str
    college_name: str
    department_code: str
    degree_course: str
    study_period: str
    department_characteristic: str

class SchoolDetailResponse(BaseModel):
    school_info: SchoolInfo
    departments: List[DepartmentInfo]

# 한글 초성 추출 함수
def get_initial_consonants(text):
    """한글 텍스트에서 초성을 추출합니다."""
    initials = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
    result = ''
    
    for char in text:
        code = ord(char)
        if 0xAC00 <= code <= 0xD7A3:  # 한글 완성형
            initial_index = (code - 0xAC00) // 588
            result += initials[initial_index]
        elif char in initials:  # 이미 초성인 경우
            result += char
        else:  # 한글이 아닌 경우
            result += char
    
    return result

def is_matching_search(school_name, search_term):
    """검색어와 학교명이 매칭되는지 확인합니다."""
    search_lower = search_term.lower()
    school_lower = school_name.lower()
    
    # 1. 직접 포함 검사
    if search_lower in school_lower:
        return True
    
    # 2. 초성 검사
    school_initials = get_initial_consonants(school_name)
    search_initials = get_initial_consonants(search_term)
    
    if search_initials in school_initials:
        return True
    
    # 3. 부분 매칭
    for i in range(len(school_name) - len(search_term) + 1):
        substring = school_name[i:i + len(search_term)]
        if get_initial_consonants(substring) == search_initials:
            return True
    
    return False

def load_schools_data():
    """학교 데이터를 로드합니다."""
    try:
        # CSV 파일이 있는지 확인
        schools_file = DATA_DIR / "schools.csv"
        if schools_file.exists():
            print(f"[DEBUG] CSV 파일 경로: {schools_file}")
            
            # 여러 인코딩 시도
            encodings = ['utf-8', 'utf-8-sig', 'cp949', 'euc-kr']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(schools_file, encoding=encoding)
                    print(f"[DEBUG] {encoding} 인코딩으로 파일 로드 성공")
                    break
                except Exception as e:
                    print(f"[DEBUG] {encoding} 인코딩 실패: {e}")
                    continue
            
            if df is None:
                print("[ERROR] 모든 인코딩 시도 실패")
                return get_default_schools_data()
            
            print(f"[DEBUG] CSV 파일에서 로드된 학교 수: {len(df)}")
            print(f"[DEBUG] 첫 5개 학교: {df.head()['school_name'].tolist()}")
            
            # 경복대학교가 있는지 확인
            kyungbok_rows = df[df['school_name'].str.contains('경복', na=False)]
            print(f"[DEBUG] '경복' 포함 학교: {kyungbok_rows['school_name'].tolist()}")
            
            return df
        else:
            print(f"[WARNING] CSV 파일이 없습니다: {schools_file}")
            # CSV 파일이 없으면 기본 데이터 반환
            return get_default_schools_data()
    except Exception as e:
        print(f"학교 데이터 로드 오류: {e}")
        return get_default_schools_data()

def load_departments_data():
    """학과 데이터를 로드합니다."""
    try:
        # 한국대학교육협의회 CSV 파일 경로
        univ_data_file = DATA_DIR / "한국대학교육협의회_대학별학과정보_20250108.csv"
        
        if univ_data_file.exists():
            print(f"[DEBUG] 대학 학과 정보 CSV 파일 경로: {univ_data_file}")
            
            # 여러 인코딩 시도
            encodings = ['utf-8', 'utf-8-sig', 'cp949', 'euc-kr']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(univ_data_file, encoding=encoding)
                    print(f"[DEBUG] {encoding} 인코딩으로 파일 로드 성공")
                    break
                except Exception as e:
                    print(f"[DEBUG] {encoding} 인코딩 실패: {e}")
                    continue
            
            if df is None:
                print("[ERROR] 모든 인코딩 시도 실패")
                return get_default_departments_data()
            
            # 필요한 컬럼만 선택하고 컬럼명 변경
            # 학과상태명이 '기존' 또는 '변경'인 것만 필터링 (폐과 제외)
            df = df[df['학과상태명'].isin(['기존', '변경'])]
            
            df = df[['학교명', '학과명', '단과대학명', '학위과정명', '수업연한', '주야과정명']].copy()
            df.columns = ['school_name', 'department_name', 'college_name', 'degree_course', 'study_period', 'day_night']
            
            # 결측값 처리
            df = df.fillna('')
            
            # 중복 제거 (같은 학교의 같은 학과명)
            df = df.drop_duplicates(subset=['school_name', 'department_name'])
            
            print(f"[DEBUG] 로드된 학과 수: {len(df)}")
            
            return df
        else:
            print(f"[WARNING] 대학 학과 정보 CSV 파일이 없습니다: {univ_data_file}")
            # 기존 departments.csv 파일 확인
            departments_file = DATA_DIR / "departments.csv"
            if departments_file.exists():
                df = pd.read_csv(departments_file, encoding='utf-8')
                return df
            else:
                return get_default_departments_data()
    except Exception as e:
        print(f"학과 데이터 로드 오류: {e}")
        return get_default_departments_data()

def get_default_schools_data():
    """기본 학교 데이터를 반환합니다."""
    schools_data = [
        {"school_name": "서울대학교", "area_name": "서울특별시", "school_type": "국립대학교"},
        {"school_name": "연세대학교", "area_name": "서울특별시", "school_type": "사립대학교"},
        {"school_name": "고려대학교", "area_name": "서울특별시", "school_type": "사립대학교"},
        {"school_name": "성균관대학교", "area_name": "서울특별시", "school_type": "사립대학교"},
        {"school_name": "한양대학교", "area_name": "서울특별시", "school_type": "사립대학교"},
        {"school_name": "중앙대학교", "area_name": "서울특별시", "school_type": "사립대학교"},
        {"school_name": "경희대학교", "area_name": "서울특별시", "school_type": "사립대학교"},
        {"school_name": "한국외국어대학교", "area_name": "서울특별시", "school_type": "사립대학교"},
        {"school_name": "서강대학교", "area_name": "서울특별시", "school_type": "사립대학교"},
        {"school_name": "동국대학교", "area_name": "서울특별시", "school_type": "사립대학교"},
        {"school_name": "홍익대학교", "area_name": "서울특별시", "school_type": "사립대학교"},
        {"school_name": "건국대학교", "area_name": "서울특별시", "school_type": "사립대학교"},
        {"school_name": "국민대학교", "area_name": "서울특별시", "school_type": "사립대학교"},
        {"school_name": "숭실대학교", "area_name": "서울특별시", "school_type": "사립대학교"},
        {"school_name": "세종대학교", "area_name": "서울특별시", "school_type": "사립대학교"},
        {"school_name": "이화여자대학교", "area_name": "서울특별시", "school_type": "사립대학교"},
        {"school_name": "숙명여자대학교", "area_name": "서울특별시", "school_type": "사립대학교"},
        {"school_name": "부산대학교", "area_name": "부산광역시", "school_type": "국립대학교"},
        {"school_name": "경북대학교", "area_name": "대구광역시", "school_type": "국립대학교"},
        {"school_name": "전남대학교", "area_name": "광주광역시", "school_type": "국립대학교"},
        {"school_name": "충남대학교", "area_name": "대전광역시", "school_type": "국립대학교"},
        {"school_name": "인하대학교", "area_name": "인천광역시", "school_type": "사립대학교"},
        {"school_name": "아주대학교", "area_name": "경기도", "school_type": "사립대학교"},
        {"school_name": "단국대학교", "area_name": "경기도", "school_type": "사립대학교"},
        {"school_name": "가천대학교", "area_name": "경기도", "school_type": "사립대학교"},
        {"school_name": "경복대학교", "area_name": "경기도", "school_type": "전문대학"},
        {"school_name": "KAIST", "area_name": "대전광역시", "school_type": "과학기술원"},
        {"school_name": "POSTECH", "area_name": "경상북도", "school_type": "과학기술원"},
        {"school_name": "GIST", "area_name": "광주광역시", "school_type": "과학기술원"},
        {"school_name": "UNIST", "area_name": "울산광역시", "school_type": "과학기술원"},
    ]
    return pd.DataFrame(schools_data)

def get_default_departments_data():
    """기본 학과 데이터를 반환합니다."""
    departments_data = [
        # 서울대학교
        {"school_name": "서울대학교", "department_name": "컴퓨터공학부", "college_name": "공과대학", "degree_course": "학사", "study_period": "4년", "department_characteristic": ""},
        {"school_name": "서울대학교", "department_name": "전기정보공학부", "college_name": "공과대학", "degree_course": "학사", "study_period": "4년", "department_characteristic": ""},
        {"school_name": "서울대학교", "department_name": "기계공학부", "college_name": "공과대학", "degree_course": "학사", "study_period": "4년", "department_characteristic": ""},
        {"school_name": "서울대학교", "department_name": "경영학과", "college_name": "경영대학", "degree_course": "학사", "study_period": "4년", "department_characteristic": ""},
        {"school_name": "서울대학교", "department_name": "경제학부", "college_name": "사회과학대학", "degree_course": "학사", "study_period": "4년", "department_characteristic": ""},
        
        # 연세대학교
        {"school_name": "연세대학교", "department_name": "컴퓨터과학과", "college_name": "공과대학", "degree_course": "학사", "study_period": "4년", "department_characteristic": ""},
        {"school_name": "연세대학교", "department_name": "전기전자공학부", "college_name": "공과대학", "degree_course": "학사", "study_period": "4년", "department_characteristic": ""},
        {"school_name": "연세대학교", "department_name": "경영학과", "college_name": "경영대학", "degree_course": "학사", "study_period": "4년", "department_characteristic": ""},
        {"school_name": "연세대학교", "department_name": "의학과", "college_name": "의과대학", "degree_course": "학사", "study_period": "6년", "department_characteristic": ""},
        
        # 고려대학교
        {"school_name": "고려대학교", "department_name": "컴퓨터학과", "college_name": "정보대학", "degree_course": "학사", "study_period": "4년", "department_characteristic": ""},
        {"school_name": "고려대학교", "department_name": "전기전자공학부", "college_name": "공과대학", "degree_course": "학사", "study_period": "4년", "department_characteristic": ""},
        {"school_name": "고려대학교", "department_name": "경영학과", "college_name": "경영대학", "degree_course": "학사", "study_period": "4년", "department_characteristic": ""},
        {"school_name": "고려대학교", "department_name": "법학과", "college_name": "법과대학", "degree_course": "학사", "study_period": "4년", "department_characteristic": ""},
        
        # 경복대학교
        {"school_name": "경복대학교", "department_name": "컴퓨터소프트웨어학과", "college_name": "IT융합학부", "degree_course": "전문학사", "study_period": "2년", "department_characteristic": ""},
        {"school_name": "경복대학교", "department_name": "간호학과", "college_name": "보건학부", "degree_course": "학사", "study_period": "4년", "department_characteristic": ""},
        {"school_name": "경복대학교", "department_name": "유아교육과", "college_name": "사회복지학부", "degree_course": "전문학사", "study_period": "3년", "department_characteristic": ""},
        {"school_name": "경복대학교", "department_name": "호텔관광경영과", "college_name": "경영학부", "degree_course": "전문학사", "study_period": "2년", "department_characteristic": ""},
        {"school_name": "경복대학교", "department_name": "뷰티케어과", "college_name": "예술학부", "degree_course": "전문학사", "study_period": "2년", "department_characteristic": ""},
    ]
    return pd.DataFrame(departments_data)

@router.get("/schools/search")
async def search_schools(
    query: str = Query(..., description="학교명 검색어")
):
    """
    학교명으로 학교 검색 (한글 초성 검색 지원)
    """
    try:
        # 학교 데이터 로드
        schools_df = load_schools_data()
        
        print(f"[DEBUG] 검색어: {query}")
        print(f"[DEBUG] 로드된 학교 수: {len(schools_df)}")
        
        if schools_df.empty:
            return {"success": False, "data": [], "total_count": 0}
        
        # 검색어가 매우 짧은 경우 인기 학교 반환
        if len(query.strip()) == 0:
            return await get_popular_schools()
        
        # 초성만 입력한 경우 인기 학교 반환
        if query in ['ㄱ', 'ㄴ', 'ㄷ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅅ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']:
            return await get_popular_schools()
        
        # 검색 수행
        matching_schools = []
        for idx, row in schools_df.iterrows():
            school_name = str(row['school_name'])
            if is_matching_search(school_name, query):
                print(f"[DEBUG] 매칭된 학교: {school_name}")
                school_info = {
                    "school_name": school_name,
                    "school_code": f"SCH_{hash(school_name) % 1000000:06d}",
                    "area_name": str(row.get('area_name', '')),
                    "school_type": str(row.get('school_type', ''))
                }
                matching_schools.append(school_info)
        
        print(f"[DEBUG] 매칭된 학교 수: {len(matching_schools)}")
        
        # 관련성에 따라 정렬
        def relevance_score(school_name, search_term):
            name_lower = school_name.lower()
            term_lower = search_term.lower()
            
            if name_lower.startswith(term_lower):
                return 100
            elif term_lower in name_lower:
                return 50
            else:
                return 0
        
        matching_schools.sort(key=lambda x: relevance_score(x["school_name"], query), reverse=True)
        
        # 상위 50개만 반환
        matching_schools = matching_schools[:50]
        
        result = {
            "success": True,
            "data": matching_schools,
            "total_count": len(matching_schools)
        }
        
        print(f"[DEBUG] 최종 응답: {result}")
        
        return result
        
    except Exception as e:
        print(f"[ERROR] 검색 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@router.get("/schools/{school_name}/departments")
async def get_school_departments(
    school_name: str,
    query: Optional[str] = Query(None, description="학과명 검색어")
):
    """
    특정 학교의 학과 정보 조회 (검색 기능 포함)
    """
    try:
        # 학과 데이터 로드
        departments_df = load_departments_data()
        
        if departments_df.empty:
            raise HTTPException(status_code=404, detail="학과 정보를 찾을 수 없습니다")
        
        # 해당 학교의 학과 필터링
        school_departments = departments_df[departments_df['school_name'] == school_name]
        
        if school_departments.empty:
            raise HTTPException(status_code=404, detail="해당 학교의 학과 정보를 찾을 수 없습니다")
        
        # 검색어가 있으면 필터링
        if query:
            # 학과명에서 검색 (초성 검색 포함)
            matching_departments = []
            for _, row in school_departments.iterrows():
                dept_name = str(row['department_name'])
                if is_matching_search(dept_name, query):
                    matching_departments.append(row)
            
            if matching_departments:
                school_departments = pd.DataFrame(matching_departments)
            else:
                school_departments = pd.DataFrame()  # 빈 데이터프레임
        
        # 학교 정보 생성
        schools_df = load_schools_data()
        school_info_row = schools_df[schools_df['school_name'] == school_name]
        
        if school_info_row.empty:
            school_info = SchoolInfo(
                school_name=school_name,
                school_code=f"SCH_{hash(school_name) % 1000000:06d}",
                area_name="",
                school_type=""
            )
        else:
            row = school_info_row.iloc[0]
            school_info = SchoolInfo(
                school_name=school_name,
                school_code=f"SCH_{hash(school_name) % 1000000:06d}",
                area_name=str(row.get('area_name', '')),
                school_type=str(row.get('school_type', ''))
            )
        
        # 학과 정보 생성
        departments = []
        for _, row in school_departments.iterrows():
            # 학위과정과 수업연한 정보 조합
            degree_info = str(row.get('degree_course', ''))
            study_period_info = str(row.get('study_period', ''))
            day_night_info = str(row.get('day_night', ''))
            
            # department_characteristic에 주야과정 정보 포함
            characteristic = day_night_info if day_night_info else ""
            
            department = DepartmentInfo(
                department_name=str(row['department_name']),
                college_name=str(row.get('college_name', '')),
                department_code=f"DEPT_{hash(str(row['department_name'])) % 1000000:06d}",
                degree_course=degree_info,
                study_period=study_period_info,
                department_characteristic=characteristic
            )
            departments.append(department)
        
        # 학과명 가나다순 정렬
        departments.sort(key=lambda x: x.department_name)
        
        return {
            "success": True,
            "data": SchoolDetailResponse(
                school_info=school_info,
                departments=departments
            )
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@router.get("/schools/popular")
async def get_popular_schools():
    """
    인기 대학교 목록 반환
    """
    try:
        schools_df = load_schools_data()
        
        # 인기 학교 목록 (상위 20개)
        popular_schools = []
        for _, row in schools_df.head(20).iterrows():
            school_info = {
                "school_name": str(row['school_name']),
                "school_code": f"SCH_{hash(str(row['school_name'])) % 1000000:06d}",
                "area_name": str(row.get('area_name', '')),
                "school_type": str(row.get('school_type', ''))
            }
            popular_schools.append(school_info)
        
        return {
            "success": True,
            "data": popular_schools,
            "total_count": len(popular_schools)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}") 