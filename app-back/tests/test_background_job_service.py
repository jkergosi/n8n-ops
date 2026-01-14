"""
Tests for background job service
"""
import pytest
from uuid import uuid4
from app.services.background_job_service import (
    background_job_service,
    BackgroundJobStatus,
    BackgroundJobType
)


@pytest.mark.asyncio
async def test_create_job():
    """Test creating a background job"""
    tenant_id = str(uuid4())
    job = await background_job_service.create_job(
        tenant_id=tenant_id,
        job_type=BackgroundJobType.PROMOTION_EXECUTE,
        resource_id=str(uuid4()),
        resource_type="promotion",
        initial_progress={"current": 0, "total": 10}
    )
    
    assert job is not None
    assert job["tenant_id"] == tenant_id
    assert job["job_type"] == BackgroundJobType.PROMOTION_EXECUTE
    assert job["status"] == BackgroundJobStatus.PENDING
    assert job["progress"]["current"] == 0
    assert job["progress"]["total"] == 10


@pytest.mark.asyncio
async def test_update_job_status():
    """Test updating job status"""
    tenant_id = str(uuid4())
    job = await background_job_service.create_job(
        tenant_id=tenant_id,
        job_type=BackgroundJobType.PROMOTION_EXECUTE,
        resource_id=str(uuid4()),
        resource_type="promotion"
    )
    job_id = job["id"]
    
    # Update to running
    updated = await background_job_service.update_job_status(
        job_id=job_id,
        status=BackgroundJobStatus.RUNNING,
        progress={"current": 5, "total": 10, "message": "Processing"}
    )
    
    assert updated["status"] == BackgroundJobStatus.RUNNING
    assert updated["started_at"] is not None
    assert updated["progress"]["current"] == 5
    assert updated["progress"]["message"] == "Processing"
    
    # Update to completed
    updated = await background_job_service.update_job_status(
        job_id=job_id,
        status=BackgroundJobStatus.COMPLETED,
        result={"success": True, "items_processed": 10}
    )
    
    assert updated["status"] == BackgroundJobStatus.COMPLETED
    assert updated["completed_at"] is not None
    assert updated["result"]["success"] is True


@pytest.mark.asyncio
async def test_update_progress():
    """Test updating job progress"""
    tenant_id = str(uuid4())
    job = await background_job_service.create_job(
        tenant_id=tenant_id,
        job_type=BackgroundJobType.PROMOTION_EXECUTE,
        resource_id=str(uuid4()),
        resource_type="promotion"
    )
    job_id = job["id"]
    
    # Update progress
    updated = await background_job_service.update_progress(
        job_id=job_id,
        current=3,
        total=10,
        message="Processing workflow 3"
    )
    
    assert updated["status"] == BackgroundJobStatus.RUNNING
    assert updated["progress"]["current"] == 3
    assert updated["progress"]["total"] == 10
    assert updated["progress"]["percentage"] == 30.0
    assert updated["progress"]["message"] == "Processing workflow 3"


@pytest.mark.asyncio
async def test_get_job():
    """Test getting a job by ID"""
    tenant_id = str(uuid4())
    job = await background_job_service.create_job(
        tenant_id=tenant_id,
        job_type=BackgroundJobType.PROMOTION_EXECUTE,
        resource_id=str(uuid4()),
        resource_type="promotion"
    )
    job_id = job["id"]
    
    retrieved = await background_job_service.get_job(job_id)
    
    assert retrieved is not None
    assert retrieved["id"] == job_id
    assert retrieved["job_type"] == BackgroundJobType.PROMOTION_EXECUTE


