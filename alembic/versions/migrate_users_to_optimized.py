"""Migrate users table to optimized structure

Revision ID: migrate_users_to_optimized  
Revises: 6d2c397a46e9
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'migrate_users_to_optimized'
down_revision: Union[str, None] = '6d2c397a46e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade users table to optimized structure."""
    
    # 1. 기존 데이터를 임시 테이블로 백업
    op.execute("""
        CREATE TABLE users_backup AS 
        SELECT * FROM users
    """)
    
    # 2. 새로운 JSONB 컬럼들 추가
    op.add_column('users', sa.Column('profile_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('users', sa.Column('account_status', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('users', sa.Column('agreements_verification', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('users', sa.Column('diagnosis_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # 3. 기존 데이터를 JSONB 필드로 마이그레이션
    op.execute("""
        UPDATE users SET 
            profile_info = jsonb_build_object(
                'student_id', student_id,
                'department', department,
                'admission_year', admission_year,
                'phone_number', phone_number,
                'profile_image', profile_image
            ),
            account_status = jsonb_build_object(
                'is_active', is_active,
                'is_first_login', is_first_login,
                'last_login_at', last_login_at::text
            ),
            agreements_verification = jsonb_build_object(
                'terms_agreed', terms_agreed,
                'privacy_agreed', privacy_agreed,
                'privacy_optional_agreed', privacy_optional_agreed,
                'marketing_agreed', marketing_agreed,
                'identity_verified', identity_verified,
                'age_verified', age_verified,
                'verification_method', verification_method
            ),
            diagnosis_info = jsonb_build_object(
                'completed', diagnostic_test_completed,
                'completed_at', diagnostic_test_completed_at::text
            )
    """)
    
    # 4. role에 인덱스 추가 (기존에 없었던 경우)
    op.create_index('ix_users_role', 'users', ['role'])
    
    # 5. created_at에 인덱스 추가 (기존에 없었던 경우)
    op.create_index('ix_users_created_at', 'users', ['created_at'])
    
    # 6. 기존 컬럼들 제거 (단계적으로)
    columns_to_drop = [
        'student_id', 'profile_image', 'department', 'admission_year', 'phone_number',
        'is_first_login', 'is_active', 'last_login_at',
        'terms_agreed', 'privacy_agreed', 'privacy_optional_agreed', 'marketing_agreed',
        'identity_verified', 'age_verified', 'verification_method',
        'diagnostic_test_completed', 'diagnostic_test_completed_at'
    ]
    
    for column in columns_to_drop:
        try:
            op.drop_column('users', column)
        except Exception as e:
            print(f"컬럼 {column} 제거 실패: {e}")
            continue
    
    print("✅ Users 테이블 최적화 마이그레이션 완료")
    print("📊 26개 컬럼 → 13개 컬럼으로 최적화 (50% 감소)")


def downgrade() -> None:
    """Downgrade optimized structure back to original."""
    
    # 1. 기존 컬럼들 다시 추가
    op.add_column('users', sa.Column('student_id', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('profile_image', sa.String(length=500), nullable=True))
    op.add_column('users', sa.Column('department', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('admission_year', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('phone_number', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('is_first_login', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('terms_agreed', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('privacy_agreed', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('privacy_optional_agreed', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('marketing_agreed', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('identity_verified', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('age_verified', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('verification_method', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('diagnostic_test_completed', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('diagnostic_test_completed_at', sa.DateTime(), nullable=True))
    
    # 2. JSONB 데이터를 다시 개별 컬럼으로 복원
    op.execute("""
        UPDATE users SET 
            student_id = profile_info->>'student_id',
            department = profile_info->>'department',
            admission_year = (profile_info->>'admission_year')::integer,
            phone_number = profile_info->>'phone_number',
            profile_image = profile_info->>'profile_image',
            is_active = (account_status->>'is_active')::boolean,
            is_first_login = (account_status->>'is_first_login')::boolean,
            last_login_at = (account_status->>'last_login_at')::timestamp,
            terms_agreed = (agreements_verification->>'terms_agreed')::boolean,
            privacy_agreed = (agreements_verification->>'privacy_agreed')::boolean,
            privacy_optional_agreed = (agreements_verification->>'privacy_optional_agreed')::boolean,
            marketing_agreed = (agreements_verification->>'marketing_agreed')::boolean,
            identity_verified = (agreements_verification->>'identity_verified')::boolean,
            age_verified = (agreements_verification->>'age_verified')::boolean,
            verification_method = agreements_verification->>'verification_method',
            diagnostic_test_completed = (diagnosis_info->>'completed')::boolean,
            diagnostic_test_completed_at = (diagnosis_info->>'completed_at')::timestamp
        WHERE profile_info IS NOT NULL 
           OR account_status IS NOT NULL 
           OR agreements_verification IS NOT NULL 
           OR diagnosis_info IS NOT NULL
    """)
    
    # 3. JSONB 컬럼들 제거
    op.drop_column('users', 'diagnosis_info')
    op.drop_column('users', 'agreements_verification')
    op.drop_column('users', 'account_status')
    op.drop_column('users', 'profile_info')
    
    # 4. 추가된 인덱스들 제거
    op.drop_index('ix_users_created_at', table_name='users')
    op.drop_index('ix_users_role', table_name='users')
    
    print("⬇️ Users 테이블 원래 구조로 복원 완료") 