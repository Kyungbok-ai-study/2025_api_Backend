"""
Question 모델과 Qdrant 벡터 DB 통합 서비스
pgvector 대신 Qdrant를 사용한 문제 벡터 관리
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..models.question import Question
from ..models.question_optimized import QuestionOptimized
from .qdrant_service import qdrant_service
from ..db.database import get_db

logger = logging.getLogger(__name__)

class QuestionVectorService:
    """Question 모델과 Qdrant 벡터 DB 통합 서비스"""
    
    def __init__(self):
        self.qdrant = qdrant_service
    
    async def add_question_to_vector_db(
        self, 
        question: Question, 
        db: Session
    ) -> Dict[str, Any]:
        """문제를 Qdrant 벡터 DB에 추가"""
        try:
            # 문제 내용 준비
            content = self._prepare_question_content(question)
            
            # 메타데이터 준비
            metadata = {
                "subject": question.subject or "",
                "area_name": question.area_name or "",
                "difficulty": question.difficulty or "중",
                "year": question.year or 2024,
                "question_type": question.question_type.value if question.question_type else "multiple_choice",
                "approval_status": question.approval_status or "pending",
                "is_active": question.is_active
            }
            
            # Qdrant에 벡터 추가
            result = await self.qdrant.add_question_vector(
                question_id=question.id,
                content=content,
                metadata=metadata
            )
            
            if result["success"]:
                # Question 모델에 Qdrant 벡터 ID 저장
                question.qdrant_vector_id = result["vector_id"]
                question.vector_db_indexed = True
                db.commit()
                
                logger.info(f"✅ 문제 {question.id} 벡터 DB 추가 완료")
                
                return {
                    "success": True,
                    "question_id": question.id,
                    "vector_id": result["vector_id"]
                }
            else:
                logger.error(f"❌ 문제 {question.id} 벡터 DB 추가 실패: {result.get('error')}")
                return result
                
        except Exception as e:
            logger.error(f"❌ 문제 벡터 DB 추가 중 오류: {e}")
            db.rollback()
            return {"success": False, "error": str(e)}
    
    async def update_question_vector(
        self, 
        question: Question, 
        db: Session
    ) -> Dict[str, Any]:
        """문제 벡터 업데이트"""
        try:
            if not question.qdrant_vector_id:
                # 벡터가 없으면 새로 추가
                return await self.add_question_to_vector_db(question, db)
            
            # 문제 내용 준비
            content = self._prepare_question_content(question)
            
            # 메타데이터 준비
            metadata = {
                "subject": question.subject or "",
                "area_name": question.area_name or "",
                "difficulty": question.difficulty or "중",
                "year": question.year or 2024,
                "question_type": question.question_type.value if question.question_type else "multiple_choice",
                "approval_status": question.approval_status or "pending",
                "is_active": question.is_active
            }
            
            # Qdrant에서 벡터 업데이트
            result = await self.qdrant.update_question_vector(
                vector_id=question.qdrant_vector_id,
                question_id=question.id,
                content=content,
                metadata=metadata
            )
            
            if result["success"]:
                db.commit()
                logger.info(f"✅ 문제 {question.id} 벡터 업데이트 완료")
                return result
            else:
                logger.error(f"❌ 문제 {question.id} 벡터 업데이트 실패: {result.get('error')}")
                return result
                
        except Exception as e:
            logger.error(f"❌ 문제 벡터 업데이트 중 오류: {e}")
            db.rollback()
            return {"success": False, "error": str(e)}
    
    def delete_question_vector(
        self, 
        question: Question, 
        db: Session
    ) -> Dict[str, Any]:
        """문제 벡터 삭제"""
        try:
            if not question.qdrant_vector_id:
                return {"success": True, "message": "벡터가 없음"}
            
            # Qdrant에서 벡터 삭제
            result = self.qdrant.delete_question_vector(question.qdrant_vector_id)
            
            if result["success"]:
                # Question 모델에서 벡터 ID 제거
                question.qdrant_vector_id = None
                question.vector_db_indexed = False
                db.commit()
                
                logger.info(f"✅ 문제 {question.id} 벡터 삭제 완료")
                return result
            else:
                logger.error(f"❌ 문제 {question.id} 벡터 삭제 실패: {result.get('error')}")
                return result
                
        except Exception as e:
            logger.error(f"❌ 문제 벡터 삭제 중 오류: {e}")
            db.rollback()
            return {"success": False, "error": str(e)}
    
    async def search_similar_questions(
        self,
        query_text: str,
        difficulty: Optional[str] = None,
        subject: Optional[str] = None,
        department: Optional[str] = None,
        limit: int = 5,
        score_threshold: float = 0.7,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """유사한 문제 검색 (pgvector 대체)"""
        try:
            # Qdrant에서 유사 문제 검색
            search_result = await self.qdrant.search_similar_questions(
                query_text=query_text,
                difficulty=difficulty,
                subject=subject,
                department=department,
                limit=limit,
                score_threshold=score_threshold
            )
            
            if not search_result["success"]:
                return search_result
            
            # DB에서 상세 정보 조회 (필요한 경우)
            if db:
                question_ids = [r["question_id"] for r in search_result["results"]]
                questions = db.query(Question).filter(Question.id.in_(question_ids)).all()
                
                # 결과에 상세 정보 추가
                question_dict = {q.id: q for q in questions}
                for result in search_result["results"]:
                    question_id = result["question_id"]
                    if question_id in question_dict:
                        question = question_dict[question_id]
                        result["question_details"] = {
                            "question_number": question.question_number,
                            "options": question.options,
                            "correct_answer": question.correct_answer,
                            "created_at": question.created_at.isoformat() if question.created_at else None
                        }
            
            return search_result
            
        except Exception as e:
            logger.error(f"❌ 유사 문제 검색 중 오류: {e}")
            return {"success": False, "error": str(e)}
    
    async def bulk_add_questions_to_vector_db(
        self, 
        questions: List[Question], 
        db: Session
    ) -> Dict[str, Any]:
        """여러 문제를 일괄로 벡터 DB에 추가"""
        try:
            success_count = 0
            failed_count = 0
            results = []
            
            for question in questions:
                if question.qdrant_vector_id:
                    # 이미 벡터가 있으면 스킵
                    continue
                
                result = await self.add_question_to_vector_db(question, db)
                results.append({
                    "question_id": question.id,
                    "success": result["success"],
                    "error": result.get("error")
                })
                
                if result["success"]:
                    success_count += 1
                else:
                    failed_count += 1
            
            logger.info(f"✅ 일괄 벡터 추가 완료: 성공 {success_count}개, 실패 {failed_count}개")
            
            return {
                "success": True,
                "total_processed": len(questions),
                "success_count": success_count,
                "failed_count": failed_count,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"❌ 일괄 벡터 추가 중 오류: {e}")
            return {"success": False, "error": str(e)}
    
    def get_questions_without_vectors(self, db: Session, limit: int = 100) -> List[Question]:
        """벡터가 없는 문제들 조회"""
        return db.query(Question).filter(
            or_(
                Question.qdrant_vector_id.is_(None),
                Question.vector_db_indexed == False
            )
        ).filter(
            Question.is_active == True
        ).limit(limit).all()
    
    def _prepare_question_content(self, question: Question) -> str:
        """문제 내용을 벡터화를 위해 준비"""
        content_parts = []
        
        # 문제 내용
        if question.content:
            content_parts.append(question.content)
        
        # 문제 설명/지문
        if question.description:
            if isinstance(question.description, list):
                content_parts.extend(question.description)
            else:
                content_parts.append(str(question.description))
        
        # 선택지 (객관식인 경우)
        if question.options and isinstance(question.options, dict):
            for key, value in question.options.items():
                content_parts.append(f"{key}. {value}")
        
        # 과목 및 영역 정보
        if question.subject:
            content_parts.append(f"과목: {question.subject}")
        
        if question.area_name:
            content_parts.append(f"영역: {question.area_name}")
        
        return " ".join(content_parts)

# 전역 인스턴스
question_vector_service = QuestionVectorService() 