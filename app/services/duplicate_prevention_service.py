"""
국가고시 문제 중복 방지 서비스
- 기존 국가고시 문제와의 유사도 검사
- AI 기반 내용 분석 및 중복 탐지
- 새로운 문제 생성시 실시간 검증
- 학습된 패턴 활용한 다양성 보장
"""
import json
import logging
import hashlib
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import text, and_, func

from ..models.question import Question

logger = logging.getLogger(__name__)

@dataclass
class SimilarityResult:
    """유사도 검사 결과"""
    is_duplicate: bool
    similarity_score: float
    similar_question_id: Optional[int]
    similar_content: Optional[str]
    reason: str
    
@dataclass
class QuestionPattern:
    """문제 패턴 분석 결과"""
    content_hash: str
    keywords: List[str]
    structure_pattern: str
    difficulty_level: str
    subject_area: str

class DuplicatePreventionService:
    """국가고시 문제 중복 방지 서비스"""
    
    def __init__(self):
        self.national_exam_cache = {}  # 국가고시 문제 캐시
        self.similarity_threshold = 0.8  # 중복 판정 임계값
        self.pattern_cache = {}  # 패턴 캐시
        
        # 학습된 분석 데이터 로드
        self.evaluator_data = self._load_evaluator_analysis()
        
    def _load_evaluator_analysis(self) -> Dict[str, Any]:
        """평가위원 분석 데이터 로드"""
        try:
            data_path = Path("data")
            analysis_data = {}
            
            # 물리치료학과 데이터
            pt_detailed = data_path / "detailed_evaluator_analysis.json"
            if pt_detailed.exists():
                with open(pt_detailed, 'r', encoding='utf-8') as f:
                    analysis_data["물리치료학과"] = json.load(f)
            
            # 작업치료학과 데이터  
            ot_detailed = data_path / "detailed_evaluator_analysis_ot.json"
            if ot_detailed.exists():
                with open(ot_detailed, 'r', encoding='utf-8') as f:
                    analysis_data["작업치료학과"] = json.load(f)
            
            logger.info(f"📊 평가위원 분석 데이터 로드: {len(analysis_data)}개 학과")
            return analysis_data
            
        except Exception as e:
            logger.error(f"평가위원 데이터 로드 실패: {e}")
            return {}
    
    async def check_duplicate_against_national_exams(
        self, 
        db: Session,
        question_content: str,
        department: str,
        options: Optional[Dict[str, str]] = None
    ) -> SimilarityResult:
        """국가고시 문제와의 중복 검사"""
        
        try:
            # 1단계: 데이터베이스의 기존 문제들과 비교
            db_similarity = await self._check_db_similarity(db, question_content, department)
            
            if db_similarity.is_duplicate:
                return db_similarity
            
            # 2단계: 분석 데이터의 패턴과 비교  
            pattern_similarity = await self._check_pattern_similarity(question_content, department)
            
            if pattern_similarity.is_duplicate:
                return pattern_similarity
            
            # 3단계: 키워드 및 구조 유사도 검사
            structure_similarity = await self._check_structure_similarity(question_content, options)
            
            if structure_similarity.is_duplicate:
                return structure_similarity
            
            # 모든 검사 통과
            return SimilarityResult(
                is_duplicate=False,
                similarity_score=max(db_similarity.similarity_score, 
                                   pattern_similarity.similarity_score,
                                   structure_similarity.similarity_score),
                similar_question_id=None,
                similar_content=None,
                reason="중복 없음 - 새로운 문제 생성 가능"
            )
            
        except Exception as e:
            logger.error(f"중복 검사 실패: {e}")
            return SimilarityResult(
                is_duplicate=False,
                similarity_score=0.0,
                similar_question_id=None,
                similar_content=None,
                reason=f"검사 오류: {str(e)}"
            )
    
    async def _check_db_similarity(
        self, db: Session, question_content: str, department: str
    ) -> SimilarityResult:
        """데이터베이스 기존 문제와의 유사도 검사"""
        
        try:
            # 같은 학과의 기존 문제들 조회
            existing_questions = db.query(Question).filter(
                and_(
                    Question.is_active == True,
                    Question.subject.like(f"%{department}%")
                )
            ).all()
            
            max_similarity = 0.0
            most_similar_question = None
            
            for q in existing_questions:
                if q.content:
                    similarity = self._calculate_text_similarity(question_content, q.content)
                    
                    if similarity > max_similarity:
                        max_similarity = similarity
                        most_similar_question = q
                    
                    # 높은 유사도 발견시 즉시 중복 판정
                    if similarity >= self.similarity_threshold:
                        return SimilarityResult(
                            is_duplicate=True,
                            similarity_score=similarity,
                            similar_question_id=q.id,
                            similar_content=q.content,
                            reason=f"기존 문제와 {similarity:.1%} 유사 (ID: {q.id})"
                        )
            
            return SimilarityResult(
                is_duplicate=False,
                similarity_score=max_similarity,
                similar_question_id=most_similar_question.id if most_similar_question else None,
                similar_content=None,
                reason=f"DB 검사 통과 (최대 유사도: {max_similarity:.1%})"
            )
            
        except Exception as e:
            logger.error(f"DB 유사도 검사 실패: {e}")
            return SimilarityResult(False, 0.0, None, None, f"DB 검사 오류: {str(e)}")
    
    async def _check_pattern_similarity(
        self, question_content: str, department: str
    ) -> SimilarityResult:
        """학습된 패턴과의 유사도 검사"""
        
        try:
            dept_data = self.evaluator_data.get(department, {})
            if not dept_data:
                return SimilarityResult(False, 0.0, None, None, "패턴 데이터 없음")
            
            # 문제 내용에서 핵심 키워드 추출
            question_keywords = self._extract_keywords(question_content)
            
            # 평가위원 데이터의 패턴과 비교
            evaluators = dept_data.get("departments", {}).get(department.replace("학과", ""), {}).get("evaluators", {})
            
            max_pattern_similarity = 0.0
            
            for evaluator_name, evaluator_data in evaluators.items():
                subjects = evaluator_data.get("subject_distribution", {})
                
                for subject, count in subjects.items():
                    subject_similarity = self._calculate_keyword_similarity(question_keywords, [subject])
                    
                    if subject_similarity > max_pattern_similarity:
                        max_pattern_similarity = subject_similarity
                    
                    # 패턴 중복 임계값 (더 낮게 설정)
                    if subject_similarity >= 0.7:
                        return SimilarityResult(
                            is_duplicate=True,
                            similarity_score=subject_similarity,
                            similar_question_id=None,
                            similar_content=f"평가위원 {evaluator_name}의 {subject} 패턴",
                            reason=f"기존 출제 패턴과 {subject_similarity:.1%} 유사"
                        )
            
            return SimilarityResult(
                is_duplicate=False,
                similarity_score=max_pattern_similarity,
                similar_question_id=None,
                similar_content=None,
                reason=f"패턴 검사 통과 (최대 유사도: {max_pattern_similarity:.1%})"
            )
            
        except Exception as e:
            logger.error(f"패턴 유사도 검사 실패: {e}")
            return SimilarityResult(False, 0.0, None, None, f"패턴 검사 오류: {str(e)}")
    
    async def _check_structure_similarity(
        self, question_content: str, options: Optional[Dict[str, str]]
    ) -> SimilarityResult:
        """문제 구조 유사도 검사"""
        
        try:
            # 문제 구조 패턴 분석
            structure_pattern = self._analyze_question_structure(question_content, options)
            
            # 캐시된 구조 패턴과 비교
            for cached_pattern, cached_info in self.pattern_cache.items():
                similarity = self._calculate_structure_similarity(structure_pattern, cached_pattern)
                
                if similarity >= 0.9:  # 구조가 거의 동일
                    return SimilarityResult(
                        is_duplicate=True,
                        similarity_score=similarity,
                        similar_question_id=cached_info.get("question_id"),
                        similar_content=None,
                        reason=f"문제 구조가 {similarity:.1%} 동일"
                    )
            
            # 새로운 패턴을 캐시에 추가
            pattern_hash = hashlib.md5(structure_pattern.encode()).hexdigest()
            self.pattern_cache[pattern_hash] = {
                "pattern": structure_pattern,
                "created_at": datetime.now(),
                "question_content": question_content[:100]
            }
            
            return SimilarityResult(
                is_duplicate=False,
                similarity_score=0.0,
                similar_question_id=None,
                similar_content=None,
                reason="구조 검사 통과 - 새로운 패턴"
            )
            
        except Exception as e:
            logger.error(f"구조 유사도 검사 실패: {e}")
            return SimilarityResult(False, 0.0, None, None, f"구조 검사 오류: {str(e)}")
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """텍스트 유사도 계산"""
        # 정규화
        clean_text1 = re.sub(r'[^\w\s]', '', text1.lower())
        clean_text2 = re.sub(r'[^\w\s]', '', text2.lower())
        
        # SequenceMatcher를 사용한 유사도 계산
        similarity = SequenceMatcher(None, clean_text1, clean_text2).ratio()
        
        return similarity
    
    def _extract_keywords(self, text: str) -> List[str]:
        """텍스트에서 핵심 키워드 추출"""
        # 의료 전문 용어 우선 추출
        medical_terms = [
            '근육', '관절', '신경', '혈관', '호흡', '순환', '소화', '내분비',
            '면역', '감각', '운동', '인지', '재활', '치료', '진단', '평가',
            '해부', '생리', '병리', '약리', '영상', '검사'
        ]
        
        keywords = []
        text_lower = text.lower()
        
        for term in medical_terms:
            if term in text_lower:
                keywords.append(term)
        
        # 한글 명사 추출 (간단한 패턴)
        korean_nouns = re.findall(r'[가-힣]{2,}', text)
        keywords.extend(korean_nouns[:5])  # 상위 5개만
        
        return list(set(keywords))
    
    def _calculate_keyword_similarity(self, keywords1: List[str], keywords2: List[str]) -> float:
        """키워드 유사도 계산"""
        if not keywords1 or not keywords2:
            return 0.0
        
        set1 = set(keywords1)
        set2 = set(keywords2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _analyze_question_structure(self, content: str, options: Optional[Dict[str, str]]) -> str:
        """문제 구조 분석"""
        structure_elements = []
        
        # 문제 길이 패턴
        if len(content) < 50:
            structure_elements.append("SHORT")
        elif len(content) < 150:
            structure_elements.append("MEDIUM")
        else:
            structure_elements.append("LONG")
        
        # 질문 유형 패턴
        if "?" in content:
            structure_elements.append("QUESTION")
        if "다음" in content:
            structure_elements.append("MULTIPLE_CHOICE")
        if "가장" in content:
            structure_elements.append("BEST_ANSWER")
        
        # 선택지 패턴
        if options:
            structure_elements.append(f"OPTIONS_{len(options)}")
        
        return "_".join(structure_elements)
    
    def _calculate_structure_similarity(self, pattern1: str, pattern2: str) -> float:
        """구조 패턴 유사도 계산"""
        elements1 = set(pattern1.split("_"))
        elements2 = set(pattern2.split("_"))
        
        if not elements1 or not elements2:
            return 0.0
        
        intersection = len(elements1 & elements2)
        union = len(elements1 | elements2)
        
        return intersection / union
    
    async def generate_unique_question_guidance(
        self, 
        db: Session,
        subject: str,
        difficulty: str,
        department: str,
        keywords: List[str]
    ) -> Dict[str, Any]:
        """중복 없는 문제 생성 가이드"""
        
        # 사용 빈도가 낮은 키워드 찾기
        unused_keywords = await self._find_unused_concepts(db, department, keywords)
        
        # 새로운 문제 접근법 제안
        alternative_approaches = await self._suggest_alternative_approaches(department, subject)
        
        # 난이도별 다양성 전략
        diversity_strategy = self._create_diversity_strategy(difficulty, department)
        
        return {
            "recommended_keywords": unused_keywords[:5],
            "alternative_approaches": alternative_approaches,
            "diversity_strategy": diversity_strategy,
            "avoid_patterns": await self._get_overused_patterns(db, department),
            "uniqueness_tips": [
                "기존 문제와 다른 관점으로 접근하세요",
                "실제 임상 상황을 반영한 새로운 시나리오를 만드세요", 
                "최신 연구나 기술을 반영하세요",
                "다학제적 접근을 시도하세요"
            ]
        }
    
    async def _find_unused_concepts(
        self, db: Session, department: str, current_keywords: List[str]
    ) -> List[str]:
        """사용되지 않은 개념 찾기"""
        
        # 평가위원 데이터에서 모든 개념 추출
        dept_data = self.evaluator_data.get(department, {})
        all_concepts = set()
        
        evaluators = dept_data.get("departments", {}).get(department.replace("학과", ""), {}).get("evaluators", {})
        for evaluator_data in evaluators.values():
            subjects = evaluator_data.get("subject_distribution", {})
            all_concepts.update(subjects.keys())
        
        # 현재 키워드와 중복되지 않는 개념들
        unused_concepts = list(all_concepts - set(current_keywords))
        
        return unused_concepts[:10]
    
    async def _suggest_alternative_approaches(self, department: str, subject: str) -> List[str]:
        """대안적 접근법 제안"""
        
        approaches = {
            "물리치료학과": [
                "환자 케이스 스터디 기반 문제",
                "운동학적 분석 문제", 
                "임상 의사결정 시나리오",
                "근거기반 치료 선택 문제"
            ],
            "작업치료학과": [
                "일상생활 적응 시나리오",
                "인지재활 프로그램 설계",
                "보조기구 선택 및 적용",
                "환경 수정 및 적응 전략"
            ],
            "간호학과": [
                "간호과정 적용 시나리오",
                "환자 안전 상황 판단",
                "의료진 협력 상황",
                "윤리적 딜레마 해결"
            ]
        }
        
        return approaches.get(department, [])
    
    def _create_diversity_strategy(self, difficulty: str, department: str) -> Dict[str, Any]:
        """다양성 전략 생성"""
        
        strategies = {
            "하": {
                "focus": "기본 개념의 새로운 표현",
                "methods": ["도식화", "비교분석", "실예 적용"]
            },
            "중": {
                "focus": "응용 및 연결 개념",
                "methods": ["통합적 사고", "원인-결과 분석", "상황 적용"]
            },
            "상": {
                "focus": "복합적 문제 해결",
                "methods": ["다단계 분석", "가설 검증", "창의적 해결책"]
            }
        }
        
        return strategies.get(difficulty, strategies["중"])
    
    async def _get_overused_patterns(self, db: Session, department: str) -> List[str]:
        """과다 사용된 패턴 추출"""
        
        try:
            # 최근 생성된 문제들의 패턴 분석
            recent_questions = db.query(Question).filter(
                and_(
                    Question.subject.like(f"%{department}%"),
                    Question.created_at >= datetime.now().replace(month=datetime.now().month-1)
                )
            ).all()
            
            pattern_count = {}
            for q in recent_questions:
                if q.content:
                    pattern = self._analyze_question_structure(q.content, q.options)
                    pattern_count[pattern] = pattern_count.get(pattern, 0) + 1
            
            # 3회 이상 사용된 패턴들
            overused = [pattern for pattern, count in pattern_count.items() if count >= 3]
            
            return overused
            
        except Exception as e:
            logger.error(f"과다 사용 패턴 분석 실패: {e}")
            return []

# 전역 서비스 인스턴스
duplicate_prevention_service = DuplicatePreventionService() 