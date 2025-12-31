"""Add environment_class to environments table

Revision ID: a1b2c3d4e5f6
Revises: '76c6e9c7f4fe'
Create Date: 2025-12-30

IMPORTANT: environment_class is the ONLY source of truth for policy enforcement.
After this migration, NEVER infer environment class at runtime.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '76c6e9c7f4fe'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add environment_class column with default 'dev'
    op.execute('''
    ALTER TABLE environments ADD COLUMN IF NOT EXISTS environment_class TEXT NOT NULL DEFAULT 'dev';
    ''')

    # Migrate existing data based on environment NAME field (not n8n_type!)
    # n8n_type is a provider type, not an environment classification
    op.execute('''
    UPDATE environments
    SET environment_class = CASE
        WHEN LOWER(n8n_name) LIKE '%prod%' OR LOWER(n8n_name) = 'live' THEN 'production'
        WHEN LOWER(n8n_name) LIKE '%stag%' OR LOWER(n8n_name) = 'uat' OR LOWER(n8n_name) = 'qa' THEN 'staging'
        ELSE 'dev'
    END
    WHERE environment_class = 'dev';
    ''')

    # NOTE: After migration, users should verify environment_class is correct
    # via admin UI. The inferred value may need manual correction.


def downgrade() -> None:
    op.execute('''
    ALTER TABLE environments DROP COLUMN IF EXISTS environment_class;
    ''')
