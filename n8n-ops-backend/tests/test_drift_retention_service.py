"""
Unit tests for the Drift Retention Service.
Tests plan-based retention defaults and cleanup logic.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.drift_retention_service import (
    DriftRetentionService,
    drift_retention_service,
)


# Test fixtures
MOCK_TENANT_ID = "00000000-0000-0000-0000-000000000001"


class TestRetentionDefaults:
    """Test plan-based retention default values."""

    def test_free_plan_defaults(self):
        """Test retention defaults for free plan."""
        service = DriftRetentionService()
        defaults = service.RETENTION_DEFAULTS["free"]

        assert defaults["drift_checks"] == 7
        assert defaults["closed_incidents"] == 0  # N/A for free
        assert defaults["reconciliation_artifacts"] == 0  # N/A for free
        assert defaults["approvals"] == 0  # N/A for free

    def test_pro_plan_defaults(self):
        """Test retention defaults for pro plan."""
        service = DriftRetentionService()
        defaults = service.RETENTION_DEFAULTS["pro"]

        assert defaults["drift_checks"] == 30
        assert defaults["closed_incidents"] == 180
        assert defaults["reconciliation_artifacts"] == 180
        assert defaults["approvals"] == 180

    def test_agency_plan_defaults(self):
        """Test retention defaults for agency plan."""
        service = DriftRetentionService()
        defaults = service.RETENTION_DEFAULTS["agency"]

        assert defaults["drift_checks"] == 90
        assert defaults["closed_incidents"] == 365
        assert defaults["reconciliation_artifacts"] == 365
        assert defaults["approvals"] == 365

    def test_enterprise_plan_defaults(self):
        """Test retention defaults for enterprise plan."""
        service = DriftRetentionService()
        defaults = service.RETENTION_DEFAULTS["enterprise"]

        assert defaults["drift_checks"] == 180
        assert defaults["closed_incidents"] == 2555  # 7 years
        assert defaults["reconciliation_artifacts"] == 2555
        assert defaults["approvals"] == 2555


class TestGetRetentionPolicy:
    """Tests for get_retention_policy method."""

    @pytest.mark.asyncio
    async def test_get_policy_with_plan_defaults(self):
        """Test getting policy falls back to plan defaults."""
        service = DriftRetentionService()

        with patch("app.services.drift_retention_service.feature_service") as mock_feature:
            mock_feature.get_tenant_subscription = AsyncMock(return_value={
                "plan": {"name": "pro"}
            })

            with patch("app.services.drift_retention_service.db_service") as mock_db:
                mock_response = MagicMock()
                mock_response.data = []  # No policy record
                mock_db.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

                policy = await service.get_retention_policy(MOCK_TENANT_ID)

                assert policy["plan"] == "pro"
                assert policy["retention_enabled"] is True
                assert policy["retention_days_drift_checks"] == 30
                assert policy["retention_days_closed_incidents"] == 180
                assert policy["retention_days_approvals"] == 180

    @pytest.mark.asyncio
    async def test_get_policy_with_custom_values(self):
        """Test getting policy with custom tenant values."""
        service = DriftRetentionService()

        with patch("app.services.drift_retention_service.feature_service") as mock_feature:
            mock_feature.get_tenant_subscription = AsyncMock(return_value={
                "plan": {"name": "agency"}
            })

            with patch("app.services.drift_retention_service.db_service") as mock_db:
                mock_response = MagicMock()
                mock_response.data = [{
                    "retention_enabled": True,
                    "retention_days_drift_checks": 60,  # Custom override
                    "retention_days_closed_incidents": None,  # Use default
                    "retention_days_reconciliation_artifacts": 180,
                    "retention_days_approvals": 180,
                }]
                mock_db.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

                policy = await service.get_retention_policy(MOCK_TENANT_ID)

                assert policy["retention_days_drift_checks"] == 60  # Custom
                assert policy["retention_days_closed_incidents"] == 365  # Default

    @pytest.mark.asyncio
    async def test_get_policy_retention_disabled(self):
        """Test getting policy when retention is disabled."""
        service = DriftRetentionService()

        with patch("app.services.drift_retention_service.feature_service") as mock_feature:
            mock_feature.get_tenant_subscription = AsyncMock(return_value={
                "plan": {"name": "enterprise"}
            })

            with patch("app.services.drift_retention_service.db_service") as mock_db:
                mock_response = MagicMock()
                mock_response.data = [{
                    "retention_enabled": False,
                }]
                mock_db.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

                policy = await service.get_retention_policy(MOCK_TENANT_ID)

                assert policy["retention_enabled"] is False

    @pytest.mark.asyncio
    async def test_get_policy_handles_error(self):
        """Test getting policy handles errors gracefully."""
        service = DriftRetentionService()

        with patch("app.services.drift_retention_service.feature_service") as mock_feature:
            mock_feature.get_tenant_subscription = AsyncMock(side_effect=Exception("DB error"))

            policy = await service.get_retention_policy(MOCK_TENANT_ID)

            # Should return safe free tier defaults
            assert policy["plan"] == "free"
            assert policy["retention_enabled"] is True
            assert policy["retention_days_drift_checks"] == 7


class TestCleanupTenantData:
    """Tests for cleanup_tenant_data method."""

    @pytest.mark.asyncio
    async def test_cleanup_skips_when_disabled(self):
        """Test cleanup is skipped when retention is disabled."""
        service = DriftRetentionService()

        with patch.object(service, "get_retention_policy", new_callable=AsyncMock) as mock_policy:
            mock_policy.return_value = {
                "retention_enabled": False,
                "retention_days_drift_checks": 30,
                "retention_days_closed_incidents": 180,
                "retention_days_reconciliation_artifacts": 180,
                "retention_days_approvals": 180,
                "plan": "pro",
            }

            result = await service.cleanup_tenant_data(MOCK_TENANT_ID)

            assert result["drift_checks_deleted"] == 0
            assert result["incident_payloads_purged"] == 0
            assert result["reconciliation_artifacts_deleted"] == 0
            assert result["approvals_deleted"] == 0

    @pytest.mark.asyncio
    async def test_cleanup_skips_zero_retention(self):
        """Test cleanup skips entities with 0 retention (never delete)."""
        service = DriftRetentionService()

        with patch.object(service, "get_retention_policy", new_callable=AsyncMock) as mock_policy:
            mock_policy.return_value = {
                "retention_enabled": True,
                "retention_days_drift_checks": 0,  # Never delete
                "retention_days_closed_incidents": 0,
                "retention_days_reconciliation_artifacts": 0,
                "retention_days_approvals": 0,
                "plan": "free",
            }

            result = await service.cleanup_tenant_data(MOCK_TENANT_ID)

            # Nothing should be deleted
            assert result["drift_checks_deleted"] == 0
            assert result["incident_payloads_purged"] == 0
            assert result["reconciliation_artifacts_deleted"] == 0
            assert result["approvals_deleted"] == 0


class TestCleanupDriftChecks:
    """Tests for _cleanup_drift_checks method."""

    @pytest.mark.asyncio
    async def test_cleanup_preserves_latest_check(self):
        """Test that the most recent drift check per environment is preserved."""
        service = DriftRetentionService()
        now = datetime.utcnow()

        with patch("app.services.drift_retention_service.db_service") as mock_db:
            # Mock environments query
            env_response = MagicMock()
            env_response.data = [{"id": "env-1"}, {"id": "env-2"}]

            # Mock latest check per env
            latest_check_response = MagicMock()
            latest_check_response.data = [{"id": "check-latest"}]

            # Mock old checks query
            old_checks_response = MagicMock()
            old_checks_response.data = [
                {"id": "check-old-1"},
                {"id": "check-old-2"},
                {"id": "check-latest"},  # Should be filtered out
            ]

            def table_side_effect(name):
                mock_query = MagicMock()
                if name == "environments":
                    mock_query.select.return_value.eq.return_value.execute.return_value = env_response
                elif name == "drift_check_history":
                    mock_query.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = latest_check_response
                    mock_query.select.return_value.eq.return_value.lt.return_value.execute.return_value = old_checks_response
                    mock_query.delete.return_value.eq.return_value.execute.return_value = MagicMock()
                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            count = await service._cleanup_drift_checks(MOCK_TENANT_ID, 30, now)

            # Should delete 2 old checks (excluding the latest)
            assert count == 2


class TestPurgeIncidentPayloads:
    """Tests for _purge_incident_payloads method."""

    @pytest.mark.asyncio
    async def test_purge_only_closed_incidents(self):
        """Test that only closed incidents are purged."""
        service = DriftRetentionService()
        now = datetime.utcnow()

        with patch("app.services.drift_retention_service.db_service") as mock_db:
            # Mock finding closed incidents
            incidents_response = MagicMock()
            incidents_response.data = [
                {"id": "incident-closed-1"},
                {"id": "incident-closed-2"},
            ]

            def table_side_effect(name):
                mock_query = MagicMock()
                if name == "drift_incidents":
                    mock_query.select.return_value.eq.return_value.eq.return_value.is_.return_value.lt.return_value.execute.return_value = incidents_response
                    mock_query.update.return_value.eq.return_value.execute.return_value = MagicMock()
                elif name == "incident_payloads":
                    mock_query.delete.return_value.eq.return_value.execute.return_value = MagicMock()
                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            count = await service._purge_incident_payloads(MOCK_TENANT_ID, 180, now)

            assert count == 2

    @pytest.mark.asyncio
    async def test_purge_skips_already_purged(self):
        """Test that already purged incidents are skipped."""
        service = DriftRetentionService()
        now = datetime.utcnow()

        with patch("app.services.drift_retention_service.db_service") as mock_db:
            # No incidents to purge (already purged)
            incidents_response = MagicMock()
            incidents_response.data = []

            mock_db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.is_.return_value.lt.return_value.execute.return_value = incidents_response

            count = await service._purge_incident_payloads(MOCK_TENANT_ID, 180, now)

            assert count == 0


class TestCleanupArtifacts:
    """Tests for _cleanup_artifacts method."""

    @pytest.mark.asyncio
    async def test_cleanup_artifacts_success(self):
        """Test successful cleanup of reconciliation artifacts."""
        service = DriftRetentionService()
        now = datetime.utcnow()

        with patch("app.services.drift_retention_service.db_service") as mock_db:
            count_response = MagicMock()
            count_response.count = 5
            count_response.data = [{"id": f"artifact-{i}"} for i in range(5)]

            mock_query = MagicMock()
            mock_query.select.return_value.eq.return_value.lt.return_value.execute.return_value = count_response
            mock_query.delete.return_value.eq.return_value.lt.return_value.execute.return_value = MagicMock()
            mock_db.client.table.return_value = mock_query

            count = await service._cleanup_artifacts(MOCK_TENANT_ID, 180, now)

            assert count == 5


class TestCleanupApprovals:
    """Tests for _cleanup_approvals method."""

    @pytest.mark.asyncio
    async def test_cleanup_approvals_success(self):
        """Test successful cleanup of approval records."""
        service = DriftRetentionService()
        now = datetime.utcnow()

        with patch("app.services.drift_retention_service.db_service") as mock_db:
            count_response = MagicMock()
            count_response.count = 3
            count_response.data = [{"id": f"approval-{i}"} for i in range(3)]

            mock_query = MagicMock()
            mock_query.select.return_value.eq.return_value.lt.return_value.execute.return_value = count_response
            mock_query.delete.return_value.eq.return_value.lt.return_value.execute.return_value = MagicMock()
            mock_db.client.table.return_value = mock_query

            count = await service._cleanup_approvals(MOCK_TENANT_ID, 180, now)

            assert count == 3


class TestCleanupAllTenants:
    """Tests for cleanup_all_tenants method."""

    @pytest.mark.asyncio
    async def test_cleanup_all_tenants_success(self):
        """Test cleaning up all tenants."""
        service = DriftRetentionService()

        with patch("app.services.drift_retention_service.db_service") as mock_db:
            # Mock tenants list
            tenants_response = MagicMock()
            tenants_response.data = [
                {"id": "tenant-1"},
                {"id": "tenant-2"},
            ]
            mock_db.client.table.return_value.select.return_value.execute.return_value = tenants_response

            with patch.object(service, "cleanup_tenant_data", new_callable=AsyncMock) as mock_cleanup:
                mock_cleanup.side_effect = [
                    {
                        "drift_checks_deleted": 5,
                        "incident_payloads_purged": 2,
                        "reconciliation_artifacts_deleted": 1,
                        "approvals_deleted": 0,
                    },
                    {
                        "drift_checks_deleted": 3,
                        "incident_payloads_purged": 0,
                        "reconciliation_artifacts_deleted": 0,
                        "approvals_deleted": 1,
                    },
                ]

                result = await service.cleanup_all_tenants()

                assert result["drift_checks_deleted"] == 8
                assert result["incident_payloads_purged"] == 2
                assert result["reconciliation_artifacts_deleted"] == 1
                assert result["approvals_deleted"] == 1
                assert result["tenants_processed"] == 2
                assert result["tenants_with_changes"] == 2

    @pytest.mark.asyncio
    async def test_cleanup_all_tenants_handles_error(self):
        """Test that cleanup_all_tenants handles errors gracefully."""
        service = DriftRetentionService()

        with patch("app.services.drift_retention_service.db_service") as mock_db:
            mock_db.client.table.return_value.select.return_value.execute.side_effect = Exception("DB error")

            result = await service.cleanup_all_tenants()

            assert "error" in result
            assert result["tenants_processed"] == 0


class TestOpenIncidentsNeverPurged:
    """Test that open incidents are never purged."""

    @pytest.mark.asyncio
    async def test_open_incidents_excluded_from_purge(self):
        """Test that the query correctly filters out non-closed incidents."""
        service = DriftRetentionService()
        now = datetime.utcnow()

        with patch("app.services.drift_retention_service.db_service") as mock_db:
            # Mock query that filters by status='closed'
            incidents_response = MagicMock()
            incidents_response.data = []

            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.is_.return_value = mock_query
            mock_query.lt.return_value = mock_query
            mock_query.execute.return_value = incidents_response

            mock_db.client.table.return_value = mock_query

            count = await service._purge_incident_payloads(MOCK_TENANT_ID, 180, now)

            # Verify that the query filtered by status='closed'
            eq_calls = [str(c) for c in mock_query.eq.call_args_list]
            assert any("closed" in str(c) for c in mock_query.eq.call_args_list)
