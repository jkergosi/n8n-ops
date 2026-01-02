"""supabase_auth_migration

Revision ID: b3da68cf4d15
Revises: 947a226f2ac2
Create Date: 2026-01-01

Migrate from Auth0 to Supabase authentication:
- Rename auth0_id column to supabase_auth_id
- Add can_be_impersonated column for admin impersonation feature
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b3da68cf4d15'
down_revision = '947a226f2ac2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename auth0_id to supabase_auth_id
    op.execute('''
    ALTER TABLE users RENAME COLUMN auth0_id TO supabase_auth_id;
    ''')

    # Add impersonation control column
    op.execute('''
    ALTER TABLE users ADD COLUMN IF NOT EXISTS can_be_impersonated BOOLEAN DEFAULT true;
    ''')


def downgrade() -> None:
    # Remove impersonation column
    op.execute('''
    ALTER TABLE users DROP COLUMN IF EXISTS can_be_impersonated;
    ''')

    # Rename back to auth0_id
    op.execute('''
    ALTER TABLE users RENAME COLUMN supabase_auth_id TO auth0_id;
    ''')
