"""
Bulk Operations API Endpoints

This module provides REST API endpoints for executing bulk workflow operations
(sync, promote, snapshot) across multiple workflows simultaneously.
"""
from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from typing import Optional
import logging

from app.schemas.bulk_operations import (
    BulkOperationRequest,
    BulkOperationResponse,
    BulkOperationType,
    BulkOperationJobStatus,
    BulkOperationResult
)
from app.services.bulk_workflow_service import bulk_workflow_service
from app.services.background_job_service import (
    background_job_service,
    BackgroundJobType,
    BackgroundJobStatus
)
from app.services.database import db_service
from app.services.auth_service import get_current_user
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


def get_tenant_id(user_info: dict) -> str:
    """Extract tenant ID from user info"""
    tenant = user_info.get("tenant") or {}
    tenant_id = tenant.get("id")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return tenant_id


def get_user_id(user_info: dict) -> str:
    """Extract user ID from user info"""
    user = user_info.get("user") or {}
    user_id = user.get("id")
    return user_id or "00000000-0000-0000-0000-000000000000"


async def _execute_bulk_sync_background(
    job_id: str,
    tenant_id: str,
    workflow_ids: list[str],
    environment_id: str,
    created_by: Optional[str] = None
):
    """Background task for executing bulk sync operation"""
    try:
        await bulk_workflow_service.execute_bulk_sync(
            tenant_id=tenant_id,
            workflow_ids=workflow_ids,
            environment_id=environment_id,
            job_id=job_id,
            created_by=created_by
        )
    except Exception as e:
        logger.error(f"Bulk sync background task failed: {str(e)}", exc_info=True)
        # Error handling is done inside execute_bulk_sync


@router.post("/sync", response_model=BulkOperationResponse)
async def bulk_sync(
    background_tasks: BackgroundTasks,
    environment_id: str,
    workflow_ids: list[str],
    user_info: dict = Depends(get_current_user)
):
    """
    Execute bulk sync operation on multiple workflows.

    Syncs workflows from their n8n environment to the database. Each workflow
    is synced independently with per-workflow error tracking.

    Args:
        environment_id: Environment ID to sync from
        workflow_ids: List of workflow IDs to sync (max 50)
        user_info: Authenticated user information

    Returns:
        BulkOperationResponse with job_id and initial status

    Raises:
        HTTPException: 400 if validation fails, 404 if environment not found
    """
    try:
        tenant_id = get_tenant_id(user_info)
        created_by = get_user_id(user_info)

        # Validate workflow_ids using the schema
        request_data = BulkOperationRequest(
            workflow_ids=workflow_ids,
            operation_type=BulkOperationType.SYNC
        )

        # Validate environment exists
        environment = await db_service.get_environment(environment_id, tenant_id)
        if not environment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Environment {environment_id} not found"
            )

        # Validate batch size (double-check even though schema validates)
        if len(request_data.workflow_ids) > settings.MAX_BULK_WORKFLOWS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exceeded maximum batch size of {settings.MAX_BULK_WORKFLOWS} workflows"
            )

        if len(request_data.workflow_ids) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No workflows selected"
            )

        # Create background job
        job = await background_job_service.create_job(
            tenant_id=tenant_id,
            job_type=BackgroundJobType.BULK_WORKFLOW_OPERATION,
            resource_id=environment_id,
            resource_type="environment",
            created_by=created_by,
            metadata={
                "operation_type": "sync",
                "environment_id": environment_id,
                "workflow_count": len(request_data.workflow_ids)
            },
            initial_progress={
                "current": 0,
                "total": len(request_data.workflow_ids),
                "percentage": 0,
                "message": f"Starting bulk sync of {len(request_data.workflow_ids)} workflow(s)..."
            }
        )

        job_id = job["id"]

        # Start background task
        background_tasks.add_task(
            _execute_bulk_sync_background,
            job_id=job_id,
            tenant_id=tenant_id,
            workflow_ids=request_data.workflow_ids,
            environment_id=environment_id,
            created_by=created_by
        )

        # Return response immediately
        return BulkOperationResponse(
            job_id=job_id,
            status=BackgroundJobStatus.PENDING,
            total_workflows=len(request_data.workflow_ids),
            completed=0,
            failed=0,
            succeeded=0
        )

    except HTTPException:
        raise
    except ValueError as e:
        # Handle validation errors from schema
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to initiate bulk sync: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate bulk sync: {str(e)}"
        )


async def _execute_bulk_promote_background(
    job_id: str,
    tenant_id: str,
    workflow_ids: list[str],
    source_environment_id: str,
    target_environment_id: str,
    created_by: Optional[str] = None
):
    """Background task for executing bulk promote operation"""
    try:
        await bulk_workflow_service.execute_bulk_promote(
            tenant_id=tenant_id,
            workflow_ids=workflow_ids,
            source_environment_id=source_environment_id,
            target_environment_id=target_environment_id,
            job_id=job_id,
            created_by=created_by
        )
    except Exception as e:
        logger.error(f"Bulk promote background task failed: {str(e)}", exc_info=True)
        # Error handling is done inside execute_bulk_promote


