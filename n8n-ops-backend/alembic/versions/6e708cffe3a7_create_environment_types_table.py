"""create_environment_types_table

Revision ID: 6e708cffe3a7
Revises: 119481472460
Create Date: 2026-01-03 15:10:36.519034

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '6e708cffe3a7'
down_revision = '119481472460'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create environment_types table
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.environment_types (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            key TEXT NOT NULL,
            label TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)

    # Create unique index on tenant_id + key
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS environment_types_tenant_key_unique
        ON public.environment_types (tenant_id, key);
    """)

    # Create index for efficient sorting
    op.execute("""
        CREATE INDEX IF NOT EXISTS environment_types_tenant_sort_idx
        ON public.environment_types (tenant_id, sort_order);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS environment_types_tenant_sort_idx;")
    op.execute("DROP INDEX IF EXISTS environment_types_tenant_key_unique;")
    op.execute("DROP TABLE IF EXISTS public.environment_types;")
