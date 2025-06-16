"""
Main API 라우터 설정
"""
from fastapi import APIRouter

from app.api.endpoints import auth, diagnosis, problems, dashboard, ai, schools, admin, adaptive_learning, auto_mapping, ai_analysis
from app.api import rag
# from app.api.endpoints import security  # aioredis 오류로 임시 비활성화

api_router = APIRouter()

# 인증 관련 라우터
api_router.include_router(auth.router, prefix="/auth", tags=["인증"])

# 진단 테스트 관련 라우터
api_router.include_router(diagnosis.router, prefix="/diagnosis", tags=["진단"])

# 문제 추천 및 AI 생성 관련 라우터
api_router.include_router(problems.router, prefix="/problems", tags=["문제"])

# 대시보드 관련 라우터
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["학생 대시보드"])

# 관리자 전용 라우터
api_router.include_router(admin.router, prefix="/admin", tags=["관리자"])

# 새로 추가된 라우터들
api_router.include_router(adaptive_learning.router, tags=["적응형 학습"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI 서비스"])
api_router.include_router(rag.router)
# api_router.include_router(security.router, prefix="/security", tags=["보안 서비스"])  # 임시 비활성화

# 학교 정보 관련 라우터
api_router.include_router(schools.router, prefix="", tags=["학교 정보"])

# 자동 매핑 관련 라우터
api_router.include_router(auto_mapping.router, tags=["자동 매핑"])

# AI 난이도 분석 관련 라우터
api_router.include_router(ai_analysis.router, prefix="/ai-analysis", tags=["AI 난이도 분석"])

# 앙상블 AI 시스템 라우터 (삭제됨 - 중복 기능) 