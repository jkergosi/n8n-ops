-- N8N Ops Database Schema for Supabase (PostgreSQL)
-- Complete setup with seed data

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLE CREATION
-- ============================================================================

-- Tenants table
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    subscription_tier VARCHAR(50) DEFAULT 'free' CHECK (subscription_tier IN ('free', 'pro', 'enterprise')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'viewer' CHECK (role IN ('admin', 'developer', 'viewer')),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('active', 'pending', 'inactive')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Environments table
CREATE TABLE IF NOT EXISTS environments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('dev', 'staging', 'production')),
    base_url VARCHAR(500) NOT NULL,
    api_key TEXT,
    is_active BOOLEAN DEFAULT true,
    last_connected TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(tenant_id, type)
);

-- Git configurations table
CREATE TABLE IF NOT EXISTS git_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE UNIQUE,
    repo_url VARCHAR(500) NOT NULL,
    branch VARCHAR(255) DEFAULT 'main',
    pat TEXT,
    last_sync TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Workflow snapshots table
CREATE TABLE IF NOT EXISTS workflow_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    workflow_id VARCHAR(255) NOT NULL,
    workflow_name VARCHAR(255) NOT NULL,
    version INTEGER NOT NULL,
    data JSONB NOT NULL,
    trigger VARCHAR(50) CHECK (trigger IN ('manual', 'auto-before-deploy', 'auto-before-restore', 'promotion')),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Deployments table
