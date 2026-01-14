"""
Test suite to verify snapshot restore endpoint handles workflow rollback correctly.
This verifies task T005 requirements.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException
from app.schemas.deployment import SnapshotType


class TestSnapshotRestoreForRollback:
    """Verify the restore endpoint handles workflow rollback correctly for T005."""

    @pytest.mark.asyncio
    async def test_restore_endpoint_exists_and_callable(self):
        """Verify the restore endpoint exists at the correct path."""
        from app.api.endpoints.snapshots import restore_snapshot
        assert callable(restore_snapshot)

    @pytest.mark.asyncio
    async def test_restore_validates_snapshot_exists(self):
        """Verify restore returns 404 when snapshot doesn't exist."""
        from app.api.endpoints.snapshots import restore_snapshot

        with patch("app.api.endpoints.snapshots.db_service") as mock_db:
            # Mock snapshot not found
            mock_result = MagicMock()
            mock_result.data = None
            mock_db.client.table().select().eq().eq().single().execute.return_value = mock_result

            user_info = {
                "tenant": {"id": "tenant-123"},
                "user": {"id": "user-123", "role": "admin"}
            }

            with pytest.raises(HTTPException) as exc_info:
                await restore_snapshot("non-existent-snapshot", user_info)

            assert exc_info.value.status_code == 404
            assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_restore_checks_environment_action_guard(self):
        """Verify restore endpoint checks RESTORE_ROLLBACK action guard."""
        from app.api.endpoints.snapshots import restore_snapshot
        from app.services.environment_action_guard import ActionGuardError

        with patch("app.api.endpoints.snapshots.db_service") as mock_db, \
             patch("app.api.endpoints.snapshots.environment_action_guard") as mock_guard:

            # Mock snapshot exists
            mock_snapshot_result = MagicMock()
            mock_snapshot_result.data = {
                "id": "snap-123",
                "environment_id": "env-456",
                "git_commit_sha": "abc123",
                "type": SnapshotType.PRE_PROMOTION.value,
                "tenant_id": "tenant-123"
            }
            mock_db.client.table().select().eq().eq().single().execute.return_value = mock_snapshot_result

            # Mock environment exists
            mock_db.get_environment = AsyncMock(return_value={
                "id": "env-456",
                "environment_class": "production",
                "git_repo_url": "https://github.com/test/repo",
                "git_pat": "token",
                "git_branch": "main",
                "n8n_type": "production"
            })

            # Mock action guard denies access
            mock_guard.assert_can_perform_action = MagicMock(side_effect=ActionGuardError(
                action="restore_rollback",
                reason="Insufficient permissions"
            ))

            user_info = {
                "tenant": {"id": "tenant-123"},
                "user": {"id": "user-123", "role": "user"}
            }

            with pytest.raises(ActionGuardError):
                await restore_snapshot("snap-123", user_info)

            # Verify the guard was called with RESTORE_ROLLBACK action
            mock_guard.assert_can_perform_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_restore_loads_workflows_from_github_at_commit_sha(self):
        """Verify restore loads workflows from GitHub at the snapshot's commit SHA."""
        from app.api.endpoints.snapshots import restore_snapshot

        with patch("app.api.endpoints.snapshots.db_service") as mock_db, \
             patch("app.api.endpoints.snapshots.environment_action_guard") as mock_guard, \
             patch("app.api.endpoints.snapshots.GitHubService") as mock_github_cls, \
             patch("app.api.endpoints.snapshots.ProviderRegistry") as mock_registry:

            snapshot_commit_sha = "commit-sha-123"

            # Mock snapshot exists
            mock_snapshot_result = MagicMock()
            mock_snapshot_result.data = {
                "id": "snap-123",
                "environment_id": "env-456",
                "git_commit_sha": snapshot_commit_sha,
                "type": SnapshotType.PRE_PROMOTION.value,
                "tenant_id": "tenant-123"
            }
            mock_db.client.table().select().eq().eq().single().execute.return_value = mock_snapshot_result

            # Mock environment
            mock_db.get_environment = AsyncMock(return_value={
                "id": "env-456",
                "environment_class": "staging",
                "git_repo_url": "https://github.com/test/repo",
                "git_pat": "token",
                "git_branch": "main",
                "n8n_type": "staging"
            })

            # Mock action guard allows
            mock_guard.assert_can_perform_action = MagicMock(return_value=None)

            # Mock GitHub service
            mock_github = MagicMock()
            mock_workflows = {
                "wf-1": {"id": "wf-1", "name": "Workflow 1", "nodes": []},
                "wf-2": {"id": "wf-2", "name": "Workflow 2", "nodes": []}
            }
            mock_github.get_all_workflows_from_github = AsyncMock(return_value=mock_workflows)
            mock_github_cls.return_value = mock_github

            # Mock provider adapter
            mock_adapter = MagicMock()
            mock_adapter.update_workflow = AsyncMock()
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            # Mock notification service
            with patch("app.api.endpoints.snapshots.notification_service") as mock_notif:
                mock_notif.emit_event = AsyncMock()

                user_info = {
                    "tenant": {"id": "tenant-123"},
                    "user": {"id": "user-123", "role": "admin"}
                }

                result = await restore_snapshot("snap-123", user_info)

            # Verify GitHub service was called with the correct commit SHA
            mock_github.get_all_workflows_from_github.assert_called_once()
            call_args = mock_github.get_all_workflows_from_github.call_args
            assert call_args.kwargs.get("commit_sha") == snapshot_commit_sha

            # Verify workflows were restored
            assert result["success"] is True
            assert result["restored"] == 2

    @pytest.mark.asyncio
    async def test_restore_updates_workflows_via_provider(self):
        """Verify restore calls update_workflow for each workflow in the snapshot."""
        from app.api.endpoints.snapshots import restore_snapshot

        with patch("app.api.endpoints.snapshots.db_service") as mock_db, \
             patch("app.api.endpoints.snapshots.environment_action_guard") as mock_guard, \
             patch("app.api.endpoints.snapshots.GitHubService") as mock_github_cls, \
             patch("app.api.endpoints.snapshots.ProviderRegistry") as mock_registry:

            # Mock snapshot
            mock_snapshot_result = MagicMock()
            mock_snapshot_result.data = {
                "id": "snap-123",
                "environment_id": "env-456",
                "git_commit_sha": "abc123",
                "type": SnapshotType.PRE_PROMOTION.value,
                "tenant_id": "tenant-123"
            }
            mock_db.client.table().select().eq().eq().single().execute.return_value = mock_snapshot_result

            # Mock environment
            mock_db.get_environment = AsyncMock(return_value={
                "id": "env-456",
                "environment_class": "staging",
                "git_repo_url": "https://github.com/test/repo",
                "git_pat": "token",
                "git_branch": "main",
                "n8n_type": "staging"
            })

            mock_guard.assert_can_perform_action = MagicMock(return_value=None)

            # Mock GitHub service with workflows
            mock_github = MagicMock()
            workflow_1_data = {"id": "wf-1", "name": "Workflow 1", "nodes": []}
            workflow_2_data = {"id": "wf-2", "name": "Workflow 2", "nodes": []}
            mock_workflows = {
                "wf-1": workflow_1_data,
                "wf-2": workflow_2_data
            }
            mock_github.get_all_workflows_from_github = AsyncMock(return_value=mock_workflows)
            mock_github_cls.return_value = mock_github

            # Mock provider adapter
            mock_adapter = MagicMock()
            mock_adapter.update_workflow = AsyncMock()
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            with patch("app.api.endpoints.snapshots.notification_service") as mock_notif:
                mock_notif.emit_event = AsyncMock()

                user_info = {
                    "tenant": {"id": "tenant-123"},
                    "user": {"id": "user-123", "role": "admin"}
                }

                result = await restore_snapshot("snap-123", user_info)

            # Verify update_workflow was called for each workflow
            assert mock_adapter.update_workflow.call_count == 2
            call_args_list = mock_adapter.update_workflow.call_args_list

            # Verify correct workflow data was passed
            called_workflow_ids = {call[0][0] for call in call_args_list}
            assert "wf-1" in called_workflow_ids
            assert "wf-2" in called_workflow_ids

    @pytest.mark.asyncio
    async def test_restore_emits_audit_events(self):
        """Verify restore emits proper notification events for audit logging."""
        from app.api.endpoints.snapshots import restore_snapshot

        with patch("app.api.endpoints.snapshots.db_service") as mock_db, \
             patch("app.api.endpoints.snapshots.environment_action_guard") as mock_guard, \
             patch("app.api.endpoints.snapshots.GitHubService") as mock_github_cls, \
             patch("app.api.endpoints.snapshots.ProviderRegistry") as mock_registry, \
             patch("app.api.endpoints.snapshots.notification_service") as mock_notif:

            # Mock snapshot
            mock_snapshot_result = MagicMock()
            mock_snapshot_result.data = {
                "id": "snap-123",
                "environment_id": "env-456",
                "git_commit_sha": "abc123",
                "type": SnapshotType.PRE_PROMOTION.value,
                "tenant_id": "tenant-123"
            }
            mock_db.client.table().select().eq().eq().single().execute.return_value = mock_snapshot_result

            # Mock environment
            mock_db.get_environment = AsyncMock(return_value={
                "id": "env-456",
                "environment_class": "staging",
                "git_repo_url": "https://github.com/test/repo",
                "git_pat": "token",
                "git_branch": "main",
                "n8n_type": "staging"
            })

            mock_guard.assert_can_perform_action = MagicMock(return_value=None)

            # Mock GitHub service
            mock_github = MagicMock()
            mock_workflows = {"wf-1": {"id": "wf-1", "name": "Workflow 1"}}
            mock_github.get_all_workflows_from_github = AsyncMock(return_value=mock_workflows)
            mock_github_cls.return_value = mock_github

            # Mock provider adapter
            mock_adapter = MagicMock()
            mock_adapter.update_workflow = AsyncMock()
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            # Mock notification service
            mock_notif.emit_event = AsyncMock()

            user_info = {
                "tenant": {"id": "tenant-123"},
                "user": {"id": "user-123", "role": "admin"}
            }

            result = await restore_snapshot("snap-123", user_info)

            # Verify notification event was emitted
            mock_notif.emit_event.assert_called()
            call_args = mock_notif.emit_event.call_args

            # Verify event type is correct
            assert call_args.kwargs["event_type"] in ["snapshot.restore_success", "snapshot.restore_failure"]
            assert call_args.kwargs["tenant_id"] == "tenant-123"
            assert call_args.kwargs["environment_id"] == "env-456"

            # Verify metadata includes snapshot_id
            metadata = call_args.kwargs["metadata"]
            assert metadata["snapshot_id"] == "snap-123"

    @pytest.mark.asyncio
    async def test_restore_handles_workflow_restore_failures_gracefully(self):
        """Verify restore continues on individual workflow failures and reports errors."""
        from app.api.endpoints.snapshots import restore_snapshot

        with patch("app.api.endpoints.snapshots.db_service") as mock_db, \
             patch("app.api.endpoints.snapshots.environment_action_guard") as mock_guard, \
             patch("app.api.endpoints.snapshots.GitHubService") as mock_github_cls, \
             patch("app.api.endpoints.snapshots.ProviderRegistry") as mock_registry:

            # Mock snapshot
            mock_snapshot_result = MagicMock()
            mock_snapshot_result.data = {
                "id": "snap-123",
                "environment_id": "env-456",
                "git_commit_sha": "abc123",
                "type": SnapshotType.PRE_PROMOTION.value,
                "tenant_id": "tenant-123"
            }
            mock_db.client.table().select().eq().eq().single().execute.return_value = mock_snapshot_result

            # Mock environment
            mock_db.get_environment = AsyncMock(return_value={
                "id": "env-456",
                "environment_class": "staging",
                "git_repo_url": "https://github.com/test/repo",
                "git_pat": "token",
                "git_branch": "main",
                "n8n_type": "staging"
            })

            mock_guard.assert_can_perform_action = MagicMock(return_value=None)

            # Mock GitHub service
            mock_github = MagicMock()
            mock_workflows = {
                "wf-1": {"id": "wf-1", "name": "Workflow 1"},
                "wf-2": {"id": "wf-2", "name": "Workflow 2"}
            }
            mock_github.get_all_workflows_from_github = AsyncMock(return_value=mock_workflows)
            mock_github_cls.return_value = mock_github

            # Mock provider adapter - first workflow fails, second succeeds
            mock_adapter = MagicMock()
            async def mock_update_workflow(wf_id, wf_data):
                if wf_id == "wf-1":
                    raise Exception("Failed to update workflow")
                # wf-2 succeeds

            mock_adapter.update_workflow = AsyncMock(side_effect=mock_update_workflow)
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            with patch("app.api.endpoints.snapshots.notification_service") as mock_notif:
                mock_notif.emit_event = AsyncMock()

                user_info = {
                    "tenant": {"id": "tenant-123"},
                    "user": {"id": "user-123", "role": "admin"}
                }

                result = await restore_snapshot("snap-123", user_info)

            # Verify partial success
            assert result["restored"] == 1
            assert result["failed"] == 1
            assert len(result["errors"]) == 1
            assert "wf-1" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_restore_returns_404_when_no_workflows_in_snapshot(self):
        """Verify restore returns 404 when snapshot has no workflows."""
        from app.api.endpoints.snapshots import restore_snapshot

        with patch("app.api.endpoints.snapshots.db_service") as mock_db, \
             patch("app.api.endpoints.snapshots.environment_action_guard") as mock_guard, \
             patch("app.api.endpoints.snapshots.GitHubService") as mock_github_cls, \
             patch("app.api.endpoints.snapshots.ProviderRegistry") as mock_registry:

            # Mock snapshot
            mock_snapshot_result = MagicMock()
            mock_snapshot_result.data = {
                "id": "snap-123",
                "environment_id": "env-456",
                "git_commit_sha": "abc123",
                "type": SnapshotType.PRE_PROMOTION.value,
                "tenant_id": "tenant-123"
            }
            mock_db.client.table().select().eq().eq().single().execute.return_value = mock_snapshot_result

            # Mock environment
            mock_db.get_environment = AsyncMock(return_value={
                "id": "env-456",
                "environment_class": "staging",
                "git_repo_url": "https://github.com/test/repo",
                "git_pat": "token",
                "git_branch": "main",
                "n8n_type": "staging"
            })

            mock_guard.assert_can_perform_action = MagicMock(return_value=None)

            # Mock GitHub service with no workflows
            mock_github = MagicMock()
            mock_github.get_all_workflows_from_github = AsyncMock(return_value={})
            mock_github_cls.return_value = mock_github

            mock_registry.get_adapter_for_environment.return_value = MagicMock()

            user_info = {
                "tenant": {"id": "tenant-123"},
                "user": {"id": "user-123", "role": "admin"}
            }

            with pytest.raises(HTTPException) as exc_info:
                await restore_snapshot("snap-123", user_info)

            assert exc_info.value.status_code == 404
            assert "no workflows found" in exc_info.value.detail.lower()
