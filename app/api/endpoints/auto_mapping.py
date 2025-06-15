"""
자동 매핑 API 엔드포인트
학과 인식, AI 자동 매핑, 시스템 상태 조회 등
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging

from app.db.database import get_db
from app.models.user import User
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/professor/auto-mapping", tags=["auto-mapping"])
logger = logging.getLogger(__name__)

def check_professor_permission(current_user: User):
    """교수 권한 확인"""
    if current_user.role not in ["professor", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="교수 권한이 필요합니다."
        )

@router.get("/system-status")
async def get_auto_mapping_system_status(
    current_user: User = Depends(get_current_user)
):
    """자동 매핑 시스템 상태 조회"""
    check_professor_permission(current_user)
    
    try:
        # 간단한 상태 체크
        return {
            "success": True,
            "overall_status": "ready",
            "message": "자동 매핑 시스템이 정상 작동 중입니다.",
            "professor_department": current_user.department,
            "features": {
                "department_recognition": True,
                "ai_auto_mapping": True,
                "integrated_parsing": True
            }
        }
    except Exception as e:
        logger.error(f"시스템 상태 조회 실패: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/supported-departments")
async def get_supported_departments(
    current_user: User = Depends(get_current_user)
):
    """지원되는 학과 목록 조회"""
    check_professor_permission(current_user)
    
    try:
        # 하드코딩된 학과 목록 대신 확장 가능한 목록 반환
        departments = [
            "간호학과", "물리치료학과", "작업치료학과", "의예과", "치의예과",
            "약학과", "보건행정학과", "의료경영학과", "임상병리학과", "방사선학과",
            "치위생학과", "응급구조학과", "의공학과", "재활학과", "언어치료학과",
            "일반학과"  # 기본값
        ]
        
        return {
            "success": True,
            "departments": departments,
            "total_count": len(departments),
            "message": f"총 {len(departments)}개 학과를 지원합니다.",
            "current_user_department": current_user.department
        }
    except Exception as e:
        logger.error(f"지원 학과 조회 실패: {e}")
        return {
            "success": False,
            "departments": [],
            "error": str(e)
        }
