"""
RAG 시스템 API 엔드포인트
"""
import os
import shutil
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db.database import get_db
from ..auth.dependencies import get_current_user
from ..models.user import User
from ..services.rag_system import RAGService

router = APIRouter(prefix="/api/rag", tags=["RAG System"])

# Pydantic 모델들
class DocumentUploadResponse(BaseModel):
    success: bool
    message: str
    document_title: Optional[str] = None
    chunks_count: Optional[int] = None
    stored_count: Optional[int] = None
    file_path: Optional[str] = None

class QuestionGenerationRequest(BaseModel):
    topic: str
    difficulty: str = "중"
    question_type: str = "multiple_choice"
    context_limit: int = 3

class QuestionGenerationResponse(BaseModel):
    success: bool
    message: str
    question: Optional[Dict[str, Any]] = None
    contexts_used: Optional[List[Dict[str, Any]]] = None
    sources: Optional[List[str]] = None

class RAGStatistics(BaseModel):
    document_count: int
    chunk_count: int
    avg_chunk_length: int
    recent_documents: List[Dict[str, Any]]
    vector_enabled: bool
    embedding_model: Optional[str] = None

class SimilaritySearchRequest(BaseModel):
    query_text: str
    limit: int = 5
    similarity_threshold: float = 0.7

# RAG 서비스 인스턴스
rag_service = RAGService()

@router.post("/upload-document", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_title: str = Form(...),
    chunk_size: int = Form(1000),
    overlap: int = Form(200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    PDF 문서 업로드 및 RAG 처리
    """
    try:
        # 파일 검증
        if not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="PDF 파일만 업로드 가능합니다."
            )
        
        # 파일 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{current_user.id}_{file.filename}"
        file_path = rag_service.upload_dir / safe_filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # RAG 처리
        result = rag_service.upload_and_process_document(
            db=db,
            file_path=str(file_path),
            document_title=document_title,
            user_id=current_user.id,
            chunk_size=chunk_size,
            overlap=overlap
        )
        
        return DocumentUploadResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"문서 업로드 처리 중 오류 발생: {str(e)}"
        )

@router.post("/generate-question", response_model=QuestionGenerationResponse)
async def generate_question_with_rag(
    request: QuestionGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    RAG 기반 문제 생성
    """
    try:
        result = rag_service.generate_question_with_rag(
            db=db,
            topic=request.topic,
            difficulty=request.difficulty,
            question_type=request.question_type,
            context_limit=request.context_limit
        )
        
        return QuestionGenerationResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"문제 생성 중 오류 발생: {str(e)}"
        )

@router.post("/similarity-search")
async def similarity_search(
    request: SimilaritySearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    벡터 유사도 검색
    """
    try:
        results = rag_service.similarity_search(
            db=db,
            query_text=request.query_text,
            limit=request.limit,
            similarity_threshold=request.similarity_threshold
        )
        
        return {
            "success": True,
            "results": results,
            "total_count": len(results)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"유사도 검색 중 오류 발생: {str(e)}"
        )

@router.get("/statistics", response_model=RAGStatistics)
async def get_rag_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    RAG 시스템 통계 정보 조회
    """
    try:
        stats = rag_service.get_rag_statistics(db)
        return RAGStatistics(**stats)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"통계 조회 중 오류 발생: {str(e)}"
        )

@router.get("/documents")
async def get_rag_documents(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    RAG 문서 목록 조회
    """
    try:
        from sqlalchemy import text
        
        with db.begin():
            result = db.execute(text("""
                SELECT DISTINCT file_title, created_at, COUNT(*) as chunk_count
                FROM questions 
                WHERE file_category = 'RAG_DOCUMENT'
                GROUP BY file_title, created_at
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """), {"limit": limit, "offset": offset})
            
            documents = []
            for row in result:
                documents.append({
                    "title": row[0],
                    "uploaded_at": row[1],
                    "chunk_count": row[2]
                })
            
            return {
                "success": True,
                "documents": documents,
                "total_count": len(documents)
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"문서 목록 조회 중 오류 발생: {str(e)}"
        )

@router.delete("/document/{document_title}")
async def delete_rag_document(
    document_title: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    RAG 문서 삭제
    """
    try:
        from sqlalchemy import text
        
        # 해당 문서의 모든 청크 삭제
        result = db.execute(text("""
            DELETE FROM questions 
            WHERE file_category = 'RAG_DOCUMENT' AND file_title = :title
        """), {"title": document_title})
        
        deleted_count = result.rowcount
        db.commit()
        
        return {
            "success": True,
            "message": f"문서 '{document_title}' 삭제 완료",
            "deleted_chunks": deleted_count
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"문서 삭제 중 오류 발생: {str(e)}"
        )

@router.post("/reindex")
async def reindex_vectors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    벡터 인덱스 재구성
    """
    try:
        from sqlalchemy import text
        
        # 벡터 인덱스 재구성 (PostgreSQL)
        with db.begin():
            db.execute(text("REINDEX INDEX CONCURRENTLY IF EXISTS questions_embedding_idx"))
        
        return {
            "success": True,
            "message": "벡터 인덱스 재구성 완료"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"벡터 인덱스 재구성 중 오류 발생: {str(e)}"
        ) 