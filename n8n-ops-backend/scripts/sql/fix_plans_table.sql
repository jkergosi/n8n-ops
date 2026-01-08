-- Fix for: "Plan 'free' not found in database" error
-- This script creates the missing plans table and seeds it with required plans.
-- Run this directly against the database if the error is occurring.

-- Create the plans table if it doesn't exist
CREATE TABLE IF NOT EXISTS plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    color_class VARCHAR(50),
    precedence INTEGER NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_plans_name ON plans(name);
CREATE INDEX IF NOT EXISTS idx_plans_is_active ON plans(is_active);
CREATE INDEX IF NOT EXISTS idx_plans_sort_order ON plans(sort_order);

-- Enable RLS on plans table
ALTER TABLE plans ENABLE ROW LEVEL SECURITY;

-- Plans table: public read access (needed for billing/entitlements APIs)
DROP POLICY IF EXISTS "plans_select_policy" ON plans;
CREATE POLICY "plans_select_policy" ON plans
    FOR SELECT USING (true);

-- Seed the plans table with all plan tiers
INSERT INTO plans (name, display_name, description, icon, color_class, precedence, sort_order, is_active)
VALUES
    ('free', 'Free', 'Get started with basic workflow management', 'Sparkles', 'text-gray-500', 10, 10, true),
    ('pro', 'Pro', 'For teams that need more power', 'Zap', 'text-blue-500', 20, 20, true),
    ('agency', 'Agency', 'For agencies managing multiple clients', 'Building2', 'text-purple-500', 30, 30, true),
    ('enterprise', 'Enterprise', 'For large organizations with advanced needs', 'Shield', 'text-amber-500', 40, 40, true)
ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    icon = EXCLUDED.icon,
    color_class = EXCLUDED.color_class,
    precedence = EXCLUDED.precedence,
    sort_order = EXCLUDED.sort_order,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();

-- Re-populate plan_features for all plans (in case the initial seeding failed)
-- Free plan features
INSERT INTO plan_features (plan_id, feature_id, value)
SELECT p.id, f.id,
    CASE f.name
        -- Limits
        WHEN 'max_environments' THEN '{"value": 1}'::jsonb
        WHEN 'max_team_members' THEN '{"value": 3}'::jsonb
        WHEN 'max_workflows_per_env' THEN '{"value": 50}'::jsonb
        WHEN 'environment_limits' THEN '{"value": 1}'::jsonb
        WHEN 'workflow_limits' THEN '{"value": 10}'::jsonb
        WHEN 'snapshots_history' THEN '{"value": 5}'::jsonb
        WHEN 'observability_limits' THEN '{"value": 7}'::jsonb
        WHEN 'agency_client_limits' THEN '{"value": 0}'::jsonb
        WHEN 'enterprise_limits' THEN '{"value": 0}'::jsonb
        -- Enabled flags
        WHEN 'workflow_snapshots' THEN '{"enabled": true}'::jsonb
        WHEN 'environment_basic' THEN '{"enabled": true}'::jsonb
        WHEN 'workflow_read' THEN '{"enabled": true}'::jsonb
        WHEN 'workflow_push' THEN '{"enabled": true}'::jsonb
        WHEN 'snapshots_enabled' THEN '{"enabled": true}'::jsonb
        WHEN 'observability_basic' THEN '{"enabled": true}'::jsonb
        WHEN 'rbac_basic' THEN '{"enabled": true}'::jsonb
        -- Disabled flags
        ELSE '{"enabled": false}'::jsonb
    END
FROM plans p
CROSS JOIN features f
WHERE p.name = 'free'
ON CONFLICT (plan_id, feature_id) DO UPDATE SET
    value = EXCLUDED.value,
    updated_at = NOW();

