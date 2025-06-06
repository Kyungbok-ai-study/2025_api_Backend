"""Add description field to questions table

Revision ID: 20250109_add_description_to_questions
Revises: 20250101_add_user_id_and_terms
Create Date: 2025-01-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20250109_add_description_to_questions'
down_revision = '20250101_add_user_id_and_terms'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add description column to questions table
    # description is an array of strings to store problem descriptions/contexts
    op.add_column('questions', sa.Column('description', postgresql.ARRAY(sa.String()), nullable=True))
    
    # Optional: Update existing questions to have empty description array
    # op.execute("UPDATE questions SET description = '{}' WHERE description IS NULL")


def downgrade() -> None:
    # Drop description column
    op.drop_column('questions', 'description') 