"""
Unit tests for the auth service.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException

from app.services.auth_service import (
    Auth0Service,
    get_current_user,
    get_current_user_optional,
)


class TestAuth0Service:
    """Tests for Auth0Service class."""

    @pytest.mark.unit
    def test_auth0_service_initialization(self):
        """Auth0Service should initialize with correct settings."""
        service = Auth0Service()
        assert service.algorithms == ["RS256"]
        assert service._jwks is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_jwks_caches_result(self):
        """get_jwks should cache the JWKS after first fetch."""
        service = Auth0Service()

        mock_jwks = {"keys": [{"kid": "test-kid", "kty": "RSA"}]}

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_jwks

            mock_client_instance = MagicMock()
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_client_instance

            # First call should fetch
            result1 = await service.get_jwks()
            assert result1 == mock_jwks

            # Second call should use cache
            result2 = await service.get_jwks()
            assert result2 == mock_jwks

            # HTTP client should only be called once
            assert mock_client_instance.get.call_count == 1


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dev_token_valid_user(self):
        """Dev token should return user when user exists."""
        mock_credentials = MagicMock()
        mock_credentials.credentials = "dev-token-user-123"

        mock_user = {
            "id": "user-123",
            "email": "test@example.com",
            "name": "Test User",
            "role": "admin",
            "tenants": {
                "id": "tenant-1",
                "name": "Test Org",
                "subscription_tier": "pro",
            }
        }

        with patch("app.services.auth_service.db_service") as mock_db:
            mock_db.client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[mock_user]
            )

            result = await get_current_user(mock_credentials)

            assert result["user"]["id"] == "user-123"
            assert result["user"]["email"] == "test@example.com"
            assert result["tenant"]["id"] == "tenant-1"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dev_token_user_not_found(self):
        """Dev token should raise 401 when user doesn't exist."""
        mock_credentials = MagicMock()
        mock_credentials.credentials = "dev-token-invalid-user"

        with patch("app.services.auth_service.db_service") as mock_db:
            mock_db.client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials)

            assert exc_info.value.status_code == 401

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_token_uses_first_user(self):
        """Without token, should use first user from database."""
        mock_user = {
            "id": "first-user",
            "email": "first@example.com",
            "name": "First User",
            "role": "admin",
            "tenants": {
                "id": "tenant-1",
                "name": "Test Org",
                "subscription_tier": "free",
            }
        }

        with patch("app.services.auth_service.db_service") as mock_db:
            mock_db.client.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[mock_user]
            )

            result = await get_current_user(None)

            assert result["user"]["id"] == "first-user"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_users_in_database(self):
        """Should raise 401 when no users exist."""
        with patch("app.services.auth_service.db_service") as mock_db:
            mock_db.client.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[]
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(None)

            assert exc_info.value.status_code == 401