@router.post("/promote", response_model=BulkOperationResponse)
async def bulk_promote(
    background_tasks: BackgroundTasks,
    source_environment_id: str,
    target_environment_id: str,
    workflow_ids: list[str],
    user_info: dict = Depends(get_current_user)
):
    """
    Execute bulk promote operation on multiple workflows.

    Promotes workflows from source environment to target environment. Each workflow
    is promoted independently with per-workflow error tracking. Uses a single
    source/target environment pair for all workflows in the batch.

    Args:
        source_environment_id: Source environment ID to promote from
        target_environment_id: Target environment ID to promote to
        workflow_ids: List of workflow IDs to promote (max 50)
        user_info: Authenticated user information

    Returns:
        BulkOperationResponse with job_id and initial status

    Raises:
        HTTPException: 400 if validation fails, 404 if environment not found
    """
    try:
        tenant_id = get_tenant_id(user_info)
        created_by = get_user_id(user_info)

        # Validate workflow_ids using the schema
        request_data = BulkOperationRequest(
            workflow_ids=workflow_ids,
            operation_type=BulkOperationType.PROMOTE
        )

        # Validate source and target environments exist
        source_env = await db_service.get_environment(source_environment_id, tenant_id)
        if not source_env:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source environment {source_environment_id} not found"
            )

        target_env = await db_service.get_environment(target_environment_id, tenant_id)
        if not target_env:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Target environment {target_environment_id} not found"
            )

        # Validate environments are different
        if source_environment_id == target_environment_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source and target environments must be different"
            )

        # Validate batch size (double-check even though schema validates)
        if len(request_data.workflow_ids) > settings.MAX_BULK_WORKFLOWS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exceeded maximum batch size of {settings.MAX_BULK_WORKFLOWS} workflows"
            )

        if len(request_data.workflow_ids) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No workflows selected"
            )

        # Create background job
        job = await background_job_service.create_job(
            tenant_id=tenant_id,
            job_type=BackgroundJobType.BULK_WORKFLOW_OPERATION,
            resource_id=source_environment_id,
            resource_type="environment",
            created_by=created_by,
            metadata={
                "operation_type": "promote",
                "source_environment_id": source_environment_id,
                "target_environment_id": target_environment_id,
                "workflow_count": len(request_data.workflow_ids)
            },
            initial_progress={
                "current": 0,
                "total": len(request_data.workflow_ids),
                "percentage": 0,
                "message": f"Starting bulk promote of {len(request_data.workflow_ids)} workflow(s)..."
            }
        )

        job_id = job["id"]

        # Start background task
        background_tasks.add_task(
            _execute_bulk_promote_background,
            job_id=job_id,
            tenant_id=tenant_id,
            workflow_ids=request_data.workflow_ids,
            source_environment_id=source_environment_id,
            target_environment_id=target_environment_id,
            created_by=created_by
        )

        # Return response immediately
        return BulkOperationResponse(
            job_id=job_id,
            status=BackgroundJobStatus.PENDING,
            total_workflows=len(request_data.workflow_ids),
            completed=0,
            failed=0,
            succeeded=0
        )

    except HTTPException:
        raise
    except ValueError as e:
        # Handle validation errors from schema
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to initiate bulk promote: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate bulk promote: {str(e)}"
        )


async def _execute_bulk_snapshot_background(
    job_id: str,
    tenant_id: str,
    workflow_ids: list[str],
    environment_id: str,
    created_by: Optional[str] = None,
    reason: Optional[str] = None,
    notes: Optional[str] = None
):
    """Background task for executing bulk snapshot operation"""
    try:
        await bulk_workflow_service.execute_bulk_snapshot(
            tenant_id=tenant_id,
            workflow_ids=workflow_ids,
            environment_id=environment_id,
            job_id=job_id,
            created_by=created_by,
            reason=reason,
            notes=notes
        )
    except Exception as e:
        logger.error(f"Bulk snapshot background task failed: {str(e)}", exc_info=True)
        # Error handling is done inside execute_bulk_snapshot


