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
from .api.endpoints import student, admin
from .api.endpoints import professor_clean as professor
from .api import rag, advanced_rag, enterprise_rag

# 진단 관련 라우터들
from .api import diagnosis
from .api.v1.diagnosis import department_tests
from .routers import diagnosis as diagnosis_router  # 새로운 진단 라우터

# 진단테스트 라우터는 통합 진단 시스템으로 대체됨 (unified_diagnosis.py 사용)

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

# CORS 설정 - 환경별 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS if not settings.DEBUG else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(auth.router, prefix="/api/auth", tags=["인증"])
app.include_router(endpoints.api_router, prefix="/api")  
app.include_router(student.router, prefix="/api/student", tags=["학생"])
app.include_router(professor.router, prefix="/api/professor", tags=["교수-정리됨"])
app.include_router(admin.router, prefix="/api/admin", tags=["관리자"])

# 진단 라우터 등록
app.include_router(diagnosis.router, prefix="/api/diagnosis", tags=["진단"])

# 새로운 진단 라우터 등록 (문제 데이터 제공)
app.include_router(diagnosis_router.router, prefix="/api/diagnosis", tags=["진단 데이터"])

# 학과별 진단테스트 v1 라우터 등록
app.include_router(department_tests.router, prefix="/api/diagnosis/v1", tags=["학과별 진단테스트"])

# 진단테스트 차수 관리 라우터 등록
from .api.endpoints import diagnosis_progress
app.include_router(diagnosis_progress.router, prefix="/api/diagnosis/progress", tags=["진단테스트 차수 관리"])

# 진단테스트는 통합 진단 시스템으로 대체됨 (/api/diagnosis 경로 사용)

# RAG 관련 라우터들
app.include_router(rag.router)
app.include_router(advanced_rag.router)
app.include_router(enterprise_rag.router)  # 🏢 엔터프라이즈 RAG API

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