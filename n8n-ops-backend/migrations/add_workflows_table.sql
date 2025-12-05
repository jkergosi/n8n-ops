-- Migration: Create workflows table for caching N8N workflow data
-- Date: 2025-12-05
-- Description: Adds a workflows table to cache workflow information from N8N API,
--              reducing direct N8N API calls and improving performance

-- Create workflows table
CREATE TABLE IF NOT EXISTS workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Foreign Keys
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    environment_id UUID NOT NULL REFERENCES environments(id) ON DELETE CASCADE,

    -- N8N Workflow Identifiers
    n8n_workflow_id VARCHAR(255) NOT NULL,  -- ID from N8N API

    -- Core Workflow Data
    name VARCHAR(255) NOT NULL,
    active BOOLEAN DEFAULT false,

    -- Full Workflow JSON (includes nodes, connections, settings, etc.)
    workflow_data JSONB NOT NULL,

    -- Metadata
    tags TEXT[],  -- Array of tag names
    created_at TIMESTAMP WITH TIME ZONE,  -- From N8N createdAt
    updated_at TIMESTAMP WITH TIME ZONE,  -- From N8N updatedAt

    -- Cache Management
    last_synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),  -- When this record was last synced from N8N
    is_deleted BOOLEAN DEFAULT false,  -- Soft delete flag for workflows removed from N8N

    -- Timestamps
    cached_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),  -- When initially cached

    -- Unique constraint: one workflow per N8N ID per environment
    CONSTRAINT unique_workflow_per_environment UNIQUE(tenant_id, environment_id, n8n_workflow_id)
);

-- Indexes for performance
CREATE INDEX idx_workflows_tenant ON workflows(tenant_id);
CREATE INDEX idx_workflows_environment ON workflows(environment_id);
CREATE INDEX idx_workflows_tenant_env ON workflows(tenant_id, environment_id);
CREATE INDEX idx_workflows_n8n_id ON workflows(n8n_workflow_id);
CREATE INDEX idx_workflows_active ON workflows(active) WHERE active = true;
CREATE INDEX idx_workflows_last_synced ON workflows(last_synced_at);
CREATE INDEX idx_workflows_tags ON workflows USING GIN(tags);  -- For tag searches
CREATE INDEX idx_workflows_not_deleted ON workflows(is_deleted) WHERE is_deleted = false;

-- Add comments for documentation
COMMENT ON TABLE workflows IS 'Cached workflow data from N8N API to reduce direct API calls';
COMMENT ON COLUMN workflows.n8n_workflow_id IS 'Original workflow ID from N8N instance';
COMMENT ON COLUMN workflows.workflow_data IS 'Complete workflow JSON including nodes, connections, and settings';
COMMENT ON COLUMN workflows.last_synced_at IS 'Timestamp of last successful sync from N8N API';
COMMENT ON COLUMN workflows.is_deleted IS 'Soft delete flag - true if workflow no longer exists in N8N';
