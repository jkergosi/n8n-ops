"""
Admin Usage Endpoints

Provides global usage overview, top tenants by metric, and tenants at/near limits.
"""

from fastapi import APIRouter, Query, Depends, HTTPException, status
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.services.database import db_service
from app.services.auth_service import get_current_user

router = APIRouter()


# ============================================================================
# Schemas
# ============================================================================

class UsageMetric(BaseModel):
    """Single usage metric with current/limit values."""
    name: str
    current: int
    limit: int
    percentage: float
    status: str  # ok, warning, critical, over_limit


class TenantUsageSummary(BaseModel):
    """Tenant with usage metrics."""
    tenant_id: str
    tenant_name: str
    plan: str
    status: str
    metrics: List[UsageMetric]
    total_usage_percentage: float


class TopTenant(BaseModel):
    """Tenant ranked by a specific metric."""
    rank: int
    tenant_id: str
    tenant_name: str
    plan: str
    value: int
    limit: Optional[int]
    percentage: Optional[float]
    trend: Optional[str]  # up, down, stable


class GlobalUsageStats(BaseModel):
    """Global usage statistics."""
    total_tenants: int
    total_workflows: int
    total_environments: int
    total_users: int
    total_executions_today: int
    total_executions_month: int
    tenants_at_limit: int
    tenants_over_limit: int
    tenants_near_limit: int


class GlobalUsageResponse(BaseModel):
    """Global usage response."""
    stats: GlobalUsageStats
    usage_by_plan: dict
    recent_growth: dict


class TopTenantsResponse(BaseModel):
    """Response for top tenants by metric."""
    metric: str
    period: str
    tenants: List[TopTenant]


class TenantsAtLimitResponse(BaseModel):
    """Response for tenants at/near limits."""
    total: int
    tenants: List[TenantUsageSummary]


# ============================================================================
# Plan Limits Configuration
# ============================================================================

PLAN_LIMITS = {
    "free": {
        "max_workflows": 10,
        "max_environments": 1,
        "max_users": 2,
        "max_executions_daily": 100,
    },
    "pro": {
        "max_workflows": 100,
        "max_environments": 3,
        "max_users": 10,
        "max_executions_daily": 1000,
    },
    "agency": {
        "max_workflows": 500,
        "max_environments": 10,
        "max_users": 50,
        "max_executions_daily": 10000,
    },
    "enterprise": {
        "max_workflows": -1,  # Unlimited
        "max_environments": -1,
        "max_users": -1,
        "max_executions_daily": -1,
    },
}


def get_limit(plan: str, metric: str) -> int:
    """Get limit for a plan and metric. Returns -1 for unlimited."""
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"]).get(metric, 0)


def calculate_usage_percentage(current: int, limit: int) -> float:
    """Calculate usage percentage. Returns 0 for unlimited."""
    if limit <= 0:  # Unlimited
        return 0
    return min(round((current / limit) * 100, 1), 999)  # Cap at 999%


def get_usage_status(percentage: float, limit: int) -> str:
    """Get usage status based on percentage."""
    if limit <= 0:  # Unlimited
        return "ok"
    if percentage >= 100:
        return "over_limit"
    if percentage >= 90:
        return "critical"
    if percentage >= 75:
        return "warning"
    return "ok"


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/", response_model=GlobalUsageResponse)
async def get_global_usage(
    user_info: dict = Depends(get_current_user)
):
    """
    Get global usage statistics across all tenants.

    Returns aggregate metrics, usage by plan, and growth trends.
    """
    try:
        # Get all tenants with their stats
        tenants_result = await db_service.client.table("tenants").select("*").execute()
        tenants = tenants_result.data or []

        # Get workflow counts
        workflows_result = await db_service.client.table("workflows").select("id, tenant_id").execute()
        workflows = workflows_result.data or []

        # Get environment counts
        envs_result = await db_service.client.table("environments").select("id, tenant_id").execute()
        environments = envs_result.data or []

        # Get user counts
        users_result = await db_service.client.table("users").select("id, tenant_id").execute()
        users = users_result.data or []

        # Get execution counts (today and month)
        today = datetime.utcnow().date()
        month_start = today.replace(day=1)

        executions_result = await db_service.client.table("executions").select("id, tenant_id, started_at").execute()
        executions = executions_result.data or []

        executions_today = sum(1 for e in executions if e.get("started_at", "")[:10] == str(today))
        executions_month = sum(1 for e in executions if e.get("started_at", "")[:10] >= str(month_start))

        # Count by tenant
        workflow_counts = {}
        env_counts = {}
        user_counts = {}

        for w in workflows:
            tid = w.get("tenant_id")
            workflow_counts[tid] = workflow_counts.get(tid, 0) + 1

        for e in environments:
            tid = e.get("tenant_id")
            env_counts[tid] = env_counts.get(tid, 0) + 1

        for u in users:
            tid = u.get("tenant_id")
            user_counts[tid] = user_counts.get(tid, 0) + 1

        # Calculate tenants at/near/over limits
        tenants_at_limit = 0
        tenants_over_limit = 0
        tenants_near_limit = 0

        usage_by_plan = {"free": 0, "pro": 0, "agency": 0, "enterprise": 0}

        for t in tenants:
            tid = t.get("id")
            plan = t.get("subscription_tier", "free") or "free"
            usage_by_plan[plan] = usage_by_plan.get(plan, 0) + 1

            # Check workflow limits
            wf_count = workflow_counts.get(tid, 0)
            wf_limit = get_limit(plan, "max_workflows")

            if wf_limit > 0:
                wf_pct = (wf_count / wf_limit) * 100
                if wf_pct >= 100:
                    tenants_over_limit += 1
                elif wf_pct >= 95:
                    tenants_at_limit += 1
                elif wf_pct >= 75:
                    tenants_near_limit += 1

        stats = GlobalUsageStats(
            total_tenants=len(tenants),
            total_workflows=len(workflows),
            total_environments=len(environments),
            total_users=len(users),
            total_executions_today=executions_today,
            total_executions_month=executions_month,
            tenants_at_limit=tenants_at_limit,
            tenants_over_limit=tenants_over_limit,
            tenants_near_limit=tenants_near_limit,
        )

        # Calculate growth (mock for now - would need historical data)
        recent_growth = {
            "tenants_7d": 5,
            "tenants_30d": 12,
            "workflows_7d": 25,
            "workflows_30d": 78,
            "executions_7d": 1500,
            "executions_30d": 8500,
        }

        return GlobalUsageResponse(
            stats=stats,
            usage_by_plan=usage_by_plan,
            recent_growth=recent_growth,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get global usage: {str(e)}"
        )


