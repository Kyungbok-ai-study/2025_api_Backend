"""
관리자 전용 API 엔드포인트 (DeepSeek 제거 버전)
"""
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, and_, text
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import json
import logging
from pathlib import Path

from app.db.database import get_db
from app.models.user import User
from app.models.verification import VerificationRequest
from app.models.question import Question
from app.services.user_migration_service import UserMigrationService
from app.auth.dependencies import get_current_user
from app.core.config import get_settings
from pydantic import BaseModel, Field

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)

# Request/Response 스키마
class AdminOnly(BaseModel):
    """관리자 권한 확인용"""
    pass

class DashboardStats(BaseModel):
    """대시보드 통계"""
    total_users: int
    total_students: int
    total_professors: int
    total_admins: int
    pending_verifications: int
    active_users_today: int
    new_registrations_this_week: int
    new_registrations_this_month: int

class RecentActivity(BaseModel):
    """최근 활동"""
    id: int
    type: str
    user_name: str
    user_id: str
    action: str
    timestamp: datetime
    status: str
    details: Optional[str] = None

class VerificationDetail(BaseModel):
    """인증 요청 상세"""
    id: int
    user_id: int
    user_name: str
    email: str
    phone_number: Optional[str]
    school: str
    department: Optional[str]
    verification_type: str
    status: str
    documents: List[Dict[str, Any]]
    submitted_at: datetime
    reviewed_at: Optional[datetime]
    reviewed_by: Optional[str]
    rejection_reason: Optional[str]

class VerificationAction(BaseModel):
    """인증 승인/거부 액션"""
    verification_id: int
    action: str = Field(..., pattern="^(approve|reject)$")
    reason: Optional[str] = None

class DatabaseTable(BaseModel):
    """데이터베이스 테이블 정보"""
    table_name: str
    row_count: int
    columns: List[str]

class TableData(BaseModel):
    """테이블 데이터"""
    columns: List[str]
    rows: List[Dict[str, Any]]
    total_count: int

def verify_admin(current_user: User = Depends(get_current_user)):
    """관리자 권한 확인"""
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다."
        )
    return current_user

@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    admin_user: User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """대시보드 통계 조회"""
    try:
        # 전체 사용자 수
        total_users = db.query(User).count()
        
        # 역할별 사용자 수
        role_counts = db.query(User.role, func.count(User.id)).group_by(User.role).all()
        role_dict = dict(role_counts)
        
        total_students = role_dict.get('student', 0)
        total_professors = role_dict.get('professor', 0)
        total_admins = role_dict.get('admin', 0)
        
        # 인증 대기 건수
        pending_verifications = db.query(VerificationRequest).filter(
            VerificationRequest.status == 'pending'
        ).count()
        
        # 오늘 활성 사용자 (오늘 로그인한 사용자) - JSON 필드 조회 방식으로 수정
        today = datetime.now().date()
        active_users_today = db.query(User).filter(
            and_(
                User.account_status.isnot(None),
                func.date(func.cast(User.account_status['last_login_at'].astext, text('TIMESTAMP'))) == today
            )
        ).count()
        
        # 이번 주 신규 가입자
        week_ago = datetime.now() - timedelta(days=7)
        new_registrations_this_week = db.query(User).filter(
            User.created_at >= week_ago
        ).count()
        
        # 이번 달 신규 가입자
        month_ago = datetime.now() - timedelta(days=30)
        new_registrations_this_month = db.query(User).filter(
            User.created_at >= month_ago
        ).count()
        
        return DashboardStats(
            total_users=total_users,
            total_students=total_students,
            total_professors=total_professors,
            total_admins=total_admins,
            pending_verifications=pending_verifications,
            active_users_today=active_users_today,
            new_registrations_this_week=new_registrations_this_week,
            new_registrations_this_month=new_registrations_this_month
        )
        
    except Exception as e:
        logger.error(f"대시보드 통계 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="통계 조회 중 오류가 발생했습니다."
        )

