"""Add round_number to diagnostic_sessions

Revision ID: add_round_number_001
Revises: 522ff2177b55
Create Date: 2025-06-16 04:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_round_number_001'
down_revision: Union[str, None] = '522ff2177b55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add round_number column to diagnostic_sessions table."""
    # Add round_number column with default value 1
    op.add_column('diagnostic_sessions', 
                  sa.Column('round_number', sa.Integer(), nullable=False, 
                           server_default='1', comment='진단테스트 회차 (1-10차)'))


def downgrade() -> None:
    """Remove round_number column from diagnostic_sessions table."""
    op.drop_column('diagnostic_sessions', 'round_number') 