CREATE TABLE IF NOT EXISTS deployments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    workflow_id VARCHAR(255) NOT NULL,
    workflow_name VARCHAR(255) NOT NULL,
    source_environment VARCHAR(50) NOT NULL,
    target_environment VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'success', 'failed')),
    snapshot_id UUID REFERENCES workflow_snapshots(id),
    error_message TEXT,
    triggered_by UUID REFERENCES users(id),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_environments_tenant ON environments(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_tenant ON workflow_snapshots(tenant_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_workflow ON workflow_snapshots(workflow_id);
CREATE INDEX IF NOT EXISTS idx_deployments_tenant ON deployments(tenant_id);
CREATE INDEX IF NOT EXISTS idx_deployments_workflow ON deployments(workflow_id);

-- ============================================================================
-- TRIGGERS FOR AUTO-UPDATING TIMESTAMPS
-- ============================================================================

-- Updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers
DROP TRIGGER IF EXISTS update_tenants_updated_at ON tenants;
CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_environments_updated_at ON environments;
CREATE TRIGGER update_environments_updated_at BEFORE UPDATE ON environments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_git_configs_updated_at ON git_configs;
CREATE TRIGGER update_git_configs_updated_at BEFORE UPDATE ON git_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SEED DATA
-- ============================================================================

-- Insert test tenant (using specific UUID for testing)
INSERT INTO tenants (id, name, email, subscription_tier)
VALUES
    ('00000000-0000-0000-0000-000000000000', 'Test Organization', 'test@example.com', 'pro'),
    (uuid_generate_v4(), 'Acme Corporation', 'admin@acme.com', 'enterprise'),
    (uuid_generate_v4(), 'StartupCo', 'founder@startup.co', 'free')
ON CONFLICT (id) DO NOTHING;

-- Insert test users
INSERT INTO users (tenant_id, email, name, role, status)
VALUES
    ('00000000-0000-0000-0000-000000000000', 'admin@test.com', 'Admin User', 'admin', 'active'),
    ('00000000-0000-0000-0000-000000000000', 'dev@test.com', 'Developer User', 'developer', 'active'),
    ('00000000-0000-0000-0000-000000000000', 'viewer@test.com', 'Viewer User', 'viewer', 'active')
ON CONFLICT (email) DO NOTHING;

-- Insert environments for test tenant
INSERT INTO environments (tenant_id, name, type, base_url, api_key, last_connected)
VALUES
    (
        '00000000-0000-0000-0000-000000000000',
        'Development',
        'dev',
        'https://ns8i839t.rpcld.net',
        '123',
        NOW()
    ),
    (
        '00000000-0000-0000-0000-000000000000',
        'Staging',
        'staging',
        'https://staging-n8n.example.com',
        'staging-api-key-456',
        NOW() - INTERVAL '2 days'
    ),
    (
        '00000000-0000-0000-0000-000000000000',
        'Production',
        'production',
        'https://prod-n8n.example.com',
        'prod-api-key-789',
        NOW() - INTERVAL '1 hour'
    )
ON CONFLICT (tenant_id, type) DO NOTHING;

-- Insert git configuration for test tenant
INSERT INTO git_configs (tenant_id, repo_url, branch, pat, last_sync)
VALUES
    (
        '00000000-0000-0000-0000-000000000000',
        'https://github.com/your-org/n8n-workflows.git',
        'main',
        'ghp_test_token_placeholder',
        NOW() - INTERVAL '3 hours'
    )
ON CONFLICT (tenant_id) DO NOTHING;

-- Insert sample workflow snapshots
INSERT INTO workflow_snapshots (tenant_id, workflow_id, workflow_name, version, data, trigger, created_by)
SELECT
    '00000000-0000-0000-0000-000000000000',
    '1',
    'Customer Onboarding',
    1,
    '{"id": "1", "name": "Customer Onboarding", "nodes": [{"id": "trigger", "type": "webhook", "position": [0, 0]}], "connections": {}, "active": true}'::jsonb,
    'manual',
    u.id
FROM users u
WHERE u.email = 'admin@test.com'
LIMIT 1
ON CONFLICT DO NOTHING;

INSERT INTO workflow_snapshots (tenant_id, workflow_id, workflow_name, version, data, trigger, created_by)
SELECT
    '00000000-0000-0000-0000-000000000000',
    '2',
    'Email Notification System',
    1,
    '{"id": "2", "name": "Email Notification System", "nodes": [{"id": "trigger", "type": "schedule", "position": [0, 0]}], "connections": {}, "active": true}'::jsonb,
    'auto-before-deploy',
    u.id
FROM users u
WHERE u.email = 'dev@test.com'
LIMIT 1
ON CONFLICT DO NOTHING;

INSERT INTO workflow_snapshots (tenant_id, workflow_id, workflow_name, version, data, trigger, created_by)
SELECT
    '00000000-0000-0000-0000-000000000000',
    '3',
    'Data Sync Pipeline',
    2,
    '{"id": "3", "name": "Data Sync Pipeline", "nodes": [{"id": "trigger", "type": "webhook", "position": [0, 0]}], "connections": {}, "active": false}'::jsonb,
    'promotion',
    u.id
FROM users u
WHERE u.email = 'admin@test.com'
LIMIT 1
ON CONFLICT DO NOTHING;

-- Insert sample deployments
INSERT INTO deployments (tenant_id, workflow_id, workflow_name, source_environment, target_environment, status, snapshot_id, triggered_by, started_at, completed_at)
SELECT
    '00000000-0000-0000-0000-000000000000',
    '1',
    'Customer Onboarding',
    'dev',
    'staging',
    'success',
    ws.id,
    u.id,
    NOW() - INTERVAL '1 day',
    NOW() - INTERVAL '1 day' + INTERVAL '2 minutes'
FROM workflow_snapshots ws
JOIN users u ON u.email = 'admin@test.com'
WHERE ws.workflow_id = '1'
LIMIT 1
ON CONFLICT DO NOTHING;

INSERT INTO deployments (tenant_id, workflow_id, workflow_name, source_environment, target_environment, status, snapshot_id, triggered_by, started_at, completed_at)
SELECT
    '00000000-0000-0000-0000-000000000000',
    '1',
    'Customer Onboarding',
    'staging',
    'production',
    'success',
    ws.id,
    u.id,
    NOW() - INTERVAL '12 hours',
    NOW() - INTERVAL '12 hours' + INTERVAL '3 minutes'
FROM workflow_snapshots ws
JOIN users u ON u.email = 'admin@test.com'
WHERE ws.workflow_id = '1'
LIMIT 1
ON CONFLICT DO NOTHING;

INSERT INTO deployments (tenant_id, workflow_id, workflow_name, source_environment, target_environment, status, snapshot_id, error_message, triggered_by, started_at, completed_at)
SELECT
    '00000000-0000-0000-0000-000000000000',
    '3',
    'Data Sync Pipeline',
    'dev',
    'staging',
    'failed',
    ws.id,
    'Connection timeout while deploying workflow',
    u.id,
    NOW() - INTERVAL '6 hours',
    NOW() - INTERVAL '6 hours' + INTERVAL '5 minutes'
FROM workflow_snapshots ws
JOIN users u ON u.email = 'dev@test.com'
WHERE ws.workflow_id = '3'
LIMIT 1
ON CONFLICT DO NOTHING;

INSERT INTO deployments (tenant_id, workflow_id, workflow_name, source_environment, target_environment, status, snapshot_id, triggered_by, started_at)
SELECT
    '00000000-0000-0000-0000-000000000000',
    '2',
    'Email Notification System',
    'dev',
    'staging',
    'running',
    ws.id,
    u.id,
    NOW() - INTERVAL '5 minutes',
    NULL
FROM workflow_snapshots ws
JOIN users u ON u.email = 'admin@test.com'
WHERE ws.workflow_id = '2'
LIMIT 1
ON CONFLICT DO NOTHING;

-- ============================================================================
-- VERIFICATION QUERIES (commented out - uncomment to verify data)
-- ============================================================================

-- SELECT * FROM tenants;
-- SELECT * FROM users;
-- SELECT * FROM environments;
-- SELECT * FROM git_configs;
-- SELECT * FROM workflow_snapshots;
-- SELECT * FROM deployments;

-- ============================================================================
-- CLEANUP (commented out - use only if you need to reset)
-- ============================================================================

-- DROP TABLE IF EXISTS deployments CASCADE;
-- DROP TABLE IF EXISTS workflow_snapshots CASCADE;
-- DROP TABLE IF EXISTS git_configs CASCADE;
-- DROP TABLE IF EXISTS environments CASCADE;
-- DROP TABLE IF EXISTS users CASCADE;
-- DROP TABLE IF EXISTS tenants CASCADE;
-- DROP FUNCTION IF EXISTS update_updated_at_column();
