from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class TenantApiKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    scopes: List[str] = Field(default_factory=list)
    created_at: datetime
    last_used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    is_active: bool


class TenantApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    scopes: List[str] = Field(default_factory=list)


class TenantApiKeyCreateResponse(BaseModel):
    api_key: str
    key: TenantApiKeyResponse


