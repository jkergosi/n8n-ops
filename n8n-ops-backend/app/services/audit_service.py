"""Audit service for entitlements logging (Phase 3)."""
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

logger = logging.getLogger(__name__)


class AuditService:
    """
    Service for logging entitlement configuration changes and access events.

    Phase 3: Provides audit trail for:
    - Configuration changes (plan assignments, overrides)
    - Access events (denials, limit exceeded)
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


# Singleton instance
audit_service = AuditService()
