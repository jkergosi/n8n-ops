from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class WorkflowReference(BaseModel):
    """Reference to a workflow that uses this credential"""
    id: str
    name: str
    n8n_workflow_id: Optional[str] = None


class CredentialBase(BaseModel):
    """Base credential model with common fields"""
    name: str = Field(..., description="Credential name")
    type: str = Field(..., description="Credential type (e.g., 'slackApi', 'githubApi')")


class CredentialCreate(CredentialBase):
    """Schema for creating a new credential"""
    data: Dict[str, Any] = Field(..., description="The credential data/secrets (encrypted by N8N)")
    environment_id: str = Field(..., description="Environment to create the credential in")


class CredentialUpdate(BaseModel):
    """Schema for updating an existing credential"""
    name: Optional[str] = Field(None, description="New credential name")
    data: Optional[Dict[str, Any]] = Field(None, description="New credential data/secrets")


class CredentialResponse(CredentialBase):
    """Response model for a credential (metadata only, no secrets)"""
    id: str
    n8n_credential_id: Optional[str] = None
    tenant_id: Optional[str] = None
    environment_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    used_by_workflows: List[WorkflowReference] = []
    environment: Optional[Dict[str, Any]] = None  # Environment info for display

    class Config:
        from_attributes = True


class CredentialTypeField(BaseModel):
    """Schema field for a credential type"""
    displayName: str
    name: str
    type: str
    default: Optional[Any] = None
    required: Optional[bool] = False
    description: Optional[str] = None
    options: Optional[List[Dict[str, Any]]] = None


class CredentialTypeSchema(BaseModel):
    """Schema for a credential type (used for building forms)"""
    name: str
    displayName: str
    properties: List[CredentialTypeField] = []
    documentationUrl: Optional[str] = None


class CredentialSyncResult(BaseModel):
    """Result of syncing credentials from N8N"""
    success: bool
    synced: int
    errors: List[str] = []
    message: str


# Logical credentials and mappings (provider-aware)

class LogicalCredentialBase(BaseModel):
    name: str
    description: Optional[str] = None
    required_type: Optional[str] = None


class LogicalCredentialCreate(LogicalCredentialBase):
    tenant_id: str


class LogicalCredentialResponse(LogicalCredentialBase):
    id: str
    tenant_id: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CredentialMappingBase(BaseModel):
    logical_credential_id: str
    environment_id: str
    provider: str = "n8n"
    physical_credential_id: str
    physical_name: Optional[str] = None
    physical_type: Optional[str] = None
    status: Optional[str] = "valid"


class CredentialMappingCreate(CredentialMappingBase):
    tenant_id: str


class CredentialMappingUpdate(BaseModel):
    physical_credential_id: Optional[str] = None
    physical_name: Optional[str] = None
    physical_type: Optional[str] = None
    status: Optional[str] = None


class CredentialMappingResponse(CredentialMappingBase):
    id: str
    tenant_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkflowCredentialDependency(BaseModel):
    """Indexed logical credential deps per workflow/provider"""
    workflow_id: str
    provider: str = "n8n"
    logical_credential_ids: List[str] = []
    updated_at: Optional[datetime] = None


# Preflight validation schemas

class CredentialIssue(BaseModel):
    """Issue found during credential preflight validation"""
    workflow_id: str
    workflow_name: str
    logical_credential_key: str  # format: type:name
    issue_type: str  # "missing_mapping" | "mapped_missing_in_target"
    message: str
    is_blocking: bool = True


class ResolvedMapping(BaseModel):
    """Successfully resolved credential mapping for promotion"""
    logical_key: str
    source_physical_name: str
    target_physical_name: str
    target_physical_id: str


class CredentialPreflightRequest(BaseModel):
    """Request for credential preflight validation"""
    source_environment_id: str
    target_environment_id: str
    workflow_ids: List[str]
    provider: str = "n8n"


class CredentialPreflightResult(BaseModel):
    """Result of credential preflight validation"""
    valid: bool
    blocking_issues: List[CredentialIssue] = []
    warnings: List[CredentialIssue] = []
    resolved_mappings: List[ResolvedMapping] = []


class CredentialDetail(BaseModel):
    """Enriched credential info with mapping status"""
    logical_key: str
    credential_type: str
    credential_name: str
    is_mapped: bool
    mapping_status: Optional[str] = None  # "valid" | "invalid" | "missing"
    target_environments: List[str] = []


class WorkflowCredentialDependencyResponse(BaseModel):
    """Response for workflow credential dependencies with enrichment"""
    workflow_id: str
    provider: str
    logical_credential_ids: List[str]
    credentials: List[CredentialDetail] = []
    updated_at: Optional[datetime] = None
