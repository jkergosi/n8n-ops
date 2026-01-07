"""add_performance_indexes

Revision ID: bf7375f4eb69
Revises: df792f7d311c
Create Date: 2026-01-06 21:01:29.984383

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bf7375f4eb69'
down_revision = 'df792f7d311c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add composite index for workflow_env_map queries
    # Optimizes filtering by tenant, environment, and status
    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_workflow_env_map_composite
        ON workflow_env_map(tenant_id, environment_id, status);
    ''')

    # Add index for executions by workflow_id and created_at
    # Optimizes execution count aggregations and recent execution queries
    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_executions_workflow_created
        ON executions(workflow_id, created_at DESC);
    ''')

    # Add index for executions by environment_id and created_at
    # Optimizes environment health queries and sparkline generation
    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_executions_environment_created
        ON executions(environment_id, created_at DESC);
    ''')

    # Add index for executions by tenant_id, workflow_id, and status
    # Optimizes execution count queries filtered by status
    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_executions_tenant_workflow_status
        ON executions(tenant_id, workflow_id, status);
    ''')


def downgrade() -> None:
    # Remove performance indexes in reverse order
    op.execute('DROP INDEX IF EXISTS idx_executions_tenant_workflow_status;')
    op.execute('DROP INDEX IF EXISTS idx_executions_environment_created;')
    op.execute('DROP INDEX IF EXISTS idx_executions_workflow_created;')
    op.execute('DROP INDEX IF EXISTS idx_workflow_env_map_composite;')
