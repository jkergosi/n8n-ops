"""add_alert_rules

Revision ID: 20260108_alert_rules
Revises: 20260108_002
Create Date: 2026-01-08

Adds support for customizable alert rules with error rate thresholds,
error type matching, workflow failure detection, escalation policies,
and multiple notification channels.
"""
from alembic import op
import sqlalchemy as sa


revision = '20260108_alert_rules'
down_revision = '20260108_002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create alert_rules table for advanced threshold-based alerting
    op.execute("""
        CREATE TABLE IF NOT EXISTS alert_rules (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            description TEXT,

            -- Rule type determines how the rule evaluates conditions
            rule_type VARCHAR(50) NOT NULL CHECK (rule_type IN (
                'error_rate',       -- Alert when error rate exceeds threshold
                'error_type',       -- Alert when specific error types occur
                'workflow_failure', -- Alert when specific workflows fail
                'consecutive_failures', -- Alert after N consecutive failures
                'execution_duration'    -- Alert when execution exceeds time limit
            )),

            -- Threshold configuration (JSON) - varies by rule_type
            -- For error_rate: { "threshold_percent": 10, "time_window_minutes": 60 }
            -- For error_type: { "error_types": ["Credential Error", "Connection Error"] }
            -- For workflow_failure: { "workflow_ids": ["id1", "id2"], "canonical_ids": ["c1"] }
            -- For consecutive_failures: { "failure_count": 3, "workflow_ids": ["id1"] }
            -- For execution_duration: { "max_duration_ms": 60000 }
            threshold_config JSONB NOT NULL DEFAULT '{}',

            -- Optional environment scope (null = all environments)
            environment_id UUID REFERENCES environments(id) ON DELETE SET NULL,

            -- Channels to notify when rule triggers
            channel_ids UUID[] NOT NULL DEFAULT '{}',

            -- Escalation policy configuration (JSON)
            -- {
            --   "levels": [
            --     { "delay_minutes": 0, "channel_ids": ["id1"], "severity": "warning" },
            --     { "delay_minutes": 15, "channel_ids": ["id1", "id2"], "severity": "critical" },
            --     { "delay_minutes": 60, "channel_ids": ["id1", "id2", "id3"], "severity": "page" }
            --   ],
            --   "auto_resolve_after_minutes": 30,
            --   "repeat_interval_minutes": 60
            -- }
            escalation_config JSONB,

            -- Current escalation state
            current_escalation_level INTEGER DEFAULT 0,
            last_escalation_at TIMESTAMPTZ,

            -- Evaluation state
            is_enabled BOOLEAN NOT NULL DEFAULT true,
            is_firing BOOLEAN NOT NULL DEFAULT false,
            consecutive_violations INTEGER NOT NULL DEFAULT 0,
            first_violation_at TIMESTAMPTZ,
            last_violation_at TIMESTAMPTZ,
            last_evaluated_at TIMESTAMPTZ,
            last_notification_at TIMESTAMPTZ,

            -- Mute/silence settings
            muted_until TIMESTAMPTZ,
            mute_reason TEXT,

            -- Timestamps
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        -- Index for tenant queries
        CREATE INDEX IF NOT EXISTS idx_alert_rules_tenant
            ON alert_rules(tenant_id);

        -- Index for enabled rules (used during evaluation)
        CREATE INDEX IF NOT EXISTS idx_alert_rules_enabled
            ON alert_rules(is_enabled, tenant_id) WHERE is_enabled = true;

        -- Index for firing rules (used for dashboard/monitoring)
        CREATE INDEX IF NOT EXISTS idx_alert_rules_firing
            ON alert_rules(is_firing, tenant_id) WHERE is_firing = true;
    """)

    # Create alert_rule_history table for tracking rule evaluations and notifications
    op.execute("""
        CREATE TABLE IF NOT EXISTS alert_rule_history (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            alert_rule_id UUID NOT NULL REFERENCES alert_rules(id) ON DELETE CASCADE,

            -- Event type
            event_type VARCHAR(50) NOT NULL CHECK (event_type IN (
                'evaluation',      -- Rule was evaluated
                'triggered',       -- Rule triggered (violation detected)
                'resolved',        -- Alert was resolved
                'escalated',       -- Escalation level increased
                'notified',        -- Notification sent
                'muted',           -- Rule was muted
                'unmuted'          -- Rule was unmuted
            )),

            -- Evaluation result details
            evaluation_result JSONB,

            -- Escalation level at this event
            escalation_level INTEGER,

            -- Notification details (if applicable)
            channels_notified UUID[],
            notification_success BOOLEAN,

            -- Event timestamp
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        -- Index for history queries
        CREATE INDEX IF NOT EXISTS idx_alert_rule_history_rule
            ON alert_rule_history(alert_rule_id, created_at DESC);

        -- Index for tenant history
        CREATE INDEX IF NOT EXISTS idx_alert_rule_history_tenant
            ON alert_rule_history(tenant_id, created_at DESC);

        -- Retention: consider adding a cleanup policy for old history
        -- For now, keep last 90 days of history per rule
    """)

    # Add trigger for updated_at on alert_rules
    op.execute("""
        CREATE OR REPLACE FUNCTION update_alert_rules_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS alert_rules_updated_at ON alert_rules;
        CREATE TRIGGER alert_rules_updated_at
            BEFORE UPDATE ON alert_rules
            FOR EACH ROW
            EXECUTE FUNCTION update_alert_rules_updated_at();
    """)

    # Create function to evaluate error rate for a tenant/environment
    op.execute("""
        CREATE OR REPLACE FUNCTION evaluate_error_rate(
            p_tenant_id UUID,
            p_environment_id UUID DEFAULT NULL,
            p_time_window_minutes INTEGER DEFAULT 60
        )
        RETURNS TABLE(
            total_executions BIGINT,
            error_count BIGINT,
            error_rate NUMERIC
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT
                COUNT(*)::BIGINT as total_executions,
                COUNT(*) FILTER (WHERE e.status = 'error')::BIGINT as error_count,
                CASE
                    WHEN COUNT(*) > 0
                    THEN (COUNT(*) FILTER (WHERE e.status = 'error')::NUMERIC / COUNT(*)::NUMERIC * 100)
                    ELSE 0::NUMERIC
                END as error_rate
            FROM executions e
            WHERE e.tenant_id = p_tenant_id
              AND e.started_at >= NOW() - (p_time_window_minutes || ' minutes')::INTERVAL
              AND (p_environment_id IS NULL OR e.environment_id = p_environment_id);
        END;
        $$ LANGUAGE plpgsql STABLE;
    """)

    # Create function to count consecutive failures for a workflow
    op.execute("""
        CREATE OR REPLACE FUNCTION count_consecutive_failures(
            p_tenant_id UUID,
            p_workflow_id TEXT,
            p_environment_id UUID DEFAULT NULL
        )
        RETURNS INTEGER AS $$
        DECLARE
            consecutive_count INTEGER := 0;
            exec_status TEXT;
            exec_cursor CURSOR FOR
                SELECT e.status
                FROM executions e
                WHERE e.tenant_id = p_tenant_id
                  AND e.workflow_id = p_workflow_id
                  AND (p_environment_id IS NULL OR e.environment_id = p_environment_id)
                ORDER BY e.started_at DESC
                LIMIT 100;  -- Only check last 100 executions
        BEGIN
            OPEN exec_cursor;
            LOOP
                FETCH exec_cursor INTO exec_status;
                EXIT WHEN NOT FOUND;

                IF exec_status = 'error' THEN
                    consecutive_count := consecutive_count + 1;
                ELSE
                    EXIT;  -- Stop counting on first non-error
                END IF;
            END LOOP;
            CLOSE exec_cursor;

            RETURN consecutive_count;
        END;
        $$ LANGUAGE plpgsql STABLE;
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS count_consecutive_failures(UUID, TEXT, UUID);")
    op.execute("DROP FUNCTION IF EXISTS evaluate_error_rate(UUID, UUID, INTEGER);")
    op.execute("DROP TRIGGER IF EXISTS alert_rules_updated_at ON alert_rules;")
    op.execute("DROP FUNCTION IF EXISTS update_alert_rules_updated_at();")
    op.execute("DROP TABLE IF EXISTS alert_rule_history;")
    op.execute("DROP TABLE IF EXISTS alert_rules;")
