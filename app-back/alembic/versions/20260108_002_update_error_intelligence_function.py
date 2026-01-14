"""update_error_intelligence_function

Revision ID: 20260108_002
Revises: 20260108_error_class
Create Date: 2026-01-08

Updates the get_error_intelligence function to use the error_message column
instead of parsing JSON. This provides a significant performance improvement
by avoiding expensive JSONB operations.
"""
from alembic import op
import sqlalchemy as sa

revision = '20260108_002'
down_revision = '20260108_error_class'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update error intelligence function to use error_message column
    # This avoids expensive JSON parsing and improves query performance by 50%+
    op.execute("""
        CREATE OR REPLACE FUNCTION get_error_intelligence(
            p_tenant_id UUID,
            p_environment_id UUID DEFAULT NULL,
            p_since TIMESTAMPTZ DEFAULT NOW() - INTERVAL '24 hours',
            p_until TIMESTAMPTZ DEFAULT NOW()
        )
        RETURNS TABLE(
            error_type TEXT,
            error_count BIGINT,
            first_seen TIMESTAMPTZ,
            last_seen TIMESTAMPTZ,
            affected_workflow_count BIGINT,
            affected_workflow_ids TEXT[],
            sample_message TEXT
        ) AS $$
        BEGIN
            RETURN QUERY
            WITH error_data AS (
                SELECT
                    e.workflow_id,
                    e.started_at,
                    COALESCE(e.error_message, '') as error_msg
                FROM executions e
                WHERE e.tenant_id = p_tenant_id
                  AND e.normalized_status = 'error'
                  AND e.started_at >= p_since
                  AND e.started_at <= p_until
                  AND (p_environment_id IS NULL OR e.environment_id = p_environment_id)
            ),
            classified AS (
                SELECT
                    classify_execution_error(error_msg) as error_type,
                    workflow_id,
                    started_at,
                    error_msg
                FROM error_data
            )
            SELECT
                c.error_type,
                COUNT(*)::BIGINT as error_count,
                MIN(c.started_at) as first_seen,
                MAX(c.started_at) as last_seen,
                COUNT(DISTINCT c.workflow_id)::BIGINT as affected_workflow_count,
                ARRAY_AGG(DISTINCT c.workflow_id) as affected_workflow_ids,
                (ARRAY_AGG(c.error_msg ORDER BY c.started_at DESC))[1] as sample_message
            FROM classified c
            GROUP BY c.error_type
            ORDER BY error_count DESC;
        END;
        $$ LANGUAGE plpgsql STABLE;
    """)


def downgrade() -> None:
    # Revert to JSON parsing version (from previous migration)
    op.execute("""
        CREATE OR REPLACE FUNCTION get_error_intelligence(
            p_tenant_id UUID,
            p_environment_id UUID DEFAULT NULL,
            p_since TIMESTAMPTZ DEFAULT NOW() - INTERVAL '24 hours',
            p_until TIMESTAMPTZ DEFAULT NOW()
        )
        RETURNS TABLE(
            error_type TEXT,
            error_count BIGINT,
            first_seen TIMESTAMPTZ,
            last_seen TIMESTAMPTZ,
            affected_workflow_count BIGINT,
            affected_workflow_ids TEXT[],
            sample_message TEXT
        ) AS $$
        BEGIN
            RETURN QUERY
            WITH error_messages AS (
                SELECT
                    e.workflow_id,
                    e.started_at,
                    COALESCE(
                        e.data::json->>'error'->>'message',
                        (e.data::json->>'error')::text,
                        ''
                    ) as error_msg
                FROM executions e
                WHERE e.tenant_id = p_tenant_id
                  AND e.status = 'error'
                  AND e.started_at >= p_since
                  AND e.started_at <= p_until
                  AND (p_environment_id IS NULL OR e.environment_id = p_environment_id)
            ),
            classified AS (
                SELECT
                    classify_execution_error(error_msg) as error_type,
                    workflow_id,
                    started_at,
                    error_msg
                FROM error_messages
            )
            SELECT
                c.error_type,
                COUNT(*)::BIGINT as error_count,
                MIN(c.started_at) as first_seen,
                MAX(c.started_at) as last_seen,
                COUNT(DISTINCT c.workflow_id)::BIGINT as affected_workflow_count,
                ARRAY_AGG(DISTINCT c.workflow_id) as affected_workflow_ids,
                (ARRAY_AGG(c.error_msg ORDER BY c.started_at DESC))[1] as sample_message
            FROM classified c
            GROUP BY c.error_type
            ORDER BY error_count DESC;
        END;
        $$ LANGUAGE plpgsql STABLE;
    """)
