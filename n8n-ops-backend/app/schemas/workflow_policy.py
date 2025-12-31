"""
Canonical WorkflowActionPolicy schema - used by both frontend and backend.
Field names must match TypeScript interface in types/index.ts

This is the single source of truth for workflow action policies.
"""
from pydantic import BaseModel
from enum import Enum
from typing import Optional


class EnvironmentClass(str, Enum):
    """Deterministic environment class for policy enforcement"""
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"


class WorkflowActionPolicy(BaseModel):
    """
    Canonical policy schema - matches frontend exactly.

    Field naming: Use snake_case for backend, frontend converts to camelCase as needed.
    """
    can_view_details: bool = True
    can_open_in_n8n: bool = True
    can_create_deployment: bool = True
    can_edit_directly: bool = False
    can_soft_delete: bool = False       # Archive workflow
    can_hard_delete: bool = False       # Permanently remove (admin-only)
    can_create_drift_incident: bool = False
    drift_incident_required: bool = False
    edit_requires_confirmation: bool = True
    edit_requires_admin: bool = False


class WorkflowPolicyResponse(BaseModel):
    """Response model for workflow policy endpoint"""
    environment_id: str
    environment_class: EnvironmentClass
    plan: str
    role: str
    policy: WorkflowActionPolicy


# Default policy matrix by environment class
DEFAULT_POLICY_MATRIX = {
    EnvironmentClass.DEV: WorkflowActionPolicy(
        can_view_details=True,
        can_open_in_n8n=True,
        can_create_deployment=True,
        can_edit_directly=True,
        can_soft_delete=True,          # Default delete = soft (archive)
        can_hard_delete=False,         # Hard delete requires explicit admin action
        can_create_drift_incident=True,  # Plan-gated below
        drift_incident_required=False,   # Plan-gated below
        edit_requires_confirmation=True,  # Warn about drift
        edit_requires_admin=False,
    ),
    EnvironmentClass.STAGING: WorkflowActionPolicy(
        can_view_details=True,
        can_open_in_n8n=True,
        can_create_deployment=True,
        can_edit_directly=True,        # Admin-gated below
        can_soft_delete=False,         # Route to deployment
        can_hard_delete=False,         # Never in staging
        can_create_drift_incident=True,
        drift_incident_required=False,   # Plan-gated below
        edit_requires_confirmation=True,
        edit_requires_admin=True,      # Admin only
    ),
    EnvironmentClass.PRODUCTION: WorkflowActionPolicy(
        can_view_details=True,
        can_open_in_n8n=True,
        can_create_deployment=True,
        can_edit_directly=False,       # Never in production
        can_soft_delete=False,         # Never in production
        can_hard_delete=False,         # Never in production
        can_create_drift_incident=True,
        drift_incident_required=True,  # Always required in production
        edit_requires_confirmation=False,  # N/A
        edit_requires_admin=False,     # N/A
    ),
}


def build_policy(
    env_class: EnvironmentClass,
    plan: str,
    role: str,
    has_drift: bool = False
) -> WorkflowActionPolicy:
    """
    Build policy based on environment class, plan, and role.

    Args:
        env_class: The environment classification (dev/staging/production)
        plan: The tenant's subscription plan (free/pro/agency/enterprise)
        role: The user's role (user/admin/superuser)
        has_drift: Whether the workflow has drift

    Returns:
        WorkflowActionPolicy with all permissions computed
    """
    # Get base policy from matrix
    base = DEFAULT_POLICY_MATRIX.get(env_class, DEFAULT_POLICY_MATRIX[EnvironmentClass.DEV])

    # Create a mutable copy
    policy = WorkflowActionPolicy(
        can_view_details=base.can_view_details,
        can_open_in_n8n=base.can_open_in_n8n,
        can_create_deployment=base.can_create_deployment,
        can_edit_directly=base.can_edit_directly,
        can_soft_delete=base.can_soft_delete,
        can_hard_delete=base.can_hard_delete,
        can_create_drift_incident=base.can_create_drift_incident,
        drift_incident_required=base.drift_incident_required,
        edit_requires_confirmation=base.edit_requires_confirmation,
        edit_requires_admin=base.edit_requires_admin,
    )

    plan_lower = plan.lower()
    is_agency_plus = plan_lower in ['agency', 'enterprise']
    is_admin = role in ['admin', 'superuser']

    # =============================================
    # PLAN-BASED RESTRICTIONS
    # =============================================

    # Free tier: No drift incident workflow at all
    if plan_lower == 'free':
        policy.can_create_drift_incident = False
        policy.drift_incident_required = False

    # Pro tier: Drift incidents optional (not required)
    if plan_lower == 'pro':
        policy.drift_incident_required = False

    # Agency+: Drift incidents required by default in staging/production
    if is_agency_plus:
        if env_class == EnvironmentClass.STAGING:
            policy.can_edit_directly = False  # Even stricter for agency+
            policy.drift_incident_required = True
        # Production already has drift_incident_required = True

    # =============================================
    # ROLE-BASED RESTRICTIONS
    # =============================================

    # Admin-gated actions
    if policy.edit_requires_admin and not is_admin:
        policy.can_edit_directly = False

    # Hard delete: Admin-only in dev, never elsewhere
    if env_class == EnvironmentClass.DEV and is_admin:
        policy.can_hard_delete = True  # Unlocks "Permanently delete" option

    # =============================================
    # DRIFT STATE RESTRICTIONS
    # =============================================

    # Drift incident only if drift exists
    if not has_drift:
        policy.can_create_drift_incident = False
        policy.drift_incident_required = False

    return policy
