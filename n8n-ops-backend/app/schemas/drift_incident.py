from pydantic import BaseModel
from typing import Optional, Any, Dict
from datetime import datetime


class DriftIncidentResponse(BaseModel):
    id: str
    tenant_id: str
    environment_id: str
    status: str = "open"
    title: Optional[str] = None
    summary: Optional[Dict[str, Any]] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


