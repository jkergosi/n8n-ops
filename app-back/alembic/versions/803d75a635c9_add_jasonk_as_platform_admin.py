"""add_jasonk_as_platform_admin

Revision ID: 803d75a635c9
Revises: '9ed964cd8ba3'
Create Date: 2026-01-03 14:14:22

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '803d75a635c9'
down_revision = '9ed964cd8ba3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('''
    INSERT INTO platform_admins (user_id, granted_by, granted_at) VALUES ('f39b83c8-2c92-489d-8896-8d3f30e05e8e', NULL, NOW()) ON CONFLICT (user_id) DO NOTHING;
    ''')


def downgrade() -> None:
    pass

