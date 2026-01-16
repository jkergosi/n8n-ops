"""
Git-Based Promotions API

New promotion endpoints using Git snapshot system with target-ownership model.

Endpoints:
Promotions:
- POST /git-promotions/initiate - Start a promotion
- POST /git-promotions/{id}/approve - Approve a pending promotion
- POST /git-promotions/{id}/reject - Reject a pending promotion
- GET /git-promotions/{id} - Get promotion status
- GET /git-promotions - List promotions

Rollbacks:
- POST /git-promotions/rollback/initiate - Start a rollback
- POST /git-promotions/rollback/{id}/approve - Approve a pending rollback
- POST /git-promotions/rollback/{id}/reject - Reject a pending rollback
- GET /git-promotions/environments/{id}/snapshots - List available snapshots
- GET /git-promotions/environments/{id}/current - Get current snapshot info

Backups:
- POST /git-promotions/backup/create - Create a backup snapshot
- GET /git-promotions/backups - List backup records
"""
import logging
from typing import Optional, List
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException, status, Depends, Query

from app.services.auth_service import get_current_user
from app.services.database import db_service
from app.services.git_promotion_service import (
    git_promotion_service,
    PromotionRequest,
    PromotionResult,
    PromotionStatus,
    RollbackRequest,
    RollbackResult,
)
from app.core.entitlements_gate import require_entitlement

logger = logging.getLogger(__name__)

router = APIRouter()


def get_tenant_id(user_info: dict) -> str:
    tenant = user_info.get("tenant") or {}
    tenant_id = tenant.get("id")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return tenant_id


class InitiatePromotionRequest(BaseModel):
    """Request to initiate a new promotion."""
    source_environment_id: str = Field(..., description="Source environment ID")
    target_environment_id: str = Field(..., description="Target environment ID")
    workflow_ids: List[str] = Field(default_factory=list, description="Workflow IDs to promote (empty = all)")
    reason: Optional[str] = Field(None, description="Reason for promotion")


class PromotionResponse(BaseModel):
    """Response for promotion operations."""
    success: bool
    promotion_id: str
    snapshot_id: Optional[str] = None
    commit_sha: Optional[str] = None
    status: str
    workflows_promoted: int = 0
    error: Optional[str] = None
    requires_approval: bool = False
    verification_passed: bool = False
    pointer_updated: bool = False


def _to_response(result: PromotionResult) -> PromotionResponse:
    """Convert PromotionResult to API response."""
    return PromotionResponse(
        success=result.success,
        promotion_id=result.promotion_id,
        snapshot_id=result.snapshot_id,
        commit_sha=result.commit_sha,
        status=result.status.value,
        workflows_promoted=result.workflows_promoted,
        error=result.error,
        requires_approval=result.requires_approval,
        verification_passed=result.verification_passed,
        pointer_updated=result.pointer_updated,
    )


@router.post("/initiate", response_model=PromotionResponse)
async def initiate_promotion(
    request: InitiatePromotionRequest,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("workflow_ci_cd"))
):
    """
    Initiate a new Git-based promotion.

    This creates a snapshot in the target environment's Git folder and either:
    - Completes the deployment (for non-PROD targets)
    - Returns PENDING_APPROVAL (for PROD targets)

    Key behaviors:
    - Snapshots are owned by TARGET environment
    - Snapshot is committed BEFORE any target mutations
    - Pointer is updated ONLY after successful deploy + verify
    - PROD targets always require approval
    """
    try:
        tenant_id = get_tenant_id(user_info)
        user = user_info.get("user", {})
        user_id = user.get("id")

        promotion_request = PromotionRequest(
            tenant_id=tenant_id,
            source_env_id=request.source_environment_id,
            target_env_id=request.target_environment_id,
            workflow_ids=request.workflow_ids,
            user_id=user_id,
            reason=request.reason,
        )

        result = await git_promotion_service.initiate_promotion(promotion_request)

        if not result.success and result.status == PromotionStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error or "Promotion failed"
            )

        return _to_response(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to initiate promotion: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate promotion: {str(e)}"
        )


@router.post("/{promotion_id}/approve", response_model=PromotionResponse)
async def approve_promotion(
    promotion_id: str,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("workflow_ci_cd"))
):
    """
    Approve a pending promotion and execute deployment.

    Only applicable to promotions with status PENDING_APPROVAL.
    This will deploy the snapshot to the target environment and
    update the environment pointer.
    """
    try:
        tenant_id = get_tenant_id(user_info)
        user = user_info.get("user", {})
        user_id = user.get("id")

        # TODO: Check user has approval permissions (admin role)

        result = await git_promotion_service.approve_and_execute(
            tenant_id=tenant_id,
            promotion_id=promotion_id,
            approved_by=user_id,
        )

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error or "Approval failed"
            )

        return _to_response(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve promotion: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve promotion: {str(e)}"
        )


