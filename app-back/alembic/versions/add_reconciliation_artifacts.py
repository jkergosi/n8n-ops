"""add_reconciliation_artifacts

Revision ID: add_recon_artifacts
Revises: 'add_drift_lifecycle'
Create Date: 2025-12-30 15:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_recon_artifacts'
down_revision = 'add_drift_lifecycle'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('''
    CREATE TABLE IF NOT EXISTS drift_reconciliation_artifacts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id UUID NOT NULL,
        incident_id UUID NOT NULL REFERENCES drift_incidents(id) ON DELETE CASCADE,

        type VARCHAR(20) NOT NULL,  -- 'promote', 'revert', 'replace'
        status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'pending', 'in_progress', 'success', 'failed'

        started_at TIMESTAMPTZ NULL,
        started_by UUID NULL,
        finished_at TIMESTAMPTZ NULL,

        -- External references (hidden from UI, but tracked)
        external_refs JSONB DEFAULT '{}',
        -- { commit_sha, pr_url, deployment_run_id, etc. }

        -- Affected workflows for this reconciliation
        affected_workflows JSONB DEFAULT '[]',

        error_message TEXT NULL,

        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_reconciliation_artifacts_tenant ON drift_reconciliation_artifacts(tenant_id);
    CREATE INDEX IF NOT EXISTS idx_reconciliation_artifacts_incident ON drift_reconciliation_artifacts(incident_id);
    CREATE INDEX IF NOT EXISTS idx_reconciliation_artifacts_status ON drift_reconciliation_artifacts(status);
    ''')


def downgrade() -> None:
    op.execute('''
    DROP TABLE IF EXISTS drift_reconciliation_artifacts;
    ''')
