from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.services.database import db_service
from app.api.endpoints.admin_audit import create_audit_log
from app.core.platform_admin import require_platform_admin, is_platform_admin


router = APIRouter()


class PlatformAdminUser(BaseModel):
    id: str
    email: str
    name: Optional[str] = None


class PlatformAdminRow(BaseModel):
    user: PlatformAdminUser
    granted_at: Optional[datetime] = None
    granted_by: Optional[PlatformAdminUser] = None


class PlatformAdminListResponse(BaseModel):
    admins: List[PlatformAdminRow]
    total: int


class PlatformAdminCreateRequest(BaseModel):
    email: EmailStr


@router.get("/", response_model=PlatformAdminListResponse)
async def list_platform_admins(user_info: dict = Depends(require_platform_admin())):
    try:
        rows_resp = (
            db_service.client.table("platform_admins")
            .select("user_id, granted_by, granted_at")
            .order("granted_at", desc=True)
            .execute()
        )
        rows = rows_resp.data or []

        user_ids = [r.get("user_id") for r in rows if r.get("user_id")]
        granted_by_ids = [r.get("granted_by") for r in rows if r.get("granted_by")]
        all_ids = list({*user_ids, *granted_by_ids})

        users_by_id: Dict[str, Dict[str, Any]] = {}
        if all_ids:
            users_resp = (
                db_service.client.table("users")
                .select("id, email, name")
                .in_("id", all_ids)
                .execute()
            )
            for u in users_resp.data or []:
                users_by_id[u["id"]] = u

        result: List[PlatformAdminRow] = []
        for r in rows:
            uid = r.get("user_id")
            if not uid:
                continue
            u = users_by_id.get(uid) or {"id": uid, "email": "", "name": None}
            gb_id = r.get("granted_by")
            gb = users_by_id.get(gb_id) if gb_id else None
            result.append(
                PlatformAdminRow(
                    user=PlatformAdminUser(id=u["id"], email=u.get("email", ""), name=u.get("name")),
                    granted_at=r.get("granted_at"),
                    granted_by=PlatformAdminUser(id=gb["id"], email=gb.get("email", ""), name=gb.get("name")) if gb else None,
                )
            )

        return PlatformAdminListResponse(admins=result, total=len(result))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to list Platform Admins: {str(e)}")


@router.post("/", response_model=PlatformAdminRow, status_code=status.HTTP_201_CREATED)
async def add_platform_admin(body: PlatformAdminCreateRequest, user_info: dict = Depends(require_platform_admin())):
    actor = (user_info or {}).get("user") or {}
    actor_id = actor.get("id")

    email = body.email.lower().strip()
    try:
        user_resp = (
            db_service.client.table("users")
            .select("id, email, name")
            .eq("email", email)
            .maybe_single()
            .execute()
        )
        target = user_resp.data
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        target_id = target["id"]

        if is_platform_admin(target_id):
            # idempotent
            return PlatformAdminRow(
                user=PlatformAdminUser(id=target["id"], email=target.get("email", ""), name=target.get("name")),
                granted_at=None,
                granted_by=None,
            )

        insert_resp = (
            db_service.client.table("platform_admins")
            .insert({"user_id": target_id, "granted_by": actor_id})
            .execute()
        )
        inserted = (insert_resp.data or [None])[0] or {}

        await create_audit_log(
            action_type="platform_admin.grant",
            action=f"Granted Platform Admin access to {email}",
            actor_id=actor_id,
            actor_email=actor.get("email"),
            actor_name=actor.get("name"),
            resource_type="platform_admin",
            resource_id=target_id,
            resource_name=email,
            new_value={"user_id": target_id, "email": email},
        )

        granted_by_user = PlatformAdminUser(id=actor_id, email=actor.get("email", ""), name=actor.get("name")) if actor_id else None
        return PlatformAdminRow(
            user=PlatformAdminUser(id=target["id"], email=target.get("email", ""), name=target.get("name")),
            granted_at=inserted.get("granted_at"),
            granted_by=granted_by_user,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to add Platform Admin: {str(e)}")


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_platform_admin(user_id: str, user_info: dict = Depends(require_platform_admin())):
    actor = (user_info or {}).get("user") or {}
    actor_id = actor.get("id")

    try:
        # enforce invariants: at least one platform admin must always exist
        count_resp = db_service.client.table("platform_admins").select("user_id", count="exact").execute()
        total = count_resp.count or 0
        if total <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last Platform Admin",
            )

        # ensure target exists
        existing = db_service.client.table("platform_admins").select("user_id").eq("user_id", user_id).execute()
        if not existing.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Platform Admin not found")

        # delete
        db_service.client.table("platform_admins").delete().eq("user_id", user_id).execute()

        await create_audit_log(
            action_type="platform_admin.revoke",
            action=f"Revoked Platform Admin access from user_id={user_id}",
            actor_id=actor_id,
            actor_email=actor.get("email"),
            actor_name=actor.get("name"),
            resource_type="platform_admin",
            resource_id=user_id,
            old_value={"user_id": user_id},
        )

        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to remove Platform Admin: {str(e)}")


