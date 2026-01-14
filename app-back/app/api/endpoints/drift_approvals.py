"""Drift Approvals API endpoints for Enterprise governance workflows."""
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
import logging

from app.services.auth_service import get_current_user
from app.services.database import db_service
from app.core.entitlements_gate import require_entitlement
from app.services.audit_service import audit_service
from app.services.gated_action_service import gated_action_service
from app.schemas.drift_policy import (
    DriftApprovalCreate,
    DriftApprovalDecision,
    DriftApprovalResponse,
    ApprovalStatus,
    ApprovalType,
    ApprovalAuditEventType,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[DriftApprovalResponse])
async def list_approvals(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    incident_id: Optional[str] = Query(None, description="Filter by incident"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("drift_policies")),
):
    """List drift approval requests for the tenant."""
    tenant_id = user_info["tenant"]["id"]

    try:
        query = db_service.client.table("drift_approvals").select(
            "*"
        ).eq("tenant_id", tenant_id)

        if status_filter:
            query = query.eq("status", status_filter)

        if incident_id:
            query = query.eq("incident_id", incident_id)

        response = query.order("created_at", desc=True).range(
            offset, offset + limit - 1
        ).execute()

        return [DriftApprovalResponse(**a) for a in (response.data or [])]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list approvals: {str(e)}",
        )


@router.get("/pending", response_model=List[DriftApprovalResponse])
async def list_pending_approvals(
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("drift_policies")),
):
    """List all pending approval requests for the tenant."""
    tenant_id = user_info["tenant"]["id"]

    try:
        response = db_service.client.table("drift_approvals").select(
            "*"
        ).eq("tenant_id", tenant_id).eq(
            "status", ApprovalStatus.pending.value
        ).order("created_at", desc=True).execute()

        return [DriftApprovalResponse(**a) for a in (response.data or [])]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list pending approvals: {str(e)}",
        )


@router.post("/", response_model=DriftApprovalResponse, status_code=status.HTTP_201_CREATED)
async def request_approval(
    payload: DriftApprovalCreate,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("drift_policies")),
):
    """Request approval for an action on a drift incident."""
    tenant_id = user_info["tenant"]["id"]
    user_id = user_info["user"]["id"]

    try:
        # Verify incident exists
        incident_response = db_service.client.table("drift_incidents").select(
            "id"
        ).eq("id", payload.incident_id).eq("tenant_id", tenant_id).execute()

        if not incident_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Incident not found",
            )

        # Check if there's already a pending approval for this action type
        existing = db_service.client.table("drift_approvals").select(
            "id"
        ).eq("incident_id", payload.incident_id).eq(
            "approval_type", payload.approval_type.value
        ).eq("status", ApprovalStatus.pending.value).execute()

        if existing.data and len(existing.data) > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A pending approval for '{payload.approval_type.value}' already exists",
            )

        now = datetime.utcnow().isoformat()

        approval_data = {
            "tenant_id": tenant_id,
            "incident_id": payload.incident_id,
            "approval_type": payload.approval_type.value,
            "status": ApprovalStatus.pending.value,
            "requested_by": user_id,
            "requested_at": now,
            "request_reason": payload.request_reason,
            "extension_hours": payload.extension_hours,
            "created_at": now,
            "updated_at": now,
        }

        response = db_service.client.table("drift_approvals").insert(
            approval_data
        ).execute()

        if response.data:
            approval_response = DriftApprovalResponse(**response.data[0])

            # Log approval request to audit trail
            action_metadata = {}
            if payload.extension_hours:
                action_metadata["extension_hours"] = payload.extension_hours

            await audit_service.log_approval_requested(
                tenant_id=tenant_id,
                approval_id=approval_response.id,
                incident_id=payload.incident_id,
                actor_id=user_id,
                approval_type=payload.approval_type,
                reason=payload.request_reason,
                action_metadata=action_metadata,
                actor_email=user_info.get("user", {}).get("email"),
            )

            logger.info(
                f"Approval request created: {approval_response.id} "
                f"(type={payload.approval_type.value}, incident={payload.incident_id})"
            )

            return approval_response

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create approval request",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create approval request: {str(e)}",
        )


