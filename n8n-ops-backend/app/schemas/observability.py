from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class EnvironmentStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNREACHABLE = "unreachable"


class DriftState(str, Enum):
    IN_SYNC = "in_sync"
    DRIFT = "drift"
    UNKNOWN = "unknown"


class TimeRange(str, Enum):
    ONE_HOUR = "1h"
    SIX_HOURS = "6h"
    TWENTY_FOUR_HOURS = "24h"
    SEVEN_DAYS = "7d"
    THIRTY_DAYS = "30d"


# Health Check Models
class HealthCheckCreate(BaseModel):
    environment_id: str
    status: EnvironmentStatus
    latency_ms: Optional[int] = None
    error_message: Optional[str] = None


class HealthCheckResponse(BaseModel):
    id: str
    tenant_id: str
    environment_id: str
    status: EnvironmentStatus
    latency_ms: Optional[int] = None
    checked_at: datetime
    error_message: Optional[str] = None


# KPI/Metrics Models
class KPIMetrics(BaseModel):
    total_executions: int
    success_count: int
    failure_count: int
    success_rate: float
    avg_duration_ms: float
    p95_duration_ms: Optional[float] = None
    delta_executions: Optional[int] = None
    delta_success_rate: Optional[float] = None


class WorkflowPerformance(BaseModel):
    workflow_id: str
    workflow_name: str
    execution_count: int
    success_count: int
    failure_count: int
    error_rate: float
    avg_duration_ms: float
    p95_duration_ms: Optional[float] = None


class EnvironmentHealth(BaseModel):
    environment_id: str
    environment_name: str
    environment_type: Optional[str] = None
    status: EnvironmentStatus
    latency_ms: Optional[int] = None
    uptime_percent: float
    active_workflows: int
    total_workflows: int
    last_deployment_at: Optional[datetime] = None
    last_snapshot_at: Optional[datetime] = None
    drift_state: DriftState
    last_checked_at: Optional[datetime] = None


class RecentDeployment(BaseModel):
    id: str
    pipeline_name: Optional[str] = None
    source_environment_name: str
    target_environment_name: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None


class PromotionSyncStats(BaseModel):
    promotions_total: int
    promotions_success: int
    promotions_failed: int
    promotions_blocked: int
    snapshots_created: int
    snapshots_restored: int
    drift_count: int
    recent_deployments: List[RecentDeployment]


class ObservabilityOverview(BaseModel):
    kpi_metrics: KPIMetrics
    workflow_performance: List[WorkflowPerformance]
    environment_health: List[EnvironmentHealth]
    promotion_sync_stats: Optional[PromotionSyncStats] = None