-- Pro plan features
INSERT INTO plan_features (plan_id, feature_id, value)
SELECT p.id, f.id,
    CASE f.name
        -- Limits
        WHEN 'max_environments' THEN '{"value": 3}'::jsonb
        WHEN 'max_team_members' THEN '{"value": 25}'::jsonb
        WHEN 'max_workflows_per_env' THEN '{"value": 500}'::jsonb
        WHEN 'environment_limits' THEN '{"value": 3}'::jsonb
        WHEN 'workflow_limits' THEN '{"value": 200}'::jsonb
        WHEN 'snapshots_history' THEN '{"value": 30}'::jsonb
        WHEN 'observability_limits' THEN '{"value": 30}'::jsonb
        WHEN 'agency_client_limits' THEN '{"value": 0}'::jsonb
        WHEN 'enterprise_limits' THEN '{"value": 0}'::jsonb
        -- Enabled flags for Pro
        WHEN 'github_sync' THEN '{"enabled": true}'::jsonb
        WHEN 'scheduled_backups' THEN '{"enabled": true}'::jsonb
        WHEN 'workflow_snapshots' THEN '{"enabled": true}'::jsonb
        WHEN 'deployments' THEN '{"enabled": true}'::jsonb
        WHEN 'observability' THEN '{"enabled": true}'::jsonb
        WHEN 'audit_logs' THEN '{"enabled": true}'::jsonb
        WHEN 'api_access' THEN '{"enabled": true}'::jsonb
        WHEN 'priority_support' THEN '{"enabled": true}'::jsonb
        WHEN 'environment_basic' THEN '{"enabled": true}'::jsonb
        WHEN 'environment_health' THEN '{"enabled": true}'::jsonb
        WHEN 'environment_diff' THEN '{"enabled": true}'::jsonb
        WHEN 'workflow_read' THEN '{"enabled": true}'::jsonb
        WHEN 'workflow_push' THEN '{"enabled": true}'::jsonb
        WHEN 'workflow_dirty_check' THEN '{"enabled": true}'::jsonb
        WHEN 'workflow_ci_cd' THEN '{"enabled": true}'::jsonb
        WHEN 'snapshots_enabled' THEN '{"enabled": true}'::jsonb
        WHEN 'snapshots_auto' THEN '{"enabled": true}'::jsonb
        WHEN 'snapshots_export' THEN '{"enabled": true}'::jsonb
        WHEN 'observability_basic' THEN '{"enabled": true}'::jsonb
        WHEN 'observability_alerts' THEN '{"enabled": true}'::jsonb
        WHEN 'observability_logs' THEN '{"enabled": true}'::jsonb
        WHEN 'rbac_basic' THEN '{"enabled": true}'::jsonb
        WHEN 'audit_logs_enabled' THEN '{"enabled": true}'::jsonb
        WHEN 'support_priority' THEN '{"enabled": true}'::jsonb
        WHEN 'drift_incidents' THEN '{"enabled": true}'::jsonb
        -- Disabled flags
        ELSE '{"enabled": false}'::jsonb
    END
FROM plans p
CROSS JOIN features f
WHERE p.name = 'pro'
ON CONFLICT (plan_id, feature_id) DO UPDATE SET
    value = EXCLUDED.value,
    updated_at = NOW();

-- Agency plan features
INSERT INTO plan_features (plan_id, feature_id, value)
SELECT p.id, f.id,
    CASE f.name
        -- Limits (agency has high limits)
        WHEN 'max_environments' THEN '{"value": 9999}'::jsonb
        WHEN 'max_team_members' THEN '{"value": 100}'::jsonb
        WHEN 'max_workflows_per_env' THEN '{"value": 1000}'::jsonb
        WHEN 'environment_limits' THEN '{"value": 9999}'::jsonb
        WHEN 'workflow_limits' THEN '{"value": 1000}'::jsonb
        WHEN 'snapshots_history' THEN '{"value": 90}'::jsonb
        WHEN 'observability_limits' THEN '{"value": 90}'::jsonb
        WHEN 'agency_client_limits' THEN '{"value": 25}'::jsonb
        WHEN 'enterprise_limits' THEN '{"value": 0}'::jsonb
        -- Disabled flags for agency
        WHEN 'sso' THEN '{"enabled": false}'::jsonb
        WHEN 'sso_saml' THEN '{"enabled": false}'::jsonb
        WHEN 'data_residency' THEN '{"enabled": false}'::jsonb
        WHEN 'observability_alerts_advanced' THEN '{"enabled": false}'::jsonb
        -- Everything else enabled
        ELSE '{"enabled": true}'::jsonb
    END
FROM plans p
CROSS JOIN features f
WHERE p.name = 'agency'
ON CONFLICT (plan_id, feature_id) DO UPDATE SET
    value = EXCLUDED.value,
    updated_at = NOW();

-- Enterprise plan features (all features enabled/high limits)
INSERT INTO plan_features (plan_id, feature_id, value)
SELECT p.id, f.id,
    CASE f.name
        -- Limits (enterprise has unlimited/very high limits)
        WHEN 'max_environments' THEN '{"value": 9999}'::jsonb
        WHEN 'max_team_members' THEN '{"value": 9999}'::jsonb
        WHEN 'max_workflows_per_env' THEN '{"value": 9999}'::jsonb
        WHEN 'environment_limits' THEN '{"value": 9999}'::jsonb
        WHEN 'workflow_limits' THEN '{"value": 5000}'::jsonb
        WHEN 'snapshots_history' THEN '{"value": 365}'::jsonb
        WHEN 'observability_limits' THEN '{"value": 365}'::jsonb
        WHEN 'agency_client_limits' THEN '{"value": 100}'::jsonb
        WHEN 'enterprise_limits' THEN '{"value": 9999}'::jsonb
        -- All flags enabled for enterprise
        ELSE '{"enabled": true}'::jsonb
    END
FROM plans p
CROSS JOIN features f
WHERE p.name = 'enterprise'
ON CONFLICT (plan_id, feature_id) DO UPDATE SET
    value = EXCLUDED.value,
    updated_at = NOW();

-- Verify the fix
SELECT name, display_name, is_active FROM plans ORDER BY sort_order;
