"""add_sparkline_aggregation_function

Revision ID: 20260108_sparkline_agg
Revises: d0ead040adb3
Create Date: 2026-01-08

Adds PostgreSQL function for SQL-side sparkline aggregation.
This enables efficient aggregation of execution data for sparkline charts
at scale (10k+ executions) by performing aggregation in the database
rather than fetching all records and aggregating client-side.

Safety features:
- Bucketizes executions by time interval
- Aggregates counts and durations per bucket
- Supports optional environment filtering
"""
from alembic import op
import sqlalchemy as sa

revision = '20260108_sparkline_agg'
down_revision = 'd0ead040adb3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create PostgreSQL function for sparkline bucket aggregation
    op.execute("""
        CREATE OR REPLACE FUNCTION get_sparkline_buckets(
            p_tenant_id UUID,
            p_since TIMESTAMPTZ,
            p_until TIMESTAMPTZ,
            p_interval_minutes INT,
            p_environment_id UUID DEFAULT NULL
        )
        RETURNS TABLE (
            bucket_start TIMESTAMPTZ,
            total_count BIGINT,
            success_count BIGINT,
            error_count BIGINT,
            avg_duration_ms DOUBLE PRECISION
        ) AS $$
        BEGIN
            RETURN QUERY
            WITH time_buckets AS (
                SELECT
                    date_trunc('minute', started_at)
                        - (EXTRACT(MINUTE FROM started_at)::INT % p_interval_minutes) * INTERVAL '1 minute'
                        AS bucket,
                    status,
                    COALESCE(duration_ms, execution_time) AS duration
                FROM executions
                WHERE tenant_id = p_tenant_id
                    AND started_at >= p_since
                    AND started_at < p_until
                    AND (p_environment_id IS NULL OR environment_id = p_environment_id)
            )
            SELECT
                bucket AS bucket_start,
                COUNT(*)::BIGINT AS total_count,
                COUNT(*) FILTER (WHERE status = 'success')::BIGINT AS success_count,
                COUNT(*) FILTER (WHERE status = 'error')::BIGINT AS error_count,
                AVG(duration)::DOUBLE PRECISION AS avg_duration_ms
            FROM time_buckets
            GROUP BY bucket
            ORDER BY bucket;
        END;
        $$ LANGUAGE plpgsql STABLE;
    """)

    # Add comment explaining the function
    op.execute("""
        COMMENT ON FUNCTION get_sparkline_buckets IS
        'Aggregates execution data into time buckets for sparkline charts.
        Performs SQL-side aggregation for better performance at scale (10k+ executions).
        Parameters:
        - p_tenant_id: Tenant UUID (required)
        - p_since: Start of time range (required)
        - p_until: End of time range (required)
        - p_interval_minutes: Bucket size in minutes (e.g., 5, 30, 60)
        - p_environment_id: Optional environment filter
        Returns buckets with total_count, success_count, error_count, avg_duration_ms';
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS get_sparkline_buckets(UUID, TIMESTAMPTZ, TIMESTAMPTZ, INT, UUID);")
