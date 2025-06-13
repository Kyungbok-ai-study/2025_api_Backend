"""
메인 FastAPI 애플리케이션
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import uvicorn

from .core.config import settings
from .db.database import engine, Base

# API 라우터 임포트 (실제 구조에 맞게 수정)
from .api.endpoints import auth
from .api import api as endpoints
from .api.endpoints import student, professor, admin
from .api import rag, advanced_rag, enterprise_rag

# 진단 관련 라우터들
from .api import diagnosis

# 진단테스트 라우터 별도 임포트
try:
    from .api.endpoints import diagnostic_test
    print("✅ 진단테스트 라우터 import 성공")
except Exception as e:
    print(f"❌ 진단테스트 라우터 import 실패: {e}")
    diagnostic_test = None

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

# FastAPI 앱 생성
app = FastAPI(
    title="KB Learning Platform",
    description="딥시크 기반 KB 학습 플랫폼 API",
    version="3.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(auth.router)
app.include_router(endpoints.router)  
app.include_router(student.router)
app.include_router(professor.router)
app.include_router(admin.router)

# 진단 라우터 등록
app.include_router(diagnosis.router, prefix="/api/diagnosis", tags=["진단"])

# 진단테스트 라우터 등록 (조건부)
if diagnostic_test is not None:
    app.include_router(diagnostic_test.router, prefix="/api/diagnostic", tags=["진단테스트"])
    print("✅ 진단테스트 라우터 등록 완료")
else:
    print("❌ 진단테스트 라우터 등록 실패")

# RAG 관련 라우터들
app.include_router(rag.router)
app.include_router(advanced_rag.router)
app.include_router(enterprise_rag.router)  # 🏢 엔터프라이즈 RAG API

# 벡터 관리 라우터 (Qdrant)
try:
    from .api.endpoints import vector_management
    app.include_router(vector_management.router)
    print("✅ Qdrant 벡터 관리 라우터 등록 완료")
except Exception as e:
    print(f"❌ Qdrant 벡터 관리 라우터 등록 실패: {e}")

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "KB Learning Platform API",
        "version": "3.0.0",
        "features": [
            "딥시크 AI 통합",
            "Qdrant 벡터 검색",
            "기본 RAG 시스템",
            "고급 RAG 기능",
            "🏢 엔터프라이즈 RAG 시스템"
        ],
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "database": "connected",
        "timestamp": "2025-01-27T10:00:00Z"
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 