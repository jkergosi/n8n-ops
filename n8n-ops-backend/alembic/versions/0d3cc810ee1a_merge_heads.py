"""merge heads

Revision ID: 0d3cc810ee1a
Revises: add_drift_policies, b2c3d4e5f6g7
Create Date: 2025-12-30 15:56:21.642788

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0d3cc810ee1a'
down_revision = ('add_drift_policies', 'b2c3d4e5f6g7')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
