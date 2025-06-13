"""add admin role

Revision ID: 03bb1307e428
Revises: 
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '03bb1307e428'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create admin role
    op.execute(
        text("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'admin') THEN
                CREATE ROLE admin WITH LOGIN PASSWORD '1234';
                GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO admin;
                GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO admin;
            END IF;
        END
        $$;
        """)
    )

def downgrade() -> None:
    # Remove admin role
    op.execute(text("DROP ROLE IF EXISTS admin;")) 