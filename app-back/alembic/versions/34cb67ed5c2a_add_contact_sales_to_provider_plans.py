"""add_contact_sales_to_provider_plans

Revision ID: 34cb67ed5c2a
Revises: 6e708cffe3a7
Create Date: 2026-01-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '34cb67ed5c2a'
down_revision = '6e708cffe3a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add contact_sales column to provider_plans if it doesn't exist
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'provider_plans'
                AND column_name = 'contact_sales'
            ) THEN
                ALTER TABLE provider_plans ADD COLUMN contact_sales BOOLEAN NOT NULL DEFAULT false;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Remove contact_sales column from provider_plans
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'provider_plans'
                AND column_name = 'contact_sales'
            ) THEN
                ALTER TABLE provider_plans DROP COLUMN contact_sales;
            END IF;
        END $$;
    """)
