"""
경복대학교 학습 지원 플랫폼 백엔드 메인 애플리케이션
"""
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import StreamingResponse
from starlette.middleware.sessions import SessionMiddleware
import json
import logging
import time
from contextlib import asynccontextmanager

from app.api.api import api_router
from app.db.database import Base, engine
from app.core.config import settings

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작 시 실행
    logger.info("🚀 CampusON API 서버 시작")
    logger.info(f"📊 설정: DEBUG={settings.DEBUG}, DB_ECHO={settings.DATABASE_ECHO}")
    
    # 데이터베이스 테이블 생성
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ 데이터베이스 테이블 초기화 완료")
    except Exception as e:
        logger.error(f"❌ 데이터베이스 초기화 실패: {str(e)}")
        raise
    
    yield
    
    # 종료 시 실행
    logger.info("🛑 CampusON API 서버 종료")

# FastAPI 앱 인스턴스 생성
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# 세션 미들웨어 (소셜 로그인용)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    max_age=3600  # 1시간
)

# 신뢰할 수 있는 호스트 미들웨어
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=["localhost", "127.0.0.1", "*.kyungbok.ac.kr"]
    )

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.ALLOWED_METHODS,
    allow_headers=settings.ALLOWED_HEADERS,
)

# 요청/응답 로깅 미들웨어
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """요청/응답 로깅"""
    start_time = time.time()
    
    # 요청 로깅
    logger.info(f"📥 {request.method} {request.url.path} - {request.client.host}")
    
    response = await call_next(request)
    
    # 응답 시간 계산
    process_time = time.time() - start_time
    
    # 응답 로깅
    logger.info(
        f"📤 {request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    
    # 응답 헤더에 처리 시간 추가
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

# 보안 헤더 미들웨어
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """보안 헤더 추가"""
    response = await call_next(request)
    
    if settings.SECURITY_HEADERS_ENABLED:
        # 보안 헤더 추가
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # 개발 환경이 아닌 경우에만 HTTPS 강제
        if not settings.DEBUG:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' https:; "
                "connect-src 'self' https:"
            )
    
    return response

# dataclasses_json과 함께 사용하기 위한 JSON 응답 처리 커스터마이징
@app.middleware("http")
async def custom_json_middleware(request, call_next):
    """JSON 응답 처리 커스터마이징"""
    response = await call_next(request)
    
    # StreamingResponse는 body() 메서드가 없으므로 체크 필요
    if (response.headers.get("content-type") == "application/json" and 
        not isinstance(response, StreamingResponse)):
        try:
            # StreamingResponse가 아닌 경우에만 body 처리
            body = await response.body()
            if body:
                # 이미 JSON 문자열로 변환된 응답 본문 처리
                body_text = body.decode()
        except Exception:
            # 에러 발생 시 원래 응답 반환
            pass
            
    return response

# 전역 예외 처리기
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 처리"""
    logger.error(f"🔥 전역 예외 발생: {type(exc).__name__}: {str(exc)}")
    
    if settings.DEBUG:
        # 개발 환경에서는 상세 에러 정보 반환
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": str(exc),
                "type": type(exc).__name__
            }
        )
    else:
        # 프로덕션 환경에서는 일반적인 에러 메시지 반환
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": "서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
            }
        )

# API 라우터 포함
app.include_router(api_router, prefix="/api")

# 루트 엔드포인트
@app.get("/")
async def root():
    """
    루트 엔드포인트
    
    Returns:
        dict: 환영 메시지 및 API 정보
    """
    return {
        "message": "경복대학교 학습 지원 플랫폼 API에 오신 것을 환영합니다.",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/api/docs" if settings.DEBUG else "문서는 개발 환경에서만 제공됩니다",
        "status": "healthy",
        "features": [
            "🔐 사용자 인증 및 권한 관리",
            "📝 진단 테스트 시스템",
            "🎯 AI 기반 맞춤형 문제 추천",
            "🤖 AI 문제 생성 (EXAONE Deep)",
            "📊 학습 대시보드 및 분석",
            "📈 학습 진행 상황 추적",
            "🔍 벡터 기반 유사도 검색",
            "📱 반응형 웹 지원"
        ]
    }

# 헬스 체크 엔드포인트
@app.get("/health")
async def health_check():
    """
    헬스 체크 엔드포인트
    
    Returns:
        dict: 서비스 상태 정보
    """
    try:
        # 데이터베이스 연결 확인
        from app.db.database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        db_status = "healthy"
    except Exception as e:
        logger.error(f"데이터베이스 헬스 체크 실패: {str(e)}")
        db_status = "unhealthy"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "timestamp": time.time(),
        "services": {
            "database": db_status,
            "api": "healthy"
        },
        "version": settings.VERSION,
        "environment": "development" if settings.DEBUG else "production"
    }

# API 정보 엔드포인트
@app.get("/api/info")
async def api_info():
    """
    API 정보 엔드포인트
    
    Returns:
        dict: API 상세 정보
    """
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "description": settings.DESCRIPTION,
        "endpoints": {
            "authentication": "/api/auth",
            "diagnosis": "/api/diagnosis",
            "problems": "/api/problems", 
            "dashboard": "/api/dashboard"
        },
        "features": {
            "pgvector_enabled": settings.PGVECTOR_ENABLED,
            "ai_model": settings.AI_MODEL_NAME,
            "public_api_enabled": settings.PUBLIC_API_ENABLED,
            "cors_enabled": True
        }
    }

# 앱 실행 설정
if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host=settings.HOST, 
        port=settings.PORT, 
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    ) 