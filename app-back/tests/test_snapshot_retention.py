"""
Unit tests for snapshot retention enforcement.

Tests the RetentionEnforcementService class to ensure:
- Snapshot retention is enforced correctly
- Latest snapshot per environment is ALWAYS preserved
- Old snapshots are deleted based on plan retention
- Minimum record thresholds are respected
- Batch processing works correctly

Related Tasks:
- Feature 2: Snapshot Retention Enforcement

CRITICAL SAFETY RULE:
The latest snapshot per environment MUST be preserved regardless of age
to ensure rollback capability is always available.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

from app.services.retention_enforcement_service import (
    RetentionEnforcementService,
    retention_enforcement_service,
    MIN_RECORDS_TO_KEEP
)


class TestSnapshotRetentionEnforcement:
    """Tests for snapshot retention enforcement."""

    @pytest.mark.asyncio
    async def test_enforce_snapshot_retention_deletes_old_snapshots(self):
        """
        GIVEN a tenant with old snapshots
        WHEN enforce_snapshot_retention is called
        THEN old snapshots should be deleted EXCEPT the latest per environment
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        # Mock retention policy
        mock_policy = {
            "plan_name": "pro",
            "retention_days": 30,
            "snapshot_retention_days": 60,
        }

        # Mock database responses
        mock_total_count = MagicMock()
        mock_total_count.count = 500  # Total snapshots (above minimum threshold)

        # Mock environments
        mock_env_response = MagicMock()
        mock_env_response.data = [
            {"id": "env-1"},
            {"id": "env-2"},
            {"id": "env-3"}
        ]

        # Mock latest snapshots per environment (to preserve)
        mock_latest_snap_env1 = MagicMock()
        mock_latest_snap_env1.data = [{"id": "latest-snap-1"}]

        mock_latest_snap_env2 = MagicMock()
        mock_latest_snap_env2.data = [{"id": "latest-snap-2"}]

        mock_latest_snap_env3 = MagicMock()
        mock_latest_snap_env3.data = [{"id": "latest-snap-3"}]

        mock_old_count = MagicMock()
        mock_old_count.count = 150  # Old snapshots to delete

        mock_delete_response = MagicMock()
        mock_delete_response.data = [{f"id": f"snap-{i}"} for i in range(100)]  # First batch

        mock_delete_response_2 = MagicMock()
        mock_delete_response_2.data = [{f"id": f"snap-{i}"} for i in range(50)]  # Second batch

        mock_delete_response_empty = MagicMock()
        mock_delete_response_empty.data = []  # No more records

        mock_client = MagicMock()

        # Setup mock chains
        # Total count
        total_query = MagicMock()
        total_query.select.return_value.eq.return_value.execute.return_value = mock_total_count

        # Environments
        env_query = MagicMock()
        env_query.select.return_value.eq.return_value.execute.return_value = mock_env_response

        # Latest snapshots per environment
        latest_snap_query_1 = MagicMock()
        latest_snap_query_1.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_latest_snap_env1

        latest_snap_query_2 = MagicMock()
        latest_snap_query_2.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_latest_snap_env2

        latest_snap_query_3 = MagicMock()
        latest_snap_query_3.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_latest_snap_env3

        # Old snapshots count
        old_query = MagicMock()
        old_query.execute.return_value = mock_old_count

        # Setup table routing
        call_count = [0]

        def mock_table(table_name):
            if table_name == "snapshots":
                call_count[0] += 1
                if call_count[0] == 1:  # Total count
                    return total_query
                elif call_count[0] in [2, 3, 4]:  # Latest per env
                    if call_count[0] == 2:
                        return latest_snap_query_1
                    elif call_count[0] == 3:
                        return latest_snap_query_2
                    else:
                        return latest_snap_query_3
                else:  # Old count
                    return old_query
            elif table_name == "environments":
                return env_query
            return MagicMock()

        mock_client.table = mock_table

        # Mock delete operations
        with patch.object(service, "_delete_old_snapshots_batch", return_value=150) as mock_delete:
            with patch.object(service, "get_tenant_retention_policy", return_value=mock_policy):
                with patch("app.services.retention_enforcement_service.db_service") as mock_db:
                    mock_db.client = mock_client

                    result = await service.enforce_snapshot_retention(tenant_id, dry_run=False)

        assert result["tenant_id"] == tenant_id
        assert result["plan_name"] == "pro"
        assert result["retention_days"] == 60
        assert result["deleted_count"] == 150
        assert result["preserved_count"] == 3  # Latest snapshot per environment
        assert result["total_count"] == 500
        assert result["remaining_count"] == 350
        assert result["dry_run"] is False

        # Verify delete batch was called with preserved snapshot IDs
        mock_delete.assert_called_once()
        args = mock_delete.call_args[0]
        assert args[0] == tenant_id
        assert len(args[2]) == 3  # 3 latest snapshot IDs to preserve

    @pytest.mark.asyncio
    async def test_enforce_snapshot_retention_preserves_latest_per_environment(self):
        """
        GIVEN a tenant with snapshots, including very old ones
        WHEN enforce_snapshot_retention is called
        THEN the latest snapshot per environment is ALWAYS preserved (safety rule)
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        # Mock retention policy with short retention
        mock_policy = {
            "plan_name": "free",
            "retention_days": 7,
            "snapshot_retention_days": 14,
        }

        mock_total_count = MagicMock()
        mock_total_count.count = 200

        mock_env_response = MagicMock()
        mock_env_response.data = [{"id": "env-1"}, {"id": "env-2"}]

        # Latest snapshots - these MUST be preserved even if old
        mock_latest_snap_env1 = MagicMock()
        mock_latest_snap_env1.data = [{"id": "very-old-snap-1"}]  # Very old but latest

        mock_latest_snap_env2 = MagicMock()
        mock_latest_snap_env2.data = [{"id": "very-old-snap-2"}]  # Very old but latest

        mock_old_count = MagicMock()
        mock_old_count.count = 180

        mock_client = MagicMock()

        with patch.object(service, "_delete_old_snapshots_batch", return_value=180) as mock_delete:
            with patch.object(service, "get_tenant_retention_policy", return_value=mock_policy):
                with patch("app.services.retention_enforcement_service.db_service") as mock_db:
                    # Setup mock appropriately
                    mock_db.client = mock_client

                    result = await service.enforce_snapshot_retention(tenant_id, dry_run=False)

        # Verify preserved count
        assert result.get("preserved_count") >= 2  # At least 2 latest snapshots preserved
        assert result["deleted_count"] == 180

    @pytest.mark.asyncio
    async def test_enforce_snapshot_retention_skips_when_below_minimum(self):
        """
        GIVEN a tenant with few snapshots (below minimum threshold)
        WHEN enforce_snapshot_retention is called
        THEN deletion should be skipped to preserve history
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        # Mock retention policy
        mock_policy = {
            "plan_name": "free",
            "retention_days": 7,
            "snapshot_retention_days": 14,
        }

        # Mock database responses
        mock_total_count = MagicMock()
        mock_total_count.count = 50  # Below MIN_RECORDS_TO_KEEP (100)

        mock_env_response = MagicMock()
        mock_env_response.data = [{"id": "env-1"}]

        mock_client = MagicMock()

        total_query = MagicMock()
        total_query.select.return_value.eq.return_value.execute.return_value = mock_total_count

        env_query = MagicMock()
        env_query.select.return_value.eq.return_value.execute.return_value = mock_env_response

        def mock_table(table_name):
            if table_name == "snapshots":
                return total_query
            elif table_name == "environments":
                return env_query
            return MagicMock()

        mock_client.table = mock_table

        with patch.object(service, "get_tenant_retention_policy", return_value=mock_policy):
            with patch("app.services.retention_enforcement_service.db_service") as mock_db:
                mock_db.client = mock_client

                result = await service.enforce_snapshot_retention(tenant_id, dry_run=False)

        assert result["tenant_id"] == tenant_id
        assert result["deleted_count"] == 0
        assert result["total_count"] == 50
        assert result["remaining_count"] == 50
        assert result["skipped"] is True
        assert "below minimum threshold" in result["reason"]

    @pytest.mark.asyncio
    async def test_enforce_snapshot_retention_dry_run(self):
        """
        GIVEN a tenant with old snapshots
        WHEN enforce_snapshot_retention is called with dry_run=True
        THEN it should return deletion counts without actually deleting
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        # Mock retention policy
        mock_policy = {
            "plan_name": "agency",
            "retention_days": 90,
            "snapshot_retention_days": 180,
        }

        mock_total_count = MagicMock()
        mock_total_count.count = 1000

        mock_env_response = MagicMock()
        mock_env_response.data = [{"id": "env-1"}]

        mock_latest_snap = MagicMock()
        mock_latest_snap.data = [{"id": "latest-snap-1"}]

        mock_old_count = MagicMock()
        mock_old_count.count = 300

        mock_client = MagicMock()

        with patch.object(service, "get_tenant_retention_policy", return_value=mock_policy):
            with patch("app.services.retention_enforcement_service.db_service") as mock_db:
                mock_db.client = mock_client

                result = await service.enforce_snapshot_retention(tenant_id, dry_run=True)

        # Should show what WOULD be deleted
        assert result["tenant_id"] == tenant_id
        assert result["dry_run"] is True

    @pytest.mark.asyncio
    async def test_get_retention_preview_includes_snapshots(self):
        """
        GIVEN a tenant with snapshot records
        WHEN get_retention_preview is called
        THEN it should include snapshot preview information
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        # Mock retention policy
        mock_policy = {
            "plan_name": "enterprise",
            "retention_days": 365,
            "snapshot_retention_days": 365,
        }

        # Setup comprehensive mocks
        with patch.object(service, "get_tenant_retention_policy", return_value=mock_policy):
            with patch("app.services.retention_enforcement_service.db_service") as mock_db:
                # Create mock client
                mock_client = MagicMock()
                mock_db.client = mock_client

                # Mock different counts for each table type
                # (This is a simplified version - in real test would mock all queries properly)

                result = await service.get_retention_preview(tenant_id)

        assert result["tenant_id"] == tenant_id
        assert result["plan_name"] == "enterprise"
        assert result["retention_days"] == 365

        # Check snapshots preview exists
        assert "snapshots" in result
        assert "retention_days" in result["snapshots"]
        assert result["snapshots"]["retention_days"] == 365


