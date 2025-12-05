-- Migration: Create tags table for caching N8N tag data
-- Date: 2025-12-05
-- Description: Adds a tags table to cache tag information from N8N API,
--              including tenant_id and environment_id for multi-tenant support

-- Create tags table
CREATE TABLE IF NOT EXISTS tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Foreign Keys
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    environment_id UUID NOT NULL REFERENCES environments(id) ON DELETE CASCADE,

    -- N8N Tag Identifiers
    tag_id VARCHAR(255) NOT NULL,  -- ID from N8N API
    name VARCHAR(255) NOT NULL,

    -- Timestamps from N8N
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,

    -- Cache Management
    last_synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Unique constraint: one tag per N8N ID per environment
    CONSTRAINT unique_tag_per_environment UNIQUE(tenant_id, environment_id, tag_id)
);

-- Indexes for performance
CREATE INDEX idx_tags_tenant ON tags(tenant_id);
CREATE INDEX idx_tags_environment ON tags(environment_id);
CREATE INDEX idx_tags_tenant_env ON tags(tenant_id, environment_id);
CREATE INDEX idx_tags_tag_id ON tags(tag_id);
CREATE INDEX idx_tags_name ON tags(name);
CREATE INDEX idx_tags_last_synced ON tags(last_synced_at);

-- Add comments for documentation
COMMENT ON TABLE tags IS 'Cached tag data from N8N API to reduce direct API calls';
COMMENT ON COLUMN tags.tag_id IS 'Original tag ID from N8N instance';
COMMENT ON COLUMN tags.name IS 'Tag name from N8N';
COMMENT ON COLUMN tags.last_synced_at IS 'Timestamp of last successful sync from N8N API';
