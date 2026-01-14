"""add_drift_handling_mode_to_environments

Revision ID: 76c6e9c7f4fe
Revises: '53259882566d'
Create Date: 2025-12-30 11:42:58

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '76c6e9c7f4fe'
down_revision = '53259882566d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('''
    ALTER TABLE environments ADD COLUMN IF NOT EXISTS drift_handling_mode TEXT NOT NULL DEFAULT 'warn_only';
    ''')


def downgrade() -> None:
    pass