@router.post("/{promotion_id}/reject")
async def reject_promotion(
    promotion_id: str,
    reason: Optional[str] = None,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("workflow_ci_cd"))
):
    """
    Reject a pending promotion.

    The snapshot remains in Git but the deployment is not executed.
    """
    try:
        tenant_id = get_tenant_id(user_info)
        user = user_info.get("user", {})
        user_id = user.get("id")

        # Update status to rejected
        try:
            db_service.client.table("deployments").update({
                "status": PromotionStatus.REJECTED.value,
                "rejected_by_user_id": user_id,
                "rejection_reason": reason,
            }).eq("id", promotion_id).eq("tenant_id", tenant_id).execute()
        except Exception as e:
            logger.warning(f"Failed to update rejection status: {e}")

        return {
            "success": True,
            "promotion_id": promotion_id,
            "status": "rejected",
            "message": "Promotion rejected",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reject promotion: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject promotion: {str(e)}"
        )


@router.get("/backups")
async def list_backups(
    environment_id: Optional[str] = Query(None),
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("workflow_ci_cd"))
):
    """
    List backup records.

    Optionally filter by environment_id.
    """
    try:
        tenant_id = get_tenant_id(user_info)

        backups = await git_promotion_service.list_backups(
            tenant_id=tenant_id,
            env_id=environment_id,
        )

        return {
            "backups": backups,
            "count": len(backups),
        }

    except Exception as e:
        logger.error(f"Failed to list backups: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list backups: {str(e)}"
        )


@router.get("/{promotion_id}")
async def get_promotion(
    promotion_id: str,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("workflow_ci_cd"))
):
    """Get promotion details."""
    try:
        tenant_id = get_tenant_id(user_info)

        result = db_service.client.table("deployments").select("*").eq(
            "id", promotion_id
        ).eq("tenant_id", tenant_id).single().execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Promotion {promotion_id} not found"
            )

        return result.data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get promotion: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get promotion: {str(e)}"
        )


@router.get("/")
async def list_promotions(
    status_filter: Optional[str] = Query(None, alias="status"),
    target_environment_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("workflow_ci_cd"))
):
    """List promotions with filtering."""
    try:
        tenant_id = get_tenant_id(user_info)

        query = db_service.client.table("deployments").select("*").eq("tenant_id", tenant_id)

        if status_filter:
            query = query.eq("status", status_filter)
        if target_environment_id:
            query = query.eq("target_environment_id", target_environment_id)

        # Pagination
        from_index = (page - 1) * page_size
        to_index = from_index + page_size - 1
        query = query.order("created_at", desc=True).range(from_index, to_index)

        result = query.execute()

        return {
            "items": result.data or [],
            "page": page,
            "page_size": page_size,
        }

    except Exception as e:
        logger.error(f"Failed to list promotions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list promotions: {str(e)}"
        )


# ============== ROLLBACK ENDPOINTS ==============

class InitiateRollbackRequest(BaseModel):
    """Request to initiate a rollback."""
    environment_id: str = Field(..., description="Environment ID to rollback")
    snapshot_id: str = Field(..., description="Target snapshot ID to rollback to")
    reason: Optional[str] = Field(None, description="Reason for rollback")


class RollbackResponse(BaseModel):
    """Response for rollback operations."""
    success: bool
    rollback_id: str
    snapshot_id: str
    commit_sha: Optional[str] = None
    status: str
    workflows_deployed: int = 0
    error: Optional[str] = None
    requires_approval: bool = False
    verification_passed: bool = False
    pointer_updated: bool = False


def _to_rollback_response(result: RollbackResult) -> RollbackResponse:
    """Convert RollbackResult to API response."""
    return RollbackResponse(
        success=result.success,
        rollback_id=result.rollback_id,
        snapshot_id=result.snapshot_id,
        commit_sha=result.commit_sha,
        status=result.status.value,
        workflows_deployed=result.workflows_deployed,
        error=result.error,
        requires_approval=result.requires_approval,
        verification_passed=result.verification_passed,
        pointer_updated=result.pointer_updated,
    )


@router.post("/rollback/initiate", response_model=RollbackResponse)
async def initiate_rollback(
    request: InitiateRollbackRequest,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("workflow_ci_cd"))
):
    """
    Initiate a rollback to a previous snapshot.

    Rollback Rules:
    - Rollback deploys a snapshot from the SAME environment
    - PROD rollback requires approval
    - STAGING/DEV rollback do not require approval

    Flow:
    1. Validate environment and snapshot exist
    2. Load snapshot content from Git
    3. If PROD: return PENDING_APPROVAL
    4. If not PROD: deploy, verify, update pointer
    """
    try:
        tenant_id = get_tenant_id(user_info)
        user = user_info.get("user", {})
        user_id = user.get("id")

        rollback_request = RollbackRequest(
            tenant_id=tenant_id,
            env_id=request.environment_id,
            snapshot_id=request.snapshot_id,
            user_id=user_id,
            reason=request.reason,
        )

        result = await git_promotion_service.initiate_rollback(rollback_request)

        if not result.success and result.status == PromotionStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error or "Rollback failed"
            )

        return _to_rollback_response(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to initiate rollback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate rollback: {str(e)}"
        )


