"""Drift Policies API endpoints for TTL/SLA and Enterprise governance."""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List

from app.services.auth_service import get_current_user
from app.services.feature_service import feature_service
from app.services.database import db_service
from app.schemas.drift_policy import (
    DriftPolicyCreate,
    DriftPolicyUpdate,
    DriftPolicyResponse,
    DriftPolicyTemplateResponse,
)

router = APIRouter()


@router.get("/", response_model=DriftPolicyResponse)
async def get_policy(
    user_info: dict = Depends(get_current_user),
):
    """Get the drift policy for the tenant (creates default if none exists)."""
    tenant_id = user_info["tenant"]["id"]

    # Check feature access for drift policies
    can_use, message = await feature_service.can_use_feature(tenant_id, "drift_policies")
    if not can_use:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "feature_not_available",
                "feature": "drift_policies",
                "message": message,
            },
        )

    try:
        response = db_service.client.table("drift_policies").select(
            "*"
        ).eq("tenant_id", tenant_id).execute()

        if response.data and len(response.data) > 0:
            return DriftPolicyResponse(**response.data[0])

        # Create default policy if none exists
        # Get plan to set plan-based retention defaults
        from app.services.feature_service import feature_service
        subscription = await feature_service.get_tenant_subscription(tenant_id)
        plan = subscription.get("plan", {}).get("name", "free").lower() if subscription else "free"
        
        # Get plan-based retention defaults
        from app.services.drift_retention_service import drift_retention_service
        retention_defaults = drift_retention_service.RETENTION_DEFAULTS.get(plan, drift_retention_service.RETENTION_DEFAULTS["free"])
        
        default_policy = DriftPolicyCreate(
            retention_enabled=True,
            retention_days_closed_incidents=retention_defaults["closed_incidents"],
            retention_days_reconciliation_artifacts=retention_defaults["reconciliation_artifacts"],
            retention_days_approvals=retention_defaults["approvals"],
        )
        new_policy = {
            "tenant_id": tenant_id,
            **default_policy.model_dump(),
        }

        create_response = db_service.client.table("drift_policies").insert(
            new_policy
        ).execute()

        if create_response.data:
            return DriftPolicyResponse(**create_response.data[0])

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create default policy",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get policy: {str(e)}",
        )


@router.post("/", response_model=DriftPolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    payload: DriftPolicyCreate,
    user_info: dict = Depends(get_current_user),
):
    """Create or replace the drift policy for the tenant."""
    tenant_id = user_info["tenant"]["id"]

    # Check feature access
    can_use, message = await feature_service.can_use_feature(tenant_id, "drift_policies")
    if not can_use:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "feature_not_available",
                "feature": "drift_policies",
                "message": message,
            },
        )

    try:
        # Upsert the policy (one per tenant)
        policy_data = {
            "tenant_id": tenant_id,
            **payload.model_dump(),
        }

        response = db_service.client.table("drift_policies").upsert(
            policy_data,
            on_conflict="tenant_id",
        ).execute()

        if response.data:
            return DriftPolicyResponse(**response.data[0])

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create policy",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create policy: {str(e)}",
        )


@router.patch("/", response_model=DriftPolicyResponse)
async def update_policy(
    payload: DriftPolicyUpdate,
    user_info: dict = Depends(get_current_user),
):
    """Update the drift policy for the tenant."""
    tenant_id = user_info["tenant"]["id"]

    # Check feature access
    can_use, message = await feature_service.can_use_feature(tenant_id, "drift_policies")
    if not can_use:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "feature_not_available",
                "feature": "drift_policies",
                "message": message,
            },
        )

    try:
        # Get existing policy first
        existing = db_service.client.table("drift_policies").select(
            "*"
        ).eq("tenant_id", tenant_id).execute()

        if not existing.data or len(existing.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Policy not found. Create one first.",
            )

        # Update only provided fields
        update_data = {k: v for k, v in payload.model_dump().items() if v is not None}

        if not update_data:
            return DriftPolicyResponse(**existing.data[0])

        response = db_service.client.table("drift_policies").update(
            update_data
        ).eq("tenant_id", tenant_id).execute()

        if response.data:
            return DriftPolicyResponse(**response.data[0])

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update policy",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update policy: {str(e)}",
        )


