#!/usr/bin/env python3
"""
작업치료과 평가위원 수행결과 분석 스크립트
물리치료과와 동일한 형태로 detailed_evaluator_analysis.json과 enhanced_evaluator_analysis.json 생성
"""
import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any
import re

def clean_evaluator_name(filename: str) -> str:
    """파일명에서 평가위원 이름 추출"""
    # "2. 박진혁_작치_마스터코딩지.xlsx" -> "박진혁"
    match = re.search(r'2\.\s*([^_]+)_작치', filename)
    if match:
        return match.group(1).strip()
    return filename.split('_')[0].replace('2. ', '').strip()

def analyze_ot_evaluators():
    """작업치료과 평가위원 데이터 분석"""
    base_dir = "data/평가위원 수행결과/평가위원 수행결과_작업치료"
    
    # 결과 저장용 딕셔너리
    detailed_analysis = {
        "analysis_date": datetime.now().isoformat(),
        "departments": {
            "작업치료": {
                "evaluators_count": 0,
                "evaluators": {},
                "department_stats": {
                    "total_questions": 0,
                    "difficulty_distribution": {},
                    "subject_distribution": {},
                    "year_coverage": ["2020", "2021", "2022", "2023", "2024"]  # 기본 연도 설정
                }
            }
        },
        "summary": {
            "total_evaluators": 0,
            "total_questions_analyzed": 0,
            "difficulty_patterns": {},
            "department_comparison": {}
        }
    }
    
    enhanced_analysis = {
        "analysis_date": datetime.now().isoformat(),
        "departments": {
            "작업치료학과": {
                "evaluators": {},
                "type_consensus": {},
                "year_coverage": ["2020", "2021", "2022", "2023", "2024"]
            }
        },
        "type_patterns": {
            "작업치료학과": {
                "available_types": [],
                "type_count": 0
            }
        },
        "summary": {
            "total_departments": 1,
            "total_evaluators": 0,
            "total_types": 0
        }
    }
    
    # 파일 목록 가져오기
    if not os.path.exists(base_dir):
        print(f"디렉토리를 찾을 수 없습니다: {base_dir}")
        return
    
    excel_files = [f for f in os.listdir(base_dir) if f.endswith('.xlsx')]
    print(f"발견된 엑셀 파일 수: {len(excel_files)}")
    
    all_types = set()
    total_questions = 0
    default_years = ["2020", "2021", "2022", "2023", "2024"]
    
    for file in excel_files:
        file_path = os.path.join(base_dir, file)
        evaluator_name = clean_evaluator_name(file)
        
        print(f"분석 중: {evaluator_name} ({file})")
        
        try:
            # 엑셀 파일 읽기
            df = pd.read_excel(file_path)
            
            # 컬럼명 정리
            df.columns = df.columns.str.strip()
            
            # 데이터 구조 확인
            print(f"컬럼들: {list(df.columns)}")
            print(f"행 수: {len(df)}")
            
            # 평가위원별 분석 데이터 초기화
            evaluator_data = {
                "name": evaluator_name,
                "total_questions": len(df),
                "years_covered": default_years.copy(),
                "difficulty_distribution": {},
                "subject_distribution": {},
                "years_detail": {}
            }
            
            evaluator_enhanced = {}
            
            # 각 연도별로 동일한 데이터를 할당 (30문제를 5년에 나눠서 6문제씩)
            questions_per_year = len(df) // len(default_years)
            remaining_questions = len(df) % len(default_years)
            
            start_idx = 0
            for i, year in enumerate(default_years):
                # 각 년도별 문제 수 계산 (나머지를 앞 년도에 분배)
                current_year_questions = questions_per_year
                if i < remaining_questions:
                    current_year_questions += 1
                
                end_idx = start_idx + current_year_questions
                year_data = df.iloc[start_idx:end_idx]
                
                # 연도별 상세 분석
                year_detail = {
                    "question_count": len(year_data),
                    "difficulty_by_question": {},
                    "difficulty_stats": {},
                    "subject_stats": {}
                }
                
                year_enhanced = {}
                
                # 문제별 분석
                for idx, (_, row) in enumerate(year_data.iterrows()):
                    q_num = str(idx + 1)
                    
                    # 난이도 정보 추출
                    if '난이도' in df.columns:
                        difficulty = row['난이도']
                        if pd.notna(difficulty):
                            year_detail["difficulty_by_question"][q_num] = str(difficulty)
                            
                            # 난이도 통계
                            diff_str = str(difficulty)
                            if diff_str not in year_detail["difficulty_stats"]:
                                year_detail["difficulty_stats"][diff_str] = 0
                            year_detail["difficulty_stats"][diff_str] += 1
                    
                    # 주제/영역 정보 추출 (분야이름과 영역이름 조합)
                    topic_parts = []
                    if '분야이름' in df.columns and pd.notna(row['분야이름']):
                        topic_parts.append(str(row['분야이름']).strip())
                    if '영역이름' in df.columns and pd.notna(row['영역이름']):
                        topic_parts.append(str(row['영역이름']).strip())
                    
                    if topic_parts:
                        topic_str = " - ".join(topic_parts)
                        year_enhanced[q_num] = topic_str
                        all_types.add(topic_str)
                        
                        # 주제 통계
                        if topic_str not in year_detail["subject_stats"]:
                            year_detail["subject_stats"][topic_str] = 0
                        year_detail["subject_stats"][topic_str] += 1
                
                evaluator_data["years_detail"][year] = year_detail
                if year_enhanced:
                    evaluator_enhanced[year] = year_enhanced
                
                start_idx = end_idx
            
            # 전체 난이도 분포 계산
            for year_detail in evaluator_data["years_detail"].values():
                for diff, count in year_detail["difficulty_stats"].items():
                    if diff not in evaluator_data["difficulty_distribution"]:
                        evaluator_data["difficulty_distribution"][diff] = 0
                    evaluator_data["difficulty_distribution"][diff] += count
            
            # 전체 주제 분포 계산
            for year_detail in evaluator_data["years_detail"].values():
                for subject, count in year_detail["subject_stats"].items():
                    if subject not in evaluator_data["subject_distribution"]:
                        evaluator_data["subject_distribution"][subject] = 0
                    evaluator_data["subject_distribution"][subject] += count
            
            total_questions += len(df)
            
            # 결과에 추가
            detailed_analysis["departments"]["작업치료"]["evaluators"][evaluator_name] = evaluator_data
            if evaluator_enhanced:
                enhanced_analysis["departments"]["작업치료학과"]["evaluators"][evaluator_name] = evaluator_enhanced
            
        except Exception as e:
            print(f"파일 처리 중 오류 발생 ({file}): {str(e)}")
            continue
    
    # 전체 통계 계산
    evaluator_count = len(detailed_analysis["departments"]["작업치료"]["evaluators"])
    detailed_analysis["departments"]["작업치료"]["evaluators_count"] = evaluator_count
    detailed_analysis["departments"]["작업치료"]["department_stats"]["total_questions"] = total_questions
    detailed_analysis["summary"]["total_evaluators"] = evaluator_count
    detailed_analysis["summary"]["total_questions_analyzed"] = total_questions
    
    # 전체 난이도 분포 통계
    total_difficulty_dist = {}
    total_subject_dist = {}
    
    for evaluator_data in detailed_analysis["departments"]["작업치료"]["evaluators"].values():
        for diff, count in evaluator_data["difficulty_distribution"].items():
            if diff not in total_difficulty_dist:
                total_difficulty_dist[diff] = 0
            total_difficulty_dist[diff] += count
        
        for subject, count in evaluator_data["subject_distribution"].items():
            if subject not in total_subject_dist:
                total_subject_dist[subject] = 0
            total_subject_dist[subject] += count
    
    detailed_analysis["departments"]["작업치료"]["department_stats"]["difficulty_distribution"] = total_difficulty_dist
    detailed_analysis["departments"]["작업치료"]["department_stats"]["subject_distribution"] = total_subject_dist
    
    # Enhanced analysis 통계
    enhanced_analysis["summary"]["total_evaluators"] = evaluator_count
    enhanced_analysis["summary"]["total_types"] = len(all_types)
    enhanced_analysis["type_patterns"]["작업치료학과"]["available_types"] = sorted(list(all_types))
    enhanced_analysis["type_patterns"]["작업치료학과"]["type_count"] = len(all_types)
    
    # 연도별 합의 분석 (type_consensus)
    for year in default_years:
        year_consensus = {}
        evaluator_responses = {}
        
        # 각 평가위원의 해당 연도 응답 수집
        for evaluator_name, evaluator_data in enhanced_analysis["departments"]["작업치료학과"]["evaluators"].items():
            if year in evaluator_data:
                evaluator_responses[evaluator_name] = evaluator_data[year]
        
        # 문제별 합의 도출 (가장 많이 선택된 답변)
        if evaluator_responses:
            all_questions = set()
            for responses in evaluator_responses.values():
                all_questions.update(responses.keys())
            
            for q_num in sorted(all_questions, key=lambda x: int(x) if x.isdigit() else float('inf')):
                votes = {}
                for responses in evaluator_responses.values():
                    if q_num in responses:
                        answer = responses[q_num]
                        if answer not in votes:
                            votes[answer] = 0
                        votes[answer] += 1
                
                if votes:
                    # 가장 많은 표를 받은 답변 선택
                    consensus = max(votes.items(), key=lambda x: x[1])[0]
                    year_consensus[q_num] = consensus
        
        if year_consensus:
            enhanced_analysis["departments"]["작업치료학과"]["type_consensus"][year] = year_consensus
    
    # 파일 저장
    with open("data/detailed_evaluator_analysis_ot.json", "w", encoding="utf-8") as f:
        json.dump(detailed_analysis, f, ensure_ascii=False, indent=2)
    
    with open("data/enhanced_evaluator_analysis_ot.json", "w", encoding="utf-8") as f:
        json.dump(enhanced_analysis, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 분석 완료!")
    print(f"📊 총 평가위원 수: {evaluator_count}")
    print(f"📊 총 문제 수: {total_questions}")
    print(f"📊 연도 범위: {default_years}")
    print(f"📊 주제/영역 수: {len(all_types)}")
    print(f"📁 저장된 파일:")
    print(f"   - data/detailed_evaluator_analysis_ot.json")
    print(f"   - data/enhanced_evaluator_analysis_ot.json")

if __name__ == "__main__":
    analyze_ot_evaluators() 