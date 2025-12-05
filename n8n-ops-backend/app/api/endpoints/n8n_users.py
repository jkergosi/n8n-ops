from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from datetime import datetime

from app.services.database import db_service

router = APIRouter()

# TODO: Replace with actual tenant ID from authenticated user
MOCK_TENANT_ID = "00000000-0000-0000-0000-000000000000"


@router.get("/")
async def get_n8n_users(environment_id: Optional[str] = None):
    """Get all N8N users, optionally filtered by environment"""
    try:
        if environment_id:
            # Get users for specific environment
            users = await db_service.get_n8n_users(MOCK_TENANT_ID, environment_id)
        else:
            # Get all users across all environments
            response = db_service.client.table("n8n_users").select(
                "*, environment:environments(id, name, type)"
            ).eq("tenant_id", MOCK_TENANT_ID).eq("is_deleted", False).order("email").execute()
            users = response.data

        return users

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch N8N users: {str(e)}"
        )


@router.get("/{user_id}")
async def get_n8n_user(user_id: str):
    """Get a specific N8N user by ID"""
    try:
        response = db_service.client.table("n8n_users").select(
            "*, environment:environments(id, name, type)"
        ).eq("id", user_id).eq("tenant_id", MOCK_TENANT_ID).single().execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="N8N user not found"
            )

        return response.data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch N8N user: {str(e)}"
        )
