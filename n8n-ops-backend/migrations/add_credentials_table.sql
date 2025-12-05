-- Migration: Create credentials table for caching N8N credential data
-- Date: 2025-12-05
-- Description: Adds a credentials table to cache credential information from N8N API,
--              reducing direct N8N API calls and improving performance

-- Create credentials table
CREATE TABLE IF NOT EXISTS credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Foreign Keys
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    environment_id UUID NOT NULL REFERENCES environments(id) ON DELETE CASCADE,

    -- N8N Credential Identifiers
    n8n_credential_id VARCHAR(255) NOT NULL,  -- ID from N8N API

    -- Core Credential Data
    name VARCHAR(255) NOT NULL,
    type VARCHAR(255) NOT NULL,  -- Credential type (e.g., 'httpBasicAuth', 'slackApi', etc.)

    -- Full Credential JSON (includes all data except sensitive credentials)
    credential_data JSONB NOT NULL,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE,  -- From N8N createdAt
    updated_at TIMESTAMP WITH TIME ZONE,  -- From N8N updatedAt

    -- Cache Management
    last_synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),  -- When this record was last synced from N8N
    is_deleted BOOLEAN DEFAULT false,  -- Soft delete flag for credentials removed from N8N

    -- Timestamps
    cached_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),  -- When initially cached

    -- Unique constraint: one credential per N8N ID per environment
    CONSTRAINT unique_credential_per_environment UNIQUE(tenant_id, environment_id, n8n_credential_id)
);

-- Indexes for performance
CREATE INDEX idx_credentials_tenant ON credentials(tenant_id);
CREATE INDEX idx_credentials_environment ON credentials(environment_id);
CREATE INDEX idx_credentials_tenant_env ON credentials(tenant_id, environment_id);
CREATE INDEX idx_credentials_n8n_id ON credentials(n8n_credential_id);
CREATE INDEX idx_credentials_type ON credentials(type);
CREATE INDEX idx_credentials_last_synced ON credentials(last_synced_at);
CREATE INDEX idx_credentials_not_deleted ON credentials(is_deleted) WHERE is_deleted = false;

-- Add comments for documentation
COMMENT ON TABLE credentials IS 'Cached credential data from N8N API to reduce direct API calls';
COMMENT ON COLUMN credentials.n8n_credential_id IS 'Original credential ID from N8N instance';
COMMENT ON COLUMN credentials.type IS 'Type of credential (e.g., httpBasicAuth, slackApi)';
COMMENT ON COLUMN credentials.credential_data IS 'Complete credential JSON (metadata only, no sensitive data)';
COMMENT ON COLUMN credentials.last_synced_at IS 'Timestamp of last successful sync from N8N API';
COMMENT ON COLUMN credentials.is_deleted IS 'Soft delete flag - true if credential no longer exists in N8N';
