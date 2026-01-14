"""
Drift Policy Enforcement Service - Centralized TTL/SLA policy enforcement.

This service is the single source of truth for drift policy enforcement during
promotion/deployment execution. It handles:
- TTL validation (expired drift incidents)
- SLA compliance checks (active drift blocking)
- Approval override verification

Implements fail-closed behavior for policy violations (blocks promotion) and
detailed logging/audit trail for compliance tracking.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import logging

from app.services.database import db_service
from app.services.entitlements_service import entitlements_service

logger = logging.getLogger(__name__)


class EnforcementResult(str, Enum):
    """Result of policy enforcement check."""
    ALLOWED = "allowed"
    BLOCKED_TTL_EXPIRED = "blocked_ttl_expired"
    BLOCKED_ACTIVE_DRIFT = "blocked_active_drift"
    BLOCKED_POLICY_VIOLATION = "blocked_policy_violation"


@dataclass
class PolicyEnforcementDecision:
    """
    Decision result from policy enforcement check.

    Attributes:
        allowed: Whether the action is allowed to proceed
        result: The enforcement result type
        reason: Human-readable reason for the decision
        incident_id: ID of the blocking incident (if any)
        incident_details: Additional details about the blocking incident
        policy_config: The policy configuration used for the decision
        correlation_id: Unique ID for tracking this enforcement check
    """
    allowed: bool
    result: EnforcementResult
    reason: Optional[str] = None
    incident_id: Optional[str] = None
    incident_details: Optional[Dict[str, Any]] = None
    policy_config: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert decision to dictionary for API responses."""
        return {
            "allowed": self.allowed,
            "result": self.result.value,
            "reason": self.reason,
            "incident_id": self.incident_id,
            "incident_details": self.incident_details,
            "policy_config": self.policy_config,
            "correlation_id": self.correlation_id,
        }


