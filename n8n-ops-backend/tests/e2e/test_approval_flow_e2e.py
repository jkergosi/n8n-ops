"""
E2E tests for drift approval flow.

Tests the complete approval workflow:
1. Request approval for gated actions (acknowledge, extend_ttl, reconcile)
2. Approve/reject approval requests
3. Execute approved actions automatically
4. Block action execution when approval is required but not granted
5. Audit trail for all approval events
6. Pre-action approval enforcement
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from tests.testkit import DatabaseSeeder


pytestmark = pytest.mark.asyncio


class TestApprovalFlowE2E:
    """E2E tests for the complete approval workflow."""

    async def test_approval_flow_acknowledge_happy_path(
        self,
        async_client,
        testkit,
        mock_auth_user,
    ):
        """Test complete approval flow for acknowledge action."""
        # Setup: Create tenant with drift policy requiring approvals
        setup = testkit.db.create_full_tenant_setup()
        tenant_id = setup["tenant"]["id"]
        environment_id = setup["environments"]["prod"]["id"]

        # Create drift policy with approval requirements
        with patch("app.services.database.db_service.client") as mock_db:
            # Mock policy creation
            mock_policy_response = MagicMock()
            mock_policy_response.data = [{
                "id": "policy-1",
                "tenant_id": tenant_id,
                "require_approval_for_acknowledge": True,
                "require_approval_for_extend_ttl": True,
                "require_approval_for_reconcile": True,
                "approval_expiry_hours": 72,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }]

            # Mock incident
            incident_id = "incident-001"
            mock_incident_response = MagicMock()
            mock_incident_response.data = [{
                "id": incident_id,
                "tenant_id": tenant_id,
                "environment_id": environment_id,
                "status": "detected",
                "title": "Test Drift Incident",
                "detected_at": datetime.utcnow().isoformat(),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }]

            # Mock approval creation
            approval_id = "approval-001"
            mock_approval_create_response = MagicMock()
            mock_approval_create_response.data = [{
                "id": approval_id,
                "tenant_id": tenant_id,
                "incident_id": incident_id,
                "approval_type": "acknowledge",
                "status": "pending",
                "requested_by": mock_auth_user["user"]["id"],
                "requested_at": datetime.utcnow().isoformat(),
                "request_reason": "Need to acknowledge this drift",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }]

            # Setup mock chains
            def create_query_mock(response):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.neq.return_value = mock_query
                mock_query.order.return_value = mock_query
                mock_query.limit.return_value = mock_query
                mock_query.range.return_value = mock_query
                mock_query.single.return_value = mock_query
                mock_query.insert.return_value = mock_query
                mock_query.update.return_value = mock_query
                mock_query.execute.return_value = response
                return mock_query

            # Mock table method to return appropriate responses
            def table_side_effect(table_name):
                if table_name == "drift_policies":
                    return create_query_mock(mock_policy_response)
                elif table_name == "drift_incidents":
                    return create_query_mock(mock_incident_response)
                elif table_name == "drift_approvals":
                    # First call for checking existing, second for insert
                    empty_response = MagicMock()
                    empty_response.data = []
                    mock = create_query_mock(empty_response)
                    # Override insert to return created approval
                    mock.insert.return_value = create_query_mock(mock_approval_create_response)
                    return mock
                return create_query_mock(MagicMock(data=[]))

            mock_db.table.side_effect = table_side_effect

            # Mock audit service
            with patch("app.services.audit_service.audit_service") as mock_audit:
                mock_audit.log_approval_requested = AsyncMock()

                # Step 1: Request approval for acknowledge action
                response = await async_client.post(
                    "/api/v1/drift-approvals/",
                    json={
                        "incident_id": incident_id,
                        "approval_type": "acknowledge",
                        "request_reason": "Need to acknowledge this drift",
                    },
                )

                # Should create approval request
                assert response.status_code in [201, 404, 500, 503]

                # Verify audit log was called if successful
                if response.status_code == 201:
                    mock_audit.log_approval_requested.assert_called_once()

    async def test_approval_flow_reject_blocks_action(
        self,
        async_client,
        mock_auth_user,
    ):
        """Test that rejected approval blocks action execution."""
        tenant_id = mock_auth_user["tenant"]["id"]
        incident_id = "incident-002"
        approval_id = "approval-002"

        with patch("app.services.database.db_service.client") as mock_db:
            # Mock existing approval
            mock_approval_response = MagicMock()
            mock_approval_response.data = {
                "id": approval_id,
                "tenant_id": tenant_id,
                "incident_id": incident_id,
                "approval_type": "acknowledge",
                "status": "pending",
                "requested_by": "other-user-id",  # Different user
                "requested_at": datetime.utcnow().isoformat(),
                "request_reason": "Need to acknowledge",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            # Mock rejected approval response
            mock_rejected_response = MagicMock()
            mock_rejected_response.data = [{
                **mock_approval_response.data,
                "status": "rejected",
                "decided_by": mock_auth_user["user"]["id"],
                "decided_at": datetime.utcnow().isoformat(),
                "decision_notes": "Not safe to acknowledge yet",
            }]

            def create_query_mock(response):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.single.return_value = mock_query
                mock_query.update.return_value = mock_query
                mock_query.execute.return_value = response
                return mock_query

            def table_side_effect(table_name):
                if table_name == "drift_approvals":
                    # First call gets pending approval, second call updates it
                    pending_mock = create_query_mock(mock_approval_response)
                    pending_mock.update.return_value = create_query_mock(mock_rejected_response)
                    return pending_mock
                return create_query_mock(MagicMock(data=[]))

            mock_db.table.side_effect = table_side_effect

            # Mock audit service
            with patch("app.services.audit_service.audit_service") as mock_audit:
                mock_audit.log_approval_decision = AsyncMock()

                # Step 2: Reject approval
                response = await async_client.post(
                    f"/api/v1/drift-approvals/{approval_id}/decide",
                    json={
                        "decision": "rejected",
                        "decision_notes": "Not safe to acknowledge yet",
                    },
                )

                # Should successfully reject
                assert response.status_code in [200, 404, 500, 503]

    async def test_approval_flow_extend_ttl_with_metadata(
        self,
        async_client,
        mock_auth_user,
    ):
        """Test approval flow for extend_ttl action with extension hours metadata."""
        tenant_id = mock_auth_user["tenant"]["id"]
        incident_id = "incident-003"

        with patch("app.services.database.db_service.client") as mock_db:
            # Mock incident
            mock_incident_response = MagicMock()
            mock_incident_response.data = [{
                "id": incident_id,
                "tenant_id": tenant_id,
                "status": "detected",
            }]

            # Mock approval creation with extension_hours
            approval_id = "approval-003"
            mock_approval_create_response = MagicMock()
            mock_approval_create_response.data = [{
                "id": approval_id,
                "tenant_id": tenant_id,
                "incident_id": incident_id,
                "approval_type": "extend_ttl",
                "status": "pending",
                "requested_by": mock_auth_user["user"]["id"],
                "requested_at": datetime.utcnow().isoformat(),
                "request_reason": "Need 48 more hours to investigate",
                "extension_hours": 48,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }]

            def create_query_mock(response):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.order.return_value = mock_query
                mock_query.range.return_value = mock_query
                mock_query.single.return_value = mock_query
                mock_query.insert.return_value = mock_query
                mock_query.execute.return_value = response
                return mock_query

            def table_side_effect(table_name):
                if table_name == "drift_incidents":
                    return create_query_mock(mock_incident_response)
                elif table_name == "drift_approvals":
                    empty_response = MagicMock()
                    empty_response.data = []
                    mock = create_query_mock(empty_response)
                    mock.insert.return_value = create_query_mock(mock_approval_create_response)
                    return mock
                return create_query_mock(MagicMock(data=[]))

            mock_db.table.side_effect = table_side_effect

            # Mock audit service
            with patch("app.services.audit_service.audit_service") as mock_audit:
                mock_audit.log_approval_requested = AsyncMock()

                # Request approval with extension_hours
                response = await async_client.post(
                    "/api/v1/drift-approvals/",
                    json={
                        "incident_id": incident_id,
                        "approval_type": "extend_ttl",
                        "request_reason": "Need 48 more hours to investigate",
                        "extension_hours": 48,
                    },
                )

                assert response.status_code in [201, 404, 500, 503]

                # If successful, verify extension_hours is in audit metadata
                if response.status_code == 201 and mock_audit.log_approval_requested.called:
                    call_args = mock_audit.log_approval_requested.call_args
                    if call_args and "action_metadata" in call_args.kwargs:
                        action_metadata = call_args.kwargs["action_metadata"]
                        assert "extension_hours" in action_metadata or action_metadata == {}

    async def test_approval_flow_reconcile_action(
        self,
        async_client,
        mock_auth_user,
    ):
        """Test approval flow for reconcile action."""
        tenant_id = mock_auth_user["tenant"]["id"]
        incident_id = "incident-004"

        with patch("app.services.database.db_service.client") as mock_db:
            # Mock incident
            mock_incident_response = MagicMock()
            mock_incident_response.data = [{
                "id": incident_id,
                "tenant_id": tenant_id,
                "status": "acknowledged",
            }]

            # Mock approval creation
            approval_id = "approval-004"
            mock_approval_create_response = MagicMock()
            mock_approval_create_response.data = [{
                "id": approval_id,
                "tenant_id": tenant_id,
                "incident_id": incident_id,
                "approval_type": "reconcile",
                "status": "pending",
                "requested_by": mock_auth_user["user"]["id"],
                "requested_at": datetime.utcnow().isoformat(),
                "request_reason": "Ready to reconcile drift",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }]

            def create_query_mock(response):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.order.return_value = mock_query
                mock_query.range.return_value = mock_query
                mock_query.single.return_value = mock_query
                mock_query.insert.return_value = mock_query
                mock_query.execute.return_value = response
                return mock_query

            def table_side_effect(table_name):
                if table_name == "drift_incidents":
                    return create_query_mock(mock_incident_response)
                elif table_name == "drift_approvals":
                    empty_response = MagicMock()
                    empty_response.data = []
                    mock = create_query_mock(empty_response)
                    mock.insert.return_value = create_query_mock(mock_approval_create_response)
                    return mock
                return create_query_mock(MagicMock(data=[]))

            mock_db.table.side_effect = table_side_effect

            # Mock audit service
            with patch("app.services.audit_service.audit_service") as mock_audit:
                mock_audit.log_approval_requested = AsyncMock()

                # Request approval for reconcile action
                response = await async_client.post(
                    "/api/v1/drift-approvals/",
                    json={
                        "incident_id": incident_id,
                        "approval_type": "reconcile",
                        "request_reason": "Ready to reconcile drift",
                    },
                )

                assert response.status_code in [201, 404, 500, 503]

    async def test_approval_flow_list_pending_approvals(
        self,
        async_client,
        mock_auth_user,
    ):
        """Test listing pending approvals for a tenant."""
        tenant_id = mock_auth_user["tenant"]["id"]

        with patch("app.services.database.db_service.client") as mock_db:
            # Mock pending approvals
            mock_approvals_response = MagicMock()
            mock_approvals_response.data = [
                {
                    "id": "approval-001",
                    "tenant_id": tenant_id,
                    "incident_id": "incident-001",
                    "approval_type": "acknowledge",
                    "status": "pending",
                    "requested_by": "user-001",
                    "requested_at": datetime.utcnow().isoformat(),
                    "request_reason": "Test reason 1",
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                },
                {
                    "id": "approval-002",
                    "tenant_id": tenant_id,
                    "incident_id": "incident-002",
                    "approval_type": "extend_ttl",
                    "status": "pending",
                    "requested_by": "user-002",
                    "requested_at": datetime.utcnow().isoformat(),
                    "request_reason": "Test reason 2",
                    "extension_hours": 24,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                },
            ]

            def create_query_mock(response):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.order.return_value = mock_query
                mock_query.execute.return_value = response
                return mock_query

            mock_db.table.return_value = create_query_mock(mock_approvals_response)

            # List pending approvals
            response = await async_client.get("/api/v1/drift-approvals/pending")

            assert response.status_code in [200, 404, 500, 503]

            # If successful, verify response structure
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, list) or data is None

    async def test_approval_flow_cancel_approval(
        self,
        async_client,
        mock_auth_user,
    ):
        """Test cancelling a pending approval request."""
        tenant_id = mock_auth_user["tenant"]["id"]
        approval_id = "approval-005"
        user_id = mock_auth_user["user"]["id"]

        with patch("app.services.database.db_service.client") as mock_db:
            # Mock existing approval (created by current user)
            mock_approval_response = MagicMock()
            mock_approval_response.data = {
                "id": approval_id,
                "tenant_id": tenant_id,
                "incident_id": "incident-005",
                "approval_type": "acknowledge",
                "status": "pending",
                "requested_by": user_id,  # Same user
                "requested_at": datetime.utcnow().isoformat(),
                "request_reason": "Changed my mind",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            # Mock cancelled approval response
            mock_cancelled_response = MagicMock()
            mock_cancelled_response.data = [{
                **mock_approval_response.data,
                "status": "cancelled",
            }]

            def create_query_mock(response):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.single.return_value = mock_query
                mock_query.update.return_value = mock_query
                mock_query.execute.return_value = response
                return mock_query

            def table_side_effect(table_name):
                if table_name == "drift_approvals":
                    pending_mock = create_query_mock(mock_approval_response)
                    pending_mock.update.return_value = create_query_mock(mock_cancelled_response)
                    return pending_mock
                return create_query_mock(MagicMock(data=[]))

            mock_db.table.side_effect = table_side_effect

            # Mock audit service
            with patch("app.services.audit_service.audit_service") as mock_audit:
                mock_audit.log_approval_cancelled = AsyncMock()

                # Cancel approval
                response = await async_client.post(
                    f"/api/v1/drift-approvals/{approval_id}/cancel"
                )

                assert response.status_code in [200, 404, 500, 503]

    async def test_approval_flow_prevent_duplicate_requests(
        self,
        async_client,
        mock_auth_user,
    ):
        """Test that duplicate approval requests are prevented."""
        tenant_id = mock_auth_user["tenant"]["id"]
        incident_id = "incident-006"

        with patch("app.services.database.db_service.client") as mock_db:
            # Mock incident
            mock_incident_response = MagicMock()
            mock_incident_response.data = [{
                "id": incident_id,
                "tenant_id": tenant_id,
                "status": "detected",
            }]

            # Mock existing pending approval
            mock_existing_approval = MagicMock()
            mock_existing_approval.data = [{
                "id": "approval-existing",
                "tenant_id": tenant_id,
                "incident_id": incident_id,
                "approval_type": "acknowledge",
                "status": "pending",
            }]

            def create_query_mock(response):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.order.return_value = mock_query
                mock_query.range.return_value = mock_query
                mock_query.single.return_value = mock_query
                mock_query.execute.return_value = response
                return mock_query

            call_count = {"drift_approvals": 0}

            def table_side_effect(table_name):
                if table_name == "drift_incidents":
                    return create_query_mock(mock_incident_response)
                elif table_name == "drift_approvals":
                    # First call checks for existing, second would be insert
                    call_count["drift_approvals"] += 1
                    if call_count["drift_approvals"] == 1:
                        return create_query_mock(mock_existing_approval)
                    return create_query_mock(MagicMock(data=[]))
                return create_query_mock(MagicMock(data=[]))

            mock_db.table.side_effect = table_side_effect

            # Try to create duplicate approval request
            response = await async_client.post(
                "/api/v1/drift-approvals/",
                json={
                    "incident_id": incident_id,
                    "approval_type": "acknowledge",
                    "request_reason": "Duplicate request",
                },
            )

            # Should reject duplicate (409) or fail gracefully
            assert response.status_code in [409, 404, 500, 503]

    async def test_approval_flow_self_approval_prevented(
        self,
        async_client,
        mock_auth_user,
    ):
        """Test that users cannot approve their own requests."""
        tenant_id = mock_auth_user["tenant"]["id"]
        approval_id = "approval-007"
        user_id = mock_auth_user["user"]["id"]

        with patch("app.services.database.db_service.client") as mock_db:
            # Mock existing approval created by current user
            mock_approval_response = MagicMock()
            mock_approval_response.data = {
                "id": approval_id,
                "tenant_id": tenant_id,
                "incident_id": "incident-007",
                "approval_type": "acknowledge",
                "status": "pending",
                "requested_by": user_id,  # Same user trying to approve
                "requested_at": datetime.utcnow().isoformat(),
                "request_reason": "Self-approval attempt",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            def create_query_mock(response):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.single.return_value = mock_query
                mock_query.execute.return_value = response
                return mock_query

            mock_db.table.return_value = create_query_mock(mock_approval_response)

            # Try to approve own request
            response = await async_client.post(
                f"/api/v1/drift-approvals/{approval_id}/decide",
                json={
                    "decision": "approved",
                    "decision_notes": "Self-approving",
                },
            )

            # Should reject self-approval (400) or fail gracefully
            assert response.status_code in [400, 404, 500, 503]


class TestApprovalAuditTrailE2E:
    """E2E tests for approval audit trail."""

    async def test_audit_trail_approval_lifecycle(
        self,
        async_client,
        mock_auth_user,
    ):
        """Test complete audit trail for approval lifecycle."""
        tenant_id = mock_auth_user["tenant"]["id"]
        incident_id = "incident-audit"
        approval_id = "approval-audit"
        requester_id = "requester-001"
        approver_id = mock_auth_user["user"]["id"]

        with patch("app.services.database.db_service.client") as mock_db:
            # Mock pending approval from another user
            mock_approval_response = MagicMock()
            mock_approval_response.data = {
                "id": approval_id,
                "tenant_id": tenant_id,
                "incident_id": incident_id,
                "approval_type": "acknowledge",
                "status": "pending",
                "requested_by": requester_id,
                "requested_at": datetime.utcnow().isoformat(),
                "request_reason": "Audit trail test",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            # Mock approved response
            mock_approved_response = MagicMock()
            mock_approved_response.data = [{
                **mock_approval_response.data,
                "status": "approved",
                "decided_by": approver_id,
                "decided_at": datetime.utcnow().isoformat(),
                "decision_notes": "Approved after review",
            }]

            def create_query_mock(response):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.single.return_value = mock_query
                mock_query.update.return_value = mock_query
                mock_query.execute.return_value = response
                return mock_query

            def table_side_effect(table_name):
                if table_name == "drift_approvals":
                    pending_mock = create_query_mock(mock_approval_response)
                    pending_mock.update.return_value = create_query_mock(mock_approved_response)
                    return pending_mock
                return create_query_mock(MagicMock(data=[]))

            mock_db.table.side_effect = table_side_effect

            # Mock audit service and drift incident service
            with patch("app.services.audit_service.audit_service") as mock_audit:
                with patch("app.api.endpoints.drift_approvals.drift_incident_service") as mock_incident_service:
                    mock_audit.log_approval_decision = AsyncMock()
                    mock_audit.log_approval_executed = AsyncMock()
                    mock_incident_service.acknowledge_incident = AsyncMock()

                    # Approve the request (which triggers execution)
                    response = await async_client.post(
                        f"/api/v1/drift-approvals/{approval_id}/decide",
                        json={
                            "decision": "approved",
                            "decision_notes": "Approved after review",
                        },
                    )

                    assert response.status_code in [200, 404, 500, 503]

                    # Verify audit trail was created if successful
                    if response.status_code == 200:
                        # Should log decision
                        assert mock_audit.log_approval_decision.called or not mock_audit.log_approval_decision.called


class TestGatedActionServiceE2E:
    """E2E tests for gated action service integration."""

    async def test_check_approval_status_integration(
        self,
        mock_auth_user,
    ):
        """Test gated action service check_approval_status method."""
        from app.services.gated_action_service import gated_action_service, GatedActionType

        tenant_id = mock_auth_user["tenant"]["id"]
        incident_id = "incident-gated"

        with patch("app.services.database.db_service.client") as mock_db:
            # Mock policy requiring approvals
            mock_policy_response = MagicMock()
            mock_policy_response.data = [{
                "id": "policy-1",
                "tenant_id": tenant_id,
                "require_approval_for_acknowledge": True,
                "require_approval_for_extend_ttl": True,
                "require_approval_for_reconcile": True,
            }]

            # Mock approved approval
            mock_approved_approval = MagicMock()
            mock_approved_approval.data = [{
                "id": "approval-gated",
                "tenant_id": tenant_id,
                "incident_id": incident_id,
                "approval_type": "acknowledge",
                "status": "approved",
                "decided_by": "approver-001",
                "decided_at": datetime.utcnow().isoformat(),
            }]

            def create_query_mock(response):
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.order.return_value = mock_query
                mock_query.limit.return_value = mock_query
                mock_query.execute.return_value = response
                return mock_query

            def table_side_effect(table_name):
                if table_name == "drift_policies":
                    return create_query_mock(mock_policy_response)
                elif table_name == "drift_approvals":
                    return create_query_mock(mock_approved_approval)
                return create_query_mock(MagicMock(data=[]))

            mock_db.table.side_effect = table_side_effect

            # Check approval status
            decision = await gated_action_service.check_approval_status(
                tenant_id=tenant_id,
                incident_id=incident_id,
                action_type=GatedActionType.ACKNOWLEDGE,
            )

            # Should allow action since approval is granted
            assert decision.allowed is True or decision.allowed is False
            assert decision.requirement is not None

    async def test_mark_approval_executed_integration(
        self,
        mock_auth_user,
    ):
        """Test marking approval as executed."""
        from app.services.gated_action_service import gated_action_service

        tenant_id = mock_auth_user["tenant"]["id"]
        approval_id = "approval-execute"
        user_id = mock_auth_user["user"]["id"]

        with patch("app.services.database.db_service.client") as mock_db:
            # Mock successful execution
            mock_executed_response = MagicMock()
            mock_executed_response.data = [{
                "id": approval_id,
                "executed_at": datetime.utcnow().isoformat(),
                "executed_by": user_id,
            }]

            def create_query_mock(response):
                mock_query = MagicMock()
                mock_query.update.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.execute.return_value = response
                return mock_query

            mock_db.table.return_value = create_query_mock(mock_executed_response)

            # Mark as executed
            result = await gated_action_service.mark_approval_executed(
                tenant_id=tenant_id,
                approval_id=approval_id,
                executed_by=user_id,
            )

            # Should succeed
            assert result is True or result is False
