"""
Pydantic schemas for untracked workflow detection and onboarding.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# Untracked Workflow Detection

class UntrackedWorkflowItem(BaseModel):
    """A single untracked workflow from an n8n environment."""
    n8n_workflow_id: str
    name: str
    active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EnvironmentUntrackedWorkflows(BaseModel):
    """Untracked workflows grouped by environment."""
    environment_id: str
    environment_name: str
    environment_class: str
    untracked_workflows: List[UntrackedWorkflowItem]


class UntrackedWorkflowsResponse(BaseModel):
    """Response for GET /api/v1/canonical/untracked"""
    environments: List[EnvironmentUntrackedWorkflows]
    total_untracked: int


# Onboarding

class OnboardWorkflowItem(BaseModel):
    """A single workflow to onboard."""
    environment_id: str
    n8n_workflow_id: str


class OnboardWorkflowsRequest(BaseModel):
    """Request for POST /api/v1/canonical/untracked/onboard"""
    workflows: List[OnboardWorkflowItem]


class OnboardResultItem(BaseModel):
    """Result for a single onboarded workflow."""
    environment_id: str
    n8n_workflow_id: str
    status: str  # 'onboarded', 'skipped', 'failed'
    canonical_workflow_id: Optional[str] = None
    reason: Optional[str] = None


class OnboardWorkflowsResponse(BaseModel):
    """Response for POST /api/v1/canonical/untracked/onboard"""
    results: List[OnboardResultItem]
    total_onboarded: int
    total_skipped: int
    total_failed: int


# Scan

class ScanEnvironmentResult(BaseModel):
    """Result for a single environment scan."""
    environment_id: str
    environment_name: str
    status: str  # 'success', 'failed'
    workflows_found: Optional[int] = None
    error: Optional[str] = None


class ScanEnvironmentsResponse(BaseModel):
    """Response for POST /api/v1/canonical/untracked/scan"""
    environments_scanned: int
    environments_failed: int
    results: List[ScanEnvironmentResult]
