"""
Unit tests for the Drift Policy Enforcement Service.

Tests the policy enforcement logic for blocking promotions based on:
- TTL expiration (expired drift incidents)
- Active drift incidents
- Policy configuration (block_deployments_on_drift, block_deployments_on_expired)

This file covers BLOCKED scenarios (T006).
For ALLOWED scenarios with approval override, see T007 tests.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.drift_policy_enforcement import (
    DriftPolicyEnforcementService,
    drift_policy_enforcement_service,
    EnforcementResult,
    PolicyEnforcementDecision,
)


# ============ Test Fixtures ============

MOCK_TENANT_ID = "00000000-0000-0000-0000-000000000001"
MOCK_ENVIRONMENT_ID = "env-001"
MOCK_INCIDENT_ID = "incident-001"
MOCK_CORRELATION_ID = "correlation-001"


@pytest.fixture
def service():
    """Create a DriftPolicyEnforcementService instance."""
    return DriftPolicyEnforcementService()


@pytest.fixture
def mock_policy_blocking_drift():
    """Create a mock drift policy with block_deployments_on_drift enabled."""
    return {
        "id": "policy-001",
        "tenant_id": MOCK_TENANT_ID,
        "block_deployments_on_drift": True,
        "block_deployments_on_expired": False,
        "critical_ttl_hours": 24,
        "high_ttl_hours": 48,
        "medium_ttl_hours": 72,
        "low_ttl_hours": 168,
        "default_ttl_hours": 72,
    }


@pytest.fixture
def mock_policy_blocking_expired():
    """Create a mock drift policy with block_deployments_on_expired enabled."""
    return {
        "id": "policy-001",
        "tenant_id": MOCK_TENANT_ID,
        "block_deployments_on_drift": False,
        "block_deployments_on_expired": True,
        "critical_ttl_hours": 24,
        "high_ttl_hours": 48,
        "medium_ttl_hours": 72,
        "low_ttl_hours": 168,
        "default_ttl_hours": 72,
    }


@pytest.fixture
def mock_policy_blocking_both():
    """Create a mock drift policy with both blocking options enabled."""
    return {
        "id": "policy-001",
        "tenant_id": MOCK_TENANT_ID,
        "block_deployments_on_drift": True,
        "block_deployments_on_expired": True,
        "critical_ttl_hours": 24,
        "high_ttl_hours": 48,
        "medium_ttl_hours": 72,
        "low_ttl_hours": 168,
        "default_ttl_hours": 72,
    }


@pytest.fixture
def mock_policy_no_blocking():
    """Create a mock drift policy with no blocking enabled."""
    return {
        "id": "policy-001",
        "tenant_id": MOCK_TENANT_ID,
        "block_deployments_on_drift": False,
        "block_deployments_on_expired": False,
        "critical_ttl_hours": 24,
        "high_ttl_hours": 48,
        "medium_ttl_hours": 72,
        "low_ttl_hours": 168,
        "default_ttl_hours": 72,
    }


@pytest.fixture
def mock_active_incident():
    """Create a mock active drift incident (not expired)."""
    future_expiry = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    return {
        "id": MOCK_INCIDENT_ID,
        "tenant_id": MOCK_TENANT_ID,
        "environment_id": MOCK_ENVIRONMENT_ID,
        "status": "detected",
        "severity": "high",
        "title": "Test Drift Incident",
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": future_expiry,
        "owner_user_id": None,
    }


@pytest.fixture
def mock_expired_incident():
    """Create a mock expired drift incident."""
    past_expiry = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    return {
        "id": MOCK_INCIDENT_ID,
        "tenant_id": MOCK_TENANT_ID,
        "environment_id": MOCK_ENVIRONMENT_ID,
        "status": "detected",
        "severity": "critical",
        "title": "Expired Drift Incident",
        "detected_at": (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat(),
        "expires_at": past_expiry,
        "owner_user_id": "user-001",
    }


@pytest.fixture
def mock_acknowledged_incident():
    """Create a mock acknowledged drift incident."""
    future_expiry = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()
    return {
        "id": MOCK_INCIDENT_ID,
        "tenant_id": MOCK_TENANT_ID,
        "environment_id": MOCK_ENVIRONMENT_ID,
        "status": "acknowledged",
        "severity": "medium",
        "title": "Acknowledged Drift Incident",
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "acknowledged_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": future_expiry,
        "owner_user_id": "user-001",
    }


# ============ EnforcementResult Enum Tests ============


class TestEnforcementResultEnum:
    """Test the EnforcementResult enum values."""

    def test_allowed_value(self):
        """Test ALLOWED enum value."""
        assert EnforcementResult.ALLOWED.value == "allowed"

    def test_blocked_ttl_expired_value(self):
        """Test BLOCKED_TTL_EXPIRED enum value."""
        assert EnforcementResult.BLOCKED_TTL_EXPIRED.value == "blocked_ttl_expired"

    def test_blocked_active_drift_value(self):
        """Test BLOCKED_ACTIVE_DRIFT enum value."""
        assert EnforcementResult.BLOCKED_ACTIVE_DRIFT.value == "blocked_active_drift"

    def test_blocked_policy_violation_value(self):
        """Test BLOCKED_POLICY_VIOLATION enum value."""
        assert EnforcementResult.BLOCKED_POLICY_VIOLATION.value == "blocked_policy_violation"


# ============ PolicyEnforcementDecision Tests ============


class TestPolicyEnforcementDecision:
    """Test the PolicyEnforcementDecision dataclass."""

    def test_decision_to_dict(self):
        """Test converting decision to dictionary."""
        decision = PolicyEnforcementDecision(
            allowed=False,
            result=EnforcementResult.BLOCKED_TTL_EXPIRED,
            reason="TTL expired",
            incident_id="inc-001",
            incident_details={"title": "Test"},
            policy_config={"block_deployments_on_expired": True},
            correlation_id="corr-001",
        )

        result = decision.to_dict()

        assert result["allowed"] is False
        assert result["result"] == "blocked_ttl_expired"
        assert result["reason"] == "TTL expired"
        assert result["incident_id"] == "inc-001"
        assert result["incident_details"] == {"title": "Test"}
        assert result["policy_config"] == {"block_deployments_on_expired": True}
        assert result["correlation_id"] == "corr-001"

    def test_decision_to_dict_minimal(self):
        """Test converting minimal decision to dictionary."""
        decision = PolicyEnforcementDecision(
            allowed=True,
            result=EnforcementResult.ALLOWED,
        )

        result = decision.to_dict()

        assert result["allowed"] is True
        assert result["result"] == "allowed"
        assert result["reason"] is None
        assert result["incident_id"] is None


# ============ is_incident_expired Tests ============


class TestIsIncidentExpired:
    """Test the is_incident_expired method."""

    def test_incident_not_expired(self, service):
        """Test incident with future expiry is not expired."""
        future_expiry = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        incident = {"expires_at": future_expiry}

        result = service.is_incident_expired(incident)

        assert result is False

    def test_incident_expired(self, service):
        """Test incident with past expiry is expired."""
        past_expiry = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        incident = {"expires_at": past_expiry}

        result = service.is_incident_expired(incident)

        assert result is True

    def test_incident_no_expiry_not_expired(self, service):
        """Test incident with no expiry set is not expired."""
        incident = {"expires_at": None}

        result = service.is_incident_expired(incident)

        assert result is False

    def test_incident_empty_expiry_not_expired(self, service):
        """Test incident with empty string expiry is not expired."""
        incident = {"expires_at": ""}

        result = service.is_incident_expired(incident)

        assert result is False

    def test_incident_invalid_expiry_format_not_expired(self, service):
        """Test incident with invalid expiry format returns False (fail-safe)."""
        incident = {"expires_at": "invalid-date-format"}

        result = service.is_incident_expired(incident)

        assert result is False

    def test_incident_expired_at_exact_boundary(self, service):
        """Test incident that expires exactly now is considered expired."""
        # Use a time slightly in the past to ensure expiry
        just_past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        incident = {"expires_at": just_past}

        result = service.is_incident_expired(incident)

        assert result is True

    def test_incident_expiry_with_z_suffix(self, service):
        """Test incident with Z suffix in expiry time."""
        past_expiry = (datetime.now(timezone.utc) - timedelta(hours=1))
        incident = {"expires_at": past_expiry.strftime("%Y-%m-%dT%H:%M:%SZ")}

        result = service.is_incident_expired(incident)

        assert result is True

    def test_incident_expiry_without_timezone(self, service):
        """Test incident with naive datetime (no timezone) is handled."""
        # Service should handle naive datetime by assuming UTC
        past_expiry = (datetime.now(timezone.utc) - timedelta(hours=1))
        incident = {"expires_at": past_expiry.strftime("%Y-%m-%dT%H:%M:%S")}

        result = service.is_incident_expired(incident)

        assert result is True


# ============ get_ttl_for_severity Tests ============


class TestGetTTLForSeverity:
    """Test the get_ttl_for_severity method."""

    def test_critical_severity_ttl(self, service, mock_policy_blocking_both):
        """Test TTL for critical severity."""
        result = service.get_ttl_for_severity(mock_policy_blocking_both, "critical")
        assert result == 24

    def test_high_severity_ttl(self, service, mock_policy_blocking_both):
        """Test TTL for high severity."""
        result = service.get_ttl_for_severity(mock_policy_blocking_both, "high")
        assert result == 48

    def test_medium_severity_ttl(self, service, mock_policy_blocking_both):
        """Test TTL for medium severity."""
        result = service.get_ttl_for_severity(mock_policy_blocking_both, "medium")
        assert result == 72

    def test_low_severity_ttl(self, service, mock_policy_blocking_both):
        """Test TTL for low severity."""
        result = service.get_ttl_for_severity(mock_policy_blocking_both, "low")
        assert result == 168

    def test_unknown_severity_uses_default(self, service, mock_policy_blocking_both):
        """Test unknown severity uses default TTL."""
        result = service.get_ttl_for_severity(mock_policy_blocking_both, "unknown")
        assert result == 72  # default_ttl_hours

    def test_none_severity_uses_default(self, service, mock_policy_blocking_both):
        """Test None severity uses default TTL."""
        result = service.get_ttl_for_severity(mock_policy_blocking_both, None)
        assert result == 72  # default_ttl_hours

    def test_case_insensitive_severity(self, service, mock_policy_blocking_both):
        """Test severity matching is case-insensitive."""
        assert service.get_ttl_for_severity(mock_policy_blocking_both, "CRITICAL") == 24
        assert service.get_ttl_for_severity(mock_policy_blocking_both, "High") == 48
        assert service.get_ttl_for_severity(mock_policy_blocking_both, "MEDIUM") == 72


# ============ check_enforcement - BLOCKED Scenarios ============


class TestCheckEnforcementBlockedByExpiredTTL:
    """Test check_enforcement when blocked due to expired TTL."""

    @pytest.mark.asyncio
    async def test_blocked_by_expired_ttl(self, service, mock_policy_blocking_expired, mock_expired_incident):
        """Test that expired TTL blocks promotion."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            # Mock entitlements check
            mock_entitlements.has_flag = AsyncMock(return_value=True)

            # Mock policy query
            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_expired]

            # Mock incidents query
            mock_incidents_response = MagicMock()
            mock_incidents_response.data = [mock_expired_incident]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            # Run check
            result = await service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
                correlation_id=MOCK_CORRELATION_ID,
            )

            # Assertions
            assert result.allowed is False
            assert result.result == EnforcementResult.BLOCKED_TTL_EXPIRED
            assert "expired" in result.reason.lower()
            assert result.incident_id == MOCK_INCIDENT_ID
            assert result.incident_details is not None
            assert result.incident_details["severity"] == "critical"
            assert result.correlation_id == MOCK_CORRELATION_ID

    @pytest.mark.asyncio
    async def test_blocked_by_expired_ttl_includes_incident_details(self, service, mock_policy_blocking_expired, mock_expired_incident):
        """Test that blocked decision includes full incident details."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_expired]

            mock_incidents_response = MagicMock()
            mock_incidents_response.data = [mock_expired_incident]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            # Verify incident details are complete
            assert result.incident_details["title"] == "Expired Drift Incident"
            assert result.incident_details["severity"] == "critical"
            assert result.incident_details["status"] == "detected"
            assert "expires_at" in result.incident_details
            assert "detected_at" in result.incident_details
            assert "owner_user_id" in result.incident_details


class TestCheckEnforcementBlockedByActiveDrift:
    """Test check_enforcement when blocked due to active drift incident."""

    @pytest.mark.asyncio
    async def test_blocked_by_active_drift(self, service, mock_policy_blocking_drift, mock_active_incident):
        """Test that active drift incident blocks promotion."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_drift]

            mock_incidents_response = MagicMock()
            mock_incidents_response.data = [mock_active_incident]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
                correlation_id=MOCK_CORRELATION_ID,
            )

            # Assertions
            assert result.allowed is False
            assert result.result == EnforcementResult.BLOCKED_ACTIVE_DRIFT
            assert "active drift incident" in result.reason.lower()
            assert result.incident_id == MOCK_INCIDENT_ID
            assert result.incident_details is not None
            assert result.correlation_id == MOCK_CORRELATION_ID

    @pytest.mark.asyncio
    async def test_blocked_by_active_drift_most_recent_incident(self, service, mock_policy_blocking_drift):
        """Test that the most recent active incident is reported."""
        older_incident = {
            "id": "incident-old",
            "status": "detected",
            "severity": "low",
            "title": "Older Incident",
            "detected_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
            "owner_user_id": None,
        }
        newer_incident = {
            "id": "incident-new",
            "status": "acknowledged",
            "severity": "high",
            "title": "Newer Incident",
            "detected_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat(),
            "owner_user_id": "user-001",
        }

        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_drift]

            # Incidents ordered by detected_at desc (newest first)
            mock_incidents_response = MagicMock()
            mock_incidents_response.data = [newer_incident, older_incident]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            # Should report the most recent (first) incident
            assert result.incident_id == "incident-new"
            assert result.incident_details["title"] == "Newer Incident"

    @pytest.mark.asyncio
    async def test_blocked_by_active_drift_acknowledged_status(self, service, mock_policy_blocking_drift, mock_acknowledged_incident):
        """Test that acknowledged incidents also block (still active)."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_drift]

            mock_incidents_response = MagicMock()
            mock_incidents_response.data = [mock_acknowledged_incident]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result.allowed is False
            assert result.result == EnforcementResult.BLOCKED_ACTIVE_DRIFT
            assert result.incident_details["status"] == "acknowledged"


class TestCheckEnforcementBlockedByBothPolicies:
    """Test check_enforcement when both blocking policies are enabled."""

    @pytest.mark.asyncio
    async def test_expired_ttl_takes_priority_over_active_drift(self, service, mock_policy_blocking_both, mock_expired_incident):
        """Test that expired TTL is checked first and takes priority."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_both]

            mock_incidents_response = MagicMock()
            mock_incidents_response.data = [mock_expired_incident]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            # Should report TTL expired, not active drift
            assert result.result == EnforcementResult.BLOCKED_TTL_EXPIRED

    @pytest.mark.asyncio
    async def test_active_drift_blocks_when_no_expiry(self, service, mock_policy_blocking_both):
        """Test active drift blocks when incident has no expiry (cannot expire)."""
        incident_no_expiry = {
            "id": MOCK_INCIDENT_ID,
            "status": "detected",
            "severity": "high",
            "title": "Incident Without Expiry",
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": None,  # No expiry set
            "owner_user_id": None,
        }

        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_both]

            mock_incidents_response = MagicMock()
            mock_incidents_response.data = [incident_no_expiry]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            # Should block due to active drift (not TTL expired since no expiry)
            assert result.result == EnforcementResult.BLOCKED_ACTIVE_DRIFT


