"""materialized_view_refresh_tracking

Revision ID: 20260108_mv_tracking
Revises: 20260108_alert_rules
Create Date: 2026-01-08

Adds tracking for materialized view refresh reliability.
Records refresh timestamps, status, and provides functions to detect stale refreshes.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260108_mv_tracking'
down_revision = '20260108_alert_rules'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create table to track materialized view refresh history
    op.execute("""
        CREATE TABLE IF NOT EXISTS materialized_view_refresh_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            view_name TEXT NOT NULL,
            refresh_started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            refresh_completed_at TIMESTAMPTZ,
            status TEXT NOT NULL CHECK (status IN ('started', 'success', 'failed')),
            error_message TEXT,
            refresh_duration_ms INTEGER,
            row_count BIGINT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)

    # Create indexes for efficient queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_mv_refresh_log_view_name
        ON materialized_view_refresh_log(view_name, refresh_started_at DESC);
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_mv_refresh_log_status
        ON materialized_view_refresh_log(status, refresh_started_at DESC);
    """)

    # Drop existing functions before recreating with new signatures
    op.execute("DROP FUNCTION IF EXISTS refresh_workflow_performance_summary();")
    op.execute("DROP FUNCTION IF EXISTS refresh_environment_health_summary();")
    op.execute("DROP FUNCTION IF EXISTS refresh_all_materialized_views();")

    # Update the individual refresh functions to log their activity
    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_workflow_performance_summary()
        RETURNS TABLE(
            success BOOLEAN,
            error_message TEXT,
            refresh_duration_ms INTEGER,
            row_count BIGINT
        ) AS $$
        DECLARE
            log_id UUID;
            start_time TIMESTAMPTZ;
            end_time TIMESTAMPTZ;
            duration_ms INTEGER;
            rows_affected BIGINT;
            error_msg TEXT;
        BEGIN
            -- Insert log entry with 'started' status
            INSERT INTO materialized_view_refresh_log (view_name, status)
            VALUES ('workflow_performance_summary', 'started')
            RETURNING id, refresh_started_at INTO log_id, start_time;

            BEGIN
                -- Attempt to refresh the materialized view
                REFRESH MATERIALIZED VIEW CONCURRENTLY workflow_performance_summary;

                -- Get row count
                SELECT COUNT(*) INTO rows_affected
                FROM workflow_performance_summary;

                end_time := clock_timestamp();
                duration_ms := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000;

                -- Update log entry with success
                UPDATE materialized_view_refresh_log
                SET
                    refresh_completed_at = end_time,
                    status = 'success',
                    refresh_duration_ms = duration_ms,
                    row_count = rows_affected
                WHERE id = log_id;

                -- Return success result
                success := TRUE;
                error_message := NULL;
                refresh_duration_ms := duration_ms;
                row_count := rows_affected;
                RETURN NEXT;

            EXCEPTION WHEN OTHERS THEN
                -- Capture error details
                error_msg := SQLERRM;
                end_time := clock_timestamp();
                duration_ms := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000;

                -- Update log entry with failure
                UPDATE materialized_view_refresh_log
                SET
                    refresh_completed_at = end_time,
                    status = 'failed',
                    error_message = error_msg,
                    refresh_duration_ms = duration_ms
                WHERE id = log_id;

                -- Return failure result
                success := FALSE;
                error_message := error_msg;
                refresh_duration_ms := duration_ms;
                row_count := NULL;
                RETURN NEXT;
            END;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_environment_health_summary()
        RETURNS TABLE(
            success BOOLEAN,
            error_message TEXT,
            refresh_duration_ms INTEGER,
            row_count BIGINT
        ) AS $$
        DECLARE
            log_id UUID;
            start_time TIMESTAMPTZ;
            end_time TIMESTAMPTZ;
            duration_ms INTEGER;
            rows_affected BIGINT;
            error_msg TEXT;
        BEGIN
            -- Insert log entry with 'started' status
            INSERT INTO materialized_view_refresh_log (view_name, status)
            VALUES ('environment_health_summary', 'started')
            RETURNING id, refresh_started_at INTO log_id, start_time;

            BEGIN
                -- Attempt to refresh the materialized view
                REFRESH MATERIALIZED VIEW CONCURRENTLY environment_health_summary;

                -- Get row count
                SELECT COUNT(*) INTO rows_affected
                FROM environment_health_summary;

                end_time := clock_timestamp();
                duration_ms := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000;

                -- Update log entry with success
                UPDATE materialized_view_refresh_log
                SET
                    refresh_completed_at = end_time,
                    status = 'success',
                    refresh_duration_ms = duration_ms,
                    row_count = rows_affected
                WHERE id = log_id;

                -- Return success result
                success := TRUE;
                error_message := NULL;
                refresh_duration_ms := duration_ms;
                row_count := rows_affected;
                RETURN NEXT;

            EXCEPTION WHEN OTHERS THEN
                -- Capture error details
                error_msg := SQLERRM;
                end_time := clock_timestamp();
                duration_ms := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000;

                -- Update log entry with failure
                UPDATE materialized_view_refresh_log
                SET
                    refresh_completed_at = end_time,
                    status = 'failed',
                    error_message = error_msg,
                    refresh_duration_ms = duration_ms
                WHERE id = log_id;

                -- Return failure result
                success := FALSE;
                error_message := error_msg;
                refresh_duration_ms := duration_ms;
                row_count := NULL;
                RETURN NEXT;
            END;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Update the master refresh function to use the new logging functions
    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
        RETURNS TABLE(
            view_name TEXT,
            success BOOLEAN,
            refresh_time INTERVAL,
            error_message TEXT
        ) AS $$
        DECLARE
            result RECORD;
        BEGIN
            -- Refresh workflow performance summary
            FOR result IN SELECT * FROM refresh_workflow_performance_summary()
            LOOP
                view_name := 'workflow_performance_summary';
                success := result.success;
                refresh_time := make_interval(secs => result.refresh_duration_ms / 1000.0);
                error_message := result.error_message;
                RETURN NEXT;
            END LOOP;

            -- Refresh environment health summary
            FOR result IN SELECT * FROM refresh_environment_health_summary()
            LOOP
                view_name := 'environment_health_summary';
                success := result.success;
                refresh_time := make_interval(secs => result.refresh_duration_ms / 1000.0);
                error_message := result.error_message;
                RETURN NEXT;
            END LOOP;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create function to get latest refresh status for all views
    op.execute("""
        CREATE OR REPLACE FUNCTION get_materialized_view_refresh_status()
        RETURNS TABLE(
            view_name TEXT,
            last_refresh_started_at TIMESTAMPTZ,
            last_refresh_completed_at TIMESTAMPTZ,
            last_status TEXT,
            last_error_message TEXT,
            last_refresh_duration_ms INTEGER,
            last_row_count BIGINT,
            minutes_since_last_refresh NUMERIC,
            is_stale BOOLEAN,
            consecutive_failures INTEGER
        ) AS $$
        BEGIN
            RETURN QUERY
            WITH latest_refreshes AS (
                SELECT DISTINCT ON (mvrl.view_name)
                    mvrl.view_name as lr_view_name,
                    mvrl.refresh_started_at,
                    mvrl.refresh_completed_at,
                    mvrl.status,
                    mvrl.error_message,
                    mvrl.refresh_duration_ms,
                    mvrl.row_count,
                    EXTRACT(EPOCH FROM (NOW() - mvrl.refresh_started_at)) / 60 as minutes_since,
                    -- Consider stale if no successful refresh in last 2 hours (120 minutes)
                    CASE
                        WHEN mvrl.status = 'success' AND
                             EXTRACT(EPOCH FROM (NOW() - mvrl.refresh_completed_at)) / 60 > 120
                        THEN TRUE
                        WHEN mvrl.status = 'failed'
                        THEN TRUE
                        ELSE FALSE
                    END as is_stale
                FROM materialized_view_refresh_log mvrl
                ORDER BY mvrl.view_name, mvrl.refresh_started_at DESC
            ),
            failure_counts AS (
                SELECT
                    mvrl.view_name as fc_view_name,
                    COUNT(*) as consecutive_failures
                FROM materialized_view_refresh_log mvrl
                INNER JOIN (
                    SELECT DISTINCT ON (mvrl2.view_name)
                        mvrl2.view_name,
                        mvrl2.refresh_started_at
                    FROM materialized_view_refresh_log mvrl2
                    ORDER BY mvrl2.view_name, mvrl2.refresh_started_at DESC
                ) latest ON mvrl.view_name = latest.view_name
                WHERE mvrl.refresh_started_at >= (
                    SELECT MIN(mvrl3.refresh_started_at)
                    FROM materialized_view_refresh_log mvrl3
                    WHERE mvrl3.view_name = mvrl.view_name
                      AND mvrl3.status = 'success'
                      AND mvrl3.refresh_started_at <= latest.refresh_started_at
                    ORDER BY mvrl3.refresh_started_at DESC
                    LIMIT 1
                )
                AND mvrl.status = 'failed'
                GROUP BY mvrl.view_name
            )
            SELECT
                lr.lr_view_name,
                lr.refresh_started_at,
                lr.refresh_completed_at,
                lr.status,
                lr.error_message,
                lr.refresh_duration_ms,
                lr.row_count,
                lr.minutes_since::NUMERIC(10,2),
                lr.is_stale,
                COALESCE(fc.consecutive_failures, 0)::INTEGER
            FROM latest_refreshes lr
            LEFT JOIN failure_counts fc ON lr.lr_view_name = fc.fc_view_name;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create function to clean up old refresh logs (keep last 1000 per view)
    op.execute("""
        CREATE OR REPLACE FUNCTION cleanup_old_refresh_logs()
        RETURNS INTEGER AS $$
        DECLARE
            deleted_count INTEGER;
        BEGIN
            WITH logs_to_keep AS (
                SELECT id
                FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (PARTITION BY view_name ORDER BY refresh_started_at DESC) as rn
                    FROM materialized_view_refresh_log
                ) ranked
                WHERE rn <= 1000
            )
            DELETE FROM materialized_view_refresh_log
            WHERE id NOT IN (SELECT id FROM logs_to_keep);

            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            RETURN deleted_count;
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS cleanup_old_refresh_logs();")
    op.execute("DROP FUNCTION IF EXISTS get_materialized_view_refresh_status();")

    # Drop the tracking-enabled functions before restoring originals
    op.execute("DROP FUNCTION IF EXISTS refresh_all_materialized_views();")
    op.execute("DROP FUNCTION IF EXISTS refresh_workflow_performance_summary();")
    op.execute("DROP FUNCTION IF EXISTS refresh_environment_health_summary();")

    # Restore original refresh functions (from the original migration)
    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_workflow_performance_summary()
        RETURNS VOID AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY workflow_performance_summary;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_environment_health_summary()
        RETURNS VOID AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY environment_health_summary;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
        RETURNS TABLE(view_name TEXT, refresh_time INTERVAL) AS $$
        DECLARE
            start_time TIMESTAMPTZ;
            end_time TIMESTAMPTZ;
        BEGIN
            -- Refresh workflow performance summary
            start_time := clock_timestamp();
            PERFORM refresh_workflow_performance_summary();
            end_time := clock_timestamp();
            view_name := 'workflow_performance_summary';
            refresh_time := end_time - start_time;
            RETURN NEXT;

            -- Refresh environment health summary
            start_time := clock_timestamp();
            PERFORM refresh_environment_health_summary();
            end_time := clock_timestamp();
            view_name := 'environment_health_summary';
            refresh_time := end_time - start_time;
            RETURN NEXT;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("DROP INDEX IF EXISTS idx_mv_refresh_log_status;")
    op.execute("DROP INDEX IF EXISTS idx_mv_refresh_log_view_name;")
    op.execute("DROP TABLE IF EXISTS materialized_view_refresh_log;")
