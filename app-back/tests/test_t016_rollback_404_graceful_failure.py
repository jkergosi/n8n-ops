"""
Test suite for T016: Test rollback fails gracefully when no snapshot exists (404 response).

This test verifies that the rollback operation fails gracefully with proper 404 responses
when attempting to rollback without an available snapshot.

Test Coverage:
- Rollback via restore endpoint returns 404 when snapshot ID doesn't exist
- Rollback returns 404 when snapshot exists but has no workflows
- Rollback returns 404 with clear error message when no PRE_PROMOTION snapshot available
- Error responses include actionable information for users
- Rollback handles missing environment configurations gracefully
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


# Mock data
MOCK_TENANT_ID = "00000000-0000-0000-0000-000000000000"
MOCK_USER_ID = "user-123"

MOCK_ENVIRONMENT = {
    "id": "env-prod",
    "tenant_id": MOCK_TENANT_ID,
    "name": "Production",
    "n8n_type": "production",
    "n8n_name": "Production Environment",
    "n8n_base_url": "https://prod.n8n.example.com",
    "n8n_api_key": "test_api_key",
    "git_repo_url": "https://github.com/test-org/n8n-workflows",
    "git_branch": "main",
    "git_pat": "ghp_test_token",
    "environment_class": "production",
    "policy_flags": {"allow_rollback_in_prod": True},
}

MOCK_SNAPSHOT = {
    "id": "snap-123",
    "tenant_id": MOCK_TENANT_ID,
    "environment_id": "env-prod",
    "git_commit_sha": "abc123def456",
    "type": "pre_promotion",
    "created_by_user_id": MOCK_USER_ID,
    "related_deployment_id": "deploy-1",
    "created_at": "2024-01-10T10:00:00Z",
    "metadata_json": {
        "promotion_id": "promo-123",
        "reason": "Pre-promotion snapshot for promotion promo-123",
        "workflows_count": 1,
    }
}


# Mock entitlements for all tests
@pytest.fixture(autouse=True)
def mock_entitlements():
    """Mock entitlements service to allow all features for testing."""
    with patch("app.core.entitlements_gate.entitlements_service") as mock_ent:
        mock_ent.enforce_flag = AsyncMock(return_value=None)
        mock_ent.has_flag = AsyncMock(return_value=True)
        yield mock_ent


class TestRollbackGracefulFailureOn404:
    """Tests verifying rollback fails gracefully with 404 responses when no snapshot exists."""

    @pytest.mark.api
    def test_rollback_returns_404_when_snapshot_id_does_not_exist(self, client: TestClient, auth_headers):
        """
        Test that rollback via restore endpoint returns 404 when snapshot ID doesn't exist.

        Scenario:
        - User attempts to restore/rollback using a non-existent snapshot ID
        - API should return 404 with clear error message

        Verification:
        - Response status code is 404
        - Error message indicates snapshot not found
        - Error message includes the snapshot ID for debugging
        """
        non_existent_snapshot_id = "snap-nonexistent-12345"

        with patch("app.api.endpoints.snapshots.db_service") as mock_db:
            # Mock snapshot query returns no data
            mock_result = MagicMock()
            mock_result.data = None
            mock_db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_result

            # Attempt to restore non-existent snapshot
            response = client.post(
                f"/api/v1/snapshots/{non_existent_snapshot_id}/restore",
                headers=auth_headers
            )

            # Verify 404 response
            assert response.status_code == 404

            # Verify error message
            data = response.json()
            assert "detail" in data
            error_message = data["detail"].lower()
            assert "snapshot" in error_message
            assert "not found" in error_message
            assert non_existent_snapshot_id in data["detail"]

    @pytest.mark.api
    def test_rollback_returns_404_when_snapshot_has_no_workflows(self, client: TestClient, auth_headers):
        """
        Test that rollback returns 404 when snapshot exists but GitHub has no workflows at that commit.

        Scenario:
        - Snapshot exists in database with a commit SHA
        - GitHub returns empty workflow list for that commit SHA
        - This indicates snapshot is corrupted or GitHub state has changed
        - User should receive clear 404 error explaining the issue

        Verification:
        - Response status code is 404
        - Error message indicates no workflows found
        - Error message includes commit SHA for debugging
        """
        with patch("app.api.endpoints.snapshots.db_service") as mock_db, \
             patch("app.api.endpoints.snapshots.environment_action_guard") as mock_guard, \
             patch("app.api.endpoints.snapshots.GitHubService") as MockGitHubService, \
             patch("app.api.endpoints.snapshots.ProviderRegistry") as mock_registry, \
             patch("app.api.endpoints.snapshots.create_audit_log") as mock_audit:

            # Mock snapshot exists
            mock_snapshot_result = MagicMock()
            mock_snapshot_result.data = MOCK_SNAPSHOT
            mock_db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_snapshot_result

            # Mock environment exists
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENT)

            # Mock action guard allows restore
            mock_guard.assert_can_perform_action = MagicMock(return_value=None)

            # Mock GitHub service returns EMPTY workflows dict (no workflows at commit SHA)
            mock_github = MagicMock()
            mock_github.get_all_workflows_from_github = AsyncMock(return_value={})
            MockGitHubService.return_value = mock_github

            mock_registry.get_adapter_for_environment.return_value = MagicMock()
            mock_audit.return_value = AsyncMock()

            # Attempt rollback
            response = client.post(
                f"/api/v1/snapshots/{MOCK_SNAPSHOT['id']}/restore",
                headers=auth_headers
            )

            # Verify 404 response
            assert response.status_code == 404

            # Verify error message
            data = response.json()
            assert "detail" in data
            error_message = data["detail"].lower()
            assert "no workflows found" in error_message
            assert MOCK_SNAPSHOT["git_commit_sha"] in data["detail"]

    @pytest.mark.api
    def test_rollback_error_message_is_clear_and_actionable(self, client: TestClient, auth_headers):
        """
        Test that 404 error messages for rollback failures are clear and actionable.

        Scenario:
        - User attempts rollback but snapshot doesn't exist
        - Error message should help user understand why rollback is unavailable

        Verification:
        - Error message uses clear language
        - Error message includes relevant IDs for debugging
        - Error message indicates what the user should check
        """
        snapshot_id = "snap-missing"

        with patch("app.api.endpoints.snapshots.db_service") as mock_db:
            # Mock snapshot not found
            mock_result = MagicMock()
            mock_result.data = None
            mock_db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_result

            response = client.post(
                f"/api/v1/snapshots/{snapshot_id}/restore",
                headers=auth_headers
            )

            assert response.status_code == 404
            data = response.json()

            # Verify error message quality
            error_detail = data["detail"]

            # Should include the snapshot ID
            assert snapshot_id in error_detail

            # Should clearly state the problem
            assert "not found" in error_detail.lower() or "does not exist" in error_detail.lower()

            # Should mention snapshot (the resource type)
            assert "snapshot" in error_detail.lower()

    @pytest.mark.api
    def test_rollback_with_invalid_snapshot_id_format_returns_404(self, client: TestClient, auth_headers):
        """
        Test that rollback with malformed snapshot ID returns 404.

        Scenario:
        - User provides invalid/malformed snapshot ID
        - System should handle gracefully with 404

        Verification:
        - Response is 404 (not 500 or other error)
        - Error message is appropriate
        """
        invalid_snapshot_ids = [
            "invalid-id-format",
            "",
            "snap@#$%invalid",
        ]

        for invalid_id in invalid_snapshot_ids:
            if not invalid_id:  # Skip empty string as it's a routing issue
                continue

            with patch("app.api.endpoints.snapshots.db_service") as mock_db:
                # Mock no snapshot found
                mock_result = MagicMock()
                mock_result.data = None
                mock_db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_result

                response = client.post(
                    f"/api/v1/snapshots/{invalid_id}/restore",
                    headers=auth_headers
                )

                # Should return 404, 405, or 422 (not crash with 500)
                # 405 can occur if special characters are rejected by routing
                assert response.status_code in [404, 405, 422], f"Expected 404/405/422 for invalid ID '{invalid_id}', got {response.status_code}"

    @pytest.mark.api
    def test_rollback_failure_does_not_modify_environment_state(self, client: TestClient, auth_headers):
        """
        Test that when rollback fails with 404, no changes are made to the environment.

        Scenario:
        - User attempts rollback with non-existent snapshot
        - System returns 404
        - No workflows should be modified

        Verification:
        - update_workflow is never called on the adapter
        - No workflows are touched
        """
        with patch("app.api.endpoints.snapshots.db_service") as mock_db, \
             patch("app.api.endpoints.snapshots.ProviderRegistry") as mock_registry:

            # Mock snapshot not found
            mock_result = MagicMock()
            mock_result.data = None
            mock_db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_result

            # Mock adapter
            mock_adapter = MagicMock()
            mock_adapter.update_workflow = AsyncMock()
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            response = client.post(
                "/api/v1/snapshots/nonexistent/restore",
                headers=auth_headers
            )

            # Verify 404 returned
            assert response.status_code == 404

            # Verify NO workflows were updated
            mock_adapter.update_workflow.assert_not_called()

    @pytest.mark.api
    def test_rollback_handles_environment_not_found_gracefully(self, client: TestClient, auth_headers):
        """
        Test that rollback handles missing environment configuration gracefully.

        Scenario:
        - Snapshot exists and references an environment
        - Environment no longer exists or user has no access
        - System should return 404 with appropriate message

        Verification:
        - Response is 404
        - Error message indicates environment issue
        """
        with patch("app.api.endpoints.snapshots.db_service") as mock_db:
            # Mock snapshot exists
            mock_snapshot_result = MagicMock()
            mock_snapshot_result.data = MOCK_SNAPSHOT
            mock_db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_snapshot_result

            # Mock environment NOT found
            mock_db.get_environment = AsyncMock(return_value=None)

            response = client.post(
                f"/api/v1/snapshots/{MOCK_SNAPSHOT['id']}/restore",
                headers=auth_headers
            )

            # Verify 404 response
            assert response.status_code == 404

            # Verify error mentions environment
            data = response.json()
            error_message = data["detail"].lower()
            assert "environment" in error_message
            assert "not found" in error_message

    @pytest.mark.api
    def test_multiple_rollback_404_scenarios_return_consistent_format(self, client: TestClient, auth_headers):
        """
        Test that all 404 rollback failures return consistent error response format.

        Scenario:
        - Various 404 scenarios (snapshot not found, workflows not found, etc.)
        - All should return consistent JSON error format

        Verification:
        - All responses have 'detail' field
        - Status code is consistently 404
        - Response structure is predictable for client handling
        """
        scenarios = []

        # Scenario 1: Snapshot not found
        with patch("app.api.endpoints.snapshots.db_service") as mock_db:
            mock_result = MagicMock()
            mock_result.data = None
            mock_db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_result

            response1 = client.post(
                "/api/v1/snapshots/snap-notfound/restore",
                headers=auth_headers
            )
            scenarios.append(("snapshot_not_found", response1))

        # Scenario 2: No workflows in snapshot
        with patch("app.api.endpoints.snapshots.db_service") as mock_db, \
             patch("app.api.endpoints.snapshots.environment_action_guard") as mock_guard, \
             patch("app.api.endpoints.snapshots.GitHubService") as MockGitHubService, \
             patch("app.api.endpoints.snapshots.ProviderRegistry") as mock_registry, \
             patch("app.api.endpoints.snapshots.create_audit_log") as mock_audit:

            mock_snapshot_result = MagicMock()
            mock_snapshot_result.data = MOCK_SNAPSHOT
            mock_db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_snapshot_result
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENT)
            mock_guard.assert_can_perform_action = MagicMock(return_value=None)

            mock_github = MagicMock()
            mock_github.get_all_workflows_from_github = AsyncMock(return_value={})
            MockGitHubService.return_value = mock_github
            mock_registry.get_adapter_for_environment.return_value = MagicMock()
            mock_audit.return_value = AsyncMock()

            response2 = client.post(
                f"/api/v1/snapshots/{MOCK_SNAPSHOT['id']}/restore",
                headers=auth_headers
            )
            scenarios.append(("no_workflows", response2))

        # Verify all scenarios return consistent 404 format
        for scenario_name, response in scenarios:
            assert response.status_code == 404, f"Scenario '{scenario_name}' should return 404"

            data = response.json()
            assert "detail" in data, f"Scenario '{scenario_name}' should have 'detail' field"
            assert isinstance(data["detail"], str), f"Scenario '{scenario_name}' detail should be a string"
            assert len(data["detail"]) > 0, f"Scenario '{scenario_name}' detail should not be empty"

    @pytest.mark.api
    def test_rollback_404_response_includes_helpful_context(self, client: TestClient, auth_headers):
        """
        Test that 404 responses include helpful context for troubleshooting.

        Scenario:
        - Rollback fails due to missing snapshot
        - Error message should include relevant IDs and context

        Verification:
        - Error includes snapshot ID
        - Error message is descriptive
        """
        snapshot_id = "snap-debug-test-123"

        with patch("app.api.endpoints.snapshots.db_service") as mock_db:
            mock_result = MagicMock()
            mock_result.data = None
            mock_db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_result

            response = client.post(
                f"/api/v1/snapshots/{snapshot_id}/restore",
                headers=auth_headers
            )

            assert response.status_code == 404
            data = response.json()

            # Should include the snapshot ID for debugging
            assert snapshot_id in data["detail"]

            # Should be more than just "not found" - should provide context
            assert len(data["detail"]) > 20, "Error message should be descriptive"

    @pytest.mark.api
    def test_rollback_graceful_failure_with_commit_sha_in_error(self, client: TestClient, auth_headers):
        """
        Test that when workflows are not found at commit SHA, error includes the SHA.

        Scenario:
        - Snapshot exists with commit SHA
        - No workflows found at that commit in GitHub
        - Error should mention the commit SHA for debugging

        Verification:
        - Error includes commit SHA
        - Error explains what was being looked for
        """
        with patch("app.api.endpoints.snapshots.db_service") as mock_db, \
             patch("app.api.endpoints.snapshots.environment_action_guard") as mock_guard, \
             patch("app.api.endpoints.snapshots.GitHubService") as MockGitHubService, \
             patch("app.api.endpoints.snapshots.ProviderRegistry") as mock_registry, \
             patch("app.api.endpoints.snapshots.create_audit_log") as mock_audit:

            commit_sha = "very-specific-commit-sha-xyz789"
            snapshot_with_sha = {**MOCK_SNAPSHOT, "git_commit_sha": commit_sha}

            mock_snapshot_result = MagicMock()
            mock_snapshot_result.data = snapshot_with_sha
            mock_db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_snapshot_result
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENT)
            mock_guard.assert_can_perform_action = MagicMock(return_value=None)

            mock_github = MagicMock()
            mock_github.get_all_workflows_from_github = AsyncMock(return_value={})
            MockGitHubService.return_value = mock_github
            mock_registry.get_adapter_for_environment.return_value = MagicMock()
            mock_audit.return_value = AsyncMock()

            response = client.post(
                f"/api/v1/snapshots/{snapshot_with_sha['id']}/restore",
                headers=auth_headers
            )

            assert response.status_code == 404
            data = response.json()

            # Error should include the commit SHA for debugging
            assert commit_sha in data["detail"]
            assert "workflows" in data["detail"].lower()
