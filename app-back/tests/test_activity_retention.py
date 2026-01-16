"""
Unit tests for activity retention enforcement.

Tests the RetentionEnforcementService class to ensure:
- Activity (background job) retention is enforced correctly
- Only completed/failed/cancelled jobs are deleted
- Running and pending jobs are preserved
- Minimum record thresholds are respected
- Batch processing works correctly

Related Tasks:
- Feature 1: Activity Retention Enforcement
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from app.services.retention_enforcement_service import (
    RetentionEnforcementService,
    retention_enforcement_service,
    MIN_RECORDS_TO_KEEP
)


class TestActivityRetentionEnforcement:
    """Tests for activity retention enforcement."""

    @pytest.mark.asyncio
    async def test_enforce_activity_retention_deletes_old_completed_jobs(self):
        """
        GIVEN a tenant with old completed background jobs
        WHEN enforce_activity_retention is called
        THEN old completed jobs should be deleted
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        # Mock retention policy
        mock_policy = {
            "plan_name": "pro",
            "retention_days": 30,
            "execution_retention_days": 30,
            "audit_log_retention_days": 30,
        }

        # Mock database responses
        mock_total_count = MagicMock()
        mock_total_count.count = 500  # Total jobs (above minimum threshold)

        mock_old_count = MagicMock()
        mock_old_count.count = 150  # Old jobs to delete

        mock_orphaned_count = MagicMock()
        mock_orphaned_count.count = 0  # No orphaned jobs

        mock_delete_response = MagicMock()
        mock_delete_response.data = [{"id": f"job-{i}"} for i in range(100)]  # First batch

        mock_delete_response_2 = MagicMock()
        mock_delete_response_2.data = [{"id": f"job-{i}"} for i in range(50)]  # Second batch

        mock_delete_response_empty = MagicMock()
        mock_delete_response_empty.data = []  # No more records

        mock_client = MagicMock()

        # Setup mock chain for total count
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_total_count

        # Setup mock chain for old count
        mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.lt.return_value.execute.return_value = mock_old_count

        # Setup mock chain for orphaned count
        mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.is_.return_value.execute.return_value = mock_orphaned_count

        # Setup mock chain for delete operations
        mock_client.table.return_value.delete.return_value.eq.return_value.in_.return_value.lt.return_value.limit.return_value.execute.side_effect = [
            mock_delete_response,
            mock_delete_response_2,
            mock_delete_response_empty
        ]

        with patch.object(service, "get_tenant_retention_policy", return_value=mock_policy):
            with patch("app.services.retention_enforcement_service.db_service") as mock_db:
                mock_db.client = mock_client

                result = await service.enforce_activity_retention(tenant_id, dry_run=False)

        assert result["tenant_id"] == tenant_id
        assert result["plan_name"] == "pro"
        assert result["retention_days"] == 30
        assert result["deleted_count"] == 150
        assert result["total_count"] == 500
        assert result["remaining_count"] == 350
        assert result["dry_run"] is False

    @pytest.mark.asyncio
    async def test_enforce_activity_retention_skips_when_below_minimum(self):
        """
        GIVEN a tenant with few background jobs (below minimum threshold)
        WHEN enforce_activity_retention is called
        THEN deletion should be skipped to preserve history
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        # Mock retention policy
        mock_policy = {
            "plan_name": "free",
            "retention_days": 7,
            "execution_retention_days": 7,
            "audit_log_retention_days": 7,
        }

        # Mock database responses
        mock_total_count = MagicMock()
        mock_total_count.count = 50  # Below MIN_RECORDS_TO_KEEP (100)

        mock_old_count = MagicMock()
        mock_old_count.count = 20  # Some old jobs

        mock_orphaned_count = MagicMock()
        mock_orphaned_count.count = 0  # No orphaned jobs

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_total_count
        mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.lt.return_value.execute.return_value = mock_old_count
        mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.is_.return_value.execute.return_value = mock_orphaned_count

        with patch.object(service, "get_tenant_retention_policy", return_value=mock_policy):
            with patch("app.services.retention_enforcement_service.db_service") as mock_db:
                mock_db.client = mock_client

                result = await service.enforce_activity_retention(tenant_id, dry_run=False)

        assert result["tenant_id"] == tenant_id
        assert result["deleted_count"] == 0
        assert result["total_count"] == 50
        assert result["remaining_count"] == 50
        assert result["skipped"] is True
        assert "below minimum threshold" in result["reason"]

    @pytest.mark.asyncio
    async def test_enforce_activity_retention_dry_run(self):
        """
        GIVEN a tenant with old background jobs
        WHEN enforce_activity_retention is called with dry_run=True
        THEN it should return deletion counts without actually deleting
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        # Mock retention policy
        mock_policy = {
            "plan_name": "agency",
            "retention_days": 90,
            "execution_retention_days": 90,
            "audit_log_retention_days": 90,
        }

        # Mock database responses
        mock_total_count = MagicMock()
        mock_total_count.count = 1000

        mock_old_count = MagicMock()
        mock_old_count.count = 300

        mock_orphaned_count = MagicMock()
        mock_orphaned_count.count = 0  # No orphaned jobs

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_total_count
        mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.lt.return_value.execute.return_value = mock_old_count
        mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.is_.return_value.execute.return_value = mock_orphaned_count

        with patch.object(service, "get_tenant_retention_policy", return_value=mock_policy):
            with patch("app.services.retention_enforcement_service.db_service") as mock_db:
                mock_db.client = mock_client

                result = await service.enforce_activity_retention(tenant_id, dry_run=True)

        # Should show what WOULD be deleted (capped: 1000 - 100 = 900 allowed, min(300, 900) = 300)
        assert result["tenant_id"] == tenant_id
        assert result["deleted_count"] == 300  # Would delete this many
        assert result["total_count"] == 1000
        assert result["remaining_count"] == 700
        assert result["dry_run"] is True

        # Verify delete was never called
        mock_client.table.return_value.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_retention_preview_includes_activity(self):
        """
        GIVEN a tenant with activity records
        WHEN get_retention_preview is called
        THEN it should include activity preview information
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        # Mock retention policy
        mock_policy = {
            "plan_name": "enterprise",
            "retention_days": 365,
            "snapshot_retention_days": 365,
        }

        # Mock database responses for different record types
        mock_exec_total = MagicMock()
        mock_exec_total.count = 5000
        mock_exec_old = MagicMock()
        mock_exec_old.count = 1000

        mock_audit_total = MagicMock()
        mock_audit_total.count = 10000
        mock_audit_old = MagicMock()
        mock_audit_old.count = 2000

        mock_activity_total = MagicMock()
        mock_activity_total.count = 800
        mock_activity_old = MagicMock()
        mock_activity_old.count = 200

        # Mock snapshots and environments
        mock_snapshot_total = MagicMock()
        mock_snapshot_total.count = 50
        mock_snapshot_old = MagicMock()
        mock_snapshot_old.count = 10
        mock_env_response = MagicMock()
        mock_env_response.data = []  # No environments for simplicity
        mock_latest_snapshot = MagicMock()
        mock_latest_snapshot.data = []

        mock_client = MagicMock()

        # Setup mock to return different counts based on table
        def mock_table_select(table_name):
            mock_chain = MagicMock()

            if table_name == "executions":
                mock_chain.select.return_value.eq.return_value.execute.return_value = mock_exec_total
                mock_chain.select.return_value.eq.return_value.lt.return_value.execute.return_value = mock_exec_old
            elif table_name == "feature_access_log":
                mock_chain.select.return_value.eq.return_value.execute.return_value = mock_audit_total
                mock_chain.select.return_value.eq.return_value.lt.return_value.execute.return_value = mock_audit_old
            elif table_name == "background_jobs":
                mock_chain.select.return_value.eq.return_value.execute.return_value = mock_activity_total
                mock_chain.select.return_value.eq.return_value.in_.return_value.lt.return_value.execute.return_value = mock_activity_old
            elif table_name == "snapshots":
                mock_chain.select.return_value.eq.return_value.execute.return_value = mock_snapshot_total
                mock_chain.select.return_value.eq.return_value.lt.return_value.execute.return_value = mock_snapshot_old
                mock_chain.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_latest_snapshot
            elif table_name == "environments":
                mock_chain.select.return_value.eq.return_value.execute.return_value = mock_env_response

            return mock_chain

        mock_client.table = mock_table_select

        with patch.object(service, "get_tenant_retention_policy", return_value=mock_policy):
            with patch("app.services.retention_enforcement_service.db_service") as mock_db:
                mock_db.client = mock_client

                result = await service.get_retention_preview(tenant_id)

        assert result["tenant_id"] == tenant_id
        assert result["plan_name"] == "enterprise"
        assert result["retention_days"] == 365

        # Check activity preview
        assert "activity" in result
        assert result["activity"]["total_count"] == 800
        assert result["activity"]["old_count"] == 200
        assert result["activity"]["to_delete"] == 200
        assert result["activity"]["would_delete"] is True
        assert result["activity"]["remaining"] == 600

        # Check total to delete includes activity
        assert result["total_to_delete"] >= 200


class TestActivityRetentionIntegration:
    """Integration tests for activity retention in combined methods."""

    @pytest.mark.asyncio
    async def test_enforce_tenant_retention_includes_activity(self):
        """
        GIVEN a tenant with old records across all types
        WHEN enforce_tenant_retention is called
        THEN it should enforce retention for executions, audit logs, AND activity
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
            "total_count": 500,
            "remaining_count": 400,
        }

        mock_audit_result = {
            "tenant_id": tenant_id,
            "deleted_count": 200,
            "total_count": 1000,
            "remaining_count": 800,
        }

        mock_activity_result = {
            "tenant_id": tenant_id,
            "deleted_count": 50,
            "total_count": 300,
            "remaining_count": 250,
        }

        with patch.object(service, "get_tenant_retention_policy", return_value=mock_policy):
            with patch.object(service, "enforce_execution_retention", return_value=mock_exec_result):
                with patch.object(service, "enforce_audit_log_retention", return_value=mock_audit_result):
                    with patch.object(service, "enforce_activity_retention", return_value=mock_activity_result):
                        result = await service.enforce_tenant_retention(tenant_id, dry_run=False)

        assert result["tenant_id"] == tenant_id
        assert result["total_deleted"] == 350  # 100 + 200 + 50
        assert "execution_result" in result
        assert "audit_log_result" in result
        assert "activity_result" in result
        assert result["activity_result"]["deleted_count"] == 50


