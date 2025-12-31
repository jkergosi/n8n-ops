"""
Admin Retention Endpoints

Provides admin-level access to retention policies and manual purge operations.
"""

from fastapi import APIRouter, Query, Depends, HTTPException, status
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from app.services.database import db_service
from app.services.auth_service import get_current_user
from app.services.drift_retention_service import drift_retention_service

router = APIRouter()


# ============================================================================
# Schemas
# ============================================================================

class RetentionPolicyResponse(BaseModel):
    """Tenant retention policy with plan defaults."""
    tenant_id: str
    tenant_name: str
    plan: str
    retention_enabled: bool
    retention_days_drift_checks: int
    retention_days_closed_incidents: int
    retention_days_reconciliation_artifacts: int
    retention_days_approvals: int


class PurgeResult(BaseModel):
    """Result of a retention purge operation."""
    tenant_id: str
    drift_checks_deleted: int
    incident_payloads_purged: int
    reconciliation_artifacts_deleted: int
    approvals_deleted: int
    executed_at: str


class PurgeAllResult(BaseModel):
    """Result of purging all tenants."""
    drift_checks_deleted: int
    incident_payloads_purged: int
    reconciliation_artifacts_deleted: int
    approvals_deleted: int
    tenants_processed: int
    tenants_with_changes: int
    executed_at: str


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/policies")
async def list_retention_policies(
    user_info: dict = Depends(get_current_user)
):
    """
    List retention policies for all tenants.

    Returns each tenant's retention configuration with plan-based defaults applied.
    """
    try:
        # Get all tenants
        tenants_result = db_service.client.table("tenants").select("id, name, subscription_tier").execute()
        tenants = tenants_result.data or []

        policies = []
        for tenant in tenants:
            tenant_id = tenant["id"]
            policy = await drift_retention_service.get_retention_policy(tenant_id)

            policies.append(RetentionPolicyResponse(
                tenant_id=tenant_id,
                tenant_name=tenant.get("name", "Unknown"),
                plan=policy.get("plan", "free"),
                retention_enabled=policy.get("retention_enabled", True),
                retention_days_drift_checks=policy.get("retention_days_drift_checks", 7),
                retention_days_closed_incidents=policy.get("retention_days_closed_incidents", 0),
                retention_days_reconciliation_artifacts=policy.get("retention_days_reconciliation_artifacts", 0),
                retention_days_approvals=policy.get("retention_days_approvals", 0),
            ))

        return {"policies": policies, "total": len(policies)}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list retention policies: {str(e)}"
        )


@router.get("/policies/{tenant_id}", response_model=RetentionPolicyResponse)
async def get_tenant_retention_policy(
    tenant_id: str,
    user_info: dict = Depends(get_current_user)
):
    """
    Get retention policy for a specific tenant.
    """
    try:
        # Verify tenant exists
        tenant_result = db_service.client.table("tenants").select("id, name, subscription_tier").eq("id", tenant_id).single().execute()
        if not tenant_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )

        tenant = tenant_result.data
        policy = await drift_retention_service.get_retention_policy(tenant_id)

        return RetentionPolicyResponse(
            tenant_id=tenant_id,
            tenant_name=tenant.get("name", "Unknown"),
            plan=policy.get("plan", "free"),
            retention_enabled=policy.get("retention_enabled", True),
            retention_days_drift_checks=policy.get("retention_days_drift_checks", 7),
            retention_days_closed_incidents=policy.get("retention_days_closed_incidents", 0),
            retention_days_reconciliation_artifacts=policy.get("retention_days_reconciliation_artifacts", 0),
            retention_days_approvals=policy.get("retention_days_approvals", 0),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get retention policy: {str(e)}"
        )


@router.post("/purge/{tenant_id}", response_model=PurgeResult)
async def purge_tenant_data(
    tenant_id: str,
    user_info: dict = Depends(get_current_user)
):
    """
    Manually trigger retention purge for a specific tenant.

    This operation:
    - Deletes drift check history older than retention period
    - Purges payloads from closed incidents older than retention period (metadata preserved)
    - Deletes reconciliation artifacts older than retention period
    - Deletes approval records older than retention period

    Note: Open incidents are NEVER purged regardless of age.
    """
    try:
        # Verify tenant exists
        tenant_result = db_service.client.table("tenants").select("id").eq("id", tenant_id).single().execute()
        if not tenant_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )

        # Execute purge
        result = await drift_retention_service.cleanup_tenant_data(tenant_id)

        return PurgeResult(
            tenant_id=tenant_id,
            drift_checks_deleted=result.get("drift_checks_deleted", 0),
            incident_payloads_purged=result.get("incident_payloads_purged", 0),
            reconciliation_artifacts_deleted=result.get("reconciliation_artifacts_deleted", 0),
            approvals_deleted=result.get("approvals_deleted", 0),
            executed_at=datetime.utcnow().isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to purge tenant data: {str(e)}"
        )


@router.post("/purge", response_model=PurgeAllResult)
async def purge_all_tenants(
    user_info: dict = Depends(get_current_user)
):
    """
    Manually trigger retention purge for ALL tenants.

    This is typically run as a scheduled job (nightly) but can be triggered
    manually by admins for immediate cleanup.

    This operation applies per-tenant retention policies to:
    - Drift check history
    - Closed incident payloads (metadata preserved)
    - Reconciliation artifacts
    - Approval records

    Note: Open incidents are NEVER purged regardless of age.
    """
    try:
        result = await drift_retention_service.cleanup_all_tenants()

        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Purge completed with errors: {result['error']}"
            )

        return PurgeAllResult(
            drift_checks_deleted=result.get("drift_checks_deleted", 0),
            incident_payloads_purged=result.get("incident_payloads_purged", 0),
            reconciliation_artifacts_deleted=result.get("reconciliation_artifacts_deleted", 0),
            approvals_deleted=result.get("approvals_deleted", 0),
            tenants_processed=result.get("tenants_processed", 0),
            tenants_with_changes=result.get("tenants_with_changes", 0),
            executed_at=datetime.utcnow().isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to purge all tenants: {str(e)}"
        )
