"""
Unit tests for the Drift Detection Service.
Tests environment-level drift detection against GitHub source of truth.
"""
import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.drift_detection_service import (
    DriftDetectionService,
    drift_detection_service,
    DriftStatus,
    WorkflowDriftInfo,
    EnvironmentDriftSummary,
)


# Test fixtures
MOCK_TENANT_ID = "00000000-0000-0000-0000-000000000001"
MOCK_ENVIRONMENT_ID = "00000000-0000-0000-0000-000000000002"


@pytest.fixture
def mock_environment():
    """Create a mock environment with GitHub configured."""
    return {
        "id": MOCK_ENVIRONMENT_ID,
        "tenant_id": MOCK_TENANT_ID,
        "n8n_name": "Development",
        "n8n_type": "development",
        "n8n_base_url": "https://dev.n8n.example.com",
        "n8n_api_key": "test-api-key",
        "is_active": True,
        "workflow_count": 5,
        "git_repo_url": "https://github.com/test/repo",
        "git_pat": "ghp_test_token",
        "git_branch": "main",
        "drift_status": DriftStatus.UNKNOWN,
    }


@pytest.fixture
def mock_environment_no_git():
    """Create a mock environment without GitHub configured."""
    return {
        "id": MOCK_ENVIRONMENT_ID,
        "tenant_id": MOCK_TENANT_ID,
        "n8n_name": "Development",
        "n8n_type": "development",
        "n8n_base_url": "https://dev.n8n.example.com",
        "is_active": True,
        "workflow_count": 5,
        "git_repo_url": None,
        "git_pat": None,
    }


@pytest.fixture
def mock_runtime_workflows():
    """Create mock workflows from the n8n runtime."""
    return [
        {
            "id": "wf-1",
            "name": "Workflow One",
            "active": True,
            "nodes": [{"id": "node-1", "type": "start"}],
            "connections": {},
        },
        {
            "id": "wf-2",
            "name": "Workflow Two",
            "active": False,
            "nodes": [{"id": "node-2", "type": "start"}],
            "connections": {},
        },
        {
            "id": "wf-3",
            "name": "New Workflow",
            "active": True,
            "nodes": [],
            "connections": {},
        },
    ]


@pytest.fixture
def mock_git_workflows():
    """Create mock workflows from GitHub."""
    return {
        "wf-1": {
            "id": "wf-1",
            "name": "Workflow One",
            "active": True,
            "nodes": [{"id": "node-1", "type": "start"}],
            "connections": {},
        },
        "wf-2": {
            "id": "wf-2",
            "name": "Workflow Two",
            "active": False,
            "nodes": [
                {"id": "node-2", "type": "start"},
                {"id": "node-3", "type": "end"},  # Modified
            ],
            "connections": {},
        },
    }


class TestDriftDetectionServiceBasic:
    """Basic tests for drift detection service."""

    def test_drift_status_constants(self):
        """Test that drift status constants are defined."""
        assert DriftStatus.UNKNOWN == "UNKNOWN"
        assert DriftStatus.IN_SYNC == "IN_SYNC"
        assert DriftStatus.DRIFT_DETECTED == "DRIFT_DETECTED"
        assert DriftStatus.NEW == "NEW"
        assert DriftStatus.ERROR == "ERROR"

    def test_environment_drift_summary_to_dict(self):
        """Test EnvironmentDriftSummary.to_dict method."""
        summary = EnvironmentDriftSummary(
            total_workflows=10,
            in_sync=7,
            with_drift=2,
            not_in_git=1,
            git_configured=True,
            last_detected_at="2024-01-01T00:00:00",
            affected_workflows=[],
        )

        result = summary.to_dict()

        assert result["totalWorkflows"] == 10
        assert result["inSync"] == 7
        assert result["withDrift"] == 2
        assert result["notInGit"] == 1
        assert result["gitConfigured"] is True
        assert result["error"] is None


