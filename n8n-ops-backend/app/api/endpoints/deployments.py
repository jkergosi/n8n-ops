from fastapi import APIRouter, HTTPException, status, Query, Depends, Request
from typing import Optional, List
from datetime import datetime, timedelta
from app.services.database import db_service
from app.schemas.deployment import (
    DeploymentResponse,
    DeploymentDetailResponse,
    DeploymentListResponse,
    DeploymentStatus,
    DeploymentWorkflowResponse,
    SnapshotResponse,
)
from app.core.entitlements_gate import require_entitlement
from app.services.background_job_service import background_job_service
from app.services.auth_service import get_current_user
from app.api.endpoints.admin_audit import create_audit_log

router = APIRouter()


# Entitlement gates for CI/CD features

# TODO: Replace with actual tenant ID from authenticated user
MOCK_TENANT_ID = "00000000-0000-0000-0000-000000000000"


@router.get("/", response_model=DeploymentListResponse)
async def get_deployments(
    status: Optional[DeploymentStatus] = Query(None, alias="status"),
    pipeline_id: Optional[str] = Query(None),
    environment_id: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    _: dict = Depends(require_entitlement("workflow_ci_cd"))
):
    """
    Get list of deployments with filtering and pagination.
    Returns summary counts for cards.
    """
    try:
        # Build query - exclude deleted deployments by default
        query = db_service.client.table("deployments").select("*").eq("tenant_id", MOCK_TENANT_ID).is_("deleted_at", "null")

        if status:
            query = query.eq("status", status.value)
        if pipeline_id:
            query = query.eq("pipeline_id", pipeline_id)
        if environment_id:
            query = query.or_(
                f"source_environment_id.eq.{environment_id},target_environment_id.eq.{environment_id}"
            )
        if from_date:
            query = query.gte("started_at", from_date.isoformat())
        if to_date:
            query = query.lte("started_at", to_date.isoformat())

        # Get total count
        count_result = query.execute()
        total = len(count_result.data) if count_result.data else 0

        # Apply pagination
        from_index = (page - 1) * page_size
        to_index = from_index + page_size
        query = query.order("started_at", desc=True).range(from_index, to_index - 1)

        result = query.execute()
        deployments_data = result.data or []

        # Calculate this week success count
        week_ago = datetime.utcnow() - timedelta(days=7)
        this_week_query = (
            db_service.client.table("deployments")
            .select("id")
            .eq("tenant_id", MOCK_TENANT_ID)
            .eq("status", DeploymentStatus.SUCCESS.value)
            .gte("started_at", week_ago.isoformat())
        )
        this_week_result = this_week_query.execute()
        this_week_success_count = len(this_week_result.data) if this_week_result.data else 0

        # Pending approvals count (can be 0 in v1)
        pending_approvals_count = 0

        # Convert to response models
        deployments = [
            DeploymentResponse(**deployment) for deployment in deployments_data
        ]

        return DeploymentListResponse(
            deployments=deployments,
            total=total,
            page=page,
            page_size=page_size,
            this_week_success_count=this_week_success_count,
            pending_approvals_count=pending_approvals_count,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch deployments: {str(e)}",
        )


@router.get("/{deployment_id}", response_model=DeploymentDetailResponse)
async def get_deployment(
    deployment_id: str,
    _: dict = Depends(require_entitlement("workflow_ci_cd"))
):
    """
    Get deployment details including workflows and linked snapshots.
    """
    try:
        # Get deployment - exclude deleted deployments
        deployment_result = (
            db_service.client.table("deployments")
            .select("*")
            .eq("id", deployment_id)
            .eq("tenant_id", MOCK_TENANT_ID)
            .is_("deleted_at", "null")
            .single()
            .execute()
        )

        if not deployment_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deployment {deployment_id} not found",
            )

        deployment = DeploymentResponse(**deployment_result.data)

        # Get deployment workflows
        workflows_result = (
            db_service.client.table("deployment_workflows")
            .select("*")
            .eq("deployment_id", deployment_id)
            .execute()
        )
        workflows = [
            DeploymentWorkflowResponse(**wf) for wf in (workflows_result.data or [])
        ]
        
        # If deployment is running, try to get job status for more details
        # Find the promotion associated with this deployment and get its job
        job_status = None
        if deployment.status == DeploymentStatus.RUNNING.value:
            try:
                # Find promotion that matches this deployment
                promotion_result = (
                    db_service.client.table("promotions")
                    .select("id")
                    .eq("tenant_id", MOCK_TENANT_ID)
                    .eq("source_environment_id", deployment.source_environment_id)
                    .eq("target_environment_id", deployment.target_environment_id)
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if promotion_result.data:
                    promotion_id = promotion_result.data[0].get("id")
                    job = await background_job_service.get_latest_job_by_resource(
                        resource_type="promotion",
                        resource_id=promotion_id,
                        tenant_id=MOCK_TENANT_ID
                    )
                    # Verify this job is for this deployment by checking result.deployment_id
                    if job and job.get("result", {}).get("deployment_id") == deployment_id:
                        job_status = {
                            "status": job.get("status"),
                            "progress": job.get("progress", {}),
                            "error_message": job.get("error_message")
                        }
            except Exception:
                # If we can't get job status, continue without it
                pass

        # Get pre snapshot if exists
        pre_snapshot = None
        if deployment.pre_snapshot_id:
            pre_snapshot_result = (
                db_service.client.table("snapshots")
                .select("*")
                .eq("id", deployment.pre_snapshot_id)
                .single()
                .execute()
            )
            if pre_snapshot_result.data:
                pre_snapshot = SnapshotResponse(**pre_snapshot_result.data)

        # Get post snapshot if exists
        post_snapshot = None
        if deployment.post_snapshot_id:
            post_snapshot_result = (
                db_service.client.table("snapshots")
                .select("*")
                .eq("id", deployment.post_snapshot_id)
                .single()
                .execute()
            )
            if post_snapshot_result.data:
                post_snapshot = SnapshotResponse(**post_snapshot_result.data)

        return DeploymentDetailResponse(
            **deployment.model_dump(),
            workflows=workflows,
            pre_snapshot=pre_snapshot,
            post_snapshot=post_snapshot,
        )

    except HTTPException:
        raise
    except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch deployment: {str(e)}",
            )


