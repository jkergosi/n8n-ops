"""add_drift_incident_lifecycle

Revision ID: add_drift_lifecycle
Revises: '53259882566d'
Create Date: 2025-12-30 14:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_drift_lifecycle'
down_revision = '53259882566d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add lifecycle timestamp fields to drift_incidents
    op.execute('''
    -- Rename 'status' values: 'open' -> 'detected', 'closed' -> 'closed'
    UPDATE drift_incidents SET status = 'detected' WHERE status = 'open';

    -- Add lifecycle timestamps
    ALTER TABLE drift_incidents
    ADD COLUMN IF NOT EXISTS detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS acknowledged_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS acknowledged_by UUID NULL,
    ADD COLUMN IF NOT EXISTS stabilized_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS stabilized_by UUID NULL,
    ADD COLUMN IF NOT EXISTS reconciled_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS reconciled_by UUID NULL,
    ADD COLUMN IF NOT EXISTS closed_by UUID NULL;

    -- Add ownership and metadata fields
    ALTER TABLE drift_incidents
    ADD COLUMN IF NOT EXISTS owner_user_id UUID NULL,
    ADD COLUMN IF NOT EXISTS reason TEXT NULL,
    ADD COLUMN IF NOT EXISTS ticket_ref TEXT NULL;

    -- Add Agency+ fields (TTL/SLA)
    ALTER TABLE drift_incidents
    ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS severity VARCHAR(20) NULL,
    ADD COLUMN IF NOT EXISTS expiration_warning_sent BOOLEAN DEFAULT false;

    -- Add drift snapshot data
    ALTER TABLE drift_incidents
    ADD COLUMN IF NOT EXISTS affected_workflows JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS drift_snapshot JSONB NULL;

    -- Add resolution tracking
    ALTER TABLE drift_incidents
    ADD COLUMN IF NOT EXISTS resolution_type VARCHAR(50) NULL,
    ADD COLUMN IF NOT EXISTS resolution_details JSONB NULL;

    -- Create indexes for better query performance
    CREATE INDEX IF NOT EXISTS idx_drift_incidents_tenant ON drift_incidents(tenant_id);
    CREATE INDEX IF NOT EXISTS idx_drift_incidents_environment ON drift_incidents(environment_id);
    CREATE INDEX IF NOT EXISTS idx_drift_incidents_status ON drift_incidents(status);
    CREATE INDEX IF NOT EXISTS idx_drift_incidents_detected_at ON drift_incidents(detected_at);
    ''')


def downgrade() -> None:
    op.execute('''
    ALTER TABLE drift_incidents
    DROP COLUMN IF EXISTS detected_at,
    DROP COLUMN IF EXISTS acknowledged_at,
    DROP COLUMN IF EXISTS acknowledged_by,
    DROP COLUMN IF EXISTS stabilized_at,
    DROP COLUMN IF EXISTS stabilized_by,
    DROP COLUMN IF EXISTS reconciled_at,
    DROP COLUMN IF EXISTS reconciled_by,
    DROP COLUMN IF EXISTS closed_by,
    DROP COLUMN IF EXISTS owner_user_id,
    DROP COLUMN IF EXISTS reason,
    DROP COLUMN IF EXISTS ticket_ref,
    DROP COLUMN IF EXISTS expires_at,
    DROP COLUMN IF EXISTS severity,
    DROP COLUMN IF EXISTS expiration_warning_sent,
    DROP COLUMN IF EXISTS affected_workflows,
    DROP COLUMN IF EXISTS drift_snapshot,
    DROP COLUMN IF EXISTS resolution_type,
    DROP COLUMN IF EXISTS resolution_details;

    DROP INDEX IF EXISTS idx_drift_incidents_tenant;
    DROP INDEX IF EXISTS idx_drift_incidents_environment;
    DROP INDEX IF EXISTS idx_drift_incidents_status;
    DROP INDEX IF EXISTS idx_drift_incidents_detected_at;
    ''')
