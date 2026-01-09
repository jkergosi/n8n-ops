"""Audit service for entitlements logging (Phase 3) and approval audit logging."""
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from app.services.database import db_service
from app.schemas.entitlements import (
    AccessResult,
    AccessType,
    AuditAction,
    AuditEntityType,
    FeatureAccessLogCreate,
    FeatureAccessLogResponse,
    FeatureConfigAuditResponse,
)
from app.schemas.drift_policy import (
    ApprovalAuditEventType,
    ApprovalType,
    ApprovalStatus,
    ApprovalAuditResponse,
)

logger = logging.getLogger(__name__)


class AuditService:
    """
    Service for logging entitlement configuration changes, access events, and approval workflows.

    Phase 3: Provides audit trail for:
    - Configuration changes (plan assignments, overrides)
    - Access events (denials, limit exceeded)

    Drift Governance: Provides audit trail for:
    - Approval workflows (requested, approved, rejected, cancelled)
    - Action execution (executed, execution_failed)
    - Auto-approval and expiration events
    """

    # ==========================================================================
    # Configuration Audit Logging
    # ==========================================================================

    async def log_config_change(
        self,
        tenant_id: Optional[str],
        entity_type: AuditEntityType,
        entity_id: str,
        action: AuditAction,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        changed_by: Optional[str] = None,
        feature_key: Optional[str] = None,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[str]:
        """
        Log a configuration change to the audit table.

        Returns the audit record ID if successful, None otherwise.
        """
        try:
            data = {
                "tenant_id": tenant_id,
                "entity_type": entity_type.value if isinstance(entity_type, AuditEntityType) else entity_type,
                "entity_id": entity_id,
                "action": action.value if isinstance(action, AuditAction) else action,
                "old_value": old_value,
                "new_value": new_value,
                "changed_by": changed_by,
                "feature_key": feature_key,
                "reason": reason,
                "ip_address": ip_address,
                "user_agent": user_agent,
            }

            response = db_service.client.table("feature_config_audit").insert(data).execute()

            if response.data:
                audit_id = response.data[0].get("id")
                logger.info(
                    f"Audit logged: {action} on {entity_type} {entity_id} "
                    f"for tenant {tenant_id}"
                )
                return audit_id
            return None
        except Exception as e:
            logger.error(f"Failed to log config change: {e}")
            return None

    async def get_config_audit_logs(
        self,
        tenant_id: Optional[str] = None,
        entity_type: Optional[AuditEntityType] = None,
        feature_key: Optional[str] = None,
        changed_by: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[List[FeatureConfigAuditResponse], int]:
        """
        Get configuration audit logs with filtering and pagination.

        Returns (logs, total_count).
        """
        try:
            query = db_service.client.table("feature_config_audit").select(
                "*, changed_by_user:changed_by(email)",
                count="exact"
            )

            if tenant_id:
                query = query.eq("tenant_id", tenant_id)
            if entity_type:
                query = query.eq("entity_type", entity_type.value if isinstance(entity_type, AuditEntityType) else entity_type)
            if feature_key:
                query = query.eq("feature_key", feature_key)
            if changed_by:
                query = query.eq("changed_by", changed_by)

            # Pagination
            offset = (page - 1) * page_size
            query = query.order("changed_at", desc=True).range(offset, offset + page_size - 1)

            response = query.execute()
            total = response.count or 0

            logs = []
            for row in response.data or []:
                changed_by_user = row.get("changed_by_user", {}) or {}
                logs.append(FeatureConfigAuditResponse(
                    id=row["id"],
                    tenant_id=row.get("tenant_id"),
                    entity_type=row["entity_type"],
                    entity_id=row["entity_id"],
                    feature_key=row.get("feature_key"),
                    action=row["action"],
                    old_value=row.get("old_value"),
                    new_value=row.get("new_value"),
                    changed_by=row.get("changed_by"),
                    changed_by_email=changed_by_user.get("email"),
                    changed_at=row["changed_at"],
                    reason=row.get("reason"),
                ))

            return logs, total
        except Exception as e:
            logger.error(f"Failed to get config audit logs: {e}")
            return [], 0

    # ==========================================================================
    # Access Logging (Denials and Limit Exceeded)
    # ==========================================================================

    async def log_access(
        self,
        tenant_id: str,
        feature_key: str,
        access_type: AccessType,
        result: AccessResult,
        user_id: Optional[str] = None,
        current_value: Optional[int] = None,
        limit_value: Optional[int] = None,
        endpoint: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[str]:
        """
        Log a feature access event (especially denials).

        Returns the log record ID if successful, None otherwise.
        """
        try:
            data = {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "feature_key": feature_key,
                "access_type": access_type.value if isinstance(access_type, AccessType) else access_type,
                "result": result.value if isinstance(result, AccessResult) else result,
                "current_value": current_value,
                "limit_value": limit_value,
                "endpoint": endpoint,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
            }

            response = db_service.client.table("feature_access_log").insert(data).execute()

            if response.data:
                log_id = response.data[0].get("id")
                if result in [AccessResult.DENIED, AccessResult.LIMIT_EXCEEDED]:
                    logger.warning(
                        f"Access {result.value}: {feature_key} for tenant {tenant_id}, "
                        f"user {user_id}, endpoint {endpoint}"
                    )
                return log_id
            return None
        except Exception as e:
            logger.error(f"Failed to log access event: {e}")
            return None

    async def log_denial(
        self,
        tenant_id: str,
        feature_key: str,
        user_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[str]:
        """Convenience method for logging flag denials."""
        return await self.log_access(
            tenant_id=tenant_id,
            feature_key=feature_key,
            access_type=AccessType.FLAG_CHECK,
            result=AccessResult.DENIED,
            user_id=user_id,
            endpoint=endpoint,
            ip_address=ip_address,
        )

    async def log_limit_exceeded(
        self,
        tenant_id: str,
        feature_key: str,
        current_value: int,
        limit_value: int,
        user_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        resource_type: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[str]:
        """Convenience method for logging limit exceeded events."""
        return await self.log_access(
            tenant_id=tenant_id,
            feature_key=feature_key,
            access_type=AccessType.LIMIT_CHECK,
            result=AccessResult.LIMIT_EXCEEDED,
            user_id=user_id,
            current_value=current_value,
            limit_value=limit_value,
            endpoint=endpoint,
            resource_type=resource_type,
            ip_address=ip_address,
        )

    async def get_access_logs(
        self,
        tenant_id: str,
        feature_key: Optional[str] = None,
        result: Optional[AccessResult] = None,
        user_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[List[FeatureAccessLogResponse], int]:
        """
        Get access logs with filtering and pagination.

        Returns (logs, total_count).
        """
        try:
            query = db_service.client.table("feature_access_log").select(
                "*, user:user_id(email)",
                count="exact"
            ).eq("tenant_id", tenant_id)

            if feature_key:
                query = query.eq("feature_key", feature_key)
            if result:
                query = query.eq("result", result.value if isinstance(result, AccessResult) else result)
            if user_id:
                query = query.eq("user_id", user_id)

            # Pagination
            offset = (page - 1) * page_size
            query = query.order("accessed_at", desc=True).range(offset, offset + page_size - 1)

            response = query.execute()
            total = response.count or 0

            logs = []
            for row in response.data or []:
                user = row.get("user", {}) or {}
                logs.append(FeatureAccessLogResponse(
                    id=row["id"],
                    tenant_id=row["tenant_id"],
                    user_id=row.get("user_id"),
                    user_email=user.get("email"),
                    feature_key=row["feature_key"],
                    access_type=row["access_type"],
                    result=row["result"],
                    current_value=row.get("current_value"),
                    limit_value=row.get("limit_value"),
                    endpoint=row.get("endpoint"),
                    resource_type=row.get("resource_type"),
                    resource_id=row.get("resource_id"),
                    accessed_at=row["accessed_at"],
                ))

            return logs, total
        except Exception as e:
            logger.error(f"Failed to get access logs: {e}")
            return [], 0

    async def get_denial_summary(
        self,
        tenant_id: str,
        days: int = 30,
    ) -> Dict[str, int]:
        """
        Get a summary of denials by feature for the last N days.

        Returns {feature_key: count}.
        """
        try:
            # Get denials in the last N days
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(days=days)

            response = db_service.client.table("feature_access_log").select(
                "feature_key"
            ).eq("tenant_id", tenant_id).in_(
                "result", ["denied", "limit_exceeded"]
            ).gte("accessed_at", cutoff.isoformat()).execute()

            # Count by feature
            summary = {}
            for row in response.data or []:
                feature = row["feature_key"]
                summary[feature] = summary.get(feature, 0) + 1

            return summary
        except Exception as e:
            logger.error(f"Failed to get denial summary: {e}")
            return {}

    # ==========================================================================
    # Approval Audit Logging (Drift Governance)
    # ==========================================================================

    async def log_approval_event(
        self,
        tenant_id: str,
        approval_id: str,
        incident_id: str,
        event_type: ApprovalAuditEventType,
        actor_id: str,
        approval_type: ApprovalType,
        previous_status: Optional[ApprovalStatus] = None,
        new_status: Optional[ApprovalStatus] = None,
        action_metadata: Optional[Dict[str, Any]] = None,
        execution_result: Optional[Dict[str, Any]] = None,
        execution_error: Optional[str] = None,
        reason: Optional[str] = None,
        actor_email: Optional[str] = None,
        actor_name: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[str]:
        """
        Log an approval workflow event to the audit table.

        This creates a comprehensive audit trail for all approval-related actions:
        - Approval requests (requested)
        - Approval decisions (approved, rejected)
        - Approval cancellations (cancelled)
        - Action execution (executed, execution_failed)
        - Auto-approval events (auto_approved)
        - Approval expiration (expired)

        Args:
            tenant_id: The tenant ID
            approval_id: The approval request ID
            incident_id: The drift incident ID
            event_type: The type of approval event
            actor_id: ID of the user performing the action
            approval_type: The type of approval (acknowledge, extend_ttl, reconcile, etc.)
            previous_status: The status before the event (if applicable)
            new_status: The status after the event (if applicable)
            action_metadata: Additional metadata about the action
            execution_result: Result data from action execution
            execution_error: Error message if execution failed
            reason: Human-readable reason for the event
            actor_email: Email of the actor
            actor_name: Name of the actor
            ip_address: IP address of the actor
            user_agent: User agent of the actor

        Returns:
            The audit record ID if successful, None otherwise.
        """
        try:
            data = {
                "tenant_id": tenant_id,
                "approval_id": approval_id,
                "incident_id": incident_id,
                "event_type": event_type.value if isinstance(event_type, ApprovalAuditEventType) else event_type,
                "actor_id": actor_id,
                "actor_email": actor_email,
                "actor_name": actor_name,
                "approval_type": approval_type.value if isinstance(approval_type, ApprovalType) else approval_type,
                "previous_status": previous_status.value if isinstance(previous_status, ApprovalStatus) else previous_status,
                "new_status": new_status.value if isinstance(new_status, ApprovalStatus) else new_status,
                "action_metadata": action_metadata or {},
                "execution_result": execution_result,
                "execution_error": execution_error,
                "reason": reason,
                "ip_address": ip_address,
                "user_agent": user_agent,
            }

            response = db_service.client.table("approval_audit_log").insert(data).execute()

            if response.data:
                audit_id = response.data[0].get("id")
                logger.info(
                    f"Approval audit logged: {event_type} for approval {approval_id} "
                    f"(tenant={tenant_id}, incident={incident_id}, actor={actor_id})"
                )
                return audit_id
            return None
        except Exception as e:
            logger.error(f"Failed to log approval event: {e}")
            return None

    async def log_approval_requested(
        self,
        tenant_id: str,
        approval_id: str,
        incident_id: str,
        actor_id: str,
        approval_type: ApprovalType,
        reason: Optional[str] = None,
        action_metadata: Optional[Dict[str, Any]] = None,
        actor_email: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[str]:
        """
        Convenience method for logging approval request creation.

        Args:
            tenant_id: The tenant ID
            approval_id: The approval request ID
            incident_id: The drift incident ID
            actor_id: ID of the user requesting approval
            approval_type: The type of approval being requested
            reason: Reason for the approval request
            action_metadata: Additional metadata (e.g., extension_hours for extend_ttl)
            actor_email: Email of the requester
            ip_address: IP address of the requester

        Returns:
            The audit record ID if successful, None otherwise.
        """
        return await self.log_approval_event(
            tenant_id=tenant_id,
            approval_id=approval_id,
            incident_id=incident_id,
            event_type=ApprovalAuditEventType.requested,
            actor_id=actor_id,
            approval_type=approval_type,
            previous_status=None,
            new_status=ApprovalStatus.pending,
            action_metadata=action_metadata,
            reason=reason,
            actor_email=actor_email,
            ip_address=ip_address,
        )

    async def log_approval_decision(
        self,
        tenant_id: str,
        approval_id: str,
        incident_id: str,
        actor_id: str,
        approval_type: ApprovalType,
        decision: ApprovalStatus,
        decision_notes: Optional[str] = None,
        actor_email: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[str]:
        """
        Convenience method for logging approval decision (approved/rejected).

        Args:
            tenant_id: The tenant ID
            approval_id: The approval request ID
            incident_id: The drift incident ID
            actor_id: ID of the user making the decision
            approval_type: The type of approval
            decision: The decision (approved or rejected)
            decision_notes: Notes explaining the decision
            actor_email: Email of the approver/rejector
            ip_address: IP address of the decision maker

        Returns:
            The audit record ID if successful, None otherwise.
        """
        event_type = (
            ApprovalAuditEventType.approved
            if decision == ApprovalStatus.approved
            else ApprovalAuditEventType.rejected
        )

        return await self.log_approval_event(
            tenant_id=tenant_id,
            approval_id=approval_id,
            incident_id=incident_id,
            event_type=event_type,
            actor_id=actor_id,
            approval_type=approval_type,
            previous_status=ApprovalStatus.pending,
            new_status=decision,
            reason=decision_notes,
            actor_email=actor_email,
            ip_address=ip_address,
        )

    async def log_approval_executed(
        self,
        tenant_id: str,
        approval_id: str,
        incident_id: str,
        actor_id: str,
        approval_type: ApprovalType,
        execution_result: Optional[Dict[str, Any]] = None,
        actor_email: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[str]:
        """
        Convenience method for logging successful approval action execution.

        Args:
            tenant_id: The tenant ID
            approval_id: The approval request ID
            incident_id: The drift incident ID
            actor_id: ID of the user executing the action
            approval_type: The type of approval
            execution_result: Result data from the action execution
            actor_email: Email of the executor
            ip_address: IP address of the executor

        Returns:
            The audit record ID if successful, None otherwise.
        """
        return await self.log_approval_event(
            tenant_id=tenant_id,
            approval_id=approval_id,
            incident_id=incident_id,
            event_type=ApprovalAuditEventType.executed,
            actor_id=actor_id,
            approval_type=approval_type,
            execution_result=execution_result,
            actor_email=actor_email,
            ip_address=ip_address,
        )

    async def log_approval_execution_failed(
        self,
        tenant_id: str,
        approval_id: str,
        incident_id: str,
        actor_id: str,
        approval_type: ApprovalType,
        execution_error: str,
        actor_email: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[str]:
        """
        Convenience method for logging failed approval action execution.

        Args:
            tenant_id: The tenant ID
            approval_id: The approval request ID
            incident_id: The drift incident ID
            actor_id: ID of the user who attempted execution
            approval_type: The type of approval
            execution_error: Error message describing the failure
            actor_email: Email of the executor
            ip_address: IP address of the executor

        Returns:
            The audit record ID if successful, None otherwise.
        """
        return await self.log_approval_event(
            tenant_id=tenant_id,
            approval_id=approval_id,
            incident_id=incident_id,
            event_type=ApprovalAuditEventType.execution_failed,
            actor_id=actor_id,
            approval_type=approval_type,
            execution_error=execution_error,
            actor_email=actor_email,
            ip_address=ip_address,
        )

    async def log_approval_cancelled(
        self,
        tenant_id: str,
        approval_id: str,
        incident_id: str,
        actor_id: str,
        approval_type: ApprovalType,
        reason: Optional[str] = None,
        actor_email: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[str]:
        """
        Convenience method for logging approval cancellation.

        Args:
            tenant_id: The tenant ID
            approval_id: The approval request ID
            incident_id: The drift incident ID
            actor_id: ID of the user cancelling the approval
            approval_type: The type of approval
            reason: Reason for cancellation
            actor_email: Email of the canceller
            ip_address: IP address of the canceller

        Returns:
            The audit record ID if successful, None otherwise.
        """
        return await self.log_approval_event(
            tenant_id=tenant_id,
            approval_id=approval_id,
            incident_id=incident_id,
            event_type=ApprovalAuditEventType.cancelled,
            actor_id=actor_id,
            approval_type=approval_type,
            previous_status=ApprovalStatus.pending,
            new_status=ApprovalStatus.cancelled,
            reason=reason,
            actor_email=actor_email,
            ip_address=ip_address,
        )

    async def get_approval_audit_logs(
        self,
        tenant_id: str,
        approval_id: Optional[str] = None,
        incident_id: Optional[str] = None,
        event_type: Optional[ApprovalAuditEventType] = None,
        approval_type: Optional[ApprovalType] = None,
        actor_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[List[ApprovalAuditResponse], int]:
        """
        Get approval audit logs with filtering and pagination.

        Args:
            tenant_id: The tenant ID
            approval_id: Filter by specific approval request ID
            incident_id: Filter by specific incident ID
            event_type: Filter by event type
            approval_type: Filter by approval type
            actor_id: Filter by actor ID
            page: Page number (1-indexed)
            page_size: Number of records per page

        Returns:
            Tuple of (logs, total_count)
        """
        try:
            query = db_service.client.table("approval_audit_log").select(
                "*",
                count="exact"
            ).eq("tenant_id", tenant_id)

            if approval_id:
                query = query.eq("approval_id", approval_id)
            if incident_id:
                query = query.eq("incident_id", incident_id)
            if event_type:
                query = query.eq("event_type", event_type.value if isinstance(event_type, ApprovalAuditEventType) else event_type)
            if approval_type:
                query = query.eq("approval_type", approval_type.value if isinstance(approval_type, ApprovalType) else approval_type)
            if actor_id:
                query = query.eq("actor_id", actor_id)

            # Pagination
            offset = (page - 1) * page_size
            query = query.order("created_at", desc=True).range(offset, offset + page_size - 1)

            response = query.execute()
            total = response.count or 0

            logs = []
            for row in response.data or []:
                logs.append(ApprovalAuditResponse(
                    id=row["id"],
                    tenant_id=row["tenant_id"],
                    approval_id=row["approval_id"],
                    incident_id=row["incident_id"],
                    event_type=row["event_type"],
                    actor_id=row["actor_id"],
                    actor_email=row.get("actor_email"),
                    actor_name=row.get("actor_name"),
                    approval_type=row["approval_type"],
                    previous_status=row.get("previous_status"),
                    new_status=row.get("new_status"),
                    action_metadata=row.get("action_metadata", {}),
                    execution_result=row.get("execution_result"),
                    execution_error=row.get("execution_error"),
                    reason=row.get("reason"),
                    ip_address=row.get("ip_address"),
                    user_agent=row.get("user_agent"),
                    created_at=row["created_at"],
                ))

            logger.info(
                f"Retrieved {len(logs)} approval audit logs "
                f"(tenant={tenant_id}, total={total})"
            )
            return logs, total
        except Exception as e:
            logger.error(f"Failed to get approval audit logs: {e}")
            return [], 0

    async def get_approval_timeline(
        self,
        tenant_id: str,
        approval_id: str,
    ) -> List[ApprovalAuditResponse]:
        """
        Get complete timeline of events for a specific approval request.

        This provides a chronological view of all events related to a single
        approval request, useful for understanding the complete approval workflow.

        Args:
            tenant_id: The tenant ID
            approval_id: The approval request ID

        Returns:
            List of approval audit events in chronological order
        """
        logs, _ = await self.get_approval_audit_logs(
            tenant_id=tenant_id,
            approval_id=approval_id,
            page=1,
            page_size=1000,  # Get all events for this approval
        )
        # Reverse to get chronological order (oldest first)
        return list(reversed(logs))

    async def get_incident_approval_history(
        self,
        tenant_id: str,
        incident_id: str,
    ) -> List[ApprovalAuditResponse]:
        """
        Get complete approval history for a specific incident.

        This shows all approval-related events across all approval requests
        for an incident, useful for compliance and reporting.

        Args:
            tenant_id: The tenant ID
            incident_id: The drift incident ID

        Returns:
            List of all approval audit events for the incident
        """
        logs, _ = await self.get_approval_audit_logs(
            tenant_id=tenant_id,
            incident_id=incident_id,
            page=1,
            page_size=1000,  # Get all events for this incident
        )
        return logs

    async def get_approval_audit_summary(
        self,
        tenant_id: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get summary statistics of approval events for the last N days.

        Provides aggregate metrics useful for governance dashboards:
        - Total approval requests
        - Approval/rejection rates
        - Most common approval types
        - Execution success/failure rates

        Args:
            tenant_id: The tenant ID
            days: Number of days to include in summary

        Returns:
            Dictionary with approval statistics
        """
        try:
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(days=days)

            response = db_service.client.table("approval_audit_log").select(
                "event_type, approval_type, execution_error"
            ).eq("tenant_id", tenant_id).gte("created_at", cutoff.isoformat()).execute()

            events = response.data or []

            # Calculate statistics
            stats = {
                "period_days": days,
                "total_events": len(events),
                "by_event_type": {},
                "by_approval_type": {},
                "execution_stats": {
                    "total_executions": 0,
                    "successful": 0,
                    "failed": 0,
                },
            }

            for event in events:
                event_type = event.get("event_type")
                approval_type = event.get("approval_type")

                # Count by event type
                stats["by_event_type"][event_type] = stats["by_event_type"].get(event_type, 0) + 1

                # Count by approval type
                stats["by_approval_type"][approval_type] = stats["by_approval_type"].get(approval_type, 0) + 1

                # Track execution statistics
                if event_type == "executed":
                    stats["execution_stats"]["total_executions"] += 1
                    stats["execution_stats"]["successful"] += 1
                elif event_type == "execution_failed":
                    stats["execution_stats"]["total_executions"] += 1
                    stats["execution_stats"]["failed"] += 1

            # Calculate approval rate
            requested = stats["by_event_type"].get("requested", 0)
            approved = stats["by_event_type"].get("approved", 0)
            rejected = stats["by_event_type"].get("rejected", 0)

            if requested > 0:
                stats["approval_rate"] = round((approved / requested) * 100, 2)
                stats["rejection_rate"] = round((rejected / requested) * 100, 2)
            else:
                stats["approval_rate"] = 0
                stats["rejection_rate"] = 0

            return stats
        except Exception as e:
            logger.error(f"Failed to get approval audit summary: {e}")
            return {
                "period_days": days,
                "total_events": 0,
                "error": str(e),
            }


# Singleton instance
audit_service = AuditService()
