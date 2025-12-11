-- Migration: Provider Abstraction Base Schema
-- Version: 002
-- Description: Add provider column to all provider-scoped tables and create provider_config JSONB
-- Run this migration in Supabase SQL Editor

-- =============================================================================
-- 1. ENVIRONMENTS TABLE
-- =============================================================================

-- Add provider column
ALTER TABLE environments
  ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- Add provider_config JSONB for flexible provider configuration
ALTER TABLE environments
  ADD COLUMN IF NOT EXISTS provider_config JSONB DEFAULT '{}'::jsonb;

-- Backfill provider_config from existing n8n_* fields
UPDATE environments
SET provider_config = jsonb_build_object(
  'base_url', n8n_base_url,
  'api_key', n8n_api_key,
  'encryption_key', n8n_encryption_key
)
WHERE provider = 'n8n'
  AND (provider_config IS NULL OR provider_config = '{}'::jsonb);

-- =============================================================================
-- 2. WORKFLOWS TABLE
-- =============================================================================

ALTER TABLE workflows
  ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- =============================================================================
-- 3. DEPLOYMENTS TABLE
-- =============================================================================

ALTER TABLE deployments
  ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- =============================================================================
-- 4. SNAPSHOTS TABLE
-- =============================================================================

ALTER TABLE snapshots
  ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- =============================================================================
-- 5. CREDENTIALS TABLE
-- =============================================================================

ALTER TABLE credentials
  ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- =============================================================================
-- 6. EXECUTIONS TABLE
-- =============================================================================

ALTER TABLE executions
  ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- =============================================================================
-- 7. PIPELINES TABLE
-- =============================================================================

ALTER TABLE pipelines
  ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- =============================================================================
-- 8. PROMOTIONS TABLE
-- =============================================================================

ALTER TABLE promotions
  ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- =============================================================================
-- 9. DEPLOYMENT_WORKFLOWS TABLE
-- =============================================================================

ALTER TABLE deployment_workflows
  ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- =============================================================================
-- 10. TAGS TABLE
-- =============================================================================

ALTER TABLE tags
  ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- =============================================================================
-- 11. N8N_USERS -> PROVIDER_USERS TABLE RENAME
-- =============================================================================

-- Rename table from n8n_users to provider_users
ALTER TABLE IF EXISTS n8n_users RENAME TO provider_users;

-- Add provider column to provider_users
ALTER TABLE provider_users
  ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- Rename n8n_user_id column to provider_user_id
ALTER TABLE provider_users
  RENAME COLUMN n8n_user_id TO provider_user_id;

-- =============================================================================
-- 12. NOTIFICATION_CHANNELS TABLE
-- =============================================================================

ALTER TABLE notification_channels
  ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- =============================================================================
-- 13. NOTIFICATION_RULES TABLE
-- =============================================================================

ALTER TABLE notification_rules
  ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- =============================================================================
-- 14. HEALTH_CHECKS TABLE
-- =============================================================================

ALTER TABLE health_checks
  ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- =============================================================================
-- VERIFICATION QUERY
-- =============================================================================
-- Run this to verify all provider columns were added:
/*
SELECT
  table_name,
  column_name,
  data_type,
  column_default
FROM information_schema.columns
WHERE column_name = 'provider'
  AND table_schema = 'public'
ORDER BY table_name;
*/