@router.delete("/{deployment_id}")
async def delete_deployment(
    deployment_id: str,
    request: Request,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("workflow_ci_cd"))
):
    """
    Soft delete a deployment.
    
    Restrictions:
    - Cannot delete running deployments
    - Cannot delete deployments less than 7 days old
    """
    try:
        # Get deployment
        deployment_result = (
            db_service.client.table("deployments")
            .select("*")
            .eq("id", deployment_id)
            .eq("tenant_id", MOCK_TENANT_ID)
            .single()
            .execute()
        )

        if not deployment_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deployment {deployment_id} not found",
            )

        deployment = deployment_result.data
        
        # Check if already deleted
        if deployment.get("deleted_at"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Deployment is already deleted"
            )

        # Check restrictions
        if deployment.get("status") == DeploymentStatus.RUNNING.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a running deployment"
            )

        # Check age restriction (7 days)
        started_at = deployment.get("started_at")
        if started_at:
            started_datetime = datetime.fromisoformat(started_at.replace('Z', '+00:00')) if isinstance(started_at, str) else started_at
            age_days = (datetime.utcnow() - started_datetime.replace(tzinfo=None)).days if hasattr(started_datetime, 'tzinfo') else (datetime.utcnow() - started_datetime).days
            if age_days < 7:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot delete deployments less than 7 days old (deployment is {age_days} days old)"
                )

        # Get user info
        user = user_info.get("user", {})
        actor_id = user.get("id")
        actor_email = user.get("email")
        actor_name = user.get("name")
        
        # Get IP address and user agent
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Perform soft delete
        deleted_deployment = await db_service.delete_deployment(
            deployment_id=deployment_id,
            tenant_id=MOCK_TENANT_ID,
            deleted_by_user_id=actor_id or "00000000-0000-0000-0000-000000000000"
        )

        if not deleted_deployment:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete deployment"
            )

        # Create audit log entry
        try:
            # Get environment info for provider context
            source_env = await db_service.get_environment(deployment.get("source_environment_id"), MOCK_TENANT_ID)
            provider = source_env.get("provider", "n8n") if source_env else "n8n"
            
            await create_audit_log(
                action_type="DEPLOYMENT_DELETED",
                action=f"Deleted deployment",
                actor_id=actor_id,
                actor_email=actor_email,
                actor_name=actor_name,
                tenant_id=MOCK_TENANT_ID,
                resource_type="deployment",
                resource_id=deployment_id,
                resource_name=f"Deployment {deployment_id[:8]}",
                provider=provider,
                old_value={
                    "deployment_id": deployment_id,
                    "status": deployment.get("status"),
                    "workflow_count": deployment.get("summary_json", {}).get("total", 0),
                    "source_environment_id": deployment.get("source_environment_id"),
                    "target_environment_id": deployment.get("target_environment_id"),
                    "pipeline_id": deployment.get("pipeline_id"),
                    "started_at": deployment.get("started_at"),
                    "finished_at": deployment.get("finished_at"),
                },
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "deleted_at": deleted_deployment.get("deleted_at"),
                    "age_days": age_days if started_at else None
                }
            )
        except Exception as audit_error:
            logger.warning(f"Failed to create audit log for deployment deletion: {str(audit_error)}")

        return {
            "success": True,
            "message": "Deployment deleted successfully",
            "deployment_id": deployment_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete deployment: {str(e)}",
        )

