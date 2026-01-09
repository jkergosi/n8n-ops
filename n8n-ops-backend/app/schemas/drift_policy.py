"""Drift Policy schemas for TTL/SLA and Enterprise governance."""
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class GatedActionType(str, Enum):
    """Types of gated actions that may require approval."""
    acknowledge = "acknowledge"
    extend_ttl = "extend_ttl"
    reconcile = "reconcile"


class ApprovalType(str, Enum):
    """Types of approval actions."""
    acknowledge = "acknowledge"
    extend_ttl = "extend_ttl"
    close = "close"
    reconcile = "reconcile"
    deployment_override = "deployment_override"  # Explicit approval to deploy despite drift


class ApprovalStatus(str, Enum):
    """Status of an approval request."""
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class ApprovalRequirement(str, Enum):
    """Result of approval requirement check."""
    not_required = "not_required"
    required_pending = "required_pending"
    required_approved = "required_approved"
    required_rejected = "required_rejected"
    required_no_request = "required_no_request"


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

    # Gated action approval requirements
    require_approval_for_acknowledge: bool = Field(default=False, description="Whether acknowledging drift requires approval")
    require_approval_for_extend_ttl: bool = Field(default=True, description="Whether extending TTL requires approval")
    require_approval_for_reconcile: bool = Field(default=True, description="Whether reconciling drift requires approval")
    approval_expiry_hours: int = Field(default=72, ge=1, description="Hours before approval request expires")
    auto_approve_config: Dict[str, Any] = Field(default_factory=dict, description="Configuration for auto-approval rules")


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

    # Gated action approval requirements
    require_approval_for_acknowledge: Optional[bool] = None
    require_approval_for_extend_ttl: Optional[bool] = None
    require_approval_for_reconcile: Optional[bool] = None
    approval_expiry_hours: Optional[int] = Field(None, ge=1)
    auto_approve_config: Optional[Dict[str, Any]] = None


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

    # Gated action approval requirements
    require_approval_for_acknowledge: bool
    require_approval_for_extend_ttl: bool
    require_approval_for_reconcile: bool
    approval_expiry_hours: int
    auto_approve_config: Dict[str, Any]

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


class GatedActionDecisionResponse(BaseModel):
    """Response from gated action approval check."""
    allowed: bool
    requirement: ApprovalRequirement
    reason: Optional[str] = None
    approval_id: Optional[str] = None
    approval_details: Optional[Dict[str, Any]] = None
    policy_config: Optional[Dict[str, Any]] = None


class ApprovalAuditEventType(str, Enum):
    """Types of approval audit events."""
    requested = "requested"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"
    executed = "executed"
    execution_failed = "execution_failed"
    auto_approved = "auto_approved"
    expired = "expired"


class ApprovalAuditCreate(BaseModel):
    """Create an approval audit event."""
    approval_id: str
    incident_id: str
    event_type: ApprovalAuditEventType
    actor_id: str
    actor_email: Optional[str] = None
    actor_name: Optional[str] = None
    approval_type: ApprovalType
    previous_status: Optional[ApprovalStatus] = None
    new_status: Optional[ApprovalStatus] = None
    action_metadata: Dict[str, Any] = Field(default_factory=dict)
    execution_result: Optional[Dict[str, Any]] = None
    execution_error: Optional[str] = None
    reason: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class ApprovalAuditResponse(BaseModel):
    """Approval audit event response."""
    id: str
    tenant_id: str
    approval_id: str
    incident_id: str
    event_type: ApprovalAuditEventType
    actor_id: str
    actor_email: Optional[str] = None
    actor_name: Optional[str] = None
    approval_type: ApprovalType
    previous_status: Optional[ApprovalStatus] = None
    new_status: Optional[ApprovalStatus] = None
    action_metadata: Dict[str, Any]
    execution_result: Optional[Dict[str, Any]] = None
    execution_error: Optional[str] = None
    reason: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
