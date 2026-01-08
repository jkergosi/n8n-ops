"""
Test suite for T008: Ensure 404 error response when no snapshot exists for rollback.

This test verifies that appropriate 404 errors are returned in rollback scenarios:
1. When querying for latest snapshot but none exists
2. When attempting to restore a non-existent snapshot
3. When snapshot exists but has no workflow data
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException
from app.schemas.deployment import SnapshotType


class TestT008_404ErrorHandling:
    """Verify 404 error responses for rollback scenarios (T008)."""

    @pytest.mark.asyncio
    async def test_get_latest_snapshot_returns_404_when_no_snapshot_exists(self):
        """
        GIVEN: A workflow and environment with no PRE_PROMOTION snapshots
        WHEN: User requests the latest snapshot for rollback
        THEN: API returns 404 with 'No snapshot available for rollback' message
        """
        from app.api.endpoints.snapshots import get_latest_snapshot_for_workflow_environment

        with patch("app.api.endpoints.snapshots.db_service") as mock_db:
            # Mock query that returns no results
            mock_result = MagicMock()
            mock_result.data = []  # Empty list indicates no snapshots found
            mock_db.client.table().select().eq().eq().eq().order().limit().execute.return_value = mock_result

            user_info = {
                "tenant": {"id": "tenant-123"},
                "user": {"id": "user-123", "role": "admin"}
            }

            with pytest.raises(HTTPException) as exc_info:
                await get_latest_snapshot_for_workflow_environment(
                    workflow_id="wf-123",
                    environment_id="env-456",
                    type=SnapshotType.PRE_PROMOTION,
                    user_info=user_info,
                    _={}
                )

            # Verify 404 status code
            assert exc_info.value.status_code == 404

            # Verify error message mentions rollback and the environment
            assert "no snapshot available for rollback" in exc_info.value.detail.lower()
            assert "env-456" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_latest_snapshot_returns_404_when_no_pre_promotion_snapshot_exists(self):
        """
        GIVEN: An environment with only MANUAL_BACKUP snapshots (no PRE_PROMOTION)
        WHEN: User requests the latest PRE_PROMOTION snapshot
        THEN: API returns 404 indicating no PRE_PROMOTION snapshot exists
        """
        from app.api.endpoints.snapshots import get_latest_snapshot_for_workflow_environment

        with patch("app.api.endpoints.snapshots.db_service") as mock_db:
            # Mock query returns empty for PRE_PROMOTION filter
            mock_result = MagicMock()
            mock_result.data = []
            mock_db.client.table().select().eq().eq().eq().order().limit().execute.return_value = mock_result

            user_info = {
                "tenant": {"id": "tenant-123"},
                "user": {"id": "user-123", "role": "admin"}
            }

            with pytest.raises(HTTPException) as exc_info:
                await get_latest_snapshot_for_workflow_environment(
                    workflow_id="wf-123",
                    environment_id="env-production",
                    type=SnapshotType.PRE_PROMOTION,
                    user_info=user_info,
                    _={}
                )

            assert exc_info.value.status_code == 404
            assert "no snapshot available" in exc_info.value.detail.lower()
            assert "pre_promotion" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_restore_snapshot_returns_404_when_snapshot_id_not_found(self):
        """
        GIVEN: A user attempts to restore using a non-existent snapshot ID
        WHEN: The restore endpoint is called
        THEN: API returns 404 with 'Snapshot not found' message
        """
        from app.api.endpoints.snapshots import restore_snapshot

        with patch("app.api.endpoints.snapshots.db_service") as mock_db:
            # Mock snapshot query returns no data
            mock_result = MagicMock()
            mock_result.data = None
            mock_db.client.table().select().eq().eq().single().execute.return_value = mock_result

            user_info = {
                "tenant": {"id": "tenant-123"},
                "user": {"id": "user-123", "role": "admin", "email": "test@example.com"}
            }

            with pytest.raises(HTTPException) as exc_info:
                await restore_snapshot("non-existent-snapshot-id", user_info)

            # Verify 404 status
            assert exc_info.value.status_code == 404

            # Verify error message contains snapshot ID
            assert "snapshot" in exc_info.value.detail.lower()
            assert "not found" in exc_info.value.detail.lower()
            assert "non-existent-snapshot-id" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_restore_snapshot_returns_404_when_no_workflows_in_github(self):
        """
        GIVEN: A snapshot exists but GitHub returns no workflows at the commit SHA
        WHEN: User attempts to restore the snapshot
        THEN: API returns 404 indicating no workflows found for restoration
        """
        from app.api.endpoints.snapshots import restore_snapshot

        with patch("app.api.endpoints.snapshots.db_service") as mock_db, \
             patch("app.api.endpoints.snapshots.environment_action_guard") as mock_guard, \
             patch("app.api.endpoints.snapshots.GitHubService") as mock_github_cls, \
             patch("app.api.endpoints.snapshots.ProviderRegistry") as mock_registry:

            commit_sha = "abc123def456"

            # Mock snapshot exists
            mock_snapshot_result = MagicMock()
            mock_snapshot_result.data = {
                "id": "snap-valid",
                "environment_id": "env-456",
                "git_commit_sha": commit_sha,
                "type": SnapshotType.PRE_PROMOTION.value,
                "tenant_id": "tenant-123"
            }
            mock_db.client.table().select().eq().eq().single().execute.return_value = mock_snapshot_result

            # Mock environment exists
            mock_db.get_environment = AsyncMock(return_value={
                "id": "env-456",
                "environment_class": "production",
                "git_repo_url": "https://github.com/test/repo",
                "git_pat": "token123",
                "git_branch": "main",
                "n8n_type": "production",
                "n8n_name": "Production Environment"
            })

            # Mock action guard allows restore
            mock_guard.assert_can_perform_action = MagicMock(return_value=None)

            # Mock GitHub service returns EMPTY workflows dict
            mock_github = MagicMock()
            mock_github.get_all_workflows_from_github = AsyncMock(return_value={})
            mock_github_cls.return_value = mock_github

            mock_registry.get_adapter_for_environment.return_value = MagicMock()

            user_info = {
                "tenant": {"id": "tenant-123"},
                "user": {"id": "user-123", "role": "admin", "email": "admin@example.com", "name": "Admin User"}
            }

            # Mock audit logging
            with patch("app.api.endpoints.snapshots.create_audit_log") as mock_audit:
                mock_audit.return_value = AsyncMock()

                with pytest.raises(HTTPException) as exc_info:
                    await restore_snapshot("snap-valid", user_info)

            # Verify 404 error
            assert exc_info.value.status_code == 404

            # Verify error message indicates no workflows found
            assert "no workflows found" in exc_info.value.detail.lower()
            assert commit_sha in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_latest_snapshot_with_no_type_filter_returns_404_when_empty(self):
        """
        GIVEN: An environment with no snapshots at all
        WHEN: User requests the latest snapshot without type filter
        THEN: API returns 404 with appropriate message
        """
        from app.api.endpoints.snapshots import get_latest_snapshot_for_workflow_environment

        with patch("app.api.endpoints.snapshots.db_service") as mock_db:
            # Mock query returns empty (no snapshots of any type)
            mock_result = MagicMock()
            mock_result.data = []
            mock_db.client.table().select().eq().eq().order().limit().execute.return_value = mock_result

            user_info = {
                "tenant": {"id": "tenant-123"},
                "user": {"id": "user-123", "role": "admin"}
            }

            with pytest.raises(HTTPException) as exc_info:
                await get_latest_snapshot_for_workflow_environment(
                    workflow_id="wf-new",
                    environment_id="env-new",
                    type=None,  # No type filter
                    user_info=user_info,
                    _={}
                )

            assert exc_info.value.status_code == 404
            assert "no snapshot available" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_error_message_clarity_for_rollback_scenario(self):
        """
        Verify that the 404 error message provides clear guidance for rollback scenarios.
        The message should help users understand why rollback is not available.
        """
        from app.api.endpoints.snapshots import get_latest_snapshot_for_workflow_environment

        with patch("app.api.endpoints.snapshots.db_service") as mock_db:
            mock_result = MagicMock()
            mock_result.data = []
            mock_db.client.table().select().eq().eq().eq().order().limit().execute.return_value = mock_result

            user_info = {
                "tenant": {"id": "tenant-123"},
                "user": {"id": "user-123", "role": "operator"}
            }

            with pytest.raises(HTTPException) as exc_info:
                await get_latest_snapshot_for_workflow_environment(
                    workflow_id="critical-workflow",
                    environment_id="prod-env",
                    type=SnapshotType.PRE_PROMOTION,
                    user_info=user_info,
                    _={}
                )

            error_detail = exc_info.value.detail

            # Error should be actionable and clear
            assert "rollback" in error_detail.lower()
            assert "prod-env" in error_detail  # Includes environment ID

            # Should indicate what type of snapshot is missing
            assert "PRE_PROMOTION" in error_detail or "pre_promotion" in error_detail.lower()
