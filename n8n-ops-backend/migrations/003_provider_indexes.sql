-- Migration: Provider Abstraction Indexes
-- Version: 003
-- Description: Add composite indexes for efficient provider-scoped queries
-- Run this migration AFTER 002_provider_abstraction.sql

-- =============================================================================
-- CORE INDEXES
-- =============================================================================

-- Environments: filter by provider and tenant
CREATE INDEX IF NOT EXISTS idx_environments_provider_tenant
  ON environments(provider, tenant_id);

-- Workflows: filter by provider and environment
CREATE INDEX IF NOT EXISTS idx_workflows_provider_env
  ON workflows(provider, environment_id);

-- Workflows: filter by provider and tenant
CREATE INDEX IF NOT EXISTS idx_workflows_provider_tenant
  ON workflows(provider, tenant_id);

-- Executions: filter by provider and environment
CREATE INDEX IF NOT EXISTS idx_executions_provider_env
  ON executions(provider, environment_id);

-- Credentials: filter by provider and environment
CREATE INDEX IF NOT EXISTS idx_credentials_provider_env
  ON credentials(provider, environment_id);

-- =============================================================================
-- ADDITIONAL INDEXES FOR COMMON QUERY PATTERNS
-- =============================================================================

-- Deployments: filter by provider and tenant
CREATE INDEX IF NOT EXISTS idx_deployments_provider_tenant
  ON deployments(provider, tenant_id);

-- Snapshots: filter by provider and environment
CREATE INDEX IF NOT EXISTS idx_snapshots_provider_env
  ON snapshots(provider, environment_id);

-- Promotions: filter by provider and tenant
CREATE INDEX IF NOT EXISTS idx_promotions_provider_tenant
  ON promotions(provider, tenant_id);

-- Pipelines: filter by provider and tenant
CREATE INDEX IF NOT EXISTS idx_pipelines_provider_tenant
  ON pipelines(provider, tenant_id);

-- Provider Users: filter by provider and environment
CREATE INDEX IF NOT EXISTS idx_provider_users_provider_env
  ON provider_users(provider, environment_id);

-- Tags: filter by provider and environment
CREATE INDEX IF NOT EXISTS idx_tags_provider_env
  ON tags(provider, environment_id);

-- Health Checks: filter by provider and environment
CREATE INDEX IF NOT EXISTS idx_health_checks_provider_env
  ON health_checks(provider, environment_id);

-- =============================================================================
-- BACKWARD COMPATIBILITY INDEX
-- =============================================================================

-- Workflows: partial index for n8n-specific queries using n8n_workflow_id
CREATE INDEX IF NOT EXISTS idx_workflows_provider_n8n_id
  ON workflows(provider, n8n_workflow_id)
  WHERE provider = 'n8n';

-- =============================================================================
-- VERIFICATION QUERY
-- =============================================================================
-- Run this to verify all indexes were created:
/*
SELECT
  indexname,
  tablename,
  indexdef
FROM pg_indexes
WHERE indexname LIKE 'idx_%provider%'
  AND schemaname = 'public'
ORDER BY tablename, indexname;
*/