@pytest.mark.asyncio
async def test_get_jobs_by_resource():
    """Test getting jobs for a resource"""
    tenant_id = str(uuid4())
    resource_id = str(uuid4())
    
    # Create multiple jobs for the same resource
    job1 = await background_job_service.create_job(
        tenant_id=tenant_id,
        job_type=BackgroundJobType.PROMOTION_EXECUTE,
        resource_id=resource_id,
        resource_type="promotion"
    )
    
    job2 = await background_job_service.create_job(
        tenant_id=tenant_id,
        job_type=BackgroundJobType.PROMOTION_EXECUTE,
        resource_id=resource_id,
        resource_type="promotion"
    )
    
    jobs = await background_job_service.get_jobs_by_resource(
        resource_type="promotion",
        resource_id=resource_id,
        tenant_id=tenant_id
    )
    
    assert len(jobs) >= 2
    assert jobs[0]["id"] == job2["id"]  # Should be ordered by created_at DESC
    assert jobs[1]["id"] == job1["id"]


@pytest.mark.asyncio
async def test_get_latest_job_by_resource():
    """Test getting the latest job for a resource"""
    tenant_id = str(uuid4())
    resource_id = str(uuid4())
    
    job1 = await background_job_service.create_job(
        tenant_id=tenant_id,
        job_type=BackgroundJobType.PROMOTION_EXECUTE,
        resource_id=resource_id,
        resource_type="promotion"
    )
    
    job2 = await background_job_service.create_job(
        tenant_id=tenant_id,
        job_type=BackgroundJobType.PROMOTION_EXECUTE,
        resource_id=resource_id,
        resource_type="promotion"
    )
    
    latest = await background_job_service.get_latest_job_by_resource(
        resource_type="promotion",
        resource_id=resource_id,
        tenant_id=tenant_id
    )
    
    assert latest is not None
    assert latest["id"] == job2["id"]  # Should be the most recent


@pytest.mark.asyncio
async def test_cancel_job():
    """Test cancelling a job"""
    tenant_id = str(uuid4())
    job = await background_job_service.create_job(
        tenant_id=tenant_id,
        job_type=BackgroundJobType.PROMOTION_EXECUTE,
        resource_id=str(uuid4()),
        resource_type="promotion"
    )
    job_id = job["id"]
    
    # Update to running first
    await background_job_service.update_job_status(
        job_id=job_id,
        status=BackgroundJobStatus.RUNNING
    )
    
    # Cancel it
    cancelled = await background_job_service.cancel_job(job_id)
    
    assert cancelled["status"] == BackgroundJobStatus.CANCELLED
    assert cancelled["error_message"] == "Job cancelled by user"


@pytest.mark.asyncio
async def test_cancel_job_invalid_status():
    """Test that cancelling a completed job fails"""
    tenant_id = str(uuid4())
    job = await background_job_service.create_job(
        tenant_id=tenant_id,
        job_type=BackgroundJobType.PROMOTION_EXECUTE,
        resource_id=str(uuid4()),
        resource_type="promotion"
    )
    job_id = job["id"]
    
    # Complete the job
    await background_job_service.update_job_status(
        job_id=job_id,
        status=BackgroundJobStatus.COMPLETED
    )
    
    # Try to cancel - should fail
    with pytest.raises(ValueError, match="Cannot cancel job"):
        await background_job_service.cancel_job(job_id)


@pytest.mark.asyncio
async def test_job_progress_calculation():
    """Test that percentage is calculated correctly"""
    tenant_id = str(uuid4())
    job = await background_job_service.create_job(
        tenant_id=tenant_id,
        job_type=BackgroundJobType.PROMOTION_EXECUTE,
        resource_id=str(uuid4()),
        resource_type="promotion"
    )
    job_id = job["id"]
    
    # Update progress without percentage
    updated = await background_job_service.update_progress(
        job_id=job_id,
        current=7,
        total=10
    )
    
    assert updated["progress"]["percentage"] == 70.0
    
    # Update with explicit percentage
    updated = await background_job_service.update_progress(
        job_id=job_id,
        current=8,
        total=10,
        percentage=80.5
    )
    
    assert updated["progress"]["percentage"] == 80.5

