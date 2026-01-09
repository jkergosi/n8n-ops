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
        """POST /pipelines should require correct number of stages for single-hop (MVP)."""
        # Use valid UUIDs for environment IDs
        env_1_id = "00000000-0000-0000-0000-000000000001"
        env_2_id = "00000000-0000-0000-0000-000000000002"

        # MVP: Only 2 environments allowed, test with mismatched stage count
        invalid_pipeline = {
            "name": "Wrong Stages Pipeline",
            "description": "2 environments but no stages",
            "is_active": True,
            "environment_ids": [env_1_id, env_2_id],
            "stages": [],  # Should have 1 stage for 2 environments
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


class TestSingleHopPipelineSuccess:
    """Tests for MVP single-hop pipeline success cases."""

    @pytest.mark.api
    def test_create_single_hop_pipeline_success(self, client: TestClient, auth_headers):
        """POST /pipelines with exactly 2 environments and 1 stage should succeed (MVP single-hop)."""
        env_source = "00000000-0000-0000-0000-000000000001"
        env_target = "00000000-0000-0000-0000-000000000002"

        single_hop_pipeline = {
            "name": "Single Hop Pipeline",
            "description": "MVP-compliant single-hop pipeline from dev to prod",
            "is_active": True,
            "environment_ids": [env_source, env_target],
            "stages": [
                {
                    "source_environment_id": env_source,
                    "target_environment_id": env_target,
                    "gates": {
                        "require_clean_drift": True,
                        "run_pre_flight_validation": True,
                        "credentials_exist_in_target": True,
                        "nodes_supported_in_target": True,
                        "webhooks_available": False,
                        "target_environment_healthy": True,
                        "max_allowed_risk_level": "Medium",
                    },
                    "approvals": {
                        "require_approval": True,
                        "approver_role": "admin",
                        "approver_group": None,
                        "required_approvals": "1 of N",
                    },
                    "policy_flags": {
                        "allow_placeholder_credentials": False,
                        "allow_overwriting_hotfixes": False,
                        "allow_force_promotion_on_conflicts": False,
                    },
                }
            ],
        }

        created_response = {
            "id": "00000000-0000-0000-0000-000000000099",
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            **single_hop_pipeline,
            "last_modified_by": None,
            "last_modified_at": "2024-01-15T10:00:00Z",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:00:00Z",
        }

        with patch("app.api.endpoints.pipelines.db_service") as mock_db:
            mock_db.create_pipeline = AsyncMock(return_value=created_response)

            response = client.post("/api/v1/pipelines", json=single_hop_pipeline, headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Single Hop Pipeline"
            assert len(data["environment_ids"]) == 2
            assert len(data["stages"]) == 1
            assert data["stages"][0]["source_environment_id"] == env_source
            assert data["stages"][0]["target_environment_id"] == env_target

    @pytest.mark.api
    def test_create_single_hop_pipeline_with_minimal_gates(self, client: TestClient, auth_headers):
        """POST /pipelines with minimal gate configuration should succeed."""
        env_source = "00000000-0000-0000-0000-000000000011"
        env_target = "00000000-0000-0000-0000-000000000012"

        minimal_pipeline = {
            "name": "Minimal Gates Pipeline",
            "description": "Single-hop with all gates disabled",
            "is_active": True,
            "environment_ids": [env_source, env_target],
            "stages": [
                {
                    "source_environment_id": env_source,
                    "target_environment_id": env_target,
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
                        "allow_placeholder_credentials": True,
                        "allow_overwriting_hotfixes": True,
                        "allow_force_promotion_on_conflicts": True,
                    },
                }
            ],
        }

        created_response = {
            "id": "00000000-0000-0000-0000-000000000098",
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            **minimal_pipeline,
            "last_modified_by": None,
            "last_modified_at": "2024-01-15T10:00:00Z",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:00:00Z",
        }

        with patch("app.api.endpoints.pipelines.db_service") as mock_db:
            mock_db.create_pipeline = AsyncMock(return_value=created_response)

            response = client.post("/api/v1/pipelines", json=minimal_pipeline, headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Minimal Gates Pipeline"
            assert len(data["environment_ids"]) == 2
            assert len(data["stages"]) == 1
            # Verify minimal gates configuration
            assert data["stages"][0]["gates"]["require_clean_drift"] is False
            assert data["stages"][0]["approvals"]["require_approval"] is False

    @pytest.mark.api
    def test_create_single_hop_pipeline_inactive(self, client: TestClient, auth_headers):
        """POST /pipelines with is_active=False should succeed."""
        env_source = "00000000-0000-0000-0000-000000000021"
        env_target = "00000000-0000-0000-0000-000000000022"

        inactive_pipeline = {
            "name": "Inactive Pipeline",
            "description": "Pipeline created in disabled state",
            "is_active": False,
            "environment_ids": [env_source, env_target],
            "stages": [
                {
                    "source_environment_id": env_source,
                    "target_environment_id": env_target,
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

        created_response = {
            "id": "00000000-0000-0000-0000-000000000097",
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            **inactive_pipeline,
            "last_modified_by": None,
            "last_modified_at": "2024-01-15T10:00:00Z",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:00:00Z",
        }

        with patch("app.api.endpoints.pipelines.db_service") as mock_db:
            mock_db.create_pipeline = AsyncMock(return_value=created_response)

            response = client.post("/api/v1/pipelines", json=inactive_pipeline, headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["is_active"] is False

    @pytest.mark.api
    def test_update_single_hop_pipeline_environments_success(self, client: TestClient, mock_pipelines, auth_headers):
        """PATCH /pipelines/{id} with new single-hop environments should succeed."""
        existing = mock_pipelines[0]
        new_source = "00000000-0000-0000-0000-000000000031"
        new_target = "00000000-0000-0000-0000-000000000032"

        updates = {
            "environment_ids": [new_source, new_target],
            "stages": [
                {
                    "source_environment_id": new_source,
                    "target_environment_id": new_target,
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

        updated_pipeline = {
            **existing,
            **updates,
            "updated_at": "2024-01-16T10:00:00Z",
        }

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
            assert len(data["environment_ids"]) == 2
            assert data["environment_ids"] == [new_source, new_target]
            assert len(data["stages"]) == 1

    @pytest.mark.api
    def test_update_single_hop_pipeline_name_and_description_success(self, client: TestClient, mock_pipelines, auth_headers):
        """PATCH /pipelines/{id} updating name/description should succeed without changing environments."""
        existing = mock_pipelines[0]
        updates = {
            "name": "Renamed Single Hop Pipeline",
            "description": "Updated description for single-hop pipeline",
        }

        updated_pipeline = {
            **existing,
            **updates,
            "updated_at": "2024-01-16T10:00:00Z",
        }

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
            assert data["name"] == "Renamed Single Hop Pipeline"
            assert data["description"] == "Updated description for single-hop pipeline"
            # Environments should remain unchanged (still single-hop)
            assert len(data["environment_ids"]) == 2
            assert len(data["stages"]) == 1


class TestMultiStagePipelineRejection:
    """Tests for MVP multi-stage pipeline rejection."""

    @pytest.mark.api
    def test_create_multi_stage_pipeline_rejected_three_environments(self, client: TestClient, auth_headers):
        """POST /pipelines with 3 environments should be rejected (MVP single-hop only)."""
        env_1 = "00000000-0000-0000-0000-000000000041"
        env_2 = "00000000-0000-0000-0000-000000000042"
        env_3 = "00000000-0000-0000-0000-000000000043"

        multi_stage_pipeline = {
            "name": "Multi-Stage Pipeline",
            "description": "This should be rejected - 3 environments requires 2 stages",
            "is_active": True,
            "environment_ids": [env_1, env_2, env_3],  # 3 environments = multi-stage
            "stages": [
                {
                    "source_environment_id": env_1,
                    "target_environment_id": env_2,
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
                },
                {
                    "source_environment_id": env_2,
                    "target_environment_id": env_3,
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
                },
            ],
        }

        response = client.post("/api/v1/pipelines", json=multi_stage_pipeline, headers=auth_headers)

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "multi-stage" in detail.lower()
        assert "mvp" in detail.lower()
        assert "separate pipelines" in detail.lower()

    @pytest.mark.api
    def test_create_multi_stage_pipeline_rejected_four_environments(self, client: TestClient, auth_headers):
        """POST /pipelines with 4 environments should be rejected (MVP single-hop only)."""
        env_1 = "00000000-0000-0000-0000-000000000051"
        env_2 = "00000000-0000-0000-0000-000000000052"
        env_3 = "00000000-0000-0000-0000-000000000053"
        env_4 = "00000000-0000-0000-0000-000000000054"

        multi_stage_pipeline = {
            "name": "Four Environment Pipeline",
            "description": "This should be rejected - 4 environments requires 3 stages",
            "is_active": True,
            "environment_ids": [env_1, env_2, env_3, env_4],  # 4 environments = multi-stage
            "stages": [
                {
                    "source_environment_id": env_1,
                    "target_environment_id": env_2,
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
                },
                {
                    "source_environment_id": env_2,
                    "target_environment_id": env_3,
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
                },
                {
                    "source_environment_id": env_3,
                    "target_environment_id": env_4,
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
                },
            ],
        }

        response = client.post("/api/v1/pipelines", json=multi_stage_pipeline, headers=auth_headers)

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "multi-stage" in detail.lower()
        assert "mvp" in detail.lower()

    @pytest.mark.api
    def test_update_pipeline_to_multi_stage_rejected(self, client: TestClient, mock_pipelines, auth_headers):
        """PATCH /pipelines/{id} updating to 3+ environments should be rejected."""
        existing = mock_pipelines[0]
        env_1 = "00000000-0000-0000-0000-000000000061"
        env_2 = "00000000-0000-0000-0000-000000000062"
        env_3 = "00000000-0000-0000-0000-000000000063"

        updates = {
            "environment_ids": [env_1, env_2, env_3],  # Attempting to add 3 environments
            "stages": [
                {
                    "source_environment_id": env_1,
                    "target_environment_id": env_2,
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
                },
                {
                    "source_environment_id": env_2,
                    "target_environment_id": env_3,
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
                },
            ],
        }

        with patch("app.api.endpoints.pipelines.db_service") as mock_db:
            mock_db.get_pipeline = AsyncMock(return_value=existing)

            response = client.patch(
                f"/api/v1/pipelines/{existing['id']}",
                json=updates,
                headers=auth_headers
            )

            assert response.status_code == 400
            detail = response.json()["detail"]
            assert "multi-stage" in detail.lower()
            assert "mvp" in detail.lower()

    @pytest.mark.api
    def test_create_multi_stage_returns_helpful_error_message(self, client: TestClient, auth_headers):
        """POST /pipelines with 3+ environments should return helpful error message."""
        env_1 = "00000000-0000-0000-0000-000000000071"
        env_2 = "00000000-0000-0000-0000-000000000072"
        env_3 = "00000000-0000-0000-0000-000000000073"

        multi_stage_pipeline = {
            "name": "Test Error Message",
            "description": "Testing error message content",
            "is_active": True,
            "environment_ids": [env_1, env_2, env_3],
            "stages": [
                {
                    "source_environment_id": env_1,
                    "target_environment_id": env_2,
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
                },
                {
                    "source_environment_id": env_2,
                    "target_environment_id": env_3,
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
                },
            ],
        }

        response = client.post("/api/v1/pipelines", json=multi_stage_pipeline, headers=auth_headers)

        assert response.status_code == 400
        detail = response.json()["detail"]
        # Verify the error message is helpful and guides users to the solution
        assert "Multi-stage pipelines are not supported in MVP" in detail
        assert "Create separate pipelines for each hop" in detail


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
