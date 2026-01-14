"""
Tests for the Untracked Workflows Service.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from app.services.untracked_workflows_service import UntrackedWorkflowsService
from app.schemas.untracked_workflow import (
    UntrackedWorkflowsResponse,
    OnboardWorkflowsResponse,
    ScanEnvironmentsResponse,
)


# Test fixtures
MOCK_TENANT_ID = "00000000-0000-0000-0000-000000000001"
MOCK_ENV_1_ID = "env-1"
MOCK_ENV_2_ID = "env-2"
MOCK_WORKFLOW_ID = "n8n-workflow-1"


@pytest.fixture
def mock_environments():
    """Mock environments for testing."""
    return [
        {
            "id": MOCK_ENV_1_ID,
            "tenant_id": MOCK_TENANT_ID,
            "name": "Development",
            "n8n_name": "Development",
            "n8n_base_url": "https://dev.n8n.example.com",
            "n8n_api_key": "dev-api-key",
            "is_active": True,
            "environment_class": "dev",
        },
        {
            "id": MOCK_ENV_2_ID,
            "tenant_id": MOCK_TENANT_ID,
            "name": "Production",
            "n8n_name": "Production",
            "n8n_base_url": "https://prod.n8n.example.com",
            "n8n_api_key": "prod-api-key",
            "is_active": True,
            "environment_class": "production",
        },
    ]


@pytest.fixture
def mock_n8n_workflows():
    """Mock workflows from n8n API."""
    return [
        {
            "id": "n8n-wf-1",
            "name": "Test Workflow 1",
            "active": True,
            "createdAt": "2024-01-01T00:00:00.000Z",
            "updatedAt": "2024-01-15T00:00:00.000Z",
        },
        {
            "id": "n8n-wf-2",
            "name": "Test Workflow 2",
            "active": False,
            "createdAt": "2024-01-05T00:00:00.000Z",
            "updatedAt": "2024-01-10T00:00:00.000Z",
        },
    ]


@pytest.fixture
def mock_untracked_mappings():
    """Mock untracked workflow mappings (canonical_id is NULL)."""
    return [
        {
            "n8n_workflow_id": "n8n-wf-1",
            "workflow_data": {
                "name": "Test Workflow 1",
                "active": True,
                "createdAt": "2024-01-01T00:00:00.000Z",
                "updatedAt": "2024-01-15T00:00:00.000Z",
            },
            "last_env_sync_at": "2024-01-15T12:00:00.000Z",
        },
    ]


class TestGetUntrackedWorkflows:
    """Tests for get_untracked_workflows method."""

    @pytest.mark.asyncio
    async def test_get_untracked_workflows_empty(self):
        """Test getting untracked workflows when there are none."""
        with patch("app.services.untracked_workflows_service.db_service") as mock_db:
            # Mock empty environments
            mock_db.get_environments = AsyncMock(return_value=[])

            result = await UntrackedWorkflowsService.get_untracked_workflows(MOCK_TENANT_ID)

            assert isinstance(result, UntrackedWorkflowsResponse)
            assert result.total_untracked == 0
            assert result.environments == []

    @pytest.mark.asyncio
    async def test_get_untracked_workflows_with_data(self, mock_environments, mock_untracked_mappings):
        """Test getting untracked workflows when they exist."""
        with patch("app.services.untracked_workflows_service.db_service") as mock_db:
            # Mock environments
            mock_db.get_environments = AsyncMock(return_value=mock_environments)

            # Mock workflow_env_map query for untracked workflows
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq1 = MagicMock()
            mock_eq2 = MagicMock()
            mock_is = MagicMock()

            mock_is.execute = MagicMock(return_value=MagicMock(data=mock_untracked_mappings))
            mock_eq2.is_ = MagicMock(return_value=mock_is)
            mock_eq1.eq = MagicMock(return_value=mock_eq2)
            mock_select.eq = MagicMock(return_value=mock_eq1)
            mock_table.select = MagicMock(return_value=mock_select)
            mock_db.client.table = MagicMock(return_value=mock_table)

            result = await UntrackedWorkflowsService.get_untracked_workflows(MOCK_TENANT_ID)

            assert isinstance(result, UntrackedWorkflowsResponse)
            # Should have at least the first environment (dev) with untracked workflows
            assert len(result.environments) > 0


class TestScanEnvironments:
    """Tests for scan_environments method."""

    @pytest.mark.asyncio
    async def test_scan_environments_success(self, mock_environments, mock_n8n_workflows):
        """Test successfully scanning environments."""
        with patch("app.services.untracked_workflows_service.db_service") as mock_db, \
             patch("app.services.untracked_workflows_service.ProviderRegistry") as mock_registry, \
             patch("app.services.untracked_workflows_service.compute_workflow_hash") as mock_hash:

            # Mock db_service
            mock_db.get_environments = AsyncMock(return_value=mock_environments)

            # Mock existing mappings (empty - all workflows are new)
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq1 = MagicMock()
            mock_eq2 = MagicMock()
            mock_not = MagicMock()

            mock_not.execute = MagicMock(return_value=MagicMock(data=[]))
            mock_eq2.not_ = MagicMock()
            mock_eq2.not_.is_ = MagicMock(return_value=mock_not)
            mock_eq1.eq = MagicMock(return_value=mock_eq2)
            mock_select.eq = MagicMock(return_value=mock_eq1)
            mock_table.select = MagicMock(return_value=mock_select)

            # Mock upsert
            mock_upsert = MagicMock()
            mock_upsert.execute = MagicMock(return_value=MagicMock(data=[{}]))
            mock_table.upsert = MagicMock(return_value=mock_upsert)

            mock_db.client.table = MagicMock(return_value=mock_table)

            # Mock adapter
            mock_adapter = MagicMock()
            mock_adapter.get_workflows = AsyncMock(return_value=mock_n8n_workflows)
            mock_adapter.get_workflow = AsyncMock(side_effect=lambda wid: {
                "id": wid,
                "name": f"Workflow {wid}",
                "active": True,
                "nodes": [],
                "connections": {},
            })
            mock_registry.get_adapter_for_environment = MagicMock(return_value=mock_adapter)

            # Mock hash computation
            mock_hash.return_value = "abc123hash"

            result = await UntrackedWorkflowsService.scan_environments(MOCK_TENANT_ID)

            assert isinstance(result, ScanEnvironmentsResponse)
            assert result.environments_scanned == 2
            assert result.environments_failed == 0
            assert len(result.results) == 2

    @pytest.mark.asyncio
    async def test_scan_environments_partial_failure(self, mock_environments):
        """Test scanning with partial environment failures."""
        with patch("app.services.untracked_workflows_service.db_service") as mock_db, \
             patch("app.services.untracked_workflows_service.ProviderRegistry") as mock_registry:

            # Mock db_service
            mock_db.get_environments = AsyncMock(return_value=mock_environments)

            # Mock adapter that fails for one environment
            def get_adapter(env):
                mock_adapter = MagicMock()
                if env.get("id") == MOCK_ENV_1_ID:
                    mock_adapter.get_workflows = AsyncMock(side_effect=Exception("Connection failed"))
                else:
                    mock_adapter.get_workflows = AsyncMock(return_value=[])
                return mock_adapter

            mock_registry.get_adapter_for_environment = get_adapter

            # Mock table for successful environment
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq1 = MagicMock()
            mock_eq2 = MagicMock()
            mock_not = MagicMock()
            mock_not.execute = MagicMock(return_value=MagicMock(data=[]))
            mock_eq2.not_ = MagicMock()
            mock_eq2.not_.is_ = MagicMock(return_value=mock_not)
            mock_eq1.eq = MagicMock(return_value=mock_eq2)
            mock_select.eq = MagicMock(return_value=mock_eq1)
            mock_table.select = MagicMock(return_value=mock_select)
            mock_db.client.table = MagicMock(return_value=mock_table)

            result = await UntrackedWorkflowsService.scan_environments(MOCK_TENANT_ID)

            assert isinstance(result, ScanEnvironmentsResponse)
            assert result.environments_scanned == 1
            assert result.environments_failed == 1

            # Check that the failed environment has an error
            failed_results = [r for r in result.results if r.status == "failed"]
            assert len(failed_results) == 1
            assert "Connection failed" in (failed_results[0].error or "")


class TestOnboardWorkflows:
    """Tests for onboard_workflows method."""

    @pytest.mark.asyncio
    async def test_onboard_workflows_success(self):
        """Test successfully onboarding workflows."""
        with patch("app.services.untracked_workflows_service.db_service") as mock_db:
            # Mock existing mapping check (no canonical_id = untracked)
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq1 = MagicMock()
            mock_eq2 = MagicMock()
            mock_eq3 = MagicMock()
            mock_maybe_single = MagicMock()

            mock_maybe_single.execute = MagicMock(return_value=MagicMock(data={"canonical_id": None, "workflow_data": {}}))
            mock_eq3.maybe_single = MagicMock(return_value=mock_maybe_single)
            mock_eq2.eq = MagicMock(return_value=mock_eq3)
            mock_eq1.eq = MagicMock(return_value=mock_eq2)
            mock_select.eq = MagicMock(return_value=mock_eq1)
            mock_table.select = MagicMock(return_value=mock_select)
            mock_db.client.table = MagicMock(return_value=mock_table)

            # Mock create_canonical_workflow_with_mapping
            mock_db.create_canonical_workflow_with_mapping = AsyncMock(return_value={
                "canonical_id": "new-canonical-id-123",
                "tenant_id": MOCK_TENANT_ID,
                "display_name": "Test Workflow",
            })

            workflows_to_onboard = [
                {"environment_id": MOCK_ENV_1_ID, "n8n_workflow_id": "n8n-wf-1"},
            ]

            result = await UntrackedWorkflowsService.onboard_workflows(
                MOCK_TENANT_ID, workflows_to_onboard
            )

            assert isinstance(result, OnboardWorkflowsResponse)
            assert result.total_onboarded == 1
            assert result.total_skipped == 0
            assert result.total_failed == 0

    @pytest.mark.asyncio
    async def test_onboard_workflows_already_mapped(self):
        """Test onboarding workflows that are already mapped (idempotent)."""
        with patch("app.services.untracked_workflows_service.db_service") as mock_db:
            # Mock existing mapping check (has canonical_id = already mapped)
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq1 = MagicMock()
            mock_eq2 = MagicMock()
            mock_eq3 = MagicMock()
            mock_maybe_single = MagicMock()

            mock_maybe_single.execute = MagicMock(return_value=MagicMock(data={
                "canonical_id": "existing-canonical-id",
            }))
            mock_eq3.maybe_single = MagicMock(return_value=mock_maybe_single)
            mock_eq2.eq = MagicMock(return_value=mock_eq3)
            mock_eq1.eq = MagicMock(return_value=mock_eq2)
            mock_select.eq = MagicMock(return_value=mock_eq1)
            mock_table.select = MagicMock(return_value=mock_select)
            mock_db.client.table = MagicMock(return_value=mock_table)

            workflows_to_onboard = [
                {"environment_id": MOCK_ENV_1_ID, "n8n_workflow_id": "n8n-wf-1"},
            ]

            result = await UntrackedWorkflowsService.onboard_workflows(
                MOCK_TENANT_ID, workflows_to_onboard
            )

            assert isinstance(result, OnboardWorkflowsResponse)
            assert result.total_onboarded == 0
            assert result.total_skipped == 1
            assert result.total_failed == 0

            # Check that the skipped workflow has the existing canonical_id
            skipped = [r for r in result.results if r.status == "skipped"]
            assert len(skipped) == 1
            assert skipped[0].canonical_workflow_id == "existing-canonical-id"

    @pytest.mark.asyncio
    async def test_onboard_workflows_empty_list(self):
        """Test onboarding with empty workflow list."""
        result = await UntrackedWorkflowsService.onboard_workflows(MOCK_TENANT_ID, [])

        assert isinstance(result, OnboardWorkflowsResponse)
        assert result.total_onboarded == 0
        assert result.total_skipped == 0
        assert result.total_failed == 0
        assert result.results == []
