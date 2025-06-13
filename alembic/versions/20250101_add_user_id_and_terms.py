"""Add user_id and terms agreement fields

Revision ID: 20250101_add_user_id_and_terms
Revises: 468e28241915
Create Date: 2025-01-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250101_add_user_id_and_terms'
down_revision = '468e28241915'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add user_id column
    op.add_column('users', sa.Column('user_id', sa.String(length=50), nullable=True))
    
    # Add terms agreement columns
    op.add_column('users', sa.Column('terms_agreed', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('privacy_agreed', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('privacy_optional_agreed', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('marketing_agreed', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('identity_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('age_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('verification_method', sa.String(length=20), nullable=True))
    
    # Fill user_id with student_id values for existing users
    op.execute("UPDATE users SET user_id = student_id WHERE user_id IS NULL")
    
    # Make user_id not nullable after filling data
    op.alter_column('users', 'user_id', nullable=False)
    
    # Create unique index on user_id
    op.create_index(op.f('ix_users_user_id'), 'users', ['user_id'], unique=True)
    
    # Make student_id nullable (since user_id is now the primary identifier)
    op.alter_column('users', 'student_id', nullable=True)


def downgrade() -> None:
    # Drop user_id column and index
    op.drop_index(op.f('ix_users_user_id'), table_name='users')
    op.drop_column('users', 'user_id')
    
    # Drop terms agreement columns
    op.drop_column('users', 'verification_method')
    op.drop_column('users', 'age_verified')
    op.drop_column('users', 'identity_verified')
    op.drop_column('users', 'marketing_agreed')
    op.drop_column('users', 'privacy_optional_agreed')
    op.drop_column('users', 'privacy_agreed')
    op.drop_column('users', 'terms_agreed')
    
    # Make student_id not nullable again
    op.alter_column('users', 'student_id', nullable=False) 