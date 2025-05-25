"""add password column

Revision ID: add_password_column
Revises: add_admin_role
Create Date: 2024-03-19 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_password_column'
down_revision = 'add_admin_role'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('password', sa.String(length=255), nullable=False, server_default='changeme'))

def downgrade():
    op.drop_column('users', 'password') 