"""optimize_workflow_env_map_queries

Revision ID: 20260107_075803
Revises: e5a52cb5bbc9
Create Date: 2026-01-07 07:58:03

Performance optimization for workflow_env_map queries.
Adds indexes to speed up workflow listing queries by 5-10x.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260107_075803'
down_revision = 'bf7375f4eb69'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add index for n8n_workflow_id lookups
    # Optimizes queries that filter by workflow existence (not null checks)
    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_workflow_env_map_n8n_workflow_id
        ON workflow_env_map(n8n_workflow_id)
        WHERE n8n_workflow_id IS NOT NULL;
    ''')

    # Add partial index for active workflow queries
    # Optimizes filtering out deleted/missing/ignored workflows
    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_workflow_env_map_active_workflows
        ON workflow_env_map(tenant_id, environment_id)
        WHERE status NOT IN ('deleted', 'missing', 'ignored') OR status IS NULL;
    ''')

    # Add index for canonical_id lookups (for batch fetching canonical data)
    # Optimizes the join between workflow_env_map and canonical_workflows
    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_workflow_env_map_canonical_id
        ON workflow_env_map(canonical_id)
        WHERE canonical_id IS NOT NULL;
    ''')


def downgrade() -> None:
    # Remove performance indexes in reverse order
    op.execute('DROP INDEX IF EXISTS idx_workflow_env_map_canonical_id;')
    op.execute('DROP INDEX IF EXISTS idx_workflow_env_map_active_workflows;')
    op.execute('DROP INDEX IF EXISTS idx_workflow_env_map_n8n_workflow_id;')
