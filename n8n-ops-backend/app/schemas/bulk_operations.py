"""
Schemas for bulk workflow operations.

This module defines request/response schemas for executing operations
(sync, promote, snapshot) across multiple workflows simultaneously.
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from enum import Enum
from app.core.config import settings


class BulkOperationType(str, Enum):
    """Type of bulk operation to perform"""
    SYNC = "sync"
    PROMOTE = "promote"
    SNAPSHOT = "snapshot"


class BulkOperationRequest(BaseModel):
    """
    Request schema for bulk workflow operations.

    Attributes:
        workflow_ids: List of workflow IDs to operate on (max MAX_BULK_WORKFLOWS)
        operation_type: Type of operation (sync, promote, or snapshot)
    """
    workflow_ids: List[str] = Field(
        ...,
        min_length=1,
        description=f"List of workflow IDs to operate on (1-{settings.MAX_BULK_WORKFLOWS} workflows)"
    )
    operation_type: BulkOperationType = Field(
        ...,
        description="Type of bulk operation to perform"
    )

    @field_validator('workflow_ids')
    @classmethod
    def validate_workflow_ids(cls, v: List[str]) -> List[str]:
        """Validate workflow_ids list"""
        if not v:
            raise ValueError("workflow_ids cannot be empty")
        if len(v) > settings.MAX_BULK_WORKFLOWS:
            raise ValueError(f"Exceeded maximum batch size of {settings.MAX_BULK_WORKFLOWS} workflows")
        # Remove duplicates while preserving order
        seen = set()
        unique_ids = []
        for wf_id in v:
            if wf_id not in seen:
                seen.add(wf_id)
                unique_ids.append(wf_id)
        return unique_ids


class BulkOperationResponse(BaseModel):
    """
    Response schema for initiated bulk workflow operations.

    Attributes:
        job_id: Background job ID for tracking operation progress
        status: Current job status (pending, running, completed, failed, cancelled)
        total_workflows: Total number of workflows in the bulk operation
        completed: Number of workflows completed so far (initially 0)
        failed: Number of workflows that failed (initially 0)
        succeeded: Number of workflows that succeeded (initially 0)
    """
    job_id: str = Field(
        ...,
        description="Background job ID for tracking the bulk operation"
    )
    status: str = Field(
        ...,
        description="Current status of the background job"
    )
    total_workflows: int = Field(
        ...,
        ge=0,
        description="Total number of workflows in this bulk operation"
    )
    completed: int = Field(
        default=0,
        ge=0,
        description="Number of workflows completed (initially 0)"
    )
    failed: int = Field(
        default=0,
        ge=0,
        description="Number of workflows that failed (initially 0)"
    )
    succeeded: int = Field(
        default=0,
        ge=0,
        description="Number of workflows that succeeded (initially 0)"
    )


class BulkOperationResult(BaseModel):
    """
    Per-workflow status tracking for bulk operations.

    This schema captures the success/failure status of individual workflows
    within a bulk operation, enabling granular error reporting and allowing
    users to identify and re-submit failed items.

    Attributes:
        workflow_id: The workflow ID that was operated on
        success: Whether the operation succeeded for this workflow
        error_message: Error details if the operation failed (None if success=True)
    """
    workflow_id: str = Field(
        ...,
        description="The workflow ID that was operated on"
    )
    success: bool = Field(
        ...,
        description="Whether the operation succeeded for this workflow"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if operation failed (None if successful)"
    )


class BulkOperationJobStatus(BaseModel):
    """
    Complete job status for a bulk operation.

    This schema provides full details about a bulk operation job including
    overall status, progress, and per-workflow results.

    Attributes:
        job_id: Background job ID
        status: Current job status (pending, running, completed, failed, cancelled)
        total_workflows: Total number of workflows in the bulk operation
        completed: Number of workflows completed so far
        succeeded: Number of workflows that succeeded
        failed: Number of workflows that failed
        results: List of per-workflow results (only populated when job is completed/failed)
        progress_message: Current progress message
        created_at: Timestamp when job was created
        updated_at: Timestamp when job was last updated
        metadata: Additional job metadata (operation_type, environment_id, etc.)
    """
    job_id: str = Field(
        ...,
        description="Background job ID"
    )
    status: str = Field(
        ...,
        description="Current status of the background job"
    )
    total_workflows: int = Field(
        ...,
        ge=0,
        description="Total number of workflows in this bulk operation"
    )
    completed: int = Field(
        default=0,
        ge=0,
        description="Number of workflows completed so far"
    )
    succeeded: int = Field(
        default=0,
        ge=0,
        description="Number of workflows that succeeded"
    )
    failed: int = Field(
        default=0,
        ge=0,
        description="Number of workflows that failed"
    )
    results: List[BulkOperationResult] = Field(
        default_factory=list,
        description="Per-workflow results (populated when job completes)"
    )
    progress_message: Optional[str] = Field(
        default=None,
        description="Current progress message"
    )
    created_at: Optional[str] = Field(
        default=None,
        description="Timestamp when job was created"
    )
    updated_at: Optional[str] = Field(
        default=None,
        description="Timestamp when job was last updated"
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Additional job metadata"
    )
