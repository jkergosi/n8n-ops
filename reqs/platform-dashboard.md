# Platform Admin → Platform Dashboard (Control Plane) — Claude Code Instructions

## Objective
Replace the current **Platform Admin page** (link list / CRUD-first) with a **Platform Dashboard** that provides platform-wide oversight:
1) Platform health
2) Tenant health/outliers
3) Capacity/abuse pressure
4) Revenue & enforcement posture
5) Security & admin activity
6) Incidents & support triage

**Design rules**
- Dashboard is **insight-first**. CRUD pages exist, but they are secondary links.
- Keep the first iteration minimal and data-backed. If you can’t populate a widget reliably, omit it.
- No marketing/pricing content on the dashboard.
- All queries must be efficient (aggregate endpoints; avoid N+1).

---

## 1) Navigation & Routing

### 1.1 Sidebar
Under the Platform section:
- Rename current entry to **Platform Dashboard**
- Route: `/platform` (or `/platform/dashboard` if routing conventions require)
- Keep existing pages accessible but not primary:
  - Tenants
  - Users
  - Platform Admins (Superusers)
  - Audit Logs
  - Incidents (if exists)
  - System Settings

### 1.2 Access control
- Platform Dashboard is **platform-admin only**
- Enforce server-side authorization on all platform endpoints.

---

## 2) Platform Dashboard Layout (V1)

### Layout rule
- **Top row:** Platform Health
- **Middle:** Tenant Health Overview + Outliers
- **Lower:** Usage & Capacity Pressure + Revenue & Enforcement
- **Bottom:** Security & Admin Activity + Incidents/Triage
- **Right column or footer:** Shortcuts (secondary links)

Use existing UI patterns (cards/tiles/tables/badges).

---

## 3) Widgets (V1) — build only what you can back with data

### 3.1 Platform Health (Top row tiles)
Create 4 tiles (clickable to deeper pages/logs):
1. **API Health**
   - Metrics: uptime (optional), error rate (5xx% last 1h/24h), p95 latency
   - Click → platform logs / observability page (or a simple “System Metrics” page)
2. **Workers / Queue**
   - Metrics: queue depth, oldest job age, dead-letter count (if applicable)
   - Click → queue/worker page (or system metrics)
3. **Database**
   - Metrics: connection usage %, slow queries count (last 1h), backup status (last success time)
   - Click → system metrics / DB status page
4. **Schedulers / Jobs**
   - Metrics: last run + failures for key jobs (metering, drift checks, sync)
   - Click → jobs status page

**If you do not have queues/workers/jobs today:** implement API Health + basic DB status only, and leave others out.

---

### 3.2 Tenant Health Overview (cards + table)
Create:
- Card: **Active Tenants**
  - `active_7d`, `active_30d`, total tenants
- Card: **At-Risk Tenants**
  - Count of tenants flagged by composite rule (see Section 5.3)
- Card: **Tenants with Drift**
  - Count last 24h/7d
- Card: **Tenants with Credential Failures**
  - Count last 24h/7d

Add tables (Top 10 lists):
- **Top Tenants by Failure Rate (24h)**
  - tenant, failures, total executions, failure%
- **Top Tenants with Drift (7d)**
  - tenant, drift environments count, last detected
- **Top Tenants with Credential Issues (7d)**
  - tenant, failing credentials count, last failure

Each row is clickable → tenant detail page (or tenant filtered view).

---

### 3.3 Usage & Capacity Pressure
Cards:
- **Executions (24h / 7d)** total + trend arrow if available
- **API Requests (24h)** total + error%
- **Storage** (db size + object storage if used)

Tables (Top 10):
- Top tenants by executions (24h/7d)
- Top tenants by workflows count
- Top tenants by environments count

Optional abuse/rate-limit signals (only if you log):
- “Tenants exceeding rate limits” (count + list)

---

### 3.4 Revenue & Plan Enforcement
Cards:
- **MRR** (current) + trend
- **Plan Distribution** (Free/Pro/Agency/Enterprise counts)
- **Trials** (started, expiring soon, converted)
- **Delinquent Orgs** (failed payments count)

Enforcement/Audit widgets (operational, not a settings UI):
- **Entitlement Exceptions**
  - Count + table of orgs where usage exceeds plan limit or enforcement override exists
  - Click → enforcement/audit page

---

### 3.5 Security & Admin Activity
Cards:
- **Impersonations**
  - Active now count + last 24h count
- **Admin Actions**
  - Count last 24h (writes/privileged actions)

Table:
- **Recent Platform Admin Activity** (last 20)
  - actor, action, target, timestamp

Optional security signals if logged:
- repeated auth failures by tenant
- unusual token creation spikes

