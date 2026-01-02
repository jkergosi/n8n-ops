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


