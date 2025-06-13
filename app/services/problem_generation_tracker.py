"""
문제 생성 이력 추적 및 중복 방지 서비스
- 생성된 문제 이력 관리
- 지식베이스 사용 추적
- 동적 키워드 확장
- 중복 방지 알고리즘
"""
import json
import logging
import hashlib
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import text, and_, func, desc

from ..models.question import Question
from ..models.user import User

logger = logging.getLogger(__name__)

@dataclass
class GenerationRecord:
    """문제 생성 기록"""
    user_id: int
    subject: str
    keywords: List[str]
    question_type: str
    difficulty: str
    used_knowledge_chunks: List[str]
    generated_concepts: List[str]
    timestamp: datetime
    session_id: str

@dataclass
class KnowledgeChunk:
    """지식베이스 청크 정보"""
    id: str
    content: str
    subject: str
    keywords: List[str]
    usage_count: int
    last_used: Optional[datetime]

class ProblemGenerationTracker:
    """문제 생성 추적 및 중복 방지 서비스"""
    
    def __init__(self):
        self.generation_history_path = Path("data/generation_history")
        self.generation_history_path.mkdir(parents=True, exist_ok=True)
        
        # 키워드 확장을 위한 관련어 맵핑
        self.concept_relations = {
            "간호학과": {
                "환자안전": ["낙상방지", "감염관리", "투약안전", "환자확인", "의료기기안전"],
                "감염관리": ["무균술", "격리", "손위생", "개인보호구", "환경관리"],
                "투약관리": ["5R원칙", "약물상호작용", "부작용관리", "투약경로", "약물계산"],
                "활력징후": ["체온", "맥박", "호흡", "혈압", "산소포화도"],
                "간호진단": ["NANDA", "간호과정", "사정", "계획", "평가"],
            },
            "물리치료학과": {
                "근골격계": ["관절", "근육", "인대", "힘줄", "뼈"],
                "신경계": ["중추신경", "말초신경", "반사", "감각", "운동"],
                "운동치료": ["관절가동범위", "근력강화", "지구력", "협응성", "균형"],
                "도수치료": ["관절가동술", "연부조직가동술", "신경가동술", "척추교정"],
                "전기치료": ["TENS", "FES", "초음파", "적외선", "레이저"],
            },
            "작업치료학과": {
                "일상생활활동": ["ADL", "IADL", "자조기술", "이동", "의사소통"],
                "인지재활": ["주의력", "기억력", "실행기능", "문제해결", "학습"],
                "감각통합": ["전정감각", "고유감각", "촉각", "시각", "청각"],
                "직업재활": ["직무분석", "작업능력평가", "직업적응", "보조공학"],
                "보조기구": ["휠체어", "보행보조기구", "일상생활보조기구", "의사소통보조기구"],
            }
        }
    
    async def get_next_generation_strategy(
        self,
        db: Session,
        user_id: int,
        subject: str,
        difficulty: str,
        question_type: str,
        requested_keywords: Optional[str] = None,
        count: int = 5
    ) -> Dict[str, Any]:
        """다음 문제 생성 전략 결정 (중복 방지)"""
        
        logger.info(f"🔍 문제 생성 전략 분석 시작 - 사용자 {user_id}")
        
        # 1. 사용자의 이전 생성 이력 분석
        generation_history = await self._get_user_generation_history(db, user_id)
        
        # 2. 사용된 지식베이스 영역 분석
        used_knowledge_areas = await self._analyze_used_knowledge_areas(db, user_id)
        
        # 3. 미사용 키워드 발굴
        unused_keywords = await self._find_unused_keywords(
            user_id, subject, requested_keywords, generation_history
        )
        
        # 4. 지식베이스 커버리지 분석
        knowledge_coverage = await self._analyze_knowledge_coverage(db, user_id, subject)
        
        # 5. 새로운 생성 전략 수립
        strategy = await self._create_generation_strategy(
            generation_history=generation_history,
            used_knowledge_areas=used_knowledge_areas,
            unused_keywords=unused_keywords,
            knowledge_coverage=knowledge_coverage,
            subject=subject,
            difficulty=difficulty,
            question_type=question_type,
            count=count
        )
        
        logger.info(f"✅ 생성 전략 수립 완료: {strategy['diversification_level']}% 다양성")
        
        return strategy
    
    async def _get_user_generation_history(
        self, db: Session, user_id: int, days: int = 30
    ) -> List[GenerationRecord]:
        """사용자의 최근 생성 이력 조회"""
        
        try:
            # 최근 30일간 생성된 문제들 조회
            since_date = datetime.now() - timedelta(days=days)
            
            generated_questions = db.query(Question).filter(
                and_(
                    Question.last_modified_by == user_id,
                    Question.file_category == "ENHANCED_GENERATED",
                    Question.created_at >= since_date
                )
            ).all()
            
            # GenerationRecord로 변환
            history = []
            for q in generated_questions:
                # 메타데이터에서 생성 정보 추출
                source_path = q.source_file_path or ""
                keywords = [q.subject] if q.subject else []
                
                record = GenerationRecord(
                    user_id=user_id,
                    subject=q.subject or "",
                    keywords=keywords,
                    question_type=q.question_type or "multiple_choice",
                    difficulty=q.difficulty or "medium",
                    used_knowledge_chunks=[],  # 추후 확장
                    generated_concepts=keywords,
                    timestamp=q.created_at or datetime.now(),
                    session_id=f"session_{q.id}"
                )
                history.append(record)
            
            logger.info(f"📊 사용자 {user_id}의 최근 {days}일 생성 이력: {len(history)}개")
            return history
            
        except Exception as e:
            logger.error(f"생성 이력 조회 실패: {e}")
            return []
    
    async def _analyze_used_knowledge_areas(
        self, db: Session, user_id: int
    ) -> Dict[str, int]:
        """사용된 지식베이스 영역 분석"""
        
        try:
            # 사용자가 생성한 문제들의 과목/영역 분석
            result = db.execute(text("""
                SELECT subject, area_name, COUNT(*) as usage_count
                FROM questions 
                WHERE last_modified_by = :user_id 
                    AND file_category = 'ENHANCED_GENERATED'
                    AND created_at >= :since_date
                GROUP BY subject, area_name
                ORDER BY usage_count DESC
            """), {
                "user_id": user_id,
                "since_date": datetime.now() - timedelta(days=30)
            }).fetchall()
            
            used_areas = {}
            for row in result:
                area_key = f"{row[0]}_{row[1]}" if row[1] else row[0]
                used_areas[area_key] = row[2]
            
            logger.info(f"📈 사용된 지식 영역: {len(used_areas)}개")
            return used_areas
            
        except Exception as e:
            logger.error(f"지식 영역 분석 실패: {e}")
            return {}
    
    async def _find_unused_keywords(
        self,
        user_id: int,
        subject: str,
        requested_keywords: Optional[str],
        generation_history: List[GenerationRecord]
    ) -> List[str]:
        """미사용 키워드 발굴"""
        
        # 이전에 사용된 키워드들 수집
        used_keywords = set()
        for record in generation_history:
            used_keywords.update(record.keywords)
            used_keywords.update(record.generated_concepts)
        
        # 사용자 부서 정보로 관련 개념 확장
        user_dept = "간호학과"  # 기본값 (실제로는 DB에서 조회)
        available_concepts = self.concept_relations.get(user_dept, {})
        
        # 미사용 키워드 찾기
        unused_keywords = []
        
        if requested_keywords:
            # 요청된 키워드와 관련된 미사용 개념 찾기
            for concept, related in available_concepts.items():
                if requested_keywords.lower() in concept.lower():
                    for related_keyword in related:
                        if related_keyword not in used_keywords:
                            unused_keywords.append(related_keyword)
        
        # 전체 개념에서 미사용 키워드 추가
        for concept, related in available_concepts.items():
            if concept not in used_keywords:
                unused_keywords.append(concept)
            for related_keyword in related:
                if related_keyword not in used_keywords:
                    unused_keywords.append(related_keyword)
        
        # 중복 제거 및 우선순위 적용
        unused_keywords = list(set(unused_keywords))
        
        # 요청된 키워드와 관련성이 높은 순으로 정렬
        if requested_keywords:
            unused_keywords.sort(key=lambda x: self._calculate_keyword_relevance(x, requested_keywords))
        
        logger.info(f"🔍 미사용 키워드 {len(unused_keywords)}개 발굴")
        return unused_keywords[:10]  # 상위 10개만 반환
    
    async def _analyze_knowledge_coverage(
        self, db: Session, user_id: int, subject: str
    ) -> Dict[str, Any]:
        """지식베이스 커버리지 분석"""
        
        try:
            # 전체 지식베이스 문서 수
            total_docs = db.execute(text("""
                SELECT COUNT(DISTINCT file_title) as total_count
                FROM questions 
                WHERE file_category = 'RAG_DOCUMENT' 
                    AND is_active = true
                    AND (subject LIKE :subject OR subject IS NULL)
            """), {"subject": f"%{subject}%"}).fetchone()
            
            # 사용된 지식베이스 문서 수 (간접적으로 추정)
            used_docs = db.execute(text("""
                SELECT COUNT(DISTINCT subject) as used_count
                FROM questions 
                WHERE last_modified_by = :user_id 
                    AND file_category = 'ENHANCED_GENERATED'
                    AND created_at >= :since_date
            """), {
                "user_id": user_id,
                "since_date": datetime.now() - timedelta(days=30)
            }).fetchone()
            
            total_count = total_docs[0] if total_docs else 0
            used_count = used_docs[0] if used_docs else 0
            
            coverage_rate = (used_count / total_count * 100) if total_count > 0 else 0
            
            coverage = {
                "total_documents": total_count,
                "used_documents": used_count,
                "coverage_rate": coverage_rate,
                "unused_rate": 100 - coverage_rate,
                "recommendation": "high_diversity" if coverage_rate < 30 else "moderate_diversity" if coverage_rate < 70 else "focus_depth"
            }
            
            logger.info(f"📊 지식베이스 커버리지: {coverage_rate:.1f}%")
            return coverage
            
        except Exception as e:
            logger.error(f"커버리지 분석 실패: {e}")
            return {
                "total_documents": 0,
                "used_documents": 0,
                "coverage_rate": 0,
                "unused_rate": 100,
                "recommendation": "high_diversity"
            }
    
    async def _create_generation_strategy(
        self,
        generation_history: List[GenerationRecord],
        used_knowledge_areas: Dict[str, int],
        unused_keywords: List[str],
        knowledge_coverage: Dict[str, Any],
        subject: str,
        difficulty: str,
        question_type: str,
        count: int
    ) -> Dict[str, Any]:
        """새로운 생성 전략 수립"""
        
        # 다양성 레벨 결정
        diversification_level = self._calculate_diversification_level(
            generation_history, knowledge_coverage
        )
        
        # 키워드 전략 수립
        keyword_strategy = await self._create_keyword_strategy(
            unused_keywords, used_knowledge_areas, diversification_level
        )
        
        # 지식베이스 활용 전략
        kb_strategy = self._create_knowledge_base_strategy(
            knowledge_coverage, diversification_level
        )
        
        # 문제 유형 다양화 전략
        type_strategy = self._create_type_diversification_strategy(
            generation_history, question_type, count
        )
        
        strategy = {
            "diversification_level": diversification_level,
            "target_keywords": keyword_strategy["primary_keywords"],
            "alternative_keywords": keyword_strategy["alternative_keywords"],
            "knowledge_base_focus": {
                "focus_areas": kb_strategy["focus_areas"],
                "kb_ratio_adjustment": kb_strategy["kb_ratio_adjustment"],
                "exploration_mode": kb_strategy["exploration_mode"]
            },
            "avoid_patterns": self._extract_avoid_patterns(generation_history),
            "type_distribution": type_strategy,
            "generation_guidance": {
                "prioritize_unused_knowledge": diversification_level > 70,
                "expand_keyword_scope": diversification_level > 50,
                "vary_question_approaches": diversification_level > 60,
                "explore_new_concepts": len(unused_keywords) > 5
            },
            "session_id": f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        
        return strategy
    
    def _calculate_diversification_level(
        self, generation_history: List[GenerationRecord], knowledge_coverage: Dict[str, Any]
    ) -> int:
        """다양성 필요 레벨 계산 (0-100)"""
        
        base_level = 50  # 기본 다양성 레벨
        
        # 최근 생성 빈도에 따른 조정
        recent_generations = len([r for r in generation_history if 
                                (datetime.now() - r.timestamp).days <= 7])
        
        if recent_generations > 10:
            base_level += 30  # 많이 생성했으면 더 다양하게
        elif recent_generations > 5:
            base_level += 15
        
        # 지식베이스 커버리지에 따른 조정
        if knowledge_coverage["coverage_rate"] > 70:
            base_level += 20  # 많이 사용했으면 더 다양하게
        elif knowledge_coverage["coverage_rate"] < 30:
            base_level -= 10  # 아직 여유 있음
        
        # 키워드 반복 사용 패턴 분석
        keyword_usage = defaultdict(int)
        for record in generation_history:
            for keyword in record.keywords:
                keyword_usage[keyword] += 1
        
        if keyword_usage and max(keyword_usage.values()) > 3:
            base_level += 25  # 같은 키워드 반복 사용 시 다양성 증가
        
        return min(100, max(0, base_level))
    
    async def _create_keyword_strategy(
        self, unused_keywords: List[str], used_knowledge_areas: Dict[str, int], 
        diversification_level: int
    ) -> Dict[str, Any]:
        """키워드 전략 수립"""
        
        if diversification_level > 70:
            # 높은 다양성: 완전히 새로운 키워드 우선
            primary_keywords = unused_keywords[:3]
            alternative_keywords = unused_keywords[3:6]
        elif diversification_level > 40:
            # 중간 다양성: 사용빈도 낮은 키워드 + 새 키워드 조합
            low_usage_areas = [area for area, count in used_knowledge_areas.items() if count <= 2]
            primary_keywords = unused_keywords[:2] + low_usage_areas[:1]
            alternative_keywords = unused_keywords[2:5]
        else:
            # 낮은 다양성: 기존 키워드 중심으로 약간의 변화
            primary_keywords = unused_keywords[:1]
            alternative_keywords = unused_keywords[1:4]
        
        return {
            "primary_keywords": primary_keywords,
            "alternative_keywords": alternative_keywords,
            "strategy": "high_diversity" if diversification_level > 70 else "moderate_diversity"
        }
    
    def _create_knowledge_base_strategy(
        self, knowledge_coverage: Dict[str, Any], diversification_level: int
    ) -> Dict[str, Any]:
        """지식베이스 활용 전략"""
        
        if knowledge_coverage["recommendation"] == "high_diversity":
            focus_areas = ["unexplored_documents", "low_usage_chunks", "cross_domain_knowledge"]
        elif knowledge_coverage["recommendation"] == "moderate_diversity":
            focus_areas = ["balanced_coverage", "related_concepts", "depth_expansion"]
        else:
            focus_areas = ["depth_focus", "advanced_concepts", "specialized_knowledge"]
        
        return {
            "focus_areas": focus_areas,
            "kb_ratio_adjustment": 0.8 if diversification_level > 70 else 0.7,  # 다양성 높을 때 지식베이스 비중 증가
            "exploration_mode": diversification_level > 60
        }
    
    def _create_type_diversification_strategy(
        self, generation_history: List[GenerationRecord], 
        requested_type: str, count: int
    ) -> Dict[str, int]:
        """문제 유형 다양화 전략"""
        
        # 최근 사용된 문제 유형 분석
        recent_types = defaultdict(int)
        for record in generation_history[-10:]:  # 최근 10개만
            recent_types[record.question_type] += 1
        
        # 요청된 유형 기반으로 분배 조정
        distribution = {requested_type: count}
        
        # 다양성이 필요한 경우 유형 분산
        if len(recent_types) > 0 and recent_types[requested_type] > 3:
            # 같은 유형을 많이 사용했으면 분산
            alternative_types = ["multiple_choice", "short_answer", "essay", "true_false"]
            alternative_types.remove(requested_type)
            
            main_count = max(1, count // 2)
            alt_count = count - main_count
            
            distribution = {
                requested_type: main_count,
                alternative_types[0]: alt_count
            }
        
        return distribution
    
    def _extract_avoid_patterns(self, generation_history: List[GenerationRecord]) -> List[str]:
        """피해야 할 패턴 추출"""
        
        patterns = []
        
        # 자주 반복되는 키워드 패턴
        keyword_frequency = defaultdict(int)
        for record in generation_history:
            for keyword in record.keywords:
                keyword_frequency[keyword] += 1
        
        # 3회 이상 사용된 키워드는 피하기 목록에 추가
        overused_keywords = [keyword for keyword, count in keyword_frequency.items() if count >= 3]
        patterns.extend([f"overused_keyword:{keyword}" for keyword in overused_keywords])
        
        # 연속으로 같은 난이도 사용 패턴
        recent_difficulties = [r.difficulty for r in generation_history[-5:]]
        if len(set(recent_difficulties)) == 1 and len(recent_difficulties) >= 3:
            patterns.append(f"repeated_difficulty:{recent_difficulties[0]}")
        
        # 같은 주제 반복 패턴
        recent_subjects = [r.subject for r in generation_history[-5:]]
        if len(set(recent_subjects)) == 1 and len(recent_subjects) >= 3:
            patterns.append(f"repeated_subject:{recent_subjects[0]}")
        
        return patterns
    
    def _calculate_keyword_relevance(self, keyword: str, target: str) -> float:
        """키워드 관련성 계산 (높을수록 관련성 높음)"""
        
        # 단순한 문자열 유사도 기반 (실제로는 더 정교한 알고리즘 사용 가능)
        target_lower = target.lower()
        keyword_lower = keyword.lower()
        
        if target_lower in keyword_lower or keyword_lower in target_lower:
            return 1.0
        
        # 공통 문자 비율
        common_chars = set(target_lower) & set(keyword_lower)
        relevance = len(common_chars) / max(len(target_lower), len(keyword_lower))
        
        return relevance
    
    async def record_generation_session(
        self,
        user_id: int,
        session_id: str,
        generated_problems: List[Dict[str, Any]],
        strategy_used: Dict[str, Any]
    ) -> None:
        """생성 세션 기록 저장"""
        
        try:
            session_record = {
                "user_id": user_id,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "strategy": strategy_used,
                "problems_generated": len(generated_problems),
                "keywords_used": strategy_used.get("target_keywords", []),
                "diversification_achieved": True  # 실제로는 생성 결과 분석 필요
            }
            
            # 파일에 저장
            session_file = self.generation_history_path / f"{session_id}.json"
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_record, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📝 생성 세션 기록 저장: {session_id}")
            
        except Exception as e:
            logger.error(f"생성 세션 기록 실패: {e}")


# 전역 서비스 인스턴스
generation_tracker = ProblemGenerationTracker() 