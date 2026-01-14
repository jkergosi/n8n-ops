"""
Gated Action Service - Centralized approval enforcement for drift incident actions.

This service enforces approval workflows for critical drift incident actions:
- Acknowledge: Accepting drift as temporary/acceptable
- Extend TTL: Extending time-to-live for drift incidents
- Reconcile: Resolving drift through reconciliation

Implements fail-safe behavior: if approval requirements cannot be determined,
actions requiring approval are blocked by default for security.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
import logging

from app.services.database import db_service
from app.schemas.drift_policy import ApprovalType, ApprovalStatus

logger = logging.getLogger(__name__)


class GatedActionType(str, Enum):
    """Types of gated actions that may require approval."""
    ACKNOWLEDGE = "acknowledge"
    EXTEND_TTL = "extend_ttl"
    RECONCILE = "reconcile"


class ApprovalRequirement(str, Enum):
    """Result of approval requirement check."""
    NOT_REQUIRED = "not_required"
    REQUIRED_PENDING = "required_pending"
    REQUIRED_APPROVED = "required_approved"
    REQUIRED_REJECTED = "required_rejected"
    REQUIRED_NO_REQUEST = "required_no_request"


@dataclass
class GatedActionDecision:
    """
    Decision result from gated action approval check.

    Attributes:
        allowed: Whether the action is allowed to proceed
        requirement: The approval requirement status
        reason: Human-readable reason for the decision
        approval_id: ID of the approval request (if any)
        approval_details: Additional details about the approval
        policy_config: The policy configuration used for the decision
    """
    allowed: bool
    requirement: ApprovalRequirement
    reason: Optional[str] = None
    approval_id: Optional[str] = None
    approval_details: Optional[Dict[str, Any]] = None
    policy_config: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert decision to dictionary for API responses."""
        return {
            "allowed": self.allowed,
            "requirement": self.requirement.value,
            "reason": self.reason,
            "approval_id": self.approval_id,
            "approval_details": self.approval_details,
            "policy_config": self.policy_config,
        }


