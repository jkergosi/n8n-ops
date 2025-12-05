-- Migration: Create n8n_users table for caching N8N user data per environment
-- Date: 2025-12-05
-- Description: Adds an n8n_users table to cache user information from N8N API per environment,
--              reducing direct N8N API calls and providing visibility into N8N instance access

-- Create n8n_users table
CREATE TABLE IF NOT EXISTS n8n_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Foreign Keys
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    environment_id UUID NOT NULL REFERENCES environments(id) ON DELETE CASCADE,

    -- N8N User Identifiers
    n8n_user_id VARCHAR(255) NOT NULL,  -- ID from N8N API

    -- Core User Data
    email VARCHAR(255) NOT NULL,
    first_name VARCHAR(255),
    last_name VARCHAR(255),

    -- N8N Specific Fields
    is_pending BOOLEAN DEFAULT false,  -- User has not completed signup yet
    role VARCHAR(100),  -- User role in N8N (e.g., 'owner', 'member', 'admin')
    settings JSONB,  -- User settings from N8N

    -- Full User JSON (includes all data from N8N)
    user_data JSONB NOT NULL,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE,  -- From N8N createdAt
    updated_at TIMESTAMP WITH TIME ZONE,  -- From N8N updatedAt

    -- Cache Management
    last_synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),  -- When this record was last synced from N8N
    is_deleted BOOLEAN DEFAULT false,  -- Soft delete flag for users removed from N8N

    -- Timestamps
    cached_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),  -- When initially cached

    -- Unique constraint: one user per N8N ID per environment
    CONSTRAINT unique_n8n_user_per_environment UNIQUE(tenant_id, environment_id, n8n_user_id)
);

-- Indexes for performance
CREATE INDEX idx_n8n_users_tenant ON n8n_users(tenant_id);
CREATE INDEX idx_n8n_users_environment ON n8n_users(environment_id);
CREATE INDEX idx_n8n_users_tenant_env ON n8n_users(tenant_id, environment_id);
CREATE INDEX idx_n8n_users_n8n_id ON n8n_users(n8n_user_id);
CREATE INDEX idx_n8n_users_email ON n8n_users(email);
CREATE INDEX idx_n8n_users_role ON n8n_users(role);
CREATE INDEX idx_n8n_users_last_synced ON n8n_users(last_synced_at);
CREATE INDEX idx_n8n_users_not_deleted ON n8n_users(is_deleted) WHERE is_deleted = false;

-- Add comments for documentation
COMMENT ON TABLE n8n_users IS 'Cached N8N user data from N8N API per environment to track instance access';
COMMENT ON COLUMN n8n_users.n8n_user_id IS 'Original user ID from N8N instance';
COMMENT ON COLUMN n8n_users.environment_id IS 'Which N8N environment this user belongs to';
COMMENT ON COLUMN n8n_users.is_pending IS 'True if user has not completed N8N signup yet';
COMMENT ON COLUMN n8n_users.role IS 'User role in N8N instance (owner, member, admin, etc.)';
COMMENT ON COLUMN n8n_users.user_data IS 'Complete user JSON from N8N API';
COMMENT ON COLUMN n8n_users.last_synced_at IS 'Timestamp of last successful sync from N8N API';
COMMENT ON COLUMN n8n_users.is_deleted IS 'Soft delete flag - true if user no longer exists in N8N';
