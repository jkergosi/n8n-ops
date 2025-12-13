"""
API tests for the environments endpoint.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient


# Mock entitlements for all environment tests
@pytest.fixture(autouse=True)
def mock_entitlements():
    """Mock entitlements service to allow all features for testing."""
    with patch("app.core.entitlements_gate.entitlements_service") as mock_ent:
        mock_ent.enforce_flag = AsyncMock(return_value=None)
        mock_ent.has_flag = AsyncMock(return_value=True)
        yield mock_ent


class TestEnvironmentsAPIGet:
    """Tests for GET /api/v1/environments endpoints."""

    @pytest.mark.api
    def test_get_environments_success(self, client: TestClient, mock_environments, auth_headers):
        """GET /environments should return list of environments."""
        with patch("app.api.endpoints.environments.db_service") as mock_db:
            mock_db.get_environments = AsyncMock(return_value=mock_environments)

            response = client.get("/api/v1/environments", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.api
    def test_get_environments_empty_list(self, client: TestClient, auth_headers):
        """GET /environments with no environments should return empty list."""
        with patch("app.api.endpoints.environments.db_service") as mock_db:
            mock_db.get_environments = AsyncMock(return_value=[])

            response = client.get("/api/v1/environments", headers=auth_headers)

            assert response.status_code == 200
            assert response.json() == []

    @pytest.mark.api
    def test_get_environment_by_id_success(self, client: TestClient, mock_environments, auth_headers):
        """GET /environments/{id} should return specific environment."""
        env = mock_environments[0]

        with patch("app.api.endpoints.environments.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=env)

            response = client.get(f"/api/v1/environments/{env['id']}", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == env["id"]

    @pytest.mark.api
    def test_get_environment_not_found(self, client: TestClient, auth_headers):
        """GET /environments/{id} should return 404 for non-existent environment."""
        with patch("app.api.endpoints.environments.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=None)

            response = client.get("/api/v1/environments/non-existent", headers=auth_headers)

            assert response.status_code == 404


class TestEnvironmentsAPICreate:
    """Tests for POST /api/v1/environments endpoint."""

    @pytest.mark.api
    def test_create_environment_success(self, client: TestClient, auth_headers):
        """POST /environments should create a new environment."""
        create_request = {
            "n8n_name": "New Environment",
            "n8n_base_url": "https://n8n.example.com",
            "n8n_api_key": "test-api-key",
            "is_active": True,
            "allow_upload": True,
        }

        created_env = {
            "id": "env-new",
            "tenant_id": "tenant-1",
            "n8n_name": "New Environment",
            "n8n_base_url": "https://n8n.example.com",
            "is_active": True,
            "created_at": "2024-01-15T00:00:00Z",
            "updated_at": "2024-01-15T00:00:00Z",
        }

        with patch("app.api.endpoints.environments.db_service") as mock_db:
            mock_db.create_environment = AsyncMock(return_value=created_env)
            with patch("app.core.feature_gate.feature_service") as mock_feature:
                mock_feature.can_add_environment = AsyncMock(return_value=(True, "", 1, 10))
                with patch("app.api.endpoints.environments.create_audit_log") as mock_audit:
                    mock_audit.return_value = None

                    response = client.post(
                        "/api/v1/environments",
                        json=create_request,
                        headers=auth_headers
                    )

                    assert response.status_code == 201
                    data = response.json()
                    assert data["n8n_name"] == "New Environment"


class TestEnvironmentsAPIUpdate:
    """Tests for PATCH /api/v1/environments/{id} endpoint."""

    @pytest.mark.api
    def test_update_environment_success(self, client: TestClient, mock_environments, auth_headers):
        """PATCH /environments/{id} should update environment."""
        env = mock_environments[0]
        update_data = {"n8n_name": "Updated Name"}

        updated_env = {**env, "n8n_name": "Updated Name"}

        with patch("app.api.endpoints.environments.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=env)
            mock_db.update_environment = AsyncMock(return_value=updated_env)

            response = client.patch(
                f"/api/v1/environments/{env['id']}",
                json=update_data,
                headers=auth_headers
            )

            assert response.status_code == 200

    @pytest.mark.api
    def test_update_environment_not_found(self, client: TestClient, auth_headers):
        """PATCH /environments/{id} should return 404 for non-existent environment."""
        with patch("app.api.endpoints.environments.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=None)

            response = client.patch(
                "/api/v1/environments/non-existent",
                json={"n8n_name": "New Name"},
                headers=auth_headers
            )

            assert response.status_code == 404


class TestEnvironmentsAPIDelete:
    """Tests for DELETE /api/v1/environments/{id} endpoint."""

    @pytest.mark.api
    def test_delete_environment_success(self, client: TestClient, mock_environments, auth_headers):
        """DELETE /environments/{id} should delete environment."""
        env = mock_environments[0]

        with patch("app.api.endpoints.environments.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=env)
            mock_db.delete_environment = AsyncMock(return_value=None)
            with patch("app.api.endpoints.environments.create_audit_log") as mock_audit:
                mock_audit.return_value = None

                response = client.delete(
                    f"/api/v1/environments/{env['id']}",
                    headers=auth_headers
                )

                assert response.status_code == 204

    @pytest.mark.api
    def test_delete_environment_not_found(self, client: TestClient, auth_headers):
        """DELETE /environments/{id} should return 404 for non-existent environment."""
        with patch("app.api.endpoints.environments.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=None)

            response = client.delete(
                "/api/v1/environments/non-existent",
                headers=auth_headers
            )

            assert response.status_code == 404


class TestEnvironmentsAPISync:
    """Tests for environment sync endpoints."""

    @pytest.mark.api
    def test_sync_environment_not_found(self, client: TestClient, auth_headers):
        """POST /environments/{id}/sync should return 404 for non-existent environment."""
        with patch("app.api.endpoints.environments.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=None)

            response = client.post(
                "/api/v1/environments/non-existent/sync",
                headers=auth_headers
            )

            assert response.status_code == 404

    @pytest.mark.api
    def test_sync_users_only_not_found(self, client: TestClient, auth_headers):
        """POST /environments/{id}/sync-users should return 404 for non-existent environment."""
        with patch("app.api.endpoints.environments.db_service") as mock_db:
            mock_db.get_environment = AsyncMock(return_value=None)

            response = client.post(
                "/api/v1/environments/non-existent/sync-users",
                headers=auth_headers
            )

            assert response.status_code == 404


class TestEnvironmentsAPITestConnection:
    """Tests for connection testing endpoints."""

    @pytest.mark.api
    def test_test_connection_success(self, client: TestClient, auth_headers):
        """POST /environments/test-connection should test N8N connection."""
        connection_request = {
            "n8n_base_url": "https://n8n.example.com",
            "n8n_api_key": "test-api-key",
        }

        with patch("app.api.endpoints.environments.N8NClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.test_connection = AsyncMock(return_value=True)
            mock_client.return_value = mock_instance

            response = client.post(
                "/api/v1/environments/test-connection",
                json=connection_request,
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    @pytest.mark.api
    def test_test_connection_failure(self, client: TestClient, auth_headers):
        """POST /environments/test-connection should return failure for bad connection."""
        connection_request = {
            "n8n_base_url": "https://invalid.example.com",
            "n8n_api_key": "bad-api-key",
        }

        with patch("app.api.endpoints.environments.N8NClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.test_connection = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            response = client.post(
                "/api/v1/environments/test-connection",
                json=connection_request,
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False


class TestEnvironmentsAPILimits:
    """Tests for environment limits endpoint."""

    @pytest.mark.api
    def test_get_environment_limits(self, client: TestClient, auth_headers):
        """GET /environments/limits should return limits info."""
        with patch("app.api.endpoints.environments.feature_service") as mock_feature:
            mock_feature.can_add_environment = AsyncMock(return_value=(True, "OK", 2, 5))

            response = client.get("/api/v1/environments/limits", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert "can_add" in data
            assert "current" in data
            assert "max" in data
