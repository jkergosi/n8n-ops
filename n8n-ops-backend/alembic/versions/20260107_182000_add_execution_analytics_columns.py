"""add_execution_analytics_columns

Revision ID: 20260107_182000
Revises: 20260107_075803
Create Date: 2026-01-07 18:20:00

Adds derived columns and indexes for execution analytics dashboard.
Enables 100% DB-driven analytics queries without N+1 enrichment or live n8n calls.

IMPORTANT: normalized_status NULL Handling
==========================================
The normalized_status column is populated during execution ingestion (upsert_execution).
Executions that were ingested BEFORE this migration will have NULL normalized_status values.

Analytics queries that filter on normalized_status IN ('success', 'error') will NOT include
these older executions with NULL values. This is intentional to avoid hot-path status mapping.

Options for handling legacy data:
1. Accept that analytics only covers executions ingested after this migration
2. Run the optional backfill script: scripts/backfill_normalized_status.py (if provided)

The backfill would set normalized_status based on the status mapping:
  - 'failed' -> 'error'
  - 'success' -> 'success'
  - 'running' -> 'running'
  - 'waiting' -> 'waiting'
  - other values -> preserved as-is

Error Field Extraction Priority
===============================
When populating error_message and error_node columns during ingestion, the following
priority order is used to extract error details from n8n execution data:

1. data.resultData.error.message (or .description) - Top-level resultData error
2. data.executionData.resultData.error.message (or .description) - Nested execution data error
3. error_node: data.resultData.lastNodeExecuted - Node where error occurred

The error_message field is truncated to 500 characters and error_node to 100 characters
to avoid oversized database values. Truncation happens in code before DB write.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260107_182000'
down_revision = '20260107_075803'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add normalized_status column for canonical status mapping
    # Maps incoming status values to canonical values (success/error/running/waiting)
    # for analytics queries without destroying original status
    op.execute('''
        ALTER TABLE executions
        ADD COLUMN IF NOT EXISTS normalized_status TEXT;
    ''')

    # Add error_message column to avoid expensive JSON parsing in analytics queries
    # Stores extracted error message, truncated to 500 chars
    op.execute('''
        ALTER TABLE executions
        ADD COLUMN IF NOT EXISTS error_message TEXT;
    ''')

    # Add error_node column to identify where errors occurred
    # Stores node name where error happened, truncated to 100 chars
    op.execute('''
        ALTER TABLE executions
        ADD COLUMN IF NOT EXISTS error_node TEXT;
    ''')

    # Add composite index for tenant/environment/started_at queries
    # Optimizes analytics queries filtered by tenant, environment, and time window
    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_executions_tenant_env_started
        ON executions(tenant_id, environment_id, started_at DESC);
    ''')

    # Add composite index for tenant/environment/workflow/started_at queries
    # Optimizes per-workflow analytics and filtering
    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_executions_tenant_env_workflow_started
        ON executions(tenant_id, environment_id, workflow_id, started_at DESC);
    ''')

    # Add partial index for failed executions
    # Optimizes queries that fetch last failure details
    # Uses normalized_status='error' to match analytics query filters
    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_executions_tenant_env_failed_started
        ON executions(tenant_id, environment_id, started_at DESC)
        WHERE normalized_status = 'error';
    ''')

    # Add composite index for normalized_status filtering
    # Optimizes analytics queries that filter by tenant, environment, and status
    # This index helps when normalized_status becomes heavily selective (e.g., filtering for errors only)
    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_executions_tenant_env_status_started
        ON executions(tenant_id, environment_id, normalized_status, started_at DESC);
    ''')


def downgrade() -> None:
    # Remove indexes in reverse order
    op.execute('DROP INDEX IF EXISTS idx_executions_tenant_env_status_started;')
    op.execute('DROP INDEX IF EXISTS idx_executions_tenant_env_failed_started;')
    op.execute('DROP INDEX IF EXISTS idx_executions_tenant_env_workflow_started;')
    op.execute('DROP INDEX IF EXISTS idx_executions_tenant_env_started;')

    # Remove columns
    op.execute('ALTER TABLE executions DROP COLUMN IF EXISTS error_node;')
    op.execute('ALTER TABLE executions DROP COLUMN IF EXISTS error_message;')
    op.execute('ALTER TABLE executions DROP COLUMN IF EXISTS normalized_status;')
