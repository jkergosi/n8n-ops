from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Dict, Any
from app.services.database import db_service
from app.services.auth_service import get_current_user

router = APIRouter()


def get_tenant_id(user_info: dict) -> str:
    tenant = user_info.get("tenant") or {}
    tenant_id = tenant.get("id")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return tenant_id


@router.get("/", response_model=List[Dict[str, Any]])
async def get_tags(environment_id: str = None, user_info: dict = Depends(get_current_user)):
    """Get all tags from the database cache, optionally filtered by environment"""
    try:
        tags = await db_service.get_tags(
            get_tenant_id(user_info),
            environment_id=environment_id
        )

        # Transform snake_case to camelCase for frontend
        transformed_tags = []
        for tag in tags:
            transformed_tags.append({
                "id": tag.get("id"),
                "tagId": tag.get("tag_id"),
                "name": tag.get("name"),
                "tenantId": tag.get("tenant_id"),
                "environmentId": tag.get("environment_id"),
                "createdAt": tag.get("created_at"),
                "updatedAt": tag.get("updated_at"),
                "lastSyncedAt": tag.get("last_synced_at"),
            })

        return transformed_tags

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch tags: {str(e)}"
        )


@router.get("/{tag_id}", response_model=Dict[str, Any])
async def get_tag(tag_id: str, user_info: dict = Depends(get_current_user)):
    """Get a specific tag by ID"""
    try:
        tag = await db_service.get_tag(tag_id, get_tenant_id(user_info))

        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tag not found"
            )

        # Transform snake_case to camelCase for frontend
        return {
            "id": tag.get("id"),
            "tagId": tag.get("tag_id"),
            "name": tag.get("name"),
            "tenantId": tag.get("tenant_id"),
            "environmentId": tag.get("environment_id"),
            "createdAt": tag.get("created_at"),
            "updatedAt": tag.get("updated_at"),
            "lastSyncedAt": tag.get("last_synced_at"),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch tag: {str(e)}"
        )
