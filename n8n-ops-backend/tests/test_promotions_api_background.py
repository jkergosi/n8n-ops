"""
Tests for promotion execution with background jobs
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from app.services.background_job_service import BackgroundJobStatus, BackgroundJobType


# Mock entitlements for all tests
@pytest.fixture(autouse=True)
def mock_entitlements():
    """Mock entitlements service to allow all features for testing."""
    with patch("app.core.entitlements_gate.entitlements_service") as mock_ent:
        mock_ent.enforce_flag = AsyncMock(return_value=None)
        mock_ent.has_flag = AsyncMock(return_value=True)
        yield mock_ent


@pytest.mark.asyncio
async def test_execute_promotion_creates_job(client, auth_headers):
    """Test that executing a promotion creates a background job"""
    from app.services.database import db_service
    
    # Create a promotion
    promotion_data = {
        "id": str(uuid4()),
        "tenant_id": "00000000-0000-0000-0000-000000000000",
        "pipeline_id": str(uuid4()),
        "source_environment_id": str(uuid4()),
        "target_environment_id": str(uuid4()),
        "status": "approved",
        "workflow_selections": [
            {"workflow_id": str(uuid4()), "workflow_name": "Test Workflow", "selected": True}
        ],
        "created_by": "00000000-0000-0000-0000-000000000000"
    }
    
    job_id = str(uuid4())
    deployment_id = str(uuid4())
    
    with patch.object(db_service, 'get_promotion', return_value=promotion_data):
        with patch.object(db_service, 'get_environment', return_value={
            "id": str(uuid4()),
            "base_url": "http://localhost:5678",
            "api_key": "test-key"
        }):
            with patch.object(db_service, 'update_promotion', return_value=promotion_data):
                with patch.object(db_service, 'create_deployment', return_value={"id": deployment_id}):
                    with patch.object(db_service, 'create_deployment_workflows_batch', AsyncMock(return_value=None)):
                        with patch('app.api.endpoints.promotions.background_job_service') as mock_job_service:
                            mock_job_service.create_job = AsyncMock(return_value={
                                "id": job_id,
                                "status": BackgroundJobStatus.PENDING
                            })
                            # Mock all methods used in background task
                            mock_job_service.update_job_status = AsyncMock(return_value={"id": job_id, "status": BackgroundJobStatus.RUNNING})
                            mock_job_service.update_progress = AsyncMock(return_value={"id": job_id, "status": BackgroundJobStatus.RUNNING})
                            
                            with patch("app.api.endpoints.promotions.check_drift_policy_blocking", AsyncMock(return_value={"blocked": False, "reason": None, "details": {}})):
                                response = client.post(
                                    f"/api/v1/promotions/execute/{promotion_data['id']}",
                                    headers=auth_headers
                                )
                            
                            assert response.status_code == 200
                            data = response.json()
                            assert "job_id" in data
                            assert "promotion_id" in data
                            assert "deployment_id" in data
                            assert data["status"] == "running"
                            
                            # Verify job was created
                            mock_job_service.create_job.assert_called_once()
                            call_kwargs = mock_job_service.create_job.call_args[1]
                            assert call_kwargs["job_type"] == BackgroundJobType.PROMOTION_EXECUTE
                            assert call_kwargs["resource_id"] == promotion_data["id"]


@pytest.mark.asyncio
async def test_get_promotion_job_status(client, auth_headers):
    """Test getting promotion job status"""
    from app.services.database import db_service
    from app.services.background_job_service import background_job_service
    
    promotion_id = str(uuid4())
    job_id = str(uuid4())
    
    mock_job = {
        "id": job_id,
        "promotion_id": promotion_id,
        "status": BackgroundJobStatus.RUNNING,
        "progress": {"current": 3, "total": 10, "percentage": 30},
        "result": {},
        "started_at": "2024-01-01T12:00:00Z"
    }
    
    with patch.object(background_job_service, 'get_latest_job_by_resource', return_value=mock_job):
        response = client.get(
            f"/api/v1/promotions/{promotion_id}/job",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert data["promotion_id"] == promotion_id
        assert data["status"] == BackgroundJobStatus.RUNNING
        assert data["progress"]["current"] == 3
        assert data["progress"]["total"] == 10


@pytest.mark.asyncio
async def test_get_promotion_job_not_found(client, auth_headers):
    """Test getting job status when no job exists"""
    from app.services.background_job_service import background_job_service
    
    promotion_id = str(uuid4())
    
    with patch.object(background_job_service, 'get_latest_job_by_resource', return_value=None):
        response = client.get(
            f"/api/v1/promotions/{promotion_id}/job",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "No job found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_execute_promotion_no_workflows(client, auth_headers):
    """Test that executing promotion with no workflows fails"""
    from app.services.database import db_service
    
    promotion_data = {
        "id": str(uuid4()),
        "tenant_id": "00000000-0000-0000-0000-000000000000",
        "pipeline_id": str(uuid4()),
        "source_environment_id": str(uuid4()),
        "target_environment_id": str(uuid4()),
        "status": "approved",
        "workflow_selections": [],
        "created_by": "00000000-0000-0000-0000-000000000000"
    }
    
    with patch.object(db_service, 'get_promotion', return_value=promotion_data):
        with patch.object(db_service, 'get_environment', return_value={
            "id": str(uuid4()),
            "base_url": "http://localhost:5678",
            "api_key": "test-key"
        }):
            response = client.post(
                f"/api/v1/promotions/execute/{promotion_data['id']}",
                headers=auth_headers
            )
            
            assert response.status_code == 400
            assert "No workflows selected" in response.json()["detail"]


@pytest.mark.asyncio
async def test_execute_promotion_invalid_status(client, auth_headers):
    """Test that executing promotion with invalid status fails"""
    from app.services.database import db_service
    
    promotion_data = {
        "id": str(uuid4()),
        "tenant_id": "00000000-0000-0000-0000-000000000000",
        "status": "completed",
        "workflow_selections": [
            {"workflow_id": str(uuid4()), "workflow_name": "Test", "selected": True}
        ]
    }
    
    with patch.object(db_service, 'get_promotion', return_value=promotion_data):
        response = client.post(
            f"/api/v1/promotions/execute/{promotion_data['id']}",
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "cannot be executed" in response.json()["detail"]

