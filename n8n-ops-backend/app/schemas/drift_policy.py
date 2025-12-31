"""Drift Policy schemas for TTL/SLA and Enterprise governance."""
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class ApprovalType(str, Enum):
    """Types of approval actions."""
    acknowledge = "acknowledge"
    extend_ttl = "extend_ttl"
    close = "close"
    reconcile = "reconcile"


class ApprovalStatus(str, Enum):
    """Status of an approval request."""
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class DriftPolicyCreate(BaseModel):
    """Create drift policy for a tenant."""
    default_ttl_hours: int = Field(default=72, ge=1)
    critical_ttl_hours: int = Field(default=24, ge=1)
    high_ttl_hours: int = Field(default=48, ge=1)
    medium_ttl_hours: int = Field(default=72, ge=1)
    low_ttl_hours: int = Field(default=168, ge=1)

    auto_create_incidents: bool = False
    auto_create_for_production_only: bool = True

    block_deployments_on_expired: bool = False
    block_deployments_on_drift: bool = False

    notify_on_detection: bool = True
    notify_on_expiration_warning: bool = True
    expiration_warning_hours: int = Field(default=24, ge=1)

    # Retention settings (in days)
    retention_enabled: bool = Field(default=True)
    retention_days_closed_incidents: int = Field(default=365, ge=0, description="Days to retain closed incidents (0 = never delete)")
    retention_days_reconciliation_artifacts: int = Field(default=180, ge=0, description="Days to retain reconciliation artifacts (0 = never delete)")
    retention_days_approvals: int = Field(default=365, ge=0, description="Days to retain approval records (0 = never delete)")


class DriftPolicyUpdate(BaseModel):
    """Update drift policy."""
    default_ttl_hours: Optional[int] = None
    critical_ttl_hours: Optional[int] = None
    high_ttl_hours: Optional[int] = None
    medium_ttl_hours: Optional[int] = None
    low_ttl_hours: Optional[int] = None

    auto_create_incidents: Optional[bool] = None
    auto_create_for_production_only: Optional[bool] = None

    block_deployments_on_expired: Optional[bool] = None
    block_deployments_on_drift: Optional[bool] = None

    notify_on_detection: Optional[bool] = None
    notify_on_expiration_warning: Optional[bool] = None
    expiration_warning_hours: Optional[int] = None

    # Retention settings
    retention_enabled: Optional[bool] = None
    retention_days_closed_incidents: Optional[int] = Field(None, ge=0)
    retention_days_reconciliation_artifacts: Optional[int] = Field(None, ge=0)
    retention_days_approvals: Optional[int] = Field(None, ge=0)


class DriftPolicyResponse(BaseModel):
    """Drift policy response."""
    id: str
    tenant_id: str

    default_ttl_hours: int
    critical_ttl_hours: int
    high_ttl_hours: int
    medium_ttl_hours: int
    low_ttl_hours: int

    auto_create_incidents: bool
    auto_create_for_production_only: bool

    block_deployments_on_expired: bool
    block_deployments_on_drift: bool

    notify_on_detection: bool
    notify_on_expiration_warning: bool
    expiration_warning_hours: int

    # Retention settings
    retention_enabled: bool
    retention_days_closed_incidents: int
    retention_days_reconciliation_artifacts: int
    retention_days_approvals: int

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DriftApprovalCreate(BaseModel):
    """Request approval for an action."""
    incident_id: str
    approval_type: ApprovalType
    request_reason: Optional[str] = None
    extension_hours: Optional[int] = None  # For extend_ttl type


class DriftApprovalDecision(BaseModel):
    """Decide on an approval request."""
    decision: ApprovalStatus = Field(..., description="Must be 'approved' or 'rejected'")
    decision_notes: Optional[str] = None


class DriftApprovalResponse(BaseModel):
    """Approval request response."""
    id: str
    tenant_id: str
    incident_id: str
    approval_type: ApprovalType
    status: ApprovalStatus

    requested_by: str
    requested_at: datetime
    request_reason: Optional[str] = None

    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None
    decision_notes: Optional[str] = None

    extension_hours: Optional[int] = None

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DriftPolicyTemplateResponse(BaseModel):
    """Policy template response."""
    id: str
    name: str
    description: Optional[str] = None
    policy_config: Dict[str, Any]
    is_system: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