class TestCheckEnforcementPolicyConfigInDecision:
    """Test that policy configuration is included in the decision."""

    @pytest.mark.asyncio
    async def test_blocked_decision_includes_policy_config(self, service, mock_policy_blocking_both, mock_active_incident):
        """Test that blocked decision includes policy configuration."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_both]

            mock_incidents_response = MagicMock()
            mock_incidents_response.data = [mock_active_incident]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            # Verify policy config is included
            assert result.policy_config is not None
            assert result.policy_config["block_deployments_on_drift"] is True
            assert result.policy_config["block_deployments_on_expired"] is True


class TestCheckEnforcementMultipleExpiredIncidents:
    """Test enforcement with multiple expired incidents."""

    @pytest.mark.asyncio
    async def test_first_expired_incident_blocks(self, service, mock_policy_blocking_expired):
        """Test that first expired incident found blocks promotion."""
        expired_incidents = [
            {
                "id": "incident-1",
                "status": "detected",
                "severity": "critical",
                "title": "First Expired",
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
                "owner_user_id": None,
            },
            {
                "id": "incident-2",
                "status": "acknowledged",
                "severity": "high",
                "title": "Second Expired",
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
                "owner_user_id": "user-001",
            },
        ]

        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_expired]

            mock_incidents_response = MagicMock()
            mock_incidents_response.data = expired_incidents

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            # Should report the first expired incident
            assert result.result == EnforcementResult.BLOCKED_TTL_EXPIRED
            assert result.incident_id == "incident-1"


# ============ check_enforcement_with_override - BLOCKED Scenarios ============


class TestCheckEnforcementWithOverrideBlocked:
    """Test check_enforcement_with_override when no override exists."""

    @pytest.mark.asyncio
    async def test_blocked_no_override_available(self, service, mock_policy_blocking_drift, mock_active_incident):
        """Test that promotion is blocked when no approval override exists."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_drift]

            mock_incidents_response = MagicMock()
            mock_incidents_response.data = [mock_active_incident]

            # No approvals found
            mock_approvals_response = MagicMock()
            mock_approvals_response.data = []

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query
                mock_query.limit.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response
                elif name == "drift_approvals":
                    mock_query.execute.return_value = mock_approvals_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement_with_override(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
                correlation_id=MOCK_CORRELATION_ID,
            )

            # Should remain blocked
            assert result.allowed is False
            assert result.result == EnforcementResult.BLOCKED_ACTIVE_DRIFT
            assert result.incident_id == MOCK_INCIDENT_ID

    @pytest.mark.asyncio
    async def test_blocked_pending_approval_not_sufficient(self, service, mock_policy_blocking_drift, mock_active_incident):
        """Test that pending approval (not approved) doesn't override block."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_drift]

            mock_incidents_response = MagicMock()
            mock_incidents_response.data = [mock_active_incident]

            # Pending approval (not approved) - should not override
            # Note: The query already filters for status="approved", so this shouldn't return
            mock_approvals_response = MagicMock()
            mock_approvals_response.data = []  # No approved approvals

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query
                mock_query.limit.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response
                elif name == "drift_approvals":
                    mock_query.execute.return_value = mock_approvals_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement_with_override(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            # Should remain blocked
            assert result.allowed is False
            assert result.result == EnforcementResult.BLOCKED_ACTIVE_DRIFT


# ============ get_blocking_incidents_summary Tests ============


class TestGetBlockingIncidentsSummary:
    """Test get_blocking_incidents_summary method."""

    @pytest.mark.asyncio
    async def test_summary_with_blocking_incidents(self, service, mock_policy_blocking_both, mock_active_incident):
        """Test summary includes blocking incidents."""
        with patch.object(service, "get_tenant_policy", new_callable=AsyncMock) as mock_policy, \
             patch.object(service, "get_active_incidents", new_callable=AsyncMock) as mock_incidents:

            mock_policy.return_value = mock_policy_blocking_both
            mock_incidents.return_value = [mock_active_incident]

            result = await service.get_blocking_incidents_summary(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result["has_policy"] is True
            assert result["blocking_enabled"] is True
            assert result["block_on_drift"] is True
            assert result["block_on_expired"] is True
            assert result["total_active_incidents"] == 1
            assert len(result["blocking_incidents"]) == 1
            assert result["is_blocked"] is True

    @pytest.mark.asyncio
    async def test_summary_with_expired_incidents(self, service, mock_policy_blocking_expired, mock_expired_incident):
        """Test summary identifies expired incidents."""
        with patch.object(service, "get_tenant_policy", new_callable=AsyncMock) as mock_policy, \
             patch.object(service, "get_active_incidents", new_callable=AsyncMock) as mock_incidents:

            mock_policy.return_value = mock_policy_blocking_expired
            mock_incidents.return_value = [mock_expired_incident]

            result = await service.get_blocking_incidents_summary(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result["has_policy"] is True
            assert result["block_on_expired"] is True
            assert len(result["expired_incidents"]) == 1
            assert result["expired_incidents"][0]["id"] == MOCK_INCIDENT_ID
            assert result["is_blocked"] is True

    @pytest.mark.asyncio
    async def test_summary_no_policy(self, service):
        """Test summary when no policy configured."""
        with patch.object(service, "get_tenant_policy", new_callable=AsyncMock) as mock_policy, \
             patch.object(service, "get_active_incidents", new_callable=AsyncMock) as mock_incidents:

            mock_policy.return_value = None
            mock_incidents.return_value = []

            result = await service.get_blocking_incidents_summary(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result["has_policy"] is False
            assert result["blocking_enabled"] is False
            assert result["blocking_incidents"] == []
            assert result["expired_incidents"] == []


# ============ validate_ttl_compliance - Blocked Cases ============


class TestValidateTTLComplianceBlocked:
    """Test validate_ttl_compliance for non-compliant (expired) incidents."""

    @pytest.mark.asyncio
    async def test_expired_incident_not_compliant(self, service, mock_policy_blocking_expired, mock_expired_incident):
        """Test that expired incident is not compliant."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db:
            mock_incident_response = MagicMock()
            mock_incident_response.data = mock_expired_incident

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_expired]

            call_count = [0]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.single.return_value = mock_query

                call_count[0] += 1
                if name == "drift_incidents":
                    mock_query.execute.return_value = mock_incident_response
                elif name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.validate_ttl_compliance(
                tenant_id=MOCK_TENANT_ID,
                incident_id=MOCK_INCIDENT_ID,
            )

            assert result["compliant"] is False
            assert result["is_expired"] is True
            assert result["time_remaining_seconds"] == 0
            assert result["severity"] == "critical"


