-- Migration: Provider Indexes (Phase 1)
-- Per req_provider_abstraction.md - Add composite indexes for provider-scoped queries

-- ============================================================================
-- 1. Environment indexes
-- ============================================================================

-- Primary environment lookups by provider and tenant
CREATE INDEX IF NOT EXISTS idx_environments_provider_tenant ON environments(provider, tenant_id);

-- ============================================================================
-- 2. Workflow indexes
-- ============================================================================

-- Workflow lookups by provider and environment
CREATE INDEX IF NOT EXISTS idx_workflows_provider_env ON workflows(provider, environment_id);

-- Workflow lookups by provider and tenant
CREATE INDEX IF NOT EXISTS idx_workflows_provider_tenant ON workflows(provider, tenant_id);

-- ============================================================================
-- 3. Execution indexes
-- ============================================================================

-- Execution lookups by provider and environment
CREATE INDEX IF NOT EXISTS idx_executions_provider_env ON executions(provider, environment_id);

-- Execution lookups by provider and tenant
CREATE INDEX IF NOT EXISTS idx_executions_provider_tenant ON executions(provider, tenant_id);

-- Executions by provider, tenant, and time (for usage queries)
CREATE INDEX IF NOT EXISTS idx_executions_provider_tenant_created ON executions(provider, tenant_id, created_at DESC);

-- ============================================================================
-- 4. Credential indexes
-- ============================================================================

-- Credential lookups by provider and environment
CREATE INDEX IF NOT EXISTS idx_credentials_provider_env ON credentials(provider, environment_id);

-- Credential lookups by provider and tenant
CREATE INDEX IF NOT EXISTS idx_credentials_provider_tenant ON credentials(provider, tenant_id);

-- ============================================================================
-- 5. Deployment indexes
-- ============================================================================

-- Deployment lookups by provider and tenant
CREATE INDEX IF NOT EXISTS idx_deployments_provider_tenant ON deployments(provider, tenant_id);

-- ============================================================================
-- 6. Snapshot indexes
-- ============================================================================

-- Snapshot lookups by provider and environment
CREATE INDEX IF NOT EXISTS idx_snapshots_provider_env ON snapshots(provider, environment_id);

-- Snapshot lookups by provider and tenant
CREATE INDEX IF NOT EXISTS idx_snapshots_provider_tenant ON snapshots(provider, tenant_id);

-- ============================================================================
-- 7. Pipeline indexes
-- ============================================================================

-- Pipeline lookups by provider and tenant
CREATE INDEX IF NOT EXISTS idx_pipelines_provider_tenant ON pipelines(provider, tenant_id);

-- ============================================================================
-- 8. Promotion indexes
-- ============================================================================

-- Promotion lookups by provider and tenant
CREATE INDEX IF NOT EXISTS idx_promotions_provider_tenant ON promotions(provider, tenant_id);

-- ============================================================================
-- 9. Tag indexes
-- ============================================================================

-- Tag lookups by provider and tenant
CREATE INDEX IF NOT EXISTS idx_tags_provider_tenant ON tags(provider, tenant_id);

-- Tag lookups by provider and environment
CREATE INDEX IF NOT EXISTS idx_tags_provider_env ON tags(provider, environment_id);

-- ============================================================================
-- 10. Provider Users indexes
-- ============================================================================

-- Provider user lookups by provider and environment
CREATE INDEX IF NOT EXISTS idx_provider_users_provider_env ON provider_users(provider, environment_id);

-- Provider user lookups by provider and tenant
CREATE INDEX IF NOT EXISTS idx_provider_users_provider_tenant ON provider_users(provider, tenant_id);

-- ============================================================================
-- 11. Health Check indexes
-- ============================================================================

-- Health check lookups by provider and environment
CREATE INDEX IF NOT EXISTS idx_health_checks_provider_env ON health_checks(provider, environment_id);

-- ============================================================================
-- 12. Notification indexes
-- ============================================================================

-- Notification channel lookups by provider
CREATE INDEX IF NOT EXISTS idx_notification_channels_provider ON notification_channels(provider);

-- Notification rule lookups by provider
CREATE INDEX IF NOT EXISTS idx_notification_rules_provider ON notification_rules(provider);
