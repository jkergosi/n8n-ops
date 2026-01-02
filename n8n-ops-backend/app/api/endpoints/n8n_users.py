from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from datetime import datetime

from app.services.database import db_service
from app.services.auth_service import get_current_user

router = APIRouter()

def get_tenant_id(user_info: dict) -> str:
    tenant = user_info.get("tenant") or {}
    tenant_id = tenant.get("id")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return tenant_id


@router.get("/")
async def get_n8n_users(environment_type: Optional[str] = None, user_info: dict = Depends(get_current_user)):
    """Get all N8N users, optionally filtered by environment type (dev, staging, production)"""
    try:
        tenant_id = get_tenant_id(user_info)
        # Get all environments first for lookup
        envs_response = db_service.client.table("environments").select(
            "id, n8n_name, n8n_type"
        ).eq("tenant_id", tenant_id).execute()
        env_lookup = {env["id"]: {"id": env["id"], "name": env["n8n_name"], "type": env["n8n_type"]} for env in envs_response.data}

        if environment_type:
            # Resolve environment type to environment ID
            env_config = await db_service.get_environment_by_type(tenant_id, environment_type)
            if not env_config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Environment '{environment_type}' not configured"
                )
            environment_id = env_config.get("id")

            # Get users for specific environment
            response = db_service.client.table("n8n_users").select(
                "*"
            ).eq("tenant_id", tenant_id).eq("environment_id", environment_id).eq("is_deleted", False).order("email").execute()
        else:
            # Get all users across all environments
            response = db_service.client.table("n8n_users").select(
                "*"
            ).eq("tenant_id", tenant_id).eq("is_deleted", False).order("email").execute()

        # Add environment info to each user
        users = []
        for user in response.data:
            user["environment"] = env_lookup.get(user.get("environment_id"))
            users.append(user)

        return users

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch N8N users: {str(e)}"
        )


@router.get("/{user_id}")
async def get_n8n_user(user_id: str, user_info: dict = Depends(get_current_user)):
    """Get a specific N8N user by ID"""
    try:
        tenant_id = get_tenant_id(user_info)
        response = db_service.client.table("n8n_users").select(
            "*"
        ).eq("id", user_id).eq("tenant_id", tenant_id).single().execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="N8N user not found"
            )

        user = response.data
        # Add environment info
        if user.get("environment_id"):
            env_response = db_service.client.table("environments").select(
                "id, n8n_name, n8n_type"
            ).eq("id", user["environment_id"]).single().execute()
            if env_response.data:
                user["environment"] = {
                    "id": env_response.data["id"],
                    "name": env_response.data["n8n_name"],
                    "type": env_response.data["n8n_type"]
                }

        return user

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch N8N user: {str(e)}"
        )