class TestDetectDrift:
    """Tests for the detect_drift method."""

    @pytest.mark.asyncio
    async def test_detect_drift_environment_not_found(self):
        """Test drift detection when environment doesn't exist."""
        with patch("app.services.drift_detection_service.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=None)

            service = DriftDetectionService()
            result = await service.detect_drift(MOCK_TENANT_ID, MOCK_ENVIRONMENT_ID)

            assert result.error == "Environment not found"
            assert result.git_configured is False

    @pytest.mark.asyncio
    async def test_detect_drift_no_git_configured(self, mock_environment_no_git):
        """Test drift detection when GitHub is not configured.

        P1 DELTA FIX: With workflows present (workflow_count > 0), this is UNMANAGED state
        (not an error). When no workflows exist, it returns UNKNOWN with error message.
        """
        with patch("app.services.drift_detection_service.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=mock_environment_no_git)
            mock_db.update_environment = AsyncMock()

            service = DriftDetectionService()
            result = await service.detect_drift(MOCK_TENANT_ID, MOCK_ENVIRONMENT_ID)

            # mock_environment_no_git has workflow_count=5, so UNMANAGED state (no error)
            assert result.git_configured is False
            assert result.error is None  # UNMANAGED is not an error state

    @pytest.mark.asyncio
    async def test_detect_drift_no_git_no_workflows(self):
        """Test drift detection when GitHub is not configured AND no workflows exist.

        This is the EMPTY state - returns UNKNOWN with error message.
        """
        empty_env = {
            "id": MOCK_ENVIRONMENT_ID,
            "tenant_id": MOCK_TENANT_ID,
            "n8n_name": "Empty Dev",
            "n8n_base_url": "https://dev.n8n.example.com",
            "is_active": True,
            "workflow_count": 0,  # No workflows
            "git_repo_url": None,
            "git_pat": None,
        }
        with patch("app.services.drift_detection_service.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=empty_env)
            mock_db.update_environment = AsyncMock()

            service = DriftDetectionService()
            result = await service.detect_drift(MOCK_TENANT_ID, MOCK_ENVIRONMENT_ID)

            assert result.git_configured is False
            assert "not configured" in result.error.lower()

    @pytest.mark.asyncio
    async def test_detect_drift_new_environment_not_onboarded(self, mock_environment):
        """Test drift detection returns NEW status when environment is not onboarded."""
        with patch("app.services.drift_detection_service.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=mock_environment)
            mock_db.update_environment = AsyncMock()

            # Mock is_env_onboarded to return False (no baseline exists)
            with patch("app.services.git_snapshot_service.git_snapshot_service") as mock_snapshot:
                mock_snapshot.is_env_onboarded = AsyncMock(return_value=(False, "new"))

                service = DriftDetectionService()
                result = await service.detect_drift(MOCK_TENANT_ID, MOCK_ENVIRONMENT_ID)

                # Should short-circuit with NEW status
                assert result.git_configured is True
                assert result.error is None
                assert result.affected_workflows == []
                assert result.in_sync == 0
                assert result.with_drift == 0
                assert result.not_in_git == 0

                # Should update status to NEW
                mock_db.update_environment.assert_called_once()
                call_args = mock_db.update_environment.call_args
                assert call_args[0][2]["drift_status"] == DriftStatus.NEW

    @pytest.mark.asyncio
    async def test_detect_drift_all_in_sync(self, mock_environment):
        """Test drift detection when all workflows are in sync."""
        synced_workflows = [
            {
                "id": "wf-1",
                "name": "Workflow One",
                "active": True,
                "nodes": [{"id": "node-1", "type": "start"}],
                "connections": {},
            }
        ]

        git_workflows = {
            "wf-1": {
                "id": "wf-1",
                "name": "Workflow One",
                "active": True,
                "nodes": [{"id": "node-1", "type": "start"}],
                "connections": {},
            }
        }

        with patch("app.services.drift_detection_service.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=mock_environment)
            mock_db.update_environment = AsyncMock()

            # Mock is_env_onboarded to return True (environment has baseline)
            with patch("app.services.git_snapshot_service.git_snapshot_service") as mock_snapshot:
                mock_snapshot.is_env_onboarded = AsyncMock(return_value=(True, "onboarded"))

                with patch("app.services.drift_detection_service.ProviderRegistry") as mock_registry:
                    mock_adapter = MagicMock()
                    mock_adapter.get_workflows = AsyncMock(return_value=synced_workflows)
                    mock_registry.get_adapter_for_environment.return_value = mock_adapter

                    with patch("app.services.drift_detection_service.GitHubService") as mock_github_cls:
                        mock_github = MagicMock()
                        mock_github.is_configured.return_value = True
                        mock_github.get_all_workflows_from_github = AsyncMock(return_value=git_workflows)
                        mock_github_cls.return_value = mock_github

                        with patch("app.services.drift_detection_service.compare_workflows") as mock_compare:
                            mock_result = MagicMock()
                            mock_result.has_drift = False
                            mock_compare.return_value = mock_result

                            service = DriftDetectionService()
                            # Mock _get_linked_workflow_ids to return None (no mapping data, backward compat)
                            service._get_linked_workflow_ids = AsyncMock(return_value=None)
                            result = await service.detect_drift(MOCK_TENANT_ID, MOCK_ENVIRONMENT_ID)

                            assert result.in_sync == 1
                            assert result.with_drift == 0
                            assert result.not_in_git == 0

    @pytest.mark.asyncio
    async def test_detect_drift_with_changes(
        self, mock_environment, mock_runtime_workflows, mock_git_workflows
    ):
        """Test drift detection when workflows have drifted."""
        with patch("app.services.drift_detection_service.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=mock_environment)
            mock_db.update_environment = AsyncMock()

            # Mock is_env_onboarded to return True (environment has baseline)
            with patch("app.services.git_snapshot_service.git_snapshot_service") as mock_snapshot:
                mock_snapshot.is_env_onboarded = AsyncMock(return_value=(True, "onboarded"))

                with patch("app.services.drift_detection_service.ProviderRegistry") as mock_registry:
                    mock_adapter = MagicMock()
                    mock_adapter.get_workflows = AsyncMock(return_value=mock_runtime_workflows)
                    mock_registry.get_adapter_for_environment.return_value = mock_adapter

                    with patch("app.services.drift_detection_service.GitHubService") as mock_github_cls:
                        mock_github = MagicMock()
                        mock_github.is_configured.return_value = True
                        mock_github.get_all_workflows_from_github = AsyncMock(return_value=mock_git_workflows)
                        mock_github_cls.return_value = mock_github

                        with patch("app.services.drift_detection_service.compare_workflows") as mock_compare:
                            # First workflow: in sync
                            # Second workflow: has drift
                            def compare_side_effect(git_workflow=None, runtime_workflow=None):
                                result = MagicMock()
                                if runtime_workflow and runtime_workflow.get("name") == "Workflow Two":
                                    result.has_drift = True
                                    result.summary = MagicMock(
                                        nodes_added=1,
                                        nodes_removed=0,
                                        nodes_modified=0,
                                        connections_changed=False,
                                        settings_changed=False,
                                    )
                                    result.differences = [{"type": "node_added"}]
                                else:
                                    result.has_drift = False
                                return result

                            mock_compare.side_effect = compare_side_effect

                            service = DriftDetectionService()
                            # Mock _get_linked_workflow_ids to return None (no mapping data, backward compat)
                            service._get_linked_workflow_ids = AsyncMock(return_value=None)
                            result = await service.detect_drift(MOCK_TENANT_ID, MOCK_ENVIRONMENT_ID)

                            assert result.total_workflows == 3
                            assert result.in_sync == 1
                            assert result.with_drift == 1
                            assert result.not_in_git == 1  # "New Workflow" not in git

    @pytest.mark.asyncio
    async def test_detect_drift_provider_error(self, mock_environment):
        """Test drift detection when provider fails."""
        with patch("app.services.drift_detection_service.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=mock_environment)
            mock_db.update_environment = AsyncMock()

            # Mock is_env_onboarded to return True (environment has baseline)
            with patch("app.services.git_snapshot_service.git_snapshot_service") as mock_snapshot:
                mock_snapshot.is_env_onboarded = AsyncMock(return_value=(True, "onboarded"))

                with patch("app.services.drift_detection_service.ProviderRegistry") as mock_registry:
                    mock_adapter = MagicMock()
                    mock_adapter.get_workflows = AsyncMock(side_effect=Exception("Connection failed"))
                    mock_registry.get_adapter_for_environment.return_value = mock_adapter

                    service = DriftDetectionService()
                    result = await service.detect_drift(MOCK_TENANT_ID, MOCK_ENVIRONMENT_ID)

                    assert "Failed to fetch workflows from provider" in result.error

    @pytest.mark.asyncio
    async def test_detect_drift_github_error(self, mock_environment, mock_runtime_workflows):
        """Test drift detection when GitHub fails."""
        with patch("app.services.drift_detection_service.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=mock_environment)
            mock_db.update_environment = AsyncMock()

            # Mock is_env_onboarded to return True (environment has baseline)
            with patch("app.services.git_snapshot_service.git_snapshot_service") as mock_snapshot:
                mock_snapshot.is_env_onboarded = AsyncMock(return_value=(True, "onboarded"))

                with patch("app.services.drift_detection_service.ProviderRegistry") as mock_registry:
                    mock_adapter = MagicMock()
                    mock_adapter.get_workflows = AsyncMock(return_value=mock_runtime_workflows)
                    mock_registry.get_adapter_for_environment.return_value = mock_adapter

                    with patch("app.services.drift_detection_service.GitHubService") as mock_github_cls:
                        mock_github = MagicMock()
                        mock_github.is_configured.return_value = True
                        mock_github.get_all_workflows_from_github = AsyncMock(
                            side_effect=Exception("GitHub API error")
                        )
                        mock_github_cls.return_value = mock_github

                        service = DriftDetectionService()
                        result = await service.detect_drift(MOCK_TENANT_ID, MOCK_ENVIRONMENT_ID)

                        assert "Failed to fetch workflows from GitHub" in result.error


class TestGetCachedDriftStatus:
    """Tests for get_cached_drift_status method."""

    @pytest.mark.asyncio
    async def test_get_cached_status_success(self, mock_environment):
        """Test getting cached drift status."""
        env_with_status = {
            **mock_environment,
            "drift_status": DriftStatus.IN_SYNC,
            "last_drift_detected_at": "2024-01-01T00:00:00",
            "active_drift_incident_id": None,
        }

        with patch("app.services.drift_detection_service.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=env_with_status)

            service = DriftDetectionService()
            result = await service.get_cached_drift_status(MOCK_TENANT_ID, MOCK_ENVIRONMENT_ID)

            assert result["driftStatus"] == DriftStatus.IN_SYNC
            assert result["lastDriftDetectedAt"] == "2024-01-01T00:00:00"

    @pytest.mark.asyncio
    async def test_get_cached_status_not_found(self):
        """Test getting cached status for non-existent environment."""
        with patch("app.services.drift_detection_service.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=None)

            service = DriftDetectionService()
            result = await service.get_cached_drift_status(MOCK_TENANT_ID, "non-existent")

            assert result["driftStatus"] == DriftStatus.UNKNOWN
            assert result["lastDriftDetectedAt"] is None


class TestUpdateEnvironmentDriftStatus:
    """Tests for _update_environment_drift_status method."""

    @pytest.mark.asyncio
    async def test_update_status_success(self, mock_environment):
        """Test updating environment drift status."""
        summary = EnvironmentDriftSummary(
            total_workflows=5,
            in_sync=4,
            with_drift=1,
            not_in_git=0,
            git_configured=True,
            last_detected_at="2024-01-01T00:00:00",
            affected_workflows=[],
        )

        with patch("app.services.drift_detection_service.db_service") as mock_db:
            mock_db.update_environment = AsyncMock()

            service = DriftDetectionService()
            await service._update_environment_drift_status(
                MOCK_TENANT_ID,
                MOCK_ENVIRONMENT_ID,
                DriftStatus.DRIFT_DETECTED,
                summary,
            )

            mock_db.update_environment.assert_called_once()
            call_args = mock_db.update_environment.call_args
            assert call_args[0][0] == MOCK_ENVIRONMENT_ID
            assert call_args[0][1] == MOCK_TENANT_ID
            assert call_args[0][2]["drift_status"] == DriftStatus.DRIFT_DETECTED

    @pytest.mark.asyncio
    async def test_update_status_handles_error(self):
        """Test that update errors are logged but don't raise."""
        summary = EnvironmentDriftSummary(
            total_workflows=0,
            in_sync=0,
            with_drift=0,
            not_in_git=0,
            git_configured=True,
            last_detected_at="2024-01-01T00:00:00",
            affected_workflows=[],
        )

        with patch("app.services.drift_detection_service.db_service") as mock_db:
            mock_db.update_environment = AsyncMock(side_effect=Exception("DB error"))

            service = DriftDetectionService()

            # Should not raise
            await service._update_environment_drift_status(
                MOCK_TENANT_ID,
                MOCK_ENVIRONMENT_ID,
                DriftStatus.ERROR,
                summary,
            )


class TestDetectDriftWithoutUpdate:
    """Tests for detect_drift with update_status=False."""

    @pytest.mark.asyncio
    async def test_detect_drift_no_update(self, mock_environment):
        """Test drift detection without updating the database."""
        synced_workflows = [
            {
                "id": "wf-1",
                "name": "Workflow One",
                "active": True,
                "nodes": [],
                "connections": {},
            }
        ]

        git_workflows = {
            "wf-1": {
                "name": "Workflow One",
                "active": True,
                "nodes": [],
                "connections": {},
            }
        }

        with patch("app.services.drift_detection_service.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=mock_environment)
            mock_db.update_environment = AsyncMock()

            # Mock is_env_onboarded to return True (environment has baseline)
            with patch("app.services.git_snapshot_service.git_snapshot_service") as mock_snapshot:
                mock_snapshot.is_env_onboarded = AsyncMock(return_value=(True, "onboarded"))

                with patch("app.services.drift_detection_service.ProviderRegistry") as mock_registry:
                    mock_adapter = MagicMock()
                    mock_adapter.get_workflows = AsyncMock(return_value=synced_workflows)
                    mock_registry.get_adapter_for_environment.return_value = mock_adapter

                    with patch("app.services.drift_detection_service.GitHubService") as mock_github_cls:
                        mock_github = MagicMock()
                        mock_github.is_configured.return_value = True
                        mock_github.get_all_workflows_from_github = AsyncMock(return_value=git_workflows)
                        mock_github_cls.return_value = mock_github

                        with patch("app.services.drift_detection_service.compare_workflows") as mock_compare:
                            mock_result = MagicMock()
                            mock_result.has_drift = False
                            mock_compare.return_value = mock_result

                            service = DriftDetectionService()
                            # Mock _get_linked_workflow_ids to return None (no mapping data, backward compat)
                            service._get_linked_workflow_ids = AsyncMock(return_value=None)
                            result = await service.detect_drift(
                                MOCK_TENANT_ID,
                                MOCK_ENVIRONMENT_ID,
                                update_status=False,
                            )

                            # Should not update the database
                            mock_db.update_environment.assert_not_called()
                            assert result.in_sync == 1


class TestSingletonInstance:
    """Test that drift_detection_service is a singleton."""

    def test_singleton_exists(self):
        """Test that the singleton instance exists."""
        assert drift_detection_service is not None
        assert isinstance(drift_detection_service, DriftDetectionService)
