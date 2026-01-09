import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.downgrade_service import (
    downgrade_service,
    GracePeriodStatus,
    DowngradeAction,
    ResourceType,
)


class MockSupabaseResponse:
    """Mock Supabase response object."""
    def __init__(self, data=None):
        self.data = data


@pytest.mark.asyncio
async def test_enforce_expired_grace_periods_idempotent():
    expired = [
        {
            "id": "gp-1",
            "tenant_id": "tenant-1",
            "resource_type": ResourceType.ENVIRONMENT.value,
            "resource_id": "env-1",
            "action": DowngradeAction.READ_ONLY.value,
            "status": GracePeriodStatus.ACTIVE.value,
        }
    ]

    with patch.object(
        downgrade_service,
        "get_expired_grace_periods",
        AsyncMock(side_effect=[expired, []]),
    ), patch.object(
        downgrade_service,
        "execute_downgrade_action",
        AsyncMock(return_value=True),
    ) as exec_action, patch.object(
        downgrade_service,
        "_update_grace_period_status",
        AsyncMock(return_value=True),
    ) as update_status:
        first_run = await downgrade_service.enforce_expired_grace_periods()
        second_run = await downgrade_service.enforce_expired_grace_periods()

    assert first_run["enforced_count"] == 1
    assert first_run["errors"] == []
    exec_action.assert_awaited_once()
    update_status.assert_awaited_once()

    assert second_run["checked_count"] == 0
    assert second_run["enforced_count"] == 0


@pytest.mark.asyncio
async def test_detect_overlimit_skips_existing_grace_periods():
    active_grace = [
        {
            "resource_type": ResourceType.ENVIRONMENT.value,
            "resource_id": "env-1",
            "status": GracePeriodStatus.ACTIVE.value,
        }
    ]

    with patch.object(
        downgrade_service,
        "get_active_grace_periods",
        AsyncMock(return_value=active_grace),
    ), patch.object(
        downgrade_service,
        "detect_environment_overlimit",
        AsyncMock(return_value=(True, 3, 1, ["env-1", "env-2"])),
    ), patch.object(
        downgrade_service,
        "detect_team_member_overlimit",
        AsyncMock(return_value=(False, 0, 0, [])),
    ), patch.object(
        downgrade_service,
        "detect_workflow_overlimit",
        AsyncMock(return_value=(False, 0, 0, [])),
    ), patch.object(
        downgrade_service,
        "initiate_grace_period",
        AsyncMock(return_value="gp-2"),
    ) as initiate_grace:
        summary = await downgrade_service.detect_overlimit_for_tenant("tenant-1")

    assert summary["grace_periods_created"] == 1
    assert summary["skipped_existing"] == 1
    initiate_grace.assert_awaited_once_with(
        tenant_id="tenant-1",
        resource_type=ResourceType.ENVIRONMENT,
        resource_id="env-2",
        reason="Scheduled over-limit check",
    )


@pytest.mark.asyncio
async def test_cancel_grace_period_idempotent():
    """Test that cancel_grace_period can be called multiple times safely."""
    tenant_id = "tenant-1"
    resource_type = ResourceType.ENVIRONMENT
    resource_id = "env-1"

    # First call succeeds
    first_response = MockSupabaseResponse(data=[{"id": "gp-1", "status": GracePeriodStatus.CANCELLED.value}])

    # Second call finds no active grace period (already cancelled)
    second_response = MockSupabaseResponse(data=None)

    call_count = 0

    def mock_execute():
        nonlocal call_count
        call_count += 1
        return first_response if call_count == 1 else second_response

    with patch.object(
        downgrade_service.db_service.client,
        "table",
        return_value=MagicMock(
            update=MagicMock(return_value=MagicMock(
                eq=MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(
                        eq=MagicMock(return_value=MagicMock(
                            eq=MagicMock(return_value=MagicMock(
                                execute=MagicMock(side_effect=mock_execute)
                            ))
                        ))
                    ))
                ))
            ))
        )
    ), patch.object(
        downgrade_service,
        "_reenable_resource",
        AsyncMock(return_value=True),
    ) as mock_reenable:
        # First call should succeed
        result1 = await downgrade_service.cancel_grace_period(
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id
        )

        # Second call should also return True (idempotent)
        result2 = await downgrade_service.cancel_grace_period(
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id
        )

    assert result1 is True
    # Second call returns False because no grace period was found to cancel
    # This is expected - the grace period was already cancelled
    assert result2 is False

    # Re-enable should only be called once (when grace period was actually cancelled)
    assert mock_reenable.await_count == 1