# ============ Database Error Handling - Fail-Closed Behavior ============


class TestDatabaseErrorHandlingFailClosed:
    """Test fail-closed behavior when database operations fail."""

    @pytest.mark.asyncio
    async def test_policy_fetch_error_continues_check(self, service):
        """Test that policy fetch error continues with enforcement check."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            # Policy fetch raises exception
            mock_db.client.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("DB error")

            result = await service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            # Should allow (no policy = no blocking)
            assert result.allowed is True
            assert result.result == EnforcementResult.ALLOWED

    @pytest.mark.asyncio
    async def test_incidents_fetch_error_allows(self, service, mock_policy_blocking_drift):
        """Test that incidents fetch error allows (no incidents found = no block)."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_drift]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    # Incidents query fails
                    mock_query.execute.side_effect = Exception("DB error")

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            # Should allow (error fetching incidents = empty list = no block)
            assert result.allowed is True


# ============ Correlation ID Tests ============


class TestCorrelationIdTracking:
    """Test correlation ID handling for audit trail."""

    @pytest.mark.asyncio
    async def test_provided_correlation_id_used(self, service, mock_policy_blocking_drift, mock_active_incident):
        """Test that provided correlation ID is used in decision."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_drift]

            mock_incidents_response = MagicMock()
            mock_incidents_response.data = [mock_active_incident]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            custom_correlation_id = "custom-correlation-12345"
            result = await service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
                correlation_id=custom_correlation_id,
            )

            assert result.correlation_id == custom_correlation_id

    @pytest.mark.asyncio
    async def test_auto_generated_correlation_id(self, service, mock_policy_no_blocking):
        """Test that correlation ID is auto-generated when not provided."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_no_blocking]

            mock_incidents_response = MagicMock()
            mock_incidents_response.data = []

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
                # No correlation_id provided
            )

            # Should have auto-generated UUID
            assert result.correlation_id is not None
            assert len(result.correlation_id) == 36  # UUID format


