from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    admin = "admin"
    developer = "developer"
    viewer = "viewer"


class UserStatus(str, Enum):
    active = "active"
    pending = "pending"
    inactive = "inactive"


class TeamMemberCreate(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    role: UserRole = UserRole.viewer


class TeamMemberUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None


class TeamMemberResponse(BaseModel):
    id: str
    tenant_id: str
    email: str
    name: str
    role: UserRole
    status: UserStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TeamMemberInvite(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.viewer
    message: Optional[str] = None


class TeamLimitsResponse(BaseModel):
    current_members: int
    max_members: Optional[int] = None  # None means unlimited
    can_add_more: bool