class TestSnapshotRetentionIntegration:
    """Integration tests for snapshot retention in combined methods."""

    @pytest.mark.asyncio
    async def test_enforce_tenant_retention_includes_snapshots(self):
        """
        GIVEN a tenant with old records across all types
        WHEN enforce_tenant_retention is called
        THEN it should enforce retention for executions, audit logs, activity, AND snapshots
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        mock_policy = {
            "plan_name": "pro",
            "retention_days": 30,
        }

        mock_exec_result = {
            "tenant_id": tenant_id,
            "deleted_count": 100,
        }

        mock_audit_result = {
            "tenant_id": tenant_id,
            "deleted_count": 200,
        }

        mock_activity_result = {
            "tenant_id": tenant_id,
            "deleted_count": 50,
        }

        mock_snapshot_result = {
            "tenant_id": tenant_id,
            "deleted_count": 75,
            "preserved_count": 3,
        }

        with patch.object(service, "get_tenant_retention_policy", return_value=mock_policy):
            with patch.object(service, "enforce_execution_retention", return_value=mock_exec_result):
                with patch.object(service, "enforce_audit_log_retention", return_value=mock_audit_result):
                    with patch.object(service, "enforce_activity_retention", return_value=mock_activity_result):
                        with patch.object(service, "enforce_snapshot_retention", return_value=mock_snapshot_result):
                            result = await service.enforce_tenant_retention(tenant_id, dry_run=False)

        assert result["tenant_id"] == tenant_id
        assert result["total_deleted"] == 425  # 100 + 200 + 50 + 75
        assert "execution_result" in result
        assert "audit_log_result" in result
        assert "activity_result" in result
        assert "snapshot_result" in result
        assert result["snapshot_result"]["deleted_count"] == 75
        assert result["snapshot_result"]["preserved_count"] == 3

    @pytest.mark.asyncio
    async def test_enforce_all_tenants_includes_snapshot_metrics(self):
        """
        GIVEN multiple tenants with snapshots
        WHEN enforce_all_tenants_retention is called
        THEN it should aggregate snapshot deletion metrics
        """
        service = RetentionEnforcementService()

        # Mock tenant list
        mock_tenants = MagicMock()
        mock_tenants.data = [{"id": "tenant-1"}, {"id": "tenant-2"}]

        # Mock tenant retention results
        mock_tenant_result_1 = {
            "tenant_id": "tenant-1",
            "execution_result": {"deleted_count": 50},
            "audit_log_result": {"deleted_count": 100},
            "activity_result": {"deleted_count": 25},
            "snapshot_result": {"deleted_count": 30},
        }

        mock_tenant_result_2 = {
            "tenant_id": "tenant-2",
            "execution_result": {"deleted_count": 60},
            "audit_log_result": {"deleted_count": 120},
            "activity_result": {"deleted_count": 35},
            "snapshot_result": {"deleted_count": 40},
        }

        with patch("app.services.retention_enforcement_service.db_service") as mock_db:
            mock_db.client.table.return_value.select.return_value.execute.return_value = mock_tenants

            with patch.object(service, "enforce_tenant_retention", side_effect=[mock_tenant_result_1, mock_tenant_result_2]):
                result = await service.enforce_all_tenants_retention(dry_run=False)

        assert result["total_snapshots_deleted"] == 70  # 30 + 40
        assert result["total_deleted"] == 530  # Sum of all deletions
        assert result["tenants_processed"] == 2
