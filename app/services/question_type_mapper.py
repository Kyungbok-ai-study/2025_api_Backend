#!/usr/bin/env python3
"""
문제 유형 자동 배정 시스템
엑셀 파일을 통해 문제 유형을 자동으로 매핑하는 서비스
"""

import json
import os
import logging
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import re

logger = logging.getLogger(__name__)

class QuestionTypeMapper:
    """문제 유형 자동 배정 시스템"""
    
    def __init__(self):
        # 데이터 디렉토리 설정
        self.data_dir = Path("app/data")
        self.data_dir.mkdir(exist_ok=True)
        
        # 문제 유형 매핑 데이터 파일
        self.type_mapping_file = self.data_dir / "question_type_mapping.json"
        
        # 기본 문제 유형 정의
        self.question_types = {
            "multiple_choice": {
                "name": "객관식",
                "description": "5지선다형 문제",
                "keywords": ["선택하시오", "맞는 것은", "틀린 것은", "올바른 것은", "①", "②", "③", "④", "⑤"],
                "patterns": [r"①.*②.*③.*④.*⑤", r"\d+\.\s+.*\n\d+\.\s+.*", r"가\).*나\).*다\)"]
            },
            "short_answer": {
                "name": "단답형",
                "description": "간단한 답안 서술",
                "keywords": ["서술하시오", "적으시오", "쓰시오", "기술하시오", "무엇인가"],
                "patterns": [r".*\?\s*$", r".*은\?\s*$", r".*인가\?\s*$"]
            },
            "essay": {
                "name": "논술형",
                "description": "장문 서술형 문제",
                "keywords": ["논술하시오", "설명하시오", "분석하시오", "비교하시오", "평가하시오"],
                "patterns": [r".*설명하시오", r".*논술하시오", r".*분석하시오"]
            },
            "true_false": {
                "name": "참/거짓",
                "description": "O/X형 문제",
                "keywords": ["참인지 거짓인지", "O 또는 X", "맞으면 O", "틀리면 X", "옳고 그름"],
                "patterns": [r".*\(O\).*\(X\)", r".*참.*거짓", r".*O.*X"]
            },
            "fill_blank": {
                "name": "빈칸채우기",
                "description": "빈칸을 채우는 문제",
                "keywords": ["빈칸에 들어갈", "괄호 안에", "_____", "□", "○○○"],
                "patterns": [r"_{2,}", r"□+", r"\(\s*\)", r"○{2,}"]
            },
            "matching": {
                "name": "연결형",
                "description": "항목을 연결하는 문제",
                "keywords": ["연결하시오", "짝지으시오", "매칭", "가-나 연결", "왼쪽과 오른쪽"],
                "patterns": [r"가.*나.*다.*라", r"A.*B.*C.*D", r"왼쪽.*오른쪽"]
            }
        }
        
        # 학과별 문제 유형 특성
        self.department_preferences = {
            "간호학과": {
                "multiple_choice": 0.6,  # 60% 객관식
                "short_answer": 0.2,     # 20% 단답형
                "essay": 0.15,           # 15% 논술형
                "true_false": 0.05       # 5% 참/거짓
            },
            "물리치료학과": {
                "multiple_choice": 0.65,
                "short_answer": 0.25,
                "essay": 0.1,
                "true_false": 0.0
            },
            "작업치료학과": {
                "multiple_choice": 0.55,
                "short_answer": 0.25,
                "essay": 0.2,
                "true_false": 0.0
            }
        }
        
        # 기존 매핑 데이터 로드
        self.load_type_mapping_data()
        
        logger.info("✅ 문제 유형 자동 배정 시스템 초기화 완료")
    
    def load_type_mapping_data(self):
        """기존 문제 유형 매핑 데이터 로드"""
        try:
            if self.type_mapping_file.exists():
                with open(self.type_mapping_file, 'r', encoding='utf-8') as f:
                    self.type_mapping_data = json.load(f)
                logger.info(f"✅ 기존 문제 유형 매핑 데이터 로드: {len(self.type_mapping_data)}개 파일")
            else:
                self.type_mapping_data = {}
                logger.info("📝 새로운 문제 유형 매핑 데이터 생성")
        except Exception as e:
            logger.error(f"❌ 문제 유형 매핑 데이터 로드 실패: {e}")
            self.type_mapping_data = {}
    
    def save_type_mapping_data(self):
        """문제 유형 매핑 데이터 저장"""
        try:
            with open(self.type_mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self.type_mapping_data, f, ensure_ascii=False, indent=2)
            logger.info("✅ 문제 유형 매핑 데이터 저장 완료")
        except Exception as e:
            logger.error(f"❌ 문제 유형 매핑 데이터 저장 실패: {e}")
    
    async def process_excel_for_question_types(
        self, 
        excel_file_path: str, 
        professor_name: str,
        department: str = "일반"
    ) -> Dict[str, Any]:
        """
        엑셀 파일에서 문제 유형 자동 배정
        """
        try:
            logger.info(f"📊 문제 유형 엑셀 처리 시작: {excel_file_path}")
            
            # 엑셀 파일 읽기
            df = pd.read_excel(excel_file_path, engine='openpyxl')
            logger.info(f"   📋 엑셀 데이터: {len(df)}행, 컬럼: {list(df.columns)}")
            
            # 문제 유형 분석 수행
            type_analysis = await self._analyze_question_types(df, professor_name, department)
            
            # 결과 저장
            file_key = f"{professor_name}_{Path(excel_file_path).stem}_{datetime.now().strftime('%Y%m%d')}"
            self.type_mapping_data[file_key] = {
                "file_path": excel_file_path,
                "professor": professor_name,
                "department": department,
                "processed_at": datetime.now().isoformat(),
                "total_questions": len(df),
                "type_analysis": type_analysis,
                "type_distribution": self._calculate_type_distribution(type_analysis)
            }
            
            # 매핑 데이터 저장
            self.save_type_mapping_data()
            
            logger.info(f"✅ 문제 유형 엑셀 처리 완료: {len(type_analysis['questions'])}개 문제")
            
            return {
                "success": True,
                "file_key": file_key,
                "total_questions": len(df),
                "type_analysis": type_analysis,
                "message": "문제 유형 자동 배정 완료"
            }
            
        except Exception as e:
            logger.error(f"❌ 문제 유형 엑셀 처리 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "문제 유형 처리 중 오류 발생"
            }
    
    async def _analyze_question_types(
        self, 
        df: pd.DataFrame, 
        professor_name: str,
        department: str
    ) -> Dict[str, Any]:
        """문제 유형 분석 수행"""
        
        type_analysis = {
            "questions": [],
            "type_stats": {},
            "confidence_scores": {},
            "auto_assigned": 0,
            "manual_required": 0
        }
        
        try:
            # 엑셀 컬럼 매핑
            column_mapping = self._map_excel_columns(df)
            logger.info(f"   📊 컬럼 매핑: {column_mapping}")
            
            # 각 문제별 유형 분석
            for idx, row in df.iterrows():
                try:
                    question_data = self._extract_question_data(row, column_mapping, idx)
                    
                    if question_data["content"]:
                        # 문제 유형 자동 판단
                        type_result = self._determine_question_type(
                            question_data["content"], 
                            question_data.get("options", ""),
                            department
                        )
                        
                        question_analysis = {
                            "question_number": idx + 1,
                            "content": question_data["content"][:100] + "..." if len(question_data["content"]) > 100 else question_data["content"],
                            "detected_type": type_result["type"],
                            "confidence": type_result["confidence"],
                            "reasoning": type_result["reasoning"],
                            "alternative_types": type_result["alternatives"],
                            "manual_review_needed": type_result["confidence"] < 0.7
                        }
                        
                        type_analysis["questions"].append(question_analysis)
                        
                        # 통계 업데이트
                        question_type = type_result["type"]
                        if question_type not in type_analysis["type_stats"]:
                            type_analysis["type_stats"][question_type] = 0
                        type_analysis["type_stats"][question_type] += 1
                        
                        # 신뢰도 점수 추가
                        if question_type not in type_analysis["confidence_scores"]:
                            type_analysis["confidence_scores"][question_type] = []
                        type_analysis["confidence_scores"][question_type].append(type_result["confidence"])
                        
                        # 자동/수동 분류 카운트
                        if type_result["confidence"] >= 0.7:
                            type_analysis["auto_assigned"] += 1
                        else:
                            type_analysis["manual_required"] += 1
                
                except Exception as e:
                    logger.warning(f"⚠️ 문제 {idx + 1} 분석 실패: {e}")
                    continue
            
            # 평균 신뢰도 계산
            for qtype, scores in type_analysis["confidence_scores"].items():
                type_analysis["confidence_scores"][qtype] = {
                    "average": sum(scores) / len(scores),
                    "count": len(scores),
                    "min": min(scores),
                    "max": max(scores)
                }
            
        except Exception as e:
            logger.error(f"❌ 문제 유형 분석 실패: {e}")
        
        return type_analysis
    
    def _map_excel_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """엑셀 컬럼 자동 매핑"""
        
        possible_columns = {
            "question": ["문제", "문항", "question", "문제내용", "내용", "지문"],
            "options": ["선택지", "보기", "options", "choices", "답안", "항목"],
            "answer": ["정답", "답", "answer", "correct_answer", "가답안"],
            "type": ["유형", "형태", "type", "분류", "종류"]
        }
        
        column_mapping = {}
        for key, candidates in possible_columns.items():
            for col in df.columns:
                if any(candidate in str(col).lower() for candidate in candidates):
                    column_mapping[key] = col
                    break
        
        return column_mapping
    
    def _extract_question_data(self, row: pd.Series, column_mapping: Dict, idx: int) -> Dict:
        """행에서 문제 데이터 추출"""
        
        return {
            "content": str(row.get(column_mapping.get("question", ""), "")).strip(),
            "options": str(row.get(column_mapping.get("options", ""), "")).strip(), 
            "answer": str(row.get(column_mapping.get("answer", ""), "")).strip(),
            "manual_type": str(row.get(column_mapping.get("type", ""), "")).strip(),
            "row_index": idx
        }
    
    def _determine_question_type(
        self, 
        question_content: str, 
        options: str = "",
        department: str = "일반"
    ) -> Dict[str, Any]:
        """문제 내용을 분석하여 유형 자동 판단"""
        
        type_scores = {}
        reasoning_details = []
        
        # 각 문제 유형별 점수 계산
        for qtype, config in self.question_types.items():
            score = 0
            matched_keywords = []
            matched_patterns = []
            
            # 키워드 매칭
            for keyword in config["keywords"]:
                if keyword in question_content or keyword in options:
                    score += 2
                    matched_keywords.append(keyword)
            
            # 패턴 매칭
            for pattern in config["patterns"]:
                if re.search(pattern, question_content + " " + options):
                    score += 3
                    matched_patterns.append(pattern)
            
            # 학과별 선호도 반영
            dept_prefs = self.department_preferences.get(department, {})
            if qtype in dept_prefs:
                score += dept_prefs[qtype] * 1  # 선호도 보너스
            
            type_scores[qtype] = score
            
            if matched_keywords or matched_patterns:
                reasoning_details.append({
                    "type": qtype,
                    "score": score,
                    "keywords": matched_keywords,
                    "patterns": matched_patterns
                })
        
        # 최고 점수 유형 결정
        if not type_scores or max(type_scores.values()) == 0:
            # 기본값: 학과별 가장 일반적인 유형
            dept_prefs = self.department_preferences.get(department, {})
            if dept_prefs:
                best_type = max(dept_prefs.items(), key=lambda x: x[1])[0]
                confidence = 0.3  # 낮은 신뢰도
            else:
                best_type = "multiple_choice"
                confidence = 0.2
            reasoning = "키워드/패턴 매칭 실패, 기본값 사용"
        else:
            best_type = max(type_scores.items(), key=lambda x: x[1])[0]
            max_score = type_scores[best_type]
            
            # 신뢰도 계산 (0-1 스케일)
            total_possible = 10  # 최대 가능 점수 (키워드 5개 * 2 + 패턴 매칭 보너스)
            confidence = min(max_score / total_possible, 1.0)
            
            reasoning = f"점수: {max_score}, 매칭된 요소들 기반 판단"
        
        # 대안 유형들 (상위 3개)
        sorted_types = sorted(type_scores.items(), key=lambda x: x[1], reverse=True)
        alternatives = [
            {"type": qtype, "score": score, "name": self.question_types[qtype]["name"]} 
            for qtype, score in sorted_types[1:4] if score > 0
        ]
        
        return {
            "type": best_type,
            "confidence": confidence,
            "reasoning": reasoning,
            "alternatives": alternatives,
            "type_scores": type_scores,
            "reasoning_details": reasoning_details
        }
    
    def _calculate_type_distribution(self, type_analysis: Dict) -> Dict[str, Any]:
        """문제 유형 분포 계산"""
        
        total = len(type_analysis["questions"])
        if total == 0:
            return {}
        
        distribution = {}
        for qtype, count in type_analysis["type_stats"].items():
            distribution[qtype] = {
                "count": count,
                "percentage": round((count / total) * 100, 1),
                "name": self.question_types.get(qtype, {}).get("name", qtype)
            }
        
        return distribution
    
    def get_question_type_for_question(
        self, 
        question_content: str, 
        file_key: str = None,
        question_number: int = None
    ) -> str:
        """
        특정 문제의 유형 조회 (파서에서 사용)
        """
        try:
            # 파일별 매핑 데이터에서 조회
            if file_key and file_key in self.type_mapping_data:
                mapping_data = self.type_mapping_data[file_key]
                questions = mapping_data.get("type_analysis", {}).get("questions", [])
                
                # 문제 번호로 조회
                if question_number:
                    for q in questions:
                        if q.get("question_number") == question_number:
                            return q.get("detected_type", "multiple_choice")
                
                # 내용 유사도로 조회
                for q in questions:
                    if question_content and len(question_content) > 20:
                        # 간단한 유사도 체크 (첫 50자 비교)
                        if question_content[:50] in q.get("content", ""):
                            return q.get("detected_type", "multiple_choice")
            
            # 실시간 분석
            type_result = self._determine_question_type(question_content)
            return type_result["type"]
            
        except Exception as e:
            logger.warning(f"⚠️ 문제 유형 조회 실패: {e}")
            return "multiple_choice"  # 기본값
    
    def get_type_mapping_summary(self) -> Dict[str, Any]:
        """문제 유형 매핑 현황 요약"""
        
        summary = {
            "total_files": len(self.type_mapping_data),
            "total_questions": 0,
            "type_distribution": {},
            "department_stats": {},
            "confidence_analysis": {
                "high_confidence": 0,    # >= 0.8
                "medium_confidence": 0,  # 0.5-0.8
                "low_confidence": 0      # < 0.5
            },
            "recent_files": []
        }
        
        try:
            for file_key, data in self.type_mapping_data.items():
                questions = data.get("type_analysis", {}).get("questions", [])
                summary["total_questions"] += len(questions)
                
                # 학과별 통계
                dept = data.get("department", "일반")
                if dept not in summary["department_stats"]:
                    summary["department_stats"][dept] = {"files": 0, "questions": 0}
                summary["department_stats"][dept]["files"] += 1
                summary["department_stats"][dept]["questions"] += len(questions)
                
                # 유형별 분포
                for q in questions:
                    qtype = q.get("detected_type", "unknown")
                    if qtype not in summary["type_distribution"]:
                        summary["type_distribution"][qtype] = 0
                    summary["type_distribution"][qtype] += 1
                    
                    # 신뢰도 분석
                    confidence = q.get("confidence", 0)
                    if confidence >= 0.8:
                        summary["confidence_analysis"]["high_confidence"] += 1
                    elif confidence >= 0.5:
                        summary["confidence_analysis"]["medium_confidence"] += 1
                    else:
                        summary["confidence_analysis"]["low_confidence"] += 1
                
                # 최근 파일 목록 (상위 5개)
                summary["recent_files"].append({
                    "file_key": file_key,
                    "professor": data.get("professor"),
                    "department": data.get("department"),
                    "processed_at": data.get("processed_at"),
                    "question_count": len(questions)
                })
            
            # 최근 파일 정렬
            summary["recent_files"] = sorted(
                summary["recent_files"], 
                key=lambda x: x["processed_at"], 
                reverse=True
            )[:5]
            
        except Exception as e:
            logger.error(f"❌ 문제 유형 매핑 요약 생성 실패: {e}")
        
        return summary

# 싱글톤 인스턴스
question_type_mapper = QuestionTypeMapper() 