class DriftPolicyEnforcementService:
    """
    Centralized service for enforcing drift TTL and SLA policies.

    This service checks:
    1. Whether the tenant has drift policy entitlement
    2. Whether a drift policy is configured and enabled
    3. Whether active drift incidents violate the policy
    4. Whether TTL has expired for any active incidents
    5. Whether approval overrides exist for blocked incidents

    Implements fail-closed behavior: if policy enforcement cannot be
    determined, the action is blocked for safety.
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

    async def get_active_incidents(
        self,
        tenant_id: str,
        environment_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get active (non-closed) drift incidents for an environment.

        Args:
            tenant_id: The tenant ID
            environment_id: The environment ID to check

        Returns:
            List of active drift incidents
        """
        try:
            response = db_service.client.table("drift_incidents").select(
                "id, status, severity, expires_at, title, detected_at, acknowledged_at, owner_user_id"
            ).eq("tenant_id", tenant_id).eq("environment_id", environment_id).in_(
                "status", ["detected", "acknowledged", "stabilized"]
            ).order("detected_at", desc=True).execute()

            return response.data or []
        except Exception as e:
            logger.error(
                f"Failed to fetch active incidents for tenant {tenant_id}, "
                f"environment {environment_id}: {e}"
            )
            return []

    def is_incident_expired(self, incident: Dict[str, Any]) -> bool:
        """
        Check if an incident's TTL has expired.

        Args:
            incident: The incident to check

        Returns:
            True if the incident is expired, False otherwise
        """
        expires_at_str = incident.get("expires_at")
        if not expires_at_str:
            # No expiration set - not expired
            return False

        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            return now >= expires_at
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse expires_at '{expires_at_str}': {e}")
            return False

    def get_ttl_for_severity(
        self,
        policy: Dict[str, Any],
        severity: Optional[str]
    ) -> int:
        """
        Get the TTL hours for a given severity level.

        Args:
            policy: The drift policy configuration
            severity: The incident severity (critical, high, medium, low)

        Returns:
            TTL in hours for the given severity
        """
        severity_ttl_map = {
            "critical": policy.get("critical_ttl_hours", 24),
            "high": policy.get("high_ttl_hours", 48),
            "medium": policy.get("medium_ttl_hours", 72),
            "low": policy.get("low_ttl_hours", 168),
        }

        if severity and severity.lower() in severity_ttl_map:
            return severity_ttl_map[severity.lower()]

        return policy.get("default_ttl_hours", 72)

    async def check_enforcement(
        self,
        tenant_id: str,
        environment_id: str,
        correlation_id: Optional[str] = None
    ) -> PolicyEnforcementDecision:
        """
        Check if drift policy enforcement blocks the action.

        This is the main entry point for policy enforcement. It checks:
        1. Entitlement - does tenant have drift_policies feature
        2. Policy existence - is a policy configured
        3. Policy settings - are blocking options enabled
        4. Active incidents - are there blocking incidents
        5. TTL expiration - are any incidents expired

        Args:
            tenant_id: The tenant ID
            environment_id: The target environment ID
            correlation_id: Optional ID for tracking/logging

        Returns:
            PolicyEnforcementDecision with the enforcement result
        """
        from uuid import uuid4

        if not correlation_id:
            correlation_id = str(uuid4())

        logger.info(
            f"Drift policy enforcement check started "
            f"(tenant_id={tenant_id}, environment_id={environment_id}, "
            f"correlation_id={correlation_id})"
        )

        # Step 1: Check entitlement
        try:
            has_drift_policies = await entitlements_service.has_flag(
                tenant_id, "drift_policies"
            )
            if not has_drift_policies:
                logger.debug(
                    f"Tenant {tenant_id} does not have drift_policies entitlement, "
                    f"skipping enforcement (correlation_id={correlation_id})"
                )
                return PolicyEnforcementDecision(
                    allowed=True,
                    result=EnforcementResult.ALLOWED,
                    reason="Drift policies feature not enabled for tenant",
                    correlation_id=correlation_id,
                )
        except Exception as e:
            logger.warning(
                f"Failed to check drift_policies entitlement for tenant {tenant_id}: {e}. "
                f"Proceeding with enforcement check (fail-safe)."
            )
            # Continue with enforcement check even if entitlement check fails

        # Step 2: Get tenant policy
        policy = await self.get_tenant_policy(tenant_id)
        if not policy:
            logger.debug(
                f"No drift policy configured for tenant {tenant_id}, "
                f"allowing action (correlation_id={correlation_id})"
            )
            return PolicyEnforcementDecision(
                allowed=True,
                result=EnforcementResult.ALLOWED,
                reason="No drift policy configured for tenant",
                correlation_id=correlation_id,
            )

        # Step 3: Check if policy blocks anything
        block_on_drift = policy.get("block_deployments_on_drift", False)
        block_on_expired = policy.get("block_deployments_on_expired", False)

        if not block_on_drift and not block_on_expired:
            logger.debug(
                f"Drift policy blocking is disabled for tenant {tenant_id}, "
                f"allowing action (correlation_id={correlation_id})"
            )
            return PolicyEnforcementDecision(
                allowed=True,
                result=EnforcementResult.ALLOWED,
                reason="Drift policy blocking is not enabled",
                policy_config={
                    "block_deployments_on_drift": block_on_drift,
                    "block_deployments_on_expired": block_on_expired,
                },
                correlation_id=correlation_id,
            )

        # Step 4: Get active incidents
        active_incidents = await self.get_active_incidents(tenant_id, environment_id)

        if not active_incidents:
            logger.debug(
                f"No active drift incidents for environment {environment_id}, "
                f"allowing action (correlation_id={correlation_id})"
            )
            return PolicyEnforcementDecision(
                allowed=True,
                result=EnforcementResult.ALLOWED,
                reason="No active drift incidents",
                policy_config={
                    "block_deployments_on_drift": block_on_drift,
                    "block_deployments_on_expired": block_on_expired,
                },
                correlation_id=correlation_id,
            )

        # Step 5: Check for expired TTL (highest priority block)
        if block_on_expired:
            for incident in active_incidents:
                if self.is_incident_expired(incident):
                    incident_id = incident.get("id")
                    incident_title = incident.get("title", "Untitled")
                    severity = incident.get("severity", "unknown")
                    expires_at = incident.get("expires_at")

                    logger.warning(
                        f"Drift policy enforcement BLOCKED: TTL expired "
                        f"(tenant_id={tenant_id}, environment_id={environment_id}, "
                        f"incident_id={incident_id}, severity={severity}, "
                        f"expires_at={expires_at}, correlation_id={correlation_id})"
                    )

                    return PolicyEnforcementDecision(
                        allowed=False,
                        result=EnforcementResult.BLOCKED_TTL_EXPIRED,
                        reason=(
                            f"Drift incident '{incident_title}' has expired. "
                            f"Please resolve or extend the TTL before deploying."
                        ),
                        incident_id=incident_id,
                        incident_details={
                            "title": incident_title,
                            "severity": severity,
                            "status": incident.get("status"),
                            "expires_at": expires_at,
                            "detected_at": incident.get("detected_at"),
                            "owner_user_id": incident.get("owner_user_id"),
                        },
                        policy_config={
                            "block_deployments_on_drift": block_on_drift,
                            "block_deployments_on_expired": block_on_expired,
                        },
                        correlation_id=correlation_id,
                    )

        # Step 6: Check for active drift blocking
        if block_on_drift and active_incidents:
            # Get the most recent incident
            incident = active_incidents[0]
            incident_id = incident.get("id")
            incident_title = incident.get("title", "Untitled")
            severity = incident.get("severity", "unknown")

            logger.warning(
                f"Drift policy enforcement BLOCKED: Active drift incident "
                f"(tenant_id={tenant_id}, environment_id={environment_id}, "
                f"incident_id={incident_id}, severity={severity}, "
                f"correlation_id={correlation_id})"
            )

            return PolicyEnforcementDecision(
                allowed=False,
                result=EnforcementResult.BLOCKED_ACTIVE_DRIFT,
                reason=(
                    f"Active drift incident '{incident_title}' exists. "
                    f"Please resolve the incident before deploying."
                ),
                incident_id=incident_id,
                incident_details={
                    "title": incident_title,
                    "severity": severity,
                    "status": incident.get("status"),
                    "expires_at": incident.get("expires_at"),
                    "detected_at": incident.get("detected_at"),
                    "owner_user_id": incident.get("owner_user_id"),
                },
                policy_config={
                    "block_deployments_on_drift": block_on_drift,
                    "block_deployments_on_expired": block_on_expired,
                },
                correlation_id=correlation_id,
            )

        # All checks passed
        logger.info(
            f"Drift policy enforcement ALLOWED "
            f"(tenant_id={tenant_id}, environment_id={environment_id}, "
            f"correlation_id={correlation_id})"
        )

        return PolicyEnforcementDecision(
            allowed=True,
            result=EnforcementResult.ALLOWED,
            reason="All drift policy checks passed",
            policy_config={
                "block_deployments_on_drift": block_on_drift,
                "block_deployments_on_expired": block_on_expired,
            },
            correlation_id=correlation_id,
        )

    async def validate_ttl_compliance(
        self,
        tenant_id: str,
        incident_id: str
    ) -> Dict[str, Any]:
        """
        Validate TTL compliance for a specific incident.

        This method checks:
        1. Whether the incident exists
        2. Whether it has an expiration set
        3. Whether the TTL has expired
        4. Time remaining until expiration (if not expired)

        Args:
            tenant_id: The tenant ID
            incident_id: The incident ID to validate

        Returns:
            Dict with compliance information:
            {
                "compliant": bool,
                "incident_id": str,
                "expires_at": str | None,
                "is_expired": bool,
                "time_remaining_seconds": int | None,
                "severity": str | None,
                "expected_ttl_hours": int | None
            }
        """
        try:
            response = db_service.client.table("drift_incidents").select(
                "id, status, severity, expires_at, title"
            ).eq("tenant_id", tenant_id).eq("id", incident_id).single().execute()

            if not response.data:
                return {
                    "compliant": True,
                    "incident_id": incident_id,
                    "error": "Incident not found",
                }

            incident = response.data
            expires_at_str = incident.get("expires_at")
            severity = incident.get("severity")

            # Get policy for expected TTL
            policy = await self.get_tenant_policy(tenant_id)
            expected_ttl = self.get_ttl_for_severity(policy, severity) if policy else None

            if not expires_at_str:
                return {
                    "compliant": True,
                    "incident_id": incident_id,
                    "expires_at": None,
                    "is_expired": False,
                    "time_remaining_seconds": None,
                    "severity": severity,
                    "expected_ttl_hours": expected_ttl,
                    "message": "No expiration set for incident",
                }

            # Parse expiration time
            try:
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                return {
                    "compliant": True,
                    "incident_id": incident_id,
                    "expires_at": expires_at_str,
                    "error": "Invalid expires_at format",
                }

            now = datetime.now(timezone.utc)
            is_expired = now >= expires_at
            time_remaining = (expires_at - now).total_seconds() if not is_expired else 0

            return {
                "compliant": not is_expired,
                "incident_id": incident_id,
                "expires_at": expires_at_str,
                "is_expired": is_expired,
                "time_remaining_seconds": int(time_remaining) if time_remaining > 0 else 0,
                "severity": severity,
                "expected_ttl_hours": expected_ttl,
            }

        except Exception as e:
            logger.error(f"Failed to validate TTL compliance for incident {incident_id}: {e}")
            return {
                "compliant": False,
                "incident_id": incident_id,
                "error": str(e),
            }

    async def get_blocking_incidents_summary(
        self,
        tenant_id: str,
        environment_id: str
    ) -> Dict[str, Any]:
        """
        Get a summary of all blocking incidents for an environment.

        This provides a comprehensive view of all drift incidents that would
        block deployments, including their TTL status and severity.

        Args:
            tenant_id: The tenant ID
            environment_id: The environment ID

        Returns:
            Summary dict with blocking incidents and policy status
        """
        policy = await self.get_tenant_policy(tenant_id)
        active_incidents = await self.get_active_incidents(tenant_id, environment_id)

        if not policy:
            return {
                "has_policy": False,
                "blocking_enabled": False,
                "total_active_incidents": len(active_incidents),
                "blocking_incidents": [],
                "expired_incidents": [],
            }

        block_on_drift = policy.get("block_deployments_on_drift", False)
        block_on_expired = policy.get("block_deployments_on_expired", False)

        expired_incidents = []
        for incident in active_incidents:
            if self.is_incident_expired(incident):
                expired_incidents.append({
                    "id": incident.get("id"),
                    "title": incident.get("title"),
                    "severity": incident.get("severity"),
                    "expires_at": incident.get("expires_at"),
                    "status": incident.get("status"),
                })

        blocking_incidents = []
        if block_on_drift:
            for incident in active_incidents:
                blocking_incidents.append({
                    "id": incident.get("id"),
                    "title": incident.get("title"),
                    "severity": incident.get("severity"),
                    "status": incident.get("status"),
                    "is_expired": incident.get("id") in [e["id"] for e in expired_incidents],
                })

        return {
            "has_policy": True,
            "blocking_enabled": block_on_drift or block_on_expired,
            "block_on_drift": block_on_drift,
            "block_on_expired": block_on_expired,
            "total_active_incidents": len(active_incidents),
            "blocking_incidents": blocking_incidents,
            "expired_incidents": expired_incidents,
            "is_blocked": (block_on_expired and len(expired_incidents) > 0) or (block_on_drift and len(active_incidents) > 0),
        }


    async def check_approval_override(
        self,
        tenant_id: str,
        incident_id: str,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check if an explicit approval exists that allows overriding the policy block.

        This method checks for approved approvals that would allow a deployment to proceed
        despite an active drift incident or expired TTL. Valid override approvals include:
        - 'acknowledge': The drift has been acknowledged and deployment is approved
        - 'deployment_override': Explicit approval to deploy despite drift
        - 'extend_ttl': TTL has been extended (checked separately for TTL expiration)
        - 'close': The incident has been approved for closure

        Args:
            tenant_id: The tenant ID
            incident_id: The incident ID to check for overrides
            correlation_id: Optional ID for tracking/logging

        Returns:
            Dict containing:
            {
                "has_override": bool,
                "approval_id": str | None,
                "approval_type": str | None,
                "approved_by": str | None,
                "approved_at": str | None,
                "decision_notes": str | None,
                "reason": str
            }
        """
        from uuid import uuid4

        if not correlation_id:
            correlation_id = str(uuid4())

        logger.debug(
            f"Checking approval override for incident {incident_id} "
            f"(tenant_id={tenant_id}, correlation_id={correlation_id})"
        )

        try:
            # Query for approved approvals that can override deployment blocks
            # Valid override types: acknowledge, deployment_override, close
            # Note: extend_ttl approvals don't override - they extend the TTL,
            # which is checked separately in TTL expiration logic
            override_types = ["acknowledge", "deployment_override", "close"]

            response = db_service.client.table("drift_approvals").select(
                "id, approval_type, status, decided_by, decided_at, decision_notes, requested_by, requested_at"
            ).eq("tenant_id", tenant_id).eq("incident_id", incident_id).eq(
                "status", "approved"
            ).in_("approval_type", override_types).order(
                "decided_at", desc=True
            ).limit(1).execute()

            if response.data and len(response.data) > 0:
                approval = response.data[0]
                approval_id = approval.get("id")
                approval_type = approval.get("approval_type")
                decided_by = approval.get("decided_by")
                decided_at = approval.get("decided_at")
                decision_notes = approval.get("decision_notes")

                logger.info(
                    f"Found valid approval override for incident {incident_id}: "
                    f"approval_id={approval_id}, type={approval_type}, "
                    f"decided_by={decided_by} (correlation_id={correlation_id})"
                )

                return {
                    "has_override": True,
                    "approval_id": approval_id,
                    "approval_type": approval_type,
                    "approved_by": decided_by,
                    "approved_at": decided_at,
                    "decision_notes": decision_notes,
                    "reason": f"Deployment approved via '{approval_type}' approval",
                }

            logger.debug(
                f"No approval override found for incident {incident_id} "
                f"(correlation_id={correlation_id})"
            )

            return {
                "has_override": False,
                "approval_id": None,
                "approval_type": None,
                "approved_by": None,
                "approved_at": None,
                "decision_notes": None,
                "reason": "No approved override exists for this incident",
            }

        except Exception as e:
            logger.error(
                f"Failed to check approval override for incident {incident_id}: {e} "
                f"(correlation_id={correlation_id})"
            )
            # Fail-closed: if we can't check approvals, don't allow override
            return {
                "has_override": False,
                "approval_id": None,
                "approval_type": None,
                "approved_by": None,
                "approved_at": None,
                "decision_notes": None,
                "reason": f"Failed to verify approval: {str(e)}",
                "error": str(e),
            }

    async def check_enforcement_with_override(
        self,
        tenant_id: str,
        environment_id: str,
        correlation_id: Optional[str] = None
    ) -> PolicyEnforcementDecision:
        """
        Check policy enforcement with approval override support.

        This is an enhanced version of check_enforcement that also checks for
        approval overrides when a blocking incident is found. If a valid override
        exists, the action is allowed to proceed.

        Args:
            tenant_id: The tenant ID
            environment_id: The target environment ID
            correlation_id: Optional ID for tracking/logging

        Returns:
            PolicyEnforcementDecision with the enforcement result,
            including override information if applicable
        """
        from uuid import uuid4

        if not correlation_id:
            correlation_id = str(uuid4())

        # First, run the standard enforcement check
        decision = await self.check_enforcement(
            tenant_id=tenant_id,
            environment_id=environment_id,
            correlation_id=correlation_id,
        )

        # If allowed or no incident to check, return as-is
        if decision.allowed or not decision.incident_id:
            return decision

        # Check for approval override on the blocking incident
        logger.info(
            f"Checking for approval override on blocking incident {decision.incident_id} "
            f"(correlation_id={correlation_id})"
        )

        override_result = await self.check_approval_override(
            tenant_id=tenant_id,
            incident_id=decision.incident_id,
            correlation_id=correlation_id,
        )

        if override_result.get("has_override"):
            logger.info(
                f"Drift policy enforcement ALLOWED via override: "
                f"approval_id={override_result.get('approval_id')}, "
                f"type={override_result.get('approval_type')} "
                f"(tenant_id={tenant_id}, environment_id={environment_id}, "
                f"correlation_id={correlation_id})"
            )

            return PolicyEnforcementDecision(
                allowed=True,
                result=EnforcementResult.ALLOWED,
                reason=override_result.get("reason"),
                incident_id=decision.incident_id,
                incident_details={
                    **(decision.incident_details or {}),
                    "override_approval_id": override_result.get("approval_id"),
                    "override_approval_type": override_result.get("approval_type"),
                    "override_approved_by": override_result.get("approved_by"),
                    "override_approved_at": override_result.get("approved_at"),
                },
                policy_config=decision.policy_config,
                correlation_id=correlation_id,
            )

        # No override found, return the original blocking decision
        logger.debug(
            f"No approval override found, maintaining block "
            f"(correlation_id={correlation_id})"
        )
        return decision

    async def get_pending_overrides(
        self,
        tenant_id: str,
        incident_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get pending approval requests that could serve as deployment overrides.

        This helps users understand what approvals are in progress that could
        unblock their deployment.

        Args:
            tenant_id: The tenant ID
            incident_id: The incident ID

        Returns:
            List of pending approval requests
        """
        try:
            override_types = ["acknowledge", "deployment_override", "close"]

            response = db_service.client.table("drift_approvals").select(
                "id, approval_type, status, requested_by, requested_at, request_reason"
            ).eq("tenant_id", tenant_id).eq("incident_id", incident_id).eq(
                "status", "pending"
            ).in_("approval_type", override_types).order(
                "requested_at", desc=True
            ).execute()

            return response.data or []

        except Exception as e:
            logger.error(
                f"Failed to get pending overrides for incident {incident_id}: {e}"
            )
            return []


# Singleton instance
drift_policy_enforcement_service = DriftPolicyEnforcementService()
