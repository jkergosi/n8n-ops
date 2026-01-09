"""
Unit tests for resource re-enable logic during plan upgrades.

This module tests the re-enable functionality that automatically restores
resources when grace periods are cancelled during plan upgrades or when
resources become compliant with plan limits.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

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
async def test_reenable_environment_clears_all_downgrade_markers():
    """Test that _reenable_environment clears all downgrade-related flags."""
    tenant_id = "tenant-123"
    environment_id = "env-456"

    # Mock the database update response
    mock_response = MockSupabaseResponse(data=[{
        "id": environment_id,
        "tenant_id": tenant_id,
        "is_read_only": False,
        "read_only_reason": None,
        "is_active": True,
        "is_deleted": False,
        "deleted_at": None,
        "deletion_reason": None,
    }])

    with patch.object(
        downgrade_service.db_service.client,
        "table",
        return_value=MagicMock(
            update=MagicMock(return_value=MagicMock(
                eq=MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(
                        execute=MagicMock(return_value=mock_response)
                    ))
                ))
            ))
        )
    ) as mock_table:
        result = await downgrade_service._reenable_environment(tenant_id, environment_id)

    assert result is True

    # Verify the update was called with correct parameters
    mock_table.assert_called_once_with("environments")
    update_call = mock_table.return_value.update
    update_call.assert_called_once()

    # Verify the update payload contains all required fields
    update_payload = update_call.call_args[0][0]
    assert update_payload["is_read_only"] is False
    assert update_payload["read_only_reason"] is None
    assert update_payload["is_active"] is True
    assert update_payload["is_deleted"] is False
    assert update_payload["deleted_at"] is None
    assert update_payload["deletion_reason"] is None
    assert "updated_at" in update_payload


@pytest.mark.asyncio
async def test_reenable_environment_handles_nonexistent_resource():
    """Test that _reenable_environment handles missing environment gracefully."""
    tenant_id = "tenant-123"
    environment_id = "env-nonexistent"

    # Mock empty response (environment not found)
    mock_response = MockSupabaseResponse(data=None)

    with patch.object(
        downgrade_service.db_service.client,
        "table",
        return_value=MagicMock(
            update=MagicMock(return_value=MagicMock(
                eq=MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(
                        execute=MagicMock(return_value=mock_response)
                    ))
                ))
            ))
        )
    ):
        result = await downgrade_service._reenable_environment(tenant_id, environment_id)

    assert result is False


@pytest.mark.asyncio
async def test_reenable_team_member_clears_deactivation_markers():
    """Test that _reenable_team_member clears deactivation-related flags."""
    tenant_id = "tenant-123"
    member_id = "member-456"

    # Mock the database update response
    mock_response = MockSupabaseResponse(data=[{
        "id": member_id,
        "tenant_id": tenant_id,
        "is_active": True,
        "deactivated_at": None,
        "deactivation_reason": None,
    }])

    with patch.object(
        downgrade_service.db_service.client,
        "table",
        return_value=MagicMock(
            update=MagicMock(return_value=MagicMock(
                eq=MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(
                        execute=MagicMock(return_value=mock_response)
                    ))
                ))
            ))
        )
    ) as mock_table:
        result = await downgrade_service._reenable_team_member(tenant_id, member_id)

    assert result is True

    # Verify the update was called with correct parameters
    mock_table.assert_called_once_with("tenant_users")
    update_call = mock_table.return_value.update
    update_call.assert_called_once()

    # Verify the update payload
    update_payload = update_call.call_args[0][0]
    assert update_payload["is_active"] is True
    assert update_payload["deactivated_at"] is None
    assert update_payload["deactivation_reason"] is None
    assert "updated_at" in update_payload


@pytest.mark.asyncio
async def test_reenable_team_member_handles_nonexistent_member():
    """Test that _reenable_team_member handles missing member gracefully."""
    tenant_id = "tenant-123"
    member_id = "member-nonexistent"

    # Mock empty response
    mock_response = MockSupabaseResponse(data=None)

    with patch.object(
        downgrade_service.db_service.client,
        "table",
        return_value=MagicMock(
            update=MagicMock(return_value=MagicMock(
                eq=MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(
                        execute=MagicMock(return_value=mock_response)
                    ))
                ))
            ))
        )
    ):
        result = await downgrade_service._reenable_team_member(tenant_id, member_id)

    assert result is False


@pytest.mark.asyncio
async def test_reenable_workflow_clears_readonly_and_archive_flags():
    """Test that _reenable_workflow clears read-only and archived flags."""
    tenant_id = "tenant-123"
    canonical_id = "wf-canonical-456"

    # Mock the database update response
    mock_response = MockSupabaseResponse(data=[{
        "id": canonical_id,
        "tenant_id": tenant_id,
        "is_read_only": False,
        "read_only_reason": None,
        "is_archived": False,
        "archived_at": None,
    }])

    with patch.object(
        downgrade_service.db_service.client,
        "table",
        return_value=MagicMock(
            update=MagicMock(return_value=MagicMock(
                eq=MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(
                        execute=MagicMock(return_value=mock_response)
                    ))
                ))
            ))
        )
    ) as mock_table:
        result = await downgrade_service._reenable_workflow(tenant_id, canonical_id)

    assert result is True

    # Verify the update was called with correct parameters
    mock_table.assert_called_once_with("canonical_workflows")
    update_call = mock_table.return_value.update
    update_call.assert_called_once()

    # Verify the update payload
    update_payload = update_call.call_args[0][0]
    assert update_payload["is_read_only"] is False
    assert update_payload["read_only_reason"] is None
    assert update_payload["is_archived"] is False
    assert update_payload["archived_at"] is None
    assert "updated_at" in update_payload


@pytest.mark.asyncio
async def test_reenable_workflow_handles_nonexistent_workflow():
    """Test that _reenable_workflow handles missing workflow gracefully."""
    tenant_id = "tenant-123"
    canonical_id = "wf-nonexistent"

    # Mock empty response
    mock_response = MockSupabaseResponse(data=None)

    with patch.object(
        downgrade_service.db_service.client,
        "table",
        return_value=MagicMock(
            update=MagicMock(return_value=MagicMock(
                eq=MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(
                        execute=MagicMock(return_value=mock_response)
                    ))
                ))
            ))
        )
    ):
        result = await downgrade_service._reenable_workflow(tenant_id, canonical_id)

    assert result is False


@pytest.mark.asyncio
async def test_reenable_resource_dispatcher_routes_to_environment():
    """Test that _reenable_resource correctly dispatches to environment method."""
    tenant_id = "tenant-123"
    resource_id = "env-456"

    with patch.object(
        downgrade_service,
        "_reenable_environment",
        AsyncMock(return_value=True)
    ) as mock_reenable_env:
        result = await downgrade_service._reenable_resource(
            tenant_id=tenant_id,
            resource_type=ResourceType.ENVIRONMENT,
            resource_id=resource_id
        )

    assert result is True
    mock_reenable_env.assert_awaited_once_with(tenant_id, resource_id)


@pytest.mark.asyncio
async def test_reenable_resource_dispatcher_routes_to_team_member():
    """Test that _reenable_resource correctly dispatches to team member method."""
    tenant_id = "tenant-123"
    resource_id = "member-456"

    with patch.object(
        downgrade_service,
        "_reenable_team_member",
        AsyncMock(return_value=True)
    ) as mock_reenable_member:
        result = await downgrade_service._reenable_resource(
            tenant_id=tenant_id,
            resource_type=ResourceType.TEAM_MEMBER,
            resource_id=resource_id
        )

    assert result is True
    mock_reenable_member.assert_awaited_once_with(tenant_id, resource_id)


@pytest.mark.asyncio
async def test_reenable_resource_dispatcher_routes_to_workflow():
    """Test that _reenable_resource correctly dispatches to workflow method."""
    tenant_id = "tenant-123"
    resource_id = "wf-canonical-456"

    with patch.object(
        downgrade_service,
        "_reenable_workflow",
        AsyncMock(return_value=True)
    ) as mock_reenable_wf:
        result = await downgrade_service._reenable_resource(
            tenant_id=tenant_id,
            resource_type=ResourceType.WORKFLOW,
            resource_id=resource_id
        )

    assert result is True
    mock_reenable_wf.assert_awaited_once_with(tenant_id, resource_id)


@pytest.mark.asyncio
async def test_cancel_grace_period_calls_reenable():
    """Test that cancel_grace_period automatically re-enables the resource."""
    tenant_id = "tenant-123"
    resource_id = "env-456"
    resource_type = ResourceType.ENVIRONMENT

    # Mock grace period cancellation
    mock_cancel_response = MockSupabaseResponse(data=[{
        "id": "gp-123",
        "tenant_id": tenant_id,
        "resource_type": resource_type.value,
        "resource_id": resource_id,
        "status": GracePeriodStatus.CANCELLED.value,
    }])

    with patch.object(
        downgrade_service.db_service.client,
        "table",
        return_value=MagicMock(
            update=MagicMock(return_value=MagicMock(
                eq=MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(
                        eq=MagicMock(return_value=MagicMock(
                            eq=MagicMock(return_value=MagicMock(
                                execute=MagicMock(return_value=mock_cancel_response)
                            ))
                        ))
                    ))
                ))
            ))
        )
    ), patch.object(
        downgrade_service,
        "_reenable_resource",
        AsyncMock(return_value=True)
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
async def test_cancel_grace_period_continues_on_reenable_failure():
    """Test that grace period is cancelled even if re-enable fails."""
    tenant_id = "tenant-123"
    resource_id = "env-456"
    resource_type = ResourceType.ENVIRONMENT

    # Mock grace period cancellation (successful)
    mock_cancel_response = MockSupabaseResponse(data=[{
        "id": "gp-123",
        "tenant_id": tenant_id,
        "resource_type": resource_type.value,
        "resource_id": resource_id,
        "status": GracePeriodStatus.CANCELLED.value,
    }])

    with patch.object(
        downgrade_service.db_service.client,
        "table",
        return_value=MagicMock(
            update=MagicMock(return_value=MagicMock(
                eq=MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(
                        eq=MagicMock(return_value=MagicMock(
                            execute=MagicMock(return_value=mock_cancel_response)
                        ))
                    ))
                ))
            ))
        )
    ), patch.object(
        downgrade_service,
        "_reenable_resource",
        AsyncMock(return_value=False)  # Re-enable fails
    ) as mock_reenable:
        result = await downgrade_service.cancel_grace_period(
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id
        )

    # Grace period should still be cancelled
    assert result is True

    # Re-enable should have been attempted
    mock_reenable.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancel_grace_periods_for_compliant_resources_reenables_all():
    """Test that compliant resources have grace periods cancelled and are re-enabled."""
    tenant_id = "tenant-123"

    # Mock active grace periods
    active_grace_periods = [
        {
            "id": "gp-env-1",
            "tenant_id": tenant_id,
            "resource_type": ResourceType.ENVIRONMENT.value,
            "resource_id": "env-1",
            "status": GracePeriodStatus.ACTIVE.value,
        },
        {
            "id": "gp-member-1",
            "tenant_id": tenant_id,
            "resource_type": ResourceType.TEAM_MEMBER.value,
            "resource_id": "member-1",
            "status": GracePeriodStatus.ACTIVE.value,
        },
        {
            "id": "gp-wf-1",
            "tenant_id": tenant_id,
            "resource_type": ResourceType.WORKFLOW.value,
            "resource_id": "wf-canonical-1",
            "status": GracePeriodStatus.ACTIVE.value,
        },
    ]

    with patch.object(
        downgrade_service,
        "get_active_grace_periods",
        AsyncMock(return_value=active_grace_periods)
    ), patch.object(
        downgrade_service,
        "detect_environment_overlimit",
        # No environments are over limit now
        AsyncMock(return_value=(False, 1, 2, []))
    ), patch.object(
        downgrade_service,
        "detect_team_member_overlimit",
        # No team members are over limit now
        AsyncMock(return_value=(False, 1, 2, []))
    ), patch.object(
        downgrade_service,
        "detect_workflow_overlimit",
        # No workflows are over limit now
        AsyncMock(return_value=(False, 1, 2, []))
    ), patch.object(
        downgrade_service,
        "cancel_grace_period",
        AsyncMock(return_value=True)
    ) as mock_cancel:
        result = await downgrade_service.cancel_grace_periods_for_compliant_resources(tenant_id)

    # All 3 grace periods should be cancelled
    assert result["cancelled_count"] == 3
    assert result["cancelled_by_type"]["environment"] == 1
    assert result["cancelled_by_type"]["team_member"] == 1
    assert result["cancelled_by_type"]["workflow"] == 1

    # Verify cancel was called for each resource
    assert mock_cancel.await_count == 3


@pytest.mark.asyncio
async def test_cancel_grace_periods_keeps_overlimit_resources():
    """Test that resources still over limit keep their grace periods."""
    tenant_id = "tenant-123"

    # Mock active grace periods
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
    ]

    with patch.object(
        downgrade_service,
        "get_active_grace_periods",
        AsyncMock(return_value=active_grace_periods)
    ), patch.object(
        downgrade_service,
        "detect_environment_overlimit",
        # env-1 is still over limit, env-2 is compliant
        AsyncMock(return_value=(True, 2, 1, ["env-1"]))
    ), patch.object(
        downgrade_service,
        "detect_team_member_overlimit",
        AsyncMock(return_value=(False, 0, 0, []))
    ), patch.object(
        downgrade_service,
        "detect_workflow_overlimit",
        AsyncMock(return_value=(False, 0, 0, []))
    ), patch.object(
        downgrade_service,
        "cancel_grace_period",
        AsyncMock(return_value=True)
    ) as mock_cancel:
        result = await downgrade_service.cancel_grace_periods_for_compliant_resources(tenant_id)

    # Only env-2's grace period should be cancelled
    assert result["cancelled_count"] == 1
    assert result["cancelled_by_type"]["environment"] == 1

    # Verify cancel was only called once (for env-2)
    assert mock_cancel.await_count == 1
    mock_cancel.assert_awaited_with(
        tenant_id=tenant_id,
        resource_type=ResourceType.ENVIRONMENT,
        resource_id="env-2"
    )


@pytest.mark.asyncio
async def test_handle_plan_upgrade_calls_cancel_grace_periods():
    """Test that handle_plan_upgrade uses the cancel_grace_periods method."""
    tenant_id = "tenant-123"
    old_plan = "starter"
    new_plan = "pro"

    active_grace_periods = [
        {
            "id": "gp-env-1",
            "tenant_id": tenant_id,
            "resource_type": ResourceType.ENVIRONMENT.value,
            "resource_id": "env-1",
            "status": GracePeriodStatus.ACTIVE.value,
        },
    ]

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
        AsyncMock(return_value=active_grace_periods)
    ), patch.object(
        downgrade_service,
        "cancel_grace_periods_for_compliant_resources",
        AsyncMock(return_value=cancellation_result)
    ) as mock_cancel_compliant:
        result = await downgrade_service.handle_plan_upgrade(
            tenant_id=tenant_id,
            old_plan=old_plan,
            new_plan=new_plan
        )

    # Verify the method was called
    mock_cancel_compliant.assert_awaited_once_with(tenant_id)

    # Verify the summary is correct
    assert result["grace_periods_cancelled"] == 1
    assert result["grace_periods_by_type"]["environment"] == 1
    assert "Cancelled grace periods for: 1 environment" in result["actions_taken"]


@pytest.mark.asyncio
async def test_handle_plan_upgrade_no_active_grace_periods():
    """Test handle_plan_upgrade when there are no active grace periods."""
    tenant_id = "tenant-123"
    old_plan = "starter"
    new_plan = "pro"

    with patch.object(
        downgrade_service,
        "get_active_grace_periods",
        AsyncMock(return_value=[])
    ), patch.object(
        downgrade_service,
        "cancel_grace_periods_for_compliant_resources",
        AsyncMock()
    ) as mock_cancel_compliant:
        result = await downgrade_service.handle_plan_upgrade(
            tenant_id=tenant_id,
            old_plan=old_plan,
            new_plan=new_plan
        )

    # Should not call cancel_grace_periods_for_compliant_resources
    mock_cancel_compliant.assert_not_awaited()

    # Verify the summary indicates no action needed
    assert result["grace_periods_cancelled"] == 0
    assert "No active grace periods to cancel" in result["actions_taken"]


@pytest.mark.asyncio
async def test_reenable_is_idempotent():
    """Test that re-enable methods are idempotent and safe to call multiple times."""
    tenant_id = "tenant-123"
    environment_id = "env-456"

    # Mock response - same for both calls
    mock_response = MockSupabaseResponse(data=[{
        "id": environment_id,
        "tenant_id": tenant_id,
        "is_read_only": False,
        "is_active": True,
    }])

    with patch.object(
        downgrade_service.db_service.client,
        "table",
        return_value=MagicMock(
            update=MagicMock(return_value=MagicMock(
                eq=MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(
                        execute=MagicMock(return_value=mock_response)
                    ))
                ))
            ))
        )
    ):
        # Call twice
        result1 = await downgrade_service._reenable_environment(tenant_id, environment_id)
        result2 = await downgrade_service._reenable_environment(tenant_id, environment_id)

    # Both should succeed
    assert result1 is True
    assert result2 is True


@pytest.mark.asyncio
async def test_reenable_handles_database_error_gracefully():
    """Test that re-enable methods handle database errors gracefully."""
    tenant_id = "tenant-123"
    environment_id = "env-456"

    with patch.object(
        downgrade_service.db_service.client,
        "table",
        side_effect=Exception("Database connection error")
    ):
        result = await downgrade_service._reenable_environment(tenant_id, environment_id)

    # Should return False on error, not raise
    assert result is False


@pytest.mark.asyncio
async def test_upgrade_flow_integration():
    """Integration test for complete upgrade flow with re-enable logic."""
    tenant_id = "tenant-123"
    old_plan = "starter"
    new_plan = "business"

    # Scenario: Tenant had 3 environments but starter only allows 1
    # After upgrade to business (allows 5), all 3 should be re-enabled

    active_grace_periods = [
        {
            "id": "gp-env-1",
            "tenant_id": tenant_id,
            "resource_type": ResourceType.ENVIRONMENT.value,
            "resource_id": "env-2",
            "status": GracePeriodStatus.ACTIVE.value,
        },
        {
            "id": "gp-env-2",
            "tenant_id": tenant_id,
            "resource_type": ResourceType.ENVIRONMENT.value,
            "resource_id": "env-3",
            "status": GracePeriodStatus.ACTIVE.value,
        },
    ]

    # Mock that no environments are over limit after upgrade
    mock_cancel_response = MockSupabaseResponse(data=[{"id": "gp-env-1"}])

    with patch.object(
        downgrade_service,
        "get_active_grace_periods",
        AsyncMock(return_value=active_grace_periods)
    ), patch.object(
        downgrade_service,
        "detect_environment_overlimit",
        AsyncMock(return_value=(False, 3, 5, []))  # 3 envs, limit is 5
    ), patch.object(
        downgrade_service,
        "detect_team_member_overlimit",
        AsyncMock(return_value=(False, 2, 10, []))
    ), patch.object(
        downgrade_service,
        "detect_workflow_overlimit",
        AsyncMock(return_value=(False, 5, 100, []))
    ), patch.object(
        downgrade_service.db_service.client,
        "table",
        return_value=MagicMock(
            update=MagicMock(return_value=MagicMock(
                eq=MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(
                        eq=MagicMock(return_value=MagicMock(
                            eq=MagicMock(return_value=MagicMock(
                                execute=MagicMock(return_value=mock_cancel_response)
                            ))
                        ))
                    ))
                ))
            ))
        )
    ), patch.object(
        downgrade_service,
        "_reenable_environment",
        AsyncMock(return_value=True)
    ) as mock_reenable_env:
        result = await downgrade_service.handle_plan_upgrade(
            tenant_id=tenant_id,
            old_plan=old_plan,
            new_plan=new_plan
        )

    # Both environments should be re-enabled
    assert result["grace_periods_cancelled"] == 2
    assert result["grace_periods_by_type"]["environment"] == 2
    assert mock_reenable_env.await_count == 2
