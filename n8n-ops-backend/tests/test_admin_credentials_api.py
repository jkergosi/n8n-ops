"""
API tests for the admin credentials endpoints (matrix, discover, validate).
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def mock_entitlements():
    """Mock entitlements service to allow all features for testing."""
    with patch("app.core.entitlements_gate.entitlements_service") as mock_ent:
        mock_ent.enforce_flag = AsyncMock(return_value=None)
        mock_ent.has_flag = AsyncMock(return_value=True)
        yield mock_ent


MOCK_ENVIRONMENTS = [
    {
        "id": "env-1",
        "tenant_id": "tenant-1",
        "n8n_name": "Development",
        "n8n_type": "development",
        "n8n_base_url": "https://dev.n8n.example.com",
    },
    {
        "id": "env-2",
        "tenant_id": "tenant-1",
        "n8n_name": "Production",
        "n8n_type": "production",
        "n8n_base_url": "https://prod.n8n.example.com",
    },
]

MOCK_LOGICAL_CREDENTIALS = [
    {
        "id": "logical-1",
        "tenant_id": "tenant-1",
        "name": "slackApi:prod-slack",
        "required_type": "slackApi",
        "description": "Production Slack credential",
        "created_at": "2024-01-01T00:00:00Z",
    },
    {
        "id": "logical-2",
        "tenant_id": "tenant-1",
        "name": "githubApi:gh-token",
        "required_type": "githubApi",
        "description": "GitHub API token",
        "created_at": "2024-01-02T00:00:00Z",
    },
]

MOCK_MAPPINGS = [
    {
        "id": "mapping-1",
        "tenant_id": "tenant-1",
        "logical_credential_id": "logical-1",
        "environment_id": "env-1",
        "provider": "n8n",
        "physical_credential_id": "n8n-cred-1",
        "physical_name": "Dev Slack",
        "physical_type": "slackApi",
        "status": "valid",
    },
    {
        "id": "mapping-2",
        "tenant_id": "tenant-1",
        "logical_credential_id": "logical-1",
        "environment_id": "env-2",
        "provider": "n8n",
        "physical_credential_id": "n8n-cred-2",
        "physical_name": "Prod Slack",
        "physical_type": "slackApi",
        "status": "valid",
    },
]

MOCK_WORKFLOWS = [
    {
        "id": "wf-1",
        "n8n_workflow_id": "n8n-wf-1",
        "name": "Test Workflow",
        "workflow_data": {
            "name": "Test Workflow",
            "nodes": [
                {
                    "id": "node-1",
                    "type": "n8n-nodes-base.slack",
                    "name": "Slack",
                    "credentials": {
                        "slackApi": {"id": "n8n-cred-1", "name": "prod-slack"}
                    },
                }
            ],
        },
    },
]


class TestCredentialMatrixEndpoint:
    """Tests for GET /api/v1/admin/credentials/matrix endpoint."""

    @pytest.mark.api
    def test_get_credential_matrix_success(self, client: TestClient, auth_headers):
        """GET /admin/credentials/matrix should return matrix view."""
        with patch("app.api.endpoints.admin_credentials.db_service") as mock_db:
            mock_db.get_environments = AsyncMock(return_value=MOCK_ENVIRONMENTS)
            mock_db.list_logical_credentials = AsyncMock(return_value=MOCK_LOGICAL_CREDENTIALS)
            mock_db.list_credential_mappings = AsyncMock(return_value=MOCK_MAPPINGS)

            response = client.get(
                "/api/v1/admin/credentials/matrix",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert "logical_credentials" in data
            assert "environments" in data
            assert "matrix" in data

    @pytest.mark.api
    def test_get_credential_matrix_empty(self, client: TestClient, auth_headers):
        """GET /admin/credentials/matrix should handle empty data."""
        with patch("app.api.endpoints.admin_credentials.db_service") as mock_db:
            mock_db.get_environments = AsyncMock(return_value=[])
            mock_db.list_logical_credentials = AsyncMock(return_value=[])
            mock_db.list_credential_mappings = AsyncMock(return_value=[])

            response = client.get(
                "/api/v1/admin/credentials/matrix",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["logical_credentials"] == []
            assert data["environments"] == []
            assert data["matrix"] == {}

    @pytest.mark.api
    def test_get_credential_matrix_with_mappings(self, client: TestClient, auth_headers):
        """GET /admin/credentials/matrix should include mapping details."""
        with patch("app.api.endpoints.admin_credentials.db_service") as mock_db:
            mock_db.get_environments = AsyncMock(return_value=MOCK_ENVIRONMENTS)
            mock_db.list_logical_credentials = AsyncMock(return_value=MOCK_LOGICAL_CREDENTIALS)
            mock_db.list_credential_mappings = AsyncMock(return_value=MOCK_MAPPINGS)

            response = client.get(
                "/api/v1/admin/credentials/matrix",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()

            assert len(data["logical_credentials"]) == 2
            assert len(data["environments"]) == 2
            assert "logical-1" in data["matrix"]
            assert data["matrix"]["logical-1"]["env-1"] is not None
            assert data["matrix"]["logical-1"]["env-1"]["physical_name"] == "Dev Slack"


class TestCredentialDiscoveryEndpoint:
    """Tests for POST /api/v1/admin/credentials/discover/{environment_id} endpoint."""

    @pytest.mark.api
    def test_discover_credentials_success(self, client: TestClient, auth_headers):
        """POST /admin/credentials/discover should return discovered credentials."""
        with patch("app.api.endpoints.admin_credentials.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENTS[0])
            mock_db.get_workflows = AsyncMock(return_value=MOCK_WORKFLOWS)
            mock_db.list_logical_credentials = AsyncMock(return_value=MOCK_LOGICAL_CREDENTIALS)
            mock_db.list_credential_mappings = AsyncMock(return_value=MOCK_MAPPINGS)

            response = client.post(
                "/api/v1/admin/credentials/discover/env-1",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.api
    def test_discover_credentials_not_found_environment(self, client: TestClient, auth_headers):
        """POST /admin/credentials/discover should return 404 for non-existent environment."""
        with patch("app.api.endpoints.admin_credentials.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=None)

            response = client.post(
                "/api/v1/admin/credentials/discover/non-existent",
                headers=auth_headers
            )

            assert response.status_code == 404

    @pytest.mark.api
    def test_discover_credentials_extracts_from_workflows(self, client: TestClient, auth_headers):
        """POST /admin/credentials/discover should extract credentials from workflow nodes."""
        with patch("app.api.endpoints.admin_credentials.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENTS[0])
            mock_db.get_workflows = AsyncMock(return_value=MOCK_WORKFLOWS)
            mock_db.list_logical_credentials = AsyncMock(return_value=[])
            mock_db.list_credential_mappings = AsyncMock(return_value=[])

            response = client.post(
                "/api/v1/admin/credentials/discover/env-1",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data) >= 1
            assert any(cred["type"] == "slackApi" for cred in data)

    @pytest.mark.api
    def test_discover_credentials_shows_workflow_count(self, client: TestClient, auth_headers):
        """POST /admin/credentials/discover should include workflow count."""
        with patch("app.api.endpoints.admin_credentials.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENTS[0])
            mock_db.get_workflows = AsyncMock(return_value=MOCK_WORKFLOWS)
            mock_db.list_logical_credentials = AsyncMock(return_value=[])
            mock_db.list_credential_mappings = AsyncMock(return_value=[])

            response = client.post(
                "/api/v1/admin/credentials/discover/env-1",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            if len(data) > 0:
                assert "workflow_count" in data[0]
                assert data[0]["workflow_count"] >= 1


class TestCredentialMappingValidationEndpoint:
    """Tests for POST /api/v1/admin/credentials/mappings/validate endpoint."""

    @pytest.mark.api
    def test_validate_mappings_success(self, client: TestClient, auth_headers):
        """POST /admin/credentials/mappings/validate should return validation report."""
        mock_adapter = MagicMock()
        mock_adapter.get_credentials = AsyncMock(return_value=[
            {"id": "n8n-cred-1", "name": "Dev Slack", "type": "slackApi"},
            {"id": "n8n-cred-2", "name": "Prod Slack", "type": "slackApi"},
        ])

        with patch("app.api.endpoints.admin_credentials.db_service") as mock_db, \
             patch("app.api.endpoints.admin_credentials.ProviderRegistry") as mock_registry:
            mock_db.list_credential_mappings = AsyncMock(return_value=MOCK_MAPPINGS)
            mock_db.list_logical_credentials = AsyncMock(return_value=MOCK_LOGICAL_CREDENTIALS)
            mock_db.get_environments = AsyncMock(return_value=MOCK_ENVIRONMENTS)
            mock_db.update_credential_mapping = AsyncMock(return_value=None)

            mock_registry.get_adapter_for_environment = MagicMock(return_value=mock_adapter)

            response = client.post(
                "/api/v1/admin/credentials/mappings/validate",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert "total" in data
            assert "valid" in data
            assert "invalid" in data
            assert "stale" in data
            assert "issues" in data

    @pytest.mark.api
    def test_validate_mappings_detects_invalid(self, client: TestClient, auth_headers):
        """POST /admin/credentials/mappings/validate should detect invalid mappings."""
        mock_adapter = MagicMock()
        mock_adapter.get_credentials = AsyncMock(return_value=[])

        with patch("app.api.endpoints.admin_credentials.db_service") as mock_db, \
             patch("app.api.endpoints.admin_credentials.ProviderRegistry") as mock_registry:
            mock_db.list_credential_mappings = AsyncMock(return_value=MOCK_MAPPINGS)
            mock_db.list_logical_credentials = AsyncMock(return_value=MOCK_LOGICAL_CREDENTIALS)
            mock_db.get_environments = AsyncMock(return_value=MOCK_ENVIRONMENTS)
            mock_db.update_credential_mapping = AsyncMock(return_value=None)

            mock_registry.get_adapter_for_environment = MagicMock(return_value=mock_adapter)

            response = client.post(
                "/api/v1/admin/credentials/mappings/validate",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["invalid"] > 0
            assert len(data["issues"]) > 0

    @pytest.mark.api
    def test_validate_mappings_filter_by_environment(self, client: TestClient, auth_headers):
        """POST /admin/credentials/mappings/validate should filter by environment."""
        mock_adapter = MagicMock()
        mock_adapter.get_credentials = AsyncMock(return_value=[
            {"id": "n8n-cred-1", "name": "Dev Slack", "type": "slackApi"},
        ])

        with patch("app.api.endpoints.admin_credentials.db_service") as mock_db, \
             patch("app.api.endpoints.admin_credentials.ProviderRegistry") as mock_registry:
            mock_db.list_credential_mappings = AsyncMock(return_value=[MOCK_MAPPINGS[0]])
            mock_db.list_logical_credentials = AsyncMock(return_value=MOCK_LOGICAL_CREDENTIALS)
            mock_db.get_environments = AsyncMock(return_value=[MOCK_ENVIRONMENTS[0]])
            mock_db.update_credential_mapping = AsyncMock(return_value=None)

            mock_registry.get_adapter_for_environment = MagicMock(return_value=mock_adapter)

            response = client.post(
                "/api/v1/admin/credentials/mappings/validate",
                params={"environment_id": "env-1"},
                headers=auth_headers
            )

            assert response.status_code == 200
            mock_db.list_credential_mappings.assert_called_once()


class TestCredentialsByEnvironmentEndpoint:
    """Tests for GET /api/v1/credentials/by-environment/{environment_id} endpoint."""

    @pytest.mark.api
    def test_get_credentials_by_environment_success(self, client: TestClient, auth_headers):
        """GET /credentials/by-environment should return credentials from N8N."""
        mock_adapter = MagicMock()
        mock_adapter.get_credentials = AsyncMock(return_value=[
            {"id": "cred-1", "name": "Slack API", "type": "slackApi"},
            {"id": "cred-2", "name": "GitHub Token", "type": "githubApi"},
        ])

        with patch("app.api.endpoints.credentials.db_service") as mock_db, \
             patch("app.api.endpoints.credentials.ProviderRegistry") as mock_registry:
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENTS[0])
            mock_registry.get_adapter_for_environment = MagicMock(return_value=mock_adapter)

            response = client.get(
                "/api/v1/credentials/by-environment/env-1",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2
            assert data[0]["name"] == "Slack API"

    @pytest.mark.api
    def test_get_credentials_by_environment_not_found(self, client: TestClient, auth_headers):
        """GET /credentials/by-environment should return 404 for non-existent environment."""
        with patch("app.api.endpoints.credentials.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=None)

            response = client.get(
                "/api/v1/credentials/by-environment/non-existent",
                headers=auth_headers
            )

            assert response.status_code == 404

    @pytest.mark.api
    def test_get_credentials_by_environment_empty(self, client: TestClient, auth_headers):
        """GET /credentials/by-environment should return empty list when no credentials."""
        mock_adapter = MagicMock()
        mock_adapter.get_credentials = AsyncMock(return_value=[])

        with patch("app.api.endpoints.credentials.db_service") as mock_db, \
             patch("app.api.endpoints.credentials.ProviderRegistry") as mock_registry:
            mock_db.get_environment = AsyncMock(return_value=MOCK_ENVIRONMENTS[0])
            mock_registry.get_adapter_for_environment = MagicMock(return_value=mock_adapter)

            response = client.get(
                "/api/v1/credentials/by-environment/env-1",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data == []
