"""
Unit tests for the auth service.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException

from app.services.auth_service import (
    SupabaseAuthService,
    get_current_user,
    get_current_user_optional,
)


class TestSupabaseAuthService:
    """Tests for SupabaseAuthService class."""

    @pytest.mark.unit
    def test_supabase_auth_service_initialization(self):
        """SupabaseAuthService should initialize with correct settings."""
        service = SupabaseAuthService()
        assert service.algorithms == ["HS256"]
        assert service.jwt_secret is not None


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_credentials_raises_401(self):
        """get_current_user should raise 401 when no credentials provided."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(None)

        assert exc_info.value.status_code == 401


class TestGetCurrentUserOptional:
    """Tests for get_current_user_optional dependency."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_credentials_returns_no_credentials_state(self):
        """get_current_user_optional should return no_credentials=True when no credentials."""
        result = await get_current_user_optional(None)

        assert result["user"] is None
        assert result["tenant"] is None
        assert result.get("no_credentials") is True


class TestSupabaseAuthServiceMethods:
    """Tests for SupabaseAuthService methods."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_or_create_user_existing_by_supabase_id(self):
        """get_or_create_user should find existing user by supabase_auth_id."""
        service = SupabaseAuthService()

        mock_user = {
            "id": "existing-user",
            "email": "existing@example.com",
            "name": "Existing User",
            "role": "admin",
            "tenants": {"id": "tenant-1", "name": "Org"},
        }

        with patch("app.services.auth_service.db_service") as mock_db:
            # First query finds user by supabase_auth_id
            mock_db.client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[mock_user]
            )

            result = await service.get_or_create_user("supabase|existing123", "existing@example.com")

            assert result["user"]["id"] == "existing-user"
            assert result["is_new"] is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_or_create_user_new_user(self):
        """get_or_create_user should return is_new=True for new user."""
        service = SupabaseAuthService()

        with patch("app.services.auth_service.db_service") as mock_db:
            # No user found by supabase_auth_id or email
            mock_db.client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )

            result = await service.get_or_create_user("supabase|newuser123", "new@example.com")

            assert result["user"] is None
            assert result["is_new"] is True
