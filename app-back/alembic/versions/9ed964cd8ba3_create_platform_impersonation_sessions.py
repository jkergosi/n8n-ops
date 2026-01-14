"""create_platform_impersonation_sessions

Revision ID: 9ed964cd8ba3
Revises: '98c25037a560'
Create Date: 2026-01-02 20:36:18

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9ed964cd8ba3'
down_revision = '98c25037a560'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('''
    CREATE TABLE IF NOT EXISTS platform_impersonation_sessions (id UUID PRIMARY KEY, actor_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, impersonated_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, impersonated_tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL, created_at TIMESTAMPTZ DEFAULT now(), ended_at TIMESTAMPTZ); CREATE INDEX IF NOT EXISTS idx_platform_impersonation_sessions_actor_active ON platform_impersonation_sessions(actor_user_id) WHERE ended_at IS NULL;
    ''')


def downgrade() -> None:
    op.execute('''
    DROP INDEX IF EXISTS idx_platform_impersonation_sessions_actor_active;
    DROP TABLE IF EXISTS platform_impersonation_sessions;
    ''')

