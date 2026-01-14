"""sync_tenant_plans_from_provider_subscriptions

Revision ID: af5ff910eede
Revises: 34cb67ed5c2a
Create Date: 2026-01-04 14:00:00.000000

This migration syncs the tenant_plans table from tenant_provider_subscriptions.
It ensures that every tenant has a tenant_plans record that matches their
highest-tier provider subscription (for backwards compatibility with the
entitlements system while supporting multi-provider).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'af5ff910eede'
down_revision = '34cb67ed5c2a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: For tenants WITH provider subscriptions but WITHOUT tenant_plans records,
    # create tenant_plans records from their provider subscription plan
    op.execute("""
        INSERT INTO tenant_plans (id, tenant_id, plan_id, is_active, entitlements_version, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            tps.tenant_id,
            p.id,
            true,
            1,
            NOW(),
            NOW()
        FROM tenant_provider_subscriptions tps
        JOIN provider_plans pp ON pp.id = tps.plan_id
        JOIN plans p ON LOWER(p.name) = LOWER(pp.name)
        WHERE tps.status = 'active'
        AND NOT EXISTS (
            SELECT 1 FROM tenant_plans tp
            WHERE tp.tenant_id = tps.tenant_id
            AND tp.is_active = true
        )
        ON CONFLICT (tenant_id) WHERE is_active = true DO NOTHING;
    """)

    # Step 2: Update existing tenant_plans to match provider subscription plan
    # (for cases where tenant_plans exists but with wrong plan)
    op.execute("""
        UPDATE tenant_plans tp
        SET
            plan_id = p.id,
            entitlements_version = tp.entitlements_version + 1,
            updated_at = NOW()
        FROM tenant_provider_subscriptions tps
        JOIN provider_plans pp ON pp.id = tps.plan_id
        JOIN plans p ON LOWER(p.name) = LOWER(pp.name)
        WHERE tp.tenant_id = tps.tenant_id
        AND tp.is_active = true
        AND tps.status = 'active'
        AND tp.plan_id != p.id;
    """)

    # Step 3: Also sync tenants.subscription_tier from provider subscriptions
    # (keep the legacy field in sync for backwards compatibility)
    op.execute("""
        UPDATE tenants t
        SET
            subscription_tier = pp.name,
            updated_at = NOW()
        FROM tenant_provider_subscriptions tps
        JOIN provider_plans pp ON pp.id = tps.plan_id
        WHERE t.id = tps.tenant_id
        AND tps.status = 'active'
        AND LOWER(t.subscription_tier) != LOWER(pp.name);
    """)


def downgrade() -> None:
    # No safe way to downgrade - data sync is a one-way operation
    pass
