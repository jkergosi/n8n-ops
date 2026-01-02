"""create_tenant_api_keys

Revision ID: 7c76f55a6ef6
Revises: 'c574200bc3db'
Create Date: 2025-12-31 23:16:06

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7c76f55a6ef6'
down_revision = 'c574200bc3db'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('''
    CREATE TABLE IF NOT EXISTS tenant_api_keys (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
      name text NOT NULL,
      key_prefix text NOT NULL,
      key_hash text NOT NULL,
      key_salt text NOT NULL,
      scopes jsonb NOT NULL DEFAULT '[]'::jsonb,
      created_at timestamptz NOT NULL DEFAULT now(),
      last_used_at timestamptz NULL,
      revoked_at timestamptz NULL,
      is_active boolean NOT NULL DEFAULT true,
      UNIQUE (tenant_id, key_prefix)
    );
    
    CREATE INDEX IF NOT EXISTS ix_tenant_api_keys_tenant_id ON tenant_api_keys(tenant_id);
    CREATE INDEX IF NOT EXISTS ix_tenant_api_keys_active ON tenant_api_keys(tenant_id) WHERE is_active = true;
    ''')


def downgrade() -> None:
    pass

