from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional, List, Dict, Any

from app.services.database import db_service
from app.core.platform_admin import require_platform_admin

router = APIRouter()


@router.get("/console/tenants")
async def console_search_tenants(
    name: Optional[str] = Query(None),
    slug: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(25, ge=1, le=100),
    _: dict = Depends(require_platform_admin()),
):
    try:
        q = db_service.client.table("tenants").select("id, name, slug, subscription_tier, created_at")
        if tenant_id:
            q = q.eq("id", tenant_id)
        if name:
            q = q.ilike("name", f"%{name}%")
        if slug:
            q = q.ilike("slug", f"%{slug}%")
        resp = q.order("created_at", desc=True).limit(limit).execute()
        return {"tenants": resp.data or []}
    except Exception as e:
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
        q = db_service.client.table("users").select("id, email, name, role, tenant_id, tenants(id, name, slug)")
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

        user_ids = [u.get("id") for u in users if u.get("id")]
        platform_admin_ids = set()
        if user_ids:
            pa_resp = db_service.client.table("platform_admins").select("user_id").in_("user_id", user_ids).execute()
            platform_admin_ids = {row.get("user_id") for row in (pa_resp.data or []) if row.get("user_id")}

        normalized: List[Dict[str, Any]] = []
        for u in users:
            t = u.get("tenants") or {}
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to search users: {str(e)}")


