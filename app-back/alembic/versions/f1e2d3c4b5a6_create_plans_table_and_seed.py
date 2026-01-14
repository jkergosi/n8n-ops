"""create_plans_table_and_seed

Revision ID: f1e2d3c4b5a6
Revises: 'd27bdb540fcc'
Create Date: 2026-01-07 16:00:00

Creates the plans table required by the plan_features table and the billing API endpoints:
- GET /api/v1/billing/plan-features/all
- GET /api/v1/billing/plan-configurations

This table is separate from subscription_plans (which is used for billing/Stripe integration).
The plans table is used for the entitlements/features system.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f1e2d3c4b5a6'
down_revision = 'd27bdb540fcc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the plans table (for entitlements system, separate from subscription_plans)
    op.execute('''
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

    -- Create index for faster lookups
    CREATE INDEX IF NOT EXISTS idx_plans_name ON plans(name);
    CREATE INDEX IF NOT EXISTS idx_plans_is_active ON plans(is_active);
    CREATE INDEX IF NOT EXISTS idx_plans_sort_order ON plans(sort_order);
    ''')

    # Enable RLS on plans table
    op.execute('''
    ALTER TABLE plans ENABLE ROW LEVEL SECURITY;

    -- Plans table: public read access (needed for billing/entitlements APIs)
    DROP POLICY IF EXISTS "plans_select_policy" ON plans;
    CREATE POLICY "plans_select_policy" ON plans
        FOR SELECT USING (true);
    ''')

    # Seed the plans table with all plan tiers
    op.execute('''
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
    ''')


def downgrade() -> None:
    # Drop the plans table (CASCADE will remove any dependent objects)
    op.execute('''
    DROP TABLE IF EXISTS plans CASCADE;
    ''')