class TestGetCurrentUserOptional:
    """Tests for get_current_user_optional dependency."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dev_token_returns_user(self):
        """Dev token should return user when valid."""
        mock_credentials = MagicMock()
        mock_credentials.credentials = "dev-token-user-456"

        mock_user = {
            "id": "user-456",
            "email": "optional@example.com",
            "name": "Optional User",
            "role": "developer",
            "tenants": {
                "id": "tenant-2",
                "name": "Optional Org",
                "subscription_tier": "pro",
            }
        }

        with patch("app.services.auth_service.db_service") as mock_db:
            mock_db.client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[mock_user]
            )

            result = await get_current_user_optional(mock_credentials)

            assert result["user"]["id"] == "user-456"
            assert result["is_new"] is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_token_returns_first_user(self):
        """Without token, should return first user."""
        mock_user = {
            "id": "first-user",
            "email": "first@example.com",
            "name": "First User",
            "role": "admin",
            "tenants": {
                "id": "tenant-1",
                "name": "Test Org",
                "subscription_tier": "free",
            }
        }

        with patch("app.services.auth_service.db_service") as mock_db:
            mock_db.client.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[mock_user]
            )

            result = await get_current_user_optional(None)

            assert result["user"]["id"] == "first-user"
            assert result["is_new"] is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_users_returns_new_user_state(self):
        """Should return is_new=True when no users exist."""
        with patch("app.services.auth_service.db_service") as mock_db:
            mock_db.client.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[]
            )
            mock_db.client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )

            result = await get_current_user_optional(None)

            assert result["user"] is None
            assert result["tenant"] is None
            assert result["is_new"] is True


class TestAuth0ServiceMethods:
    """Tests for Auth0Service additional methods."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_or_create_user_existing_by_auth0_id(self):
        """get_or_create_user should find existing user by auth0_id."""
        service = Auth0Service()

        mock_user = {
            "id": "existing-user",
            "email": "existing@example.com",
            "name": "Existing User",
            "role": "admin",
            "tenants": {"id": "tenant-1", "name": "Org"},
        }

        auth0_payload = {
            "sub": "auth0|existing123",
            "email": "existing@example.com",
            "name": "Existing User",
        }

        with patch("app.services.auth_service.db_service") as mock_db:
            # First query finds user by auth0_id
            mock_db.client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[mock_user]
            )

            result = await service.get_or_create_user(auth0_payload)

            assert result["user"]["id"] == "existing-user"
            assert result["is_new"] is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_or_create_user_missing_email(self):
        """get_or_create_user should raise error when email is missing."""
        service = Auth0Service()

        auth0_payload = {
            "sub": "auth0|user123",
            # No email claim
        }

        with patch("app.services.auth_service.db_service"):
            with pytest.raises(HTTPException) as exc_info:
                await service.get_or_create_user(auth0_payload)

            assert exc_info.value.status_code == 400

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_or_create_user_new_user(self):
        """get_or_create_user should return is_new=True for new user."""
        service = Auth0Service()

        auth0_payload = {
            "sub": "auth0|newuser123",
            "email": "new@example.com",
            "name": "New User",
        }

        with patch("app.services.auth_service.db_service") as mock_db:
            # No user found by auth0_id or email
            mock_db.client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )

            result = await service.get_or_create_user(auth0_payload)

            assert result["user"] is None
            assert result["is_new"] is True
            assert result["auth0_id"] == "auth0|newuser123"
            assert result["email"] == "new@example.com"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_user_and_tenant_success(self):
        """create_user_and_tenant should create both tenant and user."""
        service = Auth0Service()

        mock_tenant = {"id": "new-tenant", "name": "New Org", "subscription_tier": "free"}
        mock_user = {
            "id": "new-user",
            "tenant_id": "new-tenant",
            "email": "new@example.com",
            "name": "New User",
            "role": "admin",
        }

        with patch("app.services.auth_service.db_service") as mock_db:
            # Mock tenant creation
            mock_db.client.table.return_value.insert.return_value.execute.side_effect = [
                MagicMock(data=[mock_tenant]),  # Tenant insert
                MagicMock(data=[mock_user]),    # User insert
            ]

            result = await service.create_user_and_tenant(
                auth0_id="auth0|new123",
                email="new@example.com",
                name="New User",
                organization_name="New Org"
            )

            assert result["tenant"]["id"] == "new-tenant"
            assert result["user"]["id"] == "new-user"
            assert result["is_new"] is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_user_and_tenant_tenant_failure(self):
        """create_user_and_tenant should raise error if tenant creation fails."""
        service = Auth0Service()

        with patch("app.services.auth_service.db_service") as mock_db:
            # Tenant creation fails
            mock_db.client.table.return_value.insert.return_value.execute.return_value = MagicMock(
                data=[]
            )

            with pytest.raises(HTTPException) as exc_info:
                await service.create_user_and_tenant(
                    auth0_id="auth0|fail123",
                    email="fail@example.com",
                    name="Fail User"
                )

            assert exc_info.value.status_code == 500


class TestTokenValidation:
    """Tests for token validation logic."""

    @pytest.mark.unit
    def test_dev_token_format(self):
        """Dev token should follow format dev-token-{user_id}."""
        token = "dev-token-user-123"
        assert token.startswith("dev-token-")
        user_id = token.replace("dev-token-", "")
        assert user_id == "user-123"

    @pytest.mark.unit
    def test_dev_token_extraction(self):
        """User ID should be correctly extracted from dev token."""
        test_cases = [
            ("dev-token-abc123", "abc123"),
            ("dev-token-00000000-0000-0000-0000-000000000001", "00000000-0000-0000-0000-000000000001"),
            ("dev-token-simple", "simple"),
        ]

        for token, expected_id in test_cases:
            extracted = token.replace("dev-token-", "")
            assert extracted == expected_id