class TestActivityRetentionCappedDeletions:
    """Tests for the improved MIN_RECORDS_TO_KEEP semantics."""

    @pytest.mark.asyncio
    async def test_caps_deletions_to_preserve_100_records_case_1(self):
        """
        GIVEN a tenant with 101 total jobs and 100 deletable
        WHEN enforce_activity_retention is called
        THEN only 1 job should be deleted (leaving exactly 100)
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        mock_policy = {
            "plan_name": "pro",
            "retention_days": 30,
            "execution_retention_days": 30,
            "audit_log_retention_days": 30,
        }

        mock_total_count = MagicMock()
        mock_total_count.count = 101  # Just above minimum

        mock_old_count = MagicMock()
        mock_old_count.count = 100  # All but 1 are old

        mock_orphaned_count = MagicMock()
        mock_orphaned_count.count = 0  # No orphaned jobs

        mock_delete_response = MagicMock()
        mock_delete_response.data = [{"id": "job-1"}]  # Only 1 deleted

        mock_delete_response_empty = MagicMock()
        mock_delete_response_empty.data = []

        mock_client = MagicMock()

        # Setup mock chain for total count
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_total_count

        # Setup mock chain for old count and orphaned count
        mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.lt.return_value.execute.return_value = mock_old_count
        mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.is_.return_value.execute.return_value = mock_orphaned_count

        # Setup mock chain for delete operations
        mock_client.table.return_value.delete.return_value.eq.return_value.in_.return_value.lt.return_value.limit.return_value.execute.side_effect = [
            mock_delete_response,
            mock_delete_response_empty
        ]

        with patch.object(service, "get_tenant_retention_policy", return_value=mock_policy):
            with patch("app.services.retention_enforcement_service.db_service") as mock_db:
                mock_db.client = mock_client

                result = await service.enforce_activity_retention(tenant_id, dry_run=False)

        # max_deletions_allowed = 101 - 100 = 1
        # effective_delete_count = min(100, 1) = 1
        assert result["tenant_id"] == tenant_id
        assert result["deleted_count"] == 1
        assert result["total_count"] == 101
        assert result["remaining_count"] == 100  # Exactly at minimum
        assert result["dry_run"] is False

    @pytest.mark.asyncio
    async def test_caps_deletions_to_preserve_100_records_case_2(self):
        """
        GIVEN a tenant with 110 total jobs and 50 deletable
        WHEN enforce_activity_retention is called
        THEN only 10 jobs should be deleted (leaving exactly 100)
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        mock_policy = {
            "plan_name": "pro",
            "retention_days": 30,
            "execution_retention_days": 30,
            "audit_log_retention_days": 30,
        }

        mock_total_count = MagicMock()
        mock_total_count.count = 110

        mock_old_count = MagicMock()
        mock_old_count.count = 50  # 50 are deletable

        mock_orphaned_count = MagicMock()
        mock_orphaned_count.count = 0

        # Expect 10 to be deleted (110 - 100 = 10 allowed)
        mock_delete_response = MagicMock()
        mock_delete_response.data = [{"id": f"job-{i}"} for i in range(10)]

        mock_delete_response_empty = MagicMock()
        mock_delete_response_empty.data = []

        mock_client = MagicMock()

        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_total_count
        mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.lt.return_value.execute.return_value = mock_old_count
        mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.is_.return_value.execute.return_value = mock_orphaned_count
        mock_client.table.return_value.delete.return_value.eq.return_value.in_.return_value.lt.return_value.limit.return_value.execute.side_effect = [
            mock_delete_response,
            mock_delete_response_empty
        ]

        with patch.object(service, "get_tenant_retention_policy", return_value=mock_policy):
            with patch("app.services.retention_enforcement_service.db_service") as mock_db:
                mock_db.client = mock_client

                result = await service.enforce_activity_retention(tenant_id, dry_run=False)

        # max_deletions_allowed = 110 - 100 = 10
        # effective_delete_count = min(50, 10) = 10
        assert result["tenant_id"] == tenant_id
        assert result["deleted_count"] == 10
        assert result["total_count"] == 110
        assert result["remaining_count"] == 100  # Exactly at minimum
        assert result["dry_run"] is False

    @pytest.mark.asyncio
    async def test_dry_run_reports_capped_count(self):
        """
        GIVEN a tenant with 110 total jobs and 50 deletable
        WHEN enforce_activity_retention is called with dry_run=True
        THEN it should report the capped count (10) as would-be-deleted
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        mock_policy = {
            "plan_name": "pro",
            "retention_days": 30,
            "execution_retention_days": 30,
            "audit_log_retention_days": 30,
        }

        mock_total_count = MagicMock()
        mock_total_count.count = 110

        mock_old_count = MagicMock()
        mock_old_count.count = 50

        mock_orphaned_count = MagicMock()
        mock_orphaned_count.count = 0

        mock_client = MagicMock()

        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_total_count
        mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.lt.return_value.execute.return_value = mock_old_count
        mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.is_.return_value.execute.return_value = mock_orphaned_count

        with patch.object(service, "get_tenant_retention_policy", return_value=mock_policy):
            with patch("app.services.retention_enforcement_service.db_service") as mock_db:
                mock_db.client = mock_client

                result = await service.enforce_activity_retention(tenant_id, dry_run=True)

        # Should report capped count
        assert result["tenant_id"] == tenant_id
        assert result["deleted_count"] == 10  # Capped from 50
        assert result["total_count"] == 110
        assert result["remaining_count"] == 100
        assert result["dry_run"] is True

        # Verify delete was never called
        mock_client.table.return_value.delete.assert_not_called()


class TestOrphanedTerminalJobsWarning:
    """Tests for orphaned terminal jobs detection."""

    @pytest.mark.asyncio
    async def test_logs_warning_for_orphaned_jobs(self):
        """
        GIVEN a tenant with terminal jobs missing completed_at
        WHEN enforce_activity_retention is called
        THEN it should log a warning and include count in result
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        mock_policy = {
            "plan_name": "pro",
            "retention_days": 30,
            "execution_retention_days": 30,
            "audit_log_retention_days": 30,
        }

        mock_total_count = MagicMock()
        mock_total_count.count = 50  # Below minimum, will skip deletion

        mock_old_count = MagicMock()
        mock_old_count.count = 10

        mock_orphaned_count = MagicMock()
        mock_orphaned_count.count = 5  # 5 orphaned jobs

        mock_client = MagicMock()

        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_total_count
        mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.lt.return_value.execute.return_value = mock_old_count
        mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.is_.return_value.execute.return_value = mock_orphaned_count

        with patch.object(service, "get_tenant_retention_policy", return_value=mock_policy):
            with patch("app.services.retention_enforcement_service.db_service") as mock_db:
                mock_db.client = mock_client

                with patch("app.services.retention_enforcement_service.logger") as mock_logger:
                    result = await service.enforce_activity_retention(tenant_id, dry_run=False)

                    # Verify warning was logged
                    mock_logger.warning.assert_called()
                    warning_call = mock_logger.warning.call_args[0][0]
                    assert "5 terminal jobs with NULL completed_at" in warning_call

        # Result should be skipped due to low total, but still have good data
        assert result["skipped"] is True

    @pytest.mark.asyncio
    async def test_includes_orphaned_count_in_result(self):
        """
        GIVEN a tenant with orphaned terminal jobs
        WHEN enforce_activity_retention completes successfully
        THEN the result should include orphaned_terminal_jobs count
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        mock_policy = {
            "plan_name": "pro",
            "retention_days": 30,
            "execution_retention_days": 30,
            "audit_log_retention_days": 30,
        }

        mock_total_count = MagicMock()
        mock_total_count.count = 200  # Above minimum

        mock_old_count = MagicMock()
        mock_old_count.count = 50

        mock_orphaned_count = MagicMock()
        mock_orphaned_count.count = 3  # 3 orphaned jobs

        mock_delete_response = MagicMock()
        mock_delete_response.data = [{"id": f"job-{i}"} for i in range(50)]

        mock_delete_response_empty = MagicMock()
        mock_delete_response_empty.data = []

        mock_client = MagicMock()

        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_total_count
        mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.lt.return_value.execute.return_value = mock_old_count
        mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.is_.return_value.execute.return_value = mock_orphaned_count
        mock_client.table.return_value.delete.return_value.eq.return_value.in_.return_value.lt.return_value.limit.return_value.execute.side_effect = [
            mock_delete_response,
            mock_delete_response_empty
        ]

        with patch.object(service, "get_tenant_retention_policy", return_value=mock_policy):
            with patch("app.services.retention_enforcement_service.db_service") as mock_db:
                mock_db.client = mock_client

                result = await service.enforce_activity_retention(tenant_id, dry_run=False)

        assert result["orphaned_terminal_jobs"] == 3
        assert result["deleted_count"] == 50  # All deletable since 200-50=150 > 100