@router.get("/{approval_id}", response_model=DriftApprovalResponse)
async def get_approval(
    approval_id: str,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("drift_policies")),
):
    """Get a single approval request."""
    tenant_id = user_info["tenant"]["id"]

    try:
        response = db_service.client.table("drift_approvals").select(
            "*"
        ).eq("id", approval_id).eq("tenant_id", tenant_id).single().execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval request not found",
            )

        return DriftApprovalResponse(**response.data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get approval: {str(e)}",
        )


@router.post("/{approval_id}/decide", response_model=DriftApprovalResponse)
async def decide_approval(
    approval_id: str,
    payload: DriftApprovalDecision,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("drift_policies")),
):
    """Approve or reject an approval request."""
    tenant_id = user_info["tenant"]["id"]
    user_id = user_info["user"]["id"]

    # Validate decision value
    if payload.decision not in [ApprovalStatus.approved, ApprovalStatus.rejected]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be 'approved' or 'rejected'",
        )

    try:
        # Get existing approval
        existing = db_service.client.table("drift_approvals").select(
            "*"
        ).eq("id", approval_id).eq("tenant_id", tenant_id).single().execute()

        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval request not found",
            )

        approval = existing.data

        if approval["status"] != ApprovalStatus.pending.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot decide on approval in '{approval['status']}' status",
            )

        # Cannot approve your own request
        if approval["requested_by"] == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot approve your own request",
            )

        now = datetime.utcnow().isoformat()

        update_data = {
            "status": payload.decision.value,
            "decided_by": user_id,
            "decided_at": now,
            "decision_notes": payload.decision_notes,
            "updated_at": now,
        }

        response = db_service.client.table("drift_approvals").update(
            update_data
        ).eq("id", approval_id).execute()

        if response.data:
            approval_response = DriftApprovalResponse(**response.data[0])

            # Log approval decision to audit trail
            await audit_service.log_approval_decision(
                tenant_id=tenant_id,
                approval_id=approval_id,
                incident_id=approval["incident_id"],
                actor_id=user_id,
                approval_type=ApprovalType(approval["approval_type"]),
                decision=payload.decision,
                decision_notes=payload.decision_notes,
                actor_email=user_info.get("user", {}).get("email"),
            )

            # If approved, execute the action based on approval type
            if payload.decision == ApprovalStatus.approved:
                await _execute_approved_action(
                    tenant_id=tenant_id,
                    incident_id=approval["incident_id"],
                    approval_id=approval_id,
                    approval_type=approval["approval_type"],
                    extension_hours=approval.get("extension_hours"),
                    user_id=user_id,
                    user_info=user_info,
                )

            logger.info(
                f"Approval decision recorded: {approval_id} "
                f"(decision={payload.decision.value}, incident={approval['incident_id']})"
            )

            return approval_response

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update approval",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decide on approval: {str(e)}",
        )


@router.post("/{approval_id}/cancel", response_model=DriftApprovalResponse)
async def cancel_approval(
    approval_id: str,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("drift_policies")),
):
    """Cancel a pending approval request (by requester only)."""
    tenant_id = user_info["tenant"]["id"]
    user_id = user_info["user"]["id"]

    try:
        # Get existing approval
        existing = db_service.client.table("drift_approvals").select(
            "*"
        ).eq("id", approval_id).eq("tenant_id", tenant_id).single().execute()

        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval request not found",
            )

        approval = existing.data

        if approval["status"] != ApprovalStatus.pending.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel approval in '{approval['status']}' status",
            )

        # Only requester or admin can cancel
        if approval["requested_by"] != user_id:
            user_role = user_info["user"].get("role", "viewer")
            if user_role not in ["admin", "super_admin"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the requester or an admin can cancel this request",
                )

        now = datetime.utcnow().isoformat()

        update_data = {
            "status": ApprovalStatus.cancelled.value,
            "updated_at": now,
        }

        response = db_service.client.table("drift_approvals").update(
            update_data
        ).eq("id", approval_id).execute()

        if response.data:
            approval_response = DriftApprovalResponse(**response.data[0])

            # Log approval cancellation to audit trail
            await audit_service.log_approval_cancelled(
                tenant_id=tenant_id,
                approval_id=approval_id,
                incident_id=approval["incident_id"],
                actor_id=user_id,
                approval_type=ApprovalType(approval["approval_type"]),
                reason="Cancelled by user",
                actor_email=user_info.get("user", {}).get("email"),
            )

            logger.info(
                f"Approval cancelled: {approval_id} "
                f"(incident={approval['incident_id']}, actor={user_id})"
            )

            return approval_response

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel approval",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel approval: {str(e)}",
        )


