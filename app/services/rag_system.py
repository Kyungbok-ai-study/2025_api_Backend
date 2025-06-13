"""
RAG (Retrieval-Augmented Generation) 시스템 서비스
DeepSeek + Qdrant 기반으로 완전 전환
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import uuid
import asyncio

# PDF 처리를 위한 조건부 임포트
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
from sqlalchemy.orm import Session
from sqlalchemy import text, func

from ..models.question import Question
from ..core.config import settings
from ..db.database import engine
from .deepseek_service import deepseek_service
from .qdrant_service import qdrant_service

logger = logging.getLogger(__name__)

class RAGService:
    """RAG 시스템 서비스 - DeepSeek + Qdrant 기반"""
    
    def __init__(self):
        self.upload_dir = Path("uploads/rag_documents")
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # DeepSeek과 Qdrant 서비스 사용
        self.deepseek = deepseek_service
        self.vector_db = qdrant_service
        
        logger.info("✅ RAG 서비스 초기화 완료 (DeepSeek + Qdrant)")
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """PDF에서 텍스트 추출"""
        try:
            if not PYPDF2_AVAILABLE:
                logger.warning("PyPDF2가 설치되지 않아 PDF 처리를 건너뜁니다")
                return "PDF 파일 처리를 위해 PyPDF2 설치가 필요합니다"
                
            text_content = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
            
            logger.info(f"📄 PDF 텍스트 추출 완료: {len(text_content)} 문자")
            return text_content
            
        except Exception as e:
            logger.error(f"❌ PDF 텍스트 추출 실패: {e}")
            return ""
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """텍스트를 청크로 분할"""
        if not text:
            return []
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + chunk_size
            if end > text_length:
                end = text_length
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            if start >= text_length:
                break
        
        logger.info(f"📊 텍스트 청킹 완료: {len(chunks)}개 청크")
        return chunks
    
    async def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """DeepSeek으로 임베딩 생성"""
        try:
            result = await self.deepseek.create_embeddings(texts)
            
            if result["success"]:
                logger.info(f"🧠 DeepSeek 임베딩 생성 완료: {len(result['embeddings'])}개")
                return result["embeddings"]
            else:
                logger.error(f"❌ 임베딩 생성 실패: {result.get('error', 'Unknown error')}")
                return []
                
        except Exception as e:
            logger.error(f"❌ 임베딩 생성 중 오류: {e}")
            return []
    
    async def store_document_embeddings(
        self, 
        db: Session, 
        document_title: str,
        document_path: str,
        text_chunks: List[str],
        user_id: int
    ) -> int:
        """문서 임베딩을 Qdrant + PostgreSQL에 저장"""
        try:
            stored_count = 0
            
            # 메타데이터 준비
            metadatas = []
            for i, chunk in enumerate(text_chunks):
                metadata = {
                    "document_title": document_title,
                    "document_path": document_path,
                    "chunk_index": i,
                    "user_id": user_id,
                    "type": "rag_document",
                    "subject": f"RAG-{document_title}",
                    "area_name": "RAG Knowledge Base"
                }
                metadatas.append(metadata)
            
            # Qdrant에 벡터 저장
            vector_result = await self.vector_db.add_vectors(
                texts=text_chunks,
                metadatas=metadatas
            )
            
            if not vector_result["success"]:
                logger.error(f"❌ Qdrant 벡터 저장 실패: {vector_result.get('error')}")
                return 0
            
            # PostgreSQL에 메타데이터 저장
            for i, chunk in enumerate(text_chunks):
                question = Question(
                    question_number=i + 1,
                    question_type="rag_document",
                    content=chunk,
                    subject=f"RAG-{document_title}",
                    area_name="RAG Knowledge Base",
                    difficulty="중",
                    approval_status="approved",
                    source_file_path=document_path,
                    file_title=document_title,
                    file_category="RAG_DOCUMENT",
                    is_active=True,
                    last_modified_by=user_id,
                    last_modified_at=datetime.now(),
                    approved_by=user_id,
                    approved_at=datetime.now()
                )
                
                db.add(question)
                stored_count += 1
            
            db.commit()
            logger.info(f"✅ RAG 문서 저장 완료: {stored_count}개 청크 (Qdrant + PostgreSQL)")
            return stored_count
            
        except Exception as e:
            logger.error(f"❌ RAG 문서 저장 실패: {e}")
            db.rollback()
            return 0
    
    async def upload_and_process_document(
        self, 
        db: Session,
        file_path: str,
        document_title: str,
        user_id: int,
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> Dict[str, Any]:
        """문서 업로드 및 RAG 처리 - 완전 비동기"""
        try:
            logger.info(f"🚀 RAG 문서 처리 시작: {document_title}")
            
            # 1. PDF 텍스트 추출
            text_content = self.extract_text_from_pdf(file_path)
            if not text_content:
                return {"success": False, "message": "PDF 텍스트 추출 실패"}
            
            # 2. 텍스트 청킹
            text_chunks = self.chunk_text(text_content, chunk_size, overlap)
            if not text_chunks:
                return {"success": False, "message": "텍스트 청킹 실패"}
            
            # 3. 임베딩 생성 및 저장
            stored_count = await self.store_document_embeddings(
                db, document_title, file_path, text_chunks, user_id
            )
            
            if stored_count == 0:
                return {"success": False, "message": "문서 저장 실패"}
            
            return {
                "success": True,
                "message": f"🎉 RAG 문서 처리 완료",
                "document_title": document_title,
                "chunks_count": len(text_chunks),
                "stored_count": stored_count,
                "total_characters": len(text_content)
            }
            
        except Exception as e:
            logger.error(f"❌ RAG 문서 처리 실패: {e}")
            return {"success": False, "message": f"처리 중 오류 발생: {str(e)}"}
    
    async def similarity_search(
        self, 
        db: Session,
        query_text: str,
        limit: int = 5,
        similarity_threshold: float = 0.7,
        document_title: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Qdrant 기반 유사도 검색"""
        try:
            # 필터 조건 설정
            filter_conditions = {"type": "rag_document"}
            if document_title:
                filter_conditions["document_title"] = document_title
            
            # Qdrant에서 유사 문서 검색
            search_result = await self.vector_db.search_vectors(
                query_text=query_text,
                limit=limit,
                score_threshold=similarity_threshold,
                filter_conditions=filter_conditions
            )
            
            if not search_result["success"]:
                logger.error(f"❌ 벡터 검색 실패: {search_result.get('error')}")
                return []
            
            results = []
            for item in search_result["results"]:
                result = {
                    "content": item["text"],
                    "similarity": item["score"],
                    "document_title": item["metadata"].get("document_title", ""),
                    "chunk_index": item["metadata"].get("chunk_index", 0),
                    "subject": item["metadata"].get("subject", ""),
                    "area_name": item["metadata"].get("area_name", "")
                }
                results.append(result)
            
            logger.info(f"🔍 유사도 검색 완료: {len(results)}개 결과")
            return results
            
        except Exception as e:
            logger.error(f"❌ 유사도 검색 실패: {e}")
            return []
    
    async def generate_question_with_rag(
        self,
        db: Session,
        topic: str,
        difficulty: str = "중",
        question_type: str = "multiple_choice",
        context_limit: int = 3,
        department: str = "간호학과"
    ) -> Dict[str, Any]:
        """RAG 기반 문제 생성 - DeepSeek 사용"""
        try:
            logger.info(f"🎯 RAG 문제 생성 시작: {topic} ({difficulty})")
            
            # 1. 관련 컨텍스트 검색
            contexts = await self.similarity_search(
                db=db,
                query_text=topic,
                limit=context_limit,
                similarity_threshold=0.6
            )
            
            if not contexts:
                logger.warning("⚠️ 관련 컨텍스트를 찾을 수 없음")
                return {"success": False, "message": "관련 학습 자료를 찾을 수 없습니다."}
            
            # 2. 컨텍스트 통합
            context_text = "\n\n".join([ctx["content"] for ctx in contexts])
            
            # 3. DeepSeek으로 문제 생성
            prompt = f"""
다음은 {department} 학습 자료입니다:

{context_text}

위 내용을 바탕으로 다음 조건에 맞는 문제를 생성해주세요:
- 주제: {topic}
- 난이도: {difficulty}
- 문제 유형: {question_type}
- 대상: {department} 학생

문제는 다음 JSON 형식으로 작성해주세요:
{{
    "question": "문제 내용",
    "options": ["선택지1", "선택지2", "선택지3", "선택지4"],
    "correct_answer": 1,
    "explanation": "정답 해설",
    "difficulty": "{difficulty}",
    "subject": "{topic}",
    "source_contexts": ["사용된 컨텍스트 요약"]
}}
"""
            
            generation_result = await self.deepseek.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            if not generation_result["success"]:
                logger.error(f"❌ 문제 생성 실패: {generation_result.get('error')}")
                return {"success": False, "message": "문제 생성 중 오류 발생"}
            
            # 4. 결과 파싱
            try:
                question_data = json.loads(generation_result["content"])
                
                # 컨텍스트 정보 추가
                question_data["rag_contexts"] = [
                    {
                        "content": ctx["content"][:200] + "...",
                        "similarity": ctx["similarity"],
                        "source": ctx["document_title"]
                    }
                    for ctx in contexts
                ]
                
                logger.info(f"✅ RAG 문제 생성 완료: {question_data.get('subject', topic)}")
                
                return {
                    "success": True,
                    "question_data": question_data,
                    "contexts_used": len(contexts),
                    "generation_method": "DeepSeek + Qdrant RAG"
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON 파싱 실패: {e}")
                return {"success": False, "message": "생성된 문제 형식 오류"}
            
        except Exception as e:
            logger.error(f"❌ RAG 문제 생성 실패: {e}")
            return {"success": False, "message": f"문제 생성 중 오류: {str(e)}"}
    
    async def get_rag_statistics(self, db: Session) -> Dict[str, Any]:
        """RAG 시스템 통계 조회"""
        try:
            # PostgreSQL 통계
            total_docs = db.query(func.count(Question.id)).filter(
                Question.question_type == "rag_document"
            ).scalar()
            
            unique_docs = db.query(func.count(func.distinct(Question.file_title))).filter(
                Question.question_type == "rag_document"
            ).scalar()
            
            # Qdrant 통계
            qdrant_info = self.vector_db.get_collection_info()
            
            stats = {
                "total_chunks": total_docs,
                "unique_documents": unique_docs,
                "vector_db_status": qdrant_info.get("success", False),
                "vector_count": qdrant_info.get("points_count", 0) if qdrant_info.get("success") else 0,
                "collection_name": qdrant_info.get("collection_name", ""),
                "last_updated": datetime.now().isoformat(),
                "system_type": "DeepSeek + Qdrant"
            }
            
            logger.info(f"📊 RAG 통계 조회 완료: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ RAG 통계 조회 실패: {e}")
            return {
                "total_chunks": 0,
                "unique_documents": 0,
                "vector_db_status": False,
                "error": str(e)
            }
    
    async def delete_document(self, db: Session, document_title: str) -> Dict[str, Any]:
        """문서 삭제 (PostgreSQL + Qdrant)"""
        try:
            # PostgreSQL에서 삭제
            deleted_count = db.query(Question).filter(
                Question.question_type == "rag_document",
                Question.file_title == document_title
            ).delete()
            
            db.commit()
            
            # Qdrant에서 삭제 (문서별 삭제는 필터 기반으로 구현 필요)
            # 현재는 개별 ID 삭제만 지원하므로 향후 개선 필요
            
            logger.info(f"🗑️ 문서 삭제 완료: {document_title} ({deleted_count}개 청크)")
            
            return {
                "success": True,
                "message": f"문서 삭제 완료: {document_title}",
                "deleted_chunks": deleted_count
            }
            
        except Exception as e:
            logger.error(f"❌ 문서 삭제 실패: {e}")
            db.rollback()
            return {"success": False, "message": f"삭제 중 오류: {str(e)}"}
    
    async def add_document(self, doc_id: str, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """문서 추가 (테스트용 간단 버전)"""
        try:
            if metadata is None:
                metadata = {}
            
            # 메타데이터 설정
            doc_metadata = {
                "document_id": doc_id,
                "type": "test_document",
                **metadata
            }
            
            # 벡터 추가
            result = await self.vector_db.add_vectors(
                texts=[content],
                metadatas=[doc_metadata]
            )
            
            if result["success"]:
                logger.info(f"✅ 테스트 문서 추가 완료: {doc_id}")
                return {"success": True, "message": "문서 추가 완료"}
            else:
                return {"success": False, "error": result.get("error", "Unknown")}
                
        except Exception as e:
            logger.error(f"❌ 문서 추가 실패: {e}")
            return {"success": False, "error": str(e)}
    
    async def generate_answer(self, query: str, department: str = "간호학과") -> str:
        """RAG 기반 답변 생성 (테스트용 간단 버전)"""
        try:
            # 관련 문서 검색
            search_result = await self.vector_db.search_vectors(
                query_text=query,
                limit=3,
                score_threshold=0.5
            )
            
            if not search_result["success"] or not search_result["results"]:
                return "관련 정보를 찾을 수 없습니다."
            
            # 컨텍스트 구성
            contexts = []
            for result in search_result["results"]:
                contexts.append(result["text"])
            
            context_text = "\n\n".join(contexts)
            
            # DeepSeek으로 답변 생성
            prompt = f"""
다음 정보를 바탕으로 질문에 답변해주세요.

컨텍스트:
{context_text}

질문: {query}

{department} 학생에게 적합한 답변을 제공해주세요.
"""
            
            messages = [{"role": "user", "content": prompt}]
            result = await self.deepseek.chat_completion(messages, temperature=0.3)
            
            if result["success"]:
                return result["content"]
            else:
                return "답변 생성 중 오류가 발생했습니다."
                
        except Exception as e:
            logger.error(f"❌ RAG 답변 생성 실패: {e}")
            return "답변 생성 중 오류가 발생했습니다."

# 싱글톤 인스턴스
rag_service = RAGService()
rag_system = rag_service  # 하위 호환성을 위한 별칭 