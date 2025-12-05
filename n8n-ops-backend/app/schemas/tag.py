from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TagBase(BaseModel):
    tag_id: str  # ID from N8N API
    name: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TagCreate(TagBase):
    tenant_id: str
    environment_id: str


class TagResponse(TagBase):
    id: str
    tenant_id: str
    environment_id: str
    last_synced_at: datetime

    class Config:
        from_attributes = True
