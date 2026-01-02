from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any

from app.schemas.support import (
    SupportConfigResponse,
    SupportConfigUpdate,
)
from app.services.support_service import support_service
from app.services.support_attachments_service import create_signed_download_url
from app.core.entitlements_gate import require_entitlement
from app.services.auth_service import get_current_user
from app.services.database import db_service

router = APIRouter()

def get_tenant_id(user_info: dict) -> str:
    tenant = user_info.get("tenant") or {}
    tid = tenant.get("id")
    if not tid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return tid


@router.get("/config", response_model=SupportConfigResponse)
async def get_support_config(
    user_info: dict = Depends(get_current_user),
    # _: dict = Depends(require_entitlement("admin_settings"))
) -> SupportConfigResponse:
    """
    Get support configuration for the tenant.

    Returns n8n webhook URL, JSM portal settings, and request type IDs.
    """
    try:
        tenant_id = get_tenant_id(user_info)
        config = await support_service.get_config(tenant_id)

        if not config:
            # Return empty config if none exists
            return SupportConfigResponse(tenant_id=tenant_id)

        return config

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get support config: {str(e)}"
        )


@router.put("/config", response_model=SupportConfigResponse)
async def update_support_config(
    data: SupportConfigUpdate,
    user_info: dict = Depends(get_current_user),
    # _: dict = Depends(require_entitlement("admin_settings"))
) -> SupportConfigResponse:
    """
    Update support configuration for the tenant.

    Configures n8n webhook URL, JSM portal settings, and request type IDs.
    """
    try:
        config = await support_service.update_config(get_tenant_id(user_info), data)
        return config

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update support config: {str(e)}"
        )


@router.post("/test-n8n", response_model=Dict[str, Any])
async def test_n8n_connection(
    user_info: dict = Depends(get_current_user),
    # _: dict = Depends(require_entitlement("admin_settings"))
) -> Dict[str, Any]:
    """
    Test the n8n webhook connection.

    Sends a test payload to verify connectivity.
    """
    try:
        result = await support_service.test_n8n_connection(get_tenant_id(user_info))
        return result

    except Exception as e:
        return {
            "success": False,
            "message": f"Connection test failed: {str(e)}"
        }


@router.get("/requests")
async def list_support_requests(
    limit: int = 50,
    user_info: dict = Depends(get_current_user),
):
    tenant_id = get_tenant_id(user_info)
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="limit must be between 1 and 200")

    reqs_resp = (
        db_service.client.table("support_requests")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    requests = reqs_resp.data or []
    request_ids = [r["id"] for r in requests]
    attachments_by_request: Dict[str, list] = {}
    if request_ids:
        atts_resp = (
            db_service.client.table("support_attachments")
            .select("id, support_request_id, filename, content_type, size_bytes, created_at")
            .eq("tenant_id", tenant_id)
            .in_("support_request_id", request_ids)
            .execute()
        )
        for a in (atts_resp.data or []):
            rid = a.get("support_request_id")
            if rid:
                attachments_by_request.setdefault(rid, []).append(a)

    for r in requests:
        r["attachments"] = attachments_by_request.get(r["id"], [])
    return {"data": requests}


@router.get("/attachments/{attachment_id}/download-url")
async def get_support_attachment_download_url(
    attachment_id: str,
    expires_seconds: int = 3600,
    user_info: dict = Depends(get_current_user),
):
    tenant_id = get_tenant_id(user_info)
    if expires_seconds < 60 or expires_seconds > 86400:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expires_seconds must be between 60 and 86400")
    url = await create_signed_download_url(tenant_id, attachment_id, expires_seconds=expires_seconds)
    return {"url": url}
