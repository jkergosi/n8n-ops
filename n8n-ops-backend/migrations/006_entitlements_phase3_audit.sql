-- ============================================================================
-- Phase 3: Audit Logging Tables
-- Tracks configuration changes and access events for entitlements
-- ============================================================================

-- ============================================================================
-- Feature Config Audit - tracks ALL configuration changes
-- ============================================================================
CREATE TABLE IF NOT EXISTS feature_config_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL,

    -- What changed
    entity_type TEXT NOT NULL,  -- 'plan_feature', 'tenant_plan', 'tenant_override'
    entity_id UUID NOT NULL,    -- ID of the changed record
    feature_key TEXT,           -- Feature key if applicable

    -- Change details
    action TEXT NOT NULL,       -- 'create', 'update', 'delete'
    old_value JSONB,            -- Previous state (null for creates)
    new_value JSONB,            -- New state (null for deletes)

    -- Who and when
    changed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    changed_at TIMESTAMPTZ DEFAULT NOW(),

    -- Context
    reason TEXT,                -- Admin-provided reason for change
    ip_address TEXT,            -- Request IP address
    user_agent TEXT             -- Request user agent
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_feature_config_audit_tenant_id
    ON feature_config_audit(tenant_id);
CREATE INDEX IF NOT EXISTS idx_feature_config_audit_entity_type
    ON feature_config_audit(entity_type);
CREATE INDEX IF NOT EXISTS idx_feature_config_audit_feature_key
    ON feature_config_audit(feature_key);
CREATE INDEX IF NOT EXISTS idx_feature_config_audit_changed_at
    ON feature_config_audit(changed_at DESC);
CREATE INDEX IF NOT EXISTS idx_feature_config_audit_changed_by
    ON feature_config_audit(changed_by);

-- ============================================================================
-- Feature Access Log - tracks enforcement events (denials, limit hits)
-- ============================================================================
CREATE TABLE IF NOT EXISTS feature_access_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,

    -- What was accessed
    feature_key TEXT NOT NULL,

    -- Access details
    access_type TEXT NOT NULL,      -- 'flag_check', 'limit_check'
    result TEXT NOT NULL,           -- 'allowed', 'denied', 'limit_exceeded'

    -- Context for limits
    current_value INTEGER,          -- Current usage count (for limits)
    limit_value INTEGER,            -- The limit that was checked

    -- Request context
    endpoint TEXT,                  -- API endpoint that triggered check
    resource_type TEXT,             -- Type of resource being accessed
    resource_id TEXT,               -- ID of resource being accessed

    -- When
    accessed_at TIMESTAMPTZ DEFAULT NOW(),

    -- Additional context
    ip_address TEXT,
    user_agent TEXT
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_feature_access_log_tenant_id
    ON feature_access_log(tenant_id);
CREATE INDEX IF NOT EXISTS idx_feature_access_log_user_id
    ON feature_access_log(user_id);
CREATE INDEX IF NOT EXISTS idx_feature_access_log_feature_key
    ON feature_access_log(feature_key);
CREATE INDEX IF NOT EXISTS idx_feature_access_log_result
    ON feature_access_log(result);
CREATE INDEX IF NOT EXISTS idx_feature_access_log_accessed_at
    ON feature_access_log(accessed_at DESC);

-- Composite index for common queries (tenant + feature + time)
CREATE INDEX IF NOT EXISTS idx_feature_access_log_tenant_feature_time
    ON feature_access_log(tenant_id, feature_key, accessed_at DESC);

-- Index for denied access analysis
CREATE INDEX IF NOT EXISTS idx_feature_access_log_denials
    ON feature_access_log(tenant_id, accessed_at DESC)
    WHERE result IN ('denied', 'limit_exceeded');

