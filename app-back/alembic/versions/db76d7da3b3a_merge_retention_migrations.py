"""merge_retention_migrations

Revision ID: db76d7da3b3a
Revises: 20260116_activity_retention_idx, 20260116_add_deployment_retention
Create Date: 2026-01-16 16:29:00.030193

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'db76d7da3b3a'
down_revision = ('20260116_activity_retention_idx', '20260116_add_deployment_retention')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