async def _execute_approved_action(
    tenant_id: str,
    incident_id: str,
    approval_id: str,
    approval_type: str,
    extension_hours: Optional[int],
    user_id: str,
    user_info: dict,
) -> None:
    """
    Execute the action after approval is granted.

    This function is called automatically when an approval is granted.
    It executes the approved action and logs the execution to the audit trail.

    Args:
        tenant_id: The tenant ID
        incident_id: The drift incident ID
        approval_id: The approval request ID
        approval_type: The type of action to execute
        extension_hours: Hours to extend TTL (for extend_ttl actions)
        user_id: The ID of the user who approved the action
        user_info: Full user info dict for audit logging
    """
    from app.services.drift_incident_service import drift_incident_service

    now = datetime.utcnow()
    execution_result = {}
    execution_error = None

    try:
        logger.info(
            f"Executing approved action: {approval_type} "
            f"(approval={approval_id}, incident={incident_id})"
        )

        if approval_type == "acknowledge":
            await drift_incident_service.acknowledge_incident(
                tenant_id=tenant_id,
                incident_id=incident_id,
                user_id=user_id,
                reason="Approved via workflow",
            )
            execution_result = {
                "action": "acknowledge",
                "incident_id": incident_id,
                "executed_at": now.isoformat(),
            }

        elif approval_type == "extend_ttl":
            if extension_hours:
                from datetime import timedelta
                new_expiry = now + timedelta(hours=extension_hours)
                await drift_incident_service.update_incident(
                    tenant_id=tenant_id,
                    incident_id=incident_id,
                    user_id=user_id,
                    expires_at=new_expiry,
                )
                execution_result = {
                    "action": "extend_ttl",
                    "incident_id": incident_id,
                    "extension_hours": extension_hours,
                    "new_expiry": new_expiry.isoformat(),
                    "executed_at": now.isoformat(),
                }
            else:
                execution_error = "No extension_hours provided for extend_ttl action"
                logger.error(execution_error)

        elif approval_type == "close":
            await drift_incident_service.close_incident(
                tenant_id=tenant_id,
                incident_id=incident_id,
                user_id=user_id,
                reason="Approved via workflow",
            )
            execution_result = {
                "action": "close",
                "incident_id": incident_id,
                "executed_at": now.isoformat(),
            }

        elif approval_type == "reconcile":
            # Reconciliation needs additional data, so we just mark it as ready
            # and let the user trigger reconciliation separately
            execution_result = {
                "action": "reconcile",
                "incident_id": incident_id,
                "status": "approved_awaiting_reconciliation",
                "executed_at": now.isoformat(),
            }
            logger.info(
                f"Reconcile approval granted for incident {incident_id}. "
                "User must trigger reconciliation separately."
            )

        # Mark approval as executed
        await gated_action_service.mark_approval_executed(
            tenant_id=tenant_id,
            approval_id=approval_id,
            executed_by=user_id,
        )

        # Log successful execution to audit trail
        if execution_error is None:
            await audit_service.log_approval_executed(
                tenant_id=tenant_id,
                approval_id=approval_id,
                incident_id=incident_id,
                actor_id=user_id,
                approval_type=ApprovalType(approval_type),
                execution_result=execution_result,
                actor_email=user_info.get("user", {}).get("email"),
            )
            logger.info(
                f"Action executed successfully: {approval_type} "
                f"(approval={approval_id}, incident={incident_id})"
            )

    except Exception as e:
        execution_error = str(e)
        logger.error(
            f"Failed to execute approved action: {approval_type} "
            f"(approval={approval_id}, incident={incident_id}): {e}"
        )

        # Log execution failure to audit trail
        await audit_service.log_approval_execution_failed(
            tenant_id=tenant_id,
            approval_id=approval_id,
            incident_id=incident_id,
            actor_id=user_id,
            approval_type=ApprovalType(approval_type),
            execution_error=execution_error,
            actor_email=user_info.get("user", {}).get("email"),
        )

        # Re-raise the exception so the API returns an error
        raise
