-- Migration: Create executions table for caching N8N execution data
-- Date: 2025-12-05
-- Description: Adds an executions table to cache execution information from N8N API,
--              including tenant_id and environment_id for multi-tenant support

-- Create executions table
CREATE TABLE IF NOT EXISTS executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Foreign Keys
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    environment_id UUID NOT NULL REFERENCES environments(id) ON DELETE CASCADE,

    -- N8N Execution Identifiers
    execution_id VARCHAR(255) NOT NULL,  -- ID from N8N API
    workflow_id VARCHAR(255) NOT NULL,   -- N8N workflow ID that was executed
    workflow_name VARCHAR(255),           -- Name of the workflow at execution time

    -- Execution Details
    status VARCHAR(50) NOT NULL,  -- success, error, waiting, running, new, unknown, etc.
    mode VARCHAR(50),             -- manual, trigger, webhook, retry, etc.

    -- Timing Information
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE,
    execution_time FLOAT,  -- Duration in milliseconds

    -- Full Execution Data (includes detailed node execution results, errors, etc.)
    data JSONB,

    -- Cache Management
    last_synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Unique constraint: one execution record per N8N execution ID per environment
    CONSTRAINT unique_execution_per_environment UNIQUE(tenant_id, environment_id, execution_id)
);

-- Indexes for performance
CREATE INDEX idx_executions_tenant ON executions(tenant_id);
CREATE INDEX idx_executions_environment ON executions(environment_id);
CREATE INDEX idx_executions_tenant_env ON executions(tenant_id, environment_id);
CREATE INDEX idx_executions_workflow ON executions(workflow_id);
CREATE INDEX idx_executions_status ON executions(status);
CREATE INDEX idx_executions_started_at ON executions(started_at DESC);
CREATE INDEX idx_executions_workflow_status ON executions(workflow_id, status);

-- Add comments for documentation
COMMENT ON TABLE executions IS 'Cached execution data from N8N API to reduce direct API calls and provide execution history';
COMMENT ON COLUMN executions.execution_id IS 'Original execution ID from N8N instance';
COMMENT ON COLUMN executions.workflow_id IS 'N8N workflow ID that was executed';
COMMENT ON COLUMN executions.status IS 'Execution status: success, error, waiting, running, etc.';
COMMENT ON COLUMN executions.mode IS 'How the execution was triggered: manual, trigger, webhook, retry';
COMMENT ON COLUMN executions.execution_time IS 'Duration of execution in milliseconds';
COMMENT ON COLUMN executions.data IS 'Complete execution JSON including node results and error details';
COMMENT ON COLUMN executions.last_synced_at IS 'Timestamp of last successful sync from N8N API';
