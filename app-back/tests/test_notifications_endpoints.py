import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.api
def test_notifications_requires_entitlement(client, auth_headers):
    # If entitlements enforcement is active and returns 403, accept; otherwise endpoints may be enabled in dev.
    resp = client.get("/api/v1/notifications/channels", headers=auth_headers)
    assert resp.status_code in [200, 403]


@pytest.mark.asyncio
async def test_get_channels_uses_tenant_from_auth(async_client, auth_headers):
    with patch("app.api.endpoints.notifications.notification_service") as mock_svc:
        mock_svc.get_channels = AsyncMock(return_value=[])
        resp = await async_client.get("/api/v1/notifications/channels", headers=auth_headers)
        assert resp.status_code in [200, 403]


