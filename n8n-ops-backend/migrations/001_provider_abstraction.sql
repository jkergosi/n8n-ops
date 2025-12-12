-- Migration: Provider Abstraction (Phase 1)
-- Per req_provider_abstraction.md - Decouple from n8n-specific logic
-- All existing data is assumed to be n8n provider

-- ============================================================================
-- 1. Add provider column to all provider-scoped tables
-- ============================================================================

-- environments table (+ provider_config JSONB for provider-specific settings)
ALTER TABLE environments ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';
ALTER TABLE environments ADD COLUMN IF NOT EXISTS provider_config JSONB;

-- workflows table
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- deployments table
ALTER TABLE deployments ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- snapshots table
ALTER TABLE snapshots ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- credentials table
ALTER TABLE credentials ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- executions table
ALTER TABLE executions ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- pipelines table
ALTER TABLE pipelines ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- promotions table
ALTER TABLE promotions ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- deployment_workflows table
ALTER TABLE deployment_workflows ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- tags table
ALTER TABLE tags ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- notification_channels table
ALTER TABLE notification_channels ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- notification_rules table
ALTER TABLE notification_rules ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- health_checks table
ALTER TABLE health_checks ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- ============================================================================
-- 2. Rename n8n_users table to provider_users
-- ============================================================================

-- Rename table (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'n8n_users') THEN
        ALTER TABLE n8n_users RENAME TO provider_users;
    END IF;
END $$;

-- Add provider column to provider_users
ALTER TABLE provider_users ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'n8n';

-- Rename n8n_user_id column to provider_user_id (if exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.columns
        WHERE table_name = 'provider_users' AND column_name = 'n8n_user_id'
    ) THEN
        ALTER TABLE provider_users RENAME COLUMN n8n_user_id TO provider_user_id;
    END IF;
END $$;

-- ============================================================================
-- 3. Backfill provider_config from existing n8n_* fields in environments
-- ============================================================================

UPDATE environments
SET provider_config = jsonb_build_object(
    'base_url', n8n_base_url,
    'api_key', n8n_api_key,
    'encryption_key', n8n_encryption_key
)
WHERE provider_config IS NULL
  AND n8n_base_url IS NOT NULL;

-- ============================================================================
-- 4. Comments for documentation
-- ============================================================================

COMMENT ON COLUMN environments.provider IS 'Workflow automation provider type: n8n, make';
COMMENT ON COLUMN environments.provider_config IS 'Provider-specific configuration (API keys, URLs, etc.)';
COMMENT ON COLUMN workflows.provider IS 'Provider this workflow belongs to';
COMMENT ON COLUMN executions.provider IS 'Provider this execution belongs to';
COMMENT ON COLUMN credentials.provider IS 'Provider this credential belongs to';
COMMENT ON COLUMN deployments.provider IS 'Provider for this deployment';
COMMENT ON COLUMN snapshots.provider IS 'Provider for this snapshot';
COMMENT ON COLUMN pipelines.provider IS 'Provider this pipeline targets';
COMMENT ON COLUMN promotions.provider IS 'Provider for this promotion';
COMMENT ON COLUMN tags.provider IS 'Provider this tag belongs to';
COMMENT ON COLUMN provider_users.provider IS 'Provider instance this user belongs to';
