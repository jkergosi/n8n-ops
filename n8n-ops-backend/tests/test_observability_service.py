import pytest

from app.services.observability_service import ObservabilityService
from app.schemas.observability import (
    KPIMetrics,
    WorkflowPerformance,
    EnvironmentHealth,
    PromotionSyncStats,
    ObservabilityOverview,
    TimeRange,
    EnvironmentStatus,
)


class FakeDB:
    def __init__(self):
        self.execution_calls = 0

    async def get_execution_stats(self, tenant_id: str, since: str, until: str, environment_id=None):
        self.execution_calls += 1
        if self.execution_calls == 1:
            return {
                "total_executions": 10,
                "success_count": 8,
                "failure_count": 2,
                "success_rate": 80.0,
                "avg_duration_ms": 120,
                "p95_duration_ms": 300,
            }
        return {
            "total_executions": 5,
            "success_count": 4,
            "failure_count": 1,
            "success_rate": 80.0,
            "avg_duration_ms": 100,
            "p95_duration_ms": 250,
        }

    async def get_workflow_execution_stats(self, tenant_id, since, until, limit=10, sort_by="executions", environment_id=None):
        return [
            {
                "workflow_id": "wf-1",
                "workflow_name": "Test",
                "execution_count": 5,
                "success_count": 4,
                "failure_count": 1,
                "error_rate": 20.0,
                "avg_duration_ms": 120,
                "p95_duration_ms": 300,
            }
        ]

    async def get_environments(self, tenant_id):
        return [
            {"id": "env-1", "n8n_name": "Dev", "n8n_type": "dev", "is_active": True},
        ]

    async def get_latest_health_check(self, tenant_id, env_id):
        return {"status": "healthy", "latency_ms": 42, "error_message": None}

    async def get_uptime_stats(self, tenant_id, env_id, since):
        return {"uptime": 0.99}

    async def get_deployments(self, tenant_id):
        return []

    async def get_snapshots(self, tenant_id, environment_id=None):
        return []

    async def get_workflows(self, tenant_id, environment_id=None):
        return [{"id": "w1", "active": True}]

    async def get_promotion_stats(self, tenant_id, since):
        return {"promotions": 1, "success": 1, "failed": 0, "syncs": 0}

    async def get_sync_stats(self, tenant_id, since):
        return {"syncs": 2, "success": 2, "failed": 0}

    async def create_environment_health_check(self, *args, **kwargs):
        return {"id": "hc-1", "checked_at": "now"}


@pytest.mark.asyncio
async def test_get_kpi_metrics_computes_delta(monkeypatch):
    db = FakeDB()
    service = ObservabilityService()
    monkeypatch.setattr("app.services.observability_service.db_service", db)

    metrics = await service.get_kpi_metrics("tenant-1", TimeRange.TWENTY_FOUR_HOURS, include_delta=True)

    assert metrics.total_executions == 10
    assert metrics.success_count == 8
    assert metrics.failure_count == 2
    # Delta computed against second call
    assert metrics.delta_executions == 5
    assert metrics.delta_success_rate == 0


@pytest.mark.asyncio
async def test_get_observability_overview_combines_sections(monkeypatch):
    db = FakeDB()
    service = ObservabilityService()
    monkeypatch.setattr("app.services.observability_service.db_service", db)

    overview = await service.get_observability_overview("tenant-1", TimeRange.SIX_HOURS)

    assert isinstance(overview, ObservabilityOverview)
    assert isinstance(overview.kpi_metrics, KPIMetrics)
    assert len(overview.workflow_performance) == 1
    assert len(overview.environment_health) == 1
    assert isinstance(overview.promotion_sync_stats, PromotionSyncStats)
    assert overview.environment_health[0].status == EnvironmentStatus.HEALTHY

