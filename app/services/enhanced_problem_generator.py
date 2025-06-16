"""
AI 학습 기반 문제 생성 서비스 (중복 방지 포함)
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from .duplicate_prevention_service import duplicate_prevention_service
from .problem_generation_tracker import generation_tracker

logger = logging.getLogger(__name__)

class EnhancedProblemGenerator:
    """AI 학습 기반 강화된 문제 생성 서비스"""
    
    def __init__(self):
        self.learning_data = self._load_learning_data()
        
    def _load_learning_data(self) -> Dict[str, Any]:
        """학습 데이터 로드"""
        try:
            data_path = Path("data")
            learning_data = {}
            
            # 강화 분석 데이터 로드
            for dept, file_name in [
                ("물리치료학과", "enhanced_evaluator_analysis.json"),
                ("작업치료학과", "enhanced_evaluator_analysis_ot.json")
            ]:
                file_path = data_path / file_name
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        learning_data[dept] = json.load(f)
            
            logger.info(f"🤖 AI 학습 데이터 로드: {len(learning_data)}개 학과")
            return learning_data
        except Exception as e:
            logger.error(f"학습 데이터 로드 실패: {e}")
            return {}
    
    async def generate_unique_problems(
        self,
        db: Session,
        user_id: int,
        department: str,
        subject: str,
        difficulty: str,
        question_type: str = "multiple_choice",
        count: int = 5,
        keywords: Optional[str] = None
    ) -> Dict[str, Any]:
        """중복 없는 문제 생성"""
        
        logger.info(f"🚀 AI 기반 문제 생성: {department} {subject}")
        
        try:
            # 1. 생성 전략 수립
            strategy = await generation_tracker.get_next_generation_strategy(
                db, user_id, subject, difficulty, question_type, keywords, count
            )
            
            # 2. AI 학습 패턴 분석
            learned_patterns = self._analyze_learned_patterns(department, difficulty)
            
            # 3. 중복 방지 가이드 생성
            uniqueness_guide = await duplicate_prevention_service.generate_unique_question_guidance(
                db, subject, difficulty, department, strategy.get("target_keywords", [])
            )
            
            # 4. 통합 가이드 생성
            generation_guide = {
                **strategy,
                "ai_patterns": learned_patterns,
                "uniqueness_guide": uniqueness_guide,
                "department": department
            }
            
            # 5. 샘플 시나리오 생성 및 검증
            scenarios = await self._create_and_validate_scenarios(
                db, generation_guide, count, department
            )
            
            # 6. 결과 반환
            return {
                "success": True,
                "department": department,
                "total_scenarios": len(scenarios),
                "unique_scenarios": len([s for s in scenarios if s.get("is_unique", False)]),
                "scenarios": scenarios,
                "ai_learning_applied": True,
                "session_id": generation_guide.get("session_id")
            }
            
        except Exception as e:
            logger.error(f"문제 생성 실패: {e}")
            return {"success": False, "error": str(e)}
    
    def _analyze_learned_patterns(self, department: str, difficulty: str) -> Dict[str, Any]:
        """학습된 패턴 분석"""
        
        dept_data = self.learning_data.get(department, {})
        if not dept_data:
            return {"patterns": [], "insights": []}
        
        patterns = {"difficulty_distribution": {}, "areas": {}}
        
        # 연도별 데이터에서 패턴 추출
        for year, year_data in dept_data.items():
            if year.isdigit():
                for q_data in year_data.values():
                    if isinstance(q_data, dict):
                        q_diff = q_data.get("consensus_difficulty", "중")
                        patterns["difficulty_distribution"][q_diff] = \
                            patterns["difficulty_distribution"].get(q_diff, 0) + 1
                        
                        area = q_data.get("primary_area", "일반")
                        patterns["areas"][area] = patterns["areas"].get(area, 0) + 1
        
        return {
            "patterns": patterns,
            "target_difficulty_ratio": patterns["difficulty_distribution"].get(difficulty, 0),
            "recommended_areas": list(patterns["areas"].keys())[:5]
        }
    
    async def _create_and_validate_scenarios(
        self, db: Session, guide: Dict[str, Any], count: int, department: str
    ) -> List[Dict[str, Any]]:
        """시나리오 생성 및 검증"""
        
        scenarios = []
        ai_areas = guide.get("ai_patterns", {}).get("recommended_areas", [])
        keywords = guide.get("target_keywords", [])
        
        for i in range(count):
            # 키워드 선택
            if i < len(ai_areas):
                primary_concept = ai_areas[i]
            elif i < len(keywords):
                primary_concept = keywords[i]
        else:
                primary_concept = f"통합개념_{i}"
            
            # 시나리오 생성
            scenario = {
                "id": f"scenario_{i+1}",
                "primary_concept": primary_concept,
                "content": f"[{department}] {primary_concept} 관련 문제",
                "ai_enhanced": True
            }
            
            # 중복 검사
            duplicate_check = await duplicate_prevention_service.check_duplicate_against_national_exams(
                db, scenario["content"], department
            )
            
            scenario["is_unique"] = not duplicate_check.is_duplicate
            scenario["similarity_score"] = duplicate_check.similarity_score
            scenario["duplicate_reason"] = duplicate_check.reason
            
            scenarios.append(scenario)
        
        return scenarios

# 전역 인스턴스
enhanced_problem_generator = EnhancedProblemGenerator()