"""
Unit tests for the Gated Action Service.
Tests the approval enforcement workflow for drift incident actions.
"""
import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.gated_action_service import (
    GatedActionService,
    gated_action_service,
    GatedActionType,
    ApprovalRequirement,
    GatedActionDecision,
)
from app.schemas.drift_policy import ApprovalStatus


# Test fixtures
MOCK_TENANT_ID = "00000000-0000-0000-0000-000000000001"
MOCK_USER_ID = "00000000-0000-0000-0000-000000000002"
MOCK_INCIDENT_ID = "incident-001"
MOCK_APPROVAL_ID = "approval-001"


@pytest.fixture
def mock_policy():
    """Create a mock drift policy with approval requirements."""
    return {
        "id": "policy-001",
        "tenant_id": MOCK_TENANT_ID,
        "require_approval_for_acknowledge": True,
        "require_approval_for_extend_ttl": True,
        "require_approval_for_reconcile": True,
        "approval_expiry_hours": 72,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_policy_no_approvals():
    """Create a mock drift policy without approval requirements."""
    return {
        "id": "policy-002",
        "tenant_id": MOCK_TENANT_ID,
        "require_approval_for_acknowledge": False,
        "require_approval_for_extend_ttl": False,
        "require_approval_for_reconcile": False,
        "approval_expiry_hours": 72,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_pending_approval():
    """Create a mock pending approval."""
    return {
        "id": MOCK_APPROVAL_ID,
        "tenant_id": MOCK_TENANT_ID,
        "incident_id": MOCK_INCIDENT_ID,
        "approval_type": "acknowledge",
        "status": ApprovalStatus.pending.value,
        "requested_by": MOCK_USER_ID,
        "requested_at": datetime.utcnow().isoformat(),
        "request_reason": "Need to acknowledge this drift",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_approved_approval():
    """Create a mock approved approval."""
    return {
        "id": MOCK_APPROVAL_ID,
        "tenant_id": MOCK_TENANT_ID,
        "incident_id": MOCK_INCIDENT_ID,
        "approval_type": "acknowledge",
        "status": ApprovalStatus.approved.value,
        "requested_by": MOCK_USER_ID,
        "requested_at": datetime.utcnow().isoformat(),
        "request_reason": "Need to acknowledge this drift",
        "decided_by": "approver-001",
        "decided_at": datetime.utcnow().isoformat(),
        "decision_notes": "Approved",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_rejected_approval():
    """Create a mock rejected approval."""
    return {
        "id": MOCK_APPROVAL_ID,
        "tenant_id": MOCK_TENANT_ID,
        "incident_id": MOCK_INCIDENT_ID,
        "approval_type": "acknowledge",
        "status": ApprovalStatus.rejected.value,
        "requested_by": MOCK_USER_ID,
        "requested_at": datetime.utcnow().isoformat(),
        "request_reason": "Need to acknowledge this drift",
        "decided_by": "approver-001",
        "decided_at": datetime.utcnow().isoformat(),
        "decision_notes": "Rejected - needs more investigation",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_incident():
    """Create a mock drift incident."""
    return {
        "id": MOCK_INCIDENT_ID,
        "tenant_id": MOCK_TENANT_ID,
        "environment_id": "env-001",
        "status": "detected",
        "title": "Test Drift Incident",
        "detected_at": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


class TestGatedActionDecision:
    """Test GatedActionDecision dataclass."""

    def test_to_dict_conversion(self):
        """Test converting decision to dictionary."""
        decision = GatedActionDecision(
            allowed=True,
            requirement=ApprovalRequirement.NOT_REQUIRED,
            reason="Test reason",
            approval_id="test-approval",
            approval_details={"status": "approved"},
            policy_config={"approval_required": False},
        )

        result = decision.to_dict()

        assert result["allowed"] is True
        assert result["requirement"] == "not_required"
        assert result["reason"] == "Test reason"
        assert result["approval_id"] == "test-approval"
        assert result["approval_details"]["status"] == "approved"
        assert result["policy_config"]["approval_required"] is False

    def test_to_dict_with_minimal_data(self):
        """Test converting minimal decision to dictionary."""
        decision = GatedActionDecision(
            allowed=False,
            requirement=ApprovalRequirement.REQUIRED_NO_REQUEST,
        )

        result = decision.to_dict()

        assert result["allowed"] is False
        assert result["requirement"] == "required_no_request"
        assert result["reason"] is None
        assert result["approval_id"] is None
        assert result["approval_details"] is None
        assert result["policy_config"] is None


class TestGetTenantPolicy:
    """Tests for get_tenant_policy method."""

    @pytest.mark.asyncio
    async def test_get_policy_success(self, mock_policy):
        """Test successful retrieval of tenant policy."""
        mock_response = MagicMock()
        mock_response.data = [mock_policy]

        with patch("app.services.gated_action_service.db_service") as mock_db:
            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.execute.return_value = mock_response
            mock_db.client.table.return_value = mock_query

            service = GatedActionService()
            result = await service.get_tenant_policy(MOCK_TENANT_ID)

            assert result == mock_policy
            mock_db.client.table.assert_called_once_with("drift_policies")
            mock_query.eq.assert_called_once_with("tenant_id", MOCK_TENANT_ID)

    @pytest.mark.asyncio
    async def test_get_policy_not_found(self):
        """Test getting policy when none exists."""
        mock_response = MagicMock()
        mock_response.data = []

        with patch("app.services.gated_action_service.db_service") as mock_db:
            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.execute.return_value = mock_response
            mock_db.client.table.return_value = mock_query

            service = GatedActionService()
            result = await service.get_tenant_policy(MOCK_TENANT_ID)

            assert result is None

    @pytest.mark.asyncio
    async def test_get_policy_error_handling(self):
        """Test that errors are handled gracefully."""
        with patch("app.services.gated_action_service.db_service") as mock_db:
            mock_db.client.table.side_effect = Exception("Database error")

            service = GatedActionService()
            result = await service.get_tenant_policy(MOCK_TENANT_ID)

            assert result is None


class TestIsApprovalRequiredByPolicy:
    """Tests for is_approval_required_by_policy method."""

    def test_acknowledge_approval_required(self, mock_policy):
        """Test acknowledge action requires approval when policy says so."""
        service = GatedActionService()
        result = service.is_approval_required_by_policy(
            mock_policy, GatedActionType.ACKNOWLEDGE
        )
        assert result is True

    def test_extend_ttl_approval_required(self, mock_policy):
        """Test extend TTL action requires approval when policy says so."""
        service = GatedActionService()
        result = service.is_approval_required_by_policy(
            mock_policy, GatedActionType.EXTEND_TTL
        )
        assert result is True

    def test_reconcile_approval_required(self, mock_policy):
        """Test reconcile action requires approval when policy says so."""
        service = GatedActionService()
        result = service.is_approval_required_by_policy(
            mock_policy, GatedActionType.RECONCILE
        )
        assert result is True

    def test_acknowledge_approval_not_required(self, mock_policy_no_approvals):
        """Test acknowledge action does not require approval when policy says so."""
        service = GatedActionService()
        result = service.is_approval_required_by_policy(
            mock_policy_no_approvals, GatedActionType.ACKNOWLEDGE
        )
        assert result is False

    def test_extend_ttl_approval_not_required(self, mock_policy_no_approvals):
        """Test extend TTL action does not require approval when policy says so."""
        service = GatedActionService()
        result = service.is_approval_required_by_policy(
            mock_policy_no_approvals, GatedActionType.EXTEND_TTL
        )
        assert result is False

    def test_reconcile_approval_not_required(self, mock_policy_no_approvals):
        """Test reconcile action does not require approval when policy says so."""
        service = GatedActionService()
        result = service.is_approval_required_by_policy(
            mock_policy_no_approvals, GatedActionType.RECONCILE
        )
        assert result is False

    def test_no_policy_returns_false(self):
        """Test that no policy returns False (fail-safe)."""
        service = GatedActionService()
        result = service.is_approval_required_by_policy(
            None, GatedActionType.ACKNOWLEDGE
        )
        assert result is False

    def test_policy_missing_keys_returns_false(self):
        """Test that policy missing approval keys returns False."""
        service = GatedActionService()
        incomplete_policy = {"id": "test", "tenant_id": MOCK_TENANT_ID}
        result = service.is_approval_required_by_policy(
            incomplete_policy, GatedActionType.ACKNOWLEDGE
        )
        assert result is False


class TestGetPendingApproval:
    """Tests for get_pending_approval method."""

    @pytest.mark.asyncio
    async def test_get_pending_approval_success(self, mock_pending_approval):
        """Test successful retrieval of pending approval."""
        mock_response = MagicMock()
        mock_response.data = [mock_pending_approval]

        with patch("app.services.gated_action_service.db_service") as mock_db:
            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.order.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.execute.return_value = mock_response
            mock_db.client.table.return_value = mock_query

            service = GatedActionService()
            result = await service.get_pending_approval(
                MOCK_TENANT_ID, MOCK_INCIDENT_ID, GatedActionType.ACKNOWLEDGE
            )

            assert result == mock_pending_approval

    @pytest.mark.asyncio
    async def test_get_pending_approval_not_found(self):
        """Test getting pending approval when none exists."""
        mock_response = MagicMock()
        mock_response.data = []

        with patch("app.services.gated_action_service.db_service") as mock_db:
            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.order.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.execute.return_value = mock_response
            mock_db.client.table.return_value = mock_query

            service = GatedActionService()
            result = await service.get_pending_approval(
                MOCK_TENANT_ID, MOCK_INCIDENT_ID, GatedActionType.ACKNOWLEDGE
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_get_pending_approval_error_handling(self):
        """Test that errors are handled gracefully."""
        with patch("app.services.gated_action_service.db_service") as mock_db:
            mock_db.client.table.side_effect = Exception("Database error")

            service = GatedActionService()
            result = await service.get_pending_approval(
                MOCK_TENANT_ID, MOCK_INCIDENT_ID, GatedActionType.ACKNOWLEDGE
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_get_pending_approval_action_type_mapping(self):
        """Test that action types are correctly mapped to approval types."""
        mock_response = MagicMock()
        mock_response.data = []

        with patch("app.services.gated_action_service.db_service") as mock_db:
            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.order.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.execute.return_value = mock_response
            mock_db.client.table.return_value = mock_query

            service = GatedActionService()

            # Test each action type
            await service.get_pending_approval(
                MOCK_TENANT_ID, MOCK_INCIDENT_ID, GatedActionType.ACKNOWLEDGE
            )
            await service.get_pending_approval(
                MOCK_TENANT_ID, MOCK_INCIDENT_ID, GatedActionType.EXTEND_TTL
            )
            await service.get_pending_approval(
                MOCK_TENANT_ID, MOCK_INCIDENT_ID, GatedActionType.RECONCILE
            )

            # Verify all action types were handled
            assert mock_query.eq.call_count >= 9  # 3 calls per test (tenant_id, incident_id, approval_type)


class TestGetApprovedApproval:
    """Tests for get_approved_approval method."""

    @pytest.mark.asyncio
    async def test_get_approved_approval_success(self, mock_approved_approval):
        """Test successful retrieval of approved approval."""
        mock_response = MagicMock()
        mock_response.data = [mock_approved_approval]

        with patch("app.services.gated_action_service.db_service") as mock_db:
            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.order.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.execute.return_value = mock_response
            mock_db.client.table.return_value = mock_query

            service = GatedActionService()
            result = await service.get_approved_approval(
                MOCK_TENANT_ID, MOCK_INCIDENT_ID, GatedActionType.ACKNOWLEDGE
            )

            assert result == mock_approved_approval

    @pytest.mark.asyncio
    async def test_get_approved_approval_not_found(self):
        """Test getting approved approval when none exists."""
        mock_response = MagicMock()
        mock_response.data = []

        with patch("app.services.gated_action_service.db_service") as mock_db:
            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.order.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.execute.return_value = mock_response
            mock_db.client.table.return_value = mock_query

            service = GatedActionService()
            result = await service.get_approved_approval(
                MOCK_TENANT_ID, MOCK_INCIDENT_ID, GatedActionType.ACKNOWLEDGE
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_get_approved_approval_error_handling(self):
        """Test that errors are handled gracefully."""
        with patch("app.services.gated_action_service.db_service") as mock_db:
            mock_db.client.table.side_effect = Exception("Database error")

            service = GatedActionService()
            result = await service.get_approved_approval(
                MOCK_TENANT_ID, MOCK_INCIDENT_ID, GatedActionType.ACKNOWLEDGE
            )

            assert result is None


class TestCheckApprovalStatus:
    """Tests for check_approval_status method - the main entry point."""

    @pytest.mark.asyncio
    async def test_approval_not_required(self, mock_policy_no_approvals):
        """Test action is allowed when approval is not required by policy."""
        service = GatedActionService()

        with patch.object(service, "get_tenant_policy", new_callable=AsyncMock) as mock_get_policy:
            mock_get_policy.return_value = mock_policy_no_approvals

            result = await service.check_approval_status(
                MOCK_TENANT_ID, MOCK_INCIDENT_ID, GatedActionType.ACKNOWLEDGE
            )

            assert result.allowed is True
            assert result.requirement == ApprovalRequirement.NOT_REQUIRED
            assert "not required" in result.reason.lower()
            assert result.approval_id is None

    @pytest.mark.asyncio
    async def test_approval_not_required_no_policy(self):
        """Test action is allowed when no policy exists (fail-safe to allow)."""
        service = GatedActionService()

        with patch.object(service, "get_tenant_policy", new_callable=AsyncMock) as mock_get_policy:
            mock_get_policy.return_value = None

            result = await service.check_approval_status(
                MOCK_TENANT_ID, MOCK_INCIDENT_ID, GatedActionType.ACKNOWLEDGE
            )

            assert result.allowed is True
            assert result.requirement == ApprovalRequirement.NOT_REQUIRED

    @pytest.mark.asyncio
    async def test_approval_required_and_approved(self, mock_policy, mock_approved_approval):
        """Test action is allowed when approval is required and granted."""
        service = GatedActionService()

        with patch.object(service, "get_tenant_policy", new_callable=AsyncMock) as mock_get_policy:
            mock_get_policy.return_value = mock_policy

            with patch.object(service, "get_approved_approval", new_callable=AsyncMock) as mock_get_approved:
                mock_get_approved.return_value = mock_approved_approval

                result = await service.check_approval_status(
                    MOCK_TENANT_ID, MOCK_INCIDENT_ID, GatedActionType.ACKNOWLEDGE, MOCK_USER_ID
                )

                assert result.allowed is True
                assert result.requirement == ApprovalRequirement.REQUIRED_APPROVED
                assert result.approval_id == MOCK_APPROVAL_ID
                assert result.approval_details["status"] == ApprovalStatus.approved.value
                assert result.approval_details["decided_by"] == "approver-001"
                assert "granted" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_approval_required_and_pending(self, mock_policy, mock_pending_approval):
        """Test action is blocked when approval is required and pending."""
        service = GatedActionService()

        with patch.object(service, "get_tenant_policy", new_callable=AsyncMock) as mock_get_policy:
            mock_get_policy.return_value = mock_policy

            with patch.object(service, "get_approved_approval", new_callable=AsyncMock) as mock_get_approved:
                mock_get_approved.return_value = None

                with patch.object(service, "get_pending_approval", new_callable=AsyncMock) as mock_get_pending:
                    mock_get_pending.return_value = mock_pending_approval

                    result = await service.check_approval_status(
                        MOCK_TENANT_ID, MOCK_INCIDENT_ID, GatedActionType.ACKNOWLEDGE
                    )

                    assert result.allowed is False
                    assert result.requirement == ApprovalRequirement.REQUIRED_PENDING
                    assert result.approval_id == MOCK_APPROVAL_ID
                    assert result.approval_details["status"] == ApprovalStatus.pending.value
                    assert "pending" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_approval_required_and_rejected(self, mock_policy, mock_rejected_approval):
        """Test action is blocked when approval was rejected."""
        service = GatedActionService()

        with patch.object(service, "get_tenant_policy", new_callable=AsyncMock) as mock_get_policy:
            mock_get_policy.return_value = mock_policy

            with patch.object(service, "get_approved_approval", new_callable=AsyncMock) as mock_get_approved:
                mock_get_approved.return_value = None

                with patch.object(service, "get_pending_approval", new_callable=AsyncMock) as mock_get_pending:
                    mock_get_pending.return_value = None

                    mock_response = MagicMock()
                    mock_response.data = [mock_rejected_approval]

                    with patch("app.services.gated_action_service.db_service") as mock_db:
                        mock_query = MagicMock()
                        mock_query.select.return_value = mock_query
                        mock_query.eq.return_value = mock_query
                        mock_query.order.return_value = mock_query
                        mock_query.limit.return_value = mock_query
                        mock_query.execute.return_value = mock_response
                        mock_db.client.table.return_value = mock_query

                        result = await service.check_approval_status(
                            MOCK_TENANT_ID, MOCK_INCIDENT_ID, GatedActionType.ACKNOWLEDGE
                        )

                        assert result.allowed is False
                        assert result.requirement == ApprovalRequirement.REQUIRED_REJECTED
                        assert result.approval_id == MOCK_APPROVAL_ID
                        assert result.approval_details["status"] == ApprovalStatus.rejected.value
                        assert "rejected" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_approval_required_no_request(self, mock_policy):
        """Test action is blocked when approval is required but no request exists."""
        service = GatedActionService()

        with patch.object(service, "get_tenant_policy", new_callable=AsyncMock) as mock_get_policy:
            mock_get_policy.return_value = mock_policy

            with patch.object(service, "get_approved_approval", new_callable=AsyncMock) as mock_get_approved:
                mock_get_approved.return_value = None

                with patch.object(service, "get_pending_approval", new_callable=AsyncMock) as mock_get_pending:
                    mock_get_pending.return_value = None

                    mock_response = MagicMock()
                    mock_response.data = []

                    with patch("app.services.gated_action_service.db_service") as mock_db:
                        mock_query = MagicMock()
                        mock_query.select.return_value = mock_query
                        mock_query.eq.return_value = mock_query
                        mock_query.order.return_value = mock_query
                        mock_query.limit.return_value = mock_query
                        mock_query.execute.return_value = mock_response
                        mock_db.client.table.return_value = mock_query

                        result = await service.check_approval_status(
                            MOCK_TENANT_ID, MOCK_INCIDENT_ID, GatedActionType.ACKNOWLEDGE
                        )

                        assert result.allowed is False
                        assert result.requirement == ApprovalRequirement.REQUIRED_NO_REQUEST
                        assert result.approval_id is None
                        assert "submit an approval request" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_all_action_types(self, mock_policy):
        """Test check_approval_status works for all action types."""
        service = GatedActionService()

        with patch.object(service, "get_tenant_policy", new_callable=AsyncMock) as mock_get_policy:
            mock_get_policy.return_value = mock_policy

            with patch.object(service, "get_approved_approval", new_callable=AsyncMock) as mock_get_approved:
                mock_get_approved.return_value = None

                with patch.object(service, "get_pending_approval", new_callable=AsyncMock) as mock_get_pending:
                    mock_get_pending.return_value = None

                    mock_response = MagicMock()
                    mock_response.data = []

                    with patch("app.services.gated_action_service.db_service") as mock_db:
                        mock_query = MagicMock()
                        mock_query.select.return_value = mock_query
                        mock_query.eq.return_value = mock_query
                        mock_query.order.return_value = mock_query
                        mock_query.limit.return_value = mock_query
                        mock_query.execute.return_value = mock_response
                        mock_db.client.table.return_value = mock_query

                        # Test ACKNOWLEDGE
                        result = await service.check_approval_status(
                            MOCK_TENANT_ID, MOCK_INCIDENT_ID, GatedActionType.ACKNOWLEDGE
                        )
                        assert result.allowed is False
                        assert "acknowledge" in result.reason.lower()

                        # Test EXTEND_TTL
                        result = await service.check_approval_status(
                            MOCK_TENANT_ID, MOCK_INCIDENT_ID, GatedActionType.EXTEND_TTL
                        )
                        assert result.allowed is False
                        assert "extend_ttl" in result.reason.lower()

                        # Test RECONCILE
                        result = await service.check_approval_status(
                            MOCK_TENANT_ID, MOCK_INCIDENT_ID, GatedActionType.RECONCILE
                        )
                        assert result.allowed is False
                        assert "reconcile" in result.reason.lower()


class TestMarkApprovalExecuted:
    """Tests for mark_approval_executed method."""

    @pytest.mark.asyncio
    async def test_mark_executed_success(self):
        """Test successfully marking approval as executed."""
        mock_response = MagicMock()
        mock_response.data = [{"id": MOCK_APPROVAL_ID, "executed_at": datetime.utcnow().isoformat()}]

        with patch("app.services.gated_action_service.db_service") as mock_db:
            mock_query = MagicMock()
            mock_query.update.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.execute.return_value = mock_response
            mock_db.client.table.return_value = mock_query

            service = GatedActionService()
            result = await service.mark_approval_executed(
                MOCK_TENANT_ID, MOCK_APPROVAL_ID, MOCK_USER_ID
            )

            assert result is True
            mock_db.client.table.assert_called_once_with("drift_approvals")

    @pytest.mark.asyncio
    async def test_mark_executed_without_executor(self):
        """Test marking approval as executed without executor ID."""
        mock_response = MagicMock()
        mock_response.data = [{"id": MOCK_APPROVAL_ID, "executed_at": datetime.utcnow().isoformat()}]

        with patch("app.services.gated_action_service.db_service") as mock_db:
            mock_query = MagicMock()
            mock_query.update.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.execute.return_value = mock_response
            mock_db.client.table.return_value = mock_query

            service = GatedActionService()
            result = await service.mark_approval_executed(
                MOCK_TENANT_ID, MOCK_APPROVAL_ID
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_mark_executed_not_found(self):
        """Test marking approval as executed when not found."""
        mock_response = MagicMock()
        mock_response.data = []

        with patch("app.services.gated_action_service.db_service") as mock_db:
            mock_query = MagicMock()
            mock_query.update.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.execute.return_value = mock_response
            mock_db.client.table.return_value = mock_query

            service = GatedActionService()
            result = await service.mark_approval_executed(
                MOCK_TENANT_ID, MOCK_APPROVAL_ID
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_mark_executed_error_handling(self):
        """Test error handling when marking approval as executed."""
        with patch("app.services.gated_action_service.db_service") as mock_db:
            mock_db.client.table.side_effect = Exception("Database error")

            service = GatedActionService()
            result = await service.mark_approval_executed(
                MOCK_TENANT_ID, MOCK_APPROVAL_ID
            )

            assert result is False


class TestValidateIncidentExists:
    """Tests for validate_incident_exists method."""

    @pytest.mark.asyncio
    async def test_validate_incident_exists_success(self, mock_incident):
        """Test validating incident that exists and is not closed."""
        mock_response = MagicMock()
        mock_response.data = [{"id": MOCK_INCIDENT_ID, "status": "detected"}]

        with patch("app.services.gated_action_service.db_service") as mock_db:
            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.execute.return_value = mock_response
            mock_db.client.table.return_value = mock_query

            service = GatedActionService()
            result = await service.validate_incident_exists(
                MOCK_TENANT_ID, MOCK_INCIDENT_ID
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_validate_incident_not_found(self):
        """Test validating incident that doesn't exist."""
        mock_response = MagicMock()
        mock_response.data = []

        with patch("app.services.gated_action_service.db_service") as mock_db:
            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.execute.return_value = mock_response
            mock_db.client.table.return_value = mock_query

            service = GatedActionService()
            result = await service.validate_incident_exists(
                MOCK_TENANT_ID, MOCK_INCIDENT_ID
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_validate_incident_closed(self):
        """Test validating incident that is closed."""
        mock_response = MagicMock()
        mock_response.data = [{"id": MOCK_INCIDENT_ID, "status": "closed"}]

        with patch("app.services.gated_action_service.db_service") as mock_db:
            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.execute.return_value = mock_response
            mock_db.client.table.return_value = mock_query

            service = GatedActionService()
            result = await service.validate_incident_exists(
                MOCK_TENANT_ID, MOCK_INCIDENT_ID
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_validate_incident_error_handling(self):
        """Test error handling when validating incident."""
        with patch("app.services.gated_action_service.db_service") as mock_db:
            mock_db.client.table.side_effect = Exception("Database error")

            service = GatedActionService()
            result = await service.validate_incident_exists(
                MOCK_TENANT_ID, MOCK_INCIDENT_ID
            )

            assert result is False


class TestGetActionAuditSummary:
    """Tests for get_action_audit_summary method."""

    @pytest.mark.asyncio
    async def test_get_audit_summary_success(self):
        """Test getting audit summary with approvals."""
        mock_approvals = [
            {"id": "app-1", "status": "approved", "executed_at": datetime.utcnow().isoformat()},
            {"id": "app-2", "status": "pending"},
            {"id": "app-3", "status": "rejected"},
            {"id": "app-4", "status": "cancelled"},
        ]

        mock_response = MagicMock()
        mock_response.data = mock_approvals

        with patch("app.services.gated_action_service.db_service") as mock_db:
            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.order.return_value = mock_query
            mock_query.execute.return_value = mock_response
            mock_db.client.table.return_value = mock_query

            service = GatedActionService()
            result = await service.get_action_audit_summary(
                MOCK_TENANT_ID, MOCK_INCIDENT_ID
            )

            assert result["incident_id"] == MOCK_INCIDENT_ID
            assert result["total_approvals"] == 4
            assert result["statistics"]["pending"] == 1
            assert result["statistics"]["approved"] == 1
            assert result["statistics"]["rejected"] == 1
            assert result["statistics"]["cancelled"] == 1
            assert result["statistics"]["executed"] == 1
            assert len(result["approvals"]) == 4

    @pytest.mark.asyncio
    async def test_get_audit_summary_with_action_type_filter(self):
        """Test getting audit summary filtered by action type."""
        mock_approvals = [
            {"id": "app-1", "status": "approved", "approval_type": "acknowledge"},
        ]

        mock_response = MagicMock()
        mock_response.data = mock_approvals

        with patch("app.services.gated_action_service.db_service") as mock_db:
            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.order.return_value = mock_query
            mock_query.execute.return_value = mock_response
            mock_db.client.table.return_value = mock_query

            service = GatedActionService()
            result = await service.get_action_audit_summary(
                MOCK_TENANT_ID, MOCK_INCIDENT_ID, GatedActionType.ACKNOWLEDGE
            )

            assert result["action_type"] == "acknowledge"
            assert result["total_approvals"] == 1

    @pytest.mark.asyncio
    async def test_get_audit_summary_no_approvals(self):
        """Test getting audit summary when no approvals exist."""
        mock_response = MagicMock()
        mock_response.data = []

        with patch("app.services.gated_action_service.db_service") as mock_db:
            mock_query = MagicMock()
            mock_query.select.return_value = mock_query
            mock_query.eq.return_value = mock_query
            mock_query.order.return_value = mock_query
            mock_query.execute.return_value = mock_response
            mock_db.client.table.return_value = mock_query

            service = GatedActionService()
            result = await service.get_action_audit_summary(
                MOCK_TENANT_ID, MOCK_INCIDENT_ID
            )

            assert result["total_approvals"] == 0
            assert result["statistics"]["pending"] == 0
            assert result["statistics"]["approved"] == 0
            assert result["statistics"]["rejected"] == 0
            assert result["statistics"]["cancelled"] == 0
            assert result["statistics"]["executed"] == 0
            assert len(result["approvals"]) == 0

    @pytest.mark.asyncio
    async def test_get_audit_summary_error_handling(self):
        """Test error handling when getting audit summary."""
        with patch("app.services.gated_action_service.db_service") as mock_db:
            mock_db.client.table.side_effect = Exception("Database error")

            service = GatedActionService()
            result = await service.get_action_audit_summary(
                MOCK_TENANT_ID, MOCK_INCIDENT_ID
            )

            assert "error" in result
            assert result["total_approvals"] == 0


class TestSingletonInstance:
    """Test that the singleton instance is properly configured."""

    def test_singleton_exists(self):
        """Test that the singleton instance exists."""
        assert gated_action_service is not None
        assert isinstance(gated_action_service, GatedActionService)

    def test_singleton_is_same_instance(self):
        """Test that we can import and use the same singleton instance."""
        from app.services.gated_action_service import gated_action_service as imported_service
        assert imported_service is gated_action_service
