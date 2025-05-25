"""
API 라우터 설정
"""
from fastapi import APIRouter

from app.api.endpoints import auth

api_router = APIRouter()

# 인증 관련 라우터
api_router.include_router(auth.router, prefix="/auth", tags=["auth"]) 