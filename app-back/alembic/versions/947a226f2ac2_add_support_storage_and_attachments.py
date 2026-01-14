"""add_support_storage_and_attachments

Revision ID: 947a226f2ac2
Revises: '7c76f55a6ef6'
Create Date: 2026-01-01 08:52:12

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '947a226f2ac2'
down_revision = '7c76f55a6ef6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('''
    -- Support storage settings (per-tenant)
    ALTER TABLE support_config
      ADD COLUMN IF NOT EXISTS storage_bucket text;
    
    ALTER TABLE support_config
      ADD COLUMN IF NOT EXISTS storage_prefix text;
    
    -- Support request tracking (admin support side)
    CREATE TABLE IF NOT EXISTS support_requests (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
      created_by_user_id uuid NULL,
      created_by_email text NULL,
      intent_kind text NOT NULL CHECK (intent_kind IN ('bug','feature','task')),
      jsm_request_key text NOT NULL,
      payload_json jsonb NULL,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now(),
      UNIQUE (tenant_id, jsm_request_key)
    );
    
    CREATE INDEX IF NOT EXISTS ix_support_requests_tenant_created_at
      ON support_requests(tenant_id, created_at DESC);
    
    -- Attachments stored in Supabase Storage (private)
    CREATE TABLE IF NOT EXISTS support_attachments (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
      support_request_id uuid NULL REFERENCES support_requests(id) ON DELETE SET NULL,
      uploader_user_id uuid NULL,
      uploader_email text NULL,
      filename text NOT NULL,
      content_type text NOT NULL,
      object_path text NOT NULL,
      size_bytes bigint NULL,
      created_at timestamptz NOT NULL DEFAULT now()
    );
    
    CREATE INDEX IF NOT EXISTS ix_support_attachments_tenant_created_at
      ON support_attachments(tenant_id, created_at DESC);
    
    CREATE INDEX IF NOT EXISTS ix_support_attachments_request_id
      ON support_attachments(support_request_id);
    ''')


def downgrade() -> None:
    pass

