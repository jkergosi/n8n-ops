"""
API tests for the pipelines endpoint.
"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient


# All pipelines tests need to bypass the entitlement check
@pytest.fixture(autouse=True)
def mock_entitlements():
    """Mock entitlements service to allow all features for testing."""
    with patch("app.core.entitlements_gate.entitlements_service") as mock_ent:
        mock_ent.enforce_flag = AsyncMock(return_value=None)
        mock_ent.has_flag = AsyncMock(return_value=True)
        yield mock_ent


class TestPipelinesAPIGet:
    """Tests for GET /api/v1/pipelines endpoints."""

    @pytest.mark.api
    def test_get_pipelines_success(self, client: TestClient, mock_pipelines, auth_headers):
        """GET /pipelines should return list of pipelines."""
        with patch("app.api.endpoints.pipelines.db_service") as mock_db:
            mock_db.get_pipelines = AsyncMock(return_value=mock_pipelines)

            response = client.get("/api/v1/pipelines", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.api
    def test_get_pipelines_empty_list(self, client: TestClient, auth_headers):
        """GET /pipelines with no pipelines should return empty list."""
        with patch("app.api.endpoints.pipelines.db_service") as mock_db:
            mock_db.get_pipelines = AsyncMock(return_value=[])

            response = client.get("/api/v1/pipelines", headers=auth_headers)

            assert response.status_code == 200
            assert response.json() == []

    @pytest.mark.api
    def test_get_pipeline_by_id_success(self, client: TestClient, mock_pipelines, auth_headers):
        """GET /pipelines/{id} should return specific pipeline."""
        pipeline = mock_pipelines[0]

        with patch("app.api.endpoints.pipelines.db_service") as mock_db:
            mock_db.get_pipeline = AsyncMock(return_value=pipeline)

            response = client.get(f"/api/v1/pipelines/{pipeline['id']}", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == pipeline["id"]
            assert data["name"] == pipeline["name"]

    @pytest.mark.api
    def test_get_pipeline_not_found(self, client: TestClient, auth_headers):
        """GET /pipelines/{id} should return 404 for non-existent pipeline."""
        with patch("app.api.endpoints.pipelines.db_service") as mock_db:
            mock_db.get_pipeline = AsyncMock(return_value=None)

            response = client.get("/api/v1/pipelines/non-existent-id", headers=auth_headers)

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


class TestPipelinesAPICreate:
    """Tests for POST /api/v1/pipelines endpoint."""

    @pytest.mark.api
    def test_create_pipeline_success(self, client: TestClient, auth_headers):
        """POST /pipelines should create a new pipeline."""
        # Use valid UUIDs for environment IDs as the endpoint validates them
        env_1_id = "00000000-0000-0000-0000-000000000001"
        env_2_id = "00000000-0000-0000-0000-000000000002"

        new_pipeline = {
            "name": "New Pipeline",
            "description": "Test pipeline",
            "is_active": True,
            "environment_ids": [env_1_id, env_2_id],
            "stages": [
                {
                    "source_environment_id": env_1_id,
                    "target_environment_id": env_2_id,
                    "gates": {
                        "require_clean_drift": True,
                        "run_pre_flight_validation": False,
                        "credentials_exist_in_target": False,
                        "nodes_supported_in_target": False,
                        "webhooks_available": False,
                        "target_environment_healthy": False,
                        "max_allowed_risk_level": "High",
                    },
                    "approvals": {
                        "require_approval": False,
                        "approver_role": None,
                        "approver_group": None,
                        "required_approvals": None,
                    },
                    "policy_flags": {
                        "allow_placeholder_credentials": False,
                        "allow_overwriting_hotfixes": False,
                        "allow_force_promotion_on_conflicts": False,
                    },
                }
            ],
        }

        created_pipeline = {
            "id": "00000000-0000-0000-0000-000000000010",
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            **new_pipeline,
            "last_modified_by": None,
            "last_modified_at": "2024-01-15T10:00:00Z",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:00:00Z",
        }

        with patch("app.api.endpoints.pipelines.db_service") as mock_db:
            mock_db.create_pipeline = AsyncMock(return_value=created_pipeline)

            response = client.post("/api/v1/pipelines", json=new_pipeline, headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == new_pipeline["name"]
            assert "id" in data

    @pytest.mark.api
    def test_create_pipeline_requires_minimum_environments(self, client: TestClient, auth_headers):
        """POST /pipelines should require at least 2 environments."""
        invalid_pipeline = {
            "name": "Invalid Pipeline",
            "description": "Only one environment",
            "is_active": True,
            "environment_ids": ["env-1"],  # Only 1 environment
            "stages": [],
        }

        response = client.post("/api/v1/pipelines", json=invalid_pipeline, headers=auth_headers)

        assert response.status_code == 400
        assert "at least 2 environments" in response.json()["detail"].lower()

    @pytest.mark.api
    def test_create_pipeline_no_duplicate_environments(self, client: TestClient, auth_headers):
        """POST /pipelines should not allow duplicate environments."""
        invalid_pipeline = {
            "name": "Duplicate Envs Pipeline",
            "description": "Same env twice",
            "is_active": True,
            "environment_ids": ["env-1", "env-1"],  # Duplicate
            "stages": [
                {
                    "source_environment_id": "env-1",
                    "target_environment_id": "env-1",
                    "gates": {
                        "require_clean_drift": False,
                        "run_pre_flight_validation": False,
                        "credentials_exist_in_target": False,
                        "nodes_supported_in_target": False,
                        "webhooks_available": False,
                        "target_environment_healthy": False,
                        "max_allowed_risk_level": "High",
                    },
                    "approvals": {
                        "require_approval": False,
                        "approver_role": None,
                        "approver_group": None,
                        "required_approvals": None,
                    },
                    "policy_flags": {
                        "allow_placeholder_credentials": False,
                        "allow_overwriting_hotfixes": False,
                        "allow_force_promotion_on_conflicts": False,
                    },
                }
            ],
        }

        response = client.post("/api/v1/pipelines", json=invalid_pipeline, headers=auth_headers)

        assert response.status_code == 400
        assert "duplicate" in response.json()["detail"].lower()

    @pytest.mark.api
    def test_create_pipeline_stages_match_environments(self, client: TestClient, auth_headers):
        """POST /pipelines should require correct number of stages."""
        invalid_pipeline = {
            "name": "Wrong Stages Pipeline",
            "description": "3 environments but only 1 stage",
            "is_active": True,
            "environment_ids": ["env-1", "env-2", "env-3"],
            "stages": [  # Should have 2 stages for 3 environments
                {
                    "source_environment_id": "env-1",
                    "target_environment_id": "env-2",
                    "gates": {
                        "require_clean_drift": False,
                        "run_pre_flight_validation": False,
                        "credentials_exist_in_target": False,
                        "nodes_supported_in_target": False,
                        "webhooks_available": False,
                        "target_environment_healthy": False,
                        "max_allowed_risk_level": "High",
                    },
                    "approvals": {
                        "require_approval": False,
                        "approver_role": None,
                        "approver_group": None,
                        "required_approvals": None,
                    },
                    "policy_flags": {
                        "allow_placeholder_credentials": False,
                        "allow_overwriting_hotfixes": False,
                        "allow_force_promotion_on_conflicts": False,
                    },
                }
            ],
        }

        response = client.post("/api/v1/pipelines", json=invalid_pipeline, headers=auth_headers)

        assert response.status_code == 400
        assert "expected" in response.json()["detail"].lower()
        assert "stages" in response.json()["detail"].lower()


class TestPipelinesAPIUpdate:
    """Tests for PATCH /api/v1/pipelines/{id} endpoint."""

    @pytest.mark.api
    def test_update_pipeline_success(self, client: TestClient, mock_pipelines, auth_headers):
        """PATCH /pipelines/{id} should update pipeline."""
        existing = mock_pipelines[0]
        updates = {"name": "Updated Pipeline Name"}

        updated_pipeline = {**existing, **updates, "updated_at": "2024-01-16T10:00:00Z"}

        with patch("app.api.endpoints.pipelines.db_service") as mock_db:
            mock_db.get_pipeline = AsyncMock(return_value=existing)
            mock_db.update_pipeline = AsyncMock(return_value=updated_pipeline)

            response = client.patch(
                f"/api/v1/pipelines/{existing['id']}",
                json=updates,
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Updated Pipeline Name"

    @pytest.mark.api
    def test_update_pipeline_not_found(self, client: TestClient, auth_headers):
        """PATCH /pipelines/{id} should return 404 for non-existent pipeline."""
        with patch("app.api.endpoints.pipelines.db_service") as mock_db:
            mock_db.get_pipeline = AsyncMock(return_value=None)

            response = client.patch(
                "/api/v1/pipelines/non-existent",
                json={"name": "Updated"},
                headers=auth_headers
            )

            assert response.status_code == 404

    @pytest.mark.api
    def test_update_pipeline_partial(self, client: TestClient, mock_pipelines, auth_headers):
        """PATCH /pipelines/{id} should allow partial updates."""
        existing = mock_pipelines[0]
        updates = {"description": "New description only"}

        updated_pipeline = {**existing, **updates}

        with patch("app.api.endpoints.pipelines.db_service") as mock_db:
            mock_db.get_pipeline = AsyncMock(return_value=existing)
            mock_db.update_pipeline = AsyncMock(return_value=updated_pipeline)

            response = client.patch(
                f"/api/v1/pipelines/{existing['id']}",
                json=updates,
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == existing["name"]  # Unchanged
            assert data["description"] == "New description only"


class TestPipelinesAPIDelete:
    """Tests for DELETE /api/v1/pipelines/{id} endpoint."""

    @pytest.mark.api
    def test_delete_pipeline_success(self, client: TestClient, mock_pipelines, auth_headers):
        """DELETE /pipelines/{id} should delete pipeline."""
        existing = mock_pipelines[0]

        with patch("app.api.endpoints.pipelines.db_service") as mock_db:
            mock_db.get_pipeline = AsyncMock(return_value=existing)
            mock_db.delete_pipeline = AsyncMock(return_value=None)

            response = client.delete(
                f"/api/v1/pipelines/{existing['id']}",
                headers=auth_headers
            )

            assert response.status_code == 200
            assert response.json()["success"] is True

    @pytest.mark.api
    def test_delete_pipeline_not_found(self, client: TestClient, auth_headers):
        """DELETE /pipelines/{id} should return 404 for non-existent pipeline."""
        with patch("app.api.endpoints.pipelines.db_service") as mock_db:
            mock_db.get_pipeline = AsyncMock(return_value=None)

            response = client.delete(
                "/api/v1/pipelines/non-existent",
                headers=auth_headers
            )

            assert response.status_code == 404


class TestPipelinesAPIResponseFormat:
    """Tests for response format and schema validation."""

    @pytest.mark.api
    def test_pipeline_response_has_required_fields(self, client: TestClient, mock_pipelines, auth_headers):
        """Pipeline response should have all required fields."""
        pipeline = mock_pipelines[0]

        with patch("app.api.endpoints.pipelines.db_service") as mock_db:
            mock_db.get_pipeline = AsyncMock(return_value=pipeline)

            response = client.get(f"/api/v1/pipelines/{pipeline['id']}", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()

            # Check required fields
            required_fields = ["id", "name", "environment_ids", "stages"]
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"

    @pytest.mark.api
    def test_pipeline_stages_structure(self, client: TestClient, mock_pipelines, auth_headers):
        """Pipeline stages should have correct structure."""
        pipeline = mock_pipelines[0]

        with patch("app.api.endpoints.pipelines.db_service") as mock_db:
            mock_db.get_pipeline = AsyncMock(return_value=pipeline)

            response = client.get(f"/api/v1/pipelines/{pipeline['id']}", headers=auth_headers)

            data = response.json()
            assert "stages" in data
            assert isinstance(data["stages"], list)

            if len(data["stages"]) > 0:
                stage = data["stages"][0]
                assert "source_environment_id" in stage
                assert "target_environment_id" in stage