# ============ Singleton Instance Test ============


class TestSingletonInstance:
    """Test the singleton service instance."""

    def test_singleton_instance_exists(self):
        """Test that singleton instance is available."""
        assert drift_policy_enforcement_service is not None
        assert isinstance(drift_policy_enforcement_service, DriftPolicyEnforcementService)


# ============================================================================
# T007: ALLOWED Scenarios with Approval Override Tests
# ============================================================================
# The following tests cover scenarios where promotions are ALLOWED due to:
# - No policy configured
# - Policy exists but blocking is disabled
# - No active incidents
# - Explicit approval override exists
# ============================================================================


# ============ check_enforcement - ALLOWED Scenarios ============


class TestCheckEnforcementAllowedNoPolicy:
    """Test check_enforcement when allowed because no policy exists."""

    @pytest.mark.asyncio
    async def test_allowed_no_policy_configured(self, service):
        """Test that promotion is allowed when no drift policy exists."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            # No policy found
            mock_policy_response = MagicMock()
            mock_policy_response.data = []

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.execute.return_value = mock_policy_response
                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result.allowed is True
            assert result.result == EnforcementResult.ALLOWED
            assert "no drift policy" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_allowed_no_entitlement(self, service):
        """Test that promotion is allowed when tenant lacks drift_policies entitlement."""
        with patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:
            mock_entitlements.has_flag = AsyncMock(return_value=False)

            result = await service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result.allowed is True
            assert result.result == EnforcementResult.ALLOWED
            assert "not enabled" in result.reason.lower()


class TestCheckEnforcementAllowedPolicyDisabled:
    """Test check_enforcement when allowed because policy blocking is disabled."""

    @pytest.mark.asyncio
    async def test_allowed_blocking_disabled(self, service, mock_policy_no_blocking):
        """Test that promotion is allowed when policy has blocking disabled."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_no_blocking]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.execute.return_value = mock_policy_response
                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result.allowed is True
            assert result.result == EnforcementResult.ALLOWED
            assert "not enabled" in result.reason.lower()
            assert result.policy_config is not None
            assert result.policy_config["block_deployments_on_drift"] is False
            assert result.policy_config["block_deployments_on_expired"] is False

    @pytest.mark.asyncio
    async def test_allowed_blocking_disabled_with_active_incidents(self, service, mock_policy_no_blocking, mock_active_incident):
        """Test that promotion is allowed even with active incidents when blocking is disabled."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_no_blocking]

            # This mock shouldn't be called since policy has blocking disabled
            mock_incidents_response = MagicMock()
            mock_incidents_response.data = [mock_active_incident]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            # Should be allowed because blocking is disabled
            assert result.allowed is True
            assert result.result == EnforcementResult.ALLOWED


class TestCheckEnforcementAllowedNoIncidents:
    """Test check_enforcement when allowed because no active incidents exist."""

    @pytest.mark.asyncio
    async def test_allowed_no_active_incidents(self, service, mock_policy_blocking_both):
        """Test that promotion is allowed when no active incidents exist."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_both]

            # No active incidents
            mock_incidents_response = MagicMock()
            mock_incidents_response.data = []

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result.allowed is True
            assert result.result == EnforcementResult.ALLOWED
            assert "no active drift incidents" in result.reason.lower()
            assert result.policy_config is not None
            assert result.policy_config["block_deployments_on_drift"] is True
            assert result.policy_config["block_deployments_on_expired"] is True

    @pytest.mark.asyncio
    async def test_allowed_only_closed_incidents(self, service, mock_policy_blocking_drift):
        """Test that promotion is allowed when only closed incidents exist (not returned)."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_drift]

            # Query already filters out closed incidents, so empty result
            mock_incidents_response = MagicMock()
            mock_incidents_response.data = []

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result.allowed is True
            assert result.result == EnforcementResult.ALLOWED


class TestCheckEnforcementAllowedNotExpired:
    """Test check_enforcement when allowed because incidents are not expired."""

    @pytest.mark.asyncio
    async def test_allowed_only_block_expired_but_incident_not_expired(self, service, mock_policy_blocking_expired, mock_active_incident):
        """Test that promotion is allowed when block_on_expired is set but incidents aren't expired."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_expired]

            # Active incident that's NOT expired
            mock_incidents_response = MagicMock()
            mock_incidents_response.data = [mock_active_incident]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            # Should be allowed because block_on_drift is False and incident isn't expired
            assert result.allowed is True
            assert result.result == EnforcementResult.ALLOWED


