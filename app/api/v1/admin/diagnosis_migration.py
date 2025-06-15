"""
통합 진단 시스템 마이그레이션 관리자 API

diagnostic_tests + test_sessions -> unified_diagnosis 시스템 통합 관리
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.db.database import get_db
from app.services.diagnosis_migration_service import (
    DiagnosisMigrationService,
    migrate_diagnosis_systems,
    rollback_migration,
    validate_migration
)
from app.models.unified_diagnosis import (
    DiagnosisTest,
    DiagnosisQuestion,
    DiagnosisSession,
    DiagnosisResponse,
    StudentDiagnosisHistory
)
from app.models.user import User
from app.api.deps import get_current_admin_user

router = APIRouter()

@router.post("/migrate/start")
async def start_diagnosis_migration(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    진단 시스템 통합 마이그레이션 시작
    
    **주요 기능:**
    - diagnostic_tests 시스템 마이그레이션
    - test_sessions 시스템 마이그레이션
    - 응답 시스템 통합 (diagnostic_responses + test_responses)
    - 학생 이력 통합
    - 전체 학과 지원 구조 적용
    """
    try:
        # 백그라운드에서 마이그레이션 실행
        background_tasks.add_task(
            _execute_migration_task,
            db_session=db,
            admin_user_id=current_user.id
        )
        
        return {
            "status": "migration_started",
            "message": "진단 시스템 통합 마이그레이션이 시작되었습니다.",
            "started_by": current_user.email,
            "started_at": datetime.now().isoformat(),
            "estimated_duration": "10-30분"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"마이그레이션 시작 실패: {str(e)}"
        )

@router.get("/migrate/status")
async def get_migration_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """마이그레이션 상태 확인"""
    try:
        # 마이그레이션 상태 확인
        migration_status = _check_migration_status(db)
        
        return {
            "status": "success",
            "migration_status": migration_status,
            "checked_at": datetime.now().isoformat(),
            "checked_by": current_user.email
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"상태 확인 실패: {str(e)}"
        )

