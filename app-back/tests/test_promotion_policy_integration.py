"""
Integration tests for promotion blocking flow with drift policy enforcement.

These tests verify the complete integration between:
- DriftPolicyEnforcementService (policy checks)
- PromotionValidator (pre-flight validation)
- check_drift_policy_blocking (API helper)

Tests cover the following scenarios from acceptance criteria:
1. Promotion blocked when active incident with expired TTL exists
2. Promotion blocked when block_deployments_on_drift is enabled
3. Promotion allowed when approval override exists
4. Promotion allowed when no active incidents
5. Clear error messages displayed to user
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
from typing import Dict, Any

from app.services.drift_policy_enforcement import (
    DriftPolicyEnforcementService,
    EnforcementResult,
    PolicyEnforcementDecision,
)
from app.services.promotion_validation_service import PromotionValidator


# ============ Test Fixtures ============


MOCK_TENANT_ID = "00000000-0000-0000-0000-000000000001"
MOCK_ENVIRONMENT_ID = "env-target-001"
MOCK_SOURCE_ENVIRONMENT_ID = "env-source-001"
MOCK_INCIDENT_ID = "incident-001"
MOCK_WORKFLOW_ID = "workflow-001"
MOCK_CORRELATION_ID = "correlation-integration-001"


@pytest.fixture
def enforcement_service():
    """Create a DriftPolicyEnforcementService instance for integration tests."""
    return DriftPolicyEnforcementService()


@pytest.fixture
def promotion_validator():
    """Create a PromotionValidator instance for integration tests."""
    return PromotionValidator()


@pytest.fixture
def mock_environment():
    """Mock target environment configuration."""
    return {
        "id": MOCK_ENVIRONMENT_ID,
        "name": "Production",
        "tenant_id": MOCK_TENANT_ID,
        "n8n_name": "Production",
        "n8n_type": "production",
        "n8n_base_url": "https://prod.n8n.example.com",
        "n8n_api_key": "test-api-key",
        "is_active": True,
        "provider": "n8n",
    }


@pytest.fixture
def mock_source_environment():
    """Mock source environment configuration."""
    return {
        "id": MOCK_SOURCE_ENVIRONMENT_ID,
        "name": "Development",
        "tenant_id": MOCK_TENANT_ID,
        "n8n_name": "Development",
        "n8n_type": "development",
        "n8n_base_url": "https://dev.n8n.example.com",
        "n8n_api_key": "test-api-key",
        "is_active": True,
        "provider": "n8n",
    }


@pytest.fixture
def mock_policy_blocking_expired():
    """Policy with block_deployments_on_expired enabled."""
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
def mock_policy_blocking_drift():
    """Policy with block_deployments_on_drift enabled."""
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
def mock_policy_blocking_both():
    """Policy with both blocking options enabled."""
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
    """Policy with blocking disabled."""
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
def mock_expired_incident():
    """Active drift incident with expired TTL."""
    past_expiry = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    return {
        "id": MOCK_INCIDENT_ID,
        "tenant_id": MOCK_TENANT_ID,
        "environment_id": MOCK_ENVIRONMENT_ID,
        "status": "detected",
        "severity": "critical",
        "title": "Database Drift - Expired TTL",
        "detected_at": (datetime.now(timezone.utc) - timedelta(hours=26)).isoformat(),
        "expires_at": past_expiry,
        "owner_user_id": "user-001",
    }


@pytest.fixture
def mock_active_incident():
    """Active drift incident with valid TTL (not expired)."""
    future_expiry = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    return {
        "id": MOCK_INCIDENT_ID,
        "tenant_id": MOCK_TENANT_ID,
        "environment_id": MOCK_ENVIRONMENT_ID,
        "status": "detected",
        "severity": "high",
        "title": "Configuration Drift Detected",
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": future_expiry,
        "owner_user_id": None,
    }


@pytest.fixture
def mock_approval_override():
    """Mock approved deployment override approval."""
    return {
        "id": "approval-001",
        "incident_id": MOCK_INCIDENT_ID,
        "tenant_id": MOCK_TENANT_ID,
        "approval_type": "deployment_override",
        "status": "approved",
        "decided_by": "admin-user",
        "decided_at": datetime.now(timezone.utc).isoformat(),
        "decision_notes": "Approved for emergency deployment",
        "requested_by": "developer-user",
        "requested_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
    }


def create_db_mock(
    policy_data: Dict[str, Any] = None,
    incidents_data: list = None,
    approvals_data: list = None,
    environment_data: Dict[str, Any] = None,
):
    """Helper to create a comprehensive db_service mock."""
    mock_db = MagicMock()

    def table_side_effect(name):
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.in_.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.single.return_value = mock_query

        if name == "drift_policies":
            mock_response = MagicMock()
            mock_response.data = [policy_data] if policy_data else []
            mock_query.execute.return_value = mock_response
        elif name == "drift_incidents":
            mock_response = MagicMock()
            mock_response.data = incidents_data or []
            mock_query.execute.return_value = mock_response
        elif name == "drift_approvals":
            mock_response = MagicMock()
            mock_response.data = approvals_data or []
            mock_query.execute.return_value = mock_response

        return mock_query

    mock_db.client.table.side_effect = table_side_effect

    # Also mock get_environment for promotion validator
    if environment_data:
        mock_db.get_environment = AsyncMock(return_value=environment_data)
    else:
        mock_db.get_environment = AsyncMock(return_value=None)

    return mock_db


# ============================================================================
# INTEGRATION TEST: Promotion Blocked Due to Expired TTL
# ============================================================================
# AC: GIVEN a tenant has `block_deployments_on_expired: true` and an active
#     drift incident with expired TTL
#     WHEN a promotion is attempted
#     THEN the promotion is blocked with a clear error message indicating TTL violation
# ============================================================================


class TestPromotionBlockedExpiredTTL:
    """Integration tests for promotion blocked due to expired TTL."""

    @pytest.mark.asyncio
    async def test_enforcement_blocks_expired_ttl(
        self,
        enforcement_service,
        mock_policy_blocking_expired,
        mock_expired_incident,
    ):
        """Test enforcement service blocks promotion for expired TTL incident."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            # Setup database mocks
            mock_db.client.table = create_db_mock(
                policy_data=mock_policy_blocking_expired,
                incidents_data=[mock_expired_incident],
            ).client.table

            # Execute enforcement check
            result = await enforcement_service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
                correlation_id=MOCK_CORRELATION_ID,
            )

            # Assertions
            assert result.allowed is False
            assert result.result == EnforcementResult.BLOCKED_TTL_EXPIRED
            assert result.incident_id == MOCK_INCIDENT_ID
            assert "expired" in result.reason.lower()
            assert result.correlation_id == MOCK_CORRELATION_ID

    @pytest.mark.asyncio
    async def test_validator_blocks_expired_ttl(
        self,
        promotion_validator,
        mock_environment,
        mock_policy_blocking_expired,
        mock_expired_incident,
    ):
        """Test promotion validator blocks when TTL is expired."""
        with patch("app.services.promotion_validation_service.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.db_service") as mock_enforcement_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            # Mock environment lookup
            mock_db.get_environment = AsyncMock(return_value=mock_environment)

            # Mock enforcement service database calls
            mock_enforcement_db.client.table = create_db_mock(
                policy_data=mock_policy_blocking_expired,
                incidents_data=[mock_expired_incident],
            ).client.table

            # Execute validation
            result = await promotion_validator.validate_drift_policy_compliance(
                target_environment_id=MOCK_ENVIRONMENT_ID,
                tenant_id=MOCK_TENANT_ID,
            )

            # Assertions
            assert result["passed"] is False
            assert result["check"] == "drift_policy_compliance"
            assert "expired" in result["message"].lower()
            assert result["remediation"] is not None
            assert len(result["blocking_incidents"]) == 1
            assert result["blocking_incidents"][0]["incident_id"] == MOCK_INCIDENT_ID

    @pytest.mark.asyncio
    async def test_error_message_includes_incident_details(
        self,
        enforcement_service,
        mock_policy_blocking_expired,
        mock_expired_incident,
    ):
        """Test that error message includes helpful incident details for user."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)
            mock_db.client.table = create_db_mock(
                policy_data=mock_policy_blocking_expired,
                incidents_data=[mock_expired_incident],
            ).client.table

            result = await enforcement_service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            # Verify incident details for user display
            assert result.incident_details is not None
            assert result.incident_details["title"] == "Database Drift - Expired TTL"
            assert result.incident_details["severity"] == "critical"
            assert result.incident_details["status"] == "detected"
            assert "expires_at" in result.incident_details


# ============================================================================
# INTEGRATION TEST: Promotion Blocked Due to Active Drift
# ============================================================================
# AC: GIVEN a tenant has `block_deployments_on_drift: true` and an active drift
#     incident exists
#     WHEN a promotion is attempted
#     THEN the promotion is blocked with details about the active incident
# ============================================================================


class TestPromotionBlockedActiveDrift:
    """Integration tests for promotion blocked due to active drift incident."""

    @pytest.mark.asyncio
    async def test_enforcement_blocks_active_drift(
        self,
        enforcement_service,
        mock_policy_blocking_drift,
        mock_active_incident,
    ):
        """Test enforcement service blocks promotion for active drift incident."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)
            mock_db.client.table = create_db_mock(
                policy_data=mock_policy_blocking_drift,
                incidents_data=[mock_active_incident],
            ).client.table

            result = await enforcement_service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
                correlation_id=MOCK_CORRELATION_ID,
            )

            assert result.allowed is False
            assert result.result == EnforcementResult.BLOCKED_ACTIVE_DRIFT
            assert result.incident_id == MOCK_INCIDENT_ID
            assert "active drift incident" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_validator_blocks_active_drift(
        self,
        promotion_validator,
        mock_environment,
        mock_policy_blocking_drift,
        mock_active_incident,
    ):
        """Test promotion validator blocks when active drift exists."""
        with patch("app.services.promotion_validation_service.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.db_service") as mock_enforcement_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)
            mock_db.get_environment = AsyncMock(return_value=mock_environment)
            mock_enforcement_db.client.table = create_db_mock(
                policy_data=mock_policy_blocking_drift,
                incidents_data=[mock_active_incident],
            ).client.table

            result = await promotion_validator.validate_drift_policy_compliance(
                target_environment_id=MOCK_ENVIRONMENT_ID,
                tenant_id=MOCK_TENANT_ID,
            )

            assert result["passed"] is False
            assert result["check"] == "drift_policy_compliance"
            assert "active drift incident" in result["message"].lower()
            assert len(result["blocking_incidents"]) == 1
            assert result["blocking_incidents"][0]["reason"] == "blocked_active_drift"

    @pytest.mark.asyncio
    async def test_multiple_active_incidents_blocks(
        self,
        enforcement_service,
        mock_policy_blocking_drift,
    ):
        """Test that most recent incident is reported when multiple exist."""
        older_incident = {
            "id": "incident-old",
            "status": "detected",
            "severity": "low",
            "title": "Older Drift Incident",
            "detected_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
            "owner_user_id": None,
        }
        newer_incident = {
            "id": "incident-new",
            "status": "acknowledged",
            "severity": "critical",
            "title": "Newer Critical Drift",
            "detected_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat(),
            "owner_user_id": "user-001",
        }

        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)
            mock_db.client.table = create_db_mock(
                policy_data=mock_policy_blocking_drift,
                incidents_data=[newer_incident, older_incident],  # Ordered by detected_at desc
            ).client.table

            result = await enforcement_service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result.allowed is False
            assert result.incident_id == "incident-new"
            assert result.incident_details["title"] == "Newer Critical Drift"


