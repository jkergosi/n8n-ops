"""add_activity_retention_index

Revision ID: 20260116_activity_retention_idx
Revises: 20260116_add_activity_retention
Create Date: 2026-01-16 15:00:00

Adds composite index on background_jobs table to optimize the activity
retention enforcement deletion query which filters by:
- tenant_id
- status IN ('completed', 'failed', 'cancelled')
- completed_at < cutoff

The index covers all three columns in the optimal order for this query pattern.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '20260116_activity_retention_idx'
down_revision = '20260116_add_activity_retention'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add composite index for activity retention deletion query.

    Query pattern:
        DELETE FROM background_jobs
        WHERE tenant_id = ?
          AND status IN ('completed', 'failed', 'cancelled')
          AND completed_at < ?

    Index order: (tenant_id, status, completed_at)
    - tenant_id first: equality filter, highest selectivity
    - status second: IN filter on terminal statuses
    - completed_at third: range filter for cutoff
    """
    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_background_jobs_retention
        ON background_jobs (tenant_id, status, completed_at)
        WHERE status IN ('completed', 'failed', 'cancelled');
    ''')

    # Add comment for documentation
    op.execute('''
        COMMENT ON INDEX idx_background_jobs_retention IS
        'Partial index for activity retention enforcement deletion query';
    ''')


def downgrade() -> None:
    """Remove the activity retention index."""
    op.execute('DROP INDEX IF EXISTS idx_background_jobs_retention;')
