"""add_drift_policies_and_approvals

Revision ID: add_drift_policies
Revises: 'add_recon_artifacts'
Create Date: 2025-12-30 16:00:00

Phase 5 & 6: TTL/SLA Enforcement and Enterprise Policies
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_drift_policies'
down_revision = 'add_recon_artifacts'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('''
    -- Phase 5: Drift Policies for TTL/SLA enforcement
    CREATE TABLE IF NOT EXISTS drift_policies (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id UUID NOT NULL UNIQUE,

        -- TTL settings by severity (in hours)
        default_ttl_hours INTEGER DEFAULT 72,
        critical_ttl_hours INTEGER DEFAULT 24,
        high_ttl_hours INTEGER DEFAULT 48,
        medium_ttl_hours INTEGER DEFAULT 72,
        low_ttl_hours INTEGER DEFAULT 168,

        -- Auto-incident creation
        auto_create_incidents BOOLEAN DEFAULT false,
        auto_create_for_production_only BOOLEAN DEFAULT true,

        -- Enforcement settings
        block_deployments_on_expired BOOLEAN DEFAULT false,
        block_deployments_on_drift BOOLEAN DEFAULT false,

        -- Notification settings
        notify_on_detection BOOLEAN DEFAULT true,
        notify_on_expiration_warning BOOLEAN DEFAULT true,
        expiration_warning_hours INTEGER DEFAULT 24,

        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_drift_policies_tenant ON drift_policies(tenant_id);

    -- Phase 6: Drift Approvals for Enterprise governance
    CREATE TABLE IF NOT EXISTS drift_approvals (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id UUID NOT NULL,
        incident_id UUID NOT NULL REFERENCES drift_incidents(id) ON DELETE CASCADE,

        approval_type VARCHAR(20) NOT NULL,  -- 'acknowledge', 'extend_ttl', 'close', 'reconcile'
        status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'pending', 'approved', 'rejected', 'cancelled'

        requested_by UUID NOT NULL,
        requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        request_reason TEXT,

        decided_by UUID NULL,
        decided_at TIMESTAMPTZ NULL,
        decision_notes TEXT NULL,

        -- For TTL extensions
        extension_hours INTEGER NULL,

        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_drift_approvals_tenant ON drift_approvals(tenant_id);
    CREATE INDEX IF NOT EXISTS idx_drift_approvals_incident ON drift_approvals(incident_id);
    CREATE INDEX IF NOT EXISTS idx_drift_approvals_status ON drift_approvals(status);

    -- Phase 6: Policy Templates for org-wide defaults
    CREATE TABLE IF NOT EXISTS drift_policy_templates (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

        name VARCHAR(100) NOT NULL,
        description TEXT,

        -- Template configuration
        policy_config JSONB NOT NULL DEFAULT '{}',

        -- System templates are predefined
        is_system BOOLEAN DEFAULT false,
        is_default BOOLEAN DEFAULT false,

        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    -- Insert predefined templates
    INSERT INTO drift_policy_templates (name, description, is_system, policy_config) VALUES
    ('Strict', 'Tight controls for production environments', true, '{
        "default_ttl_hours": 24,
        "critical_ttl_hours": 4,
        "block_deployments_on_expired": true,
        "block_deployments_on_drift": true,
        "require_approval_for_acknowledge": true,
        "require_approval_for_close": true
    }'),
    ('Standard', 'Balanced controls for most teams', true, '{
        "default_ttl_hours": 72,
        "critical_ttl_hours": 24,
        "block_deployments_on_expired": true,
        "block_deployments_on_drift": false,
        "require_approval_for_acknowledge": false,
        "require_approval_for_close": false
    }'),
    ('Relaxed', 'Minimal controls for development', true, '{
        "default_ttl_hours": 168,
        "critical_ttl_hours": 72,
        "block_deployments_on_expired": false,
        "block_deployments_on_drift": false,
        "require_approval_for_acknowledge": false,
        "require_approval_for_close": false
    }')
    ON CONFLICT DO NOTHING;
    ''')


def downgrade() -> None:
    op.execute('''
    DROP TABLE IF EXISTS drift_policy_templates;
    DROP TABLE IF EXISTS drift_approvals;
    DROP TABLE IF EXISTS drift_policies;
    ''')
