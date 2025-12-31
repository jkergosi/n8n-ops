"""add_incident_payloads_and_soft_delete

Revision ID: d2e3f4a5b6c7
Revises: 'c1a2b3c4d5e6'
Create Date: 2025-12-31 12:01:00

Creates incident_payloads table to separate payload storage from incident metadata.
Adds soft-delete fields to drift_incidents.
Migrates existing payload data to the new table.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd2e3f4a5b6c7'
down_revision = 'c1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add soft-delete fields to drift_incidents
    op.execute('''
    ALTER TABLE drift_incidents
        ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
    ALTER TABLE drift_incidents
        ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ NULL;
    ALTER TABLE drift_incidents
        ADD COLUMN IF NOT EXISTS payload_purged_at TIMESTAMPTZ NULL;

    CREATE INDEX IF NOT EXISTS idx_drift_incidents_is_deleted
        ON drift_incidents(is_deleted);
    CREATE INDEX IF NOT EXISTS idx_drift_incidents_payload_purged
        ON drift_incidents(payload_purged_at) WHERE payload_purged_at IS NOT NULL;
    ''')

    # Create incident_payloads table
    op.execute('''
    CREATE TABLE IF NOT EXISTS incident_payloads (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        incident_id UUID NOT NULL UNIQUE,
        drift_snapshot JSONB NULL,
        affected_workflows JSONB NULL,
        summary JSONB NULL,
        resolution_details JSONB NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT fk_incident_payloads_incident
            FOREIGN KEY (incident_id) REFERENCES drift_incidents(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_incident_payloads_incident
        ON incident_payloads(incident_id);
    ''')

    # Migrate existing payload data from drift_incidents to incident_payloads
    op.execute('''
    INSERT INTO incident_payloads (incident_id, drift_snapshot, affected_workflows, summary, resolution_details, created_at, updated_at)
    SELECT
        id,
        drift_snapshot,
        affected_workflows,
        summary,
        resolution_details,
        created_at,
        updated_at
    FROM drift_incidents
    WHERE drift_snapshot IS NOT NULL
       OR affected_workflows IS NOT NULL
       OR summary IS NOT NULL
       OR resolution_details IS NOT NULL
    ON CONFLICT (incident_id) DO NOTHING;
    ''')

    # Note: We keep the original columns on drift_incidents for now to avoid breaking existing code
    # They will be deprecated and eventually removed in a future migration


def downgrade() -> None:
    # Copy data back to drift_incidents before dropping incident_payloads
    op.execute('''
    UPDATE drift_incidents di
    SET
        drift_snapshot = ip.drift_snapshot,
        affected_workflows = ip.affected_workflows,
        summary = ip.summary,
        resolution_details = ip.resolution_details
    FROM incident_payloads ip
    WHERE di.id = ip.incident_id;
    ''')

    op.execute('''
    DROP TABLE IF EXISTS incident_payloads;
    DROP INDEX IF EXISTS idx_drift_incidents_payload_purged;
    DROP INDEX IF EXISTS idx_drift_incidents_is_deleted;
    ALTER TABLE drift_incidents DROP COLUMN IF EXISTS payload_purged_at;
    ALTER TABLE drift_incidents DROP COLUMN IF EXISTS deleted_at;
    ALTER TABLE drift_incidents DROP COLUMN IF EXISTS is_deleted;
    ''')
