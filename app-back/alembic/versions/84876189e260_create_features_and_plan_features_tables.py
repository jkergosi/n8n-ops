"""create_features_and_plan_features_tables

Revision ID: 84876189e260
Revises: 'f1e2d3c4b5a6'
Create Date: 2026-01-07 12:00:00

Creates the features and plan_features tables required by the billing API endpoints:
- GET /api/v1/billing/plan-features/all
- GET /api/v1/billing/feature-display-names

These tables store:
- features: All available features with their types and display names
- plan_features: The mapping of features to plans with their values
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '84876189e260'
down_revision = 'f1e2d3c4b5a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the features table
    op.execute('''
    CREATE TABLE IF NOT EXISTS features (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(100) NOT NULL UNIQUE,
        display_name VARCHAR(255) NOT NULL,
        description TEXT,
        type VARCHAR(20) NOT NULL DEFAULT 'flag' CHECK (type IN ('flag', 'limit')),
        default_value JSONB DEFAULT '{}',
        status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'deprecated', 'hidden')),
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- Create index for faster lookups
    CREATE INDEX IF NOT EXISTS idx_features_name ON features(name);
    CREATE INDEX IF NOT EXISTS idx_features_status ON features(status);
    ''')

    # Create the plan_features table
    op.execute('''
    CREATE TABLE IF NOT EXISTS plan_features (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        plan_id UUID NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
        feature_id UUID NOT NULL REFERENCES features(id) ON DELETE CASCADE,
        value JSONB DEFAULT '{}',
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(plan_id, feature_id)
    );

    -- Create indexes for faster lookups
    CREATE INDEX IF NOT EXISTS idx_plan_features_plan_id ON plan_features(plan_id);
    CREATE INDEX IF NOT EXISTS idx_plan_features_feature_id ON plan_features(feature_id);
    ''')

    # Enable RLS on both tables
    op.execute('''
    ALTER TABLE features ENABLE ROW LEVEL SECURITY;
    ALTER TABLE plan_features ENABLE ROW LEVEL SECURITY;

    -- Features table: public read access (needed for billing API)
    DROP POLICY IF EXISTS "features_select_policy" ON features;
    CREATE POLICY "features_select_policy" ON features
        FOR SELECT USING (true);

    -- Plan features table: public read access (needed for billing API)
    DROP POLICY IF EXISTS "plan_features_select_policy" ON plan_features;
    CREATE POLICY "plan_features_select_policy" ON plan_features
        FOR SELECT USING (true);
    ''')

    # Seed the features table with all features from the frontend
    op.execute('''
    INSERT INTO features (name, display_name, description, type, default_value, status) VALUES
    -- Legacy features
    ('max_environments', 'Environments', 'Maximum number of environments', 'limit', '{"value": 1}', 'active'),
    ('max_team_members', 'Team Members', 'Maximum number of team members', 'limit', '{"value": 3}', 'active'),
    ('max_workflows_per_env', 'Workflows per Environment', 'Maximum workflows per environment', 'limit', '{"value": 50}', 'active'),
    ('github_sync', 'GitHub Sync', 'Sync workflows with GitHub repositories', 'flag', '{"enabled": false}', 'active'),
    ('scheduled_backups', 'Scheduled Backups', 'Automatic scheduled backups', 'flag', '{"enabled": false}', 'active'),
    ('workflow_snapshots', 'Workflow Snapshots', 'Create point-in-time snapshots', 'flag', '{"enabled": true}', 'active'),
    ('deployments', 'Deployments', 'Deploy workflows across environments', 'flag', '{"enabled": false}', 'active'),
    ('observability', 'Observability', 'Monitor workflow execution', 'flag', '{"enabled": false}', 'active'),
    ('audit_logs', 'Audit Logs', 'Track changes and access', 'flag', '{"enabled": false}', 'active'),
    ('custom_branding', 'Custom Branding', 'White-label branding options', 'flag', '{"enabled": false}', 'active'),
    ('sso', 'Single Sign-On', 'SSO authentication', 'flag', '{"enabled": false}', 'active'),
    ('api_access', 'API Access', 'Programmatic API access', 'flag', '{"enabled": false}', 'active'),
    ('priority_support', 'Priority Support', 'Priority customer support', 'flag', '{"enabled": false}', 'active'),
    -- Phase 2 Environment features
    ('environment_basic', 'Basic Environments', 'Basic environment management', 'flag', '{"enabled": true}', 'active'),
    ('environment_health', 'Environment Health Monitoring', 'Health checks and monitoring', 'flag', '{"enabled": false}', 'active'),
    ('environment_diff', 'Drift Detection', 'Detect environment drift', 'flag', '{"enabled": false}', 'active'),
    ('environment_limits', 'Environment Limit', 'Environment count limit', 'limit', '{"value": 1}', 'active'),
    -- Phase 2 Workflow features
    ('workflow_read', 'View Workflows', 'View workflow details', 'flag', '{"enabled": true}', 'active'),
    ('workflow_push', 'Push/Upload Workflows', 'Upload and push workflows', 'flag', '{"enabled": true}', 'active'),
    ('workflow_dirty_check', 'Dirty State Detection', 'Detect unsaved changes', 'flag', '{"enabled": false}', 'active'),
    ('workflow_ci_cd', 'Workflow CI/CD', 'CI/CD pipelines for workflows', 'flag', '{"enabled": false}', 'active'),
    ('workflow_ci_cd_approval', 'CI/CD Approvals', 'Approval workflows for CI/CD', 'flag', '{"enabled": false}', 'active'),
    ('workflow_limits', 'Workflow Limit', 'Workflow count limit', 'limit', '{"value": 10}', 'active'),
    -- Phase 2 Snapshot features
    ('snapshots_enabled', 'Snapshots', 'Snapshot functionality enabled', 'flag', '{"enabled": true}', 'active'),
    ('snapshots_auto', 'Automatic Snapshots', 'Automatic snapshot creation', 'flag', '{"enabled": false}', 'active'),
    ('snapshots_history', 'Snapshot Retention', 'Snapshot history retention days', 'limit', '{"value": 5}', 'active'),
    ('snapshots_export', 'Export Snapshots', 'Export snapshots to files', 'flag', '{"enabled": false}', 'active'),
    -- Phase 2 Observability features
    ('observability_basic', 'Basic Metrics', 'Basic execution metrics', 'flag', '{"enabled": true}', 'active'),
    ('observability_alerts', 'Alerting', 'Alert notifications', 'flag', '{"enabled": false}', 'active'),
    ('observability_alerts_advanced', 'Advanced Alerting', 'Advanced alert rules', 'flag', '{"enabled": false}', 'active'),
    ('observability_logs', 'Execution Logs', 'Detailed execution logs', 'flag', '{"enabled": false}', 'active'),
    ('observability_limits', 'Log Retention', 'Log retention days', 'limit', '{"value": 7}', 'active'),
    -- Phase 2 RBAC features
    ('rbac_basic', 'Basic Role Management', 'Basic role-based access', 'flag', '{"enabled": true}', 'active'),
    ('rbac_advanced', 'Advanced RBAC', 'Advanced role permissions', 'flag', '{"enabled": false}', 'active'),
    ('audit_logs_enabled', 'Audit Logging', 'Audit log functionality', 'flag', '{"enabled": false}', 'active'),
    ('audit_export', 'Export Audit Logs', 'Export audit log data', 'flag', '{"enabled": false}', 'active'),
    -- Phase 2 Agency features
    ('agency_enabled', 'Agency Mode', 'Agency functionality enabled', 'flag', '{"enabled": false}', 'active'),
    ('agency_client_management', 'Client Management', 'Manage agency clients', 'flag', '{"enabled": false}', 'active'),
    ('agency_whitelabel', 'White-label Branding', 'White-label customization', 'flag', '{"enabled": false}', 'active'),
    ('agency_client_limits', 'Client Limit', 'Agency client count limit', 'limit', '{"value": 0}', 'active'),
    -- Phase 2 Enterprise features
    ('sso_saml', 'SSO/SAML Authentication', 'SAML-based SSO', 'flag', '{"enabled": false}', 'active'),
    ('support_priority', 'Priority Support', 'Priority customer support', 'flag', '{"enabled": false}', 'active'),
    ('data_residency', 'Data Residency Controls', 'Data location controls', 'flag', '{"enabled": false}', 'active'),
    ('enterprise_limits', 'Enterprise Quotas', 'Enterprise-grade limits', 'limit', '{"value": 0}', 'active'),
    -- Drift features
    ('drift_incidents', 'Drift Incidents', 'Create drift incident tickets', 'flag', '{"enabled": false}', 'active')
    ON CONFLICT (name) DO UPDATE SET
        display_name = EXCLUDED.display_name,
        description = EXCLUDED.description,
        type = EXCLUDED.type,
        default_value = EXCLUDED.default_value,
        updated_at = NOW();
    ''')

    # Seed plan_features table for all plans
    # First, create the free plan features
    op.execute('''
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
    ''')

    # Pro plan features
    op.execute('''
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
            -- Disabled flags
            ELSE '{"enabled": false}'::jsonb
        END
    FROM plans p
    CROSS JOIN features f
    WHERE p.name = 'pro'
    ON CONFLICT (plan_id, feature_id) DO UPDATE SET
        value = EXCLUDED.value,
        updated_at = NOW();
    ''')

    # Agency plan features
    op.execute('''
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
    ''')

    # Enterprise plan features (all features enabled/high limits)
    op.execute('''
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
    ''')


def downgrade() -> None:
    op.execute('''
    DROP TABLE IF EXISTS plan_features CASCADE;
    DROP TABLE IF EXISTS features CASCADE;
    ''')
