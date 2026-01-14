"""Entitlements schemas for plan-based feature access."""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from enum import Enum


class FeatureType(str, Enum):
    FLAG = "flag"
    LIMIT = "limit"


class FeatureStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    HIDDEN = "hidden"


class FeatureResponse(BaseModel):
    """Feature definition response."""
    id: str
    name: str
    display_name: str
    description: Optional[str] = None
    type: FeatureType
    default_value: Dict[str, Any]
    status: FeatureStatus

    class Config:
        from_attributes = True


class PlanResponse(BaseModel):
    """Plan definition response."""
    id: str
    name: str
    display_name: str
    description: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True

    class Config:
        from_attributes = True


class PlanFeatureResponse(BaseModel):
    """Plan-feature mapping response."""
    feature_name: str
    feature_type: FeatureType
    value: Dict[str, Any]


class TenantPlanResponse(BaseModel):
    """Tenant's current plan assignment."""
    plan_id: str
    plan_name: str
    plan_display_name: str
    entitlements_version: int
    effective_from: datetime
    effective_until: Optional[datetime] = None


class EntitlementsResponse(BaseModel):
    """Full entitlements context for a tenant."""
    plan_id: Optional[str] = None
    plan_name: str
    entitlements_version: int
    features: Dict[str, Any]  # {feature_name: resolved_value}


class FeatureCheckResult(BaseModel):
    """Result of checking a specific feature."""
    feature_name: str
    allowed: bool
    value: Optional[Union[bool, int]] = None
    message: Optional[str] = None
    required_plan: Optional[str] = None


class LimitCheckResult(BaseModel):
    """Result of checking a limit feature."""
    feature_name: str
    allowed: bool
    current: int
    limit: int
    message: Optional[str] = None


# =============================================================================
# Phase 3: Tenant Feature Overrides
# =============================================================================

class TenantFeatureOverrideCreate(BaseModel):
    """Create a tenant feature override."""
    feature_key: str = Field(..., description="Feature key to override")
    value: Dict[str, Any] = Field(..., description="Override value: {'enabled': true} or {'value': 500}")
    reason: Optional[str] = Field(None, description="Admin note explaining the override")
    expires_at: Optional[datetime] = Field(None, description="When override expires (null = permanent)")


class TenantFeatureOverrideUpdate(BaseModel):
    """Update a tenant feature override."""
    value: Optional[Dict[str, Any]] = Field(None, description="Override value")
    reason: Optional[str] = Field(None, description="Admin note")
    expires_at: Optional[datetime] = Field(None, description="Expiration time")
    is_active: Optional[bool] = Field(None, description="Whether override is active")


class TenantFeatureOverrideResponse(BaseModel):
    """Tenant feature override response."""
    id: str
    tenant_id: str
    feature_id: str
    feature_key: str
    feature_display_name: str
    value: Dict[str, Any]
    reason: Optional[str] = None
    created_by: Optional[str] = None
    created_by_email: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantFeatureOverrideListResponse(BaseModel):
    """List of tenant feature overrides."""
    overrides: List[TenantFeatureOverrideResponse]
    total: int


# =============================================================================
# Phase 3: Audit Logging
# =============================================================================

class AuditEntityType(str, Enum):
    PLAN_FEATURE = "plan_feature"
    TENANT_PLAN = "tenant_plan"
    TENANT_OVERRIDE = "tenant_override"


class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class FeatureConfigAuditResponse(BaseModel):
    """Feature configuration audit log entry."""
    id: str
    tenant_id: Optional[str] = None
    entity_type: AuditEntityType
    entity_id: str
    feature_key: Optional[str] = None
    action: AuditAction
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    changed_by: Optional[str] = None
    changed_by_email: Optional[str] = None
    changed_at: datetime
    reason: Optional[str] = None

    class Config:
        from_attributes = True


class FeatureConfigAuditListResponse(BaseModel):
    """Paginated list of audit entries."""
    audits: List[FeatureConfigAuditResponse]
    total: int
    page: int
    page_size: int


class AccessResult(str, Enum):
    ALLOWED = "allowed"
    DENIED = "denied"
    LIMIT_EXCEEDED = "limit_exceeded"


class AccessType(str, Enum):
    FLAG_CHECK = "flag_check"
    LIMIT_CHECK = "limit_check"


class FeatureAccessLogResponse(BaseModel):
    """Feature access log entry."""
    id: str
    tenant_id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    feature_key: str
    access_type: AccessType
    result: AccessResult
    current_value: Optional[int] = None
    limit_value: Optional[int] = None
    endpoint: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    accessed_at: datetime

    class Config:
        from_attributes = True


class FeatureAccessLogListResponse(BaseModel):
    """Paginated list of access log entries."""
    logs: List[FeatureAccessLogResponse]
    total: int
    page: int
    page_size: int


class FeatureAccessLogCreate(BaseModel):
    """Create a feature access log entry (internal use)."""
    feature_key: str
    access_type: AccessType
    result: AccessResult
    current_value: Optional[int] = None
    limit_value: Optional[int] = None
    endpoint: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None


# =============================================================================
# Phase 4: Admin Management
# =============================================================================

class FeatureMatrixEntry(BaseModel):
    """A single feature with its values across all plans."""
    feature_id: str
    feature_key: str
    feature_display_name: str
    feature_type: FeatureType
    description: Optional[str] = None
    status: FeatureStatus
    plan_values: Dict[str, Any]  # {plan_name: value}


class FeatureMatrixResponse(BaseModel):
    """Full feature matrix showing all features and their plan values."""
    features: List[FeatureMatrixEntry]
    plans: List[PlanResponse]
    total_features: int


class PlanFeatureUpdate(BaseModel):
    """Update a plan-feature value."""
    value: Dict[str, Any] = Field(..., description="New value: {'enabled': true} or {'value': 500}")
    reason: Optional[str] = Field(None, description="Admin note explaining the change")


class PlanFeatureValueResponse(BaseModel):
    """Response for a plan-feature value update."""
    plan_id: str
    plan_name: str
    feature_id: str
    feature_key: str
    value: Dict[str, Any]
    updated_at: datetime


class AdminFeatureResponse(BaseModel):
    """Full feature details for admin view."""
    id: str
    key: str
    display_name: str
    description: Optional[str] = None
    type: FeatureType
    default_value: Dict[str, Any]
    status: FeatureStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AdminPlanResponse(BaseModel):
    """Full plan details for admin view."""
    id: str
    name: str
    display_name: str
    description: Optional[str] = None
    sort_order: int
    is_active: bool
    tenant_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AdminPlanListResponse(BaseModel):
    """List of plans for admin view."""
    plans: List[AdminPlanResponse]
    total: int


class AdminFeatureListResponse(BaseModel):
    """List of features for admin view."""
    features: List[AdminFeatureResponse]
    total: int