# ============ check_approval_override - Tests ============


class TestCheckApprovalOverride:
    """Test the check_approval_override method."""

    @pytest.mark.asyncio
    async def test_override_found_acknowledge_approval(self, service):
        """Test that acknowledge approval provides valid override."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db:
            mock_approval = {
                "id": "approval-001",
                "approval_type": "acknowledge",
                "status": "approved",
                "decided_by": "user-approver",
                "decided_at": "2024-01-15T10:00:00Z",
                "decision_notes": "Reviewed and approved for deployment",
                "requested_by": "user-requester",
                "requested_at": "2024-01-15T09:00:00Z",
            }

            mock_approvals_response = MagicMock()
            mock_approvals_response.data = [mock_approval]

            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.in_.return_value = mock_query
            mock_query.order.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.execute.return_value = mock_approvals_response

            mock_db.client.table.return_value = mock_query

            result = await service.check_approval_override(
                tenant_id=MOCK_TENANT_ID,
                incident_id=MOCK_INCIDENT_ID,
            )

            assert result["has_override"] is True
            assert result["approval_id"] == "approval-001"
            assert result["approval_type"] == "acknowledge"
            assert result["approved_by"] == "user-approver"
            assert result["approved_at"] == "2024-01-15T10:00:00Z"
            assert result["decision_notes"] == "Reviewed and approved for deployment"
            assert "acknowledge" in result["reason"]

    @pytest.mark.asyncio
    async def test_override_found_deployment_override_approval(self, service):
        """Test that deployment_override approval provides valid override."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db:
            mock_approval = {
                "id": "approval-002",
                "approval_type": "deployment_override",
                "status": "approved",
                "decided_by": "admin-user",
                "decided_at": "2024-01-15T11:00:00Z",
                "decision_notes": "Urgent hotfix approved",
                "requested_by": "developer",
                "requested_at": "2024-01-15T10:30:00Z",
            }

            mock_approvals_response = MagicMock()
            mock_approvals_response.data = [mock_approval]

            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.in_.return_value = mock_query
            mock_query.order.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.execute.return_value = mock_approvals_response

            mock_db.client.table.return_value = mock_query

            result = await service.check_approval_override(
                tenant_id=MOCK_TENANT_ID,
                incident_id=MOCK_INCIDENT_ID,
            )

            assert result["has_override"] is True
            assert result["approval_type"] == "deployment_override"

    @pytest.mark.asyncio
    async def test_override_found_close_approval(self, service):
        """Test that close approval provides valid override."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db:
            mock_approval = {
                "id": "approval-003",
                "approval_type": "close",
                "status": "approved",
                "decided_by": "manager",
                "decided_at": "2024-01-15T12:00:00Z",
                "decision_notes": "Issue resolved in production",
                "requested_by": "operator",
                "requested_at": "2024-01-15T11:30:00Z",
            }

            mock_approvals_response = MagicMock()
            mock_approvals_response.data = [mock_approval]

            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.in_.return_value = mock_query
            mock_query.order.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.execute.return_value = mock_approvals_response

            mock_db.client.table.return_value = mock_query

            result = await service.check_approval_override(
                tenant_id=MOCK_TENANT_ID,
                incident_id=MOCK_INCIDENT_ID,
            )

            assert result["has_override"] is True
            assert result["approval_type"] == "close"

    @pytest.mark.asyncio
    async def test_no_override_no_approvals(self, service):
        """Test no override when no approvals exist."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db:
            mock_approvals_response = MagicMock()
            mock_approvals_response.data = []

            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.in_.return_value = mock_query
            mock_query.order.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.execute.return_value = mock_approvals_response

            mock_db.client.table.return_value = mock_query

            result = await service.check_approval_override(
                tenant_id=MOCK_TENANT_ID,
                incident_id=MOCK_INCIDENT_ID,
            )

            assert result["has_override"] is False
            assert result["approval_id"] is None
            assert result["approval_type"] is None
            assert result["approved_by"] is None
            assert "no approved override" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_no_override_database_error_fail_closed(self, service):
        """Test no override when database error occurs (fail-closed behavior)."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db:
            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.in_.return_value = mock_query
            mock_query.order.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.execute.side_effect = Exception("Connection error")

            mock_db.client.table.return_value = mock_query

            result = await service.check_approval_override(
                tenant_id=MOCK_TENANT_ID,
                incident_id=MOCK_INCIDENT_ID,
            )

            assert result["has_override"] is False
            assert "error" in result
            assert "failed to verify" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_override_uses_correlation_id(self, service):
        """Test that check_approval_override uses provided correlation ID."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db:
            mock_approvals_response = MagicMock()
            mock_approvals_response.data = []

            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.in_.return_value = mock_query
            mock_query.order.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.execute.return_value = mock_approvals_response

            mock_db.client.table.return_value = mock_query

            # This just verifies the method runs without error with correlation_id
            result = await service.check_approval_override(
                tenant_id=MOCK_TENANT_ID,
                incident_id=MOCK_INCIDENT_ID,
                correlation_id="test-correlation-id",
            )

            assert result is not None


