"""Rate limiting middleware for FastAPI.

This middleware enforces per-user and per-tenant rate limits on API v1 endpoints.
Exempts health checks and webhook endpoints from rate limiting.
"""
from typing import Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

from app.core.config import settings
from app.services.rate_limiter import get_rate_limiter
from app.services.auth_service import supabase_auth_service
from app.services.database import db_service

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce rate limits on API requests.

    This middleware:
    1. Checks if rate limiting is enabled
    2. Exempts specific paths (health, webhooks)
    3. Extracts user and tenant IDs from authentication
    4. Enforces per-user and per-tenant rate limits
    5. Returns HTTP 429 when limits are exceeded
    """

    # Paths exempt from rate limiting
    EXEMPT_PATHS = [
        "/health",
        "/api/v1/health",
        "/api/v1/webhooks",  # GitHub webhooks
        "/docs",
        "/openapi.json",
        "/redoc",
    ]

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.rate_limiter = get_rate_limiter(
            user_limit=settings.RATE_LIMIT_PER_USER_MINUTE,
            tenant_limit=settings.RATE_LIMIT_PER_TENANT_MINUTE,
            window_seconds=60
        )
        logger.info(
            f"RateLimitMiddleware initialized: enabled={settings.RATE_LIMIT_ENABLED}, "
            f"user_limit={settings.RATE_LIMIT_PER_USER_MINUTE}, "
            f"tenant_limit={settings.RATE_LIMIT_PER_TENANT_MINUTE}"
        )

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process each request and enforce rate limits.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware/handler in the chain

        Returns:
            Response: HTTP response or 429 if rate limited
        """
        # Skip rate limiting if disabled
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Skip exempt paths
        request_path = request.url.path
        if self._is_exempt_path(request_path):
            return await call_next(request)

        # Only rate limit API v1 endpoints
        if not request_path.startswith(settings.API_V1_PREFIX):
            return await call_next(request)

        # Extract user and tenant IDs from authentication
        user_id, tenant_id = await self._extract_user_tenant(request)

        # If no user/tenant ID, allow the request (authentication will handle it)
        if not user_id and not tenant_id:
            return await call_next(request)

        # Check rate limit
        allowed, limit_type, retry_after = self.rate_limiter.check_rate_limit(
            user_id=user_id,
            tenant_id=tenant_id
        )

        if not allowed:
            # Rate limit exceeded - return 429
            return self._create_rate_limit_response(
                limit_type=limit_type,
                retry_after=retry_after,
                user_id=user_id,
                tenant_id=tenant_id
            )

        # Record the request
        self.rate_limiter.record_request(user_id=user_id, tenant_id=tenant_id)

        # Get current usage for response headers
        usage = self.rate_limiter.get_current_usage(user_id=user_id, tenant_id=tenant_id)

        # Process the request
        response = await call_next(request)

        # Add rate limit headers to response
        if user_id and "user_count" in usage:
            response.headers["X-RateLimit-Limit-User"] = str(usage["user_limit"])
            response.headers["X-RateLimit-Remaining-User"] = str(
                max(0, usage["user_limit"] - usage["user_count"])
            )

        if tenant_id and "tenant_count" in usage:
            response.headers["X-RateLimit-Limit-Tenant"] = str(usage["tenant_limit"])
            response.headers["X-RateLimit-Remaining-Tenant"] = str(
                max(0, usage["tenant_limit"] - usage["tenant_count"])
            )

        return response

    def _is_exempt_path(self, path: str) -> bool:
        """
        Check if a path is exempt from rate limiting.

        Args:
            path: Request path

        Returns:
            True if path is exempt, False otherwise
        """
        return any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS)

    async def _extract_user_tenant(self, request: Request) -> tuple[Optional[str], Optional[str]]:
        """
        Extract user_id and tenant_id from the request.

        Args:
            request: The HTTP request

        Returns:
            Tuple of (user_id, tenant_id), both may be None
        """
        try:
            # Extract authorization header
            auth_header = request.headers.get("authorization", "")
            if not auth_header.lower().startswith("bearer "):
                return None, None

            token = auth_header.split(" ", 1)[1].strip()

            # Verify token and get user
            try:
                payload = await supabase_auth_service.verify_token(token)
                supabase_user_id = payload.get("sub")
                if not supabase_user_id:
                    return None, None
            except Exception:
                # Invalid token - let auth middleware handle it
                return None, None

            # Get user and tenant from database
            try:
                user_resp = db_service.client.table("users").select(
                    "id, tenant_id"
                ).eq(
                    "supabase_auth_id", supabase_user_id
                ).maybe_single().execute()

                if not user_resp.data:
                    return None, None

                user_data = user_resp.data
                user_id = user_data.get("id")
                tenant_id = user_data.get("tenant_id")

                return str(user_id) if user_id else None, str(tenant_id) if tenant_id else None

            except Exception as e:
                logger.warning(f"Failed to fetch user/tenant for rate limiting: {e}")
                return None, None

        except Exception as e:
            logger.error(f"Error extracting user/tenant for rate limiting: {e}")
            return None, None

    def _create_rate_limit_response(
        self,
        limit_type: str,
        retry_after: int,
        user_id: Optional[str],
        tenant_id: Optional[str]
    ) -> JSONResponse:
        """
        Create a 429 Rate Limit Exceeded response.

        Args:
            limit_type: "user" or "tenant"
            retry_after: Seconds until rate limit resets
            user_id: User ID (for logging)
            tenant_id: Tenant ID (for logging)

        Returns:
            JSONResponse with 429 status
        """
        # Get current usage for detailed error message
        usage = self.rate_limiter.get_current_usage(user_id=user_id, tenant_id=tenant_id)

        if limit_type == "user":
            message = (
                f"User rate limit exceeded. "
                f"Limit: {usage.get('user_limit', settings.RATE_LIMIT_PER_USER_MINUTE)} requests per minute. "
                f"Try again in {retry_after} seconds."
            )
            limit_value = usage.get("user_limit", settings.RATE_LIMIT_PER_USER_MINUTE)
        else:
            message = (
                f"Tenant rate limit exceeded. "
                f"Limit: {usage.get('tenant_limit', settings.RATE_LIMIT_PER_TENANT_MINUTE)} requests per minute. "
                f"Try again in {retry_after} seconds."
            )
            limit_value = usage.get("tenant_limit", settings.RATE_LIMIT_PER_TENANT_MINUTE)

        logger.warning(
            f"Rate limit exceeded: type={limit_type}, user_id={user_id}, "
            f"tenant_id={tenant_id}, retry_after={retry_after}s"
        )

        # Create response with standard headers
        headers = {
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": str(limit_value),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(retry_after),
        }

        return JSONResponse(
            status_code=429,
            content={
                "detail": message,
                "error": "rate_limit_exceeded",
                "limit_type": limit_type,
                "retry_after": retry_after
            },
            headers=headers
        )
