"""make_canonical_id_nullable_with_constraints

Revision ID: e5a52cb5bbc9
Revises: '94a957608da9'
Create Date: 2026-01-06 17:26:00

Migration: e5a52cb5bbc9 - Make canonical_id nullable and update constraints
See: fix_sync_flow_untracked_handling plan
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e5a52cb5bbc9'
down_revision = '94a957608da9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing foreign key constraint
    op.execute('ALTER TABLE workflow_env_map DROP CONSTRAINT IF EXISTS workflow_env_map_tenant_id_canonical_id_fkey;')
    
    # Make canonical_id nullable
    op.execute('ALTER TABLE workflow_env_map ALTER COLUMN canonical_id DROP NOT NULL;')
    
    # Re-add foreign key with ON DELETE SET NULL (not CASCADE, not DEFERRABLE)
    op.execute("""
        ALTER TABLE workflow_env_map 
        ADD CONSTRAINT workflow_env_map_canonical_id_fkey 
        FOREIGN KEY (tenant_id, canonical_id) 
        REFERENCES canonical_workflows(tenant_id, canonical_id) 
        ON DELETE SET NULL;
    """)
    
    # Add UNIQUE constraint on (tenant_id, environment_id, n8n_workflow_id)
    op.execute("""
        ALTER TABLE workflow_env_map 
        ADD CONSTRAINT workflow_env_map_tenant_env_n8n_unique 
        UNIQUE (tenant_id, environment_id, n8n_workflow_id);
    """)
    
    # Add partial unique index for canonical_id (only when NOT NULL) - this replaces the old composite PK constraint
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_workflow_env_map_canonical_partial 
        ON workflow_env_map(tenant_id, environment_id, canonical_id) 
        WHERE canonical_id IS NOT NULL;
    """)
    
    # Add index for untracked workflows (canonical_id IS NULL)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_workflow_env_map_untracked 
        ON workflow_env_map(tenant_id, environment_id) 
        WHERE canonical_id IS NULL;
    """)


def downgrade() -> None:
    # Drop indexes
    op.execute('DROP INDEX IF EXISTS idx_workflow_env_map_untracked;')
    op.execute('DROP INDEX IF EXISTS idx_workflow_env_map_canonical_partial;')
    
    # Drop unique constraint
    op.execute('ALTER TABLE workflow_env_map DROP CONSTRAINT IF EXISTS workflow_env_map_tenant_env_n8n_unique;')
    
    # Drop foreign key
    op.execute('ALTER TABLE workflow_env_map DROP CONSTRAINT IF EXISTS workflow_env_map_canonical_id_fkey;')
    
    # Make canonical_id NOT NULL again
    op.execute('ALTER TABLE workflow_env_map ALTER COLUMN canonical_id SET NOT NULL;')
    
    # Restore original foreign key with CASCADE
    op.execute("""
        ALTER TABLE workflow_env_map 
        ADD CONSTRAINT workflow_env_map_tenant_id_canonical_id_fkey 
        FOREIGN KEY (tenant_id, canonical_id) 
        REFERENCES canonical_workflows(tenant_id, canonical_id) 
        ON DELETE CASCADE;
    """)
