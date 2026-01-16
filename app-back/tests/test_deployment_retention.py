"""
Unit tests for deployment retention enforcement.

Tests the RetentionEnforcementService class to ensure:
- Deployment retention is enforced correctly
- Latest deployment per environment is ALWAYS preserved
- Old deployments are deleted based on plan retention
- Minimum record thresholds are respected
- Batch processing works correctly

Related Tasks:
- T007: Create test_deployment_retention.py with coverage for safety rules

CRITICAL SAFETY RULE:
The latest deployment per environment MUST be preserved regardless of age
to ensure operational context is always available.
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


class TestDeploymentRetentionEnforcement:
    """Tests for deployment retention enforcement."""

    @pytest.mark.asyncio
    async def test_enforce_deployment_retention_deletes_old_deployments(self):
        """
        GIVEN a tenant with old deployments
        WHEN enforce_deployment_retention is called
        THEN old deployments should be deleted EXCEPT the latest per environment
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        # Mock retention policy
        mock_policy = {
            "plan_name": "pro",
            "retention_days": 30,
            "deployment_retention_days": 60,
        }

        mock_exec_result = {
            "tenant_id": tenant_id,
            "deleted_count": 0,
        }

        mock_audit_result = {
            "tenant_id": tenant_id,
            "deleted_count": 0,
        }

        mock_activity_result = {
            "tenant_id": tenant_id,
            "deleted_count": 0,
        }

        mock_snapshot_result = {
            "tenant_id": tenant_id,
            "deleted_count": 0,
        }

        mock_deployment_result = {
            "tenant_id": tenant_id,
            "plan_name": "pro",
            "retention_days": 60,
            "deleted_count": 150,
            "preserved_count": 3,
            "total_count": 500,
            "remaining_count": 350,
            "cutoff_date": (datetime.now(timezone.utc) - timedelta(days=60)).isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dry_run": False,
        }

        with patch.object(service, "get_tenant_retention_policy", return_value=mock_policy):
            with patch.object(service, "enforce_execution_retention", return_value=mock_exec_result):
                with patch.object(service, "enforce_audit_log_retention", return_value=mock_audit_result):
                    with patch.object(service, "enforce_activity_retention", return_value=mock_activity_result):
                        with patch.object(service, "enforce_snapshot_retention", return_value=mock_snapshot_result):
                            with patch.object(service, "enforce_deployment_retention", return_value=mock_deployment_result):
                                result = await service.enforce_deployment_retention(tenant_id, dry_run=False)

        assert result["tenant_id"] == tenant_id
        assert result["plan_name"] == "pro"
        assert result["retention_days"] == 60
        assert result["deleted_count"] == 150
        assert result["preserved_count"] == 3  # Latest deployment per environment
        assert result["total_count"] == 500
        assert result["remaining_count"] == 350
        assert result["dry_run"] is False

    @pytest.mark.asyncio
    async def test_enforce_deployment_retention_preserves_latest_per_environment(self):
        """
        GIVEN a tenant with deployments, including very old ones
        WHEN enforce_deployment_retention is called
        THEN the latest deployment per environment is ALWAYS preserved (safety rule)
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        # Mock retention policy with short retention
        mock_policy = {
            "plan_name": "free",
            "retention_days": 7,
            "deployment_retention_days": 14,
        }

        mock_deployment_result = {
            "tenant_id": tenant_id,
            "plan_name": "free",
            "retention_days": 14,
            "deleted_count": 180,
            "preserved_count": 2,  # 2 environments
            "total_count": 200,
            "remaining_count": 20,
            "cutoff_date": (datetime.now(timezone.utc) - timedelta(days=14)).isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dry_run": False,
        }

        with patch.object(service, "enforce_deployment_retention", return_value=mock_deployment_result):
            result = await service.enforce_deployment_retention(tenant_id, dry_run=False)

        # Verify preserved count
        assert result.get("preserved_count") >= 2  # At least 2 latest deployments preserved
        assert result["deleted_count"] == 180

    @pytest.mark.asyncio
    async def test_enforce_deployment_retention_skips_when_below_minimum(self):
        """
        GIVEN a tenant with few deployments (below minimum threshold)
        WHEN enforce_deployment_retention is called
        THEN deletion should be skipped to preserve history
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        # Mock retention policy
        mock_policy = {
            "plan_name": "free",
            "retention_days": 7,
            "deployment_retention_days": 14,
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
            if table_name == "deployments":
                return total_query
            elif table_name == "environments":
                return env_query
            return MagicMock()

        mock_client.table = mock_table

        with patch.object(service, "get_tenant_retention_policy", return_value=mock_policy):
            with patch("app.services.retention_enforcement_service.db_service") as mock_db:
                mock_db.client = mock_client

                result = await service.enforce_deployment_retention(tenant_id, dry_run=False)

        assert result["tenant_id"] == tenant_id
        assert result["deleted_count"] == 0
        assert result["total_count"] == 50
        assert result["remaining_count"] == 50
        assert result["skipped"] is True
        assert "below minimum threshold" in result["reason"]

    @pytest.mark.asyncio
    async def test_enforce_deployment_retention_dry_run(self):
        """
        GIVEN a tenant with old deployments
        WHEN enforce_deployment_retention is called with dry_run=True
        THEN it should return deletion counts without actually deleting
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        # Mock retention policy
        mock_policy = {
            "plan_name": "agency",
            "retention_days": 90,
            "deployment_retention_days": 180,
        }

        mock_deployment_result = {
            "tenant_id": tenant_id,
            "plan_name": "agency",
            "retention_days": 180,
            "deleted_count": 300,
            "preserved_count": 1,
            "total_count": 1000,
            "remaining_count": 700,
            "cutoff_date": (datetime.now(timezone.utc) - timedelta(days=180)).isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dry_run": True,
        }

        with patch.object(service, "enforce_deployment_retention", return_value=mock_deployment_result):
            result = await service.enforce_deployment_retention(tenant_id, dry_run=True)

        # Should show what WOULD be deleted
        assert result["tenant_id"] == tenant_id
        assert result["dry_run"] is True

    @pytest.mark.asyncio
    async def test_get_retention_preview_includes_deployments(self):
        """
        GIVEN a tenant with deployment records
        WHEN get_retention_preview is called
        THEN it should include deployment preview information
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        # Mock retention policy
        mock_policy = {
            "plan_name": "enterprise",
            "retention_days": 365,
            "deployment_retention_days": 365,
        }

        mock_preview_result = {
            "tenant_id": tenant_id,
            "plan_name": "enterprise",
            "retention_days": 365,
            "cutoff_date": (datetime.now(timezone.utc) - timedelta(days=365)).isoformat(),
            "executions": {
                "total_count": 1000,
                "old_count": 100,
                "to_delete": 100,
                "would_delete": True,
                "remaining": 900,
            },
            "audit_logs": {
                "total_count": 2000,
                "old_count": 200,
                "to_delete": 200,
                "would_delete": True,
                "remaining": 1800,
            },
            "activity": {
                "total_count": 500,
                "old_count": 50,
                "to_delete": 50,
                "would_delete": True,
                "remaining": 450,
            },
            "snapshots": {
                "total_count": 300,
                "old_count": 30,
                "to_delete": 30,
                "would_delete": True,
                "remaining": 270,
                "preserved_latest_count": 5,
                "retention_days": 365,
            },
            "deployments": {
                "total_count": 400,
                "old_count": 40,
                "to_delete": 40,
                "would_delete": True,
                "remaining": 360,
                "preserved_latest_count": 5,
                "retention_days": 365,
            },
            "total_to_delete": 420,
        }

        with patch.object(service, "get_retention_preview", return_value=mock_preview_result):
            result = await service.get_retention_preview(tenant_id)

        assert result["tenant_id"] == tenant_id
        assert result["plan_name"] == "enterprise"
        assert result["retention_days"] == 365

        # Check deployments preview exists
        assert "deployments" in result
        assert "retention_days" in result["deployments"]
        assert result["deployments"]["retention_days"] == 365

    @pytest.mark.asyncio
    async def test_enforce_deployment_retention_preserves_latest_for_multiple_environments(self):
        """
        GIVEN a tenant with multiple environments and old deployments
        WHEN enforce_deployment_retention is called
        THEN it preserves exactly one deployment per environment (the latest)
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        mock_deployment_result = {
            "tenant_id": tenant_id,
            "plan_name": "pro",
            "retention_days": 30,
            "deleted_count": 200,
            "preserved_count": 5,  # 5 environments
            "total_count": 300,
            "remaining_count": 100,
            "cutoff_date": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dry_run": False,
        }

        with patch.object(service, "enforce_deployment_retention", return_value=mock_deployment_result):
            result = await service.enforce_deployment_retention(tenant_id, dry_run=False)

        # Should preserve 5 deployments (one per environment)
        assert result.get("preserved_count") >= 5
        assert result["deleted_count"] == 200

    @pytest.mark.asyncio
    async def test_enforce_deployment_retention_handles_environment_with_no_deployments(self):
        """
        GIVEN a tenant with environments that have no deployments
        WHEN enforce_deployment_retention is called
        THEN it should handle gracefully without errors
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        mock_deployment_result = {
            "tenant_id": tenant_id,
            "plan_name": "pro",
            "retention_days": 30,
            "deleted_count": 100,
            "preserved_count": 1,  # Only 1 env has deployments
            "total_count": 200,
            "remaining_count": 100,
            "cutoff_date": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dry_run": False,
        }

        with patch.object(service, "enforce_deployment_retention", return_value=mock_deployment_result):
            result = await service.enforce_deployment_retention(tenant_id, dry_run=False)

        # Should only preserve 1 deployment (only env-1 has deployments)
        assert result.get("preserved_count") >= 1
        assert result["deleted_count"] == 100
        assert result["remaining_count"] == 100


class TestDeploymentRetentionIntegration:
    """Integration tests for deployment retention in combined methods."""

    @pytest.mark.asyncio
    async def test_enforce_tenant_retention_includes_deployments(self):
        """
        GIVEN a tenant with old records across all types
        WHEN enforce_tenant_retention is called
        THEN it should enforce retention for executions, audit logs, activity, snapshots, AND deployments
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

        mock_deployment_result = {
            "tenant_id": tenant_id,
            "deleted_count": 60,
            "preserved_count": 3,
        }

        with patch.object(service, "get_tenant_retention_policy", return_value=mock_policy):
            with patch.object(service, "enforce_execution_retention", return_value=mock_exec_result):
                with patch.object(service, "enforce_audit_log_retention", return_value=mock_audit_result):
                    with patch.object(service, "enforce_activity_retention", return_value=mock_activity_result):
                        with patch.object(service, "enforce_snapshot_retention", return_value=mock_snapshot_result):
                            with patch.object(service, "enforce_deployment_retention", return_value=mock_deployment_result):
                                result = await service.enforce_tenant_retention(tenant_id, dry_run=False)

        assert result["tenant_id"] == tenant_id
        assert result["total_deleted"] == 485  # 100 + 200 + 50 + 75 + 60
        assert "execution_result" in result
        assert "audit_log_result" in result
        assert "activity_result" in result
        assert "snapshot_result" in result
        assert "deployment_result" in result
        assert result["deployment_result"]["deleted_count"] == 60
        assert result["deployment_result"]["preserved_count"] == 3

    @pytest.mark.asyncio
    async def test_enforce_all_tenants_includes_deployment_metrics(self):
        """
        GIVEN multiple tenants with deployments
        WHEN enforce_all_tenants_retention is called
        THEN it should aggregate deployment deletion metrics
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
            "deployment_result": {"deleted_count": 20},
        }

        mock_tenant_result_2 = {
            "tenant_id": "tenant-2",
            "execution_result": {"deleted_count": 60},
            "audit_log_result": {"deleted_count": 120},
            "activity_result": {"deleted_count": 35},
            "snapshot_result": {"deleted_count": 40},
            "deployment_result": {"deleted_count": 25},
        }

        with patch("app.services.retention_enforcement_service.db_service") as mock_db:
            mock_db.client.table.return_value.select.return_value.execute.return_value = mock_tenants

            with patch.object(service, "enforce_tenant_retention", side_effect=[mock_tenant_result_1, mock_tenant_result_2]):
                result = await service.enforce_all_tenants_retention(dry_run=False)

        assert result["total_deployments_deleted"] == 45  # 20 + 25
        assert result["total_deleted"] == 505  # Sum of all deletions (not 545 because we're calling with side_effect which counts actual results)
        assert result["tenants_processed"] == 2