@router.get("/top-tenants", response_model=TopTenantsResponse)
async def get_top_tenants(
    metric: str = Query("workflows", description="Metric to rank by: workflows, users, environments, executions"),
    period: str = Query("all", description="Time period: today, week, month, all"),
    limit: int = Query(10, ge=1, le=50),
    user_info: dict = Depends(get_current_user)
):
    """
    Get top tenants ranked by a specific metric.
    """
    try:
        # Get all tenants
        tenants_result = await db_service.client.table("tenants").select("*").execute()
        tenants = {t["id"]: t for t in (tenants_result.data or [])}

        tenant_values = []

        if metric == "workflows":
            result = await db_service.client.table("workflows").select("tenant_id").execute()
            counts = {}
            for item in (result.data or []):
                tid = item.get("tenant_id")
                counts[tid] = counts.get(tid, 0) + 1

            for tid, count in counts.items():
                if tid in tenants:
                    t = tenants[tid]
                    plan = t.get("subscription_tier", "free") or "free"
                    limit_val = get_limit(plan, "max_workflows")
                    tenant_values.append({
                        "tenant_id": tid,
                        "tenant_name": t.get("name", "Unknown"),
                        "plan": plan,
                        "value": count,
                        "limit": limit_val if limit_val > 0 else None,
                    })

        elif metric == "users":
            result = await db_service.client.table("users").select("tenant_id").execute()
            counts = {}
            for item in (result.data or []):
                tid = item.get("tenant_id")
                counts[tid] = counts.get(tid, 0) + 1

            for tid, count in counts.items():
                if tid in tenants:
                    t = tenants[tid]
                    plan = t.get("subscription_tier", "free") or "free"
                    limit_val = get_limit(plan, "max_users")
                    tenant_values.append({
                        "tenant_id": tid,
                        "tenant_name": t.get("name", "Unknown"),
                        "plan": plan,
                        "value": count,
                        "limit": limit_val if limit_val > 0 else None,
                    })

        elif metric == "environments":
            result = await db_service.client.table("environments").select("tenant_id").execute()
            counts = {}
            for item in (result.data or []):
                tid = item.get("tenant_id")
                counts[tid] = counts.get(tid, 0) + 1

            for tid, count in counts.items():
                if tid in tenants:
                    t = tenants[tid]
                    plan = t.get("subscription_tier", "free") or "free"
                    limit_val = get_limit(plan, "max_environments")
                    tenant_values.append({
                        "tenant_id": tid,
                        "tenant_name": t.get("name", "Unknown"),
                        "plan": plan,
                        "value": count,
                        "limit": limit_val if limit_val > 0 else None,
                    })

        elif metric == "executions":
            # Filter by period
            date_filter = None
            if period == "today":
                date_filter = str(datetime.utcnow().date())
            elif period == "week":
                date_filter = str((datetime.utcnow() - timedelta(days=7)).date())
            elif period == "month":
                date_filter = str((datetime.utcnow() - timedelta(days=30)).date())

            result = await db_service.client.table("executions").select("tenant_id, started_at").execute()
            counts = {}
            for item in (result.data or []):
                if date_filter and item.get("started_at", "")[:10] < date_filter:
                    continue
                tid = item.get("tenant_id")
                counts[tid] = counts.get(tid, 0) + 1

            for tid, count in counts.items():
                if tid in tenants:
                    t = tenants[tid]
                    plan = t.get("subscription_tier", "free") or "free"
                    tenant_values.append({
                        "tenant_id": tid,
                        "tenant_name": t.get("name", "Unknown"),
                        "plan": plan,
                        "value": count,
                        "limit": None,
                    })

        # Sort by value descending
        tenant_values.sort(key=lambda x: x["value"], reverse=True)

        # Take top N and add rank
        top_tenants = []
        for i, tv in enumerate(tenant_values[:limit]):
            pct = None
            if tv["limit"]:
                pct = round((tv["value"] / tv["limit"]) * 100, 1)

            top_tenants.append(TopTenant(
                rank=i + 1,
                tenant_id=tv["tenant_id"],
                tenant_name=tv["tenant_name"],
                plan=tv["plan"],
                value=tv["value"],
                limit=tv["limit"],
                percentage=pct,
                trend="stable",  # Would need historical data for real trends
            ))

        return TopTenantsResponse(
            metric=metric,
            period=period,
            tenants=top_tenants,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get top tenants: {str(e)}"
        )


