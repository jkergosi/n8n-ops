"""
Downgrade Grace Period API Endpoints

Provides API endpoints for viewing and managing grace periods.
Tenant admins can view their active grace periods and manually cancel them.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Dict, Any
from datetime import datetime, timezone
import logging

from app.schemas.downgrade import (
    GracePeriodListResponse,
    GracePeriodDetailResponse,
    DowngradeGracePeriodResponse,
    GracePeriodSummary,
)
from app.services.downgrade_service import downgrade_service
from app.services.database import db_service
from app.services.auth_service import get_current_user
from app.core.rbac import require_tenant_admin
from app.core.downgrade_policy import ResourceType

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/grace-periods", response_model=GracePeriodListResponse)
async def list_grace_periods(
    user_info: dict = Depends(get_current_user),
    _admin_guard: dict = Depends(require_tenant_admin()),
    status_filter: str = "active",  # active, expired, all
):
    """
    Get all grace periods for the current tenant.

    Returns a list of grace periods with a summary of counts by type and status.
    """
    try:
        tenant_id = user_info["tenant"]["id"]

        # Get grace periods based on filter
        if status_filter == "active":
            grace_periods = await downgrade_service.get_active_grace_periods(tenant_id)
        elif status_filter == "all":
            # Get all grace periods for this tenant
            response = db_service.client.table("downgrade_grace_periods").select(
                "*"
            ).eq("tenant_id", tenant_id).order("created_at", desc=True).execute()
            grace_periods = response.data or []
        else:
            # Default to active
            grace_periods = await downgrade_service.get_active_grace_periods(tenant_id)

        # Calculate summary
        active_count = 0
        expired_count = 0
        by_resource_type: Dict[str, int] = {}
        expiring_soon = []

        now = datetime.now(timezone.utc)

        for gp in grace_periods:
            gp_status = gp.get("status", "")

            # Count by status
            if gp_status == "active":
                active_count += 1

                # Check if expiring soon (within 7 days)
                expires_at_str = gp.get("expires_at")
                if expires_at_str:
                    try:
                        if isinstance(expires_at_str, str):
                            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                        else:
                            expires_at = expires_at_str

                        days_remaining = (expires_at - now).days
                        if days_remaining <= 7:
                            expiring_soon.append({
                                "id": gp.get("id"),
                                "resource_type": gp.get("resource_type"),
                                "resource_id": gp.get("resource_id"),
                                "days_remaining": days_remaining,
                                "expires_at": expires_at_str,
                            })
                    except Exception:
                        pass
            elif gp_status == "expired":
                expired_count += 1

            # Count by resource type
            resource_type = gp.get("resource_type", "unknown")
            by_resource_type[resource_type] = by_resource_type.get(resource_type, 0) + 1

        summary = GracePeriodSummary(
            tenant_id=tenant_id,
            active_count=active_count,
            expired_count=expired_count,
            by_resource_type=by_resource_type,
            expiring_soon=expiring_soon,
        )

        return GracePeriodListResponse(
            grace_periods=grace_periods,
            total_count=len(grace_periods),
            summary=summary,
        )

    except Exception as e:
        logger.error(f"Failed to list grace periods for tenant: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve grace periods: {str(e)}"
        )


@router.get("/grace-periods/{grace_period_id}", response_model=GracePeriodDetailResponse)
async def get_grace_period(
    grace_period_id: str,
    user_info: dict = Depends(get_current_user),
    _admin_guard: dict = Depends(require_tenant_admin()),
):
    """
    Get detailed information about a specific grace period.

    Returns the grace period record with additional context like days remaining,
    resource name, and tenant name.
    """
    try:
        tenant_id = user_info["tenant"]["id"]

        # Get the grace period
        response = db_service.client.table("downgrade_grace_periods").select(
            "*"
        ).eq("id", grace_period_id).eq("tenant_id", tenant_id).maybe_single().execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Grace period not found"
            )

        grace_period = response.data

        # Calculate days remaining
        expires_at_str = grace_period.get("expires_at")
        days_remaining = None
        if expires_at_str:
            try:
                if isinstance(expires_at_str, str):
                    expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                else:
                    expires_at = expires_at_str

                now = datetime.now(timezone.utc)
                days_remaining = (expires_at - now).days
            except Exception:
                pass

        # Get resource name (if available)
        resource_name = None
        resource_type = grace_period.get("resource_type")
        resource_id = grace_period.get("resource_id")

        try:
            if resource_type == "environment":
                env_response = db_service.client.table("environments").select(
                    "name"
                ).eq("id", resource_id).maybe_single().execute()
                if env_response.data:
                    resource_name = env_response.data.get("name")
            elif resource_type == "workflow":
                wf_response = db_service.client.table("canonical_workflows").select(
                    "name"
                ).eq("id", resource_id).maybe_single().execute()
                if wf_response.data:
                    resource_name = wf_response.data.get("name")
            # For team members, we could fetch user name, but skip for now
        except Exception:
            pass

        # Get tenant name
        tenant_name = user_info.get("tenant", {}).get("name")

        return GracePeriodDetailResponse(
            **grace_period,
            days_remaining=days_remaining,
            resource_name=resource_name,
            tenant_name=tenant_name,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get grace period {grace_period_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve grace period: {str(e)}"
        )


@router.post("/grace-periods/{grace_period_id}/cancel")
async def cancel_grace_period(
    grace_period_id: str,
    user_info: dict = Depends(get_current_user),
    _admin_guard: dict = Depends(require_tenant_admin()),
):
    """
    Manually cancel a grace period.

    This can be used when a tenant admin manually resolves an over-limit
    situation (e.g., removes resources) and wants to cancel the grace period
    immediately rather than waiting for the next enforcement cycle.
    """
    try:
        tenant_id = user_info["tenant"]["id"]

        # Get the grace period to verify it exists and belongs to this tenant
        response = db_service.client.table("downgrade_grace_periods").select(
            "*"
        ).eq("id", grace_period_id).eq("tenant_id", tenant_id).maybe_single().execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Grace period not found"
            )

        grace_period = response.data

        # Check if already cancelled or expired
        if grace_period.get("status") != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Grace period is already {grace_period.get('status')}"
            )

        # Get resource type
        resource_type_str = grace_period.get("resource_type")
        try:
            resource_type = ResourceType(resource_type_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid resource type: {resource_type_str}"
            )

        # Cancel the grace period
        resource_id = grace_period.get("resource_id")
        cancelled = await downgrade_service.cancel_grace_period(
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id
        )

        if not cancelled:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel grace period"
            )

        logger.info(
            f"Manually cancelled grace period {grace_period_id} for tenant {tenant_id} "
            f"by user {user_info.get('user', {}).get('id')}"
        )

        return {
            "message": "Grace period cancelled successfully",
            "grace_period_id": grace_period_id,
            "resource_type": resource_type_str,
            "resource_id": resource_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel grace period {grace_period_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel grace period: {str(e)}"
        )


@router.get("/grace-periods/summary")
async def get_grace_periods_summary(
    user_info: dict = Depends(get_current_user),
    _admin_guard: dict = Depends(require_tenant_admin()),
):
    """
    Get a summary of all grace periods for the current tenant.

    Returns counts by status and resource type without listing all records.
    Useful for dashboard widgets.
    """
    try:
        tenant_id = user_info["tenant"]["id"]

        # Get all grace periods
        response = db_service.client.table("downgrade_grace_periods").select(
            "*"
        ).eq("tenant_id", tenant_id).execute()

        grace_periods = response.data or []

        # Calculate summary
        active_count = 0
        expired_count = 0
        by_resource_type: Dict[str, int] = {}
        expiring_soon = []

        now = datetime.now(timezone.utc)

        for gp in grace_periods:
            gp_status = gp.get("status", "")

            # Count by status
            if gp_status == "active":
                active_count += 1

                # Check if expiring soon (within 7 days)
                expires_at_str = gp.get("expires_at")
                if expires_at_str:
                    try:
                        if isinstance(expires_at_str, str):
                            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                        else:
                            expires_at = expires_at_str

                        days_remaining = (expires_at - now).days
                        if days_remaining <= 7:
                            expiring_soon.append({
                                "id": gp.get("id"),
                                "resource_type": gp.get("resource_type"),
                                "resource_id": gp.get("resource_id"),
                                "days_remaining": days_remaining,
                                "expires_at": expires_at_str,
                            })
                    except Exception:
                        pass
            elif gp_status == "expired":
                expired_count += 1

            # Count by resource type
            resource_type = gp.get("resource_type", "unknown")
            by_resource_type[resource_type] = by_resource_type.get(resource_type, 0) + 1

        return GracePeriodSummary(
            tenant_id=tenant_id,
            active_count=active_count,
            expired_count=expired_count,
            by_resource_type=by_resource_type,
            expiring_soon=expiring_soon,
        )

    except Exception as e:
        logger.error(f"Failed to get grace periods summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve summary: {str(e)}"
        )
