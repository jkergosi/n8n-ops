from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class SubscriptionPlan(str, Enum):
    free = "free"
    pro = "pro"
    agency = "agency"
    enterprise = "enterprise"


class TenantStatus(str, Enum):
    active = "active"
    trial = "trial"
    suspended = "suspended"
    cancelled = "cancelled"
    archived = "archived"
    pending = "pending"


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    subscription_plan: SubscriptionPlan = SubscriptionPlan.free


class TenantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    subscription_plan: Optional[SubscriptionPlan] = None
    status: Optional[TenantStatus] = None
    primary_contact_name: Optional[str] = None


class TenantResponse(BaseModel):
    id: str
    name: str
    email: str
    subscription_plan: SubscriptionPlan
    status: TenantStatus
    workflow_count: int = 0
    environment_count: int = 0
    user_count: int = 0
    primary_contact_name: Optional[str] = None
    last_active_at: Optional[datetime] = None
    scheduled_deletion_at: Optional[datetime] = None
    stripe_customer_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantListResponse(BaseModel):
    tenants: List[TenantResponse]
    total: int
    page: int
    page_size: int


class TenantStats(BaseModel):
    total: int
    active: int
    suspended: int
    pending: int
    trial: int = 0
    cancelled: int = 0
    by_plan: dict


class TenantNoteCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class TenantNoteResponse(BaseModel):
    id: str
    tenant_id: str
    author_id: Optional[str] = None
    author_email: Optional[str] = None
    author_name: Optional[str] = None
    content: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantNoteListResponse(BaseModel):
    notes: List[TenantNoteResponse]
    total: int


class ScheduleDeletionRequest(BaseModel):
    retention_days: int = Field(30, ge=30, le=90)
