-- Credential-safe promotion: logical credentials, mappings, dependencies

create table if not exists logical_credentials (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  name text not null,
  description text,
  required_type text,
  created_at timestamptz not null default now(),
  unique (tenant_id, name)
);

create index if not exists idx_logical_credentials_tenant_name
  on logical_credentials(tenant_id, name);

create table if not exists credential_mappings (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  logical_credential_id uuid not null references logical_credentials(id) on delete cascade,
  environment_id uuid not null,
  provider text not null default 'n8n',
  physical_credential_id text not null,
  physical_name text,
  physical_type text,
  status text default 'valid',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (environment_id, provider, logical_credential_id)
);

create index if not exists idx_credential_mappings_env_provider_logical
  on credential_mappings(environment_id, provider, logical_credential_id);

create index if not exists idx_credential_mappings_tenant
  on credential_mappings(tenant_id);

create table if not exists workflow_credential_dependencies (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  workflow_id text not null,
  provider text not null default 'n8n',
  logical_credential_ids jsonb not null default '[]'::jsonb,
  updated_at timestamptz not null default now(),
  unique (workflow_id, provider)
);

create index if not exists idx_workflow_cred_deps_workflow_provider
  on workflow_credential_dependencies(workflow_id, provider);

create index if not exists idx_workflow_cred_deps_tenant
  on workflow_credential_dependencies(tenant_id);

