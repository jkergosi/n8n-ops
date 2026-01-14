"""
Promotion Lock Service

Provides concurrency control for promotion operations to prevent multiple
promotions from executing against the same target environment simultaneously.

This service uses database-level checks against the promotions table to detect
active promotions, rather than advisory locks, since promotion operations
are long-running and span multiple HTTP requests.
"""
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from fastapi import HTTPException, status

from app.services.database import db_service

logger = logging.getLogger(__name__)


@dataclass
class PromotionConflict:
    """Information about a conflicting promotion."""
    promotion_id: str
    promotion_name: Optional[str]
    started_at: Optional[str]
    started_by: Optional[str]
    target_environment_id: str
    target_environment_name: Optional[str] = None


class PromotionConflictError(HTTPException):
    """
    Exception raised when a promotion cannot proceed due to another
    active promotion targeting the same environment.
    """
    def __init__(self, conflict: PromotionConflict):
        detail = {
            "error": "promotion_conflict",
            "message": f"Cannot start promotion: another promotion is already running for this environment",
            "blocking_promotion": {
                "id": conflict.promotion_id,
                "name": conflict.promotion_name,
                "started_at": conflict.started_at,
                "started_by": conflict.started_by,
                "target_environment_id": conflict.target_environment_id,
                "target_environment_name": conflict.target_environment_name,
            }
        }
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )
        self.conflict = conflict


class PromotionLockService:
    """
    Service for managing promotion concurrency control.

    Prevents race conditions when multiple users or systems attempt to
    promote workflows to the same target environment simultaneously.

    The service performs a check-and-acquire pattern:
    1. Check if any promotion is currently running for the target environment
    2. If not, the caller can proceed with the promotion
    3. If yes, raise PromotionConflictError with details about the blocking promotion

    Note: This service does NOT use database-level locks. Instead, it relies on
    the promotions table status field ('running') to track active promotions.
    The actual atomicity is ensured by:
    - Setting status to 'running' at promotion start
    - Checking for running status before allowing new promotions
    - Setting status to 'completed' or 'failed' at promotion end

    For additional safety, callers should update promotion status within a
    transaction when possible.
    """

    def __init__(self):
        self.db_service = db_service

    async def check_and_acquire_promotion_lock(
        self,
        tenant_id: str,
        target_environment_id: str,
        requesting_promotion_id: Optional[str] = None
    ) -> bool:
        """
        Check if a promotion can proceed and acquire a logical lock.

        This method checks if there are any active (running) promotions
        targeting the same environment. If there are, it raises a
        PromotionConflictError with details about the blocking promotion.

        Args:
            tenant_id: The tenant ID
            target_environment_id: The target environment for the promotion
            requesting_promotion_id: Optional ID of the promotion requesting the lock.
                                    If provided, this promotion will be excluded from
                                    the conflict check (useful for retry scenarios).

        Returns:
            True if the promotion can proceed (no conflicts found)

        Raises:
            PromotionConflictError: If another promotion is already running
                                   for the target environment
        """
        logger.info(
            f"Checking promotion lock for tenant={tenant_id}, "
            f"target_environment={target_environment_id}"
        )

        # Check for active promotion using the database service method
        active_promotion = await self.db_service.get_active_promotion_for_environment(
            tenant_id=tenant_id,
            target_environment_id=target_environment_id
        )

        if active_promotion is None:
            logger.info(
                f"No active promotion found for environment={target_environment_id}, "
                f"promotion can proceed"
            )
            return True

        # If we have a requesting promotion ID, check if the active promotion
        # is the same one (retry scenario)
        if requesting_promotion_id and active_promotion.get("id") == requesting_promotion_id:
            logger.info(
                f"Active promotion {requesting_promotion_id} is the requesting promotion, "
                f"allowing it to proceed"
            )
            return True

        # Found a conflicting promotion
        conflict = PromotionConflict(
            promotion_id=active_promotion.get("id"),
            promotion_name=active_promotion.get("name"),
            started_at=active_promotion.get("started_at"),
            started_by=active_promotion.get("created_by"),
            target_environment_id=target_environment_id,
            target_environment_name=active_promotion.get("target_environment_name"),
        )

        logger.warning(
            f"Promotion conflict detected: promotion {conflict.promotion_id} "
            f"is already running for environment {target_environment_id}"
        )

        raise PromotionConflictError(conflict)

    async def get_active_promotion_for_environment(
        self,
        tenant_id: str,
        target_environment_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get details about any active promotion for an environment.

        This is a convenience method for checking lock status without
        raising an exception.

        Args:
            tenant_id: The tenant ID
            target_environment_id: The target environment ID

        Returns:
            The active promotion record if one exists, None otherwise
        """
        return await self.db_service.get_active_promotion_for_environment(
            tenant_id=tenant_id,
            target_environment_id=target_environment_id
        )

    async def is_environment_locked(
        self,
        tenant_id: str,
        target_environment_id: str
    ) -> bool:
        """
        Check if an environment is currently locked by an active promotion.

        Args:
            tenant_id: The tenant ID
            target_environment_id: The target environment ID

        Returns:
            True if the environment has an active promotion, False otherwise
        """
        active_promotion = await self.db_service.get_active_promotion_for_environment(
            tenant_id=tenant_id,
            target_environment_id=target_environment_id
        )
        return active_promotion is not None


# Global service instance
promotion_lock_service = PromotionLockService()
