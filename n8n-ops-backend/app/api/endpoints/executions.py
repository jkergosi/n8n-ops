from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any
from app.services.database import db_service

router = APIRouter()

# TODO: Replace with actual tenant ID from authenticated user
MOCK_TENANT_ID = "00000000-0000-0000-0000-000000000000"


@router.get("/", response_model=List[Dict[str, Any]])
async def get_executions(environment_id: str = None, workflow_id: str = None):
    """Get all executions from the database cache, optionally filtered by environment and workflow"""
    try:
        executions = await db_service.get_executions(
            MOCK_TENANT_ID,
            environment_id=environment_id,
            workflow_id=workflow_id
        )

        # Transform snake_case to camelCase for frontend
        transformed_executions = []
        for execution in executions:
            transformed_executions.append({
                "id": execution.get("id"),
                "executionId": execution.get("execution_id"),
                "workflowId": execution.get("workflow_id"),
                "workflowName": execution.get("workflow_name"),
                "status": execution.get("status"),
                "mode": execution.get("mode"),
                "startedAt": execution.get("started_at"),
                "finishedAt": execution.get("finished_at"),
                "executionTime": execution.get("execution_time"),
                "data": execution.get("data"),
                "tenantId": execution.get("tenant_id"),
                "environmentId": execution.get("environment_id"),
                "createdAt": execution.get("created_at"),
                "updatedAt": execution.get("updated_at"),
            })

        return transformed_executions

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch executions: {str(e)}"
        )


@router.get("/{execution_id}", response_model=Dict[str, Any])
async def get_execution(execution_id: str):
    """Get a specific execution by ID"""
    try:
        execution = await db_service.get_execution(execution_id, MOCK_TENANT_ID)

        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found"
            )

        # Transform snake_case to camelCase for frontend
        return {
            "id": execution.get("id"),
            "executionId": execution.get("execution_id"),
            "workflowId": execution.get("workflow_id"),
            "workflowName": execution.get("workflow_name"),
            "status": execution.get("status"),
            "mode": execution.get("mode"),
            "startedAt": execution.get("started_at"),
            "finishedAt": execution.get("finished_at"),
            "executionTime": execution.get("execution_time"),
            "data": execution.get("data"),
            "tenantId": execution.get("tenant_id"),
            "environmentId": execution.get("environment_id"),
            "createdAt": execution.get("created_at"),
            "updatedAt": execution.get("updated_at"),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch execution: {str(e)}"
        )