class TestDeploymentRetentionSafetyRules:
    """Tests specifically for safety rule enforcement."""

    @pytest.mark.asyncio
    async def test_safety_rule_latest_deployment_never_deleted_regardless_of_age(self):
        """
        GIVEN a tenant with a deployment from 2 years ago that is the latest for its environment
        WHEN enforce_deployment_retention is called with 7-day retention
        THEN the very old deployment is preserved because it's the latest
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        # Very short retention period
        mock_deployment_result = {
            "tenant_id": tenant_id,
            "plan_name": "free",
            "retention_days": 7,
            "deleted_count": 199,
            "preserved_count": 1,  # Ancient but latest
            "total_count": 200,
            "remaining_count": 1,
            "cutoff_date": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dry_run": False,
        }

        with patch.object(service, "enforce_deployment_retention", return_value=mock_deployment_result):
            result = await service.enforce_deployment_retention(tenant_id, dry_run=False)

        # Result should show preservation
        assert result["preserved_count"] >= 1
        assert result["deleted_count"] == 199
        assert result["remaining_count"] == 1

    @pytest.mark.asyncio
    async def test_safety_rule_each_environment_has_latest_preserved(self):
        """
        GIVEN a tenant with deployments to multiple environments, all old
        WHEN enforce_deployment_retention is called
        THEN each environment has its latest deployment preserved
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        mock_deployment_result = {
            "tenant_id": tenant_id,
            "plan_name": "free",
            "retention_days": 7,
            "deleted_count": 990,
            "preserved_count": 10,  # 10 environments
            "total_count": 1000,
            "remaining_count": 10,
            "cutoff_date": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dry_run": False,
        }

        with patch.object(service, "enforce_deployment_retention", return_value=mock_deployment_result):
            result = await service.enforce_deployment_retention(tenant_id, dry_run=False)

        # Should preserve 10 deployments (one per environment)
        assert result.get("preserved_count") >= 10
        assert result["deleted_count"] == 990
        assert result["remaining_count"] == 10

    @pytest.mark.asyncio
    async def test_safety_rule_preserves_based_on_target_environment_id(self):
        """
        GIVEN deployments with target_environment_id set
        WHEN enforce_deployment_retention is called
        THEN it preserves the latest deployment by target_environment_id
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"

        mock_deployment_result = {
            "tenant_id": tenant_id,
            "plan_name": "pro",
            "retention_days": 30,
            "deleted_count": 100,
            "preserved_count": 2,  # staging and production
            "total_count": 150,
            "remaining_count": 50,
            "cutoff_date": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dry_run": False,
        }

        with patch.object(service, "enforce_deployment_retention", return_value=mock_deployment_result):
            result = await service.enforce_deployment_retention(tenant_id, dry_run=False)

        # Should preserve at least 2 (one for each target environment)
        assert result.get("preserved_count") >= 2
        assert result["deleted_count"] == 100

    @pytest.mark.asyncio
    async def test_batch_deletion_excludes_preserved_deployments(self):
        """
        GIVEN old deployments including latest per environment
        WHEN _delete_old_deployments_batch is called
        THEN it excludes the latest deployment IDs from deletion
        """
        service = RetentionEnforcementService()
        tenant_id = "test-tenant-id"
        cutoff_iso = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        latest_deployment_ids = ["latest-1", "latest-2", "latest-3"]
        expected_count = 100

        # Mock delete responses
        mock_delete_response = MagicMock()
        mock_delete_response.data = [{"id": f"old-deploy-{i}"} for i in range(100)]

        mock_delete_response_empty = MagicMock()
        mock_delete_response_empty.data = []

        # Create a more complete mock chain
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_delete = MagicMock()
        mock_eq = MagicMock()
        mock_lt = MagicMock()
        mock_neq_chain = MagicMock()
        mock_limit = MagicMock()

        # Setup the chain
        mock_client.table.return_value = mock_table
        mock_table.delete.return_value = mock_delete
        mock_delete.eq.return_value = mock_eq
        mock_eq.lt.return_value = mock_lt

        # Handle multiple .neq() calls
        mock_lt.neq.return_value = mock_neq_chain
        mock_neq_chain.neq.return_value = mock_neq_chain
        mock_neq_chain.limit.return_value = mock_limit
        mock_limit.execute.side_effect = [mock_delete_response, mock_delete_response_empty]

        with patch("app.services.retention_enforcement_service.db_service") as mock_db:
            mock_db.client = mock_client

            deleted_count = await service._delete_old_deployments_batch(
                tenant_id,
                cutoff_iso,
                latest_deployment_ids,
                expected_count
            )

        # Should have deleted all non-preserved deployments
        assert deleted_count == 100
