from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional, List, Dict, Any
import json
import logging

from app.services.database import db_service
from app.core.platform_admin import require_platform_admin

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/console/tenants")
async def console_search_tenants(
    name: Optional[str] = Query(None),
    slug: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(25, ge=1, le=100),
    _: dict = Depends(require_platform_admin()),
):
    """Search tenants for support console - uses same view as admin tenants page"""
    try:
        # Use tenant_admin_list view (same as /tenants/ endpoint)
        q = db_service.client.table("tenant_admin_list").select("*")
        if tenant_id:
            q = q.eq("id", tenant_id)
        if name:
            q = q.ilike("name", f"%{name}%")
        if slug:
            q = q.ilike("slug", f"%{slug}%")
        resp = q.order("created_at", desc=True).limit(limit).execute()
        return {"tenants": resp.data or []}
    except Exception as e:
        logger.error(f"Failed to search tenants: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to search tenants: {str(e)}")


@router.get("/console/users")
async def console_search_users(
    email: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(25, ge=1, le=100),
    _: dict = Depends(require_platform_admin()),
):
    try:
        q = db_service.client.table("users").select("id, email, name, role, tenant_id, created_at")
        if user_id:
            q = q.eq("id", user_id)
        if tenant_id:
            q = q.eq("tenant_id", tenant_id)
        if email:
            q = q.ilike("email", f"%{email}%")
        if name:
            q = q.ilike("name", f"%{name}%")

        resp = q.order("created_at", desc=True).limit(limit).execute()
        users = resp.data or []

        tenant_ids = list(set(u.get("tenant_id") for u in users if u.get("tenant_id")))
        tenant_map: Dict[str, Dict[str, Any]] = {}
        if tenant_ids:
            tenants_resp = db_service.client.table("tenants").select("id, name, slug").in_("id", tenant_ids).execute()
            for t in (tenants_resp.data or []):
                tenant_map[t.get("id")] = t

        user_ids = [u.get("id") for u in users if u.get("id")]
        platform_admin_ids = set()
        if user_ids:
            pa_resp = db_service.client.table("platform_admins").select("user_id").in_("user_id", user_ids).execute()
            platform_admin_ids = {row.get("user_id") for row in (pa_resp.data or []) if row.get("user_id")}

        normalized: List[Dict[str, Any]] = []
        for u in users:
            t = tenant_map.get(u.get("tenant_id"), {})
            normalized.append(
                {
                    "id": u.get("id"),
                    "name": u.get("name"),
                    "email": u.get("email"),
                    "role": u.get("role"),
                    "tenant": {"id": t.get("id"), "name": t.get("name"), "slug": t.get("slug")} if t else None,
                    "is_platform_admin": u.get("id") in platform_admin_ids,
                }
            )

        return {"users": normalized}
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        logger.error(f"Error searching users ({error_type}): {error_msg}")
        
        error_lower = error_msg.lower()
        if any([
            "json" in error_lower and ("could not" in error_lower or "cannot" in error_lower or "invalid" in error_lower),
            "html" in error_lower,
            "<!doctype" in error_lower,
            "cloudflare" in error_lower,
            "worker threw exception" in error_lower,
        ]):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Database service returned an invalid response. Please try again or contact support."
            )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to search users: {error_msg}")
