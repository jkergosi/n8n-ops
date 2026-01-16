"""add_deployment_retention_to_plan_defaults

Revision ID: 20260116_add_deployment_retention
Revises: 20260116_add_snapshot_retention
Create Date: 2026-01-16 16:00:00

Adds deployment_retention_days column to plan_retention_defaults table
to support plan-based retention enforcement for deployment history.

Safety: Most recent deployment per environment is ALWAYS preserved
regardless of retention period.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260116_add_deployment_retention'
down_revision = '20260116_add_snapshot_retention'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add deployment_retention_days column to plan_retention_defaults table.

    Plan-based defaults:
    - free: 7 days (minimal deployment history)
    - pro: 30 days (standard operational history)
    - agency: 90 days (extended history for client work)
    - enterprise: 365 days (full year for compliance/audit)

    Note: Most recent deployment per environment is ALWAYS preserved
    regardless of retention period for operational safety.
    """
    op.execute('''
        -- Add deployment_retention_days column
        ALTER TABLE plan_retention_defaults
        ADD COLUMN IF NOT EXISTS deployment_retention_days INTEGER DEFAULT 7;

        -- Update existing plans with appropriate retention values
        UPDATE plan_retention_defaults
        SET deployment_retention_days = CASE plan_name
            WHEN 'free' THEN 7
            WHEN 'pro' THEN 30
            WHEN 'agency' THEN 90
            WHEN 'enterprise' THEN 365
            ELSE 7
        END,
        updated_at = NOW();
    ''')


def downgrade() -> None:
    """Remove deployment_retention_days column from plan_retention_defaults table."""
    op.execute('''
        ALTER TABLE plan_retention_defaults
        DROP COLUMN IF EXISTS deployment_retention_days;
    ''')
