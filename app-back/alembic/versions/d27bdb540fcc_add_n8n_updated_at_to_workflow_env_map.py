"""add_n8n_updated_at_to_workflow_env_map

Revision ID: d27bdb540fcc
Revises: '20260107_075803'
Create Date: 2026-01-07 10:35:05

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd27bdb540fcc'
down_revision = '20260107_075803'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('''
    ALTER TABLE workflow_env_map ADD COLUMN IF NOT EXISTS n8n_updated_at TIMESTAMPTZ;
    ''')


def downgrade() -> None:
    pass

