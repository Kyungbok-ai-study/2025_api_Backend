"""Merge multiple heads

Revision ID: 522ff2177b55
Revises: 010_dept_test_integration, migrate_users_to_optimized
Create Date: 2025-06-16 02:33:04.737240

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '522ff2177b55'
down_revision: Union[str, None] = ('010_dept_test_integration', 'migrate_users_to_optimized')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
