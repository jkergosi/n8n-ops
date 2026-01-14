"""Add archive fields to workflows table

Revision ID: b2c3d4e5f6g7
Revises: 'a1b2c3d4e5f6'
Create Date: 2025-12-30

Adds soft delete (archive) capability for workflows.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6g7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add archive fields to workflows table
    op.execute('''
    ALTER TABLE workflows ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT FALSE;
    ''')
    op.execute('''
    ALTER TABLE workflows ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP;
    ''')
    op.execute('''
    ALTER TABLE workflows ADD COLUMN IF NOT EXISTS archived_by TEXT;
    ''')

    # Create index for efficient filtering of non-archived workflows
    op.execute('''
    CREATE INDEX IF NOT EXISTS idx_workflows_is_archived ON workflows(is_archived);
    ''')


def downgrade() -> None:
    op.execute('''
    DROP INDEX IF EXISTS idx_workflows_is_archived;
    ''')
    op.execute('''
    ALTER TABLE workflows DROP COLUMN IF EXISTS archived_by;
    ''')
    op.execute('''
    ALTER TABLE workflows DROP COLUMN IF EXISTS archived_at;
    ''')
    op.execute('''
    ALTER TABLE workflows DROP COLUMN IF EXISTS is_archived;
    ''')
