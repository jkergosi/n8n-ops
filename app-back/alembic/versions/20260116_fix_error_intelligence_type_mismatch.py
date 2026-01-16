"""fix_error_intelligence_type_mismatch

Revision ID: 20260116_fix_types
Revises: 20260115_hotfix_policy
Create Date: 2026-01-16

Fixes type mismatch in get_error_intelligence function where workflow_id
is VARCHAR but we're returning TEXT[] causing 'structure of query does not
match function result type' error.
"""
from alembic import op
import sqlalchemy as sa

revision = '20260116_fix_types'
down_revision = '20260115_hotfix_policy'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fix the get_error_intelligence function to properly cast VARCHAR[] to TEXT[]
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
                    workflow_id::TEXT as workflow_id,  -- Cast to TEXT
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
                ARRAY_AGG(DISTINCT c.workflow_id)::TEXT[] as affected_workflow_ids,  -- Explicit cast
                (ARRAY_AGG(c.error_msg ORDER BY c.started_at DESC))[1] as sample_message
            FROM classified c
            GROUP BY c.error_type
            ORDER BY error_count DESC;
        END;
        $$ LANGUAGE plpgsql STABLE;
    """)


def downgrade() -> None:
    # Revert to previous version (from 20260108_002)
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
