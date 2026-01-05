"""
Unit tests for plan_resolver module.

Tests the single source of truth for tenant plan resolution
from tenant_provider_subscriptions table.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.plan_resolver import (
    resolve_effective_plan,
    get_effective_plan_name,
    _normalize_plan_name,
    _get_plan_rank,
    _is_subscription_active,
    PLAN_PRECEDENCE,
)


class TestNormalizePlanName:
    """Test plan name normalization."""

    def test_lowercase_conversion(self):
        assert _normalize_plan_name("PRO") == "pro"
        assert _normalize_plan_name("Enterprise") == "enterprise"
        assert _normalize_plan_name("AGENCY") == "agency"

    def test_whitespace_stripping(self):
        assert _normalize_plan_name("  pro  ") == "pro"
        assert _normalize_plan_name("\tenterprise\n") == "enterprise"

    def test_none_returns_free(self):
        assert _normalize_plan_name(None) == "free"

    def test_empty_string_returns_free(self):
        assert _normalize_plan_name("") == "free"


class TestGetPlanRank:
    """Test plan precedence ranking."""

    def test_known_plans(self):
        assert _get_plan_rank("free") == 0
        assert _get_plan_rank("pro") == 10
        assert _get_plan_rank("agency") == 20
        assert _get_plan_rank("enterprise") == 30

    def test_unknown_plan_returns_zero(self):
        assert _get_plan_rank("unknown") == 0
        assert _get_plan_rank("platinum") == 0

    def test_case_insensitive(self):
        assert _get_plan_rank("PRO") == 10
        assert _get_plan_rank("Enterprise") == 30


class TestIsSubscriptionActive:
    """Test subscription active status checking."""

    def setup_method(self):
        self.now = datetime.now(timezone.utc)

    def test_active_status_is_active(self):
        sub = {"status": "active"}
        assert _is_subscription_active(sub, self.now) is True

    def test_trialing_status_is_active(self):
        sub = {"status": "trialing"}
        assert _is_subscription_active(sub, self.now) is True

    def test_cancelled_status_is_not_active(self):
        sub = {"status": "cancelled"}
        assert _is_subscription_active(sub, self.now) is False

    def test_expired_status_is_not_active(self):
        sub = {"status": "expired"}
        assert _is_subscription_active(sub, self.now) is False

    def test_starts_in_future_is_not_active(self):
        future = (self.now + timedelta(days=1)).isoformat()
        sub = {"status": "active", "starts_at": future}
        assert _is_subscription_active(sub, self.now) is False

    def test_starts_in_past_is_active(self):
        past = (self.now - timedelta(days=1)).isoformat()
        sub = {"status": "active", "starts_at": past}
        assert _is_subscription_active(sub, self.now) is True

    def test_ends_in_past_is_not_active(self):
        past = (self.now - timedelta(days=1)).isoformat()
        sub = {"status": "active", "current_period_end": past}
        assert _is_subscription_active(sub, self.now) is False

    def test_ends_in_future_is_active(self):
        future = (self.now + timedelta(days=30)).isoformat()
        sub = {"status": "active", "current_period_end": future}
        assert _is_subscription_active(sub, self.now) is True

    def test_no_dates_is_active(self):
        sub = {"status": "active"}
        assert _is_subscription_active(sub, self.now) is True


class TestResolveEffectivePlan:
    """Test the main resolve_effective_plan function."""

    def setup_method(self):
        self.tenant_id = uuid4()
        self.now = datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_no_subscriptions_returns_free(self):
        """Unit test: no active subs => free"""
        mock_db = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_db.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        result = await resolve_effective_plan(self.tenant_id, db=mock_db)

        assert result["plan_name"] == "free"
        assert result["source"] == "provider_subscriptions"
        assert result["contributing_subscriptions"] == []
        assert result["highest_subscription_id"] is None
        assert result["plan_rank"] == 0

    @pytest.mark.asyncio
    async def test_single_active_pro_returns_pro(self):
        """Unit test: active pro => pro"""
        sub_id = str(uuid4())
        mock_db = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{
            "id": sub_id,
            "tenant_id": str(self.tenant_id),
            "provider_id": "provider-1",
            "plan_id": "plan-1",
            "status": "active",
            "current_period_start": (self.now - timedelta(days=1)).isoformat(),
            "current_period_end": (self.now + timedelta(days=30)).isoformat(),
            "plan": {"id": "plan-1", "name": "pro", "display_name": "Pro"}
        }]
        mock_db.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        result = await resolve_effective_plan(self.tenant_id, db=mock_db)

        assert result["plan_name"] == "pro"
        assert result["source"] == "provider_subscriptions"
        assert sub_id in result["contributing_subscriptions"]
        assert result["highest_subscription_id"] == sub_id
        assert result["plan_rank"] == 10

    @pytest.mark.asyncio
    async def test_multiple_subs_highest_tier_wins(self):
        """Unit test: active pro + active agency => agency"""
        pro_sub_id = str(uuid4())
        agency_sub_id = str(uuid4())
        mock_db = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": pro_sub_id,
                "tenant_id": str(self.tenant_id),
                "provider_id": "provider-1",
                "plan_id": "plan-pro",
                "status": "active",
                "current_period_end": (self.now + timedelta(days=30)).isoformat(),
                "plan": {"id": "plan-pro", "name": "pro", "display_name": "Pro"}
            },
            {
                "id": agency_sub_id,
                "tenant_id": str(self.tenant_id),
                "provider_id": "provider-2",
                "plan_id": "plan-agency",
                "status": "active",
                "current_period_end": (self.now + timedelta(days=30)).isoformat(),
                "plan": {"id": "plan-agency", "name": "agency", "display_name": "Agency"}
            }
        ]
        mock_db.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        result = await resolve_effective_plan(self.tenant_id, db=mock_db)

        assert result["plan_name"] == "agency"
        assert result["plan_rank"] == 20
        assert result["highest_subscription_id"] == agency_sub_id
        assert len(result["contributing_subscriptions"]) == 2
        assert pro_sub_id in result["contributing_subscriptions"]
        assert agency_sub_id in result["contributing_subscriptions"]

    @pytest.mark.asyncio
    async def test_expired_pro_no_active_returns_free(self):
        """Unit test: expired pro + no active => free"""
        sub_id = str(uuid4())
        mock_db = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{
            "id": sub_id,
            "tenant_id": str(self.tenant_id),
            "provider_id": "provider-1",
            "plan_id": "plan-1",
            "status": "active",
            "current_period_start": (self.now - timedelta(days=60)).isoformat(),
            "current_period_end": (self.now - timedelta(days=30)).isoformat(),  # Expired
            "plan": {"id": "plan-1", "name": "pro", "display_name": "Pro"}
        }]
        mock_db.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        result = await resolve_effective_plan(self.tenant_id, db=mock_db)

        assert result["plan_name"] == "free"
        assert result["contributing_subscriptions"] == []
        assert result["highest_subscription_id"] is None

    @pytest.mark.asyncio
    async def test_cancelled_subscription_not_counted(self):
        """Cancelled subscriptions should not be counted as active."""
        sub_id = str(uuid4())
        mock_db = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{
            "id": sub_id,
            "tenant_id": str(self.tenant_id),
            "provider_id": "provider-1",
            "plan_id": "plan-1",
            "status": "cancelled",
            "current_period_end": (self.now + timedelta(days=30)).isoformat(),
            "plan": {"id": "plan-1", "name": "enterprise", "display_name": "Enterprise"}
        }]
        mock_db.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        result = await resolve_effective_plan(self.tenant_id, db=mock_db)

        assert result["plan_name"] == "free"
        assert result["contributing_subscriptions"] == []

    @pytest.mark.asyncio
    async def test_trialing_subscription_is_active(self):
        """Trialing subscriptions should count as active."""
        sub_id = str(uuid4())
        mock_db = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{
            "id": sub_id,
            "tenant_id": str(self.tenant_id),
            "provider_id": "provider-1",
            "plan_id": "plan-1",
            "status": "trialing",
            "current_period_end": (self.now + timedelta(days=14)).isoformat(),
            "plan": {"id": "plan-1", "name": "pro", "display_name": "Pro"}
        }]
        mock_db.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        result = await resolve_effective_plan(self.tenant_id, db=mock_db)

        assert result["plan_name"] == "pro"
        assert sub_id in result["contributing_subscriptions"]


class TestGetEffectivePlanName:
    """Test the convenience function."""

    @pytest.mark.asyncio
    async def test_returns_just_plan_name(self):
        """get_effective_plan_name should return just the plan string."""
        tenant_id = uuid4()
        mock_db = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{
            "id": str(uuid4()),
            "tenant_id": str(tenant_id),
            "status": "active",
            "current_period_end": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "plan": {"id": "plan-1", "name": "enterprise", "display_name": "Enterprise"}
        }]
        mock_db.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        with patch("app.services.plan_resolver.db_service", mock_db):
            result = await get_effective_plan_name(tenant_id)

        assert result == "enterprise"
        assert isinstance(result, str)
