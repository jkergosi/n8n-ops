"""add_policy_flags_to_environments

Revision ID: 10bc9f88fc9c
Revises: '0d3cc810ee1a'
Create Date: 2025-12-31 08:43:12

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '10bc9f88fc9c'
down_revision = '0d3cc810ee1a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('''
    ALTER TABLE environments ADD COLUMN IF NOT EXISTS policy_flags JSONB NOT NULL DEFAULT '{}'::jsonb;
    ''')


def downgrade() -> None:
    op.execute('''
    ALTER TABLE environments DROP COLUMN IF EXISTS policy_flags;
    ''')

