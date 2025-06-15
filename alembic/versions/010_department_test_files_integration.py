"""Department test files integration

Revision ID: 010_department_test_files_integration
Revises: 009_unified_diagnosis_system
Create Date: 2025-06-15 13:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '010_department_test_files_integration'
down_revision = '009_unified_diagnosis_system'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply department test files integration changes"""
    
    # 1. diagnosis_tests 테이블에 파일 기반 플래그 추가
    op.add_column('diagnosis_tests', 
                  sa.Column('is_file_based', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('diagnosis_tests', 
                  sa.Column('source_file_path', sa.String(500), nullable=True))
    op.add_column('diagnosis_tests', 
                  sa.Column('file_version', sa.String(50), nullable=True))
    op.add_column('diagnosis_tests',
                  sa.Column('last_file_sync', sa.DateTime(timezone=True), nullable=True))

    # 2. 진단테스트 파일 동기화 상태 테이블 생성
    op.create_table('diagnosis_file_sync_status',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.String(100), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('last_modified', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_sync', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('file_hash', sa.String(64), nullable=True),
        sa.Column('question_count', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 인덱스 생성
    op.create_index('ix_diagnosis_file_sync_status_subject', 'diagnosis_file_sync_status', ['subject'])
    op.create_index('ix_diagnosis_file_sync_status_sync_status', 'diagnosis_file_sync_status', ['sync_status'])
    op.create_index('ix_diagnosis_file_sync_status_is_active', 'diagnosis_file_sync_status', ['is_active'])

    # 3. diagnosis_tests 테이블에 인덱스 추가
    op.create_index('ix_diagnosis_tests_is_file_based', 'diagnosis_tests', ['is_file_based'])
    op.create_index('ix_diagnosis_tests_source_file_path', 'diagnosis_tests', ['source_file_path'])

    # 4. 진단 질문 테이블에 파일 원본 정보 필드 추가 (이미 있으면 스킵)
    try:
        op.add_column('diagnosis_questions', 
                      sa.Column('original_question_id', sa.String(100), nullable=True))
    except Exception:
        pass  # 이미 존재하는 경우
    
    # 5. 기본 동기화 상태 데이터 삽입
    sync_data_insert = """
    INSERT INTO diagnosis_file_sync_status (subject, file_path, sync_status, is_active) VALUES
    ('컴퓨터공학', 'departments/computer_science/diagnostic_test_computer_science.json', 'pending', true),
    ('소프트웨어공학', 'departments/computer_science/diagnostic_test_computer_science.json', 'pending', true),
    ('인공지능', 'departments/computer_science/diagnostic_test_computer_science.json', 'pending', true),
    ('데이터사이언스', 'departments/computer_science/diagnostic_test_computer_science.json', 'pending', true),
    ('정보시스템', 'departments/computer_science/diagnostic_test_computer_science.json', 'pending', true),
    ('의학', 'departments/medical/diagnostic_test_medical.json', 'pending', true),
    ('간호학', 'departments/nursing/diagnostic_test_nursing.json', 'pending', true),
    ('물리치료학', 'departments/physical_therapy/diagnostic_test_physics_therapy.json', 'synced', true),
    ('경영학', 'departments/business/diagnostic_test_business.json', 'pending', true),
    ('법학', 'departments/law/diagnostic_test_law.json', 'pending', true),
    ('교육학', 'departments/education/diagnostic_test_education.json', 'pending', true)
    ON CONFLICT DO NOTHING;
    """
    
    op.execute(sync_data_insert)


def downgrade() -> None:
    """Revert department test files integration changes"""
    
    # 인덱스 제거
    op.drop_index('ix_diagnosis_tests_source_file_path', table_name='diagnosis_tests')
    op.drop_index('ix_diagnosis_tests_is_file_based', table_name='diagnosis_tests')
    
    # diagnosis_file_sync_status 테이블 제거
    op.drop_index('ix_diagnosis_file_sync_status_is_active', table_name='diagnosis_file_sync_status')
    op.drop_index('ix_diagnosis_file_sync_status_sync_status', table_name='diagnosis_file_sync_status')
    op.drop_index('ix_diagnosis_file_sync_status_subject', table_name='diagnosis_file_sync_status')
    op.drop_table('diagnosis_file_sync_status')
    
    # diagnosis_tests 테이블에서 컬럼 제거
    op.drop_column('diagnosis_tests', 'last_file_sync')
    op.drop_column('diagnosis_tests', 'file_version')
    op.drop_column('diagnosis_tests', 'source_file_path')
    op.drop_column('diagnosis_tests', 'is_file_based')
    
    # diagnosis_questions 테이블에서 컬럼 제거 (선택적)
    try:
        op.drop_column('diagnosis_questions', 'original_question_id')
    except Exception:
        pass 