@router.post("/rollback/{rollback_id}/approve", response_model=RollbackResponse)
async def approve_rollback(
    rollback_id: str,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("workflow_ci_cd"))
):
    """
    Approve a pending rollback and execute deployment.

    Only applicable to rollbacks with status PENDING_APPROVAL (PROD rollbacks).
    This will deploy the snapshot to the environment and update the pointer.
    """
    try:
        tenant_id = get_tenant_id(user_info)
        user = user_info.get("user", {})
        user_id = user.get("id")

        # TODO: Check user has approval permissions (admin role)

        result = await git_promotion_service.approve_and_execute_rollback(
            tenant_id=tenant_id,
            rollback_id=rollback_id,
            approved_by=user_id,
        )

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error or "Rollback approval failed"
            )

        return _to_rollback_response(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve rollback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve rollback: {str(e)}"
        )


@router.post("/rollback/{rollback_id}/reject")
async def reject_rollback(
    rollback_id: str,
    reason: Optional[str] = None,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("workflow_ci_cd"))
):
    """
    Reject a pending rollback.

    The snapshot remains in Git but the rollback is not executed.
    """
    try:
        tenant_id = get_tenant_id(user_info)
        user = user_info.get("user", {})
        user_id = user.get("id")

        # Update status to rejected
        try:
            db_service.client.table("deployments").update({
                "status": PromotionStatus.REJECTED.value,
                "rejected_by_user_id": user_id,
                "rejection_reason": reason,
            }).eq("id", rollback_id).eq("tenant_id", tenant_id).eq("operation_type", "rollback").execute()
        except Exception as e:
            logger.warning(f"Failed to update rejection status: {e}")

        return {
            "success": True,
            "rollback_id": rollback_id,
            "status": "rejected",
            "message": "Rollback rejected",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reject rollback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject rollback: {str(e)}"
        )


# ============== SNAPSHOT INFO ENDPOINTS ==============

@router.get("/environments/{environment_id}/snapshots")
async def list_environment_snapshots(
    environment_id: str,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("workflow_ci_cd"))
):
    """
    List available snapshots for an environment.

    Returns snapshots from <env>/snapshots/ directory with manifest info.
    Used for rollback selection UI.
    """
    try:
        tenant_id = get_tenant_id(user_info)

        snapshots = await git_promotion_service.get_available_snapshots(
            tenant_id=tenant_id,
            env_id=environment_id,
        )

        return {
            "environment_id": environment_id,
            "snapshots": snapshots,
            "count": len(snapshots),
        }

    except Exception as e:
        logger.error(f"Failed to list snapshots: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list snapshots: {str(e)}"
        )


@router.get("/environments/{environment_id}/current")
async def get_current_snapshot(
    environment_id: str,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("workflow_ci_cd"))
):
    """
    Get current snapshot info for an environment.

    Returns the snapshot ID and pointer info from current.json.
    Used to show current state in rollback UI.
    """
    try:
        tenant_id = get_tenant_id(user_info)

        pointer = await git_promotion_service.get_current_snapshot_info(
            tenant_id=tenant_id,
            env_id=environment_id,
        )

        if not pointer:
            return {
                "environment_id": environment_id,
                "is_onboarded": False,
                "current_snapshot_id": None,
                "pointer": None,
            }

        return {
            "environment_id": environment_id,
            "is_onboarded": True,
            "current_snapshot_id": pointer.get("current_snapshot_id"),
            "pointer": pointer,
        }

    except Exception as e:
        logger.error(f"Failed to get current snapshot: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get current snapshot: {str(e)}"
        )


# ============== BACKUP ENDPOINTS ==============

class CreateBackupRequest(BaseModel):
    """Request to create a backup."""
    environment_id: str = Field(..., description="Environment ID to backup")
    reason: Optional[str] = Field(None, description="Reason for backup")


@router.post("/backup/create")
async def create_backup(
    request: CreateBackupRequest,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("workflow_ci_cd"))
):
    """
    Create a backup snapshot for an environment.

    Backup Rules:
    - Creates snapshot with kind=backup
    - Does NOT update the environment pointer
    - Snapshot is stored under <env>/snapshots/<id>/
    - Can be restored later using the rollback endpoint
    """
    try:
        tenant_id = get_tenant_id(user_info)
        user = user_info.get("user", {})
        user_id = user.get("id")

        result = await git_promotion_service.create_backup(
            tenant_id=tenant_id,
            env_id=request.environment_id,
            user_id=user_id,
            reason=request.reason,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error") or "Backup failed"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create backup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create backup: {str(e)}"
        )
