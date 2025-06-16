"""Add student diagnosis progress tracking tables

Revision ID: add_student_diagnosis_progress
Revises: dae1d8a124d1
Create Date: 2025-06-16 15:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_student_diagnosis_progress'
down_revision: Union[str, None] = 'dae1d8a124d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add student diagnosis progress tracking tables."""
    
    # 학생별 진단테스트 차수 진행 상황 테이블
    op.create_table('student_diagnosis_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('department', sa.String(length=100), nullable=False),
        sa.Column('current_round', sa.Integer(), nullable=False, default=0),
        sa.Column('max_available_round', sa.Integer(), nullable=False, default=1),
        sa.Column('completed_rounds', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default=list),
        sa.Column('round_details', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default=dict),
        sa.Column('total_tests_completed', sa.Integer(), nullable=False, default=0),
        sa.Column('average_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('total_study_time', sa.Integer(), nullable=False, default=0),
        sa.Column('learning_pattern', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('next_recommendation', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_test_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='student_diagnosis_progress_user_id_fkey'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'department', name='uq_student_department_progress')
    )
    
    # 인덱스 생성
    op.create_index('ix_student_diagnosis_progress_id', 'student_diagnosis_progress', ['id'])
    op.create_index('ix_student_diagnosis_progress_user_id', 'student_diagnosis_progress', ['user_id'])
    op.create_index('ix_student_diagnosis_progress_department', 'student_diagnosis_progress', ['department'])
    op.create_index('ix_student_diagnosis_progress_current_round', 'student_diagnosis_progress', ['current_round'])
    
    # 진단테스트 차수별 설정 테이블
    op.create_table('diagnosis_round_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('department', sa.String(length=100), nullable=False),
        sa.Column('round_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('focus_area', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('total_questions', sa.Integer(), nullable=False, default=30),
        sa.Column('time_limit_minutes', sa.Integer(), nullable=False, default=60),
        sa.Column('passing_score', sa.Float(), nullable=False, default=60.0),
        sa.Column('test_file_path', sa.String(length=300), nullable=False),
        sa.Column('prerequisite_rounds', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default=list),
        sa.Column('unlock_condition', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('department', 'round_number', name='uq_department_round')
    )
    
    # 인덱스 생성
    op.create_index('ix_diagnosis_round_config_id', 'diagnosis_round_config', ['id'])
    op.create_index('ix_diagnosis_round_config_department', 'diagnosis_round_config', ['department'])
    op.create_index('ix_diagnosis_round_config_round_number', 'diagnosis_round_config', ['round_number'])


def downgrade() -> None:
    """Remove student diagnosis progress tracking tables."""
    
    # 인덱스 삭제
    op.drop_index('ix_diagnosis_round_config_round_number', table_name='diagnosis_round_config')
    op.drop_index('ix_diagnosis_round_config_department', table_name='diagnosis_round_config')
    op.drop_index('ix_diagnosis_round_config_id', table_name='diagnosis_round_config')
    
    op.drop_index('ix_student_diagnosis_progress_current_round', table_name='student_diagnosis_progress')
    op.drop_index('ix_student_diagnosis_progress_department', table_name='student_diagnosis_progress')
    op.drop_index('ix_student_diagnosis_progress_user_id', table_name='student_diagnosis_progress')
    op.drop_index('ix_student_diagnosis_progress_id', table_name='student_diagnosis_progress')
    
    # 테이블 삭제
    op.drop_table('diagnosis_round_config')
    op.drop_table('student_diagnosis_progress') 