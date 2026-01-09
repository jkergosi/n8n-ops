"""Rate limiting service with sliding window algorithm.

This service provides in-memory rate limiting with per-user and per-tenant limits.
Uses a sliding window approach to track requests within time windows.
"""
from typing import Dict, Tuple, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    Tracks requests in time windows and enforces per-user and per-tenant limits.
    Thread-safe for single-process deployments.
    """

    def __init__(
        self,
        user_limit_per_minute: int = 60,
        tenant_limit_per_minute: int = 300,
        window_seconds: int = 60
    ):
        """
        Initialize the rate limiter.

        Args:
            user_limit_per_minute: Maximum requests per minute per user
            tenant_limit_per_minute: Maximum requests per minute per tenant
            window_seconds: Time window in seconds for rate limiting (default: 60)
        """
        self.user_limit = user_limit_per_minute
        self.tenant_limit = tenant_limit_per_minute
        self.window_seconds = window_seconds

        # Storage: key -> deque of timestamps
        self._user_requests: Dict[str, deque] = defaultdict(deque)
        self._tenant_requests: Dict[str, deque] = defaultdict(deque)

        logger.info(
            f"RateLimiter initialized: {user_limit_per_minute} req/min/user, "
            f"{tenant_limit_per_minute} req/min/tenant, {window_seconds}s window"
        )

    def _clean_old_requests(self, request_queue: deque, now: datetime) -> None:
        """
        Remove requests older than the time window.

        Args:
            request_queue: Queue of request timestamps
            now: Current timestamp
        """
        cutoff_time = now - timedelta(seconds=self.window_seconds)
        while request_queue and request_queue[0] < cutoff_time:
            request_queue.popleft()

    def check_rate_limit(
        self,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Check if a request should be allowed based on rate limits.

        Args:
            user_id: User identifier (optional)
            tenant_id: Tenant identifier (optional)

        Returns:
            Tuple of (allowed, limit_type, retry_after_seconds):
            - allowed: True if request is allowed, False if rate limited
            - limit_type: "user" or "tenant" if rate limited, None otherwise
            - retry_after_seconds: Seconds until rate limit resets, None if allowed
        """
        now = datetime.utcnow()

        # Check user rate limit
        if user_id:
            user_queue = self._user_requests[user_id]
            self._clean_old_requests(user_queue, now)

            if len(user_queue) >= self.user_limit:
                # Calculate retry-after based on oldest request in window
                oldest_request = user_queue[0]
                retry_after = int((oldest_request + timedelta(seconds=self.window_seconds) - now).total_seconds()) + 1
                logger.warning(
                    f"User rate limit exceeded: user_id={user_id}, "
                    f"count={len(user_queue)}, limit={self.user_limit}"
                )
                return False, "user", retry_after

        # Check tenant rate limit
        if tenant_id:
            tenant_queue = self._tenant_requests[tenant_id]
            self._clean_old_requests(tenant_queue, now)

            if len(tenant_queue) >= self.tenant_limit:
                # Calculate retry-after based on oldest request in window
                oldest_request = tenant_queue[0]
                retry_after = int((oldest_request + timedelta(seconds=self.window_seconds) - now).total_seconds()) + 1
                logger.warning(
                    f"Tenant rate limit exceeded: tenant_id={tenant_id}, "
                    f"count={len(tenant_queue)}, limit={self.tenant_limit}"
                )
                return False, "tenant", retry_after

        return True, None, None

    def record_request(
        self,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> None:
        """
        Record a request for rate limiting tracking.

        Should be called after check_rate_limit returns True.

        Args:
            user_id: User identifier (optional)
            tenant_id: Tenant identifier (optional)
        """
        now = datetime.utcnow()

        if user_id:
            self._user_requests[user_id].append(now)

        if tenant_id:
            self._tenant_requests[tenant_id].append(now)

    def get_current_usage(
        self,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Get current request counts for user and/or tenant.

        Args:
            user_id: User identifier (optional)
            tenant_id: Tenant identifier (optional)

        Returns:
            Dictionary with current counts:
            - user_count: Current requests in window for user
            - user_limit: User rate limit
            - tenant_count: Current requests in window for tenant
            - tenant_limit: Tenant rate limit
        """
        now = datetime.utcnow()
        result = {}

        if user_id:
            user_queue = self._user_requests[user_id]
            self._clean_old_requests(user_queue, now)
            result["user_count"] = len(user_queue)
            result["user_limit"] = self.user_limit

        if tenant_id:
            tenant_queue = self._tenant_requests[tenant_id]
            self._clean_old_requests(tenant_queue, now)
            result["tenant_count"] = len(tenant_queue)
            result["tenant_limit"] = self.tenant_limit

        return result

    def reset(self) -> None:
        """Reset all rate limit counters. Useful for testing."""
        self._user_requests.clear()
        self._tenant_requests.clear()
        logger.info("Rate limiter counters reset")


# Global rate limiter instance
_rate_limiter_instance: Optional[RateLimiter] = None


def get_rate_limiter(
    user_limit: int = 60,
    tenant_limit: int = 300,
    window_seconds: int = 60
) -> RateLimiter:
    """
    Get or create the global rate limiter instance.

    Args:
        user_limit: Maximum requests per minute per user
        tenant_limit: Maximum requests per minute per tenant
        window_seconds: Time window in seconds

    Returns:
        Global RateLimiter instance
    """
    global _rate_limiter_instance

    if _rate_limiter_instance is None:
        _rate_limiter_instance = RateLimiter(
            user_limit_per_minute=user_limit,
            tenant_limit_per_minute=tenant_limit,
            window_seconds=window_seconds
        )

    return _rate_limiter_instance
