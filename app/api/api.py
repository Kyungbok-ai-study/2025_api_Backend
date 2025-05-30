"""
Main API 라우터 설정
"""
from fastapi import APIRouter

from app.api.endpoints import auth, diagnosis, problems, dashboard, professor, ai, security

api_router = APIRouter()

# 인증 관련 라우터
api_router.include_router(auth.router, prefix="/auth", tags=["인증"])

# 진단 테스트 관련 라우터
api_router.include_router(diagnosis.router, prefix="/diagnosis", tags=["진단"])

# 문제 추천 및 AI 생성 관련 라우터
api_router.include_router(problems.router, prefix="/problems", tags=["문제"])

# 대시보드 관련 라우터
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["학생 대시보드"])

# 새로 추가된 라우터들
api_router.include_router(professor.router, prefix="/professor", tags=["교수 대시보드"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI 서비스"])
api_router.include_router(security.router, prefix="/security", tags=["보안 서비스"]) 