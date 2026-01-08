"""add_impersonation_columns_to_audit_logs

Revision ID: 20260108_audit_imp_cols
Revises: 380513d302f0
Create Date: 2026-01-08

Adds impersonation tracking columns to audit_logs table to support dual-actor attribution.

This migration adds columns to track:
1. impersonation_session_id - Links audit entries to specific impersonation sessions
2. impersonated_user_id - The user being impersonated (effective user)
3. impersonated_user_email - Email of impersonated user for quick reference
4. impersonated_tenant_id - Tenant context of impersonated user

Security Pattern:
- actor_id represents the impersonator (platform admin who initiated the action)
- impersonated_user_id represents the effective user being impersonated
- tenant_id represents the effective tenant context (impersonated user's tenant)

This enables complete audit trail showing:
"Platform Admin X performed Action Y as User Z in Tenant W"
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260108_audit_imp_cols'
down_revision = '380513d302f0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add impersonation tracking columns to audit_logs table
    op.execute('''
        -- Add impersonation session ID
        ALTER TABLE audit_logs
        ADD COLUMN IF NOT EXISTS impersonation_session_id UUID;

        -- Add impersonated user details
        ALTER TABLE audit_logs
        ADD COLUMN IF NOT EXISTS impersonated_user_id UUID;

        ALTER TABLE audit_logs
        ADD COLUMN IF NOT EXISTS impersonated_user_email VARCHAR(255);

        ALTER TABLE audit_logs
        ADD COLUMN IF NOT EXISTS impersonated_tenant_id UUID;

        -- Add column comments for documentation
        COMMENT ON COLUMN audit_logs.impersonation_session_id IS
        'ID of platform_impersonation_sessions if this action was performed during impersonation. NULL for normal operations.';

        COMMENT ON COLUMN audit_logs.impersonated_user_id IS
        'ID of the user being impersonated (effective user). actor_id represents the impersonator (platform admin). NULL for normal operations.';

        COMMENT ON COLUMN audit_logs.impersonated_user_email IS
        'Email of the impersonated user for quick reference without JOIN. NULL for normal operations.';

        COMMENT ON COLUMN audit_logs.impersonated_tenant_id IS
        'Tenant ID of the impersonated user. Typically matches tenant_id field during impersonation. NULL for normal operations.';
    ''')

    # Add foreign key constraints
    op.execute('''
        -- Link to platform_impersonation_sessions table
        ALTER TABLE audit_logs
        ADD CONSTRAINT fk_audit_logs_impersonation_session
        FOREIGN KEY (impersonation_session_id)
        REFERENCES platform_impersonation_sessions(id)
        ON DELETE SET NULL;

        -- Link to users table for impersonated user
        ALTER TABLE audit_logs
        ADD CONSTRAINT fk_audit_logs_impersonated_user
        FOREIGN KEY (impersonated_user_id)
        REFERENCES users(id)
        ON DELETE SET NULL;

        -- Link to tenants table for impersonated tenant
        ALTER TABLE audit_logs
        ADD CONSTRAINT fk_audit_logs_impersonated_tenant
        FOREIGN KEY (impersonated_tenant_id)
        REFERENCES tenants(id)
        ON DELETE SET NULL;
    ''')


def downgrade() -> None:
    # Drop foreign key constraints first
    op.execute('''
        ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS fk_audit_logs_impersonated_tenant;
        ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS fk_audit_logs_impersonated_user;
        ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS fk_audit_logs_impersonation_session;
    ''')

    # Drop columns
    op.execute('''
        ALTER TABLE audit_logs DROP COLUMN IF EXISTS impersonated_tenant_id;
        ALTER TABLE audit_logs DROP COLUMN IF EXISTS impersonated_user_email;
        ALTER TABLE audit_logs DROP COLUMN IF EXISTS impersonated_user_id;
        ALTER TABLE audit_logs DROP COLUMN IF EXISTS impersonation_session_id;
    ''')