@pytest.mark.asyncio
async def test_handle_plan_upgrade_idempotent():
    """Test that handle_plan_upgrade can be called multiple times without errors."""
    tenant_id = "tenant-1"
    old_plan = "starter"
    new_plan = "pro"

    # First call: has active grace periods
    active_grace_periods = [
        {
            "id": "gp-1",
            "tenant_id": tenant_id,
            "resource_type": ResourceType.ENVIRONMENT.value,
            "resource_id": "env-1",
            "status": GracePeriodStatus.ACTIVE.value,
        }
    ]

    call_count = 0

    async def mock_get_grace_periods(tenant_id):
        nonlocal call_count
        call_count += 1
        # First call returns active grace periods, second returns empty
        return active_grace_periods if call_count == 1 else []

    cancellation_result = {
        "tenant_id": tenant_id,
        "checked_count": 1,
        "cancelled_count": 1,
        "cancelled_by_type": {
            "environment": 1,
            "team_member": 0,
            "workflow": 0,
        },
        "errors": [],
    }

    with patch.object(
        downgrade_service,
        "get_active_grace_periods",
        mock_get_grace_periods
    ), patch.object(
        downgrade_service,
        "cancel_grace_periods_for_compliant_resources",
        AsyncMock(return_value=cancellation_result)
    ) as mock_cancel:
        # First call
        result1 = await downgrade_service.handle_plan_upgrade(
            tenant_id=tenant_id,
            old_plan=old_plan,
            new_plan=new_plan
        )

        # Second call (simulating duplicate webhook or retry)
        result2 = await downgrade_service.handle_plan_upgrade(
            tenant_id=tenant_id,
            old_plan=old_plan,
            new_plan=new_plan
        )

    # First call should process grace periods
    assert result1["grace_periods_cancelled"] == 1
    assert "Cancelled grace periods" in result1["actions_taken"][0]

    # Second call should find no grace periods (already processed)
    assert result2["grace_periods_cancelled"] == 0
    assert "No active grace periods to cancel" in result2["actions_taken"][0]

    # cancel_grace_periods_for_compliant_resources called only once
    # (second call skips it when no active grace periods)
    assert mock_cancel.await_count == 1


@pytest.mark.asyncio
async def test_reenable_resource_called_on_grace_period_cancellation():
    """Test that re-enable logic is invoked when grace period is cancelled."""
    tenant_id = "tenant-1"
    resource_type = ResourceType.TEAM_MEMBER
    resource_id = "member-1"

    mock_response = MockSupabaseResponse(data=[{"id": "gp-1", "status": GracePeriodStatus.CANCELLED.value}])

    with patch.object(
        downgrade_service.db_service.client,
        "table",
        return_value=MagicMock(
            update=MagicMock(return_value=MagicMock(
                eq=MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(
                        eq=MagicMock(return_value=MagicMock(
                            eq=MagicMock(return_value=MagicMock(
                                execute=MagicMock(return_value=mock_response)
                            ))
                        ))
                    ))
                ))
            ))
        )
    ), patch.object(
        downgrade_service,
        "_reenable_resource",
        AsyncMock(return_value=True),
    ) as mock_reenable:
        result = await downgrade_service.cancel_grace_period(
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id
        )

    assert result is True

    # Verify re-enable was called with correct parameters
    mock_reenable.assert_awaited_once_with(
        tenant_id=tenant_id,
        resource_type=resource_type,
        resource_id=resource_id
    )


