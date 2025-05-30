"""
API 라우터 설정
"""
from fastapi import APIRouter

from app.api.endpoints import auth, diagnosis, problems, dashboard

api_router = APIRouter()

# 인증 관련 라우터
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# 진단 테스트 관련 라우터
api_router.include_router(diagnosis.router, prefix="/diagnosis", tags=["diagnosis"])

# 문제 추천 및 AI 생성 관련 라우터
api_router.include_router(problems.router, prefix="/problems", tags=["problems"])

# 대시보드 관련 라우터
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"]) 