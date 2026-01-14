import pytest
from fastapi import HTTPException

from app.core import feature_gate


@pytest.mark.asyncio
async def test_require_feature_allows_when_enabled(monkeypatch):
    async def fake_can_use_feature(tenant_id: str, feature_name: str):
        return True, ""

    async def fake_get_current_user():
        return {"tenant": {"id": "tenant-1"}, "user": {"id": "user-1"}}

    monkeypatch.setattr(feature_gate.feature_service, "can_use_feature", fake_can_use_feature)
    monkeypatch.setattr(feature_gate, "get_current_user", fake_get_current_user)

    dependency = feature_gate.require_feature("workflow_ci_cd")
    result = await dependency(await fake_get_current_user())

    assert result["tenant"]["id"] == "tenant-1"


@pytest.mark.asyncio
async def test_require_feature_blocks_when_disabled(monkeypatch):
    async def fake_can_use_feature(tenant_id: str, feature_name: str):
        return False, "upgrade required"

    async def fake_get_current_user():
        return {"tenant": {"id": "tenant-1"}, "user": {"id": "user-1"}}

    monkeypatch.setattr(feature_gate.feature_service, "can_use_feature", fake_can_use_feature)
    monkeypatch.setattr(feature_gate, "get_current_user", fake_get_current_user)

    dependency = feature_gate.require_feature("workflow_ci_cd")

    with pytest.raises(HTTPException) as exc:
        await dependency(await fake_get_current_user())

    assert exc.value.status_code == 403
    assert exc.value.detail["error"] == "feature_not_available"
    assert exc.value.detail["required_plan"] == feature_gate.FEATURE_REQUIRED_PLANS.get("workflow_ci_cd", "pro")


@pytest.mark.asyncio
async def test_require_environment_limit_includes_usage(monkeypatch):
    async def fake_can_add_environment(tenant_id: str):
        return True, "", 2, 5

    async def fake_get_current_user():
        return {"tenant": {"id": "tenant-1"}, "user": {"id": "user-1"}}

    monkeypatch.setattr(feature_gate.feature_service, "can_add_environment", fake_can_add_environment)
    monkeypatch.setattr(feature_gate, "get_current_user", fake_get_current_user)

    dependency = feature_gate.require_environment_limit()
    result = await dependency(await fake_get_current_user())

    assert result["environment_limit"]["current"] == 2
    assert result["environment_limit"]["max"] == 5


@pytest.mark.asyncio
async def test_require_environment_limit_blocks_when_at_limit(monkeypatch):
    async def fake_can_add_environment(tenant_id: str):
        return False, "limit reached", 5, 5

    async def fake_get_current_user():
        return {"tenant": {"id": "tenant-1"}, "user": {"id": "user-1"}}

    monkeypatch.setattr(feature_gate.feature_service, "can_add_environment", fake_can_add_environment)
    monkeypatch.setattr(feature_gate, "get_current_user", fake_get_current_user)

    dependency = feature_gate.require_environment_limit()

    with pytest.raises(HTTPException) as exc:
        await dependency(await fake_get_current_user())

    assert exc.value.status_code == 403
    assert exc.value.detail["error"] == "environment_limit_reached"
    assert exc.value.detail["current_count"] == 5
    assert exc.value.detail["max_count"] == 5

