-- Additional tables for Billing and Teams functionality

-- ============================================================================
-- SUBSCRIPTION PLANS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS subscription_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    price_monthly DECIMAL(10, 2) NOT NULL,
    price_yearly DECIMAL(10, 2),
    stripe_price_id_monthly VARCHAR(255),
    stripe_price_id_yearly VARCHAR(255),
    stripe_product_id VARCHAR(255),
    max_environments INTEGER DEFAULT 1,
    max_team_members INTEGER DEFAULT 1,
    max_workflows INTEGER,
    features JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- SUBSCRIPTIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE UNIQUE,
    plan_id UUID REFERENCES subscription_plans(id),
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'canceled', 'past_due', 'unpaid', 'trialing')),
    billing_cycle VARCHAR(20) DEFAULT 'monthly' CHECK (billing_cycle IN ('monthly', 'yearly')),
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    cancel_at_period_end BOOLEAN DEFAULT false,
    canceled_at TIMESTAMP WITH TIME ZONE,
    trial_end TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- PAYMENT HISTORY TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS payment_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES subscriptions(id),
    stripe_payment_intent_id VARCHAR(255),
    stripe_invoice_id VARCHAR(255),
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(50) CHECK (status IN ('succeeded', 'failed', 'pending', 'refunded')),
    payment_method VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_subscriptions_tenant ON subscriptions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_customer ON subscriptions(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_subscription ON subscriptions(stripe_subscription_id);
CREATE INDEX IF NOT EXISTS idx_payment_history_tenant ON payment_history(tenant_id);
CREATE INDEX IF NOT EXISTS idx_payment_history_subscription ON payment_history(subscription_id);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

DROP TRIGGER IF EXISTS update_subscription_plans_updated_at ON subscription_plans;
CREATE TRIGGER update_subscription_plans_updated_at BEFORE UPDATE ON subscription_plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_subscriptions_updated_at ON subscriptions;
CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SEED DATA FOR SUBSCRIPTION PLANS
-- ============================================================================

INSERT INTO subscription_plans (name, display_name, description, price_monthly, price_yearly, max_environments, max_team_members, max_workflows, features)
VALUES
    (
        'free',
        'Free',
        'Perfect for individuals getting started with n8n workflow management',
        0.00,
        0.00,
        1,
        1,
        10,
        '{"environments": 1, "team_members": 1, "workflows": 10, "github_sync": false, "snapshots": true, "deployments": false, "scheduled_backups": false, "priority_support": false}'::jsonb
    ),
    (
        'pro',
        'Pro',
        'For teams that need advanced workflow management and collaboration',
        29.00,
        290.00,
        3,
        5,
        NULL,
        '{"environments": 3, "team_members": 5, "workflows": "unlimited", "github_sync": true, "snapshots": true, "deployments": true, "scheduled_backups": true, "priority_support": true}'::jsonb
    ),
    (
        'enterprise',
        'Enterprise',
        'For organizations requiring custom solutions and dedicated support',
        99.00,
        990.00,
        NULL,
        NULL,
        NULL,
        '{"environments": "unlimited", "team_members": "unlimited", "workflows": "unlimited", "github_sync": true, "snapshots": true, "deployments": true, "scheduled_backups": true, "priority_support": true, "sso": true, "custom_roles": true, "audit_logs": true}'::jsonb
    )
ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    price_monthly = EXCLUDED.price_monthly,
    price_yearly = EXCLUDED.price_yearly,
    max_environments = EXCLUDED.max_environments,
    max_team_members = EXCLUDED.max_team_members,
    max_workflows = EXCLUDED.max_workflows,
    features = EXCLUDED.features;

-- ============================================================================
-- CREATE SUBSCRIPTIONS FOR EXISTING TENANTS
-- ============================================================================

-- Create subscription for test tenant (Pro plan)
INSERT INTO subscriptions (tenant_id, plan_id, status, billing_cycle, current_period_start, current_period_end)
SELECT
    t.id,
    sp.id,
    'active',
    'monthly',
    NOW(),
    NOW() + INTERVAL '1 month'
FROM tenants t
CROSS JOIN subscription_plans sp
WHERE t.id = '00000000-0000-0000-0000-000000000000'
  AND sp.name = 'pro'
ON CONFLICT (tenant_id) DO NOTHING;

-- Update tenant subscription_tier to match plan
UPDATE tenants t
SET subscription_tier = sp.name
FROM subscriptions s
JOIN subscription_plans sp ON s.plan_id = sp.id
WHERE t.id = s.tenant_id;

-- ============================================================================
-- SAMPLE PAYMENT HISTORY
-- ============================================================================

INSERT INTO payment_history (tenant_id, subscription_id, amount, currency, status, payment_method, description)
SELECT
    '00000000-0000-0000-0000-000000000000',
    s.id,
    29.00,
    'USD',
    'succeeded',
    'card',
    'Pro Plan - Monthly subscription'
FROM subscriptions s
WHERE s.tenant_id = '00000000-0000-0000-0000-000000000000'
LIMIT 1
ON CONFLICT DO NOTHING;

-- Add a past payment
INSERT INTO payment_history (tenant_id, subscription_id, amount, currency, status, payment_method, description, created_at)
SELECT
    '00000000-0000-0000-0000-000000000000',
    s.id,
    29.00,
    'USD',
    'succeeded',
    'card',
    'Pro Plan - Monthly subscription',
    NOW() - INTERVAL '1 month'
FROM subscriptions s
WHERE s.tenant_id = '00000000-0000-0000-0000-000000000000'
LIMIT 1
ON CONFLICT DO NOTHING;

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to check if tenant has reached team member limit
CREATE OR REPLACE FUNCTION check_team_member_limit()
RETURNS TRIGGER AS $$
DECLARE
    member_count INTEGER;
    max_members INTEGER;
BEGIN
    -- Get current member count
    SELECT COUNT(*) INTO member_count
    FROM users
    WHERE tenant_id = NEW.tenant_id AND status = 'active';

    -- Get max members allowed for tenant's plan
    SELECT sp.max_team_members INTO max_members
    FROM subscriptions s
    JOIN subscription_plans sp ON s.plan_id = sp.id
    WHERE s.tenant_id = NEW.tenant_id;

    -- Check limit (NULL means unlimited)
    IF max_members IS NOT NULL AND member_count >= max_members THEN
        RAISE EXCEPTION 'Team member limit reached. Upgrade your plan to add more members.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to enforce team member limit
DROP TRIGGER IF EXISTS enforce_team_member_limit ON users;
CREATE TRIGGER enforce_team_member_limit
    BEFORE INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION check_team_member_limit();

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- SELECT * FROM subscription_plans;
-- SELECT * FROM subscriptions;
-- SELECT * FROM payment_history;
