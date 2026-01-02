from fastapi import APIRouter, HTTPException, status, Depends
from typing import List

from app.schemas.security import TenantApiKeyResponse, TenantApiKeyCreate, TenantApiKeyCreateResponse
from app.services.auth_service import get_current_user
from app.services import api_key_service


router = APIRouter()


@router.get("/api-keys", response_model=List[TenantApiKeyResponse])
async def list_tenant_api_keys(user_info: dict = Depends(get_current_user)):
    tenant = user_info.get("tenant")
    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    tenant_id = tenant["id"]
    return await api_key_service.list_keys(tenant_id)


@router.post("/api-keys", response_model=TenantApiKeyCreateResponse)
async def create_tenant_api_key(payload: TenantApiKeyCreate, user_info: dict = Depends(get_current_user)):
    tenant = user_info.get("tenant")
    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    tenant_id = tenant["id"]

    result = await api_key_service.create_key(tenant_id, payload.name, payload.scopes)
    row = result["row"]
    if not row:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create API key")

    key = TenantApiKeyResponse(**row)
    return TenantApiKeyCreateResponse(api_key=result["api_key"], key=key)


@router.delete("/api-keys/{key_id}", response_model=TenantApiKeyResponse)
async def revoke_tenant_api_key(key_id: str, user_info: dict = Depends(get_current_user)):
    tenant = user_info.get("tenant")
    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    tenant_id = tenant["id"]

    updated = await api_key_service.revoke_key(tenant_id, key_id)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    return TenantApiKeyResponse(**updated)


