"""
Test rollback restores correct workflow state.

This test verifies that when a rollback is triggered using a PRE_PROMOTION snapshot,
the workflow is restored to its correct pre-promotion state in the target environment.

Test Coverage:
- Rollback restores workflow to exact state captured in PRE_PROMOTION snapshot
- Workflow content matches snapshot data after rollback
- Multiple workflows can be rolled back simultaneously
- Workflow active state is preserved during rollback
- Rollback works with different workflow structures (nodes, connections, settings)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from fastapi.testclient import TestClient


# Mock data
MOCK_TENANT_ID = "00000000-0000-0000-0000-000000000000"

MOCK_ENVIRONMENT = {
    "id": "env-prod",
    "tenant_id": MOCK_TENANT_ID,
    "name": "Production",
    "n8n_type": "production",
    "n8n_base_url": "https://prod.n8n.example.com",
    "n8n_api_key": "test_api_key",
    "git_repo_url": "https://github.com/test-org/n8n-workflows",
    "git_branch": "main",
    "git_pat": "ghp_test_token",
    "environment_class": "production",
    "policy_flags": {"allow_rollback_in_prod": True},
}

# Original workflow state (before promotion)
ORIGINAL_WORKFLOW_STATE = {
    "id": "wf-123",
    "name": "Customer Notification Workflow",
    "nodes": [
        {
            "id": "node-1",
            "type": "n8n-nodes-base.webhook",
            "name": "Webhook",
            "parameters": {"path": "customer-notify"}
        },
        {
            "id": "node-2",
            "type": "n8n-nodes-base.sendEmail",
            "name": "Send Email",
            "parameters": {"subject": "Welcome"}
        }
    ],
    "connections": {
        "Webhook": {
            "main": [[{"node": "Send Email", "type": "main", "index": 0}]]
        }
    },
    "settings": {"executionOrder": "v1"},
    "active": True
}

# Modified workflow state (after promotion - changed state)
MODIFIED_WORKFLOW_STATE = {
    "id": "wf-123",
    "name": "Customer Notification Workflow - Updated",
    "nodes": [
        {
            "id": "node-1",
            "type": "n8n-nodes-base.webhook",
            "name": "Webhook",
            "parameters": {"path": "customer-notify"}
        },
        {
            "id": "node-2",
            "type": "n8n-nodes-base.sendEmail",
            "name": "Send Email",
            "parameters": {"subject": "Welcome New Customer"}
        },
        {
            "id": "node-3",
            "type": "n8n-nodes-base.slack",
            "name": "Notify Slack",
            "parameters": {"channel": "#notifications"}
        }
    ],
    "connections": {
        "Webhook": {
            "main": [
                [{"node": "Send Email", "type": "main", "index": 0}],
                [{"node": "Notify Slack", "type": "main", "index": 0}]
            ]
        }
    },
    "settings": {"executionOrder": "v1"},
    "active": True
}

# PRE_PROMOTION snapshot capturing original state
MOCK_PRE_PROMOTION_SNAPSHOT = {
    "id": "snap-pre-promo-123",
    "tenant_id": MOCK_TENANT_ID,
    "environment_id": "env-prod",
    "git_commit_sha": "abc123def456",
    "type": "pre_promotion",
    "created_by_user_id": "user-1",
    "related_deployment_id": "deploy-1",
    "created_at": "2024-01-10T10:00:00Z",
    "metadata_json": {
        "promotion_id": "promo-123",
        "reason": "Pre-promotion snapshot for promotion promo-123",
        "workflows_count": 1,
        "workflows": [
            {
                "workflow_id": "wf-123",
                "workflow_name": "Customer Notification Workflow",
                "active": True
            }
        ]
    }
}

# GitHub workflows at the PRE_PROMOTION snapshot commit
GITHUB_WORKFLOWS_AT_SNAPSHOT = {
    "wf-123": ORIGINAL_WORKFLOW_STATE
}

# Second workflow for multi-workflow rollback test
ORIGINAL_WORKFLOW_STATE_2 = {
    "id": "wf-456",
    "name": "Data Sync Workflow",
    "nodes": [
        {
            "id": "node-1",
            "type": "n8n-nodes-base.schedule",
            "name": "Schedule",
            "parameters": {"interval": 3600}
        },
        {
            "id": "node-2",
            "type": "n8n-nodes-base.httpRequest",
            "name": "Fetch Data"
        }
    ],
    "connections": {
        "Schedule": {
            "main": [[{"node": "Fetch Data", "type": "main", "index": 0}]]
        }
    },
    "active": False
}

MODIFIED_WORKFLOW_STATE_2 = {
    "id": "wf-456",
    "name": "Data Sync Workflow - Enhanced",
    "nodes": [
        {
            "id": "node-1",
            "type": "n8n-nodes-base.schedule",
            "name": "Schedule",
            "parameters": {"interval": 1800}
        },
        {
            "id": "node-2",
            "type": "n8n-nodes-base.httpRequest",
            "name": "Fetch Data"
        },
        {
            "id": "node-3",
            "type": "n8n-nodes-base.postgres",
            "name": "Save to DB"
        }
    ],
    "connections": {
        "Schedule": {
            "main": [[{"node": "Fetch Data", "type": "main", "index": 0}]]
        },
        "Fetch Data": {
            "main": [[{"node": "Save to DB", "type": "main", "index": 0}]]
        }
    },
    "active": True
}

GITHUB_WORKFLOWS_AT_SNAPSHOT_MULTI = {
    "wf-123": ORIGINAL_WORKFLOW_STATE,
    "wf-456": ORIGINAL_WORKFLOW_STATE_2
}

MOCK_PRE_PROMOTION_SNAPSHOT_MULTI = {
    "id": "snap-pre-promo-456",
    "tenant_id": MOCK_TENANT_ID,
    "environment_id": "env-prod",
    "git_commit_sha": "xyz789abc123",
    "type": "pre_promotion",
    "created_by_user_id": "user-1",
    "related_deployment_id": "deploy-2",
    "created_at": "2024-01-11T10:00:00Z",
    "metadata_json": {
        "promotion_id": "promo-456",
        "reason": "Pre-promotion snapshot for promotion promo-456",
        "workflows_count": 2,
        "workflows": [
            {
                "workflow_id": "wf-123",
                "workflow_name": "Customer Notification Workflow",
                "active": True
            },
            {
                "workflow_id": "wf-456",
                "workflow_name": "Data Sync Workflow",
                "active": False
            }
        ]
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


class TestRollbackRestoresCorrectWorkflowState:
    """Tests verifying rollback restores workflows to correct state."""

    @pytest.mark.api
    def test_rollback_restores_single_workflow_to_snapshot_state(self, client: TestClient, auth_headers):
        """
        Test that rollback restores a single workflow to its exact state captured in PRE_PROMOTION snapshot.

        Scenario:
        1. Workflow was in state A (original)
        2. PRE_PROMOTION snapshot captured state A
        3. Promotion changed workflow to state B (modified)
        4. Rollback using snapshot should restore to state A

        Verification:
        - Workflow content matches snapshot data
        - update_workflow called with correct workflow data
        - Active state is preserved from snapshot
        """
        with patch("app.api.endpoints.snapshots.db_service") as mock_db, \
             patch("app.api.endpoints.snapshots.GitHubService") as MockGitHubService, \
             patch("app.api.endpoints.snapshots.ProviderRegistry") as mock_registry:

            # Mock the db_service.client chain for snapshot retrieval
            mock_snapshot_result = MagicMock()
            mock_snapshot_result.data = MOCK_PRE_PROMOTION_SNAPSHOT
            mock_db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_snapshot_result
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENT)

            # Mock GitHub service to return workflows at snapshot commit
            mock_github = MagicMock()
            mock_github.get_all_workflows_from_github = AsyncMock(return_value=GITHUB_WORKFLOWS_AT_SNAPSHOT)
            MockGitHubService.return_value = mock_github

            # Mock adapter - workflow currently in modified state
            mock_adapter = MagicMock()
            mock_adapter.get_workflow = AsyncMock(return_value=MODIFIED_WORKFLOW_STATE)
            mock_adapter.update_workflow = AsyncMock()
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            # Execute rollback
            response = client.post(
                f"/api/v1/snapshots/{MOCK_PRE_PROMOTION_SNAPSHOT['id']}/restore",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["restored"] == 1
            assert data["failed"] == 0

            # Verify update_workflow was called with original state
            mock_adapter.update_workflow.assert_called_once()
            call_args = mock_adapter.update_workflow.call_args
            restored_workflow_id = call_args[0][0]
            restored_workflow_data = call_args[0][1]

            assert restored_workflow_id == "wf-123"
            assert restored_workflow_data["name"] == ORIGINAL_WORKFLOW_STATE["name"]
            assert len(restored_workflow_data["nodes"]) == 2  # Original had 2 nodes
            assert restored_workflow_data["active"] is True

            # Verify node structure matches original
            assert restored_workflow_data["nodes"][0]["type"] == "n8n-nodes-base.webhook"
            assert restored_workflow_data["nodes"][1]["type"] == "n8n-nodes-base.sendEmail"

    @pytest.mark.api
    def test_rollback_restores_multiple_workflows(self, client: TestClient, auth_headers):
        """
        Test that rollback can restore multiple workflows simultaneously to their snapshot states.

        Scenario:
        - PRE_PROMOTION snapshot contains 2 workflows
        - Both workflows have been modified after promotion
        - Rollback should restore both to their original states

        Verification:
        - All workflows from snapshot are restored
        - Each workflow matches its state in the snapshot
        """
        with patch("app.api.endpoints.snapshots.db_service") as mock_db, \
             patch("app.api.endpoints.snapshots.GitHubService") as MockGitHubService, \
             patch("app.api.endpoints.snapshots.ProviderRegistry") as mock_registry:

            # Mock the db_service.client chain for snapshot retrieval
            mock_snapshot_result = MagicMock()
            mock_snapshot_result.data = MOCK_PRE_PROMOTION_SNAPSHOT_MULTI
            mock_db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_snapshot_result
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENT)

            # Mock GitHub with both workflows at snapshot state
            mock_github = MagicMock()
            mock_github.get_all_workflows_from_github = AsyncMock(
                return_value=GITHUB_WORKFLOWS_AT_SNAPSHOT_MULTI
            )
            MockGitHubService.return_value = mock_github

            # Mock adapter
            mock_adapter = MagicMock()
            mock_adapter.update_workflow = AsyncMock()
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            # Execute rollback
            response = client.post(
                f"/api/v1/snapshots/{MOCK_PRE_PROMOTION_SNAPSHOT_MULTI['id']}/restore",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["restored"] == 2
            assert data["failed"] == 0

            # Verify both workflows were updated
            assert mock_adapter.update_workflow.call_count == 2

            # Check that both workflow IDs were restored
            restored_ids = [call[0][0] for call in mock_adapter.update_workflow.call_args_list]
            assert "wf-123" in restored_ids
            assert "wf-456" in restored_ids

    @pytest.mark.api
    def test_rollback_preserves_workflow_active_state_from_snapshot(self, client: TestClient, auth_headers):
        """
        Test that rollback preserves the active/inactive state captured in the snapshot.

        Scenario:
        - Workflow was active=True in snapshot
        - After promotion, workflow is still active
        - Rollback should maintain active=True state

        Verification:
        - Restored workflow has active state matching snapshot metadata
        """
        with patch("app.api.endpoints.snapshots.db_service") as mock_db, \
             patch("app.api.endpoints.snapshots.GitHubService") as MockGitHubService, \
             patch("app.api.endpoints.snapshots.ProviderRegistry") as mock_registry:

            # Mock the db_service.client chain for snapshot retrieval
            mock_snapshot_result = MagicMock()
            mock_snapshot_result.data = MOCK_PRE_PROMOTION_SNAPSHOT
            mock_db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_snapshot_result
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENT)

            mock_github = MagicMock()
            mock_github.get_all_workflows_from_github = AsyncMock(return_value=GITHUB_WORKFLOWS_AT_SNAPSHOT)
            MockGitHubService.return_value = mock_github

            mock_adapter = MagicMock()
            mock_adapter.update_workflow = AsyncMock()
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            response = client.post(
                f"/api/v1/snapshots/{MOCK_PRE_PROMOTION_SNAPSHOT['id']}/restore",
                headers=auth_headers
            )

            assert response.status_code == 200

            # Verify active state from snapshot is preserved
            call_args = mock_adapter.update_workflow.call_args
            restored_workflow_data = call_args[0][1]

            # Check against snapshot metadata
            snapshot_workflow_metadata = MOCK_PRE_PROMOTION_SNAPSHOT["metadata_json"]["workflows"][0]
            assert restored_workflow_data["active"] == snapshot_workflow_metadata["active"]

    @pytest.mark.api
    def test_rollback_restores_workflow_structure_correctly(self, client: TestClient, auth_headers):
        """
        Test that rollback restores complex workflow structures (nodes, connections, settings).

        Scenario:
        - Original workflow has specific nodes, connections, and settings
        - Modified workflow has additional nodes and changed connections
        - Rollback should restore exact original structure

        Verification:
        - Node count matches original
        - Node types match original
        - Connections match original
        - Settings match original
        """
        with patch("app.api.endpoints.snapshots.db_service") as mock_db, \
             patch("app.api.endpoints.snapshots.GitHubService") as MockGitHubService, \
             patch("app.api.endpoints.snapshots.ProviderRegistry") as mock_registry:

            # Mock the db_service.client chain for snapshot retrieval
            mock_snapshot_result = MagicMock()
            mock_snapshot_result.data = MOCK_PRE_PROMOTION_SNAPSHOT
            mock_db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_snapshot_result
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENT)

            mock_github = MagicMock()
            mock_github.get_all_workflows_from_github = AsyncMock(return_value=GITHUB_WORKFLOWS_AT_SNAPSHOT)
            MockGitHubService.return_value = mock_github

            mock_adapter = MagicMock()
            mock_adapter.update_workflow = AsyncMock()
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            response = client.post(
                f"/api/v1/snapshots/{MOCK_PRE_PROMOTION_SNAPSHOT['id']}/restore",
                headers=auth_headers
            )

            assert response.status_code == 200

            # Extract restored workflow data
            call_args = mock_adapter.update_workflow.call_args
            restored_workflow = call_args[0][1]

            # Verify nodes structure
            assert len(restored_workflow["nodes"]) == len(ORIGINAL_WORKFLOW_STATE["nodes"])
            assert restored_workflow["nodes"][0]["type"] == ORIGINAL_WORKFLOW_STATE["nodes"][0]["type"]
            assert restored_workflow["nodes"][1]["type"] == ORIGINAL_WORKFLOW_STATE["nodes"][1]["type"]

            # Verify connections structure
            assert "Webhook" in restored_workflow["connections"]
            assert len(restored_workflow["connections"]["Webhook"]["main"]) == 1

            # Verify settings
            assert restored_workflow["settings"] == ORIGINAL_WORKFLOW_STATE["settings"]

    @pytest.mark.api
    def test_rollback_uses_correct_git_commit_sha_from_snapshot(self, client: TestClient, auth_headers):
        """
        Test that rollback fetches workflows from the exact git commit SHA stored in the snapshot.

        Scenario:
        - PRE_PROMOTION snapshot has specific git_commit_sha
        - Rollback should fetch workflows from that specific commit

        Verification:
        - get_all_workflows_from_github called with correct commit_sha parameter
        """
        with patch("app.api.endpoints.snapshots.db_service") as mock_db, \
             patch("app.api.endpoints.snapshots.GitHubService") as MockGitHubService, \
             patch("app.api.endpoints.snapshots.ProviderRegistry") as mock_registry:

            # Mock the db_service.client chain for snapshot retrieval
            mock_snapshot_result = MagicMock()
            mock_snapshot_result.data = MOCK_PRE_PROMOTION_SNAPSHOT
            mock_db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_snapshot_result
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENT)

            mock_github = MagicMock()
            mock_github.get_all_workflows_from_github = AsyncMock(return_value=GITHUB_WORKFLOWS_AT_SNAPSHOT)
            MockGitHubService.return_value = mock_github

            mock_adapter = MagicMock()
            mock_adapter.update_workflow = AsyncMock()
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            response = client.post(
                f"/api/v1/snapshots/{MOCK_PRE_PROMOTION_SNAPSHOT['id']}/restore",
                headers=auth_headers
            )

            assert response.status_code == 200

            # Verify GitHub was called with the correct commit SHA
            mock_github.get_all_workflows_from_github.assert_called_once()
            # Check call arguments - should include the commit_sha
            call_args = mock_github.get_all_workflows_from_github.call_args
            # The commit_sha is passed as a keyword argument
            assert call_args.kwargs.get("commit_sha") == MOCK_PRE_PROMOTION_SNAPSHOT["git_commit_sha"]

    @pytest.mark.api
    def test_rollback_with_inactive_workflow_in_snapshot(self, client: TestClient, auth_headers):
        """
        Test rollback correctly handles workflows that were inactive in the snapshot.

        Scenario:
        - Workflow was inactive (active=False) when snapshot was created
        - After promotion, workflow might be active
        - Rollback should restore it to inactive state

        Verification:
        - Restored workflow has active=False as captured in snapshot
        """
        # Modify snapshot to have inactive workflow
        snapshot_with_inactive = {
            **MOCK_PRE_PROMOTION_SNAPSHOT,
            "metadata_json": {
                **MOCK_PRE_PROMOTION_SNAPSHOT["metadata_json"],
                "workflows": [
                    {
                        "workflow_id": "wf-456",
                        "workflow_name": "Data Sync Workflow",
                        "active": False  # Explicitly inactive
                    }
                ]
            }
        }

        # Workflow state in snapshot is inactive
        workflow_state_inactive = {
            **ORIGINAL_WORKFLOW_STATE_2,
            "active": False
        }

        github_workflows = {"wf-456": workflow_state_inactive}

        with patch("app.api.endpoints.snapshots.db_service") as mock_db, \
             patch("app.api.endpoints.snapshots.GitHubService") as MockGitHubService, \
             patch("app.api.endpoints.snapshots.ProviderRegistry") as mock_registry:

            # Mock the db_service.client chain for snapshot retrieval
            mock_snapshot_result = MagicMock()
            mock_snapshot_result.data = snapshot_with_inactive
            mock_db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_snapshot_result
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENT)

            mock_github = MagicMock()
            mock_github.get_all_workflows_from_github = AsyncMock(return_value=github_workflows)
            MockGitHubService.return_value = mock_github

            mock_adapter = MagicMock()
            mock_adapter.update_workflow = AsyncMock()
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            response = client.post(
                f"/api/v1/snapshots/{snapshot_with_inactive['id']}/restore",
                headers=auth_headers
            )

            assert response.status_code == 200

            # Verify workflow was restored with active=False
            call_args = mock_adapter.update_workflow.call_args
            restored_workflow = call_args[0][1]
            assert restored_workflow["active"] is False

    @pytest.mark.api
    def test_rollback_handles_partial_failure_gracefully(self, client: TestClient, auth_headers):
        """
        Test that rollback handles partial failures (some workflows restore, others fail).

        Scenario:
        - Snapshot contains 2 workflows
        - First workflow restores successfully
        - Second workflow fails to restore

        Verification:
        - Response indicates partial success
        - Successfully restored count is 1
        - Failed count is 1
        - Errors list contains failure details
        """
        with patch("app.api.endpoints.snapshots.db_service") as mock_db, \
             patch("app.api.endpoints.snapshots.GitHubService") as MockGitHubService, \
             patch("app.api.endpoints.snapshots.ProviderRegistry") as mock_registry:

            # Mock the db_service.client chain for snapshot retrieval
            mock_snapshot_result = MagicMock()
            mock_snapshot_result.data = MOCK_PRE_PROMOTION_SNAPSHOT_MULTI
            mock_db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_snapshot_result
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENT)

            mock_github = MagicMock()
            mock_github.get_all_workflows_from_github = AsyncMock(
                return_value=GITHUB_WORKFLOWS_AT_SNAPSHOT_MULTI
            )
            MockGitHubService.return_value = mock_github

            # Mock adapter to fail on second workflow
            mock_adapter = MagicMock()
            call_count = 0

            async def update_workflow_with_failure(workflow_id, workflow_data):
                nonlocal call_count
                call_count += 1
                if call_count == 2:  # Fail on second call
                    raise Exception("N8N API error: Connection timeout")

            mock_adapter.update_workflow = AsyncMock(side_effect=update_workflow_with_failure)
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            response = client.post(
                f"/api/v1/snapshots/{MOCK_PRE_PROMOTION_SNAPSHOT_MULTI['id']}/restore",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()

            # Verify partial success
            assert data["success"] is False  # Overall operation failed
            assert data["restored"] == 1
            assert data["failed"] == 1
            assert len(data["errors"]) >= 1
            assert "Connection timeout" in str(data["errors"])

    @pytest.mark.api
    def test_rollback_success_message_contains_workflow_count(self, client: TestClient, auth_headers):
        """
        Test that rollback success response includes helpful information.

        Verification:
        - Message indicates number of workflows restored
        - Response contains all expected fields
        """
        with patch("app.api.endpoints.snapshots.db_service") as mock_db, \
             patch("app.api.endpoints.snapshots.GitHubService") as MockGitHubService, \
             patch("app.api.endpoints.snapshots.ProviderRegistry") as mock_registry:

            # Mock the db_service.client chain for snapshot retrieval
            mock_snapshot_result = MagicMock()
            mock_snapshot_result.data = MOCK_PRE_PROMOTION_SNAPSHOT_MULTI
            mock_db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_snapshot_result
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENT)

            mock_github = MagicMock()
            mock_github.get_all_workflows_from_github = AsyncMock(
                return_value=GITHUB_WORKFLOWS_AT_SNAPSHOT_MULTI
            )
            MockGitHubService.return_value = mock_github

            mock_adapter = MagicMock()
            mock_adapter.update_workflow = AsyncMock()
            mock_registry.get_adapter_for_environment.return_value = mock_adapter

            response = client.post(
                f"/api/v1/snapshots/{MOCK_PRE_PROMOTION_SNAPSHOT_MULTI['id']}/restore",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "success" in data
            assert "restored" in data
            assert "failed" in data
            assert "errors" in data
            assert "message" in data

            # Verify message contains count
            assert "2" in data["message"] or data["restored"] == 2
            assert "workflows" in data["message"].lower()