@router.post("/migrate/validate")
async def validate_migration_result(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """마이그레이션 결과 검증"""
    try:
        validation_results = validate_migration(db)
        
        return {
            "status": "success",
            "validation_results": validation_results,
            "validated_at": datetime.now().isoformat(),
            "validated_by": current_user.email
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"검증 실패: {str(e)}"
        )

@router.post("/migrate/rollback")
async def rollback_diagnosis_migration(
    background_tasks: BackgroundTasks,
    confirm: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    진단 시스템 마이그레이션 롤백
    
    **⚠️ 주의:** 이 작업은 되돌릴 수 없습니다.
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="롤백을 수행하려면 confirm=true 파라미터가 필요합니다."
        )
    
    try:
        # 백그라운드에서 롤백 실행
        background_tasks.add_task(
            _execute_rollback_task,
            db_session=db,
            admin_user_id=current_user.id
        )
        
        return {
            "status": "rollback_started",
            "message": "진단 시스템 마이그레이션 롤백이 시작되었습니다.",
            "started_by": current_user.email,
            "started_at": datetime.now().isoformat(),
            "warning": "이 작업은 되돌릴 수 없습니다."
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"롤백 시작 실패: {str(e)}"
        )

@router.get("/unified-system/overview")
async def get_unified_system_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """통합 진단 시스템 현황 조회"""
    try:
        overview = {
            "system_status": "active",
            "statistics": {
                "total_tests": db.query(DiagnosisTest).count(),
                "total_questions": db.query(DiagnosisQuestion).count(),
                "total_sessions": db.query(DiagnosisSession).count(),
                "total_responses": db.query(DiagnosisResponse).count(),
                "total_histories": db.query(StudentDiagnosisHistory).count()
            },
            "department_distribution": _get_department_distribution(db),
            "subject_distribution": _get_subject_distribution(db),
            "recent_activity": _get_recent_activity(db),
            "system_health": _check_system_health(db)
        }
        
        return {
            "status": "success",
            "overview": overview,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"현황 조회 실패: {str(e)}"
        )

@router.get("/unified-system/departments/{department}/tests")
async def get_department_tests(
    department: str,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """학과별 진단테스트 목록 조회"""
    try:
        query = db.query(DiagnosisTest).filter(
            DiagnosisTest.department == department
        )
        
        if active_only:
            query = query.filter(DiagnosisTest.status == "active")
        
        tests = query.all()
        
        test_list = []
        for test in tests:
            test_list.append({
                "id": test.id,
                "title": test.title,
                "description": test.description,
                "subject_area": test.subject_area,
                "total_questions": test.total_questions,
                "status": test.status,
                "is_published": test.is_published,
                "created_at": test.created_at.isoformat(),
                "session_count": len(test.sessions) if test.sessions else 0
            })
        
        return {
            "status": "success",
            "department": department,
            "test_count": len(test_list),
            "tests": test_list,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"학과별 테스트 조회 실패: {str(e)}"
        )

@router.post("/unified-system/tests/{test_id}/activate")
async def activate_diagnosis_test(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """진단테스트 활성화"""
    try:
        test = db.query(DiagnosisTest).filter(DiagnosisTest.id == test_id).first()
        if not test:
            raise HTTPException(status_code=404, detail="테스트를 찾을 수 없습니다.")
        
        test.status = "active"
        test.is_published = True
        test.publish_date = datetime.now()
        test.updated_at = datetime.now()
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"테스트 '{test.title}'이 활성화되었습니다.",
            "test_id": test_id,
            "activated_by": current_user.email,
            "activated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"테스트 활성화 실패: {str(e)}"
        )

@router.get("/unified-system/analytics/performance")
async def get_performance_analytics(
    department: Optional[str] = None,
    subject_area: Optional[str] = None,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """성과 분석 데이터 조회"""
    try:
        # 성과 분석 로직 구현
        analytics = _generate_performance_analytics(
            db, department, subject_area, days
        )
        
        return {
            "status": "success",
            "analytics": analytics,
            "filters": {
                "department": department,
                "subject_area": subject_area,
                "days": days
            },
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"성과 분석 실패: {str(e)}"
        )

# 백그라운드 태스크 함수들
async def _execute_migration_task(db_session: Session, admin_user_id: int):
    """마이그레이션 실행 태스크"""
    try:
        result = migrate_diagnosis_systems(db_session)
        
        # 마이그레이션 결과 로깅
        _log_migration_result(result, admin_user_id, "migration")
        
    except Exception as e:
        # 에러 로깅
        _log_migration_error(str(e), admin_user_id, "migration")

async def _execute_rollback_task(db_session: Session, admin_user_id: int):
    """롤백 실행 태스크"""
    try:
        result = rollback_migration(db_session)
        
        # 롤백 결과 로깅
        _log_migration_result(result, admin_user_id, "rollback")
        
    except Exception as e:
        # 에러 로깅
        _log_migration_error(str(e), admin_user_id, "rollback")

# 유틸리티 함수들
def _check_migration_status(db: Session) -> Dict[str, Any]:
    """마이그레이션 상태 확인"""
    try:
        # 새로운 테이블 존재 확인
        unified_tables_exist = _check_unified_tables_exist(db)
        
        # 데이터 존재 확인
        data_counts = {
            "diagnosis_tests": db.query(DiagnosisTest).count() if unified_tables_exist else 0,
            "diagnosis_questions": db.query(DiagnosisQuestion).count() if unified_tables_exist else 0,
            "diagnosis_sessions": db.query(DiagnosisSession).count() if unified_tables_exist else 0,
            "diagnosis_responses": db.query(DiagnosisResponse).count() if unified_tables_exist else 0
        }
        
        # 마이그레이션 완료 여부 판단
        migration_completed = (
            unified_tables_exist and 
            sum(data_counts.values()) > 0
        )
        
        return {
            "migration_completed": migration_completed,
            "unified_tables_exist": unified_tables_exist,
            "data_counts": data_counts,
            "last_checked": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "migration_completed": False,
            "error": str(e),
            "last_checked": datetime.now().isoformat()
        }

def _check_unified_tables_exist(db: Session) -> bool:
    """통합 테이블 존재 확인"""
    try:
        # 간단한 쿼리로 테이블 존재 확인
        db.execute("SELECT 1 FROM diagnosis_tests LIMIT 1")
        return True
    except:
        return False

def _get_department_distribution(db: Session) -> Dict[str, int]:
    """학과별 분포"""
    try:
        from sqlalchemy import func
        
        result = db.query(
            DiagnosisTest.department,
            func.count(DiagnosisTest.id).label('count')
        ).group_by(DiagnosisTest.department).all()
        
        return {dept: count for dept, count in result}
    except:
        return {}

def _get_subject_distribution(db: Session) -> Dict[str, int]:
    """과목별 분포"""
    try:
        from sqlalchemy import func
        
        result = db.query(
            DiagnosisTest.subject_area,
            func.count(DiagnosisTest.id).label('count')
        ).group_by(DiagnosisTest.subject_area).all()
        
        return {subject: count for subject, count in result}
    except:
        return {}

def _get_recent_activity(db: Session) -> List[Dict[str, Any]]:
    """최근 활동"""
    try:
        recent_sessions = db.query(DiagnosisSession).order_by(
            DiagnosisSession.created_at.desc()
        ).limit(10).all()
        
        activities = []
        for session in recent_sessions:
            activities.append({
                "type": "session_created",
                "test_title": session.test.title if session.test else "Unknown",
                "department": session.test.department if session.test else "Unknown",
                "user_id": session.user_id,
                "created_at": session.created_at.isoformat()
            })
        
        return activities
    except:
        return []

def _check_system_health(db: Session) -> Dict[str, Any]:
    """시스템 상태 확인"""
    try:
        # 기본적인 상태 확인
        health_status = {
            "database_connection": True,
            "tables_accessible": True,
            "data_integrity": True,
            "last_health_check": datetime.now().isoformat()
        }
        
        # 간단한 데이터 무결성 검사
        orphaned_questions = db.query(DiagnosisQuestion).filter(
            ~DiagnosisQuestion.test_id.in_(
                db.query(DiagnosisTest.id)
            )
        ).count()
        
        if orphaned_questions > 0:
            health_status["data_integrity"] = False
            health_status["issues"] = [f"고아 문제 {orphaned_questions}개 발견"]
        
        return health_status
        
    except Exception as e:
        return {
            "database_connection": False,
            "error": str(e),
            "last_health_check": datetime.now().isoformat()
        }

def _generate_performance_analytics(
    db: Session, 
    department: Optional[str], 
    subject_area: Optional[str], 
    days: int
) -> Dict[str, Any]:
    """성과 분석 생성"""
    try:
        from sqlalchemy import func
        from datetime import timedelta
        
        # 기간 설정
        start_date = datetime.now() - timedelta(days=days)
        
        # 기본 쿼리
        query = db.query(DiagnosisSession).filter(
            DiagnosisSession.created_at >= start_date
        )
        
        # 필터 적용
        if department:
            query = query.join(DiagnosisTest).filter(
                DiagnosisTest.department == department
            )
        
        if subject_area:
            query = query.join(DiagnosisTest).filter(
                DiagnosisTest.subject_area == subject_area
            )
        
        sessions = query.all()
        
        # 분석 결과 생성
        analytics = {
            "total_sessions": len(sessions),
            "completed_sessions": len([s for s in sessions if s.status == "completed"]),
            "average_score": sum([s.percentage_score or 0 for s in sessions]) / len(sessions) if sessions else 0,
            "department_performance": {},
            "subject_performance": {},
            "time_distribution": {},
            "generated_for_period": f"{days} days"
        }
        
        return analytics
        
    except Exception as e:
        return {
            "error": str(e),
            "generated_at": datetime.now().isoformat()
        }

def _log_migration_result(result: Dict[str, Any], admin_user_id: int, operation: str):
    """마이그레이션 결과 로깅"""
    # 실제 구현에서는 로깅 시스템에 기록
    print(f"[{operation.upper()}] Admin {admin_user_id}: {result}")

def _log_migration_error(error: str, admin_user_id: int, operation: str):
    """마이그레이션 에러 로깅"""
    # 실제 구현에서는 에러 로깅 시스템에 기록
    print(f"[{operation.upper()} ERROR] Admin {admin_user_id}: {error}") 