"""add_snapshot_retention_to_plan_defaults

Revision ID: 20260116_add_snapshot_retention
Revises: 20260116_add_activity_retention
Create Date: 2026-01-16 15:00:00

Adds snapshot_retention_days column to plan_retention_defaults table
to support plan-based retention enforcement for workflow snapshots.

Safety: Latest snapshot per environment/workflow is ALWAYS preserved
regardless of retention period.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260116_add_snapshot_retention'
down_revision = '20260116_add_activity_retention'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add snapshot_retention_days column to plan_retention_defaults table.

    Plan-based defaults (longer than activity due to rollback requirements):
    - free: 14 days (basic snapshot history)
    - pro: 60 days (2 months for rollback safety)
    - agency: 180 days (6 months for client work)
    - enterprise: 365 days (full year for compliance/audit)

    Note: Latest snapshot per environment is ALWAYS preserved regardless
    of retention period for operational safety.
    """
    op.execute('''
        -- Add snapshot_retention_days column
        ALTER TABLE plan_retention_defaults
        ADD COLUMN IF NOT EXISTS snapshot_retention_days INTEGER DEFAULT 14;

        -- Update existing plans with appropriate retention values
        UPDATE plan_retention_defaults
        SET snapshot_retention_days = CASE plan_name
            WHEN 'free' THEN 14
            WHEN 'pro' THEN 60
            WHEN 'agency' THEN 180
            WHEN 'enterprise' THEN 365
            ELSE 14
        END,
        updated_at = NOW();
    ''')


def downgrade() -> None:
    """Remove snapshot_retention_days column from plan_retention_defaults table."""
    op.execute('''
        ALTER TABLE plan_retention_defaults
        DROP COLUMN IF EXISTS snapshot_retention_days;
    ''')
