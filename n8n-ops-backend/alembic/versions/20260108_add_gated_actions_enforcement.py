"""add_gated_actions_enforcement

Revision ID: 20260108_gated_actions
Revises: 20260108_audit_imp_idx
Create Date: 2026-01-08

Adds comprehensive audit trail support for gated actions approval workflow.

This migration enhances the approval system to:
1. Track complete approval lifecycle events with full audit trail
2. Support all gated actions: acknowledge, extend_ttl, and reconcile
3. Record action execution context and results
4. Enable governance compliance reporting
5. Provide persistent approval records for accountability

Changes:
- Creates approval_audit table for tracking all approval events
- Adds approval_id reference to drift_approvals for execution tracking
- Adds executed_at and execution_result fields to drift_approvals
- Adds metadata fields for storing action-specific context
- Creates indexes optimized for audit queries and reporting
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260108_gated_actions'
down_revision = '20260108_audit_imp_idx'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create approval_audit table for comprehensive event tracking
    op.execute("""
        CREATE TABLE IF NOT EXISTS approval_audit (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            approval_id UUID NOT NULL REFERENCES drift_approvals(id) ON DELETE CASCADE,
            incident_id UUID NOT NULL REFERENCES drift_incidents(id) ON DELETE CASCADE,

            -- Event type tracking
            event_type VARCHAR(50) NOT NULL CHECK (event_type IN (
                'requested',           -- Approval requested
                'approved',            -- Approval granted
                'rejected',            -- Approval rejected
                'cancelled',           -- Approval cancelled by requester
                'executed',            -- Action executed after approval
                'execution_failed',    -- Action execution failed
                'auto_approved',       -- Automatically approved (if policy allows)
                'expired'              -- Approval request expired
            )),

            -- Actor context
            actor_id UUID NOT NULL,           -- User who triggered this event
            actor_email TEXT,
            actor_name TEXT,

            -- Event details
            approval_type VARCHAR(20) NOT NULL,  -- 'acknowledge', 'extend_ttl', 'reconcile'
            previous_status VARCHAR(20),         -- Status before this event
            new_status VARCHAR(20),              -- Status after this event

            -- Action-specific metadata
            -- For acknowledge: { "reason": "...", "ticket_ref": "..." }
            -- For extend_ttl: { "extension_hours": 24, "new_expiry": "..." }
            -- For reconcile: { "reconciliation_type": "...", "affected_workflows": [...] }
            action_metadata JSONB DEFAULT '{}',

            -- Execution tracking (for 'executed' events)
            execution_result JSONB,              -- Result of action execution
            execution_error TEXT,                -- Error message if execution failed

            -- Audit context
            reason TEXT,                         -- Reason provided for decision/action
            ip_address TEXT,                     -- IP address of actor
            user_agent TEXT,                     -- User agent of actor

            -- Timestamp
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        -- Index for approval history queries
        CREATE INDEX IF NOT EXISTS idx_approval_audit_approval_id
            ON approval_audit(approval_id, created_at DESC);

        -- Index for incident approval history
        CREATE INDEX IF NOT EXISTS idx_approval_audit_incident_id
            ON approval_audit(incident_id, created_at DESC);

        -- Index for tenant audit queries
        CREATE INDEX IF NOT EXISTS idx_approval_audit_tenant
            ON approval_audit(tenant_id, created_at DESC);

        -- Index for event type filtering (e.g., find all executed actions)
        CREATE INDEX IF NOT EXISTS idx_approval_audit_event_type
            ON approval_audit(tenant_id, event_type, created_at DESC);

        -- Index for actor activity tracking
        CREATE INDEX IF NOT EXISTS idx_approval_audit_actor
            ON approval_audit(actor_id, created_at DESC);

        -- Composite index for approval type filtering
        CREATE INDEX IF NOT EXISTS idx_approval_audit_type_status
            ON approval_audit(tenant_id, approval_type, event_type);
    """)

    # Enhance drift_approvals table with execution tracking
    op.execute("""
        -- Add execution tracking fields
        ALTER TABLE drift_approvals
        ADD COLUMN IF NOT EXISTS executed_at TIMESTAMPTZ NULL,
        ADD COLUMN IF NOT EXISTS executed_by UUID NULL,
        ADD COLUMN IF NOT EXISTS execution_result JSONB NULL,
        ADD COLUMN IF NOT EXISTS execution_error TEXT NULL;

        -- Add action metadata for storing action-specific context
        ALTER TABLE drift_approvals
        ADD COLUMN IF NOT EXISTS action_metadata JSONB DEFAULT '{}';

        -- Add IP and user agent for audit trail
        ALTER TABLE drift_approvals
        ADD COLUMN IF NOT EXISTS requester_ip TEXT NULL,
        ADD COLUMN IF NOT EXISTS requester_user_agent TEXT NULL,
        ADD COLUMN IF NOT EXISTS approver_ip TEXT NULL,
        ADD COLUMN IF NOT EXISTS approver_user_agent TEXT NULL;

        -- Add expiration for approval requests
        ALTER TABLE drift_approvals
        ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ NULL;

        -- Create index for executed approvals
        CREATE INDEX IF NOT EXISTS idx_drift_approvals_executed
            ON drift_approvals(tenant_id, executed_at DESC)
            WHERE executed_at IS NOT NULL;

        -- Create index for pending approvals with expiration
        CREATE INDEX IF NOT EXISTS idx_drift_approvals_pending_expiry
            ON drift_approvals(status, expires_at)
            WHERE status = 'pending' AND expires_at IS NOT NULL;

        -- Create composite index for approval type and status filtering
        CREATE INDEX IF NOT EXISTS idx_drift_approvals_type_status
            ON drift_approvals(tenant_id, approval_type, status);
    """)

    # Add columns to drift_policies for gated action configuration
    op.execute("""
        -- Add approval requirements for each gated action type
        ALTER TABLE drift_policies
        ADD COLUMN IF NOT EXISTS require_approval_for_acknowledge BOOLEAN DEFAULT false,
        ADD COLUMN IF NOT EXISTS require_approval_for_extend_ttl BOOLEAN DEFAULT true,
        ADD COLUMN IF NOT EXISTS require_approval_for_reconcile BOOLEAN DEFAULT true;

        -- Add approval expiration settings
        ALTER TABLE drift_policies
        ADD COLUMN IF NOT EXISTS approval_expiry_hours INTEGER DEFAULT 72;

        -- Add auto-approval settings (for specific users or roles)
        ALTER TABLE drift_policies
        ADD COLUMN IF NOT EXISTS auto_approve_config JSONB DEFAULT '{}';

        -- COMMENT on the new columns for documentation
        COMMENT ON COLUMN drift_policies.require_approval_for_acknowledge IS 'Whether acknowledging drift requires approval';
        COMMENT ON COLUMN drift_policies.require_approval_for_extend_ttl IS 'Whether extending TTL requires approval';
        COMMENT ON COLUMN drift_policies.require_approval_for_reconcile IS 'Whether reconciling drift requires approval';
        COMMENT ON COLUMN drift_policies.approval_expiry_hours IS 'Hours before approval request expires (default: 72)';
        COMMENT ON COLUMN drift_policies.auto_approve_config IS 'Configuration for auto-approval rules (JSON)';
    """)

    # Update existing policy templates to include gated action settings
    op.execute("""
        -- Update Strict template with approval requirements
        UPDATE drift_policy_templates
        SET policy_config = policy_config || '{
            "require_approval_for_acknowledge": true,
            "require_approval_for_extend_ttl": true,
            "require_approval_for_reconcile": true,
            "approval_expiry_hours": 48
        }'::jsonb
        WHERE name = 'Strict' AND is_system = true;

        -- Update Standard template with selective approval requirements
        UPDATE drift_policy_templates
        SET policy_config = policy_config || '{
            "require_approval_for_acknowledge": false,
            "require_approval_for_extend_ttl": true,
            "require_approval_for_reconcile": true,
            "approval_expiry_hours": 72
        }'::jsonb
        WHERE name = 'Standard' AND is_system = true;

        -- Update Relaxed template with minimal approval requirements
        UPDATE drift_policy_templates
        SET policy_config = policy_config || '{
            "require_approval_for_acknowledge": false,
            "require_approval_for_extend_ttl": false,
            "require_approval_for_reconcile": false,
            "approval_expiry_hours": 168
        }'::jsonb
        WHERE name = 'Relaxed' AND is_system = true;
    """)

    # Add trigger for updated_at on approval_audit (for consistency)
    op.execute("""
        -- Note: approval_audit is append-only, but this is for any future updates
        CREATE OR REPLACE FUNCTION update_drift_approvals_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS drift_approvals_updated_at ON drift_approvals;
        CREATE TRIGGER drift_approvals_updated_at
            BEFORE UPDATE ON drift_approvals
            FOR EACH ROW
            EXECUTE FUNCTION update_drift_approvals_updated_at();
    """)

    # Add table comments for documentation
    op.execute("""
        COMMENT ON TABLE approval_audit IS 'Complete audit trail for all approval workflow events and action executions';
        COMMENT ON COLUMN approval_audit.event_type IS 'Type of event: requested, approved, rejected, cancelled, executed, execution_failed, auto_approved, expired';
        COMMENT ON COLUMN approval_audit.action_metadata IS 'Action-specific context (reason, ticket_ref, extension_hours, reconciliation details, etc.)';
        COMMENT ON COLUMN approval_audit.execution_result IS 'Result of action execution (for executed events)';
    """)


def downgrade() -> None:
    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS drift_approvals_updated_at ON drift_approvals;")
    op.execute("DROP FUNCTION IF EXISTS update_drift_approvals_updated_at();")

    # Remove columns from drift_policies
    op.execute("""
        ALTER TABLE drift_policies
        DROP COLUMN IF EXISTS require_approval_for_acknowledge,
        DROP COLUMN IF EXISTS require_approval_for_extend_ttl,
        DROP COLUMN IF EXISTS require_approval_for_reconcile,
        DROP COLUMN IF EXISTS approval_expiry_hours,
        DROP COLUMN IF EXISTS auto_approve_config;
    """)

    # Remove columns from drift_approvals
    op.execute("""
        DROP INDEX IF EXISTS idx_drift_approvals_type_status;
        DROP INDEX IF EXISTS idx_drift_approvals_pending_expiry;
        DROP INDEX IF EXISTS idx_drift_approvals_executed;

        ALTER TABLE drift_approvals
        DROP COLUMN IF EXISTS executed_at,
        DROP COLUMN IF EXISTS executed_by,
        DROP COLUMN IF EXISTS execution_result,
        DROP COLUMN IF EXISTS execution_error,
        DROP COLUMN IF EXISTS action_metadata,
        DROP COLUMN IF EXISTS requester_ip,
        DROP COLUMN IF EXISTS requester_user_agent,
        DROP COLUMN IF EXISTS approver_ip,
        DROP COLUMN IF EXISTS approver_user_agent,
        DROP COLUMN IF EXISTS expires_at;
    """)

    # Drop approval_audit table and indexes
    op.execute("""
        DROP INDEX IF EXISTS idx_approval_audit_type_status;
        DROP INDEX IF EXISTS idx_approval_audit_actor;
        DROP INDEX IF EXISTS idx_approval_audit_event_type;
        DROP INDEX IF EXISTS idx_approval_audit_tenant;
        DROP INDEX IF EXISTS idx_approval_audit_incident_id;
        DROP INDEX IF EXISTS idx_approval_audit_approval_id;
        DROP TABLE IF EXISTS approval_audit;
    """)