@router.get("/dashboard/activities", response_model=List[RecentActivity])
async def get_recent_activities(
    limit: int = 10,
    admin_user: User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """최근 활동 조회"""
    try:
        activities = []
        
        # 최근 가입자
        recent_users = db.query(User).order_by(desc(User.created_at)).limit(limit//2).all()
        for user in recent_users:
            activities.append(RecentActivity(
                id=user.id,
                type='register',
                user_name=user.name,
                user_id=user.user_id,
                action='회원가입',
                timestamp=user.created_at,
                status='success'
            ))
        
        # 최근 인증 요청
        recent_verifications = db.query(VerificationRequest).options(
            joinedload(VerificationRequest.user)
        ).order_by(desc(VerificationRequest.submitted_at)).limit(limit//2).all()
        
        for verification in recent_verifications:
            activities.append(RecentActivity(
                id=verification.id,
                type='verification',
                user_name=verification.user.name,
                user_id=verification.user.user_id,
                action=f'{verification.verification_type} 인증 요청',
                timestamp=verification.submitted_at,
                status=verification.status
            ))
        
        # 시간순 정렬
        activities.sort(key=lambda x: x.timestamp, reverse=True)
        return activities[:limit]
        
    except Exception as e:
        logger.error(f"최근 활동 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="활동 조회 중 오류가 발생했습니다."
        )

@router.get("/verifications", response_model=List[VerificationDetail])
async def get_pending_verifications(
    status_filter: Optional[str] = 'pending',
    admin_user: User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """인증 요청 목록 조회"""
    try:
        query = db.query(VerificationRequest).options(
            joinedload(VerificationRequest.user)
        )
        
        if status_filter and status_filter != 'all':
            query = query.filter(VerificationRequest.status == status_filter)
        
        verifications = query.order_by(desc(VerificationRequest.submitted_at)).all()
        
        result = []
        for verification in verifications:
            result.append(VerificationDetail(
                id=verification.id,
                user_id=verification.user_id,
                user_name=verification.user.name,
                email=verification.user.email,
                phone_number=verification.user.profile_info.get('phone_number') if verification.user.profile_info else None,
                school=verification.school,
                department=verification.department,
                verification_type=verification.verification_type,
                status=verification.status,
                documents=verification.documents,
                submitted_at=verification.submitted_at,
                reviewed_at=verification.reviewed_at,
                reviewed_by=verification.reviewed_by,
                rejection_reason=verification.rejection_reason
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"인증 요청 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="인증 요청 조회 중 오류가 발생했습니다."
        )

@router.post("/verifications/action")
async def handle_verification_action(
    action_data: VerificationAction,
    admin_user: User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """인증 요청 승인/거부 처리"""
    try:
        verification = db.query(VerificationRequest).filter(
            VerificationRequest.id == action_data.verification_id
        ).first()
        
        if not verification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="인증 요청을 찾을 수 없습니다."
            )
        
        if verification.status != 'pending':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 처리된 인증 요청입니다."
            )
        
        # 승인/거부 처리
        if action_data.action == 'approve':
            verification.status = 'approved'
            
            # 사용자 인증 상태 업데이트
            user = verification.user
            if user:
                user.account_status = user.account_status or {}
                user.account_status['identity_verified'] = True
                
        elif action_data.action == 'reject':
            verification.status = 'rejected'
            verification.rejection_reason = action_data.reason
        
        verification.reviewed_at = datetime.utcnow()
        verification.reviewed_by = admin_user.name
        
        db.commit()
        
        return {
            "message": f"인증 요청이 {action_data.action}되었습니다.",
            "verification_id": verification.id,
            "status": verification.status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"인증 처리 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="인증 처리 중 오류가 발생했습니다."
        )

@router.post("/users/migrate")
async def migrate_users_to_optimized(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 데이터를 최적화된 구조로 마이그레이션"""
    try:
        migration_service = UserMigrationService(db)
        result = await migration_service.migrate_to_optimized_structure()
        
        return {
            "success": True,
            "message": "사용자 마이그레이션이 완료되었습니다.",
            "migrated_users": result.get("migrated_count", 0),
            "total_users": result.get("total_count", 0)
        }
        
    except Exception as e:
        logger.error(f"사용자 마이그레이션 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"마이그레이션 실패: {str(e)}"
        )

@router.get("/users/migration-status")
async def get_migration_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """마이그레이션 상태 확인"""
    try:
        migration_service = UserMigrationService(db)
        status_info = await migration_service.get_migration_status()
        
        return {
            "migration_needed": status_info.get("migration_needed", False),
            "current_structure": status_info.get("current_structure", "unknown"),
            "recommended_action": status_info.get("recommended_action", "none"),
            "statistics": status_info.get("statistics", {})
        }
        
    except Exception as e:
        logger.error(f"마이그레이션 상태 확인 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="상태 확인 중 오류가 발생했습니다."
        )

@router.post("/users/rollback-migration")
async def rollback_user_migration(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 마이그레이션 롤백"""
    try:
        migration_service = UserMigrationService(db)
        result = await migration_service.rollback_migration()
        
        return {
            "success": True,
            "message": "마이그레이션 롤백이 완료되었습니다.",
            "rollback_details": result
        }
        
    except Exception as e:
        logger.error(f"마이그레이션 롤백 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"롤백 실패: {str(e)}"
        ) 