@router.get("/templates", response_model=List[DriftPolicyTemplateResponse])
async def list_templates(
    user_info: dict = Depends(get_current_user),
):
    """List available policy templates."""
    tenant_id = user_info["tenant"]["id"]

    # Check feature access
    can_use, message = await feature_service.can_use_feature(tenant_id, "drift_policies")
    if not can_use:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "feature_not_available",
                "feature": "drift_policies",
                "message": message,
            },
        )

    try:
        response = db_service.client.table("drift_policy_templates").select(
            "*"
        ).order("name").execute()

        return [DriftPolicyTemplateResponse(**t) for t in (response.data or [])]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list templates: {str(e)}",
        )


@router.post("/cleanup", status_code=status.HTTP_200_OK)
async def trigger_cleanup(
    user_info: dict = Depends(get_current_user),
):
    """
    Manually trigger retention cleanup for the tenant.
    
    This runs the same cleanup logic as the scheduled job.
    Useful for testing or immediate cleanup.
    """
    tenant_id = user_info["tenant"]["id"]

    # Check feature access
    can_use, message = await feature_service.can_use_feature(tenant_id, "drift_policies")
    if not can_use:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "feature_not_available",
                "feature": "drift_policies",
                "message": message,
            },
        )

    try:
        from app.services.drift_retention_service import drift_retention_service

        results = await drift_retention_service.cleanup_tenant_data(tenant_id)

        return {
            "message": "Cleanup completed",
            "results": results,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run cleanup: {str(e)}",
        )


@router.post("/apply-template/{template_id}", response_model=DriftPolicyResponse)
async def apply_template(
    template_id: str,
    user_info: dict = Depends(get_current_user),
):
    """Apply a policy template to the tenant."""
    tenant_id = user_info["tenant"]["id"]

    # Check feature access
    can_use, message = await feature_service.can_use_feature(tenant_id, "drift_policies")
    if not can_use:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "feature_not_available",
                "feature": "drift_policies",
                "message": message,
            },
        )

    try:
        # Get the template
        template_response = db_service.client.table("drift_policy_templates").select(
            "*"
        ).eq("id", template_id).single().execute()

        if not template_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found",
            )

        template = template_response.data
        policy_config = template.get("policy_config", {})

        # Create/update policy with template values
        policy_data = {
            "tenant_id": tenant_id,
            "default_ttl_hours": policy_config.get("default_ttl_hours", 72),
            "critical_ttl_hours": policy_config.get("critical_ttl_hours", 24),
            "high_ttl_hours": policy_config.get("high_ttl_hours", 48),
            "medium_ttl_hours": policy_config.get("medium_ttl_hours", 72),
            "low_ttl_hours": policy_config.get("low_ttl_hours", 168),
            "auto_create_incidents": policy_config.get("auto_create_incidents", False),
            "auto_create_for_production_only": policy_config.get("auto_create_for_production_only", True),
            "block_deployments_on_expired": policy_config.get("block_deployments_on_expired", False),
            "block_deployments_on_drift": policy_config.get("block_deployments_on_drift", False),
            "notify_on_detection": policy_config.get("notify_on_detection", True),
            "notify_on_expiration_warning": policy_config.get("notify_on_expiration_warning", True),
            "expiration_warning_hours": policy_config.get("expiration_warning_hours", 24),
        }

        response = db_service.client.table("drift_policies").upsert(
            policy_data,
            on_conflict="tenant_id",
        ).execute()

        if response.data:
            return DriftPolicyResponse(**response.data[0])

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to apply template",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply template: {str(e)}",
        )
