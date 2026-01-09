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


class FakeSupabaseTable:
    """Fake Supabase table for testing"""
    def __init__(self, data=None):
        self._data = data or []
        self._query = self

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def gte(self, *args, **kwargs):
        return self

    def lte(self, *args, **kwargs):
        return self

    def lt(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        return type('Response', (), {'data': self._data, 'count': len(self._data)})()


class FakeSupabaseClient:
    """Fake Supabase client for testing"""
    def __init__(self):
        self._executions = []

    def table(self, name):
        if name == "executions":
            return FakeSupabaseTable(self._executions)
        return FakeSupabaseTable([])


class FakeDB:
    def __init__(self):
        self.execution_calls = 0
        self.client = FakeSupabaseClient()

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
        return {"uptime_percent": 99.0}

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

    async def get_deployment_stats(self, tenant_id, since):
        return {"total": 5, "success": 4, "failed": 1, "blocked": 0}

    async def get_snapshot_stats(self, tenant_id, since):
        return {"created": 10, "restored": 2}

    async def get_recent_deployments_with_details(self, tenant_id, limit=5):
        return []

    async def create_environment_health_check(self, *args, **kwargs):
        return {"id": "hc-1", "checked_at": "now"}

    async def get_credentials(self, tenant_id, environment_id=None):
        return []

    async def get_last_workflow_failures_batch(self, tenant_id, workflow_ids, environment_id=None):
        return {}

    async def get_failed_executions(self, tenant_id, since, until, environment_id=None):
        return []

    async def get_error_intelligence_aggregated(self, tenant_id, since, until, environment_id=None):
        return []

    async def get_execution_count_in_range(self, tenant_id, since, until, environment_id=None):
        return 10  # Return small count to avoid SQL aggregation

    async def get_sparkline_aggregated(self, tenant_id, since, until, interval_minutes, environment_id=None):
        return None  # Return None to use client-side aggregation


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
async def test_sparkline_returns_warnings_when_limit_exceeded(monkeypatch):
    """Test that sparkline returns warnings when execution count exceeds limit"""
    class FakeDBWithManyExecutions(FakeDB):
        async def get_execution_count_in_range(self, tenant_id, since, until, environment_id=None):
            return 100000  # Exceeds SPARKLINE_MAX_EXECUTIONS (50000)

    db = FakeDBWithManyExecutions()
    service = ObservabilityService()
    monkeypatch.setattr("app.services.observability_service.db_service", db)

    # Patch settings to use lower threshold for testing
    from app.core.config import settings
    original_max = settings.SPARKLINE_MAX_EXECUTIONS
    settings.SPARKLINE_MAX_EXECUTIONS = 50000

    try:
        sparklines = await service._get_sparkline_data("tenant-1", TimeRange.TWENTY_FOUR_HOURS)

        # Should have warnings
        assert "warnings" in sparklines
        assert len(sparklines["warnings"]) > 0

        # Check warning structure
        warning = sparklines["warnings"][0]
        assert warning.code == "EXECUTION_LIMIT_EXCEEDED"
        assert "100,000" in warning.message  # Contains actual count
        assert warning.actual_count == 100000
        assert warning.limit_applied == 50000
    finally:
        settings.SPARKLINE_MAX_EXECUTIONS = original_max


@pytest.mark.asyncio
async def test_sparkline_no_warnings_for_small_datasets(monkeypatch):
    """Test that sparkline returns no warnings for small datasets"""
    db = FakeDB()  # Returns 10 executions
    service = ObservabilityService()
    monkeypatch.setattr("app.services.observability_service.db_service", db)

    sparklines = await service._get_sparkline_data("tenant-1", TimeRange.TWENTY_FOUR_HOURS)

    # Should not have warnings for small datasets
    assert "warnings" not in sparklines or sparklines.get("warnings") is None or len(sparklines.get("warnings", [])) == 0

    # Should still have sparkline data
    assert "executions" in sparklines
    assert "success_rate" in sparklines
    assert "duration" in sparklines
    assert "failures" in sparklines


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

