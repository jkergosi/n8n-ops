"""add_untracked_missing_status

Revision ID: 94a957608da9
Revises: '3e894b287688'
Create Date: 2026-01-06 17:25:00

Migration: 94a957608da9 - Add untracked and missing status to workflow_env_map
See: fix_sync_flow_untracked_handling plan
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '94a957608da9'
down_revision = '3e894b287688'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update CHECK constraint to include 'untracked' and 'missing'
    op.execute('ALTER TABLE workflow_env_map DROP CONSTRAINT IF EXISTS workflow_env_map_status_check;')
    op.execute("""
        ALTER TABLE workflow_env_map 
        ADD CONSTRAINT workflow_env_map_status_check 
        CHECK (status IN ('linked', 'ignored', 'deleted', 'untracked', 'missing'));
    """)


def downgrade() -> None:
    # Restore original CHECK constraint
    op.execute('ALTER TABLE workflow_env_map DROP CONSTRAINT IF EXISTS workflow_env_map_status_check;')
    op.execute("""
        ALTER TABLE workflow_env_map 
        ADD CONSTRAINT workflow_env_map_status_check 
        CHECK (status IN ('linked', 'ignored', 'deleted'));
    """)
