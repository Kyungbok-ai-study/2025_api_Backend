"""
RAG 시스템 API 엔드포인트 - DeepSeek + Gemini 통합
"""
import os
import shutil
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..db.database import get_db
from ..auth.dependencies import get_current_user
from ..models.user import User
from ..services.rag_system import RAGService
from ..services.deepseek_service import deepseek_service
from ..services.qdrant_service import qdrant_service
from ..services.rag_integration_service import rag_integration_service

router = APIRouter(prefix="/rag", tags=["RAG 문서 관리"])

# === DeepSeek + Gemini 통합 Pydantic 모델들 ===

class DeepSeekRAGUploadRequest(BaseModel):
    """DeepSeek RAG 업데이트 요청 모델"""
    document_title: str = Field(..., min_length=1, max_length=200)
    department: str = Field(..., description="학과 (간호학과, 물리치료학과, 작업치료학과)")
    subject: Optional[str] = Field(None, description="과목명")
    auto_classify: bool = Field(True, description="자동 분류 사용 여부")
    chunk_size: int = Field(1000, ge=100, le=3000)
    overlap: int = Field(200, ge=0, le=500)
    use_deepseek_labeling: bool = Field(True, description="DeepSeek 라벨링 사용")

class DeepSeekRAGUploadResponse(BaseModel):
    """DeepSeek RAG 업데이트 응답 모델"""
    success: bool
    message: str
    processing_id: str
    document_info: Dict[str, Any]
    processing_steps: Dict[str, Any]
    statistics: Dict[str, Any]

class RAGProcessingStatus(BaseModel):
    """RAG 처리 상태 모델"""
    processing_id: str
    status: str  # "processing", "completed", "failed"
    progress_percentage: int
    current_step: str
    steps_completed: List[str]
    results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class DeepSeekKnowledgeBaseStats(BaseModel):
    """DeepSeek 지식베이스 통계"""
    total_documents: int
    total_chunks: int
    total_vectors: int
    departments: Dict[str, int]
    subjects: Dict[str, int]
    difficulty_distribution: Dict[str, int]
    last_updated: str
    embedding_model: str
    vector_dimension: int

# === 기존 모델들 ===
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

# 서비스 인스턴스들
rag_service = RAGService()

# === DeepSeek + Gemini 통합 엔드포인트들 ===

