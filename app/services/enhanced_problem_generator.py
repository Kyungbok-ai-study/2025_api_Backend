"""
향상된 문제 생성 서비스
7:3 비율 지식베이스 활용 + AI 챗봇 스타일 상세 해설 + 중복 방지
"""
import json
import logging
import random
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import asyncio

from sqlalchemy.orm import Session
from sqlalchemy import text, and_, func, or_

from ..models.question import Question
from ..models.user import User
from ..core.config import settings

logger = logging.getLogger(__name__)

class MockRAGService:
    """RAG 서비스 Mock (API 키가 없을 때 사용)"""
    
    def similarity_search(self, db: Session, query_text: str, limit: int = 5, similarity_threshold: float = 0.7, department_filter: str = None) -> List[Dict[str, Any]]:
        """Mock 유사도 검색 (학과별 필터링 포함)"""
        try:
            # 기본 필터: 승인된 문제들만
            query = db.query(Question).filter(
                and_(
                    Question.approval_status == "approved",
                    Question.is_active == True
                )
            )
            
            # 학과별 필터링 추가
            if department_filter:
                # 학과명이 subject나 file_title에 포함된 경우만 선택
                department_keywords = {
                    "간호학과": ["간호", "nursing", "환자", "병원", "의료"],
                    "물리치료학과": ["물리치료", "재활", "운동", "근골격", "신경"],
                    "작업치료학과": ["작업치료", "ADL", "인지", "일상생활", "재활"]
                }
                
                if department_filter in department_keywords:
                    keywords = department_keywords[department_filter]
                    filter_conditions = []
                    for keyword in keywords:
                        filter_conditions.append(Question.subject.like(f"%{keyword}%"))
                        filter_conditions.append(Question.content.like(f"%{keyword}%"))
                        filter_conditions.append(Question.file_title.like(f"%{keyword}%"))
                    
                    query = query.filter(or_(*filter_conditions))
            
            questions = query.limit(limit * 2).all()
            
            mock_results = []
            for q in questions[:limit]:
                mock_results.append({
                    "id": q.id,
                    "content": q.content,
                    "subject": q.subject,
                    "file_title": f"Mock 지식베이스 - {q.subject}",
                    "similarity": 0.8 + random.random() * 0.15,
                    "department": department_filter or "일반"
                })
            
            return mock_results
        except Exception as e:
            logger.warning(f"Mock 유사도 검색 실패: {e}")
            return []

