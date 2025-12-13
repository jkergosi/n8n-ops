"""
Tests for restore API endpoints.
Critical path tests for GitHub restore preview, execution, snapshots, and rollback.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from fastapi.testclient import TestClient


# Mock data
MOCK_TENANT_ID = "00000000-0000-0000-0000-000000000000"

MOCK_ENVIRONMENT = {
    "id": "env-1",
    "tenant_id": MOCK_TENANT_ID,
    "name": "Development",
    "n8n_type": "development",
    "n8n_base_url": "https://dev.n8n.example.com",
    "n8n_api_key": "test_api_key",
    "git_repo_url": "https://github.com/test-org/n8n-workflows",
    "git_branch": "main",
    "git_pat": "ghp_test_token",
    "n8n_encryption_key": "test_encryption_key",
    "is_active": True,
}

MOCK_ENVIRONMENT_NO_GIT = {
    "id": "env-2",
    "tenant_id": MOCK_TENANT_ID,
    "name": "Production",
    "n8n_type": "production",
    "n8n_base_url": "https://prod.n8n.example.com",
    "n8n_api_key": "test_api_key",
    "git_repo_url": None,
    "git_branch": None,
    "git_pat": None,
    "is_active": True,
}

MOCK_GITHUB_WORKFLOWS = [
    {
        "_comment": "Workflow ID: wf-1",
        "name": "Email Automation",
        "nodes": [
            {"id": "node-1", "type": "n8n-nodes-base.start", "name": "Start"},
            {"id": "node-2", "type": "n8n-nodes-base.emailSend", "name": "Send Email"},
        ],
        "connections": {},
        "active": False,
    },
    {
        "_comment": "Workflow ID: wf-2",
        "name": "Data Sync",
        "nodes": [
            {"id": "node-1", "type": "n8n-nodes-base.schedule", "name": "Schedule"},
            {"id": "node-2", "type": "n8n-nodes-base.httpRequest", "name": "API Call"},
            {"id": "node-3", "type": "n8n-nodes-base.postgres", "name": "Database"},
        ],
        "connections": {},
        "active": True,
    },
    {
        "_comment": "New workflow without ID",
        "name": "New Workflow",
        "nodes": [
            {"id": "node-1", "type": "n8n-nodes-base.webhook", "name": "Webhook"},
        ],
        "connections": {},
        "active": False,
    },
]

MOCK_N8N_WORKFLOWS = [
    {
        "id": "wf-1",
        "name": "Email Automation",
        "active": True,
        "nodes": [{"id": "node-1", "type": "n8n-nodes-base.start"}],
        "connections": {},
    },
]

MOCK_SNAPSHOTS = [
    {
        "id": "snap-1",
        "tenant_id": MOCK_TENANT_ID,
        "workflow_id": "wf-1",
        "workflow_name": "Email Automation",
        "version": 1,
        "data": {
            "id": "wf-1",
            "name": "Email Automation v1",
            "nodes": [{"id": "node-1", "type": "n8n-nodes-base.start"}],
            "connections": {},
        },
        "trigger": "manual",
        "created_at": "2024-01-01T00:00:00Z",
    },
    {
        "id": "snap-2",
        "tenant_id": MOCK_TENANT_ID,
        "workflow_id": "wf-1",
        "workflow_name": "Email Automation",
        "version": 2,
        "data": {
            "id": "wf-1",
            "name": "Email Automation v2",
            "nodes": [
                {"id": "node-1", "type": "n8n-nodes-base.start"},
                {"id": "node-2", "type": "n8n-nodes-base.emailSend"},
            ],
            "connections": {},
        },
        "trigger": "auto-before-restore",
        "created_at": "2024-01-02T00:00:00Z",
    },
]


class TestGetRestorePreview:
    """Tests for GET /restore/{environment_id}/preview endpoint."""

    def test_preview_success(self, client, auth_headers):
        """Should return preview of workflows to be restored."""
        with patch("app.api.endpoints.restore.db_service") as mock_db, \
             patch("app.api.endpoints.restore.GitHubService") as MockGitHubService, \
             patch("app.api.endpoints.restore.ProviderRegistry") as mock_registry:
            # Mock environment lookup
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENT)

            # Mock GitHub service
            mock_github = MagicMock()
            mock_github.is_configured.return_value = True
            mock_github.get_all_workflows_from_github = AsyncMock(return_value=MOCK_GITHUB_WORKFLOWS)
            MockGitHubService.return_value = mock_github

            # Mock n8n adapter
            mock_adapter = MagicMock()
            mock_adapter.get_workflows = AsyncMock(return_value=MOCK_N8N_WORKFLOWS)
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            response = client.get(
                "/api/v1/restore/env-1/preview",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["environment_id"] == "env-1"
            assert data["environment_name"] == "Development"
            assert data["github_repo"] == "https://github.com/test-org/n8n-workflows"
            assert len(data["workflows"]) == 3
            # Check workflow statuses (update vs new)
            assert data["total_update"] == 1  # wf-1 exists
            assert data["total_new"] == 2  # wf-2 and new workflow

    def test_preview_environment_not_found(self, client, auth_headers):
        """Should return 404 when environment not found."""
        with patch("app.api.endpoints.restore.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=None)

            response = client.get(
                "/api/v1/restore/non-existent/preview",
                headers=auth_headers,
            )

            assert response.status_code == 404
            assert "Environment not found" in response.json()["detail"]

    def test_preview_no_github_config(self, client, auth_headers):
        """Should return 400 when GitHub not configured."""
        with patch("app.api.endpoints.restore.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENT_NO_GIT)

            response = client.get(
                "/api/v1/restore/env-2/preview",
                headers=auth_headers,
            )

            assert response.status_code == 400
            assert "GitHub repository not configured" in response.json()["detail"]

    def test_preview_invalid_github_url(self, client, auth_headers):
        """Should return 400 for invalid GitHub URL format."""
        with patch("app.api.endpoints.restore.db_service") as mock_db:
            invalid_env = {**MOCK_ENVIRONMENT, "git_repo_url": "not-a-valid-url"}
            mock_db.get_environment = AsyncMock(return_value=invalid_env)

            response = client.get(
                "/api/v1/restore/env-1/preview",
                headers=auth_headers,
            )

            assert response.status_code == 400
            assert "Invalid GitHub repository URL" in response.json()["detail"]

    def test_preview_github_not_configured(self, client, auth_headers):
        """Should return 400 when GitHub service not properly configured."""
        with patch("app.api.endpoints.restore.db_service") as mock_db, \
             patch("app.api.endpoints.restore.GitHubService") as MockGitHubService:
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENT)

            mock_github = MagicMock()
            mock_github.is_configured.return_value = False
            MockGitHubService.return_value = mock_github

            response = client.get(
                "/api/v1/restore/env-1/preview",
                headers=auth_headers,
            )

            assert response.status_code == 400
            assert "GitHub is not properly configured" in response.json()["detail"]

    def test_preview_shows_encryption_key_availability(self, client, auth_headers):
        """Should indicate whether encryption key is available."""
        with patch("app.api.endpoints.restore.db_service") as mock_db, \
             patch("app.api.endpoints.restore.GitHubService") as MockGitHubService, \
             patch("app.api.endpoints.restore.ProviderRegistry") as mock_registry:
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENT)

            mock_github = MagicMock()
            mock_github.is_configured.return_value = True
            mock_github.get_all_workflows_from_github = AsyncMock(return_value=[])
            MockGitHubService.return_value = mock_github

            mock_adapter = MagicMock()
            mock_adapter.get_workflows = AsyncMock(return_value=[])
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            response = client.get(
                "/api/v1/restore/env-1/preview",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["has_encryption_key"] is True

    def test_preview_shows_node_counts(self, client, auth_headers):
        """Should include node counts in workflow previews."""
        with patch("app.api.endpoints.restore.db_service") as mock_db, \
             patch("app.api.endpoints.restore.GitHubService") as MockGitHubService, \
             patch("app.api.endpoints.restore.ProviderRegistry") as mock_registry:
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENT)

            mock_github = MagicMock()
            mock_github.is_configured.return_value = True
            mock_github.get_all_workflows_from_github = AsyncMock(return_value=MOCK_GITHUB_WORKFLOWS)
            MockGitHubService.return_value = mock_github

            mock_adapter = MagicMock()
            mock_adapter.get_workflows = AsyncMock(return_value=[])
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            response = client.get(
                "/api/v1/restore/env-1/preview",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            # Check node counts are included
            email_workflow = next(w for w in data["workflows"] if w["name"] == "Email Automation")
            assert email_workflow["nodes_count"] == 2


class TestExecuteRestore:
    """Tests for POST /restore/{environment_id}/execute endpoint."""

    def test_execute_restore_success(self, client, auth_headers):
        """Should restore workflows from GitHub to N8N."""
        restore_options = {
            "include_workflows": True,
            "include_credentials": False,
            "include_tags": False,
            "create_snapshots": True,
            "selected_workflow_ids": None,
        }

        with patch("app.api.endpoints.restore.db_service") as mock_db, \
             patch("app.api.endpoints.restore.GitHubService") as MockGitHubService, \
             patch("app.api.endpoints.restore.ProviderRegistry") as mock_registry:
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENT)
            mock_db.get_workflow_snapshots = AsyncMock(return_value=[])
            mock_db.create_workflow_snapshot = AsyncMock(return_value={"id": "snap-new"})
            mock_db.sync_workflows_from_n8n = AsyncMock()
            mock_db.update_environment_workflow_count = AsyncMock()

            mock_github = MagicMock()
            mock_github.get_all_workflows_from_github = AsyncMock(return_value=MOCK_GITHUB_WORKFLOWS)
            MockGitHubService.return_value = mock_github

            mock_adapter = MagicMock()
            mock_adapter.get_workflows = AsyncMock(return_value=MOCK_N8N_WORKFLOWS)
            mock_adapter.update_workflow = AsyncMock()
            mock_adapter.create_workflow = AsyncMock(return_value={"id": "wf-new"})
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            response = client.post(
                "/api/v1/restore/env-1/execute",
                json=restore_options,
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["workflows_updated"] >= 0
            assert data["workflows_created"] >= 0
            assert "results" in data

    def test_execute_restore_creates_snapshots(self, client, auth_headers):
        """Should create snapshots before updating existing workflows."""
        restore_options = {
            "include_workflows": True,
            "create_snapshots": True,
        }

        with patch("app.api.endpoints.restore.db_service") as mock_db, \
             patch("app.api.endpoints.restore.GitHubService") as MockGitHubService, \
             patch("app.api.endpoints.restore.ProviderRegistry") as mock_registry:
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENT)
            mock_db.get_workflow_snapshots = AsyncMock(return_value=[{"id": "snap-1"}])
            mock_db.create_workflow_snapshot = AsyncMock(return_value={"id": "snap-new"})
            mock_db.sync_workflows_from_n8n = AsyncMock()
            mock_db.update_environment_workflow_count = AsyncMock()

            mock_github = MagicMock()
            mock_github.get_all_workflows_from_github = AsyncMock(return_value=MOCK_GITHUB_WORKFLOWS[:1])
            MockGitHubService.return_value = mock_github

            mock_adapter = MagicMock()
            mock_adapter.get_workflows = AsyncMock(return_value=MOCK_N8N_WORKFLOWS)
            mock_adapter.update_workflow = AsyncMock()
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            response = client.post(
                "/api/v1/restore/env-1/execute",
                json=restore_options,
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["snapshots_created"] >= 1

    def test_execute_restore_selected_workflows_only(self, client, auth_headers):
        """Should only restore selected workflow IDs."""
        restore_options = {
            "include_workflows": True,
            "create_snapshots": False,
            "selected_workflow_ids": ["wf-1"],
        }

        with patch("app.api.endpoints.restore.db_service") as mock_db, \
             patch("app.api.endpoints.restore.GitHubService") as MockGitHubService, \
             patch("app.api.endpoints.restore.ProviderRegistry") as mock_registry:
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENT)
            mock_db.sync_workflows_from_n8n = AsyncMock()
            mock_db.update_environment_workflow_count = AsyncMock()

            mock_github = MagicMock()
            mock_github.get_all_workflows_from_github = AsyncMock(return_value=MOCK_GITHUB_WORKFLOWS)
            MockGitHubService.return_value = mock_github

            mock_adapter = MagicMock()
            mock_adapter.get_workflows = AsyncMock(return_value=MOCK_N8N_WORKFLOWS)
            mock_adapter.update_workflow = AsyncMock()
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            response = client.post(
                "/api/v1/restore/env-1/execute",
                json=restore_options,
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            # Should only have processed the selected workflow
            assert data["workflows_updated"] == 1

    def test_execute_restore_handles_workflow_failure(self, client, auth_headers):
        """Should track failed workflows in results."""
        restore_options = {
            "include_workflows": True,
            "create_snapshots": False,
        }

        with patch("app.api.endpoints.restore.db_service") as mock_db, \
             patch("app.api.endpoints.restore.GitHubService") as MockGitHubService, \
             patch("app.api.endpoints.restore.ProviderRegistry") as mock_registry:
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENT)
            mock_db.sync_workflows_from_n8n = AsyncMock()
            mock_db.update_environment_workflow_count = AsyncMock()

            mock_github = MagicMock()
            mock_github.get_all_workflows_from_github = AsyncMock(return_value=MOCK_GITHUB_WORKFLOWS[:1])
            MockGitHubService.return_value = mock_github

            mock_adapter = MagicMock()
            mock_adapter.get_workflows = AsyncMock(return_value=MOCK_N8N_WORKFLOWS)
            mock_adapter.update_workflow = AsyncMock(side_effect=Exception("API error"))
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            response = client.post(
                "/api/v1/restore/env-1/execute",
                json=restore_options,
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert data["workflows_failed"] >= 1
            assert len(data["errors"]) >= 1

    def test_execute_restore_environment_not_found(self, client, auth_headers):
        """Should return 404 when environment not found."""
        with patch("app.api.endpoints.restore.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=None)

            response = client.post(
                "/api/v1/restore/non-existent/execute",
                json={"include_workflows": True},
                headers=auth_headers,
            )

            assert response.status_code == 404


class TestGetWorkflowSnapshots:
    """Tests for GET /restore/snapshots/{workflow_id} endpoint."""

    def test_get_snapshots_success(self, client, auth_headers):
        """Should return all snapshots for a workflow."""
        with patch("app.api.endpoints.restore.db_service") as mock_db:
            mock_db.get_workflow_snapshots = AsyncMock(return_value=MOCK_SNAPSHOTS)

            response = client.get(
                "/api/v1/restore/snapshots/wf-1",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["workflow_id"] == "wf-1"
            assert data[0]["version"] == 1
            assert data[1]["version"] == 2

    def test_get_snapshots_empty(self, client, auth_headers):
        """Should return empty list when no snapshots exist."""
        with patch("app.api.endpoints.restore.db_service") as mock_db:
            mock_db.get_workflow_snapshots = AsyncMock(return_value=[])

            response = client.get(
                "/api/v1/restore/snapshots/wf-no-snapshots",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data == []

    def test_get_snapshots_includes_trigger_info(self, client, auth_headers):
        """Should include trigger type in snapshot response."""
        with patch("app.api.endpoints.restore.db_service") as mock_db:
            mock_db.get_workflow_snapshots = AsyncMock(return_value=MOCK_SNAPSHOTS)

            response = client.get(
                "/api/v1/restore/snapshots/wf-1",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data[0]["trigger"] == "manual"
            assert data[1]["trigger"] == "auto-before-restore"


class TestRollbackWorkflow:
    """Tests for POST /restore/rollback endpoint."""

    def test_rollback_success(self, client, auth_headers):
        """Should rollback workflow to a previous snapshot."""
        rollback_request = {"snapshot_id": "snap-1"}

        with patch("app.api.endpoints.restore.db_service") as mock_db, \
             patch("app.api.endpoints.restore.ProviderRegistry") as mock_registry:
            # Mock snapshot lookup
            mock_db.get_workflow_snapshots = AsyncMock(return_value=MOCK_SNAPSHOTS)
            mock_db.get_environments = AsyncMock(return_value=[MOCK_ENVIRONMENT])
            mock_db.create_workflow_snapshot = AsyncMock(return_value={"id": "snap-pre-rollback"})
            mock_db.sync_workflows_from_n8n = AsyncMock()

            # Mock adapter
            mock_adapter = MagicMock()
            mock_adapter.get_workflow = AsyncMock(return_value=MOCK_N8N_WORKFLOWS[0])
            mock_adapter.get_workflows = AsyncMock(return_value=MOCK_N8N_WORKFLOWS)
            mock_adapter.update_workflow = AsyncMock()
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            response = client.post(
                "/api/v1/restore/rollback",
                json=rollback_request,
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "rolled back" in data["message"].lower()
            assert data["workflow_id"] == "wf-1"

    def test_rollback_snapshot_not_found(self, client, auth_headers):
        """Should return 404 when snapshot not found."""
        with patch("app.api.endpoints.restore.db_service") as mock_db:
            mock_db.get_workflow_snapshots = AsyncMock(return_value=[])

            response = client.post(
                "/api/v1/restore/rollback",
                json={"snapshot_id": "non-existent"},
                headers=auth_headers,
            )

            assert response.status_code == 404
            assert "Snapshot not found" in response.json()["detail"]

    def test_rollback_no_workflow_data(self, client, auth_headers):
        """Should return 400 when snapshot has no workflow data."""
        snapshot_without_data = {
            "id": "snap-no-data",
            "workflow_id": "wf-1",
            "workflow_name": "Test",
            "version": 1,
            "data": None,
            "trigger": "manual",
            "created_at": "2024-01-01T00:00:00Z",
        }

        with patch("app.api.endpoints.restore.db_service") as mock_db:
            mock_db.get_workflow_snapshots = AsyncMock(return_value=[snapshot_without_data])

            response = client.post(
                "/api/v1/restore/rollback",
                json={"snapshot_id": "snap-no-data"},
                headers=auth_headers,
            )

            assert response.status_code == 400
            assert "does not contain workflow data" in response.json()["detail"]

    def test_rollback_workflow_not_found_in_any_environment(self, client, auth_headers):
        """Should return 404 when workflow not found in any environment."""
        with patch("app.api.endpoints.restore.db_service") as mock_db, \
             patch("app.api.endpoints.restore.ProviderRegistry") as mock_registry:
            mock_db.get_workflow_snapshots = AsyncMock(return_value=MOCK_SNAPSHOTS)
            mock_db.get_environments = AsyncMock(return_value=[MOCK_ENVIRONMENT])

            # Mock adapter that can't find the workflow
            mock_adapter = MagicMock()
            mock_adapter.get_workflow = AsyncMock(return_value=None)
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            response = client.post(
                "/api/v1/restore/rollback",
                json={"snapshot_id": "snap-1"},
                headers=auth_headers,
            )

            assert response.status_code == 404
            assert "Could not find workflow" in response.json()["detail"]

    def test_rollback_creates_pre_rollback_snapshot(self, client, auth_headers):
        """Should create snapshot of current state before rollback."""
        with patch("app.api.endpoints.restore.db_service") as mock_db, \
             patch("app.api.endpoints.restore.ProviderRegistry") as mock_registry:
            mock_db.get_workflow_snapshots = AsyncMock(return_value=MOCK_SNAPSHOTS)
            mock_db.get_environments = AsyncMock(return_value=[MOCK_ENVIRONMENT])
            mock_db.create_workflow_snapshot = AsyncMock(return_value={"id": "snap-pre-rollback"})
            mock_db.sync_workflows_from_n8n = AsyncMock()

            mock_adapter = MagicMock()
            mock_adapter.get_workflow = AsyncMock(return_value=MOCK_N8N_WORKFLOWS[0])
            mock_adapter.get_workflows = AsyncMock(return_value=MOCK_N8N_WORKFLOWS)
            mock_adapter.update_workflow = AsyncMock()
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            response = client.post(
                "/api/v1/restore/rollback",
                json={"snapshot_id": "snap-1"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            # Verify snapshot was created with correct trigger
            create_snapshot_calls = mock_db.create_workflow_snapshot.call_args_list
            assert len(create_snapshot_calls) >= 1
            snapshot_data = create_snapshot_calls[0][0][0]
            assert snapshot_data["trigger"] == "auto-before-rollback"


class TestExtractWorkflowIdFromComment:
    """Tests for extract_workflow_id_from_comment helper function."""

    def test_extract_valid_id(self):
        """Should extract workflow ID from _comment field."""
        from app.api.endpoints.restore import extract_workflow_id_from_comment

        workflow_data = {"_comment": "Workflow ID: wf-123", "name": "Test"}
        result = extract_workflow_id_from_comment(workflow_data)
        assert result == "wf-123"

    def test_extract_no_comment(self):
        """Should return None when no _comment field."""
        from app.api.endpoints.restore import extract_workflow_id_from_comment

        workflow_data = {"name": "Test"}
        result = extract_workflow_id_from_comment(workflow_data)
        assert result is None

    def test_extract_no_id_in_comment(self):
        """Should return None when _comment doesn't contain ID."""
        from app.api.endpoints.restore import extract_workflow_id_from_comment

        workflow_data = {"_comment": "Some other comment", "name": "Test"}
        result = extract_workflow_id_from_comment(workflow_data)
        assert result is None

    def test_extract_empty_comment(self):
        """Should return None for empty _comment."""
        from app.api.endpoints.restore import extract_workflow_id_from_comment

        workflow_data = {"_comment": "", "name": "Test"}
        result = extract_workflow_id_from_comment(workflow_data)
        assert result is None