-- ============================================================================
-- Automatic Audit Triggers for tenant_plans changes
-- ============================================================================
CREATE OR REPLACE FUNCTION audit_tenant_plan_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO feature_config_audit (
            tenant_id, entity_type, entity_id, action, new_value, changed_at
        ) VALUES (
            NEW.tenant_id, 'tenant_plan', NEW.id, 'create',
            jsonb_build_object('plan_id', NEW.plan_id, 'is_active', NEW.is_active),
            NOW()
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        -- Only audit if plan_id or is_active changed
        IF OLD.plan_id IS DISTINCT FROM NEW.plan_id OR OLD.is_active IS DISTINCT FROM NEW.is_active THEN
            INSERT INTO feature_config_audit (
                tenant_id, entity_type, entity_id, action, old_value, new_value, changed_at
            ) VALUES (
                NEW.tenant_id, 'tenant_plan', NEW.id, 'update',
                jsonb_build_object('plan_id', OLD.plan_id, 'is_active', OLD.is_active),
                jsonb_build_object('plan_id', NEW.plan_id, 'is_active', NEW.is_active),
                NOW()
            );
        END IF;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO feature_config_audit (
            tenant_id, entity_type, entity_id, action, old_value, changed_at
        ) VALUES (
            OLD.tenant_id, 'tenant_plan', OLD.id, 'delete',
            jsonb_build_object('plan_id', OLD.plan_id, 'is_active', OLD.is_active),
            NOW()
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_audit_tenant_plan ON tenant_plans;
CREATE TRIGGER trigger_audit_tenant_plan
    AFTER INSERT OR UPDATE OR DELETE ON tenant_plans
    FOR EACH ROW EXECUTE FUNCTION audit_tenant_plan_changes();

-- ============================================================================
-- Automatic Audit Triggers for tenant_feature_overrides changes
-- ============================================================================
CREATE OR REPLACE FUNCTION audit_tenant_override_changes()
RETURNS TRIGGER AS $$
DECLARE
    v_feature_key TEXT;
BEGIN
    -- Get feature key for the audit record
    IF TG_OP = 'DELETE' THEN
        SELECT key INTO v_feature_key FROM features WHERE id = OLD.feature_id;
    ELSE
        SELECT key INTO v_feature_key FROM features WHERE id = NEW.feature_id;
    END IF;

    IF TG_OP = 'INSERT' THEN
        INSERT INTO feature_config_audit (
            tenant_id, entity_type, entity_id, feature_key, action,
            new_value, changed_by, reason, changed_at
        ) VALUES (
            NEW.tenant_id, 'tenant_override', NEW.id, v_feature_key, 'create',
            jsonb_build_object(
                'value', NEW.value,
                'is_active', NEW.is_active,
                'expires_at', NEW.expires_at
            ),
            NEW.created_by, NEW.reason, NOW()
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO feature_config_audit (
            tenant_id, entity_type, entity_id, feature_key, action,
            old_value, new_value, changed_at
        ) VALUES (
            NEW.tenant_id, 'tenant_override', NEW.id, v_feature_key, 'update',
            jsonb_build_object(
                'value', OLD.value,
                'is_active', OLD.is_active,
                'expires_at', OLD.expires_at
            ),
            jsonb_build_object(
                'value', NEW.value,
                'is_active', NEW.is_active,
                'expires_at', NEW.expires_at
            ),
            NOW()
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO feature_config_audit (
            tenant_id, entity_type, entity_id, feature_key, action,
            old_value, changed_at
        ) VALUES (
            OLD.tenant_id, 'tenant_override', OLD.id, v_feature_key, 'delete',
            jsonb_build_object(
                'value', OLD.value,
                'is_active', OLD.is_active,
                'expires_at', OLD.expires_at
            ),
            NOW()
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_audit_tenant_override ON tenant_feature_overrides;
CREATE TRIGGER trigger_audit_tenant_override
    AFTER INSERT OR UPDATE OR DELETE ON tenant_feature_overrides
    FOR EACH ROW EXECUTE FUNCTION audit_tenant_override_changes();

