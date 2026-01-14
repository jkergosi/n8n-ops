"""
Unit tests for the rate limiting service and middleware.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.rate_limiter import RateLimiter


class TestRateLimiter:
    """Tests for RateLimiter service."""

    @pytest.mark.unit
    def test_rate_limiter_initialization(self):
        """RateLimiter should initialize with correct limits."""
        limiter = RateLimiter(user_limit_per_minute=100, tenant_limit_per_minute=500)
        assert limiter.user_limit == 100
        assert limiter.tenant_limit == 500
        assert limiter.window_seconds == 60

    @pytest.mark.unit
    def test_user_rate_limit_allows_requests_under_limit(self):
        """Should allow requests under the user rate limit."""
        limiter = RateLimiter(user_limit_per_minute=5, tenant_limit_per_minute=10)
        user_id = "test-user-1"

        # Make 5 requests (at limit)
        for i in range(5):
            allowed, limit_type, retry_after = limiter.check_rate_limit(user_id=user_id)
            assert allowed is True
            assert limit_type is None
            assert retry_after is None
            limiter.record_request(user_id=user_id)

    @pytest.mark.unit
    def test_user_rate_limit_blocks_requests_over_limit(self):
        """Should block requests over the user rate limit."""
        limiter = RateLimiter(user_limit_per_minute=3, tenant_limit_per_minute=10)
        user_id = "test-user-2"

        # Make 3 requests (reach limit)
        for i in range(3):
            allowed, limit_type, retry_after = limiter.check_rate_limit(user_id=user_id)
            assert allowed is True
            limiter.record_request(user_id=user_id)

        # 4th request should be blocked
        allowed, limit_type, retry_after = limiter.check_rate_limit(user_id=user_id)
        assert allowed is False
        assert limit_type == "user"
        assert retry_after > 0

    @pytest.mark.unit
    def test_tenant_rate_limit_allows_requests_under_limit(self):
        """Should allow requests under the tenant rate limit."""
        limiter = RateLimiter(user_limit_per_minute=10, tenant_limit_per_minute=5)
        tenant_id = "test-tenant-1"

        # Make 5 requests (at limit)
        for i in range(5):
            allowed, limit_type, retry_after = limiter.check_rate_limit(tenant_id=tenant_id)
            assert allowed is True
            assert limit_type is None
            assert retry_after is None
            limiter.record_request(tenant_id=tenant_id)

    @pytest.mark.unit
    def test_tenant_rate_limit_blocks_requests_over_limit(self):
        """Should block requests over the tenant rate limit."""
        limiter = RateLimiter(user_limit_per_minute=10, tenant_limit_per_minute=3)
        tenant_id = "test-tenant-2"

        # Make 3 requests (reach limit)
        for i in range(3):
            allowed, limit_type, retry_after = limiter.check_rate_limit(tenant_id=tenant_id)
            assert allowed is True
            limiter.record_request(tenant_id=tenant_id)

        # 4th request should be blocked
        allowed, limit_type, retry_after = limiter.check_rate_limit(tenant_id=tenant_id)
        assert allowed is False
        assert limit_type == "tenant"
        assert retry_after > 0

    @pytest.mark.unit
    def test_both_user_and_tenant_limits(self):
        """Should enforce both user and tenant limits."""
        limiter = RateLimiter(user_limit_per_minute=2, tenant_limit_per_minute=5)
        user_id = "test-user-3"
        tenant_id = "test-tenant-3"

        # Make 2 requests (reach user limit)
        for i in range(2):
            allowed, limit_type, retry_after = limiter.check_rate_limit(
                user_id=user_id, tenant_id=tenant_id
            )
            assert allowed is True
            limiter.record_request(user_id=user_id, tenant_id=tenant_id)

        # 3rd request should be blocked by user limit
        allowed, limit_type, retry_after = limiter.check_rate_limit(
            user_id=user_id, tenant_id=tenant_id
        )
        assert allowed is False
        assert limit_type == "user"

    @pytest.mark.unit
    def test_get_current_usage(self):
        """Should return current usage counts."""
        limiter = RateLimiter(user_limit_per_minute=10, tenant_limit_per_minute=20)
        user_id = "test-user-4"
        tenant_id = "test-tenant-4"

        # Make 3 requests
        for i in range(3):
            limiter.check_rate_limit(user_id=user_id, tenant_id=tenant_id)
            limiter.record_request(user_id=user_id, tenant_id=tenant_id)

        usage = limiter.get_current_usage(user_id=user_id, tenant_id=tenant_id)
        assert usage["user_count"] == 3
        assert usage["user_limit"] == 10
        assert usage["tenant_count"] == 3
        assert usage["tenant_limit"] == 20

    @pytest.mark.unit
    def test_reset_clears_all_counters(self):
        """Should clear all rate limit counters."""
        limiter = RateLimiter(user_limit_per_minute=10, tenant_limit_per_minute=20)
        user_id = "test-user-5"
        tenant_id = "test-tenant-5"

        # Make some requests
        for i in range(3):
            limiter.check_rate_limit(user_id=user_id, tenant_id=tenant_id)
            limiter.record_request(user_id=user_id, tenant_id=tenant_id)

        # Verify requests recorded
        usage = limiter.get_current_usage(user_id=user_id, tenant_id=tenant_id)
        assert usage["user_count"] == 3
        assert usage["tenant_count"] == 3

        # Reset
        limiter.reset()

        # Verify counters cleared
        usage = limiter.get_current_usage(user_id=user_id, tenant_id=tenant_id)
        assert usage["user_count"] == 0
        assert usage["tenant_count"] == 0

    @pytest.mark.unit
    def test_different_users_tracked_separately(self):
        """Should track different users separately."""
        limiter = RateLimiter(user_limit_per_minute=2, tenant_limit_per_minute=10)
        user_id_1 = "test-user-6"
        user_id_2 = "test-user-7"

        # User 1 reaches limit
        for i in range(2):
            limiter.check_rate_limit(user_id=user_id_1)
            limiter.record_request(user_id=user_id_1)

        # User 1 blocked
        allowed, limit_type, _ = limiter.check_rate_limit(user_id=user_id_1)
        assert allowed is False
        assert limit_type == "user"

        # User 2 still allowed
        allowed, limit_type, _ = limiter.check_rate_limit(user_id=user_id_2)
        assert allowed is True

    @pytest.mark.unit
    def test_different_tenants_tracked_separately(self):
        """Should track different tenants separately."""
        limiter = RateLimiter(user_limit_per_minute=10, tenant_limit_per_minute=2)
        tenant_id_1 = "test-tenant-6"
        tenant_id_2 = "test-tenant-7"

        # Tenant 1 reaches limit
        for i in range(2):
            limiter.check_rate_limit(tenant_id=tenant_id_1)
            limiter.record_request(tenant_id=tenant_id_1)

        # Tenant 1 blocked
        allowed, limit_type, _ = limiter.check_rate_limit(tenant_id=tenant_id_1)
        assert allowed is False
        assert limit_type == "tenant"

        # Tenant 2 still allowed
        allowed, limit_type, _ = limiter.check_rate_limit(tenant_id=tenant_id_2)
        assert allowed is True

    @pytest.mark.unit
    def test_no_user_or_tenant_always_allowed(self):
        """Should always allow requests with no user or tenant ID."""
        limiter = RateLimiter(user_limit_per_minute=1, tenant_limit_per_minute=1)

        # Should always be allowed without IDs
        for i in range(10):
            allowed, limit_type, retry_after = limiter.check_rate_limit()
            assert allowed is True
            assert limit_type is None
            assert retry_after is None