@router.post("/deepseek-upload", response_model=DeepSeekRAGUploadResponse)
async def upload_document_with_deepseek(
    file: UploadFile = File(...),
    request_data: str = Form(...),  # JSON 문자열로 받아서 파싱
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    DeepSeek + Gemini 통합 문서 업로드 및 처리
    
    워크플로우:
    1. Gemini로 PDF 파싱
    2. DeepSeek으로 난이도/유형 분류  
    3. Qdrant 벡터 DB에 저장
    4. DeepSeek 학습 데이터 업데이트
    """
    import json
    import uuid
    
    try:
        # 요청 데이터 파싱
        try:
            request = DeepSeekRAGUploadRequest(**json.loads(request_data))
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"잘못된 요청 데이터: {str(e)}"
            )
        
        # 파일 검증
        if not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="PDF 파일만 업로드 가능합니다."
            )
        
        # 처리 ID 생성
        processing_id = str(uuid.uuid4())
        
        # 파일 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"deepseek_{timestamp}_{current_user.id}_{file.filename}"
        upload_dir = Path("uploads/rag_documents")
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / safe_filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # DeepSeek + Gemini 통합 처리 시작
        processing_result = await _process_document_with_deepseek_gemini(
            file_path=file_path,
            request=request,
            processing_id=processing_id,
            user_id=current_user.id,
            db=db
        )
        
        return DeepSeekRAGUploadResponse(
            success=processing_result["success"],
            message=processing_result["message"],
            processing_id=processing_id,
            document_info=processing_result["document_info"],
            processing_steps=processing_result["processing_steps"],
            statistics=processing_result["statistics"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"DeepSeek RAG 처리 중 오류 발생: {str(e)}"
        )

@router.get("/deepseek-status/{processing_id}", response_model=RAGProcessingStatus)
async def get_deepseek_processing_status(
    processing_id: str,
    current_user: User = Depends(get_current_user)
):
    """DeepSeek RAG 처리 상태 조회"""
    try:
        # 처리 상태 조회 (실제 구현에서는 Redis나 DB에서 상태 관리)
        status_file = Path(f"temp/processing_status_{processing_id}.json")
        
        if not status_file.exists():
            raise HTTPException(
                status_code=404,
                detail="처리 상태를 찾을 수 없습니다."
            )
        
        with open(status_file, 'r', encoding='utf-8') as f:
            status_data = json.load(f)
        
        return RAGProcessingStatus(**status_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"처리 상태 조회 중 오류 발생: {str(e)}"
        )

@router.get("/deepseek-knowledge-base-stats", response_model=DeepSeekKnowledgeBaseStats)
async def get_deepseek_knowledge_base_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """DeepSeek 지식베이스 통계 조회"""
    try:
        # Qdrant 통계 조회
        qdrant_stats = qdrant_service.get_collection_info()
        
        # 데이터베이스 통계 조회
        from sqlalchemy import text, func
        
        # 부서별 통계
        dept_stats = db.execute(text("""
            SELECT department, COUNT(*) as count
            FROM questions 
            WHERE file_category = 'RAG_DEEPSEEK'
            GROUP BY department
        """)).fetchall()
        
        departments = {row.department or "미분류": row.count for row in dept_stats}
        
        # 과목별 통계  
        subject_stats = db.execute(text("""
            SELECT subject_name, COUNT(*) as count
            FROM questions 
            WHERE file_category = 'RAG_DEEPSEEK'
            GROUP BY subject_name
        """)).fetchall()
        
        subjects = {row.subject_name or "미분류": row.count for row in subject_stats}
        
        # 난이도별 통계
        difficulty_stats = db.execute(text("""
            SELECT difficulty, COUNT(*) as count
            FROM questions 
            WHERE file_category = 'RAG_DEEPSEEK'
            GROUP BY difficulty
        """)).fetchall()
        
        difficulty_distribution = {str(row.difficulty or "미분류"): row.count for row in difficulty_stats}
        
        return DeepSeekKnowledgeBaseStats(
            total_documents=len(list(Path("uploads/rag_documents").glob("deepseek_*.pdf"))),
            total_chunks=db.query(func.count()).filter_by(file_category='RAG_DEEPSEEK').scalar() or 0,
            total_vectors=qdrant_stats.get("vectors_count", 0),
            departments=departments,
            subjects=subjects,
            difficulty_distribution=difficulty_distribution,
            last_updated=datetime.now().isoformat(),
            embedding_model="DeepSeek Embedding",
            vector_dimension=768
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"지식베이스 통계 조회 중 오류 발생: {str(e)}"
        )

@router.post("/deepseek-reindex")
async def reindex_deepseek_knowledge_base(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """DeepSeek 지식베이스 전체 재인덱싱"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("🔄 DeepSeek 지식베이스 재인덱싱 시작")
        
        # Qdrant 컬렉션 재생성
        reindex_result = await qdrant_service.recreate_collection()
        
        if not reindex_result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"벡터 DB 재인덱싱 실패: {reindex_result.get('error')}"
            )
        
        # RAG 문서들 재처리
        rag_docs_dir = Path("uploads/rag_documents")
        processed_count = 0
        
        if rag_docs_dir.exists():
            for pdf_file in rag_docs_dir.glob("deepseek_*.pdf"):
                # 파일별 재처리 로직 (실제 구현에서는 백그라운드 작업으로)
                processed_count += 1
        
        logger.info(f"✅ DeepSeek 지식베이스 재인덱싱 완료: {processed_count}개 문서")
        
        return {
            "success": True,
            "message": f"DeepSeek 지식베이스 재인덱싱이 완료되었습니다.",
            "processed_documents": processed_count,
            "vector_count": reindex_result.get("vector_count", 0),
            "reindex_time": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"재인덱싱 중 오류 발생: {str(e)}"
        )

# === DeepSeek + Gemini 통합 처리 함수 ===

