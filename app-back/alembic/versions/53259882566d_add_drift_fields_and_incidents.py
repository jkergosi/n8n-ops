"""add_drift_fields_and_incidents

Revision ID: 53259882566d
Revises: 'ebd702d672dc'
Create Date: 2025-12-30 11:25:48

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '53259882566d'
down_revision = 'ebd702d672dc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('''
    CREATE EXTENSION IF NOT EXISTS pgcrypto; ALTER TABLE environments ADD COLUMN IF NOT EXISTS drift_status TEXT NOT NULL DEFAULT 'IN_SYNC'; ALTER TABLE environments ADD COLUMN IF NOT EXISTS last_drift_detected_at TIMESTAMPTZ NULL; ALTER TABLE environments ADD COLUMN IF NOT EXISTS active_drift_incident_id UUID NULL; CREATE TABLE IF NOT EXISTS drift_incidents ( id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID NOT NULL, environment_id UUID NOT NULL, status TEXT NOT NULL DEFAULT 'open', title TEXT NULL, summary JSONB NULL, created_by UUID NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), closed_at TIMESTAMPTZ NULL );
    ''')


def downgrade() -> None:
    pass