@router.get("/tenants-at-limit", response_model=TenantsAtLimitResponse)
async def get_tenants_at_limit(
    threshold: int = Query(75, ge=50, le=100, description="Percentage threshold for 'near limit'"),
    user_info: dict = Depends(get_current_user)
):
    """
    Get tenants that are at, near, or over their plan limits.
    """
    try:
        # Get all tenants
        tenants_result = await db_service.client.table("tenants").select("*").execute()
        tenants = tenants_result.data or []

        # Get counts
        workflows_result = await db_service.client.table("workflows").select("id, tenant_id").execute()
        envs_result = await db_service.client.table("environments").select("id, tenant_id").execute()
        users_result = await db_service.client.table("users").select("id, tenant_id").execute()

        workflow_counts = {}
        env_counts = {}
        user_counts = {}

        for w in (workflows_result.data or []):
            tid = w.get("tenant_id")
            workflow_counts[tid] = workflow_counts.get(tid, 0) + 1

        for e in (envs_result.data or []):
            tid = e.get("tenant_id")
            env_counts[tid] = env_counts.get(tid, 0) + 1

        for u in (users_result.data or []):
            tid = u.get("tenant_id")
            user_counts[tid] = user_counts.get(tid, 0) + 1

        # Find tenants at/near/over limits
        at_limit_tenants = []

        for t in tenants:
            tid = t.get("id")
            plan = t.get("subscription_tier", "free") or "free"

            if plan == "enterprise":
                continue  # Skip unlimited plans

            metrics = []
            max_pct = 0

            # Check workflows
            wf_current = workflow_counts.get(tid, 0)
            wf_limit = get_limit(plan, "max_workflows")
            wf_pct = calculate_usage_percentage(wf_current, wf_limit)
            wf_status = get_usage_status(wf_pct, wf_limit)
            max_pct = max(max_pct, wf_pct)

            metrics.append(UsageMetric(
                name="workflows",
                current=wf_current,
                limit=wf_limit,
                percentage=wf_pct,
                status=wf_status,
            ))

            # Check environments
            env_current = env_counts.get(tid, 0)
            env_limit = get_limit(plan, "max_environments")
            env_pct = calculate_usage_percentage(env_current, env_limit)
            env_status = get_usage_status(env_pct, env_limit)
            max_pct = max(max_pct, env_pct)

            metrics.append(UsageMetric(
                name="environments",
                current=env_current,
                limit=env_limit,
                percentage=env_pct,
                status=env_status,
            ))

            # Check users
            user_current = user_counts.get(tid, 0)
            user_limit = get_limit(plan, "max_users")
            user_pct = calculate_usage_percentage(user_current, user_limit)
            user_status = get_usage_status(user_pct, user_limit)
            max_pct = max(max_pct, user_pct)

            metrics.append(UsageMetric(
                name="users",
                current=user_current,
                limit=user_limit,
                percentage=user_pct,
                status=user_status,
            ))

            # Add to list if any metric is at/near/over threshold
            if max_pct >= threshold:
                at_limit_tenants.append(TenantUsageSummary(
                    tenant_id=tid,
                    tenant_name=t.get("name", "Unknown"),
                    plan=plan,
                    status=t.get("status", "active") or "active",
                    metrics=metrics,
                    total_usage_percentage=max_pct,
                ))

        # Sort by highest usage percentage
        at_limit_tenants.sort(key=lambda x: x.total_usage_percentage, reverse=True)

        return TenantsAtLimitResponse(
            total=len(at_limit_tenants),
            tenants=at_limit_tenants,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenants at limit: {str(e)}"
        )
