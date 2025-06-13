"""
Qdrant 벡터 데이터베이스 관리 API
pgvector 대신 Qdrant를 사용한 벡터 관리 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging

from ...db.database import get_db
from ...models.question import Question
from ...services.question_vector_service import question_vector_service
from ...services.qdrant_service import qdrant_service
from ...core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vectors", tags=["벡터 관리"])

@router.post("/questions/{question_id}/add")
async def add_question_vector(
    question_id: int,
    db: Session = Depends(get_db)
):
    """특정 문제를 Qdrant 벡터 DB에 추가"""
    try:
        # 문제 조회
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다")
        
        # 이미 벡터가 있는지 확인
        if question.qdrant_vector_id:
            return {
                "success": True,
                "message": "이미 벡터가 존재합니다",
                "vector_id": question.qdrant_vector_id
            }
        
        # 벡터 추가
        result = await question_vector_service.add_question_to_vector_db(question, db)
        
        if result["success"]:
            return {
                "success": True,
                "message": "문제 벡터 추가 완료",
                "question_id": question_id,
                "vector_id": result["vector_id"]
            }
        else:
            raise HTTPException(status_code=500, detail=f"벡터 추가 실패: {result.get('error')}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 문제 벡터 추가 API 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/questions/{question_id}/update")
async def update_question_vector(
    question_id: int,
    db: Session = Depends(get_db)
):
    """특정 문제의 벡터 업데이트"""
    try:
        # 문제 조회
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다")
        
        # 벡터 업데이트
        result = await question_vector_service.update_question_vector(question, db)
        
        if result["success"]:
            return {
                "success": True,
                "message": "문제 벡터 업데이트 완료",
                "question_id": question_id,
                "vector_id": result["vector_id"]
            }
        else:
            raise HTTPException(status_code=500, detail=f"벡터 업데이트 실패: {result.get('error')}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 문제 벡터 업데이트 API 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/questions/{question_id}/delete")
async def delete_question_vector(
    question_id: int,
    db: Session = Depends(get_db)
):
    """특정 문제의 벡터 삭제"""
    try:
        # 문제 조회
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다")
        
        # 벡터 삭제
        result = question_vector_service.delete_question_vector(question, db)
        
        if result["success"]:
            return {
                "success": True,
                "message": "문제 벡터 삭제 완료",
                "question_id": question_id
            }
        else:
            raise HTTPException(status_code=500, detail=f"벡터 삭제 실패: {result.get('error')}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 문제 벡터 삭제 API 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/questions/search")
async def search_similar_questions(
    query_text: str,
    difficulty: Optional[str] = None,
    subject: Optional[str] = None,
    department: Optional[str] = None,
    limit: int = 5,
    score_threshold: float = 0.7,
    include_details: bool = True,
    db: Session = Depends(get_db)
):
    """유사한 문제 검색 (pgvector 대체)"""
    try:
        # 유사 문제 검색
        result = await question_vector_service.search_similar_questions(
            query_text=query_text,
            difficulty=difficulty,
            subject=subject,
            department=department,
            limit=limit,
            score_threshold=score_threshold,
            db=db if include_details else None
        )
        
        if result["success"]:
            return {
                "success": True,
                "query": query_text,
                "filters": {
                    "difficulty": difficulty,
                    "subject": subject,
                    "department": department
                },
                "results": result["results"],
                "total_found": result["total_found"]
            }
        else:
            raise HTTPException(status_code=500, detail=f"검색 실패: {result.get('error')}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 유사 문제 검색 API 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/questions/bulk-add")
async def bulk_add_question_vectors(
    background_tasks: BackgroundTasks,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """벡터가 없는 문제들을 일괄로 벡터 DB에 추가"""
    try:
        # 벡터가 없는 문제들 조회
        questions = question_vector_service.get_questions_without_vectors(db, limit)
        
        if not questions:
            return {
                "success": True,
                "message": "벡터 추가가 필요한 문제가 없습니다",
                "total_processed": 0
            }
        
        # 백그라운드에서 일괄 처리
        background_tasks.add_task(
            _bulk_add_vectors_background,
            questions,
            db
        )
        
        return {
            "success": True,
            "message": f"{len(questions)}개 문제의 벡터 추가를 백그라운드에서 시작했습니다",
            "total_to_process": len(questions)
        }
        
    except Exception as e:
        logger.error(f"❌ 일괄 벡터 추가 API 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/collection/info")
async def get_collection_info():
    """Qdrant 컬렉션 정보 조회"""
    try:
        result = qdrant_service.get_collection_info()
        
        if result["success"]:
            return {
                "success": True,
                "collection_info": result
            }
        else:
            raise HTTPException(status_code=500, detail=f"컬렉션 정보 조회 실패: {result.get('error')}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 컬렉션 정보 조회 API 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_vector_db_status():
    """벡터 DB 상태 확인"""
    try:
        # Qdrant 연결 상태 확인
        collection_info = qdrant_service.get_collection_info()
        
        return {
            "success": True,
            "qdrant_enabled": settings.QDRANT_ENABLED,
            "qdrant_host": settings.QDRANT_HOST,
            "qdrant_port": settings.QDRANT_PORT,
            "vector_dimension": settings.VECTOR_DIMENSION,
            "collection_connected": collection_info["success"],
            "collection_info": collection_info if collection_info["success"] else None
        }
        
    except Exception as e:
        logger.error(f"❌ 벡터 DB 상태 확인 API 오류: {e}")
        return {
            "success": False,
            "error": str(e),
            "qdrant_enabled": settings.QDRANT_ENABLED
        }

async def _bulk_add_vectors_background(questions: List[Question], db: Session):
    """백그라운드에서 일괄 벡터 추가 처리"""
    try:
        result = await question_vector_service.bulk_add_questions_to_vector_db(questions, db)
        logger.info(f"✅ 백그라운드 일괄 벡터 추가 완료: {result}")
    except Exception as e:
        logger.error(f"❌ 백그라운드 일괄 벡터 추가 실패: {e}")

@router.post("/migrate-from-pgvector")
async def migrate_from_pgvector(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """pgvector에서 Qdrant로 마이그레이션"""
    try:
        # 모든 활성 문제 조회
        questions = db.query(Question).filter(
            Question.is_active == True
        ).all()
        
        if not questions:
            return {
                "success": True,
                "message": "마이그레이션할 문제가 없습니다",
                "total_questions": 0
            }
        
        # 백그라운드에서 마이그레이션 처리
        background_tasks.add_task(
            _migrate_pgvector_to_qdrant_background,
            questions,
            db
        )
        
        return {
            "success": True,
            "message": f"{len(questions)}개 문제의 pgvector → Qdrant 마이그레이션을 시작했습니다",
            "total_questions": len(questions)
        }
        
    except Exception as e:
        logger.error(f"❌ pgvector 마이그레이션 API 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _migrate_pgvector_to_qdrant_background(questions: List[Question], db: Session):
    """백그라운드에서 pgvector → Qdrant 마이그레이션 처리"""
    try:
        success_count = 0
        failed_count = 0
        
        for question in questions:
            try:
                # Qdrant에 벡터 추가
                result = await question_vector_service.add_question_to_vector_db(question, db)
                
                if result["success"]:
                    success_count += 1
                    logger.info(f"✅ 문제 {question.id} 마이그레이션 완료")
                else:
                    failed_count += 1
                    logger.error(f"❌ 문제 {question.id} 마이그레이션 실패: {result.get('error')}")
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ 문제 {question.id} 마이그레이션 중 오류: {e}")
        
        logger.info(f"✅ pgvector → Qdrant 마이그레이션 완료: 성공 {success_count}개, 실패 {failed_count}개")
        
    except Exception as e:
        logger.error(f"❌ 백그라운드 마이그레이션 실패: {e}") 