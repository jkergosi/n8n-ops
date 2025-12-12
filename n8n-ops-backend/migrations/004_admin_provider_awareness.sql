-- Migration: Admin Provider Awareness (Phase 1)
-- Per req_super_provider.md - Make admin features provider-aware

-- ============================================================================
-- 1. Add provider column to audit_logs table
-- ============================================================================

-- Add provider column (nullable - NULL for platform-scoped actions)
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS provider TEXT;

-- Index for provider filtering
CREATE INDEX IF NOT EXISTS idx_audit_logs_provider ON audit_logs(provider);
CREATE INDEX IF NOT EXISTS idx_audit_logs_provider_timestamp ON audit_logs(provider, timestamp DESC);

-- Composite index for common admin queries
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_provider ON audit_logs(tenant_id, provider);

-- ============================================================================
-- 2. Usage aggregation indexes for provider-filtered queries
-- ============================================================================

-- Support efficient provider-filtered usage queries
-- Note: Some of these may already exist from 002_provider_indexes.sql
-- Using IF NOT EXISTS to avoid errors

CREATE INDEX IF NOT EXISTS idx_workflows_provider_tenant ON workflows(provider, tenant_id);
CREATE INDEX IF NOT EXISTS idx_executions_provider_tenant ON executions(provider, tenant_id);
CREATE INDEX IF NOT EXISTS idx_environments_provider_tenant ON environments(provider, tenant_id);

-- For global usage "top tenants" queries
CREATE INDEX IF NOT EXISTS idx_executions_provider_tenant_created ON executions(provider, tenant_id, created_at DESC);

-- For health check queries by provider
CREATE INDEX IF NOT EXISTS idx_health_checks_provider_env ON health_checks(provider, environment_id);

-- ============================================================================
-- 3. Backfill existing audit_logs with provider context
-- ============================================================================

-- For workflow-related actions, set provider to n8n
UPDATE audit_logs al
SET provider = 'n8n'
WHERE al.provider IS NULL
  AND al.resource_type IN ('workflow', 'execution', 'credential', 'environment',
                            'deployment', 'snapshot', 'pipeline', 'promotion', 'tag');

-- Platform-scoped actions remain NULL (tenant, user, plan, subscription, etc.)

-- ============================================================================
-- 4. Comments for documentation
-- ============================================================================

COMMENT ON COLUMN audit_logs.provider IS 'Provider type (n8n, make) for provider-scoped actions. NULL for platform-scoped actions like tenant/user management.';
