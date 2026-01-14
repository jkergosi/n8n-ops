"""create_tenant_admin_list_view

Revision ID: 119481472460
Revises: '803d75a635c9'
Create Date: 2026-01-03 14:34:33

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '119481472460'
down_revision = '803d75a635c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('''
    CREATE OR REPLACE VIEW tenant_admin_list AS\nSELECT\n  t.*,\n  COALESCE(w.workflow_count, 0) AS workflow_count,\n  COALESCE(e.environment_count, 0) AS environment_count,\n  COALESCE(u.user_count, 0) AS user_count\nFROM tenants t\nLEFT JOIN (\n  SELECT tenant_id, COUNT(*)::int AS workflow_count\n  FROM workflows\n  WHERE is_deleted = false\n  GROUP BY tenant_id\n) w ON w.tenant_id = t.id\nLEFT JOIN (\n  SELECT tenant_id, COUNT(*)::int AS environment_count\n  FROM environments\n  GROUP BY tenant_id\n) e ON e.tenant_id = t.id\nLEFT JOIN (\n  SELECT tenant_id, COUNT(*)::int AS user_count\n  FROM users\n  GROUP BY tenant_id\n) u ON u.tenant_id = t.id;
    ''')


def downgrade() -> None:
    op.execute('DROP VIEW IF EXISTS tenant_admin_list;')