---

### 3.6 Incidents & Support Triage
If you have an incident concept:
- Card: **Open Incidents**
- Table: **Incident Queue**
  - severity, tenant, status, age, updated

If you do not have incidents yet:
- Add a placeholder section (not a widget) with a single link: “Create incident system” (internal backlog item).

---

## 4) Drill-Down Pages (keep existing, add if missing)
From the dashboard, links should route to:
- `/platform/tenants` (list + search)
- `/platform/tenants/:id` (tenant detail: plan, usage, failures, drift, creds)
- `/platform/users` (search)
- `/platform/admins` (platform admins)
- `/platform/audit-logs`
- `/platform/system-metrics` (optional, can be simple)
- `/platform/enforcement` (entitlement exceptions / audits)
- `/platform/incidents` (if exists)

---

## 5) Backend/API (minimal, efficient)

### 5.1 Create a single overview endpoint
Implement:
- `GET /api/platform/overview`

Return structure (suggested):
```json
{
  "platform_health": {
    "api": {"error_rate_1h": 0.0, "error_rate_24h": 0.0, "p95_latency_ms_1h": 0},
    "db": {"connections_used_pct": 0.0, "slow_queries_1h": 0, "last_backup_at": "ISO"},
    "jobs": [{"name":"metering","last_run_at":"ISO","status":"ok|fail","failures_24h":0}],
    "queue": {"depth": 0, "oldest_job_age_sec": 0, "dead_letters_24h": 0}
  },
  "tenants": {
    "total": 0,
    "active_7d": 0,
    "active_30d": 0,
    "at_risk": 0,
    "with_drift_7d": 0,
    "with_credential_failures_7d": 0
  },
  "usage": {
    "executions_24h": 0,
    "executions_7d": 0,
    "api_requests_24h": 0,
    "storage_db_bytes": 0,
    "storage_obj_bytes": 0
  },
  "revenue": {
    "mrr_cents": 0,
    "plan_distribution": {"free":0,"pro":0,"agency":0,"enterprise":0},
    "trials": {"started_30d":0,"expiring_7d":0,"converted_30d":0},
    "delinquent_orgs": 0,
    "entitlement_exceptions": 0
  },
  "security": {
    "impersonations_active": 0,
    "impersonations_24h": 0,
    "admin_actions_24h": 0
  },
  "top_lists": {
    "tenants_by_fail_rate_24h": [],
    "tenants_by_executions_24h": [],
    "tenants_with_drift_7d": [],
    "tenants_with_credential_issues_7d": [],
    "entitlement_exceptions": [],
    "recent_admin_activity": [],
    "open_incidents": []
  }
}
```

### 5.2 Add supporting endpoints only as needed
If tables need pagination/filters beyond Top 10:
- `GET /api/platform/tenants?query=...`
- `GET /api/platform/tenants/:id/health`
- `GET /api/platform/audit-logs?query=...`
- `GET /api/platform/enforcement/exceptions?status=...`
- `GET /api/platform/incidents?...`

### 5.3 Define “At-Risk Tenant” (V1)
Keep it simple and explainable:
- At-risk if ANY:
  - failure_rate_24h >= 10% AND failures >= 20
  - drift_detected_count_7d >= 3
  - credential_failures_7d >= 5
  - delinquent == true
Store the computed value in the overview response (so UI is dumb/simple).

### 5.4 Performance constraints
- No N+1 queries. Use aggregates + grouped queries.
- Cache overview for 30–60 seconds (server-side) if expensive.

---

## 6) UI/UX Requirements
- Tiles show status states (OK/Warn/Critical) using existing badge semantics.
- Tables must be sortable by primary metric where possible.
- Every widget must have a drill-down destination.
- No “Feature Matrix” and no pricing content here.

---

## 7) Implementation Order (recommended)
1. Add platform dashboard route + platform-admin guard
2. Implement UI shell + empty states
3. Implement `/api/platform/overview` with minimal data (tenant counts, activity, executions)
4. Add Top 10 lists iteratively (fail rate, executions, drift, creds)
5. Add revenue signals (plan distribution, delinquent, MRR if available)
6. Add security/admin activity table
7. Add incidents section (if exists)
8. Validate performance and permissions

---

## 8) Acceptance Criteria
- Platform dashboard exists at `/platform` (or agreed route)
- Only platform admins can access it and its APIs
- Dashboard shows:
  - Platform health tiles (at least API + DB)
  - Tenant activity counts
  - Top outliers table(s)
  - Usage/capacity indicators
  - Revenue/enforcement posture (plan distribution at minimum)
  - Recent platform admin activity
- All widgets link to drill-down pages
- No marketing/pricing content on the dashboard