@pytest.mark.asyncio
async def test_cancel_grace_period_succeeds_even_if_reenable_fails():
    """Test that grace period cancellation succeeds even if re-enable fails."""
    tenant_id = "tenant-1"
    resource_type = ResourceType.WORKFLOW
    resource_id = "wf-canonical-1"

    mock_response = MockSupabaseResponse(data=[{"id": "gp-1", "status": GracePeriodStatus.CANCELLED.value}])

    with patch.object(
        downgrade_service.db_service.client,
        "table",
        return_value=MagicMock(
            update=MagicMock(return_value=MagicMock(
                eq=MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(
                        eq=MagicMock(return_value=MagicMock(
                            eq=MagicMock(return_value=MagicMock(
                                execute=MagicMock(return_value=mock_response)
                            ))
                        ))
                    ))
                ))
            ))
        )
    ), patch.object(
        downgrade_service,
        "_reenable_resource",
        AsyncMock(return_value=False),  # Re-enable fails
    ) as mock_reenable:
        result = await downgrade_service.cancel_grace_period(
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id
        )

    # Grace period should still be marked as cancelled
    assert result is True

    # Re-enable should have been attempted
    mock_reenable.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancel_compliant_resources_only_cancels_compliant():
    """Test that only resources within new limits have grace periods cancelled."""
    tenant_id = "tenant-1"

    # Three environments with grace periods
    active_grace_periods = [
        {
            "id": "gp-env-1",
            "tenant_id": tenant_id,
            "resource_type": ResourceType.ENVIRONMENT.value,
            "resource_id": "env-1",
            "status": GracePeriodStatus.ACTIVE.value,
        },
        {
            "id": "gp-env-2",
            "tenant_id": tenant_id,
            "resource_type": ResourceType.ENVIRONMENT.value,
            "resource_id": "env-2",
            "status": GracePeriodStatus.ACTIVE.value,
        },
        {
            "id": "gp-env-3",
            "tenant_id": tenant_id,
            "resource_type": ResourceType.ENVIRONMENT.value,
            "resource_id": "env-3",
            "status": GracePeriodStatus.ACTIVE.value,
        },
    ]

    with patch.object(
        downgrade_service,
        "get_active_grace_periods",
        AsyncMock(return_value=active_grace_periods),
    ), patch.object(
        downgrade_service,
        "detect_environment_overlimit",
        # Still 1 over limit: env-1 is still over limit
        AsyncMock(return_value=(True, 3, 2, ["env-1"])),
    ), patch.object(
        downgrade_service,
        "detect_team_member_overlimit",
        AsyncMock(return_value=(False, 0, 0, [])),
    ), patch.object(
        downgrade_service,
        "detect_workflow_overlimit",
        AsyncMock(return_value=(False, 0, 0, [])),
    ), patch.object(
        downgrade_service,
        "cancel_grace_period",
        AsyncMock(return_value=True),
    ) as mock_cancel:
        result = await downgrade_service.cancel_grace_periods_for_compliant_resources(tenant_id)

    # Only 2 grace periods should be cancelled (env-2 and env-3)
    assert result["cancelled_count"] == 2
    assert result["cancelled_by_type"]["environment"] == 2

    # Verify cancel was called exactly twice
    assert mock_cancel.await_count == 2

    # Verify env-1 was NOT cancelled (still over limit)
    cancel_calls = [call.kwargs for call in mock_cancel.await_args_list]
    cancelled_ids = [call["resource_id"] for call in cancel_calls]
    assert "env-1" not in cancelled_ids
    assert "env-2" in cancelled_ids
    assert "env-3" in cancelled_ids

