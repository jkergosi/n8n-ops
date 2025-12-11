-- Phase 1: Admin/Superuser Tables
-- Run this migration in Supabase SQL editor

-- =============================================================================
-- Audit Logs Table (comprehensive admin action logging)
-- =============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_id UUID REFERENCES users(id) ON DELETE SET NULL,
    actor_email TEXT,
    actor_name TEXT,
    tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL,
    tenant_name TEXT,
    action TEXT NOT NULL,
    action_type TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    resource_name TEXT,
    old_value JSONB,
    new_value JSONB,
    reason TEXT,
    ip_address TEXT,
    user_agent TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_id ON audit_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action_type ON audit_logs(action_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor_id ON audit_logs(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource_type ON audit_logs(resource_type);

-- =============================================================================
-- Tenant Notes Table (internal notes about tenants)
-- =============================================================================
CREATE TABLE IF NOT EXISTS tenant_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    author_id UUID REFERENCES users(id) ON DELETE SET NULL,
    author_email TEXT,
    author_name TEXT,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tenant_notes_tenant_id ON tenant_notes(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_notes_created_at ON tenant_notes(created_at DESC);

-- =============================================================================
-- Add missing columns to tenants table
-- =============================================================================
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active';
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS scheduled_deletion_at TIMESTAMPTZ;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS primary_contact_name TEXT;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMPTZ;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT;

-- =============================================================================
-- Add Stripe columns to plans table (if exists)
-- =============================================================================
ALTER TABLE plans ADD COLUMN IF NOT EXISTS stripe_product_id TEXT;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS stripe_price_id_monthly TEXT;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS stripe_price_id_annual TEXT;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS price_monthly INTEGER DEFAULT 0;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS price_annual INTEGER DEFAULT 0;

-- =============================================================================
-- Subscriptions table enhancements
-- =============================================================================
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS trial_start TIMESTAMPTZ;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS trial_end TIMESTAMPTZ;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS canceled_at TIMESTAMPTZ;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS cancel_at_period_end BOOLEAN DEFAULT FALSE;

-- =============================================================================
-- Enable RLS policies for new tables
-- =============================================================================
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_notes ENABLE ROW LEVEL SECURITY;

-- Policy: Only superusers can access audit logs
CREATE POLICY audit_logs_superuser_policy ON audit_logs
    FOR ALL
    USING (true);  -- In production, add proper superuser check

-- Policy: Only superusers can access tenant notes
CREATE POLICY tenant_notes_superuser_policy ON tenant_notes
    FOR ALL
    USING (true);  -- In production, add proper superuser check
