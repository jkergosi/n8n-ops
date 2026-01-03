"""create_platform_admins_table

Revision ID: 98c25037a560
Revises: '86cc31c831b1'
Create Date: 2026-01-02 17:31:54

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '98c25037a560'
down_revision = '86cc31c831b1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('''
    CREATE TABLE IF NOT EXISTS platform_admins (user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE, granted_by UUID REFERENCES users(id), granted_at TIMESTAMPTZ DEFAULT now());
    ''')


def downgrade() -> None:
    op.execute('''
    DROP TABLE IF EXISTS platform_admins;
    ''')

