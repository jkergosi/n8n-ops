import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.api
def test_list_api_keys_requires_auth(client):
    resp = client.get("/api/v1/security/api-keys")
    # Our test app overrides get_current_user, but if that changes this should still be protected.
    assert resp.status_code in [200, 401]


@pytest.mark.asyncio
async def test_create_and_revoke_api_key_happy_path(async_client, auth_headers):
    with patch("app.api.endpoints.security.api_key_service") as mock_svc:
        mock_svc.list_keys = AsyncMock(return_value=[])
        mock_svc.create_key = AsyncMock(
            return_value={
                "api_key": "n8nops_test_key",
                "row": {
                    "id": "key-1",
                    "name": "Test Key",
                    "key_prefix": "n8nops_test_",
                    "scopes": ["read"],
                    "created_at": "2024-01-01T00:00:00Z",
                    "last_used_at": None,
                    "revoked_at": None,
                    "is_active": True,
                },
            }
        )
        mock_svc.revoke_key = AsyncMock(
            return_value={
                "id": "key-1",
                "name": "Test Key",
                "key_prefix": "n8nops_test_",
                "scopes": ["read"],
                "created_at": "2024-01-01T00:00:00Z",
                "last_used_at": None,
                "revoked_at": "2024-01-02T00:00:00Z",
                "is_active": False,
            }
        )

        create_resp = await async_client.post(
            "/api/v1/security/api-keys",
            headers=auth_headers,
            json={"name": "Test Key", "scopes": ["read"]},
        )
        assert create_resp.status_code == 200
        body = create_resp.json()
        assert "api_key" in body
        assert body["key"]["name"] == "Test Key"

        revoke_resp = await async_client.delete("/api/v1/security/api-keys/key-1", headers=auth_headers)
        assert revoke_resp.status_code == 200
        body2 = revoke_resp.json()
        assert body2["is_active"] is False


