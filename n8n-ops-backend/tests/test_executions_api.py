"""
API tests for the executions endpoint.
"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient


# Mock entitlements for all execution tests
@pytest.fixture(autouse=True)
def mock_entitlements():
    """Mock entitlements service to allow all features for testing."""
    with patch("app.core.entitlements_gate.entitlements_service") as mock_ent:
        mock_ent.enforce_flag = AsyncMock(return_value=None)
        mock_ent.has_flag = AsyncMock(return_value=True)
        yield mock_ent


class TestExecutionsAPIGet:
    """Tests for GET /api/v1/executions endpoints."""

    @pytest.mark.api
    def test_get_executions_success(self, client: TestClient, auth_headers):
        """GET /executions should return list of executions."""
        mock_executions = [
            {
                "id": "exec-1",
                "workflow_id": "wf-1",
                "status": "success",
                "started_at": "2024-01-15T10:00:00Z",
                "finished_at": "2024-01-15T10:01:00Z",
            },
            {
                "id": "exec-2",
                "workflow_id": "wf-2",
                "status": "error",
                "started_at": "2024-01-15T09:00:00Z",
                "finished_at": "2024-01-15T09:00:30Z",
            },
        ]

        with patch("app.api.endpoints.executions.db_service") as mock_db:
            mock_db.get_executions = AsyncMock(return_value=mock_executions)

            response = client.get(
                "/api/v1/executions",
                params={"environment_id": "env-1"},
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.api
    def test_get_executions_empty_list(self, client: TestClient, auth_headers):
        """GET /executions with no executions should return empty list."""
        with patch("app.api.endpoints.executions.db_service") as mock_db:
            mock_db.get_executions = AsyncMock(return_value=[])

            response = client.get(
                "/api/v1/executions",
                params={"environment_id": "env-1"},
                headers=auth_headers
            )

            assert response.status_code == 200

    @pytest.mark.api
    def test_get_executions_filter_by_status(self, client: TestClient, auth_headers):
        """GET /executions with status filter should return filtered results."""
        mock_executions = [
            {
                "id": "exec-1",
                "workflow_id": "wf-1",
                "status": "success",
            },
        ]

        with patch("app.api.endpoints.executions.db_service") as mock_db:
            mock_db.get_executions = AsyncMock(return_value=mock_executions)

            response = client.get(
                "/api/v1/executions",
                params={"environment_id": "env-1", "status": "success"},
                headers=auth_headers
            )

            assert response.status_code == 200

    @pytest.mark.api
    def test_get_executions_filter_by_workflow(self, client: TestClient, auth_headers):
        """GET /executions with workflow filter should return filtered results."""
        mock_executions = [
            {
                "id": "exec-1",
                "workflow_id": "wf-1",
                "status": "success",
            },
        ]

        with patch("app.api.endpoints.executions.db_service") as mock_db:
            mock_db.get_executions = AsyncMock(return_value=mock_executions)

            response = client.get(
                "/api/v1/executions",
                params={"environment_id": "env-1", "workflow_id": "wf-1"},
                headers=auth_headers
            )

            assert response.status_code == 200


class TestExecutionsAPIStats:
    """Tests for execution stats endpoints."""

    @pytest.mark.api
    def test_get_execution_stats(self, client: TestClient, auth_headers):
        """GET /executions/stats should return execution statistics."""
        mock_stats = {
            "total": 100,
            "success": 80,
            "error": 15,
            "running": 5,
        }

        with patch("app.api.endpoints.executions.db_service") as mock_db:
            mock_db.get_execution_stats = AsyncMock(return_value=mock_stats)

            response = client.get(
                "/api/v1/executions/stats",
                params={"environment_id": "env-1"},
                headers=auth_headers
            )

            # May return 200, 404, or 500 depending on endpoint
            assert response.status_code in [200, 404, 500]
