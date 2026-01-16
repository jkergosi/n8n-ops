"""Add prod_hotfix_keep_behavior to drift_policies

Revision ID: 20260115_hotfix_policy
Revises: (auto-determined by Alembic)
Create Date: 2026-01-15

This migration adds the prod_hotfix_keep_behavior column to drift_policies table.
This column controls what happens when a user keeps a PROD hotfix:
- force_update_dev: Also push the hotfix to DEV runtime (default)
- no_dev_update: Only update approved state, don't touch DEV
"""
from alembic import op
import sqlalchemy as sa


revision = '20260115_hotfix_policy'
down_revision = '20260112_sync_unique'
branch_labels = None
depends_on = None


def upgrade():
    """Add prod_hotfix_keep_behavior column to drift_policies table."""
    # Add column with default value
    op.add_column(
        'drift_policies',
        sa.Column(
            'prod_hotfix_keep_behavior',
            sa.String(length=50),
            nullable=False,
            server_default='force_update_dev'
        )
    )


def downgrade():
    """Remove prod_hotfix_keep_behavior column from drift_policies table."""
    op.drop_column('drift_policies', 'prod_hotfix_keep_behavior')