@router.post("/snapshot", response_model=BulkOperationResponse)
async def bulk_snapshot(
    background_tasks: BackgroundTasks,
    environment_id: str,
    workflow_ids: list[str],
    reason: Optional[str] = None,
    notes: Optional[str] = None,
    user_info: dict = Depends(get_current_user)
):
    """
    Execute bulk snapshot operation on multiple workflows.

    Creates one snapshot per workflow, exporting each to Git independently.
    Each workflow snapshot is created with per-workflow error tracking.

    Args:
        environment_id: Environment ID to snapshot from
        workflow_ids: List of workflow IDs to snapshot (max 50)
        reason: Optional reason for creating the snapshots
        notes: Optional notes for the snapshots
        user_info: Authenticated user information

    Returns:
        BulkOperationResponse with job_id and initial status

    Raises:
        HTTPException: 400 if validation fails, 404 if environment not found
    """
    try:
        tenant_id = get_tenant_id(user_info)
        created_by = get_user_id(user_info)

        # Validate workflow_ids using the schema
        request_data = BulkOperationRequest(
            workflow_ids=workflow_ids,
            operation_type=BulkOperationType.SNAPSHOT
        )

        # Validate environment exists
        environment = await db_service.get_environment(environment_id, tenant_id)
        if not environment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Environment {environment_id} not found"
            )

        # Validate batch size (double-check even though schema validates)
        if len(request_data.workflow_ids) > settings.MAX_BULK_WORKFLOWS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exceeded maximum batch size of {settings.MAX_BULK_WORKFLOWS} workflows"
            )

        if len(request_data.workflow_ids) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No workflows selected"
            )

        # Create background job
        job = await background_job_service.create_job(
            tenant_id=tenant_id,
            job_type=BackgroundJobType.BULK_WORKFLOW_OPERATION,
            resource_id=environment_id,
            resource_type="environment",
            created_by=created_by,
            metadata={
                "operation_type": "snapshot",
                "environment_id": environment_id,
                "workflow_count": len(request_data.workflow_ids),
                "reason": reason,
                "notes": notes
            },
            initial_progress={
                "current": 0,
                "total": len(request_data.workflow_ids),
                "percentage": 0,
                "message": f"Starting bulk snapshot of {len(request_data.workflow_ids)} workflow(s)..."
            }
        )

        job_id = job["id"]

        # Start background task
        background_tasks.add_task(
            _execute_bulk_snapshot_background,
            job_id=job_id,
            tenant_id=tenant_id,
            workflow_ids=request_data.workflow_ids,
            environment_id=environment_id,
            created_by=created_by,
            reason=reason,
            notes=notes
        )

        # Return response immediately
        return BulkOperationResponse(
            job_id=job_id,
            status=BackgroundJobStatus.PENDING,
            total_workflows=len(request_data.workflow_ids),
            completed=0,
            failed=0,
            succeeded=0
        )

    except HTTPException:
        raise
    except ValueError as e:
        # Handle validation errors from schema
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to initiate bulk snapshot: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate bulk snapshot: {str(e)}"
        )


@router.get("/jobs/{job_id}", response_model=BulkOperationJobStatus)
async def get_bulk_operation_status(
    job_id: str,
    user_info: dict = Depends(get_current_user)
):
    """
    Get the status of a bulk operation job.

    Retrieves the current status, progress, and per-workflow results for a
    bulk operation job. The results list is populated once the job completes
    (successfully or with failures).

    Args:
        job_id: Background job ID returned from POST endpoints
        user_info: Authenticated user information

    Returns:
        BulkOperationJobStatus with current status and results

    Raises:
        HTTPException: 404 if job not found or doesn't belong to tenant
    """
    try:
        tenant_id = get_tenant_id(user_info)

        # Retrieve the background job
        job = await background_job_service.get_job(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

        # Verify job belongs to the tenant
        if job.get("tenant_id") != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

        # Verify this is a bulk workflow operation job
        if job.get("job_type") != BackgroundJobType.BULK_WORKFLOW_OPERATION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job is not a bulk workflow operation"
            )

        # Extract job metadata and progress
        metadata = job.get("metadata") or {}
        progress = job.get("progress") or {}
        result = job.get("result") or {}

        # Get total workflows from metadata (set during job creation)
        total_workflows = metadata.get("workflow_count", 0)

        # Get current counts from progress/result
        completed = result.get("completed", progress.get("current", 0))
        succeeded = result.get("succeeded", progress.get("succeeded", 0))
        failed = result.get("failed", progress.get("failed", 0))

        # Get per-workflow results (only populated when job completes/fails)
        results_data = result.get("results", [])

        # Convert results to BulkOperationResult objects
        results = [
            BulkOperationResult(
                workflow_id=r.get("workflow_id", ""),
                success=r.get("success", False),
                error_message=r.get("error_message")
            )
            for r in results_data
        ]

        # Get progress message
        progress_message = progress.get("message")

        # Build and return response
        return BulkOperationJobStatus(
            job_id=job_id,
            status=job.get("status", "unknown"),
            total_workflows=total_workflows,
            completed=completed,
            succeeded=succeeded,
            failed=failed,
            results=results,
            progress_message=progress_message,
            created_at=job.get("created_at"),
            updated_at=job.get("updated_at"),
            metadata=metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get bulk operation status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get bulk operation status: {str(e)}"
        )