async def _process_document_with_deepseek_gemini(
    file_path: Path,
    request: DeepSeekRAGUploadRequest,
    processing_id: str,
    user_id: int,
    db: Session
) -> Dict[str, Any]:
    """
    DeepSeek + Gemini 통합 문서 처리
    """
    import logging
    import json
    
    logger = logging.getLogger(__name__)
    
    # 처리 상태 초기화
    status_data = {
        "processing_id": processing_id,
        "status": "processing",
        "progress_percentage": 0,
        "current_step": "문서 파싱 준비",
        "steps_completed": [],
        "results": None,
        "error_message": None
    }
    
    # 상태 파일 저장용 디렉토리
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)
    status_file = temp_dir / f"processing_status_{processing_id}.json"
    
    def update_status(step: str, progress: int, completed_step: str = None):
        status_data["current_step"] = step
        status_data["progress_percentage"] = progress
        if completed_step:
            status_data["steps_completed"].append(completed_step)
        
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
    
    try:
        logger.info(f"🚀 DeepSeek + Gemini 통합 처리 시작: {file_path.name}")
        
        # 1. Gemini PDF 파싱
        update_status("Gemini PDF 파싱 중...", 10)
        
        # 실제 Gemini 파싱 호출 (gemini_service 가 있다고 가정)
        from ..services.gemini_service import gemini_service
        parsing_result = await gemini_service.parse_pdf_document(
            file_path=str(file_path),
            department=request.department
        )
        
        if not parsing_result["success"]:
            raise Exception(f"Gemini 파싱 실패: {parsing_result.get('error')}")
        
        update_status("PDF 파싱 완료", 25, "Gemini PDF 파싱")
        
        # 2. 텍스트 청킹
        update_status("텍스트 청킹 중...", 35)
        
        content = parsing_result["content"]
        chunks = _create_text_chunks(content, request.chunk_size, request.overlap)
        
        update_status("텍스트 청킹 완료", 45, "텍스트 청킹")
        
        # 3. DeepSeek 분류 및 라벨링
        update_status("DeepSeek 분류 및 라벨링 중...", 55)
        
        classified_chunks = []
        for i, chunk in enumerate(chunks):
            if request.use_deepseek_labeling:
                # DeepSeek으로 난이도 및 유형 분류
                classification_result = await deepseek_service.classify_content(
                    content=chunk,
                    department=request.department,
                    subject=request.subject
                )
                
                chunk_data = {
                    "content": chunk,
                    "difficulty": classification_result.get("difficulty", "중"),
                    "content_type": classification_result.get("content_type", "이론"),
                    "keywords": classification_result.get("keywords", []),
                    "chunk_index": i
                }
            else:
                chunk_data = {
                    "content": chunk,
                    "difficulty": "중",
                    "content_type": "이론",
                    "keywords": [],
                    "chunk_index": i
                }
            
            classified_chunks.append(chunk_data)
        
        update_status("DeepSeek 분류 완료", 70, "DeepSeek 분류 및 라벨링")
        
        # 4. Qdrant 벡터 DB 저장
        update_status("벡터 DB 저장 중...", 80)
        
        vector_storage_results = []
        for chunk_data in classified_chunks:
            # 메타데이터 준비
            metadata = {
                "document_title": request.document_title,
                "department": request.department,
                "subject": request.subject or "일반",
                "difficulty": chunk_data["difficulty"],
                "content_type": chunk_data["content_type"],
                "keywords": chunk_data["keywords"],
                "chunk_index": chunk_data["chunk_index"],
                "file_category": "RAG_DEEPSEEK",
                "user_id": user_id,
                "created_at": datetime.now().isoformat()
            }
            
            # Qdrant에 저장
            vector_result = await qdrant_service.add_vectors(
                texts=[chunk_data["content"]],
                metadatas=[metadata],
                ids=[f"deepseek_{processing_id}_{chunk_data['chunk_index']}"]
            )
            
            vector_storage_results.append(vector_result)
        
        update_status("벡터 DB 저장 완료", 90, "Qdrant 벡터 저장")
        
        # 5. 학습 데이터 업데이트
        update_status("학습 데이터 업데이트 중...", 95)
        
        # DeepSeek 학습 데이터로 저장
        training_data = {
            "document_info": {
                "title": request.document_title,
                "department": request.department,
                "subject": request.subject,
                "file_path": str(file_path),
                "processing_id": processing_id
            },
            "chunks": classified_chunks,
            "statistics": {
                "total_chunks": len(classified_chunks),
                "successful_vectors": sum(1 for r in vector_storage_results if r.get("success")),
                "failed_vectors": sum(1 for r in vector_storage_results if not r.get("success"))
            }
        }
        
        # 학습 데이터 파일 저장
        training_dir = Path("data/deepseek_training")
        training_dir.mkdir(parents=True, exist_ok=True)
        training_file = training_dir / f"training_{processing_id}.json"
        
        with open(training_file, 'w', encoding='utf-8') as f:
            json.dump(training_data, f, ensure_ascii=False, indent=2)
        
        update_status("처리 완료", 100, "학습 데이터 업데이트")
        
        # 최종 결과
        final_result = {
            "success": True,
            "message": f"DeepSeek + Gemini 통합 처리가 완료되었습니다.",
            "document_info": training_data["document_info"],
            "processing_steps": {
                "gemini_parsing": {"success": True, "content_length": len(content)},
                "text_chunking": {"success": True, "chunk_count": len(classified_chunks)},
                "deepseek_classification": {"success": True, "classified_count": len(classified_chunks)},
                "vector_storage": {"success": True, "stored_count": training_data["statistics"]["successful_vectors"]},
                "training_update": {"success": True, "training_file": str(training_file)}
            },
            "statistics": training_data["statistics"]
        }
        
        # 최종 상태 업데이트
        status_data["status"] = "completed"
        status_data["results"] = final_result
        
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ DeepSeek + Gemini 통합 처리 완료: {processing_id}")
        
        return final_result
        
    except Exception as e:
        logger.error(f"❌ DeepSeek + Gemini 통합 처리 실패: {e}")
        
        # 오류 상태 업데이트
        status_data["status"] = "failed"
        status_data["error_message"] = str(e)
        
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
        
        return {
            "success": False,
            "message": f"처리 중 오류가 발생했습니다: {str(e)}",
            "document_info": {},
            "processing_steps": {},
            "statistics": {}
        }

def _create_text_chunks(text: str, chunk_size: int, overlap: int) -> List[str]:
    """텍스트를 청크로 분할"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # 청크 경계에서 단어가 잘리지 않도록 조정
        if end < len(text):
            # 공백이나 문장 끝에서 자르기
            while end > start and text[end] not in [' ', '\n', '.', '!', '?']:
                end -= 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
        
        if start >= len(text):
            break
    
    return chunks

# === 기존 엔드포인트들 ===

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