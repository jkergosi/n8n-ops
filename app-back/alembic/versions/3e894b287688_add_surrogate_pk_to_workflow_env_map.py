"""add_surrogate_pk_to_workflow_env_map

Revision ID: 3e894b287688
Revises: 'dd6be28dfaab'
Create Date: 2026-01-06 17:24:12

Migration: 3e894b287688 - Add surrogate primary key to workflow_env_map
See: fix_sync_flow_untracked_handling plan
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '3e894b287688'
down_revision = 'dd6be28dfaab'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if id column already exists as PRIMARY KEY
    # If it does, skip this migration
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT COUNT(*) 
        FROM information_schema.columns 
        WHERE table_name = 'workflow_env_map' 
        AND column_name = 'id'
        AND table_schema = 'public'
    """))
    has_id_column = result.scalar() > 0
    
    if has_id_column:
        # Check if it's already a PRIMARY KEY
        result = conn.execute(sa.text("""
            SELECT COUNT(*) 
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name = 'workflow_env_map'
            AND tc.constraint_type = 'PRIMARY KEY'
            AND kcu.column_name = 'id'
            AND tc.table_schema = 'public'
        """))
        is_pk = result.scalar() > 0
        
        if is_pk:
            # Already has id as PK, skip migration
            return
    
    # Ensure UUID generator extension exists
    op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto;')
    
    # Add id column as nullable
    op.execute('ALTER TABLE workflow_env_map ADD COLUMN IF NOT EXISTS id UUID;')
    
    # Backfill IDs for existing rows
    op.execute('UPDATE workflow_env_map SET id = gen_random_uuid() WHERE id IS NULL;')
    
    # Set NOT NULL
    op.execute('ALTER TABLE workflow_env_map ALTER COLUMN id SET NOT NULL;')
    
    # Drop existing composite PK
    op.execute('ALTER TABLE workflow_env_map DROP CONSTRAINT IF EXISTS workflow_env_map_pkey;')
    
    # Add PK on id
    op.execute('ALTER TABLE workflow_env_map ADD PRIMARY KEY (id);')


def downgrade() -> None:
    # Drop the surrogate PK
    op.execute('ALTER TABLE workflow_env_map DROP CONSTRAINT IF EXISTS workflow_env_map_pkey;')
    
    # Drop id column
    op.execute('ALTER TABLE workflow_env_map DROP COLUMN IF EXISTS id;')
    
    # Restore composite PK
    op.execute('''
        ALTER TABLE workflow_env_map 
        ADD CONSTRAINT workflow_env_map_pkey 
        PRIMARY KEY (tenant_id, environment_id, canonical_id);
    ''')
