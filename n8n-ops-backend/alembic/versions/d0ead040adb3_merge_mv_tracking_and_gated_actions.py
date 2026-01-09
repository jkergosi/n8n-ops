"""merge_mv_tracking_and_gated_actions

Revision ID: d0ead040adb3
Revises: 20260108_gated_actions, 20260108_mv_tracking
Create Date: 2026-01-08 18:28:16.131674

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd0ead040adb3'
down_revision = ('20260108_gated_actions', '20260108_mv_tracking')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