class GatedActionService:
    """
    Service for enforcing approval workflows on gated drift incident actions.

    This service:
    1. Checks if tenant has drift policy configured
    2. Determines if an action requires approval
    3. Verifies approval status before allowing action execution
    4. Provides audit trail support for approval enforcement
    """

    async def get_tenant_policy(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the drift policy for a tenant.

        Args:
            tenant_id: The tenant ID

        Returns:
            The drift policy configuration, or None if not found/configured
        """
        try:
            response = db_service.client.table("drift_policies").select(
                "*"
            ).eq("tenant_id", tenant_id).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to fetch drift policy for tenant {tenant_id}: {e}")
            return None

    def is_approval_required_by_policy(
        self,
        policy: Optional[Dict[str, Any]],
        action_type: GatedActionType
    ) -> bool:
        """
        Check if approval is required for a specific action type based on policy.

        Args:
            policy: The drift policy configuration
            action_type: The type of action being performed

        Returns:
            True if approval is required, False otherwise
        """
        if not policy:
            return False

        # Map action types to policy configuration keys
        policy_key_map = {
            GatedActionType.ACKNOWLEDGE: "require_approval_for_acknowledge",
            GatedActionType.EXTEND_TTL: "require_approval_for_extend_ttl",
            GatedActionType.RECONCILE: "require_approval_for_reconcile",
        }

        policy_key = policy_key_map.get(action_type)
        if not policy_key:
            return False

        # Check if the policy requires approval for this action
        return policy.get(policy_key, False)

    async def get_pending_approval(
        self,
        tenant_id: str,
        incident_id: str,
        action_type: GatedActionType
    ) -> Optional[Dict[str, Any]]:
        """
        Get pending approval request for a specific action on an incident.

        Args:
            tenant_id: The tenant ID
            incident_id: The incident ID
            action_type: The type of action

        Returns:
            The pending approval record, or None if not found
        """
        try:
            # Map GatedActionType to ApprovalType
            approval_type_map = {
                GatedActionType.ACKNOWLEDGE: "acknowledge",
                GatedActionType.EXTEND_TTL: "extend_ttl",
                GatedActionType.RECONCILE: "reconcile",
            }

            approval_type = approval_type_map.get(action_type)
            if not approval_type:
                return None

            response = db_service.client.table("drift_approvals").select(
                "*"
            ).eq("tenant_id", tenant_id).eq(
                "incident_id", incident_id
            ).eq("approval_type", approval_type).eq(
                "status", ApprovalStatus.pending.value
            ).order("created_at", desc=True).limit(1).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(
                f"Failed to fetch pending approval for tenant {tenant_id}, "
                f"incident {incident_id}, action {action_type}: {e}"
            )
            return None

    async def get_approved_approval(
        self,
        tenant_id: str,
        incident_id: str,
        action_type: GatedActionType
    ) -> Optional[Dict[str, Any]]:
        """
        Get most recent approved approval for a specific action on an incident.

        Args:
            tenant_id: The tenant ID
            incident_id: The incident ID
            action_type: The type of action

        Returns:
            The approved approval record, or None if not found
        """
        try:
            # Map GatedActionType to ApprovalType
            approval_type_map = {
                GatedActionType.ACKNOWLEDGE: "acknowledge",
                GatedActionType.EXTEND_TTL: "extend_ttl",
                GatedActionType.RECONCILE: "reconcile",
            }

            approval_type = approval_type_map.get(action_type)
            if not approval_type:
                return None

            response = db_service.client.table("drift_approvals").select(
                "*"
            ).eq("tenant_id", tenant_id).eq(
                "incident_id", incident_id
            ).eq("approval_type", approval_type).eq(
                "status", ApprovalStatus.approved.value
            ).order("decided_at", desc=True).limit(1).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(
                f"Failed to fetch approved approval for tenant {tenant_id}, "
                f"incident {incident_id}, action {action_type}: {e}"
            )
            return None

    async def check_approval_status(
        self,
        tenant_id: str,
        incident_id: str,
        action_type: GatedActionType,
        user_id: Optional[str] = None
    ) -> GatedActionDecision:
        """
        Check if an action requires approval and if approval has been granted.

        This is the main entry point for gated action enforcement. It checks:
        1. Policy existence - is a policy configured
        2. Approval requirement - does the action require approval
        3. Approval status - is there a pending or approved approval

        Args:
            tenant_id: The tenant ID
            incident_id: The incident ID
            action_type: The type of action being performed
            user_id: Optional user ID performing the action

        Returns:
            GatedActionDecision with the approval status and decision
        """
        logger.info(
            f"Gated action approval check started "
            f"(tenant_id={tenant_id}, incident_id={incident_id}, "
            f"action_type={action_type.value}, user_id={user_id})"
        )

        # Step 1: Get tenant policy
        policy = await self.get_tenant_policy(tenant_id)

        # Step 2: Check if approval is required
        approval_required = self.is_approval_required_by_policy(policy, action_type)

        if not approval_required:
            logger.debug(
                f"Approval not required for {action_type.value} "
                f"(tenant_id={tenant_id}, incident_id={incident_id})"
            )
            return GatedActionDecision(
                allowed=True,
                requirement=ApprovalRequirement.NOT_REQUIRED,
                reason=f"Approval not required for {action_type.value} action",
                policy_config={
                    "approval_required": False
                } if policy else None,
            )

        # Step 3: Check for approved approval
        approved_approval = await self.get_approved_approval(
            tenant_id, incident_id, action_type
        )

        if approved_approval:
            approval_id = approved_approval.get("id")
            decided_by = approved_approval.get("decided_by")
            decided_at = approved_approval.get("decided_at")

            logger.info(
                f"Gated action ALLOWED with approval "
                f"(tenant_id={tenant_id}, incident_id={incident_id}, "
                f"action_type={action_type.value}, approval_id={approval_id})"
            )

            return GatedActionDecision(
                allowed=True,
                requirement=ApprovalRequirement.REQUIRED_APPROVED,
                reason=f"Approval granted for {action_type.value} action",
                approval_id=approval_id,
                approval_details={
                    "status": ApprovalStatus.approved.value,
                    "decided_by": decided_by,
                    "decided_at": decided_at,
                    "request_reason": approved_approval.get("request_reason"),
                    "decision_notes": approved_approval.get("decision_notes"),
                },
                policy_config={
                    "approval_required": True
                },
            )

        # Step 4: Check for pending approval
        pending_approval = await self.get_pending_approval(
            tenant_id, incident_id, action_type
        )

        if pending_approval:
            approval_id = pending_approval.get("id")
            requested_by = pending_approval.get("requested_by")
            requested_at = pending_approval.get("requested_at")

            logger.warning(
                f"Gated action BLOCKED: Pending approval "
                f"(tenant_id={tenant_id}, incident_id={incident_id}, "
                f"action_type={action_type.value}, approval_id={approval_id})"
            )

            return GatedActionDecision(
                allowed=False,
                requirement=ApprovalRequirement.REQUIRED_PENDING,
                reason=(
                    f"Approval required for {action_type.value} action. "
                    f"A pending approval request exists and must be decided before proceeding."
                ),
                approval_id=approval_id,
                approval_details={
                    "status": ApprovalStatus.pending.value,
                    "requested_by": requested_by,
                    "requested_at": requested_at,
                    "request_reason": pending_approval.get("request_reason"),
                },
                policy_config={
                    "approval_required": True
                },
            )

        # Step 5: Check for rejected approval
        try:
            approval_type_map = {
                GatedActionType.ACKNOWLEDGE: "acknowledge",
                GatedActionType.EXTEND_TTL: "extend_ttl",
                GatedActionType.RECONCILE: "reconcile",
            }
            approval_type = approval_type_map.get(action_type)

            response = db_service.client.table("drift_approvals").select(
                "*"
            ).eq("tenant_id", tenant_id).eq(
                "incident_id", incident_id
            ).eq("approval_type", approval_type).eq(
                "status", ApprovalStatus.rejected.value
            ).order("decided_at", desc=True).limit(1).execute()

            if response.data and len(response.data) > 0:
                rejected_approval = response.data[0]
                approval_id = rejected_approval.get("id")
                decided_by = rejected_approval.get("decided_by")
                decided_at = rejected_approval.get("decided_at")
                decision_notes = rejected_approval.get("decision_notes")

                logger.warning(
                    f"Gated action BLOCKED: Previous approval was rejected "
                    f"(tenant_id={tenant_id}, incident_id={incident_id}, "
                    f"action_type={action_type.value}, approval_id={approval_id})"
                )

                return GatedActionDecision(
                    allowed=False,
                    requirement=ApprovalRequirement.REQUIRED_REJECTED,
                    reason=(
                        f"Approval required for {action_type.value} action. "
                        f"A previous approval request was rejected. "
                        f"Please submit a new approval request."
                    ),
                    approval_id=approval_id,
                    approval_details={
                        "status": ApprovalStatus.rejected.value,
                        "decided_by": decided_by,
                        "decided_at": decided_at,
                        "decision_notes": decision_notes,
                    },
                    policy_config={
                        "approval_required": True
                    },
                )
        except Exception as e:
            logger.error(f"Failed to check for rejected approval: {e}")

        # Step 6: No approval request exists
        logger.warning(
            f"Gated action BLOCKED: No approval request "
            f"(tenant_id={tenant_id}, incident_id={incident_id}, "
            f"action_type={action_type.value})"
        )

        return GatedActionDecision(
            allowed=False,
            requirement=ApprovalRequirement.REQUIRED_NO_REQUEST,
            reason=(
                f"Approval required for {action_type.value} action. "
                f"Please submit an approval request before proceeding."
            ),
            policy_config={
                "approval_required": True
            },
        )

    async def mark_approval_executed(
        self,
        tenant_id: str,
        approval_id: str,
        executed_by: Optional[str] = None
    ) -> bool:
        """
        Mark an approval as executed after the action completes.

        This updates the approval record to track when the approved action
        was actually executed, providing a complete audit trail.

        Args:
            tenant_id: The tenant ID
            approval_id: The approval ID
            executed_by: Optional user ID who executed the action

        Returns:
            True if successful, False otherwise
        """
        try:
            update_data = {
                "executed_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            if executed_by:
                update_data["executed_by"] = executed_by

            response = db_service.client.table("drift_approvals").update(
                update_data
            ).eq("id", approval_id).eq("tenant_id", tenant_id).execute()

            if response.data:
                logger.info(
                    f"Marked approval {approval_id} as executed "
                    f"(tenant_id={tenant_id}, executed_by={executed_by})"
                )
                return True

            return False
        except Exception as e:
            logger.error(
                f"Failed to mark approval {approval_id} as executed: {e}"
            )
            return False

    async def validate_incident_exists(
        self,
        tenant_id: str,
        incident_id: str
    ) -> bool:
        """
        Validate that an incident exists and is not closed.

        Args:
            tenant_id: The tenant ID
            incident_id: The incident ID

        Returns:
            True if incident exists and is not closed, False otherwise
        """
        try:
            response = db_service.client.table("drift_incidents").select(
                "id, status"
            ).eq("tenant_id", tenant_id).eq("id", incident_id).execute()

            if not response.data or len(response.data) == 0:
                logger.warning(
                    f"Incident {incident_id} not found for tenant {tenant_id}"
                )
                return False

            incident = response.data[0]
            if incident.get("status") == "closed":
                logger.warning(
                    f"Incident {incident_id} is closed and cannot be modified"
                )
                return False

            return True
        except Exception as e:
            logger.error(
                f"Failed to validate incident {incident_id} existence: {e}"
            )
            return False

    async def get_action_audit_summary(
        self,
        tenant_id: str,
        incident_id: str,
        action_type: Optional[GatedActionType] = None
    ) -> Dict[str, Any]:
        """
        Get audit summary of all approval actions for an incident.

        This provides a comprehensive view of all approval requests and decisions
        for a specific incident, useful for compliance reporting.

        Args:
            tenant_id: The tenant ID
            incident_id: The incident ID
            action_type: Optional filter by action type

        Returns:
            Summary dict with approval history and statistics
        """
        try:
            query = db_service.client.table("drift_approvals").select(
                "*"
            ).eq("tenant_id", tenant_id).eq("incident_id", incident_id)

            if action_type:
                approval_type_map = {
                    GatedActionType.ACKNOWLEDGE: "acknowledge",
                    GatedActionType.EXTEND_TTL: "extend_ttl",
                    GatedActionType.RECONCILE: "reconcile",
                }
                approval_type = approval_type_map.get(action_type)
                if approval_type:
                    query = query.eq("approval_type", approval_type)

            response = query.order("created_at", desc=True).execute()

            approvals = response.data or []

            # Calculate statistics
            total = len(approvals)
            pending = len([a for a in approvals if a["status"] == "pending"])
            approved = len([a for a in approvals if a["status"] == "approved"])
            rejected = len([a for a in approvals if a["status"] == "rejected"])
            cancelled = len([a for a in approvals if a["status"] == "cancelled"])
            executed = len([a for a in approvals if a.get("executed_at")])

            return {
                "incident_id": incident_id,
                "action_type": action_type.value if action_type else "all",
                "total_approvals": total,
                "statistics": {
                    "pending": pending,
                    "approved": approved,
                    "rejected": rejected,
                    "cancelled": cancelled,
                    "executed": executed,
                },
                "approvals": approvals,
            }
        except Exception as e:
            logger.error(
                f"Failed to get action audit summary for incident {incident_id}: {e}"
            )
            return {
                "incident_id": incident_id,
                "error": str(e),
                "total_approvals": 0,
                "statistics": {},
                "approvals": [],
            }


# Singleton instance
gated_action_service = GatedActionService()
