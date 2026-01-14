from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class ApprovalType(str, Enum):
    ONE_OF_N = "1 of N"
    ALL = "All"


class PipelineStageGates(BaseModel):
    require_clean_drift: bool = False
    run_pre_flight_validation: bool = False
    credentials_exist_in_target: bool = False
    nodes_supported_in_target: bool = False
    webhooks_available: bool = False
    target_environment_healthy: bool = False
    max_allowed_risk_level: RiskLevel = RiskLevel.HIGH


class PipelineStageApprovals(BaseModel):
    require_approval: bool = False
    approver_role: Optional[str] = None
    approver_group: Optional[str] = None
    required_approvals: Optional[ApprovalType] = None


class PipelineStageSchedule(BaseModel):
    restrict_promotion_times: bool = False
    allowed_days: Optional[List[str]] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class PipelineStagePolicyFlags(BaseModel):
    allow_placeholder_credentials: bool = False
    allow_overwriting_hotfixes: bool = False
    allow_force_promotion_on_conflicts: bool = False


class PipelineStage(BaseModel):
    source_environment_id: str
    target_environment_id: str
    gates: PipelineStageGates
    approvals: PipelineStageApprovals
    schedule: Optional[PipelineStageSchedule] = None
    policy_flags: PipelineStagePolicyFlags


class PipelineBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True
    environment_ids: List[str]
    stages: List[PipelineStage]


class PipelineCreate(PipelineBase):
    pass


class PipelineUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    environment_ids: Optional[List[str]] = None
    stages: Optional[List[PipelineStage]] = None


class PipelineResponse(PipelineBase):
    id: str
    tenant_id: str
    last_modified_by: Optional[str] = None
    last_modified_at: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

