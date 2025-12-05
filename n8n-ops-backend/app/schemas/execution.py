from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class ExecutionBase(BaseModel):
    execution_id: str
    workflow_id: str
    workflow_name: Optional[str] = None
    status: str  # success, error, waiting, running, etc.
    mode: str  # manual, trigger, webhook, etc.
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    execution_time: Optional[float] = None  # Duration in milliseconds
    data: Optional[Dict[str, Any]] = None  # Full execution data from N8N


class ExecutionCreate(ExecutionBase):
    tenant_id: str
    environment_id: str


class ExecutionResponse(ExecutionBase):
    id: str
    tenant_id: str
    environment_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
