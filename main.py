"""
경복대학교 학습 지원 플랫폼 백엔드 메인 애플리케이션
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
import json

from app.api.api import api_router
from app.db.database import Base, engine

# FastAPI 앱 인스턴스 생성
app = FastAPI(
    title="경복대학교 학습 지원 플랫폼 API",
    description="경복대학교 학생 및 교수를 위한 학습 지원 플랫폼 API",
    version="0.1.0",
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경에서는 모든 origin 허용 (프로덕션에서는 변경 필요)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 포함
app.include_router(api_router, prefix="/api")

# dataclasses_json과 함께 사용하기 위한 JSON 응답 처리 커스터마이징
@app.middleware("http")
async def custom_json_middleware(request, call_next):
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

# 루트 엔드포인트
@app.get("/")
async def root():
    """
    루트 엔드포인트
    
    Returns:
        dict: 환영 메시지
    """
    return {"message": "경복대학교 학습 지원 플랫폼 API에 오신 것을 환영합니다."}

# 앱 실행 설정
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 