class TestRestoreIntegration:
    """Integration tests for restore workflow."""

    def test_full_restore_flow(self, client, auth_headers):
        """Test complete flow: preview -> execute -> verify."""
        with patch("app.api.endpoints.restore.db_service") as mock_db, \
             patch("app.api.endpoints.restore.GitHubService") as MockGitHubService, \
             patch("app.api.endpoints.restore.ProviderRegistry") as mock_registry:
            # Setup mocks
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENT)
            mock_db.get_workflow_snapshots = AsyncMock(return_value=[])
            mock_db.create_workflow_snapshot = AsyncMock(return_value={"id": "snap-1"})
            mock_db.sync_workflows_from_n8n = AsyncMock()
            mock_db.update_environment_workflow_count = AsyncMock()

            mock_github = MagicMock()
            mock_github.is_configured.return_value = True
            mock_github.get_all_workflows_from_github = AsyncMock(return_value=MOCK_GITHUB_WORKFLOWS)
            MockGitHubService.return_value = mock_github

            mock_adapter = MagicMock()
            mock_adapter.get_workflows = AsyncMock(return_value=MOCK_N8N_WORKFLOWS)
            mock_adapter.update_workflow = AsyncMock()
            mock_adapter.create_workflow = AsyncMock(return_value={"id": "wf-new"})
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            # Step 1: Preview
            preview_response = client.get(
                "/api/v1/restore/env-1/preview",
                headers=auth_headers,
            )
            assert preview_response.status_code == 200
            preview_data = preview_response.json()
            assert len(preview_data["workflows"]) > 0

            # Step 2: Execute
            execute_response = client.post(
                "/api/v1/restore/env-1/execute",
                json={"include_workflows": True, "create_snapshots": True},
                headers=auth_headers,
            )
            assert execute_response.status_code == 200
            execute_data = execute_response.json()
            assert execute_data["success"] is True

    def test_restore_and_rollback_flow(self, client, auth_headers):
        """Test restore followed by rollback."""
        with patch("app.api.endpoints.restore.db_service") as mock_db, \
             patch("app.api.endpoints.restore.GitHubService") as MockGitHubService, \
             patch("app.api.endpoints.restore.ProviderRegistry") as mock_registry:
            # Setup mocks
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENT)
            mock_db.get_environments = AsyncMock(return_value=[MOCK_ENVIRONMENT])
            mock_db.get_workflow_snapshots = AsyncMock(return_value=MOCK_SNAPSHOTS)
            mock_db.create_workflow_snapshot = AsyncMock(return_value={"id": "snap-new"})
            mock_db.sync_workflows_from_n8n = AsyncMock()
            mock_db.update_environment_workflow_count = AsyncMock()

            mock_github = MagicMock()
            mock_github.get_all_workflows_from_github = AsyncMock(return_value=MOCK_GITHUB_WORKFLOWS[:1])
            MockGitHubService.return_value = mock_github

            mock_adapter = MagicMock()
            mock_adapter.get_workflow = AsyncMock(return_value=MOCK_N8N_WORKFLOWS[0])
            mock_adapter.get_workflows = AsyncMock(return_value=MOCK_N8N_WORKFLOWS)
            mock_adapter.update_workflow = AsyncMock()
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            # Step 1: Execute restore
            restore_response = client.post(
                "/api/v1/restore/env-1/execute",
                json={"include_workflows": True, "create_snapshots": True},
                headers=auth_headers,
            )
            assert restore_response.status_code == 200

            # Step 2: Rollback to previous version
            rollback_response = client.post(
                "/api/v1/restore/rollback",
                json={"snapshot_id": "snap-1"},
                headers=auth_headers,
            )
            assert rollback_response.status_code == 200
            assert rollback_response.json()["success"] is True
