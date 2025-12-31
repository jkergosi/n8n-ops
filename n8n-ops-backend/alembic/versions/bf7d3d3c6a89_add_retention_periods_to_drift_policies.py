"""add_retention_periods_to_drift_policies

Revision ID: bf7d3d3c6a89
Revises: '10bc9f88fc9c'
Create Date: 2025-12-31 09:44:51

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'bf7d3d3c6a89'
down_revision = '10bc9f88fc9c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('''
    ALTER TABLE drift_policies ADD COLUMN IF NOT EXISTS retention_days_closed_incidents INTEGER DEFAULT 365; ALTER TABLE drift_policies ADD COLUMN IF NOT EXISTS retention_days_reconciliation_artifacts INTEGER DEFAULT 180; ALTER TABLE drift_policies ADD COLUMN IF NOT EXISTS retention_days_approvals INTEGER DEFAULT 365; ALTER TABLE drift_policies ADD COLUMN IF NOT EXISTS retention_enabled BOOLEAN DEFAULT true;
    ''')


def downgrade() -> None:
    op.execute('''
    ALTER TABLE drift_policies DROP COLUMN IF EXISTS retention_enabled;
    ALTER TABLE drift_policies DROP COLUMN IF EXISTS retention_days_approvals;
    ALTER TABLE drift_policies DROP COLUMN IF EXISTS retention_days_reconciliation_artifacts;
    ALTER TABLE drift_policies DROP COLUMN IF EXISTS retention_days_closed_incidents;
    ''')

