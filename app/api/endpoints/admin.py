"""
관리자 전용 API 엔드포인트
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
        
        # 오늘 활성 사용자 (오늘 로그인한 사용자)
        today = datetime.now().date()
        active_users_today = db.query(User).filter(
            func.date(User.last_login_at) == today
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
            detail="활동 내역 조회 중 오류가 발생했습니다."
        )

@router.get("/verifications", response_model=List[VerificationDetail])
async def get_pending_verifications(
    status_filter: Optional[str] = 'pending',
    admin_user: User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """인증 요청 목록 조회"""
    try:
        query = db.query(VerificationRequest).options(joinedload(VerificationRequest.user))
        
        if status_filter:
            query = query.filter(VerificationRequest.status == status_filter)
        
        verifications = query.order_by(desc(VerificationRequest.submitted_at)).all()
        
        result = []
        for verification in verifications:
            # 서류 목록 파싱
            documents = []
            if verification.documents:
                try:
                    documents = json.loads(verification.documents)
                    # documents가 리스트가 아닌 경우 빈 리스트로 설정
                    if not isinstance(documents, list):
                        documents = []
                except json.JSONDecodeError:
                    documents = []
            
            result.append(VerificationDetail(
                id=verification.id,
                user_id=verification.user_id,
                user_name=verification.user.name,
                email=verification.user.email,
                phone_number=verification.user.phone_number,
                school=verification.user.school,
                department=verification.user.department,
                verification_type=verification.verification_type,
                status=verification.status,
                documents=documents,
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
    """인증 승인/거부 처리"""
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
        
        # 인증 상태 업데이트
        if action_data.action == 'approve':
            verification.status = 'approved'
            # 사용자 역할 업데이트
            user = db.query(User).filter(User.id == verification.user_id).first()
            if user:
                user.role = verification.verification_type  # 'student' or 'professor'
        else:
            verification.status = 'rejected'
            verification.rejection_reason = action_data.reason
        
        verification.reviewed_at = datetime.now()
        verification.reviewed_by = admin_user.user_id
        
        db.commit()
        
        return {
            "message": f"인증이 {'승인' if action_data.action == 'approve' else '거부'}되었습니다.",
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

@router.get("/database/tables", response_model=List[DatabaseTable])
async def get_database_tables(
    admin_user: User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """데이터베이스 테이블 목록 조회"""
    try:
        tables_info = []
        
        # 주요 테이블들 조회
        tables = ['users', 'verification_requests']
        
        for table_name in tables:
            try:
                # 테이블 행 수 조회
                result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                row_count = result.scalar()
                
                # 컬럼 정보 조회
                if table_name == 'users':
                    columns = [
                        'id', 'user_id', 'name', 'email', 'role', 'school', 
                        'department', 'is_active', 'created_at', 'last_login_at'
                    ]
                elif table_name == 'verification_requests':
                    columns = [
                        'id', 'user_id', 'verification_type', 'status', 
                        'created_at', 'reviewed_at', 'reviewed_by'
                    ]
                else:
                    columns = []
                
                tables_info.append(DatabaseTable(
                    table_name=table_name,
                    row_count=row_count,
                    columns=columns
                ))
                
            except Exception as e:
                logger.warning(f"테이블 {table_name} 조회 실패: {e}")
        
        return tables_info
        
    except Exception as e:
        logger.error(f"데이터베이스 테이블 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="테이블 조회 중 오류가 발생했습니다."
        )

@router.get("/database/tables/{table_name}/data", response_model=TableData)
async def get_table_data(
    table_name: str,
    page: int = 1,
    limit: int = 50,
    admin_user: User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """테이블 데이터 조회"""
    try:
        # 보안을 위해 허용된 테이블만 조회
        allowed_tables = ['users', 'verification_requests']
        if table_name not in allowed_tables:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="허용되지 않은 테이블입니다."
            )
        
        offset = (page - 1) * limit
        
        # 전체 행 수 조회
        total_result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        total_count = total_result.scalar()
        
        # 데이터 조회
        if table_name == 'users':
            query = text("""
                SELECT id, user_id, name, email, role, school, department, 
                       is_active, created_at, last_login_at
                FROM users 
                ORDER BY created_at DESC 
                LIMIT :limit OFFSET :offset
            """)
            columns = ['id', 'user_id', 'name', 'email', 'role', 'school', 
                      'department', 'is_active', 'created_at', 'last_login_at']
        
        elif table_name == 'verification_requests':
            query = text("""
                SELECT vr.id, vr.user_id, u.name as user_name, vr.verification_type, 
                       vr.status, vr.created_at, vr.reviewed_at, vr.reviewed_by
                FROM verification_requests vr
                LEFT JOIN users u ON vr.user_id = u.id
                ORDER BY vr.created_at DESC 
                LIMIT :limit OFFSET :offset
            """)
            columns = ['id', 'user_id', 'user_name', 'verification_type', 
                      'status', 'created_at', 'reviewed_at', 'reviewed_by']
        
        result = db.execute(query, {"limit": limit, "offset": offset})
        rows = []
        
        for row in result:
            row_dict = {}
            for i, column in enumerate(columns):
                value = row[i]
                # datetime 객체를 문자열로 변환
                if isinstance(value, datetime):
                    row_dict[column] = value.isoformat()
                else:
                    row_dict[column] = value
            rows.append(row_dict)
        
        return TableData(
            columns=columns,
            rows=rows,
            total_count=total_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"테이블 데이터 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="데이터 조회 중 오류가 발생했습니다."
        )

@router.delete("/database/tables/{table_name}/rows/{row_id}")
async def delete_table_row(
    table_name: str,
    row_id: int,
    admin_user: User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """테이블 행 삭제"""
    try:
        # 보안을 위해 허용된 테이블만 삭제
        allowed_tables = ['users', 'verification_requests']
        if table_name not in allowed_tables:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="허용되지 않은 테이블입니다."
            )
        
        # 관리자 계정 삭제 방지
        if table_name == 'users':
            user = db.query(User).filter(User.id == row_id).first()
            if user and user.role == 'admin':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="관리자 계정은 삭제할 수 없습니다."
                )
        
        # 행 삭제
        if table_name == 'users':
            deleted = db.query(User).filter(User.id == row_id).delete()
        elif table_name == 'verification_requests':
            deleted = db.query(VerificationRequest).filter(VerificationRequest.id == row_id).delete()
        
        if deleted == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="삭제할 데이터를 찾을 수 없습니다."
            )
        
        db.commit()
        
        return {"message": "데이터가 성공적으로 삭제되었습니다.", "deleted_id": row_id}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"데이터 삭제 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="데이터 삭제 중 오류가 발생했습니다."
        ) 