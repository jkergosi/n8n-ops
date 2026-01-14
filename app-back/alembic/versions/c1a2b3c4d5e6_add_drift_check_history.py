"""add_drift_check_history

Revision ID: c1a2b3c4d5e6
Revises: 'bf7d3d3c6a89'
Create Date: 2025-12-31 12:00:00

Adds drift_check_history table for storing historical drift check results,
and adds retention_days_drift_checks to drift_policies.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c1a2b3c4d5e6'
down_revision = 'bf7d3d3c6a89'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create drift_check_history table
    op.execute('''
    CREATE TABLE IF NOT EXISTS drift_check_history (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id UUID NOT NULL,
        environment_id UUID NOT NULL,
        checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        drift_status TEXT NOT NULL,
        total_workflows INTEGER NOT NULL DEFAULT 0,
        drifted_workflows INTEGER NOT NULL DEFAULT 0,
        missing_in_git INTEGER NOT NULL DEFAULT 0,
        missing_in_runtime INTEGER NOT NULL DEFAULT 0,
        in_sync_workflows INTEGER NOT NULL DEFAULT 0,
        summary_json JSONB NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT fk_drift_check_history_environment
            FOREIGN KEY (environment_id) REFERENCES environments(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_drift_check_history_tenant
        ON drift_check_history(tenant_id);
    CREATE INDEX IF NOT EXISTS idx_drift_check_history_environment
        ON drift_check_history(environment_id);
    CREATE INDEX IF NOT EXISTS idx_drift_check_history_checked_at
        ON drift_check_history(checked_at);
    CREATE INDEX IF NOT EXISTS idx_drift_check_history_tenant_checked
        ON drift_check_history(tenant_id, checked_at DESC);
    ''')

    # Create drift_check_workflow_flags table for per-workflow status in each check
    op.execute('''
    CREATE TABLE IF NOT EXISTS drift_check_workflow_flags (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        check_id UUID NOT NULL,
        workflow_id UUID NOT NULL,
        n8n_workflow_id TEXT NULL,
        workflow_name TEXT NULL,
        drift_flag TEXT NOT NULL,
        change_summary TEXT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT fk_drift_check_workflow_flags_check
            FOREIGN KEY (check_id) REFERENCES drift_check_history(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_drift_check_workflow_flags_check
        ON drift_check_workflow_flags(check_id);
    ''')

    # Add retention_days_drift_checks to drift_policies
    op.execute('''
    ALTER TABLE drift_policies
        ADD COLUMN IF NOT EXISTS retention_days_drift_checks INTEGER DEFAULT 30;
    ''')


def downgrade() -> None:
    op.execute('''
    ALTER TABLE drift_policies DROP COLUMN IF EXISTS retention_days_drift_checks;
    DROP TABLE IF EXISTS drift_check_workflow_flags;
    DROP TABLE IF EXISTS drift_check_history;
    ''')
