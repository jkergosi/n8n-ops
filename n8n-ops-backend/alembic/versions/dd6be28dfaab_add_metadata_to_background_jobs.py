"""add_metadata_to_background_jobs

Revision ID: dd6be28dfaab
Revises: f1b00536558e
Create Date: 2026-01-06 15:50:07.527169

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dd6be28dfaab'
down_revision = 'f1b00536558e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add metadata column to background_jobs table
    op.execute("""
        ALTER TABLE background_jobs
        ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb
    """)

    # Add comment for documentation
    op.execute("""
        COMMENT ON COLUMN background_jobs.metadata IS 'Additional metadata for the job'
    """)


def downgrade() -> None:
    # Remove metadata column from background_jobs table
    op.execute("""
        ALTER TABLE background_jobs
        DROP COLUMN IF EXISTS metadata
    """)
