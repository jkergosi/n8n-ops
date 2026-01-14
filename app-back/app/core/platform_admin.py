from fastapi import Depends, HTTPException, status

from app.services.auth_service import get_current_user
from app.services.database import db_service


def is_platform_admin(user_id: str) -> bool:
    try:
        resp = (
            db_service.client.table("platform_admins")
            .select("user_id")
            .eq("user_id", user_id)
            .execute()
        )
        return bool(resp.data)
    except Exception:
        return False


def require_platform_admin(allow_when_impersonating: bool = False):
    async def dependency(user_info: dict = Depends(get_current_user)) -> dict:
        user = (user_info or {}).get("user") or {}
        impersonating = bool((user_info or {}).get("impersonating"))

        actor = (user_info or {}).get("actor_user") or {}
        actor_id = actor.get("id") if impersonating else user.get("id")
        if not actor_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        if impersonating and not allow_when_impersonating:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Platform routes are not available during impersonation")

        if not is_platform_admin(actor_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Platform Admin access required")

        # expose computed boolean for downstream use
        return {**user_info, "is_platform_admin": True, "actor_user_id": actor_id}

    return dependency