# ============ check_enforcement_with_override - ALLOWED Scenarios ============


class TestCheckEnforcementWithOverrideAllowed:
    """Test check_enforcement_with_override when allowed via approval override."""

    @pytest.mark.asyncio
    async def test_allowed_via_acknowledge_override(self, service, mock_policy_blocking_drift, mock_active_incident):
        """Test that promotion is allowed when acknowledge approval exists."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_drift]

            mock_incidents_response = MagicMock()
            mock_incidents_response.data = [mock_active_incident]

            # Valid approval override exists
            mock_approval = {
                "id": "approval-001",
                "approval_type": "acknowledge",
                "status": "approved",
                "decided_by": "approver-user",
                "decided_at": "2024-01-15T10:00:00Z",
                "decision_notes": "Approved for deployment",
                "requested_by": "requester-user",
                "requested_at": "2024-01-15T09:00:00Z",
            }
            mock_approvals_response = MagicMock()
            mock_approvals_response.data = [mock_approval]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query
                mock_query.limit.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response
                elif name == "drift_approvals":
                    mock_query.execute.return_value = mock_approvals_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement_with_override(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
                correlation_id=MOCK_CORRELATION_ID,
            )

            assert result.allowed is True
            assert result.result == EnforcementResult.ALLOWED
            assert "acknowledge" in result.reason.lower()
            assert result.incident_id == MOCK_INCIDENT_ID
            assert result.incident_details is not None
            assert result.incident_details.get("override_approval_id") == "approval-001"
            assert result.incident_details.get("override_approval_type") == "acknowledge"
            assert result.incident_details.get("override_approved_by") == "approver-user"
            assert result.correlation_id == MOCK_CORRELATION_ID

    @pytest.mark.asyncio
    async def test_allowed_via_deployment_override(self, service, mock_policy_blocking_drift, mock_active_incident):
        """Test that promotion is allowed when deployment_override approval exists."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_drift]

            mock_incidents_response = MagicMock()
            mock_incidents_response.data = [mock_active_incident]

            mock_approval = {
                "id": "approval-002",
                "approval_type": "deployment_override",
                "status": "approved",
                "decided_by": "admin-user",
                "decided_at": "2024-01-15T10:00:00Z",
                "decision_notes": "Emergency deployment approved",
                "requested_by": "dev-user",
                "requested_at": "2024-01-15T09:30:00Z",
            }
            mock_approvals_response = MagicMock()
            mock_approvals_response.data = [mock_approval]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query
                mock_query.limit.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response
                elif name == "drift_approvals":
                    mock_query.execute.return_value = mock_approvals_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement_with_override(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result.allowed is True
            assert result.incident_details.get("override_approval_type") == "deployment_override"

    @pytest.mark.asyncio
    async def test_allowed_via_close_override(self, service, mock_policy_blocking_drift, mock_active_incident):
        """Test that promotion is allowed when close approval exists."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_drift]

            mock_incidents_response = MagicMock()
            mock_incidents_response.data = [mock_active_incident]

            mock_approval = {
                "id": "approval-003",
                "approval_type": "close",
                "status": "approved",
                "decided_by": "manager",
                "decided_at": "2024-01-15T10:00:00Z",
                "decision_notes": "Drift resolved, ok to deploy",
                "requested_by": "engineer",
                "requested_at": "2024-01-15T09:45:00Z",
            }
            mock_approvals_response = MagicMock()
            mock_approvals_response.data = [mock_approval]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query
                mock_query.limit.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response
                elif name == "drift_approvals":
                    mock_query.execute.return_value = mock_approvals_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement_with_override(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result.allowed is True
            assert result.incident_details.get("override_approval_type") == "close"

    @pytest.mark.asyncio
    async def test_allowed_via_override_for_expired_ttl(self, service, mock_policy_blocking_expired, mock_expired_incident):
        """Test that promotion is allowed when approval override exists for expired TTL incident."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_expired]

            mock_incidents_response = MagicMock()
            mock_incidents_response.data = [mock_expired_incident]

            mock_approval = {
                "id": "approval-004",
                "approval_type": "deployment_override",
                "status": "approved",
                "decided_by": "lead-engineer",
                "decided_at": "2024-01-15T10:00:00Z",
                "decision_notes": "Approved despite expired TTL",
                "requested_by": "developer",
                "requested_at": "2024-01-15T09:55:00Z",
            }
            mock_approvals_response = MagicMock()
            mock_approvals_response.data = [mock_approval]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query
                mock_query.limit.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response
                elif name == "drift_approvals":
                    mock_query.execute.return_value = mock_approvals_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement_with_override(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result.allowed is True
            assert result.result == EnforcementResult.ALLOWED
            assert result.incident_details.get("override_approval_id") == "approval-004"

    @pytest.mark.asyncio
    async def test_allowed_no_incidents_skips_override_check(self, service, mock_policy_blocking_both):
        """Test that override check is skipped when no incidents exist."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_both]

            mock_incidents_response = MagicMock()
            mock_incidents_response.data = []

            # Approvals should not be queried
            approvals_query_count = [0]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query
                mock_query.limit.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response
                elif name == "drift_approvals":
                    approvals_query_count[0] += 1

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement_with_override(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result.allowed is True
            assert result.result == EnforcementResult.ALLOWED
            # Override check should not have been made
            assert approvals_query_count[0] == 0

    @pytest.mark.asyncio
    async def test_override_includes_original_incident_details(self, service, mock_policy_blocking_drift, mock_active_incident):
        """Test that override response includes original incident details."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_drift]

            mock_incidents_response = MagicMock()
            mock_incidents_response.data = [mock_active_incident]

            mock_approval = {
                "id": "approval-005",
                "approval_type": "acknowledge",
                "status": "approved",
                "decided_by": "approver",
                "decided_at": "2024-01-15T10:00:00Z",
                "decision_notes": "Approved",
                "requested_by": "requester",
                "requested_at": "2024-01-15T09:00:00Z",
            }
            mock_approvals_response = MagicMock()
            mock_approvals_response.data = [mock_approval]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query
                mock_query.limit.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response
                elif name == "drift_approvals":
                    mock_query.execute.return_value = mock_approvals_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement_with_override(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            # Should include both original incident details and override info
            assert result.incident_details.get("title") == "Test Drift Incident"
            assert result.incident_details.get("severity") == "high"
            assert result.incident_details.get("status") == "detected"
            assert result.incident_details.get("override_approval_id") == "approval-005"


# ============ get_pending_overrides - Tests ============


class TestGetPendingOverrides:
    """Test the get_pending_overrides method."""

    @pytest.mark.asyncio
    async def test_pending_overrides_found(self, service):
        """Test that pending overrides are returned."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db:
            pending_approvals = [
                {
                    "id": "pending-001",
                    "approval_type": "acknowledge",
                    "status": "pending",
                    "requested_by": "user-1",
                    "requested_at": "2024-01-15T09:00:00Z",
                    "request_reason": "Need to deploy hotfix",
                },
                {
                    "id": "pending-002",
                    "approval_type": "deployment_override",
                    "status": "pending",
                    "requested_by": "user-2",
                    "requested_at": "2024-01-15T09:30:00Z",
                    "request_reason": "Urgent production fix",
                },
            ]

            mock_response = MagicMock()
            mock_response.data = pending_approvals

            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.in_.return_value = mock_query
            mock_query.order.return_value = mock_query
            mock_query.execute.return_value = mock_response

            mock_db.client.table.return_value = mock_query

            result = await service.get_pending_overrides(
                tenant_id=MOCK_TENANT_ID,
                incident_id=MOCK_INCIDENT_ID,
            )

            assert len(result) == 2
            assert result[0]["id"] == "pending-001"
            assert result[0]["approval_type"] == "acknowledge"
            assert result[1]["id"] == "pending-002"
            assert result[1]["approval_type"] == "deployment_override"

    @pytest.mark.asyncio
    async def test_no_pending_overrides(self, service):
        """Test empty result when no pending overrides exist."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db:
            mock_response = MagicMock()
            mock_response.data = []

            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.in_.return_value = mock_query
            mock_query.order.return_value = mock_query
            mock_query.execute.return_value = mock_response

            mock_db.client.table.return_value = mock_query

            result = await service.get_pending_overrides(
                tenant_id=MOCK_TENANT_ID,
                incident_id=MOCK_INCIDENT_ID,
            )

            assert result == []

    @pytest.mark.asyncio
    async def test_pending_overrides_database_error(self, service):
        """Test empty result when database error occurs."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db:
            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.in_.return_value = mock_query
            mock_query.order.return_value = mock_query
            mock_query.execute.side_effect = Exception("DB error")

            mock_db.client.table.return_value = mock_query

            result = await service.get_pending_overrides(
                tenant_id=MOCK_TENANT_ID,
                incident_id=MOCK_INCIDENT_ID,
            )

            assert result == []


# ============ validate_ttl_compliance - Allowed/Compliant Cases ============


class TestValidateTTLComplianceAllowed:
    """Test validate_ttl_compliance for compliant (not expired) incidents."""

    @pytest.mark.asyncio
    async def test_compliant_incident_not_expired(self, service, mock_policy_blocking_both):
        """Test that non-expired incident is compliant."""
        future_expiry = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        incident = {
            "id": MOCK_INCIDENT_ID,
            "status": "detected",
            "severity": "high",
            "title": "Active Incident",
            "expires_at": future_expiry,
        }

        with patch("app.services.drift_policy_enforcement.db_service") as mock_db:
            mock_incident_response = MagicMock()
            mock_incident_response.data = incident

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_both]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.single.return_value = mock_query

                if name == "drift_incidents":
                    mock_query.execute.return_value = mock_incident_response
                elif name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.validate_ttl_compliance(
                tenant_id=MOCK_TENANT_ID,
                incident_id=MOCK_INCIDENT_ID,
            )

            assert result["compliant"] is True
            assert result["is_expired"] is False
            assert result["time_remaining_seconds"] > 0
            assert result["severity"] == "high"
            assert result["expected_ttl_hours"] == 48  # high severity TTL

    @pytest.mark.asyncio
    async def test_compliant_incident_no_expiry_set(self, service, mock_policy_blocking_both):
        """Test that incident with no expiry is compliant."""
        incident = {
            "id": MOCK_INCIDENT_ID,
            "status": "detected",
            "severity": "medium",
            "title": "Incident Without Expiry",
            "expires_at": None,
        }

        with patch("app.services.drift_policy_enforcement.db_service") as mock_db:
            mock_incident_response = MagicMock()
            mock_incident_response.data = incident

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_both]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.single.return_value = mock_query

                if name == "drift_incidents":
                    mock_query.execute.return_value = mock_incident_response
                elif name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.validate_ttl_compliance(
                tenant_id=MOCK_TENANT_ID,
                incident_id=MOCK_INCIDENT_ID,
            )

            assert result["compliant"] is True
            assert result["is_expired"] is False
            assert result["expires_at"] is None
            assert "no expiration set" in result.get("message", "").lower()

    @pytest.mark.asyncio
    async def test_compliant_incident_not_found(self, service):
        """Test compliance check when incident not found."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db:
            mock_incident_response = MagicMock()
            mock_incident_response.data = None

            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.single.return_value = mock_query
            mock_query.execute.return_value = mock_incident_response

            mock_db.client.table.return_value = mock_query

            result = await service.validate_ttl_compliance(
                tenant_id=MOCK_TENANT_ID,
                incident_id="nonexistent-incident",
            )

            assert result["compliant"] is True
            assert "not found" in result.get("error", "").lower()


# ============ get_blocking_incidents_summary - Allowed Cases ============


class TestGetBlockingIncidentsSummaryAllowed:
    """Test get_blocking_incidents_summary when not blocked."""

    @pytest.mark.asyncio
    async def test_summary_not_blocked_no_incidents(self, service, mock_policy_blocking_both):
        """Test summary shows not blocked when no incidents exist."""
        with patch.object(service, "get_tenant_policy", new_callable=AsyncMock) as mock_policy, \
             patch.object(service, "get_active_incidents", new_callable=AsyncMock) as mock_incidents:

            mock_policy.return_value = mock_policy_blocking_both
            mock_incidents.return_value = []

            result = await service.get_blocking_incidents_summary(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result["has_policy"] is True
            assert result["blocking_enabled"] is True
            assert result["total_active_incidents"] == 0
            assert result["blocking_incidents"] == []
            assert result["expired_incidents"] == []
            assert result["is_blocked"] is False

    @pytest.mark.asyncio
    async def test_summary_not_blocked_policy_disabled(self, service, mock_policy_no_blocking, mock_active_incident):
        """Test summary shows not blocked when policy blocking is disabled."""
        with patch.object(service, "get_tenant_policy", new_callable=AsyncMock) as mock_policy, \
             patch.object(service, "get_active_incidents", new_callable=AsyncMock) as mock_incidents:

            mock_policy.return_value = mock_policy_no_blocking
            mock_incidents.return_value = [mock_active_incident]

            result = await service.get_blocking_incidents_summary(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result["has_policy"] is True
            assert result["blocking_enabled"] is False
            assert result["total_active_incidents"] == 1
            assert result["is_blocked"] is False


# ============ Edge Cases and Special Scenarios ============


class TestEdgeCasesAndSpecialScenarios:
    """Test edge cases and special scenarios for allowed scenarios."""

    @pytest.mark.asyncio
    async def test_allowed_with_stabilized_incident_no_block_on_drift(self, service, mock_policy_blocking_expired):
        """Test allowed when incident is stabilized and only block_on_expired is enabled."""
        stabilized_incident = {
            "id": MOCK_INCIDENT_ID,
            "status": "stabilized",
            "severity": "low",
            "title": "Stabilized Incident",
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=100)).isoformat(),
            "owner_user_id": "user-001",
        }

        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_expired]

            mock_incidents_response = MagicMock()
            mock_incidents_response.data = [stabilized_incident]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            # Should be allowed since block_on_drift is False and incident is not expired
            assert result.allowed is True
            assert result.result == EnforcementResult.ALLOWED

    @pytest.mark.asyncio
    async def test_multiple_overrides_uses_most_recent(self, service, mock_policy_blocking_drift, mock_active_incident):
        """Test that most recent override approval is used."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_drift]

            mock_incidents_response = MagicMock()
            mock_incidents_response.data = [mock_active_incident]

            # Query is ordered by decided_at DESC and limited to 1, so first is most recent
            most_recent_approval = {
                "id": "approval-recent",
                "approval_type": "deployment_override",
                "status": "approved",
                "decided_by": "recent-approver",
                "decided_at": "2024-01-15T12:00:00Z",
                "decision_notes": "Latest approval",
                "requested_by": "requester",
                "requested_at": "2024-01-15T11:00:00Z",
            }
            mock_approvals_response = MagicMock()
            mock_approvals_response.data = [most_recent_approval]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query
                mock_query.limit.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response
                elif name == "drift_approvals":
                    mock_query.execute.return_value = mock_approvals_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement_with_override(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result.allowed is True
            assert result.incident_details.get("override_approval_id") == "approval-recent"
            assert result.incident_details.get("override_approved_by") == "recent-approver"

    @pytest.mark.asyncio
    async def test_decision_to_dict_with_override_info(self, service, mock_policy_blocking_drift, mock_active_incident):
        """Test that decision with override info serializes correctly to dict."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            mock_policy_response = MagicMock()
            mock_policy_response.data = [mock_policy_blocking_drift]

            mock_incidents_response = MagicMock()
            mock_incidents_response.data = [mock_active_incident]

            mock_approval = {
                "id": "approval-serialize",
                "approval_type": "acknowledge",
                "status": "approved",
                "decided_by": "approver",
                "decided_at": "2024-01-15T10:00:00Z",
                "decision_notes": "Approved",
                "requested_by": "requester",
                "requested_at": "2024-01-15T09:00:00Z",
            }
            mock_approvals_response = MagicMock()
            mock_approvals_response.data = [mock_approval]

            def table_side_effect(name):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query
                mock_query.limit.return_value = mock_query

                if name == "drift_policies":
                    mock_query.execute.return_value = mock_policy_response
                elif name == "drift_incidents":
                    mock_query.execute.return_value = mock_incidents_response
                elif name == "drift_approvals":
                    mock_query.execute.return_value = mock_approvals_response

                return mock_query

            mock_db.client.table.side_effect = table_side_effect

            result = await service.check_enforcement_with_override(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            # Convert to dict and verify structure
            result_dict = result.to_dict()

            assert result_dict["allowed"] is True
            assert result_dict["result"] == "allowed"
            assert result_dict["incident_id"] == MOCK_INCIDENT_ID
            assert "override_approval_id" in result_dict["incident_details"]
            assert result_dict["incident_details"]["override_approval_id"] == "approval-serialize"
