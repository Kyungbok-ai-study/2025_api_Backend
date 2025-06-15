"""
사용자 데이터 마이그레이션 서비스
기존 users 테이블 구조에서 최적화된 구조로 데이터 이전
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import json

from app.db.database import get_db
from app.models.user import User

class UserMigrationService:
    """사용자 데이터 마이그레이션 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def migrate_existing_users(self) -> Dict[str, Any]:
        """기존 사용자 데이터를 최적화된 구조로 마이그레이션"""
        try:
            # 1. 마이그레이션할 사용자 수 확인
            count_query = text("SELECT COUNT(*) FROM users WHERE profile_info IS NULL")
            total_users = self.db.execute(count_query).scalar()
            
            if total_users == 0:
                return {
                    "status": "success",
                    "message": "모든 사용자가 이미 마이그레이션되었습니다.",
                    "migrated_count": 0,
                    "total_count": 0
                }
            
            # 2. 마이그레이션 실행
            migrated_count = 0
            users = self.db.query(User).filter(User.profile_info.is_(None)).all()
            
            for user in users:
                try:
                    # 프로필 정보 설정
                    user.set_profile_info(
                        student_id=getattr(user, 'student_id', None),
                        department=getattr(user, 'department', None),
                        admission_year=getattr(user, 'admission_year', None),
                        phone_number=getattr(user, 'phone_number', None),
                        profile_image=getattr(user, 'profile_image', None)
                    )
                    
                    # 계정 상태 설정
                    user.set_account_status(
                        is_active=getattr(user, 'is_active', True),
                        is_first_login=getattr(user, 'is_first_login', True),
                        last_login_at=getattr(user, 'last_login_at', None)
                    )
                    
                    # 약관 동의 정보 설정
                    user.set_agreements(
                        terms_agreed=getattr(user, 'terms_agreed', False),
                        privacy_agreed=getattr(user, 'privacy_agreed', False),
                        privacy_optional_agreed=getattr(user, 'privacy_optional_agreed', False),
                        marketing_agreed=getattr(user, 'marketing_agreed', False)
                    )
                    
                    # 인증 상태 설정
                    user.set_verification_status(
                        identity_verified=getattr(user, 'identity_verified', False),
                        age_verified=getattr(user, 'age_verified', False),
                        verification_method=getattr(user, 'verification_method', None)
                    )
                    
                    # 진단테스트 정보 설정
                    user.set_diagnostic_test_info(
                        completed=getattr(user, 'diagnostic_test_completed', False),
                        completed_at=getattr(user, 'diagnostic_test_completed_at', None)
                    )
                    
                    migrated_count += 1
                    
                except Exception as e:
                    print(f"사용자 ID {user.id} 마이그레이션 실패: {e}")
                    continue
            
            # 3. 변경사항 저장
            self.db.commit()
            
            return {
                "status": "success",
                "message": f"{migrated_count}명의 사용자가 성공적으로 마이그레이션되었습니다.",
                "migrated_count": migrated_count,
                "total_count": total_users,
                "success_rate": f"{(migrated_count/total_users)*100:.1f}%" if total_users > 0 else "0%"
            }
            
        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": f"마이그레이션 중 오류 발생: {str(e)}",
                "migrated_count": 0,
                "total_count": 0
            }
    
    def validate_migration(self) -> Dict[str, Any]:
        """마이그레이션 결과 검증"""
        try:
            # 전체 사용자 수
            total_users = self.db.query(User).count()
            
            # 마이그레이션된 사용자 수
            migrated_users = self.db.query(User).filter(
                User.profile_info.isnot(None)
            ).count()
            
            # JSONB 필드별 데이터 확인
            profile_info_count = self.db.query(User).filter(
                User.profile_info.isnot(None)
            ).count()
            
            account_status_count = self.db.query(User).filter(
                User.account_status.isnot(None)
            ).count()
            
            agreements_count = self.db.query(User).filter(
                User.agreements_verification.isnot(None)
            ).count()
            
            diagnosis_count = self.db.query(User).filter(
                User.diagnosis_info.isnot(None)
            ).count()
            
            return {
                "total_users": total_users,
                "migrated_users": migrated_users,
                "migration_rate": f"{(migrated_users/total_users)*100:.1f}%" if total_users > 0 else "0%",
                "jsonb_fields": {
                    "profile_info": profile_info_count,
                    "account_status": account_status_count,
                    "agreements_verification": agreements_count,
                    "diagnosis_info": diagnosis_count
                },
                "status": "완료" if migrated_users == total_users else "진행중"
            }
            
        except Exception as e:
            return {
                "error": f"검증 중 오류 발생: {str(e)}"
            }
    
    def rollback_migration(self) -> Dict[str, Any]:
        """마이그레이션 롤백 (긴급시 사용)"""
        try:
            # JSONB 필드를 NULL로 설정
            update_query = text("""
                UPDATE users SET 
                    profile_info = NULL,
                    account_status = NULL,
                    agreements_verification = NULL,
                    diagnosis_info = NULL
            """)
            
            result = self.db.execute(update_query)
            self.db.commit()
            
            return {
                "status": "success",
                "message": "마이그레이션이 성공적으로 롤백되었습니다.",
                "affected_rows": result.rowcount
            }
            
        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": f"롤백 중 오류 발생: {str(e)}"
            }

def get_migration_service(db: Session = next(get_db())) -> UserMigrationService:
    """마이그레이션 서비스 인스턴스 반환"""
    return UserMigrationService(db) 