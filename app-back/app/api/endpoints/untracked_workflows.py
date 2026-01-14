"""
API endpoints for untracked workflow detection and onboarding.

Endpoints:
- GET /api/v1/canonical/untracked - Get all untracked workflows
- POST /api/v1/canonical/untracked/scan - Scan environments for untracked workflows
- POST /api/v1/canonical/untracked/onboard - Onboard selected workflows
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
import logging

from app.schemas.untracked_workflow import (
    UntrackedWorkflowsResponse,
    OnboardWorkflowsRequest,
    OnboardWorkflowsResponse,
    ScanEnvironmentsResponse,
)
from app.services.untracked_workflows_service import UntrackedWorkflowsService
from app.core.entitlements_gate import require_entitlement
from app.services.auth_service import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


def get_tenant_id(user_info: dict) -> str:
    """Extract tenant_id from user_info."""
    tenant = user_info.get("tenant") or {}
    tenant_id = tenant.get("id")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return tenant_id


def get_user_id(user_info: dict) -> str:
    """Extract user_id from user_info."""
    user = user_info.get("user") or {}
    return user.get("id")


@router.get("/untracked", response_model=UntrackedWorkflowsResponse)
async def get_untracked_workflows(
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("workflow_read"))
):
    """
    Get all untracked workflows across environments.

    Returns cached data from workflow_env_map where canonical_id is NULL.
    Call POST /untracked/scan first to refresh the data from n8n.
    """
    tenant_id = get_tenant_id(user_info)

    try:
        result = await UntrackedWorkflowsService.get_untracked_workflows(tenant_id)
        return result
    except Exception as e:
        logger.error(f"Failed to get untracked workflows: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get untracked workflows: {str(e)}"
        )


@router.post("/untracked/scan", response_model=ScanEnvironmentsResponse)
async def scan_environments(
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("environment_basic"))
):
    """
    Scan all active environments for untracked workflows.

    This performs a live scan of each n8n environment, diffs against
    workflow_env_map, and creates rows for any workflows not yet mapped.

    Partial failure handling: Each environment is scanned independently.
    Failure in one environment does not affect others.
    """
    tenant_id = get_tenant_id(user_info)

    try:
        result = await UntrackedWorkflowsService.scan_environments(tenant_id)
        return result
    except Exception as e:
        logger.error(f"Failed to scan environments: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scan environments: {str(e)}"
        )


@router.post("/untracked/onboard", response_model=OnboardWorkflowsResponse)
async def onboard_workflows(
    request: OnboardWorkflowsRequest,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("workflow_push"))
):
    """
    Onboard selected untracked workflows into the canonical system.

    For each workflow:
    - If already mapped: returns status='skipped' (idempotent)
    - If not mapped: creates canonical workflow and mapping, returns status='onboarded'
    - If error: returns status='failed' with reason

    Bulk operation returns partial results - some may succeed while others fail.
    """
    tenant_id = get_tenant_id(user_info)
    user_id = get_user_id(user_info)

    if not request.workflows:
        return OnboardWorkflowsResponse(
            results=[],
            total_onboarded=0,
            total_skipped=0,
            total_failed=0
        )

    try:
        # Convert Pydantic models to dicts
        workflows_list = [
            {"environment_id": w.environment_id, "n8n_workflow_id": w.n8n_workflow_id}
            for w in request.workflows
        ]

        result = await UntrackedWorkflowsService.onboard_workflows(
            tenant_id=tenant_id,
            workflows=workflows_list,
            created_by_user_id=user_id
        )
        return result
    except Exception as e:
        logger.error(f"Failed to onboard workflows: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to onboard workflows: {str(e)}"
        )
