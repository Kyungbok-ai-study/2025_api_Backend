"""통합 진단 시스템 테이블 생성

Revision ID: 009_unified_diagnosis
Revises: 468e28241915
Create Date: 2024-12-27 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '009_unified_diagnosis'
down_revision = '468e28241915'
branch_labels = None
depends_on = None

def upgrade():
    """통합 진단 시스템 테이블 생성"""
    
    # 1. diagnosis_tests 테이블 생성
    op.create_table(
        'diagnosis_tests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('department', sa.String(length=100), nullable=False),
        sa.Column('subject_area', sa.String(length=100), nullable=False),
        sa.Column('test_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('scoring_criteria', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('analysis_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('test_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('is_published', sa.Boolean(), nullable=False),
        sa.Column('publish_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expire_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 인덱스 생성
    op.create_index('ix_diagnosis_tests_id', 'diagnosis_tests', ['id'])
    op.create_index('ix_diagnosis_tests_department', 'diagnosis_tests', ['department'])
    op.create_index('ix_diagnosis_tests_subject_area', 'diagnosis_tests', ['subject_area'])
    op.create_index('ix_diagnosis_tests_status', 'diagnosis_tests', ['status'])
    op.create_index('ix_diagnosis_tests_created_at', 'diagnosis_tests', ['created_at'])

    # 2. diagnosis_questions 테이블 생성
    op.create_table(
        'diagnosis_questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('test_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.String(length=50), nullable=True),
        sa.Column('question_number', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('question_type', sa.String(length=50), nullable=True),
        sa.Column('options', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('correct_answer', sa.String(length=20), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('classification', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('question_properties', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ai_analysis', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('source_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['test_id'], ['diagnosis_tests.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('question_id')
    )
    
    # 인덱스 생성
    op.create_index('ix_diagnosis_questions_id', 'diagnosis_questions', ['id'])
    op.create_index('ix_diagnosis_questions_test_id', 'diagnosis_questions', ['test_id'])
    op.create_index('ix_diagnosis_questions_question_id', 'diagnosis_questions', ['question_id'])

    # 3. diagnosis_sessions 테이블 생성
    op.create_table(
        'diagnosis_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('test_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_token', sa.String(length=100), nullable=True),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_time_spent', sa.Integer(), nullable=True),
        sa.Column('raw_score', sa.Float(), nullable=True),
        sa.Column('percentage_score', sa.Float(), nullable=True),
        sa.Column('scaled_score', sa.Float(), nullable=True),
        sa.Column('response_stats', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('diagnosis_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('advanced_analysis', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('session_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['test_id'], ['diagnosis_tests.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_token')
    )
    
    # 인덱스 생성
    op.create_index('ix_diagnosis_sessions_id', 'diagnosis_sessions', ['id'])
    op.create_index('ix_diagnosis_sessions_test_id', 'diagnosis_sessions', ['test_id'])
    op.create_index('ix_diagnosis_sessions_user_id', 'diagnosis_sessions', ['user_id'])
    op.create_index('ix_diagnosis_sessions_session_token', 'diagnosis_sessions', ['session_token'])
    op.create_index('ix_diagnosis_sessions_status', 'diagnosis_sessions', ['status'])
    op.create_index('ix_diagnosis_sessions_created_at', 'diagnosis_sessions', ['created_at'])

    # 4. diagnosis_responses 테이블 생성
    op.create_table(
        'diagnosis_responses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('user_answer', sa.String(length=500), nullable=True),
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        sa.Column('points_earned', sa.Float(), nullable=True),
        sa.Column('response_time', sa.Float(), nullable=True),
        sa.Column('first_response_time', sa.Float(), nullable=True),
        sa.Column('total_view_time', sa.Float(), nullable=True),
        sa.Column('response_behavior', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('cognitive_analysis', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('response_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('answered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['diagnosis_questions.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['diagnosis_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 인덱스 생성
    op.create_index('ix_diagnosis_responses_id', 'diagnosis_responses', ['id'])
    op.create_index('ix_diagnosis_responses_session_id', 'diagnosis_responses', ['session_id'])
    op.create_index('ix_diagnosis_responses_question_id', 'diagnosis_responses', ['question_id'])

    # 5. student_diagnosis_history 테이블 수정 (기존 테이블이 있다면)
    op.create_table(
        'student_diagnosis_history_new',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('department', sa.String(length=100), nullable=False),
        sa.Column('subject_area', sa.String(length=100), nullable=False),
        sa.Column('learning_progression', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('predictions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('recommendations', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('performance_stats', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 인덱스 생성
    op.create_index('ix_student_diagnosis_history_new_id', 'student_diagnosis_history_new', ['id'])
    op.create_index('ix_student_diagnosis_history_new_user_id', 'student_diagnosis_history_new', ['user_id'])
    op.create_index('ix_student_diagnosis_history_new_department', 'student_diagnosis_history_new', ['department'])
    op.create_index('ix_student_diagnosis_history_new_subject_area', 'student_diagnosis_history_new', ['subject_area'])
    op.create_index('ix_student_diagnosis_history_new_last_updated', 'student_diagnosis_history_new', ['last_updated'])

def downgrade():
    """통합 진단 시스템 테이블 삭제"""
    
    # 테이블 삭제 (역순)
    op.drop_table('student_diagnosis_history_new')
    op.drop_table('diagnosis_responses')
    op.drop_table('diagnosis_sessions')  
    op.drop_table('diagnosis_questions')
    op.drop_table('diagnosis_tests') 