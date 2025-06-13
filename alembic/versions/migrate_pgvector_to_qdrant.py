"""
pgvector에서 Qdrant로 마이그레이션

Revision ID: migrate_pgvector_to_qdrant
Revises: 6d2c397a46e9
Create Date: 2025-01-27 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'migrate_pgvector_to_qdrant'
down_revision = '6d2c397a46e9'
branch_labels = None
depends_on = None

def upgrade():
    """pgvector에서 Qdrant로 마이그레이션"""
    
    # questions 테이블에 qdrant_vector_id 컬럼 추가
    op.add_column('questions', sa.Column('qdrant_vector_id', sa.String(100), nullable=True))
    op.create_index('ix_questions_qdrant_vector_id', 'questions', ['qdrant_vector_id'])
    
    # questions_optimized 테이블에 qdrant_vector_id 컬럼 추가 (존재하는 경우)
    try:
        op.add_column('questions_optimized', sa.Column('qdrant_vector_id', sa.String(100), nullable=True))
        op.create_index('ix_questions_optimized_qdrant_vector_id', 'questions_optimized', ['qdrant_vector_id'])
    except:
        # 테이블이 없으면 무시
        pass
    
    # pgvector embedding 컬럼 제거 (존재하는 경우)
    try:
        op.drop_column('questions', 'embedding')
    except:
        # 컬럼이 없으면 무시
        pass
    
    try:
        op.drop_column('questions_optimized', 'embedding')
    except:
        # 컬럼이 없으면 무시
        pass

def downgrade():
    """Qdrant에서 pgvector로 롤백 (권장하지 않음)"""
    
    # qdrant_vector_id 컬럼 제거
    try:
        op.drop_index('ix_questions_qdrant_vector_id', 'questions')
        op.drop_column('questions', 'qdrant_vector_id')
    except:
        pass
    
    try:
        op.drop_index('ix_questions_optimized_qdrant_vector_id', 'questions_optimized')
        op.drop_column('questions_optimized', 'qdrant_vector_id')
    except:
        pass
    
    # pgvector embedding 컬럼 재추가 (권장하지 않음)
    # 주의: 이 작업은 데이터 손실을 야기할 수 있습니다
    print("경고: pgvector로의 롤백은 데이터 손실을 야기할 수 있습니다.")
    print("Qdrant에 저장된 벡터 데이터는 복구되지 않습니다.") 