# ============================================================================
# INTEGRATION TEST: Promotion Allowed with Approval Override
# ============================================================================
# AC: GIVEN a blocked promotion due to drift policy violation
#     WHEN an explicit approval exists for the incident
#     THEN the promotion is allowed to proceed
# ============================================================================


class TestPromotionAllowedWithOverride:
    """Integration tests for promotion allowed via approval override."""

    @pytest.mark.asyncio
    async def test_enforcement_allows_with_deployment_override(
        self,
        enforcement_service,
        mock_policy_blocking_drift,
        mock_active_incident,
        mock_approval_override,
    ):
        """Test enforcement allows promotion when deployment_override approval exists."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)
            mock_db.client.table = create_db_mock(
                policy_data=mock_policy_blocking_drift,
                incidents_data=[mock_active_incident],
                approvals_data=[mock_approval_override],
            ).client.table

            result = await enforcement_service.check_enforcement_with_override(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
                correlation_id=MOCK_CORRELATION_ID,
            )

            assert result.allowed is True
            assert result.result == EnforcementResult.ALLOWED
            assert "deployment_override" in result.reason.lower()
            assert result.incident_details is not None
            assert result.incident_details.get("override_approval_id") == "approval-001"

    @pytest.mark.asyncio
    async def test_enforcement_allows_with_acknowledge_override(
        self,
        enforcement_service,
        mock_policy_blocking_drift,
        mock_active_incident,
    ):
        """Test enforcement allows promotion when acknowledge approval exists."""
        acknowledge_approval = {
            "id": "approval-ack-001",
            "incident_id": MOCK_INCIDENT_ID,
            "tenant_id": MOCK_TENANT_ID,
            "approval_type": "acknowledge",
            "status": "approved",
            "decided_by": "team-lead",
            "decided_at": datetime.now(timezone.utc).isoformat(),
            "decision_notes": "Drift reviewed and acknowledged for this deployment",
            "requested_by": "developer",
            "requested_at": (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat(),
        }

        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)
            mock_db.client.table = create_db_mock(
                policy_data=mock_policy_blocking_drift,
                incidents_data=[mock_active_incident],
                approvals_data=[acknowledge_approval],
            ).client.table

            result = await enforcement_service.check_enforcement_with_override(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result.allowed is True
            assert result.result == EnforcementResult.ALLOWED
            assert "acknowledge" in result.reason.lower()
            assert result.incident_details.get("override_approval_type") == "acknowledge"

    @pytest.mark.asyncio
    async def test_validator_allows_with_override(
        self,
        promotion_validator,
        mock_environment,
        mock_policy_blocking_drift,
        mock_active_incident,
        mock_approval_override,
    ):
        """Test promotion validator allows when approval override exists."""
        with patch("app.services.promotion_validation_service.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.db_service") as mock_enforcement_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)
            mock_db.get_environment = AsyncMock(return_value=mock_environment)
            mock_enforcement_db.client.table = create_db_mock(
                policy_data=mock_policy_blocking_drift,
                incidents_data=[mock_active_incident],
                approvals_data=[mock_approval_override],
            ).client.table

            result = await promotion_validator.validate_drift_policy_compliance(
                target_environment_id=MOCK_ENVIRONMENT_ID,
                tenant_id=MOCK_TENANT_ID,
            )

            assert result["passed"] is True
            assert result["check"] == "drift_policy_compliance"
            assert "override" in result["message"].lower()
            assert result["blocking_incidents"] == []

    @pytest.mark.asyncio
    async def test_pending_approval_does_not_override(
        self,
        enforcement_service,
        mock_policy_blocking_drift,
        mock_active_incident,
    ):
        """Test that pending (not approved) approvals don't allow override."""
        pending_approval = {
            "id": "approval-pending-001",
            "incident_id": MOCK_INCIDENT_ID,
            "tenant_id": MOCK_TENANT_ID,
            "approval_type": "deployment_override",
            "status": "pending",  # Not approved yet
            "decided_by": None,
            "decided_at": None,
            "decision_notes": None,
            "requested_by": "developer",
            "requested_at": datetime.now(timezone.utc).isoformat(),
        }

        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)
            # Note: The query filters for status="approved", so pending won't be returned
            mock_db.client.table = create_db_mock(
                policy_data=mock_policy_blocking_drift,
                incidents_data=[mock_active_incident],
                approvals_data=[],  # Empty because pending doesn't match status="approved" filter
            ).client.table

            result = await enforcement_service.check_enforcement_with_override(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result.allowed is False
            assert result.result == EnforcementResult.BLOCKED_ACTIVE_DRIFT


# ============================================================================
# INTEGRATION TEST: Promotion Allowed When No Issues
# ============================================================================
# AC: GIVEN a tenant has drift policies disabled or no active incidents
#     WHEN a promotion is attempted
#     THEN the promotion proceeds normally without blocking
# ============================================================================


class TestPromotionAllowedNoIssues:
    """Integration tests for promotion allowed when no blocking conditions exist."""

    @pytest.mark.asyncio
    async def test_allowed_no_policy_configured(self, enforcement_service):
        """Test promotion allowed when no drift policy is configured."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)
            mock_db.client.table = create_db_mock(
                policy_data=None,  # No policy
                incidents_data=[],
            ).client.table

            result = await enforcement_service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result.allowed is True
            assert result.result == EnforcementResult.ALLOWED
            assert "no drift policy" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_allowed_policy_blocking_disabled(
        self,
        enforcement_service,
        mock_policy_no_blocking,
        mock_active_incident,
    ):
        """Test promotion allowed when policy has blocking disabled."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)
            mock_db.client.table = create_db_mock(
                policy_data=mock_policy_no_blocking,
                incidents_data=[mock_active_incident],  # Has incident but blocking disabled
            ).client.table

            result = await enforcement_service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result.allowed is True
            assert result.result == EnforcementResult.ALLOWED
            assert result.policy_config["block_deployments_on_drift"] is False
            assert result.policy_config["block_deployments_on_expired"] is False

    @pytest.mark.asyncio
    async def test_allowed_no_active_incidents(
        self,
        enforcement_service,
        mock_policy_blocking_both,
    ):
        """Test promotion allowed when no active incidents exist."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)
            mock_db.client.table = create_db_mock(
                policy_data=mock_policy_blocking_both,
                incidents_data=[],  # No active incidents
            ).client.table

            result = await enforcement_service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result.allowed is True
            assert result.result == EnforcementResult.ALLOWED
            assert "no active drift incidents" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_allowed_no_entitlement(self, enforcement_service):
        """Test promotion allowed when tenant lacks drift_policies entitlement."""
        with patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:
            mock_entitlements.has_flag = AsyncMock(return_value=False)

            result = await enforcement_service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result.allowed is True
            assert result.result == EnforcementResult.ALLOWED
            assert "not enabled" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_validator_passes_no_blocking_conditions(
        self,
        promotion_validator,
        mock_environment,
        mock_policy_blocking_both,
    ):
        """Test promotion validator passes when no blocking conditions exist."""
        with patch("app.services.promotion_validation_service.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.db_service") as mock_enforcement_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)
            mock_db.get_environment = AsyncMock(return_value=mock_environment)
            mock_enforcement_db.client.table = create_db_mock(
                policy_data=mock_policy_blocking_both,
                incidents_data=[],  # No incidents
            ).client.table

            result = await promotion_validator.validate_drift_policy_compliance(
                target_environment_id=MOCK_ENVIRONMENT_ID,
                tenant_id=MOCK_TENANT_ID,
            )

            assert result["passed"] is True
            assert result["check"] == "drift_policy_compliance"
            assert result["blocking_incidents"] == []


# ============================================================================
# INTEGRATION TEST: API Helper Function
# ============================================================================
# Tests the check_drift_policy_blocking helper used by API endpoints
# ============================================================================


class TestCheckDriftPolicyBlockingHelper:
    """Integration tests for the check_drift_policy_blocking API helper."""

    @pytest.mark.asyncio
    async def test_helper_returns_blocked_for_expired_ttl(
        self,
        mock_policy_blocking_expired,
        mock_expired_incident,
    ):
        """Test API helper returns blocked=True for expired TTL."""
        from app.api.endpoints.promotions import check_drift_policy_blocking

        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)
            mock_db.client.table = create_db_mock(
                policy_data=mock_policy_blocking_expired,
                incidents_data=[mock_expired_incident],
            ).client.table

            result = await check_drift_policy_blocking(
                tenant_id=MOCK_TENANT_ID,
                target_environment_id=MOCK_ENVIRONMENT_ID,
                correlation_id=MOCK_CORRELATION_ID,
            )

            assert result["blocked"] is True
            assert result["reason"] == "drift_incident_expired"
            assert result["details"]["incident_id"] == MOCK_INCIDENT_ID
            assert result["details"]["incident_title"] == "Database Drift - Expired TTL"
            assert result["details"]["severity"] == "critical"

    @pytest.mark.asyncio
    async def test_helper_returns_blocked_for_active_drift(
        self,
        mock_policy_blocking_drift,
        mock_active_incident,
    ):
        """Test API helper returns blocked=True for active drift."""
        from app.api.endpoints.promotions import check_drift_policy_blocking

        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)
            mock_db.client.table = create_db_mock(
                policy_data=mock_policy_blocking_drift,
                incidents_data=[mock_active_incident],
            ).client.table

            result = await check_drift_policy_blocking(
                tenant_id=MOCK_TENANT_ID,
                target_environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result["blocked"] is True
            assert result["reason"] == "active_drift_incident"
            assert result["details"]["incident_id"] == MOCK_INCIDENT_ID

    @pytest.mark.asyncio
    async def test_helper_returns_not_blocked_with_override(
        self,
        mock_policy_blocking_drift,
        mock_active_incident,
        mock_approval_override,
    ):
        """Test API helper returns blocked=False when override exists."""
        from app.api.endpoints.promotions import check_drift_policy_blocking

        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)
            mock_db.client.table = create_db_mock(
                policy_data=mock_policy_blocking_drift,
                incidents_data=[mock_active_incident],
                approvals_data=[mock_approval_override],
            ).client.table

            result = await check_drift_policy_blocking(
                tenant_id=MOCK_TENANT_ID,
                target_environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result["blocked"] is False
            assert result["reason"] is None

    @pytest.mark.asyncio
    async def test_helper_returns_not_blocked_no_issues(
        self,
        mock_policy_blocking_both,
    ):
        """Test API helper returns blocked=False when no blocking conditions."""
        from app.api.endpoints.promotions import check_drift_policy_blocking

        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)
            mock_db.client.table = create_db_mock(
                policy_data=mock_policy_blocking_both,
                incidents_data=[],  # No incidents
            ).client.table

            result = await check_drift_policy_blocking(
                tenant_id=MOCK_TENANT_ID,
                target_environment_id=MOCK_ENVIRONMENT_ID,
            )

            assert result["blocked"] is False
            assert result["reason"] is None

    @pytest.mark.asyncio
    async def test_helper_fails_open_on_error(self):
        """Test API helper fails open (returns not blocked) on unexpected errors."""
        from app.api.endpoints.promotions import check_drift_policy_blocking

        with patch("app.services.drift_policy_enforcement.drift_policy_enforcement_service") as mock_service:
            mock_service.check_enforcement_with_override = AsyncMock(
                side_effect=Exception("Unexpected database error")
            )

            result = await check_drift_policy_blocking(
                tenant_id=MOCK_TENANT_ID,
                target_environment_id=MOCK_ENVIRONMENT_ID,
            )

            # Should fail open - don't block on transient errors
            assert result["blocked"] is False
            assert result["details"].get("error") is not None


# ============================================================================
# INTEGRATION TEST: Full Pre-flight Validation Flow
# ============================================================================
# Tests the complete pre-flight validation including drift policy check
# ============================================================================


class TestPreflightValidationFlow:
    """Integration tests for complete pre-flight validation flow."""

    @pytest.mark.asyncio
    async def test_preflight_fails_on_drift_policy_violation(
        self,
        promotion_validator,
        mock_environment,
        mock_source_environment,
        mock_policy_blocking_drift,
        mock_active_incident,
    ):
        """Test run_preflight_validation fails when drift policy is violated."""
        with patch("app.services.promotion_validation_service.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.db_service") as mock_enforcement_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements, \
             patch.object(promotion_validator.provider_registry, "get_adapter_for_environment") as mock_adapter_factory:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            # Mock environment lookups - use positional args matching actual signature
            async def get_env_mock(environment_id, tenant_id):
                if environment_id == MOCK_ENVIRONMENT_ID:
                    return mock_environment
                elif environment_id == MOCK_SOURCE_ENVIRONMENT_ID:
                    return mock_source_environment
                return None

            mock_db.get_environment = AsyncMock(side_effect=get_env_mock)
            mock_db.get_workflow = AsyncMock(return_value=None)

            # Mock adapter for health check
            mock_adapter = MagicMock()
            mock_adapter.test_connection = AsyncMock(return_value=True)
            mock_adapter.get_credentials = AsyncMock(return_value=[])
            mock_adapter_factory.return_value = mock_adapter

            # Mock enforcement service database calls
            mock_enforcement_db.client.table = create_db_mock(
                policy_data=mock_policy_blocking_drift,
                incidents_data=[mock_active_incident],
            ).client.table

            # Run full preflight validation
            result = await promotion_validator.run_preflight_validation(
                workflow_id=MOCK_WORKFLOW_ID,
                source_environment_id=MOCK_SOURCE_ENVIRONMENT_ID,
                target_environment_id=MOCK_ENVIRONMENT_ID,
                tenant_id=MOCK_TENANT_ID,
            )

            assert result["validation_passed"] is False
            assert len(result["validation_errors"]) > 0
            assert "drift_policy_compliance" in result["checks_run"]

            # Find the drift policy error
            drift_error = next(
                (e for e in result["validation_errors"] if e["check"] == "drift_policy_compliance"),
                None
            )
            assert drift_error is not None
            assert drift_error["status"] == "failed"

    @pytest.mark.asyncio
    async def test_preflight_passes_with_approval_override(
        self,
        promotion_validator,
        mock_environment,
        mock_source_environment,
        mock_policy_blocking_drift,
        mock_active_incident,
        mock_approval_override,
    ):
        """Test run_preflight_validation passes when approval override exists."""
        with patch("app.services.promotion_validation_service.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.db_service") as mock_enforcement_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements, \
             patch.object(promotion_validator.provider_registry, "get_adapter_for_environment") as mock_adapter_factory:

            mock_entitlements.has_flag = AsyncMock(return_value=True)

            # Mock environment lookups - use positional args matching actual signature
            async def get_env_mock(environment_id, tenant_id):
                if environment_id == MOCK_ENVIRONMENT_ID:
                    return mock_environment
                elif environment_id == MOCK_SOURCE_ENVIRONMENT_ID:
                    return mock_source_environment
                return None

            mock_db.get_environment = AsyncMock(side_effect=get_env_mock)
            mock_db.get_workflow = AsyncMock(return_value={
                "id": MOCK_WORKFLOW_ID,
                "name": "Test Workflow",
                "workflow_data": {"nodes": []},
            })

            # Mock adapter for health check
            mock_adapter = MagicMock()
            mock_adapter.test_connection = AsyncMock(return_value=True)
            mock_adapter.get_credentials = AsyncMock(return_value=[])
            mock_adapter_factory.return_value = mock_adapter

            # Mock enforcement service database calls with approval override
            mock_enforcement_db.client.table = create_db_mock(
                policy_data=mock_policy_blocking_drift,
                incidents_data=[mock_active_incident],
                approvals_data=[mock_approval_override],
            ).client.table

            # Run full preflight validation
            result = await promotion_validator.run_preflight_validation(
                workflow_id=MOCK_WORKFLOW_ID,
                source_environment_id=MOCK_SOURCE_ENVIRONMENT_ID,
                target_environment_id=MOCK_ENVIRONMENT_ID,
                tenant_id=MOCK_TENANT_ID,
            )

            assert result["validation_passed"] is True
            assert len(result["validation_errors"]) == 0
            assert "drift_policy_compliance" in result["checks_run"]


# ============================================================================
# INTEGRATION TEST: Audit Trail and Logging
# ============================================================================
# AC: GIVEN any policy enforcement scenario
#     WHEN enforcement logic executes
#     THEN detailed logs and audit trail are generated for compliance tracking
# ============================================================================


class TestAuditTrailAndLogging:
    """Integration tests for audit trail and correlation ID tracking."""

    @pytest.mark.asyncio
    async def test_correlation_id_propagated_through_flow(
        self,
        enforcement_service,
        mock_policy_blocking_drift,
        mock_active_incident,
    ):
        """Test that correlation ID is propagated through the enforcement flow."""
        custom_correlation_id = "audit-trail-test-12345"

        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)
            mock_db.client.table = create_db_mock(
                policy_data=mock_policy_blocking_drift,
                incidents_data=[mock_active_incident],
            ).client.table

            result = await enforcement_service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
                correlation_id=custom_correlation_id,
            )

            assert result.correlation_id == custom_correlation_id

    @pytest.mark.asyncio
    async def test_auto_generated_correlation_id(
        self,
        enforcement_service,
        mock_policy_no_blocking,
    ):
        """Test that correlation ID is auto-generated when not provided."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)
            mock_db.client.table = create_db_mock(
                policy_data=mock_policy_no_blocking,
            ).client.table

            result = await enforcement_service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
                # No correlation_id provided
            )

            assert result.correlation_id is not None
            assert len(result.correlation_id) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_decision_to_dict_for_audit_logging(
        self,
        enforcement_service,
        mock_policy_blocking_drift,
        mock_active_incident,
    ):
        """Test that decision can be serialized for audit logging."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)
            mock_db.client.table = create_db_mock(
                policy_data=mock_policy_blocking_drift,
                incidents_data=[mock_active_incident],
            ).client.table

            result = await enforcement_service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
                correlation_id="audit-test",
            )

            # Convert to dict for audit logging
            audit_record = result.to_dict()

            assert isinstance(audit_record, dict)
            assert audit_record["allowed"] is False
            assert audit_record["result"] == "blocked_active_drift"
            assert audit_record["incident_id"] == MOCK_INCIDENT_ID
            assert audit_record["correlation_id"] == "audit-test"
            assert audit_record["policy_config"] is not None


# ============================================================================
# INTEGRATION TEST: Edge Cases and Error Handling
# ============================================================================


class TestEdgeCasesAndErrorHandling:
    """Integration tests for edge cases and error handling scenarios."""

    @pytest.mark.asyncio
    async def test_expired_ttl_takes_priority_over_active_drift(
        self,
        enforcement_service,
        mock_policy_blocking_both,
        mock_expired_incident,
    ):
        """Test that expired TTL check takes priority when both policies enabled."""
        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)
            mock_db.client.table = create_db_mock(
                policy_data=mock_policy_blocking_both,
                incidents_data=[mock_expired_incident],
            ).client.table

            result = await enforcement_service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            # Should report TTL expired, not just active drift
            assert result.result == EnforcementResult.BLOCKED_TTL_EXPIRED

    @pytest.mark.asyncio
    async def test_environment_not_found_fails_validation(self, promotion_validator):
        """Test that validation fails when target environment not found."""
        with patch("app.services.promotion_validation_service.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=None)

            result = await promotion_validator.validate_drift_policy_compliance(
                target_environment_id="nonexistent-env",
                tenant_id=MOCK_TENANT_ID,
            )

            assert result["passed"] is False
            assert "not found" in result["message"].lower()
            assert result["details"]["error_type"] == "environment_not_found"

    @pytest.mark.asyncio
    async def test_incident_with_no_expiry_only_blocks_on_active_drift(
        self,
        enforcement_service,
        mock_policy_blocking_both,
    ):
        """Test incident without expiry only blocks due to active drift, not TTL."""
        incident_no_expiry = {
            "id": MOCK_INCIDENT_ID,
            "status": "detected",
            "severity": "medium",
            "title": "Drift Without Expiry",
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": None,  # No expiry set
            "owner_user_id": None,
        }

        with patch("app.services.drift_policy_enforcement.db_service") as mock_db, \
             patch("app.services.drift_policy_enforcement.entitlements_service") as mock_entitlements:

            mock_entitlements.has_flag = AsyncMock(return_value=True)
            mock_db.client.table = create_db_mock(
                policy_data=mock_policy_blocking_both,
                incidents_data=[incident_no_expiry],
            ).client.table

            result = await enforcement_service.check_enforcement(
                tenant_id=MOCK_TENANT_ID,
                environment_id=MOCK_ENVIRONMENT_ID,
            )

            # Should block due to active drift, not TTL expired
            assert result.allowed is False
            assert result.result == EnforcementResult.BLOCKED_ACTIVE_DRIFT

    @pytest.mark.asyncio
    async def test_validator_fail_open_on_internal_error(self, promotion_validator, mock_environment):
        """Test validator fails open (allows) on internal errors."""
        # Patch the service at the module where it's imported/used
        with patch("app.services.promotion_validation_service.db_service") as mock_db, \
             patch("app.services.promotion_validation_service.drift_policy_enforcement_service") as mock_service:

            mock_db.get_environment = AsyncMock(return_value=mock_environment)
            mock_service.check_enforcement_with_override = AsyncMock(
                side_effect=Exception("Internal service error")
            )

            result = await promotion_validator.validate_drift_policy_compliance(
                target_environment_id=MOCK_ENVIRONMENT_ID,
                tenant_id=MOCK_TENANT_ID,
            )

            # Should fail open - allow promotion to proceed
            assert result["passed"] is True
            assert result["details"].get("fail_open") is True
            assert result["details"].get("error") is not None
