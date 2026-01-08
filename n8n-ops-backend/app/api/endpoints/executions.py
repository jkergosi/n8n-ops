from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Dict, Any, Optional
from app.services.database import db_service
from app.services.auth_service import get_current_user

router = APIRouter()

# Fallback tenant ID (should not be used in production)
def get_tenant_id(user_info: dict) -> str:
    tenant = user_info.get("tenant") or {}
    tenant_id = tenant.get("id")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return tenant_id


@router.get("/", response_model=List[Dict[str, Any]])
async def get_executions(
    environment_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    user_info: dict = Depends(get_current_user)
):
    """Get all executions from the database cache, optionally filtered by environment and workflow"""
    try:
        tenant_id = get_tenant_id(user_info)
        executions = await db_service.get_executions(
            tenant_id,
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
async def get_execution(
    execution_id: str,
    user_info: dict = Depends(get_current_user)
):
    """Get a specific execution by ID"""
    try:
        tenant_id = get_tenant_id(user_info)
        execution = await db_service.get_execution(execution_id, tenant_id)

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


@router.get("/analytics", response_model=Dict[str, Any])
async def get_execution_analytics(
    environment_id: str,
    from_time: str,
    to_time: str,
    limit: int = 100,
    offset: int = 0,
    search: Optional[str] = None,
    user_info: dict = Depends(get_current_user)
):
    """
    Get execution analytics aggregated by workflow for Pro/Agency tier.
    Returns workflow health metrics from database with no live n8n queries.

    Query Parameters:
        - environment_id (required): Environment to analyze
        - from_time (required): ISO8601 UTC start timestamp
        - to_time (required): ISO8601 UTC end timestamp
        - limit (optional): Max results, default 100, max 500
        - offset (optional): Pagination offset, default 0
        - search (optional): Workflow name/ID search filter (min 3 chars)

    Returns:
        Analytics envelope with metadata and workflow metrics
    """
    import logging
    from datetime import datetime, timedelta

    logger = logging.getLogger(__name__)

    try:
        tenant_id = get_tenant_id(user_info)

        # Validate and parse timestamps
        try:
            from_dt = datetime.fromisoformat(from_time.replace('Z', '+00:00'))
            to_dt = datetime.fromisoformat(to_time.replace('Z', '+00:00'))
        except (ValueError, AttributeError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid timestamp format. Use ISO8601 UTC format: {str(e)}"
            )

        # Validate from < to
        if from_dt >= to_dt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="from_time must be before to_time"
            )

        # Enforce 30-day max time window
        time_window = to_dt - from_dt
        if time_window > timedelta(days=30):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Time window cannot exceed 30 days. Please reduce the date range."
            )

        # Cap limit at 500
        if limit > 500:
            limit = 500

        # Validate search length (must be None or >= 3 chars)
        if search is not None and len(search) < 3:
            # Skip search if < 3 chars
            search = None

        # Log analytics request for observability
        logger.info(
            f"Analytics query: tenant_id={tenant_id}, environment_id={environment_id}, "
            f"time_window_days={time_window.days}, limit={limit}, offset={offset}, "
            f"search={search}"
        )

        # Record start time for query duration logging
        query_start = datetime.utcnow()

        # Fetch analytics from database
        analytics_items = await db_service.get_execution_analytics(
            tenant_id=tenant_id,
            environment_id=environment_id,
            from_dt=from_time,
            to_dt=to_time,
            limit=limit,
            offset=offset,
            search=search
        )

        # Calculate query duration
        query_duration_ms = int((datetime.utcnow() - query_start).total_seconds() * 1000)

        # Log query performance
        logger.info(
            f"Analytics query completed: result_count={len(analytics_items)}, "
            f"query_duration_ms={query_duration_ms}"
        )

        # Build response envelope with metadata
        response = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "from": from_time,
            "to": to_time,
            "time_window_days": time_window.days,
            "items": [
                {
                    "workflowId": item["workflow_id"],
                    "workflowName": item["workflow_name"],
                    "totalRuns": item["total_runs"],
                    "successRuns": item["success_runs"],
                    "failureRuns": item["failure_runs"],
                    "successRate": item["success_rate"],
                    "avgDurationMs": item["avg_duration_ms"],
                    "p50DurationMs": item["p50_duration_ms"],
                    "p95DurationMs": item["p95_duration_ms"],
                    "lastFailureAt": item["last_failure_at"],
                    "lastFailureError": item["last_failure_error"],
                    "lastFailureNode": item["last_failure_node"]
                }
                for item in analytics_items
            ]
        }

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch execution analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch execution analytics: {str(e)}"
        )
