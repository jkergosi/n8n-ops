"""
Platform Overview Endpoint

Provides platform-wide dashboard data for platform admins.
Returns platform health, tenant health, usage, revenue, and security signals.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.services.database import db_service
from app.core.platform_admin import require_platform_admin

router = APIRouter()


# ============================================================================
# Schemas
# ============================================================================

class APIHealthMetrics(BaseModel):
    """API health metrics."""
    error_rate_1h: float = 0.0
    error_rate_24h: float = 0.0
    p95_latency_ms_1h: int = 0


class DBHealthMetrics(BaseModel):
    """Database health metrics."""
    connections_used_pct: float = 0.0
    slow_queries_1h: int = 0
    last_backup_at: Optional[str] = None


class JobStatus(BaseModel):
    """Background job status."""
    name: str
    last_run_at: Optional[str] = None
    status: str = "unknown"
    failures_24h: int = 0


class QueueMetrics(BaseModel):
    """Queue/worker metrics."""
    depth: int = 0
    oldest_job_age_sec: int = 0
    dead_letters_24h: int = 0


class PlatformHealthMetrics(BaseModel):
    """Platform health overview."""
    api: APIHealthMetrics = APIHealthMetrics()
    db: DBHealthMetrics = DBHealthMetrics()
    jobs: List[JobStatus] = []
    queue: QueueMetrics = QueueMetrics()


class TenantMetrics(BaseModel):
    """Tenant health overview."""
    total: int = 0
    active_7d: int = 0
    active_30d: int = 0
    at_risk: int = 0
    with_drift_7d: int = 0
    with_credential_failures_7d: int = 0


class UsageMetrics(BaseModel):
    """Platform usage metrics."""
    executions_24h: int = 0
    executions_7d: int = 0
    api_requests_24h: int = 0
    storage_db_bytes: int = 0
    storage_obj_bytes: int = 0


class TrialMetrics(BaseModel):
    """Trial subscription metrics."""
    started_30d: int = 0
    expiring_7d: int = 0
    converted_30d: int = 0


class PlanDistribution(BaseModel):
    """Distribution of tenants by plan."""
    free: int = 0
    pro: int = 0
    agency: int = 0
    enterprise: int = 0


class RevenueMetrics(BaseModel):
    """Revenue and billing metrics."""
    mrr_cents: int = 0
    plan_distribution: PlanDistribution = PlanDistribution()
    trials: TrialMetrics = TrialMetrics()
    delinquent_orgs: int = 0
    entitlement_exceptions: int = 0


class SecurityMetrics(BaseModel):
    """Security and admin activity metrics."""
    impersonations_active: int = 0
    impersonations_24h: int = 0
    admin_actions_24h: int = 0


class TenantFailRate(BaseModel):
    """Tenant failure rate entry."""
    tenant_id: str
    tenant_name: str
    failures: int
    total_executions: int
    failure_rate: float


class TenantExecutions(BaseModel):
    """Tenant execution count entry."""
    tenant_id: str
    tenant_name: str
    executions: int


class TenantDrift(BaseModel):
    """Tenant drift entry."""
    tenant_id: str
    tenant_name: str
    drift_count: int
    last_detected: Optional[str] = None


class TenantCredentialIssue(BaseModel):
    """Tenant credential issue entry."""
    tenant_id: str
    tenant_name: str
    failing_count: int
    last_failure: Optional[str] = None


class EntitlementException(BaseModel):
    """Entitlement exception entry."""
    tenant_id: str
    tenant_name: str
    exception_type: str
    description: str


class AdminActivity(BaseModel):
    """Recent admin activity entry."""
    actor_id: str
    actor_name: str
    action: str
    target: Optional[str] = None
    timestamp: str


class OpenIncident(BaseModel):
    """Open incident entry."""
    id: str
    severity: str
    tenant_id: str
    tenant_name: str
    status: str
    age_hours: int
    updated_at: str


class TopLists(BaseModel):
    """Top 10 lists for dashboard."""
    tenants_by_fail_rate_24h: List[TenantFailRate] = []
    tenants_by_executions_24h: List[TenantExecutions] = []
    tenants_with_drift_7d: List[TenantDrift] = []
    tenants_with_credential_issues_7d: List[TenantCredentialIssue] = []
    entitlement_exceptions: List[EntitlementException] = []
    recent_admin_activity: List[AdminActivity] = []
    open_incidents: List[OpenIncident] = []


class PlatformOverviewResponse(BaseModel):
    """Complete platform overview response."""
    platform_health: PlatformHealthMetrics = PlatformHealthMetrics()
    tenants: TenantMetrics = TenantMetrics()
    usage: UsageMetrics = UsageMetrics()
    revenue: RevenueMetrics = RevenueMetrics()
    security: SecurityMetrics = SecurityMetrics()
    top_lists: TopLists = TopLists()


# ============================================================================
# Helper Functions
# ============================================================================

def get_tenant_map(tenant_ids: List[str]) -> dict:
    """Get tenant id -> name mapping."""
    if not tenant_ids:
        return {}
    try:
        resp = db_service.client.table("tenants").select("id, name").in_("id", tenant_ids).execute()
        return {t["id"]: t["name"] for t in (resp.data or [])}
    except Exception:
        return {}


def is_tenant_at_risk(
    failure_rate_24h: float,
    failures_24h: int,
    drift_count_7d: int,
    credential_failures_7d: int,
    is_delinquent: bool
) -> bool:
    """
    Determine if a tenant is at risk based on the V1 rules:
    - failure_rate_24h >= 10% AND failures >= 20
    - drift_detected_count_7d >= 3
    - credential_failures_7d >= 5
    - delinquent == true
    """
    if failure_rate_24h >= 0.10 and failures_24h >= 20:
        return True
    if drift_count_7d >= 3:
        return True
    if credential_failures_7d >= 5:
        return True
    if is_delinquent:
        return True
    return False


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/overview", response_model=PlatformOverviewResponse)
async def get_platform_overview(
    _: dict = Depends(require_platform_admin()),
):
    """
    Get platform-wide overview for the dashboard.

    Returns platform health, tenant metrics, usage, revenue, and security signals.
    Requires platform admin access.
    """
    try:
        now = datetime.utcnow()
        cutoff_24h = (now - timedelta(hours=24)).isoformat()
        cutoff_7d = (now - timedelta(days=7)).isoformat()
        cutoff_30d = (now - timedelta(days=30)).isoformat()

        # Initialize response
        response = PlatformOverviewResponse()

        # ====================================================================
        # Platform Health (API + DB + Jobs)
        # ====================================================================

        # API Health - we don't have metrics collection yet, so return defaults
        response.platform_health.api = APIHealthMetrics(
            error_rate_1h=0.0,
            error_rate_24h=0.0,
            p95_latency_ms_1h=0
        )

        # DB Health - basic health check
        response.platform_health.db = DBHealthMetrics(
            connections_used_pct=0.0,  # Would need PG stats
            slow_queries_1h=0,
            last_backup_at=None  # Would need backup system integration
        )

        # Background Jobs Status
        try:
            jobs_resp = db_service.client.table("background_jobs").select(
                "job_type, status, created_at, finished_at"
            ).order("created_at", desc=True).limit(100).execute()

            job_types = {}
            for job in (jobs_resp.data or []):
                jt = job.get("job_type", "unknown")
                if jt not in job_types:
                    job_types[jt] = {
                        "last_run_at": job.get("finished_at") or job.get("created_at"),
                        "status": "ok" if job.get("status") == "completed" else "fail",
                        "failures_24h": 0
                    }
                # Count failures in 24h
                created = job.get("created_at", "")
                if created >= cutoff_24h and job.get("status") == "failed":
                    job_types[jt]["failures_24h"] += 1

            response.platform_health.jobs = [
                JobStatus(name=name, **data) for name, data in job_types.items()
            ]
        except Exception:
            pass

        # Queue metrics (if we have a queue table)
        response.platform_health.queue = QueueMetrics(depth=0, oldest_job_age_sec=0, dead_letters_24h=0)

        # ====================================================================
        # Tenant Metrics
        # ====================================================================

        # Total tenants
        try:
            total_resp = db_service.client.table("tenants").select("id", count="exact").execute()
            response.tenants.total = total_resp.count or 0
        except Exception:
            pass

        # Active tenants (have users who logged in recently - approximation via updated_at)
        try:
            # Get tenants with recent activity (users with recent updated_at)
            active_7d_resp = db_service.client.table("users").select(
                "tenant_id"
            ).gte("updated_at", cutoff_7d).execute()
            active_7d_ids = set(u.get("tenant_id") for u in (active_7d_resp.data or []) if u.get("tenant_id"))
            response.tenants.active_7d = len(active_7d_ids)

            active_30d_resp = db_service.client.table("users").select(
                "tenant_id"
            ).gte("updated_at", cutoff_30d).execute()
            active_30d_ids = set(u.get("tenant_id") for u in (active_30d_resp.data or []) if u.get("tenant_id"))
            response.tenants.active_30d = len(active_30d_ids)
        except Exception:
            pass

        # Tenants with drift (last 7 days)
        try:
            # Check drift_incidents table
            drift_resp = db_service.client.table("drift_incidents").select(
                "tenant_id"
            ).gte("created_at", cutoff_7d).execute()
            drift_tenant_ids = set(d.get("tenant_id") for d in (drift_resp.data or []) if d.get("tenant_id"))
            response.tenants.with_drift_7d = len(drift_tenant_ids)
        except Exception:
            # Try environments table
            try:
                drift_env_resp = db_service.client.table("environments").select(
                    "tenant_id"
                ).eq("drift_detected", True).execute()
                drift_tenant_ids = set(e.get("tenant_id") for e in (drift_env_resp.data or []) if e.get("tenant_id"))
                response.tenants.with_drift_7d = len(drift_tenant_ids)
            except Exception:
                pass

        # Tenants with credential failures (last 7 days)
        try:
            cred_resp = db_service.client.table("credentials").select(
                "tenant_id"
            ).in_("health_status", ["failing", "error", "failed"]).execute()
            cred_tenant_ids = set(c.get("tenant_id") for c in (cred_resp.data or []) if c.get("tenant_id"))
            response.tenants.with_credential_failures_7d = len(cred_tenant_ids)
        except Exception:
            pass

        # ====================================================================
        # Usage Metrics
        # ====================================================================

        # Executions 24h and 7d
        try:
            exec_24h_resp = db_service.client.table("executions").select(
                "id", count="exact"
            ).gte("started_at", cutoff_24h).execute()
            response.usage.executions_24h = exec_24h_resp.count or 0

            exec_7d_resp = db_service.client.table("executions").select(
                "id", count="exact"
            ).gte("started_at", cutoff_7d).execute()
            response.usage.executions_7d = exec_7d_resp.count or 0
        except Exception:
            pass

        # ====================================================================
        # Revenue & Plan Distribution
        # ====================================================================

        try:
            plans_resp = db_service.client.table("tenants").select("subscription_tier").execute()
            plan_counts = {"free": 0, "pro": 0, "agency": 0, "enterprise": 0}
            for t in (plans_resp.data or []):
                tier = (t.get("subscription_tier") or "free").lower()
                if tier in plan_counts:
                    plan_counts[tier] += 1
                elif "agency" in tier:
                    plan_counts["agency"] += 1
                elif "enterprise" in tier:
                    plan_counts["enterprise"] += 1
                elif "pro" in tier:
                    plan_counts["pro"] += 1
                else:
                    plan_counts["free"] += 1

            response.revenue.plan_distribution = PlanDistribution(**plan_counts)
        except Exception:
            pass

        # Delinquent orgs (check for payment_status or stripe_subscription_status)
        try:
            delinquent_resp = db_service.client.table("tenants").select(
                "id", count="exact"
            ).eq("payment_status", "delinquent").execute()
            response.revenue.delinquent_orgs = delinquent_resp.count or 0
        except Exception:
            pass

        # Entitlement exceptions (check entitlement_overrides table)
        try:
            overrides_resp = db_service.client.table("entitlement_overrides").select(
                "id", count="exact"
            ).execute()
            response.revenue.entitlement_exceptions = overrides_resp.count or 0
        except Exception:
            pass

        # ====================================================================
        # Security Metrics
        # ====================================================================

        # Active impersonation sessions
        try:
            active_imp_resp = db_service.client.table("platform_impersonation_sessions").select(
                "id", count="exact"
            ).is_("ended_at", "null").execute()
            response.security.impersonations_active = active_imp_resp.count or 0

            imp_24h_resp = db_service.client.table("platform_impersonation_sessions").select(
                "id", count="exact"
            ).gte("created_at", cutoff_24h).execute()
            response.security.impersonations_24h = imp_24h_resp.count or 0
        except Exception:
            pass

        # Admin actions (from audit logs)
        try:
            admin_actions_resp = db_service.client.table("audit_logs").select(
                "id", count="exact"
            ).gte("created_at", cutoff_24h).in_(
                "action_type", ["impersonation.write", "platform.admin_action", "entitlement.override"]
            ).execute()
            response.security.admin_actions_24h = admin_actions_resp.count or 0
        except Exception:
            pass

        # ====================================================================
        # Top Lists
        # ====================================================================

        # Top tenants by failure rate (24h)
        try:
            # Get all executions in last 24h grouped by tenant
            exec_resp = db_service.client.table("executions").select(
                "tenant_id, status"
            ).gte("started_at", cutoff_24h).execute()

            tenant_exec_stats = {}
            for e in (exec_resp.data or []):
                tid = e.get("tenant_id")
                if not tid:
                    continue
                if tid not in tenant_exec_stats:
                    tenant_exec_stats[tid] = {"total": 0, "failed": 0}
                tenant_exec_stats[tid]["total"] += 1
                if e.get("status") == "failed":
                    tenant_exec_stats[tid]["failed"] += 1

            # Calculate failure rates
            fail_rates = []
            for tid, stats in tenant_exec_stats.items():
                if stats["total"] > 0:
                    rate = stats["failed"] / stats["total"]
                    fail_rates.append({
                        "tenant_id": tid,
                        "failures": stats["failed"],
                        "total_executions": stats["total"],
                        "failure_rate": round(rate, 4)
                    })

            # Sort by failure rate descending
            fail_rates.sort(key=lambda x: x["failure_rate"], reverse=True)
            top_fail = fail_rates[:10]

            # Get tenant names
            tenant_ids = [f["tenant_id"] for f in top_fail]
            tenant_map = get_tenant_map(tenant_ids)

            response.top_lists.tenants_by_fail_rate_24h = [
                TenantFailRate(
                    tenant_id=f["tenant_id"],
                    tenant_name=tenant_map.get(f["tenant_id"], "Unknown"),
                    failures=f["failures"],
                    total_executions=f["total_executions"],
                    failure_rate=f["failure_rate"]
                ) for f in top_fail
            ]
        except Exception:
            pass

        # Top tenants by executions (24h)
        try:
            exec_counts = {}
            for e in (exec_resp.data or []):
                tid = e.get("tenant_id")
                if tid:
                    exec_counts[tid] = exec_counts.get(tid, 0) + 1

            sorted_execs = sorted(exec_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            tenant_ids = [t[0] for t in sorted_execs]
            tenant_map = get_tenant_map(tenant_ids)

            response.top_lists.tenants_by_executions_24h = [
                TenantExecutions(
                    tenant_id=tid,
                    tenant_name=tenant_map.get(tid, "Unknown"),
                    executions=count
                ) for tid, count in sorted_execs
            ]
        except Exception:
            pass

        # Top tenants with drift (7d)
        try:
            drift_resp = db_service.client.table("drift_incidents").select(
                "tenant_id, created_at"
            ).gte("created_at", cutoff_7d).execute()

            drift_counts = {}
            drift_last = {}
            for d in (drift_resp.data or []):
                tid = d.get("tenant_id")
                if not tid:
                    continue
                drift_counts[tid] = drift_counts.get(tid, 0) + 1
                created = d.get("created_at", "")
                if created > drift_last.get(tid, ""):
                    drift_last[tid] = created

            sorted_drift = sorted(drift_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            tenant_ids = [t[0] for t in sorted_drift]
            tenant_map = get_tenant_map(tenant_ids)

            response.top_lists.tenants_with_drift_7d = [
                TenantDrift(
                    tenant_id=tid,
                    tenant_name=tenant_map.get(tid, "Unknown"),
                    drift_count=count,
                    last_detected=drift_last.get(tid)
                ) for tid, count in sorted_drift
            ]
        except Exception:
            pass

        # Top tenants with credential issues (7d)
        try:
            cred_resp = db_service.client.table("credentials").select(
                "tenant_id, health_status, updated_at"
            ).in_("health_status", ["failing", "error", "failed"]).execute()

            cred_counts = {}
            cred_last = {}
            for c in (cred_resp.data or []):
                tid = c.get("tenant_id")
                if not tid:
                    continue
                cred_counts[tid] = cred_counts.get(tid, 0) + 1
                updated = c.get("updated_at", "")
                if updated > cred_last.get(tid, ""):
                    cred_last[tid] = updated

            sorted_creds = sorted(cred_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            tenant_ids = [t[0] for t in sorted_creds]
            tenant_map = get_tenant_map(tenant_ids)

            response.top_lists.tenants_with_credential_issues_7d = [
                TenantCredentialIssue(
                    tenant_id=tid,
                    tenant_name=tenant_map.get(tid, "Unknown"),
                    failing_count=count,
                    last_failure=cred_last.get(tid)
                ) for tid, count in sorted_creds
            ]
        except Exception:
            pass

        # Entitlement exceptions
        try:
            overrides_resp = db_service.client.table("entitlement_overrides").select(
                "tenant_id, feature_key, value, reason"
            ).limit(10).execute()

            tenant_ids = [o.get("tenant_id") for o in (overrides_resp.data or []) if o.get("tenant_id")]
            tenant_map = get_tenant_map(tenant_ids)

            response.top_lists.entitlement_exceptions = [
                EntitlementException(
                    tenant_id=o.get("tenant_id", ""),
                    tenant_name=tenant_map.get(o.get("tenant_id", ""), "Unknown"),
                    exception_type=o.get("feature_key", "unknown"),
                    description=o.get("reason", "")
                ) for o in (overrides_resp.data or [])
            ]
        except Exception:
            pass

        # Recent admin activity
        try:
            audit_resp = db_service.client.table("audit_logs").select(
                "actor_id, action_type, action, resource_type, resource_id, created_at"
            ).order("created_at", desc=True).limit(20).execute()

            actor_ids = [a.get("actor_id") for a in (audit_resp.data or []) if a.get("actor_id")]
            actor_names = {}
            if actor_ids:
                users_resp = db_service.client.table("users").select("id, name").in_("id", actor_ids).execute()
                actor_names = {u["id"]: u["name"] for u in (users_resp.data or [])}

            response.top_lists.recent_admin_activity = [
                AdminActivity(
                    actor_id=a.get("actor_id", ""),
                    actor_name=actor_names.get(a.get("actor_id", ""), "Unknown"),
                    action=a.get("action") or a.get("action_type", ""),
                    target=f"{a.get('resource_type', '')}/{a.get('resource_id', '')}" if a.get("resource_type") else None,
                    timestamp=a.get("created_at", "")
                ) for a in (audit_resp.data or [])
            ]
        except Exception:
            pass

        # Open incidents
        try:
            incidents_resp = db_service.client.table("drift_incidents").select(
                "id, severity, tenant_id, status, created_at, updated_at"
            ).in_("status", ["open", "acknowledged"]).order("created_at", desc=True).limit(10).execute()

            tenant_ids = [i.get("tenant_id") for i in (incidents_resp.data or []) if i.get("tenant_id")]
            tenant_map = get_tenant_map(tenant_ids)

            response.top_lists.open_incidents = [
                OpenIncident(
                    id=i.get("id", ""),
                    severity=i.get("severity", "medium"),
                    tenant_id=i.get("tenant_id", ""),
                    tenant_name=tenant_map.get(i.get("tenant_id", ""), "Unknown"),
                    status=i.get("status", "open"),
                    age_hours=int((now - datetime.fromisoformat(i.get("created_at", now.isoformat()).replace("Z", "+00:00").replace("+00:00", ""))).total_seconds() / 3600) if i.get("created_at") else 0,
                    updated_at=i.get("updated_at", "")
                ) for i in (incidents_resp.data or [])
            ]
        except Exception:
            pass

        # ====================================================================
        # Calculate At-Risk Tenants
        # ====================================================================
        try:
            at_risk_count = 0

            # Get all tenants
            all_tenants_resp = db_service.client.table("tenants").select(
                "id, payment_status"
            ).execute()

            for tenant in (all_tenants_resp.data or []):
                tid = tenant.get("id")
                if not tid:
                    continue

                # Get tenant stats
                stats = tenant_exec_stats.get(tid, {"total": 0, "failed": 0})
                failure_rate = stats["failed"] / stats["total"] if stats["total"] > 0 else 0
                drift_count = drift_counts.get(tid, 0) if 'drift_counts' in dir() else 0
                cred_failures = cred_counts.get(tid, 0) if 'cred_counts' in dir() else 0
                is_delinquent = tenant.get("payment_status") == "delinquent"

                if is_tenant_at_risk(failure_rate, stats["failed"], drift_count, cred_failures, is_delinquent):
                    at_risk_count += 1

            response.tenants.at_risk = at_risk_count
        except Exception:
            pass

        return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"Platform overview error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch platform overview: {str(e)}"
        )
