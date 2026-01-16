"""add_activity_retention_to_plan_defaults

Revision ID: 20260116_add_activity_retention
Revises: 20260116_fix_error_intelligence_type_mismatch
Create Date: 2026-01-16 14:00:00

Adds activity_retention_days column to plan_retention_defaults table
to support plan-based retention enforcement for Activity operational logs.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260116_add_activity_retention'
down_revision = '20260116_fix_types'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add activity_retention_days column to plan_retention_defaults table.

    Plan-based defaults:
    - free: 7 days (minimal retention for free tier)
    - pro: 30 days (standard retention for professional use)
    - agency: 90 days (extended retention for agencies)
    - enterprise: 365 days (full year retention for enterprise)
    """
    op.execute('''
        -- Add activity_retention_days column
        ALTER TABLE plan_retention_defaults
        ADD COLUMN IF NOT EXISTS activity_retention_days INTEGER DEFAULT 7;

        -- Update existing plans with appropriate retention values
        UPDATE plan_retention_defaults
        SET activity_retention_days = CASE plan_name
            WHEN 'free' THEN 7
            WHEN 'pro' THEN 30
            WHEN 'agency' THEN 90
            WHEN 'enterprise' THEN 365
            ELSE 7
        END,
        updated_at = NOW();
    ''')


def downgrade() -> None:
    """Remove activity_retention_days column from plan_retention_defaults table."""
    op.execute('''
        ALTER TABLE plan_retention_defaults
        DROP COLUMN IF EXISTS activity_retention_days;
    ''')
