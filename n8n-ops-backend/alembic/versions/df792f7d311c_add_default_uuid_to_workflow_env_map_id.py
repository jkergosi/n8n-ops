"""add_default_uuid_to_workflow_env_map_id

Revision ID: df792f7d311c
Revises: e5a52cb5bbc9
Create Date: 2026-01-06 18:07:43.493701

Migration to add DEFAULT gen_random_uuid() to workflow_env_map.id column.
This fixes the NOT NULL constraint violation when inserting new rows.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'df792f7d311c'
down_revision = 'e5a52cb5bbc9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure UUID generator extension exists
    op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto;')

    # Add DEFAULT value to id column for auto-generation
    op.execute('ALTER TABLE workflow_env_map ALTER COLUMN id SET DEFAULT gen_random_uuid();')


def downgrade() -> None:
    # Remove DEFAULT value from id column
    op.execute('ALTER TABLE workflow_env_map ALTER COLUMN id DROP DEFAULT;')