class EnhancedProblemGenerator:
    """향상된 문제 생성기 (중복 방지 기능 포함)"""
    
    def __init__(self):
        try:
            from ..services.rag_system import RAGService
            self.rag_service = RAGService()
        except Exception as e:
            logger.warning(f"RAGService 초기화 실패, Mock 사용: {e}")
            self.rag_service = MockRAGService()
        
        # 문제 생성 추적기 초기화
        try:
            from ..services.problem_generation_tracker import generation_tracker
            self.tracker = generation_tracker
        except Exception as e:
            logger.warning(f"Generation Tracker 초기화 실패: {e}")
            self.tracker = None
        
        # 문제 생성 비율 설정
        self.knowledge_base_ratio = 0.7  # 70% 지식베이스
        self.ai_knowledge_ratio = 0.3    # 30% AI 지식
        
        # 학과별 전문 용어 및 개념
        self.department_concepts = {
            "간호학과": {
                "core_concepts": [
                    "환자안전", "감염관리", "투약관리", "활력징후", "간호진단",
                    "간호중재", "환자교육", "가족간호", "응급간호", "수술간호",
                    "정신간호", "지역사회간호", "모성간호", "아동간호", "노인간호"
                ],
                "procedures": [
                    "정맥주사", "도뇨관 삽입", "상처드레싱", "흡인", "산소요법",
                    "위관영양", "관장", "활력징후 측정", "CPR", "응급처치"
                ],
                "assessment_areas": [
                    "신체사정", "통증사정", "영양상태", "낙상위험", "욕창위험",
                    "정신상태", "인지기능", "일상생활능력", "의식수준", "호흡상태"
                ]
            },
            "물리치료학과": {
                "core_concepts": [
                    "근골격계", "신경계", "심폐기능", "운동치료", "도수치료",
                    "전기치료", "운동학습", "기능평가", "재활의학", "운동처방"
                ],
                "procedures": [
                    "관절가동범위 운동", "근력강화 운동", "보행훈련", "균형훈련",
                    "호흡재활", "전기자극치료", "초음파치료", "냉온열치료"
                ],
                "assessment_areas": [
                    "근력평가", "관절가동범위", "균형능력", "보행분석",
                    "기능적 움직임", "통증평가", "신경학적 검사", "심폐기능"
                ]
            },
            "작업치료학과": {
                "core_concepts": [
                    "일상생활활동", "인지재활", "감각통합", "직업재활", "보조기구",
                    "환경수정", "의미있는 활동", "기능적 수행", "삶의 질", "참여"
                ],
                "procedures": [
                    "ADL 훈련", "인지훈련", "작업분석", "보조기 제작",
                    "환경평가", "작업수행 평가", "감각재활", "손기능 훈련"
                ],
                "assessment_areas": [
                    "작업수행", "인지기능", "감각기능", "시지각", "손기능",
                    "일상생활능력", "사회참여", "직업능력", "여가활동"
                ]
            }
        }
    
    async def generate_problems_with_ratio(
        self,
        db: Session,
        user: User,
        subject: str,
        difficulty: str,
        question_type: str,
        count: int,
        keywords: Optional[str] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """7:3 비율로 문제 생성 (중복 방지 적용)"""
        
        logger.info(f"🚀 중복 방지 기능이 적용된 문제 생성 시작 - 사용자: {user.id}")
        
        # 1. 생성 전략 분석 (중복 방지)
        generation_strategy = None
        if self.tracker:
            try:
                generation_strategy = await self.tracker.get_next_generation_strategy(
                    db=db,
                    user_id=user.id,
                    subject=subject,
                    difficulty=difficulty,
                    question_type=question_type,
                    requested_keywords=keywords,
                    count=count
                )
                logger.info(f"📊 생성 전략 적용: {generation_strategy['diversification_level']}% 다양성")
            except Exception as e:
                logger.warning(f"생성 전략 분석 실패, 기본 전략 사용: {e}")
        
        # 2. 전략에 따른 키워드 및 비율 조정
        if generation_strategy:
            effective_keywords = self._apply_generation_strategy(
                keywords, generation_strategy
            )
            # 다양성이 높을 때 지식베이스 비중 증가
            # strategy는 딕셔너리이므로 직접 접근
            kb_ratio = 0.7  # 기본값
            if "knowledge_base_focus" in generation_strategy:
                kb_focus = generation_strategy["knowledge_base_focus"]
                if isinstance(kb_focus, dict) and "kb_ratio_adjustment" in kb_focus:
                    kb_ratio = kb_focus["kb_ratio_adjustment"]
                elif "kb_ratio_adjustment" in generation_strategy:
                    kb_ratio = generation_strategy["kb_ratio_adjustment"]
            ai_ratio = 1.0 - kb_ratio
        else:
            effective_keywords = keywords
            kb_ratio = self.knowledge_base_ratio
            ai_ratio = self.ai_knowledge_ratio
        
        # 3. 비율 계산
        knowledge_base_count = max(1, int(count * kb_ratio))
        ai_knowledge_count = count - knowledge_base_count
        
        logger.info(f"📈 조정된 생성 비율 - 지식베이스: {knowledge_base_count}개({kb_ratio:.1%}), AI지식: {ai_knowledge_count}개({ai_ratio:.1%})")
        
        generated_problems = []
        
        # 4. 지식베이스 기반 문제 생성 (전략 적용)
        kb_problems = await self._generate_from_knowledge_base_with_strategy(
            db, user, subject, difficulty, question_type, 
            knowledge_base_count, effective_keywords, context, generation_strategy
        )
        generated_problems.extend(kb_problems)
        
        # 5. AI 지식 기반 문제 생성 (전략 적용)
        ai_problems = await self._generate_from_ai_knowledge_with_strategy(
            user, subject, difficulty, question_type,
            ai_knowledge_count, effective_keywords, context, generation_strategy
        )
        generated_problems.extend(ai_problems)
        
        # 6. 문제 섞기 (전략적 셔플)
        self._strategic_shuffle(generated_problems, generation_strategy)
        
        # 7. 각 문제에 대해 AI 챗봇 스타일 해설 생성
        for problem in generated_problems:
            problem["detailed_explanation"] = await self._generate_chatbot_explanation(
                problem, user.department
            )
        
        # 8. 생성 세션 기록
        if self.tracker and generation_strategy:
            try:
                await self.tracker.record_generation_session(
                    user_id=user.id,
                    session_id=generation_strategy["session_id"],
                    generated_problems=generated_problems,
                    strategy_used=generation_strategy
                )
            except Exception as e:
                logger.warning(f"생성 세션 기록 실패: {e}")
        
        return {
            "success": True,
            "total_count": len(generated_problems),
            "knowledge_base_count": knowledge_base_count,
            "ai_knowledge_count": ai_knowledge_count,
            "problems": generated_problems,
            "generation_metadata": {
                "method": "7:3_ratio_generation_with_diversity",
                "department": user.department,
                "subject": subject,
                "generated_by": user.id,
                "timestamp": datetime.now().isoformat(),
                "kb_ratio": kb_ratio,
                "ai_ratio": ai_ratio,
                "diversification_applied": generation_strategy is not None,
                "diversification_level": generation_strategy["diversification_level"] if generation_strategy else 0,
                "keywords_used": effective_keywords,
                "strategy_session_id": generation_strategy["session_id"] if generation_strategy else None
            }
        }
    
    def _apply_generation_strategy(
        self, original_keywords: Optional[str], strategy: Dict[str, Any]
    ) -> str:
        """생성 전략에 따른 키워드 적용"""
        
        target_keywords = strategy.get("target_keywords", [])
        alternative_keywords = strategy.get("alternative_keywords", [])
        
        # 전략에서 제안한 키워드 우선 사용
        if target_keywords:
            if original_keywords:
                # 원래 키워드 + 전략 키워드 조합
                combined_keywords = [original_keywords] + target_keywords[:2]
            else:
                combined_keywords = target_keywords[:3]
            
            effective_keywords = ", ".join(combined_keywords)
        else:
            effective_keywords = original_keywords or ""
        
        logger.info(f"🎯 전략 적용 키워드: {effective_keywords}")
        return effective_keywords
    
    async def _generate_from_knowledge_base_with_strategy(
        self,
        db: Session,
        user: User,
        subject: str,
        difficulty: str,
        question_type: str,
        count: int,
        keywords: Optional[str],
        context: Optional[str],
        strategy: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """전략이 적용된 지식베이스 기반 문제 생성"""
        
        problems = []
        
        try:
            # 전략에 따른 검색 쿼리 다양화
            search_queries = self._create_diverse_search_queries(
                subject, keywords, user.department, strategy
            )
            
            all_docs = []
            # 다양한 쿼리로 문서 검색 (학과별 필터링 적용)
            for query in search_queries:
                docs = self.rag_service.similarity_search(
                    db=db,
                    query_text=query,
                    limit=count * 2,
                    similarity_threshold=0.6,
                    department_filter=user.department  # 학과별 필터링 추가
                )
                all_docs.extend(docs)
                logger.info(f"🎯 {user.department} 지식베이스에서 '{query}' 검색: {len(docs)}개 문서")
            
            # 중복 제거 및 다양성 확보
            unique_docs = self._ensure_document_diversity(all_docs, strategy)
            
            if not unique_docs:
                logger.warning("지식베이스에서 관련 문서를 찾을 수 없어 AI 지식으로 대체합니다.")
                return await self._generate_from_ai_knowledge_with_strategy(
                    user, subject, difficulty, question_type, count, keywords, context, strategy
                )
            
            # 문서 기반으로 다양한 문제 생성
            dept_concepts = self.department_concepts.get(user.department, self.department_concepts["간호학과"])
            
            for i in range(count):
                doc = unique_docs[i % len(unique_docs)]
                
                # 전략에 따른 개념 추출
                extracted_concepts = self._extract_concepts_with_strategy(
                    doc["content"], dept_concepts, strategy
                )
                
                problem = await self._create_problem_from_document_with_strategy(
                    doc, extracted_concepts, question_type, difficulty, user.department, i, strategy
                )
                
                problem["source"] = "knowledge_base"
                problem["source_document"] = doc["file_title"]
                problem["similarity_score"] = doc["similarity"]
                problem["diversification_applied"] = True
                
                problems.append(problem)
            
            logger.info(f"📚 전략 적용 지식베이스 문제 생성: {len(problems)}개")
            
        except Exception as e:
            logger.error(f"전략 적용 지식베이스 문제 생성 실패: {e}")
            # 실패 시 기본 방식으로 대체
            return await self._generate_from_knowledge_base(
                db, user, subject, difficulty, question_type, count, keywords, context
            )
        
        return problems
    
    async def _generate_from_ai_knowledge_with_strategy(
        self,
        user: User,
        subject: str,
        difficulty: str,
        question_type: str,
        count: int,
        keywords: Optional[str],
        context: Optional[str],
        strategy: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """전략이 적용된 AI 지식 기반 문제 생성"""
        
        problems = []
        dept_concepts = self.department_concepts.get(user.department, self.department_concepts["간호학과"])
        
        # 전략에 따른 개념 선택
        concepts_to_use = self._select_concepts_with_strategy(dept_concepts, strategy)
        
        for i in range(count):
            # 전략에 따른 개념 선택
            if strategy and strategy.get("target_keywords"):
                # 전략 키워드 우선 사용
                main_concept = strategy["target_keywords"][i % len(strategy["target_keywords"])]
            elif keywords:
                main_concept = keywords
            else:
                # 다양성 확보를 위한 개념 선택
                concept_category = random.choice(list(concepts_to_use.keys()))
                main_concept = random.choice(concepts_to_use[concept_category])
            
            problem = await self._create_ai_generated_problem_with_strategy(
                main_concept, subject, question_type, difficulty, user.department, i, strategy
            )
            
            problem["source"] = "ai_knowledge"
            problem["base_concept"] = main_concept
            problem["concept_category"] = "strategic_selection"
            problem["diversification_applied"] = True
            
            problems.append(problem)
        
        logger.info(f"🤖 전략 적용 AI 지식 문제 생성: {len(problems)}개")
        return problems
    
    def _create_diverse_search_queries(
        self, subject: str, keywords: Optional[str], department: str, 
        strategy: Optional[Dict[str, Any]]
    ) -> List[str]:
        """다양한 검색 쿼리 생성"""
        
        queries = [subject]
        
        if keywords:
            queries.append(keywords)
        
        # 전략에서 제안한 키워드 추가
        if strategy:
            target_keywords = strategy.get("target_keywords", [])
            alternative_keywords = strategy.get("alternative_keywords", [])
            
            queries.extend(target_keywords[:2])
            queries.extend(alternative_keywords[:1])
        
        # 학과별 전문 용어 추가 (다양성 확보)
        dept_concepts = self.department_concepts.get(department, {})
        if dept_concepts:
            for category, concepts in dept_concepts.items():
                queries.append(random.choice(concepts))
        
        # 중복 제거
        unique_queries = list(set(queries))
        
        logger.info(f"🔍 다양성 검색 쿼리 {len(unique_queries)}개 생성")
        return unique_queries[:5]  # 최대 5개 쿼리
    
    def _ensure_document_diversity(
        self, all_docs: List[Dict[str, Any]], strategy: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """문서 다양성 확보"""
        
        if not all_docs:
            return []
        
        # 중복 제거 (파일명 기준)
        seen_files = set()
        unique_docs = []
        
        for doc in all_docs:
            file_title = doc.get("file_title", "")
            if file_title not in seen_files:
                seen_files.add(file_title)
                unique_docs.append(doc)
        
        # 전략에 따른 문서 정렬
        if strategy and strategy.get("diversification_level", 0) > 70:
            # 높은 다양성: 유사도가 낮은 것부터 (더 다양한 문서)
            unique_docs.sort(key=lambda x: x.get("similarity", 0))
        else:
            # 일반적인 경우: 유사도가 높은 것부터
            unique_docs.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        
        logger.info(f"📊 문서 다양성 확보: {len(unique_docs)}개 고유 문서")
        return unique_docs
    
    def _extract_concepts_with_strategy(
        self, text: str, dept_concepts: Dict[str, List[str]], 
        strategy: Optional[Dict[str, Any]]
    ) -> List[str]:
        """전략에 따른 개념 추출"""
        
        # 기본 개념 추출
        found_concepts = self._extract_concepts_from_text(text, dept_concepts)
        
        # 전략 적용
        if strategy:
            avoid_patterns = strategy.get("avoid_patterns", [])
            target_keywords = strategy.get("target_keywords", [])
            
            # 피해야 할 패턴 제거
            filtered_concepts = []
            for concept in found_concepts:
                should_avoid = any(
                    pattern.startswith("overused_keyword:") and concept in pattern
                    for pattern in avoid_patterns
                )
                if not should_avoid:
                    filtered_concepts.append(concept)
            
            # 전략 키워드 우선 추가
            if target_keywords:
                for keyword in target_keywords:
                    if keyword not in filtered_concepts:
                        filtered_concepts.insert(0, keyword)
            
            found_concepts = filtered_concepts
        
        return found_concepts[:5]  # 최대 5개
    
    def _select_concepts_with_strategy(
        self, dept_concepts: Dict[str, List[str]], strategy: Optional[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """전략에 따른 개념 선택"""
        
        if not strategy:
            return dept_concepts
        
        avoid_patterns = strategy.get("avoid_patterns", [])
        diversification_level = strategy.get("diversification_level", 50)
        
        # 피해야 할 키워드 추출
        avoid_keywords = set()
        for pattern in avoid_patterns:
            if pattern.startswith("overused_keyword:"):
                avoid_keywords.add(pattern.split(":", 1)[1])
        
        # 전략에 따른 개념 필터링
        filtered_concepts = {}
        for category, concepts in dept_concepts.items():
            filtered_concepts[category] = [
                concept for concept in concepts 
                if concept not in avoid_keywords
            ]
        
        # 다양성이 높을 때 모든 카테고리 사용, 낮을 때 일부만 사용
        if diversification_level > 70:
            return filtered_concepts
        elif diversification_level > 40:
            # 절반의 카테고리만 사용
            categories = list(filtered_concepts.keys())
            selected_categories = random.sample(categories, max(1, len(categories) // 2))
            return {cat: filtered_concepts[cat] for cat in selected_categories}
        else:
            # 하나의 카테고리만 집중 사용
            category = random.choice(list(filtered_concepts.keys()))
            return {category: filtered_concepts[category]}
    
    async def _create_problem_from_document_with_strategy(
        self,
        doc: Dict[str, Any],
        concepts: List[str],
        question_type: str,
        difficulty: str,
        department: str,
        index: int,
        strategy: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """전략이 적용된 문서 기반 문제 생성"""
        
        # 전략에 따른 접근 방식 다양화
        if strategy and strategy.get("generation_guidance", {}).get("vary_question_approaches"):
            # 다양한 접근 방식 적용
            approaches = ["analytical", "practical", "comparative", "evaluative"]
            approach = random.choice(approaches)
        else:
            approach = "standard"
        
        main_concept = concepts[0] if concepts else "핵심 개념"
        doc_content = doc["content"][:200]
        
        problem_id = f"kb_strategy_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{index}"
        
        # 접근 방식에 따른 문제 생성
        if question_type == "multiple_choice":
            question_text, choices, correct_answer = self._create_multiple_choice_with_approach(
                doc_content, main_concept, department, approach
            )
        elif question_type == "short_answer":
            question_text = self._create_short_answer_with_approach(
                doc_content, main_concept, approach
            )
            choices = None
            correct_answer = f"{main_concept}에 대한 {approach} 접근 답안"
        elif question_type == "essay":
            question_text = self._create_essay_with_approach(
                doc_content, main_concept, approach
            )
            choices = None
            correct_answer = f"{main_concept}에 대한 포괄적 {approach} 논술 답안"
        else:  # true_false
            question_text = f"{main_concept}에 대한 다음 설명이 올바른지 판단하시오: '{doc_content[:50]}...'"
            choices = {"O": "참", "X": "거짓"}
            correct_answer = "O"
        
        return {
            "id": problem_id,
            "question": question_text,
            "type": question_type,
            "choices": choices,
            "correct_answer": correct_answer,
            "difficulty": difficulty,
            "main_concept": main_concept,
            "related_concepts": concepts[:5],
            "approach": approach,
            "confidence_score": min(0.9, doc["similarity"] + 0.1),
            "generated_at": datetime.now().isoformat()
        }
    
    async def _create_ai_generated_problem_with_strategy(
        self,
        concept: str,
        subject: str,
        question_type: str,
        difficulty: str,
        department: str,
        index: int,
        strategy: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """전략이 적용된 AI 생성 문제"""
        
        problem_id = f"ai_strategy_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{index}"
        
        # 전략에 따른 문제 스타일 다양화
        style_variations = self._get_style_variations(department, strategy)
        
        dept_styles = style_variations.get(department, style_variations["간호학과"])
        
        if question_type == "multiple_choice":
            question_text = dept_styles.get("multiple_choice", f"{concept}에 대한 설명으로 올바른 것은?")
            choices, correct_answer = self._generate_multiple_choices_with_strategy(concept, department, strategy)
        elif question_type == "short_answer":
            question_text = dept_styles.get("short_answer", f"{concept}에 대해 설명하시오.")
            choices = None
            correct_answer = f"{concept}에 대한 {department} 관점의 전략적 답안"
        elif question_type == "essay":
            question_text = dept_styles.get("essay", f"{concept}에 대해 논술하시오.")
            choices = None
            correct_answer = f"{concept}에 대한 포괄적이고 전략적인 논술 답안"
        else:  # true_false
            question_text = f"{concept}는 {subject} 영역에서 핵심적인 개념이다."
            choices = {"O": "참", "X": "거짓"}
            correct_answer = "O"
        
        return {
            "id": problem_id,
            "question": question_text,
            "type": question_type,
            "choices": choices,
            "correct_answer": correct_answer,
            "difficulty": difficulty,
            "main_concept": concept,
            "strategy_applied": True,
            "confidence_score": 0.8 + random.random() * 0.1,
            "generated_at": datetime.now().isoformat()
        }
    
    def _create_multiple_choice_with_approach(
        self, doc_content: str, concept: str, department: str, approach: str
    ) -> Tuple[str, Dict[str, str], str]:
        """접근 방식에 따른 객관식 문제 생성"""
        
        approach_templates = {
            "analytical": f"다음 자료를 분석할 때 {concept}의 핵심 요소는?",
            "practical": f"다음 상황에서 {concept}을 실제 적용할 때 가장 중요한 것은?",
            "comparative": f"다음 자료를 바탕으로 {concept}과 관련된 접근법을 비교할 때 옳은 것은?",
            "evaluative": f"다음 내용을 평가할 때 {concept}의 타당성을 판단하는 기준은?",
            "standard": f"다음 자료를 바탕으로 {concept}에 대한 설명으로 가장 적절한 것은?"
        }
        
        question_text = approach_templates.get(approach, approach_templates["standard"])
        question_text += f"\n\n[자료] {doc_content[:100]}..."
        
        choices, correct_answer = self._generate_multiple_choices(concept, department)
        
        return question_text, choices, correct_answer
    
    def _create_short_answer_with_approach(
        self, doc_content: str, concept: str, approach: str
    ) -> str:
        """접근 방식에 따른 단답형 문제 생성"""
        
        approach_templates = {
            "analytical": f"{concept}에 대해 다음 자료를 분석적으로 검토하여 핵심 요소들을 설명하시오.",
            "practical": f"{concept}의 실무 적용 방안을 다음 자료를 참고하여 구체적으로 제시하시오.",
            "comparative": f"{concept}과 관련된 다양한 접근법을 비교하여 설명하시오.",
            "evaluative": f"{concept}의 효과성을 평가하는 기준을 제시하고 설명하시오.",
            "standard": f"{concept}에 대해 다음 내용을 참고하여 설명하시오."
        }
        
        question_text = approach_templates.get(approach, approach_templates["standard"])
        question_text += f"\n참고: {doc_content[:100]}..."
        
        return question_text
    
    def _create_essay_with_approach(
        self, doc_content: str, concept: str, approach: str
    ) -> str:
        """접근 방식에 따른 논술형 문제 생성"""
        
        approach_templates = {
            "analytical": f"{concept}에 대한 다음 자료를 분석하고 이론적 배경을 종합하여 논술하시오.",
            "practical": f"{concept}의 실무 적용을 위한 전략을 수립하고 구체적인 실행 방안을 논술하시오.",
            "comparative": f"{concept}과 관련된 다양한 관점을 비교·분석하여 종합적으로 논술하시오.",
            "evaluative": f"{concept}의 현재 상황을 평가하고 개선 방향을 제시하여 논술하시오.",
            "standard": f"{concept}에 대한 다음 자료를 분석하고 종합적으로 논술하시오."
        }
        
        question_text = approach_templates.get(approach, approach_templates["standard"])
        question_text += f"\n자료: {doc_content[:150]}..."
        
        return question_text
    
    def _get_style_variations(
        self, department: str, strategy: Optional[Dict[str, Any]]
    ) -> Dict[str, Dict[str, str]]:
        """전략에 따른 스타일 변형"""
        
        if not strategy or strategy.get("diversification_level", 0) < 50:
            # 기본 스타일 사용
            return {
                "간호학과": {
                    "multiple_choice": "다음 중 {concept}과 관련된 간호중재로 가장 적절한 것은?",
                    "short_answer": "{concept} 시 간호사가 수행해야 할 핵심 역할을 기술하시오.",
                    "essay": "{concept}에 대한 간호과정을 단계별로 설명하시오."
                },
                "물리치료학과": {
                    "multiple_choice": "다음 중 {concept}에 대한 물리치료적 접근으로 옳은 것은?",
                    "short_answer": "{concept} 환자의 기능평가 방법을 설명하시오.",
                    "essay": "{concept} 환자를 위한 재활치료 계획을 수립하시오."
                },
                "작업치료학과": {
                    "multiple_choice": "다음 중 {concept}과 관련된 작업치료 중재로 효과적인 것은?",
                    "short_answer": "{concept} 향상을 위한 활동을 제시하시오.",
                    "essay": "{concept}과 일상생활 참여의 관계를 논술하시오."
                }
            }
        else:
            # 다양한 스타일 변형
            return {
                "간호학과": {
                    "multiple_choice": "임상 현장에서 {concept} 상황을 마주했을 때 우선적으로 고려해야 할 요소는?",
                    "short_answer": "{concept}에 대한 근거기반 접근법을 구체적 사례와 함께 설명하시오.",
                    "essay": "{concept}이 환자 안전과 치료 효과에 미치는 영향을 다각도로 분석하시오."
                },
                "물리치료학과": {
                    "multiple_choice": "{concept} 치료 계획 수립 시 개별 환자 특성에 따른 최적의 접근은?",
                    "short_answer": "{concept}의 기능적 평가와 치료 효과 측정 방법을 제시하시오.",
                    "essay": "{concept} 재활 과정에서의 다학제 협력과 환자 중심 접근을 논술하시오."
                },
                "작업치료학과": {
                    "multiple_choice": "{concept} 개입에서 의미있는 활동 선택의 핵심 원칙은?",
                    "short_answer": "{concept}과 관련된 환경적 요인과 개인적 요인의 상호작용을 설명하시오.",
                    "essay": "{concept}을 통한 일상생활 참여 증진과 삶의 질 향상 전략을 논술하시오."
                }
            }
    
    def _generate_multiple_choices_with_strategy(
        self, concept: str, department: str, strategy: Optional[Dict[str, Any]]
    ) -> Tuple[Dict[str, str], str]:
        """전략에 따른 객관식 선택지 생성 (정답 위치 랜덤화)"""
        
        # 전략 적용으로 선택지 다양화
        if strategy and strategy.get("diversification_level", 0) > 60:
            # 더 정교하고 다양한 선택지 생성
            advanced_patterns = self._get_advanced_choice_patterns(department)
            dept_pattern = advanced_patterns.get(department, advanced_patterns["간호학과"])
            
            correct_option = random.choice(dept_pattern["advanced_correct"]).format(concept=concept)
            incorrect_options = [opt.format(concept=concept) for opt in random.sample(dept_pattern["advanced_incorrect"], 3)]
            
            # 모든 선택지를 리스트로 만들기
            all_options = [correct_option] + incorrect_options
            
            # 선택지 섞기
            random.shuffle(all_options)
            
            # 정답이 위치한 인덱스 찾기
            correct_index = all_options.index(correct_option)
            
            # 선택지 번호 매핑
            choice_labels = ["1", "2", "3", "4"]
            choices = {}
            for i, option in enumerate(all_options):
                choices[choice_labels[i]] = option
            
            # 정답 번호 결정
            correct_answer = choice_labels[correct_index]
            
            logger.info(f"🎯 고급 전략 정답 다양화: '{concept}' 문제의 정답이 {correct_answer}번에 배치됨")
            
            return choices, correct_answer
        else:
            # 기본 선택지 생성 (이미 정답 위치가 랜덤화됨)
            return self._generate_multiple_choices(concept, department)
    
    def _get_advanced_choice_patterns(self, department: str) -> Dict[str, Dict[str, List[str]]]:
        """고급 선택지 패턴"""
        
        return {
            "간호학과": {
                "advanced_correct": [
                    "{concept}는 환자의 개별적 특성과 문화적 배경을 고려한 전인적 접근이 핵심이다",
                    "{concept} 적용 시 최신 근거와 임상 가이드라인을 바탕으로 한 비판적 사고가 필요하다",
                    "{concept}는 다학제팀 협력과 지속적인 질 개선을 통해 최적화될 수 있다"
                ],
                "advanced_incorrect": [
                    "{concept}는 표준화된 프로토콜만 엄격히 따르면 충분하다",
                    "{concept} 적용에서 환자의 주관적 경험은 객관적 데이터보다 덜 중요하다",
                    "{concept}는 의료진 중심의 효율성을 우선적으로 고려해야 한다"
                ]
            },
            "물리치료학과": {
                "advanced_correct": [
                    "{concept}는 환자의 기능적 목표와 생활 패턴을 고려한 맞춤형 접근이 필수적이다",
                    "{concept} 치료는 정량적 평가와 정성적 관찰을 종합한 통합적 판단에 기반해야 한다",
                    "{concept}는 환자의 능동적 참여와 자기효능감 증진을 통해 효과가 극대화된다"
                ],
                "advanced_incorrect": [
                    "{concept}는 치료사의 경험과 직관에만 의존하여 적용하는 것이 가장 효과적이다",
                    "{concept} 치료에서 환자의 통증 호소는 치료 진행에 방해가 되므로 무시해야 한다",
                    "{concept}는 단기간 집중 치료로만 충분한 효과를 얻을 수 있다"
                ]
            },
            "작업치료학과": {
                "advanced_correct": [
                    "{concept}는 개인의 가치와 흥미를 반영한 의미있는 활동을 통해 구현되어야 한다",
                    "{concept} 개입은 환경적 맥락과 사회적 지원 체계를 통합적으로 고려해야 한다",
                    "{concept}는 클라이언트의 자율성과 선택권을 존중하는 협력적 관계에서 효과적이다"
                ],
                "advanced_incorrect": [
                    "{concept}는 치료사가 정한 활동을 클라이언트가 수동적으로 따르는 것이 최선이다",
                    "{concept} 개입에서 개인의 선호보다는 객관적 기능 향상만을 목표로 해야 한다",
                    "{concept}는 치료실 환경에서만 훈련하면 일상생활에 자동으로 전이된다"
                ]
            }
        }
    
    def _strategic_shuffle(
        self, problems: List[Dict[str, Any]], strategy: Optional[Dict[str, Any]]
    ) -> None:
        """전략적 문제 섞기"""
        
        if not strategy:
            random.shuffle(problems)
            return
        
        diversification_level = strategy.get("diversification_level", 50)
        
        if diversification_level > 70:
            # 높은 다양성: 출처별로 균등하게 분산
            kb_problems = [p for p in problems if p.get("source") == "knowledge_base"]
            ai_problems = [p for p in problems if p.get("source") == "ai_knowledge"]
            
            # 교대로 배치
            shuffled = []
            for i in range(max(len(kb_problems), len(ai_problems))):
                if i < len(kb_problems):
                    shuffled.append(kb_problems[i])
                if i < len(ai_problems):
                    shuffled.append(ai_problems[i])
            
            problems[:] = shuffled
        else:
            # 일반적인 셔플
            random.shuffle(problems)

    async def _generate_chatbot_explanation(
        self,
        problem: Dict[str, Any],
        department: str
    ) -> str:
        """AI 챗봇 스타일 상세 해설 생성"""
        
        question = problem["question"]
        correct_answer = problem["correct_answer"]
        main_concept = problem.get("main_concept", "핵심 개념")
        difficulty = problem["difficulty"]
        question_type = problem["type"]
        
        # 챗봇 스타일 해설 템플릿
        explanation_parts = []
        
        # 1. 인사 및 문제 분석
        explanation_parts.append(f"안녕하세요! 이 문제에 대해 상세히 설명드리겠습니다. 😊")
        explanation_parts.append(f"\n**📋 문제 분석**")
        explanation_parts.append(f"이 문제는 {department}의 '{main_concept}' 영역에서 출제된 {self._get_difficulty_korean(difficulty)} 문제입니다.")
        
        # 2. 문제 출제 의도
        explanation_parts.append(f"\n**🎯 출제 의도**")
        intent = await self._generate_question_intent(main_concept, department, question_type)
        explanation_parts.append(intent)
        
        # 3. 정답 해설
        explanation_parts.append(f"\n**✅ 정답 해설**")
        if question_type == "multiple_choice":
            explanation_parts.append(f"정답: **{correct_answer}**")
            explanation_parts.append(f"\n{await self._generate_correct_answer_explanation(question, correct_answer, main_concept, department)}")
            
            # 오답 해설
            if problem.get("choices"):
                explanation_parts.append(f"\n**❌ 오답 분석**")
                wrong_analysis = await self._generate_wrong_answer_analysis(problem["choices"], correct_answer, main_concept, department)
                explanation_parts.append(wrong_analysis)
        else:
            explanation_parts.append(await self._generate_subjective_answer_guide(question, main_concept, department))
        
        # 4. 핵심 개념 정리
        explanation_parts.append(f"\n**📚 핵심 개념 정리**")
        key_concepts = await self._generate_key_concepts_summary(main_concept, department)
        explanation_parts.append(key_concepts)
        
        # 5. 실무 적용
        explanation_parts.append(f"\n**🏥 실무 적용**")
        practical_application = await self._generate_practical_application(main_concept, department)
        explanation_parts.append(practical_application)
        
        # 6. 추가 학습 가이드
        explanation_parts.append(f"\n**📖 추가 학습 가이드**")
        study_guide = await self._generate_study_guide(main_concept, department)
        explanation_parts.append(study_guide)
        
        # 7. 마무리
        explanation_parts.append(f"\n**💪 학습 팁**")
        explanation_parts.append(f"이런 유형의 문제를 잘 풀기 위해서는 {main_concept}의 기본 원리를 확실히 이해하고, 실제 사례에 적용해보는 연습이 중요합니다!")
        explanation_parts.append(f"\n궁금한 점이 있으시면 언제든 질문해 주세요! 화이팅! 🎓✨")
        
        return "\n".join(explanation_parts)
    
    def _build_search_query(self, subject: str, keywords: Optional[str], department: str) -> str:
        """검색 쿼리 생성"""
        query_parts = [subject]
        
        if keywords:
            query_parts.append(keywords)
        
        # 학과별 전문 용어 추가
        dept_concepts = self.department_concepts.get(department, {})
        if dept_concepts.get("core_concepts"):
            query_parts.extend(random.sample(dept_concepts["core_concepts"], min(2, len(dept_concepts["core_concepts"]))))
        
        return " ".join(query_parts)
    
    def _extract_concepts_from_text(self, text: str, dept_concepts: Dict[str, List[str]]) -> List[str]:
        """텍스트에서 학과별 개념 추출"""
        found_concepts = []
        
        for category, concepts in dept_concepts.items():
            for concept in concepts:
                if concept in text:
                    found_concepts.append(concept)
        
        # 찾은 개념이 없으면 랜덤 선택
        if not found_concepts:
            all_concepts = []
            for concepts in dept_concepts.values():
                all_concepts.extend(concepts)
            found_concepts = random.sample(all_concepts, min(3, len(all_concepts)))
        
        return found_concepts[:5]  # 최대 5개
    
    def _create_multiple_choice_from_doc(
        self, doc_content: str, concept: str, department: str
    ) -> Tuple[str, Dict[str, str], str]:
        """문서 기반 객관식 문제 생성"""
        
        question_text = f"다음 자료를 바탕으로 {concept}에 대한 설명으로 가장 적절한 것은?\n\n[자료] {doc_content[:100]}..."
        
        choices, correct_answer = self._generate_multiple_choices(concept, department)
        
        return question_text, choices, correct_answer
    
    def _generate_multiple_choices(self, concept: str, department: str) -> Tuple[Dict[str, str], str]:
        """객관식 선택지 생성 (정답 위치 랜덤화)"""
        
        # 학과별 정답/오답 패턴
        dept_patterns = {
            "간호학과": {
                "correct": [
                    f"{concept}는 환자 안전을 최우선으로 고려하여 시행한다",
                    f"{concept} 시 근거기반 실무를 적용하여 체계적으로 접근한다",
                    f"{concept}는 개별 환자의 특성을 고려한 맞춤형 접근이 필요하다",
                    f"{concept}에서는 전인적 간호 관점을 적용한 체계적 접근이 필요하다",
                    f"{concept} 수행 시 환자의 자율성과 존엄성을 존중해야 한다"
                ],
                "incorrect": [
                    f"{concept}는 획일적인 방법으로 모든 환자에게 동일하게 적용한다",
                    f"{concept} 시 환자의 주관적 호소는 중요하지 않다",
                    f"{concept}는 의료진의 편의를 우선적으로 고려한다",
                    f"{concept}에서는 표준화된 프로토콜만 준수하면 충분하다",
                    f"{concept} 시 비용 효율성이 환자 안전보다 우선시되어야 한다",
                    f"{concept}는 의료진의 경험에만 의존하여 수행한다"
                ]
            },
            "물리치료학과": {
                "correct": [
                    f"{concept}는 개별 환자의 기능적 목표에 맞춘 치료 계획이 필요하다",
                    f"{concept} 치료 시 근거중심의 평가를 통해 적절한 중재를 선택한다",
                    f"{concept}는 점진적이고 체계적인 접근을 통해 기능 향상을 도모한다",
                    f"{concept}에서는 환자의 기능적 독립성 향상을 최우선 목표로 한다",
                    f"{concept} 적용 시 생체역학적 원리와 운동학습 이론을 고려한다"
                ],
                "incorrect": [
                    f"{concept}는 모든 환자에게 동일한 치료 프로토콜을 적용한다",
                    f"{concept} 치료는 증상 완화에만 집중하면 충분하다",
                    f"{concept}는 환자의 협조 없이도 치료 효과를 기대할 수 있다",
                    f"{concept}에서는 치료사의 직감에만 의존하여 중재를 선택한다",
                    f"{concept} 시 통증 완화보다는 운동량 증가가 더 중요하다",
                    f"{concept}는 장기적 목표보다는 즉각적 효과만 추구한다"
                ]
            },
            "작업치료학과": {
                "correct": [
                    f"{concept}는 의미있는 활동을 통해 기능을 향상시키는 것이 중요하다",
                    f"{concept} 개입 시 환경적 요인을 고려한 통합적 접근이 필요하다",
                    f"{concept}는 일상생활 참여를 최대화하는 목표 설정이 중요하다",
                    f"{concept}에서는 개인의 가치와 흥미를 반영한 활동 선택이 필수적이다",
                    f"{concept} 적용 시 작업수행의 맥락적 요소를 종합적으로 분석한다"
                ],
                "incorrect": [
                    f"{concept}는 단순 반복 훈련만으로 충분한 효과를 얻을 수 있다",
                    f"{concept} 치료에서 개인의 흥미나 가치는 고려할 필요가 없다",
                    f"{concept}는 기능 향상보다는 증상 완화가 우선이다",
                    f"{concept}에서는 표준화된 활동만 사용하는 것이 효과적이다",
                    f"{concept} 시 환경적 제약은 치료 과정에서 배제해야 한다",
                    f"{concept}는 치료실 내에서만 이루어지면 충분하다"
                ]
            }
        }
        
        dept_pattern = dept_patterns.get(department, dept_patterns["간호학과"])
        
        # 정답과 오답 선택
        correct_option = random.choice(dept_pattern["correct"])
        incorrect_options = random.sample(dept_pattern["incorrect"], 3)
        
        # 모든 선택지를 리스트로 만들기
        all_options = [correct_option] + incorrect_options
        
        # 선택지 섞기
        random.shuffle(all_options)
        
        # 정답이 위치한 인덱스 찾기
        correct_index = all_options.index(correct_option)
        
        # 선택지 번호 매핑
        choice_labels = ["1", "2", "3", "4"]
        choices = {}
        for i, option in enumerate(all_options):
            choices[choice_labels[i]] = option
        
        # 정답 번호 결정
        correct_answer = choice_labels[correct_index]
        
        logger.info(f"🎯 정답 다양화: '{concept}' 문제의 정답이 {correct_answer}번에 배치됨")
        
        return choices, correct_answer
    
    def _get_difficulty_korean(self, difficulty: str) -> str:
        """난이도 한글 변환"""
        mapping = {
            "easy": "쉬운",
            "medium": "보통",
            "hard": "어려운"
        }
        return mapping.get(difficulty, "보통")
    
    async def _generate_question_intent(self, concept: str, department: str, question_type: str) -> str:
        """문제 출제 의도 생성"""
        
        type_intents = {
            "multiple_choice": "객관적 지식의 정확한 이해와 적용 능력을 평가",
            "short_answer": "핵심 개념에 대한 체계적 이해와 설명 능력을 평가",
            "essay": "종합적 사고력과 논리적 서술 능력을 평가",
            "true_false": "기본 개념에 대한 명확한 이해를 평가"
        }
        
        dept_focuses = {
            "간호학과": "임상 상황에서의 전문적 판단력과 근거기반 간호실무 능력",
            "물리치료학과": "기능적 평가와 치료적 중재 선택 능력",
            "작업치료학과": "작업수행과 일상생활 참여 향상을 위한 전문적 접근 능력"
        }
        
        intent = f"이 문제는 '{concept}'에 대한 {type_intents.get(question_type, '이해')}을 목적으로 합니다.\n"
        intent += f"특히 {department}의 핵심 역량인 {dept_focuses.get(department, '전문적 지식')}을 확인하고자 출제되었습니다."
        
        return intent
    
    async def _generate_correct_answer_explanation(self, question: str, correct_answer: str, concept: str, department: str) -> str:
        """정답 해설 생성"""
        
        explanations = {
            "간호학과": f"이 답이 정답인 이유는 '{concept}'의 간호학적 접근에서 환자 중심의 전인적 케어를 강조하기 때문입니다. 근거기반 실무와 환자 안전이 핵심 원칙으로 작용합니다.",
            "물리치료학과": f"이 답이 정답인 이유는 '{concept}'의 물리치료적 접근에서 개별화된 평가와 기능 중심의 치료가 중요하기 때문입니다. 근거중심의 치료와 점진적 접근이 핵심입니다.",
            "작업치료학과": f"이 답이 정답인 이유는 '{concept}'의 작업치료적 접근에서 의미있는 활동과 환경적 맥락을 고려한 통합적 개입이 중요하기 때문입니다."
        }
        
        return explanations.get(department, f"'{concept}'에 대한 전문적 이해를 바탕으로 한 적절한 답변입니다.")
    
    async def _generate_wrong_answer_analysis(self, choices: Dict[str, str], correct_answer: str, concept: str, department: str) -> str:
        """오답 분석 생성"""
        
        analysis = []
        for key, choice in choices.items():
            if key != correct_answer:
                analysis.append(f"**{key}번**: {choice}")
                analysis.append(f"→ 이 선택지가 틀린 이유: {concept}의 기본 원칙에 부합하지 않으며, {department}의 전문적 접근법과 상반됩니다.\n")
        
        return "\n".join(analysis)
    
    async def _generate_subjective_answer_guide(self, question: str, concept: str, department: str) -> str:
        """주관식 답안 가이드 생성"""
        
        guides = {
            "간nursing": f"'{concept}'에 대해 답할 때는 다음 요소들을 포함해야 합니다:\n• 정의와 특성\n• 간호학적 중요성\n• 실무 적용 방안\n• 환자 안전과의 연관성",
            "물리치료학과": f"'{concept}'에 대해 답할 때는 다음 요소들을 포함해야 합니다:\n• 해부학적/생리학적 기초\n• 평가 방법\n• 치료적 접근법\n• 기능적 목표",
            "작업치료학과": f"'{concept}'에 대해 답할 때는 다음 요소들을 포함해야 합니다:\n• 작업수행에 미치는 영향\n• 평가 도구와 방법\n• 중재 전략\n• 일상생활과의 연관성"
        }
        
        return guides.get(department, f"'{concept}'에 대한 전문적이고 체계적인 설명이 필요합니다.")
    
    async def _generate_key_concepts_summary(self, concept: str, department: str) -> str:
        """핵심 개념 정리"""
        
        summaries = {
            "간호학과": f"**{concept}의 간호학적 핵심:**\n• 환자 중심 접근\n• 근거기반 실무\n• 전인적 케어\n• 안전한 간호 제공\n• 지속적 평가와 개선",
            "물리치료학과": f"**{concept}의 물리치료학적 핵심:**\n• 기능 중심 평가\n• 개별화된 치료\n• 점진적 접근\n• 근거중심 치료\n• 기능적 목표 달성",
            "작업치료학과": f"**{concept}의 작업치료학적 핵심:**\n• 의미있는 활동\n• 환경적 고려\n• 참여 중심 접근\n• 개별적 목표\n• 통합적 개입"
        }
        
        return summaries.get(department, f"**{concept}의 핵심 요소들**")
    
    async def _generate_practical_application(self, concept: str, department: str) -> str:
        """실무 적용 가이드"""
        
        applications = {
            "간호학과": f"**임상 현장에서 {concept} 적용 시:**\n• 환자 상태 지속 모니터링\n• 다학제팀과의 협력\n• 가족 교육 및 지지\n• 감염관리 원칙 준수\n• 문서화 및 보고체계 활용",
            "물리치료학과": f"**치료 현장에서 {concept} 적용 시:**\n• 체계적 평가 실시\n• 개별 치료 계획 수립\n• 진행상황 지속적 모니터링\n• 환자 교육 및 홈프로그램 제공\n• 다학제팀과의 의사소통",
            "작업치료학과": f"**작업치료 현장에서 {concept} 적용 시:**\n• 작업 분석 및 환경 평가\n• 의미있는 활동 선정\n• 보조기구 및 환경 수정\n• 가족 및 돌봄자 교육\n• 지역사회 자원 연계"
        }
        
        return applications.get(department, f"**{concept}의 실무 적용 방안**")
    
    async def _generate_study_guide(self, concept: str, department: str) -> str:
        """추가 학습 가이드"""
        
        guides = {
            "간호학과": f"**{concept} 추가 학습 방향:**\n• 관련 간호진단 및 중재 연결\n• 최신 연구 논문 및 가이드라인 검토\n• 시뮬레이션 및 사례 연구\n• 윤리적 고려사항 학습",
            "물리치료학과": f"**{concept} 추가 학습 방향:**\n• 관련 해부학/생리학 복습\n• 최신 치료 기법 및 연구 동향\n• 평가 도구 실습\n• 사례 기반 학습",
            "작업치료학과": f"**{concept} 추가 학습 방향:**\n• 작업과학 이론적 배경\n• 평가 도구 활용법\n• 다양한 중재 기법\n• 지역사회 기반 서비스 이해"
        }
        
        return guides.get(department, f"**{concept}에 대한 심화 학습 권장사항**")


# 전역 서비스 인스턴스
enhanced_generator = EnhancedProblemGenerator()