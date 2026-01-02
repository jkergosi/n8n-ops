"""ensure_agency_plan_in_billing

Revision ID: c574200bc3db
Revises: '7c71b22483d5'
Create Date: 2025-12-31 18:32:27

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c574200bc3db'
down_revision = '7c71b22483d5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('''
    -- Ensure Agency exists in entitlements plans table
    UPDATE plans
    SET display_name = 'Agency',
        description = 'For agencies managing multiple clients',
        is_active = true,
        updated_at = now()
    WHERE name = 'agency';
    
    INSERT INTO plans (name, display_name, description, sort_order, is_active, created_at, updated_at)
    SELECT 'agency', 'Agency', 'For agencies managing multiple clients', 30, true, now(), now()
    WHERE NOT EXISTS (SELECT 1 FROM plans WHERE name = 'agency');
    
    -- Ensure Agency exists in billing subscription_plans table (drives Billing page Available Plans)
    UPDATE subscription_plans
    SET display_name = 'Agency',
        description = 'For agencies managing multiple clients',
        price_monthly = 149.00,
        price_yearly = 1490.00,
        is_active = true,
        features = '{
          "max_environments": "unlimited",
          "max_team_members": "unlimited",
          "github_backup": "scheduled",
          "github_restore": true,
          "scheduled_backup": true,
          "environment_promotion": "manual",
          "credential_remapping": false,
          "workflow_diff": true,
          "workflow_lifecycle": true,
          "execution_metrics": "advanced",
          "alerting": "basic",
          "role_based_access": true,
          "audit_logs": "full",
          "secret_vault": false,
          "sso_scim": false,
          "compliance_tools": false,
          "environment_protection": false,
          "support": "priority"
        }'::jsonb
    WHERE name = 'agency';
    
    INSERT INTO subscription_plans (
      name,
      display_name,
      description,
      price_monthly,
      price_yearly,
      stripe_price_id_monthly,
      stripe_price_id_yearly,
      features,
      max_environments,
      max_team_members,
      max_workflows,
      is_active
    )
    SELECT
      'agency',
      'Agency',
      'For agencies managing multiple clients',
      149.00,
      1490.00,
      NULL,
      NULL,
      '{
        "max_environments": "unlimited",
        "max_team_members": "unlimited",
        "github_backup": "scheduled",
        "github_restore": true,
        "scheduled_backup": true,
        "environment_promotion": "manual",
        "credential_remapping": false,
        "workflow_diff": true,
        "workflow_lifecycle": true,
        "execution_metrics": "advanced",
        "alerting": "basic",
        "role_based_access": true,
        "audit_logs": "full",
        "secret_vault": false,
        "sso_scim": false,
        "compliance_tools": false,
        "environment_protection": false,
        "support": "priority"
      }'::jsonb,
      NULL,
      NULL,
      NULL,
      true
    WHERE NOT EXISTS (SELECT 1 FROM subscription_plans WHERE name = 'agency');
    ''')


def downgrade() -> None:
    pass

