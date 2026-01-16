# 00 - System Overview

**Generated:** 2026-01-08
**Evidence-Based:** Repository scan only

### Quick Reference

| Topic | Document |
|-------|----------|
| User-facing terminology mapping | `14_terminology_and_rules.md` §1 |
| Unmanaged workflow decision flow | `14_terminology_and_rules.md` §2 |
| GIT_UNAVAILABLE state handling | `14_terminology_and_rules.md` §3 |
| DEV environment rules | `14_terminology_and_rules.md` §4 |
| Sync removal guarantees | `14_terminology_and_rules.md` §5 |

## Repository Structure

### Top-Level Structure

```
n8n-ops-trees/
├── app-back/          # FastAPI backend application
├── app-front/                # React frontend application
├── mvp_readiness_pack/        # This documentation pack
├── scripts/                   # Utility scripts (port management)
└── docs/                      # Root-level documentation
```

### Backend Structure (`app-back/`)

**Evidence:** `app-back/app/` directory structure

```
app-back/
├── app/
│   ├── main.py                # FastAPI app entrypoint, router registration, startup/shutdown
│   ├── api/
│   │   └── endpoints/         # 51 endpoint modules (50 .py files)
│   ├── core/                  # Core utilities (rbac, platform_admin, tenant_isolation, etc.)
│   ├── schemas/               # 27 Pydantic schema files
│   ├── services/              # 64 service files (59 .py, 5 .md)
│   └── seed/                  # Database seeding scripts
├── alembic/                   # Database migrations (63 version files)
├── tests/                     # 103 test files (85 .py, 16 .json, 2 .md)
├── docs/                      # Backend documentation
│   └── security/             # RLS policy documentation (7 files)
└── scripts/                   # Utility scripts (19 files)
```

### Frontend Structure (`app-front/`)

**Evidence:** `app-front/src/` directory structure

```
app-front/
├── src/
│   ├── App.tsx                # Root component
│   ├── main.tsx               # Entry point
│   ├── components/            # React components
│   ├── pages/                 # Page components (39 admin pages, platform pages, etc.)
│   ├── lib/                   # Utilities (SSE hooks, API client, auth)
│   ├── hooks/                 # Custom React hooks
│   ├── store/                 # Zustand state management
│   └── types/                  # TypeScript type definitions
└── package.json               # Dependencies and scripts
```

## Backend Entrypoints

### Main Application

**File:** `app-back/app/main.py`  
**Evidence:** Lines 16-20, 586-588

- **Entrypoint:** `app.main:app` (FastAPI instance)
- **Default Port:** 4000 (via uvicorn.run, line 588)
- **Router Prefix:** `/api/v1` (from `settings.API_V1_PREFIX`, line 18)

### Background Job Runners

**Evidence:** `app-back/app/main.py:startup_event()` (lines 403-451)

All schedulers start on application startup:

1. **Deployment Scheduler**
   - **File:** `app/services/deployment_scheduler.py:start_scheduler()`
   - **Purpose:** Execute scheduled deployments
   - **Started:** Line 419-420

2. **Drift Detection Scheduler**
   - **File:** `app/services/drift_scheduler.py:start_all_drift_schedulers()`
   - **Purpose:** Periodic drift checks
   - **Started:** Line 424-425

3. **Canonical Workflow Sync Scheduler**
   - **File:** `app/services/canonical_sync_scheduler.py:start_canonical_sync_schedulers()`
   - **Purpose:** Sync canonical workflows with Git
   - **Started:** Line 429-430

4. **Health Check Scheduler**
   - **File:** `app/services/health_check_scheduler.py:start_health_check_scheduler()`
   - **Purpose:** Monitor environment health
   - **Started:** Line 434-435

5. **Rollup Scheduler**
   - **File:** `app/services/rollup_scheduler.py:start_rollup_scheduler()`
   - **Purpose:** Pre-compute observability rollups
   - **Started:** Line 439-440

6. **Retention Enforcement Scheduler**
   - **File:** `app/services/background_jobs/retention_job.py:start_retention_scheduler()`
   - **Purpose:** Enforce data retention policies
   - **Started:** Line 444-445

7. **Downgrade Enforcement Scheduler**
   - **File:** `app/services/background_jobs/downgrade_enforcement_job.py:start_downgrade_enforcement_scheduler()`
   - **Purpose:** Enforce grace period expiry and detect over-limit resources
   - **Started:** Line 449-450

8. **Alert Rules Evaluation Scheduler**
   - **File:** `app/services/background_jobs/alert_rules_scheduler.py:start_alert_rules_scheduler()`
   - **Purpose:** Periodic evaluation of alert rules and trigger notifications
   - **Started:** Application startup (verified via migration `alembic/versions/20260108_add_alert_rules.py`)
   - **Interval:** Configurable via `ALERT_RULES_EVALUATION_INTERVAL_SECONDS`

**Shutdown:** All schedulers stopped in `shutdown_event()` (lines 493-528)

### SSE Entrypoints

**Evidence:** `app-back/app/api/endpoints/sse.py`

1. **Deployments SSE Stream**
   - **Path:** `/api/v1/sse/deployments` or `/api/v1/sse/deployments/{deployment_id}`
   - **Handler:** `sse.py:sse_deployments_stream()` (line 245)
   - **Auth:** `require_entitlement("workflow_ci_cd")`

2. **Background Jobs SSE Stream**
   - **Path:** `/api/v1/sse/background-jobs`
   - **Handler:** `sse.py:sse_background_jobs_stream()` (line 685)
   - **Auth:** Optional token parameter

## Frontend Entrypoints

### Main Application

**File:** `app-front/src/main.tsx`  
**Evidence:** Standard React entrypoint

- **Framework:** React 19.2.0 (from `package.json`)
- **Router:** React Router DOM 7.9.6
- **Build Tool:** Vite 7.2.4

### Key Routes (High-Level)

**Evidence:** `app-front/src/pages/` directory structure

**Core Pages:**
- `/environments` - `EnvironmentsPage.tsx`
- `/workflows` - `WorkflowsPage.tsx`
- `/deployments` - `DeploymentsPage.tsx`
- `/promotions` - `PromotionPage.tsx`
- `/pipelines` - `PipelinesPage.tsx`
- `/incidents` - `IncidentsPage.tsx`
- `/canonical-workflows` - `CanonicalWorkflowsPage.tsx`
- `/billing` - `BillingPage.tsx`
- `/observability` - `ObservabilityPage.tsx`
- `/executions` - `ExecutionsPage.tsx`

**Admin Pages:** `app-front/src/pages/admin/` (39 files)

**Platform Pages:** `app-front/src/pages/platform/` (4 files)

### SSE Hooks

**Evidence:** `app-front/src/lib/`

1. **Deployments SSE**
   - **File:** `use-deployments-sse.ts`
   - **Hook:** `useDeploymentsSSE()`
   - **Reconnect:** Exponential backoff (1s → 30s, max 10 attempts, line 66-68)

2. **Background Jobs SSE**
   - **File:** `use-background-jobs-sse.ts`
   - **Hook:** `useBackgroundJobsSSE()`
   - **Reconnect:** Exponential backoff (similar pattern)

## External Integrations

### Supabase

**Evidence:** `app-back/app/core/config.py` (lines 11-13)

- **URL:** `SUPABASE_URL` (from env)
- **Keys:** `SUPABASE_KEY` (anon), `SUPABASE_SERVICE_KEY` (service role)
- **Usage:** 
  - Backend uses `SUPABASE_SERVICE_KEY` (bypasses RLS)
  - Frontend uses `SUPABASE_KEY` (enforces RLS when enabled)
- **Database:** PostgreSQL via Supabase
- **Auth:** JWT-based authentication via Supabase Auth

**RLS Status:** 12 of 76 tables have RLS enabled (15.8%)  
**Evidence:** `app-back/docs/security/RLS_POLICIES.md` (line 5)

### Stripe

**Evidence:** `app-back/app/core/config.py` (lines 46-51)

- **Secret Key:** `STRIPE_SECRET_KEY`
- **Publishable Key:** `STRIPE_PUBLISHABLE_KEY`
- **Webhook Secret:** `STRIPE_WEBHOOK_SECRET`
- **Price IDs:** `STRIPE_PRO_PRICE_ID_MONTHLY`, `STRIPE_PRO_PRICE_ID_YEARLY`
- **Service:** `app/services/stripe_service.py`
- **Webhook Handler:** `app/api/endpoints/billing.py:stripe_webhook()`

### GitHub

**Evidence:** `app-back/app/core/config.py` (lines 18-22)

- **Token:** `GITHUB_TOKEN`
- **Repo:** `GITHUB_REPO_OWNER` / `GITHUB_REPO_NAME`
- **Branch:** `GITHUB_BRANCH` (default: "main")
- **Service:** `app/services/github_service.py`
- **Webhook Handler:** `app/api/endpoints/github_webhooks.py`

### N8N Provider APIs

**Evidence:** `app-back/app/services/n8n_client.py`

- **Adapter Pattern:** `app/services/adapters/n8n_adapter.py`
- **Provider Registry:** `app/services/provider_registry.py`
- **Multi-Provider Support:** Architecture supports multiple workflow providers

### Notifications

**Evidence:** `app-back/app/services/notification_service.py`

- **Service:** `app/services/notification_service.py`
- **Email:** SMTP via `app/services/email_service.py`
- **Config:** `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` (lines 54-58 in config.py)

## API Router Registration

**Evidence:** `app-back/app/main.py` (lines 94-380)

All routers registered with prefix `/api/v1`:

- `/environments` → `environments.router`
- `/workflows` → `workflows.router`
- `/promotions` → `promotions.router`
- `/pipelines` → `pipelines.router`
- `/deployments` → `deployments.router`
- `/incidents` → `incidents.router`
- `/canonical/workflows` → `canonical_workflows.router`
- `/billing` → `billing.router`
- `/observability` → `observability.router`
- `/executions` → `executions.router`
- `/sse` → `sse.router`
- `/platform` → `platform_impersonation.router`, `platform_console.router`, `platform_overview.router`
- `/admin/*` → Various admin routers
- `/health` → `health.router`

**Total Endpoint Modules:** 51 files in `app/api/endpoints/`

## Middleware

**Evidence:** `app-back/app/main.py`

1. **Impersonation Write Audit Middleware** (lines 22-82)
   - Logs all write operations during impersonation
   - Captures actor and impersonated user context

2. **CORS Middleware** (lines 85-91)
   - Allows origins from `BACKEND_CORS_ORIGINS`
   - Credentials enabled

3. **Global Exception Handler** (lines 531-584)
   - Catches unhandled exceptions
   - Emits `system.error` events
   - Returns 500 with error type

## Startup Cleanup

**Evidence:** `app-back/app/main.py:startup_event()` (lines 410-487)

- **Stale Job Cleanup:** `background_job_service.cleanup_stale_jobs(max_runtime_hours=24)` (line 412)
- **Stale Deployment Cleanup:** Marks `RUNNING` deployments >1hr old as `FAILED` (lines 454-487)

---

## CI/CD Workflows

**Evidence:** `.github/workflows/` directory contains 3 GitHub Actions workflows

### 1. Production Deployment

**File:** `.github/workflows/deploy-prod.yml`

**Trigger:**
- Release published event (GitHub releases)
- Manual dispatch with `deploy-prod` confirmation input (requires exact match)

**Jobs:**
1. **Pre-Deploy Backup**
   - Creates database backup artifact
   - Retention: 30 days
   - Stored as GitHub Actions artifact

2. **Database Migration**
   - Runs Alembic migrations with advisory lock
   - Ensures only one migration runs at a time
   - Fails deployment if migration fails

3. **Backend Deployment**
   - Deploys FastAPI backend to production server
   - Health check with 5 retries, 10-second intervals
   - Rollback on health check failure

4. **Frontend Deployment**
   - Builds Vite production bundle
   - Deploys static assets to CDN/hosting
   - Cache invalidation for updated assets

**Safety Mechanisms:**
- Concurrency group prevents multiple simultaneous deployments
- Manual approval required for production (via `deploy-prod` confirmation)
- Automatic rollback on health check failure
- Database backup before migration

### 2. Staging Deployment

**File:** `.github/workflows/deploy-staging.yml`

**Trigger:**
- Push to `develop` branch
- Manual dispatch

**Structure:** Similar to production deployment with staging-specific configuration

### 3. E2E Test Suite

**File:** `.github/workflows/e2e-tests.yml`

**Trigger:**
- Pull requests to `main` or `develop`
- Push to `main` branch

**Jobs:**

1. **Backend E2E Tests**
   - Runs pytest tests/e2e/
   - Uses respx for HTTP-boundary mocking (no real API calls)
   - Test database: PostgreSQL 15 with Supabase schema
   - Coverage: 5 E2E test suites (promotion, drift, canonical, downgrade, impersonation)

2. **Frontend E2E Tests**
   - Runs Playwright tests with chromium browser
   - Mocked backend API responses
   - Coverage: 4 Playwright specs (promotion, drift, canonical, impersonation flows)

3. **Test Summary**
   - Aggregates results from both jobs
   - Posts summary comment on PR (success/failure counts, duration)
   - Fails workflow if any test fails

**Test Infrastructure:**
- HTTP-boundary mocking with respx (backend)
- Playwright browser automation (frontend)
- Test factories and golden JSON fixtures
- GitHub Actions cache for dependencies

---

## Environment States

**Evidence:** `app-back/app/services/drift_detection_service.py`, `app-front/src/lib/environment-utils.ts`

### Baseline Presence Check

The environment state model is anchored on `is_env_onboarded()` from `git_snapshot_service.py`:

```python
async def is_env_onboarded(tenant_id, env_id) -> bool:
    # Returns True only if:
    # 1. current.json pointer exists
    # 2. Snapshot referenced by pointer exists and is readable
```

This function is the **single source of truth** for whether an environment has a valid baseline.

### Environment-Level States (DriftStatus)

| Status | Condition | Description |
|--------|-----------|-------------|
| `NEW` | `is_env_onboarded() == False` | No baseline exists; drift detection skipped |
| `IN_SYNC` | Baseline exists, runtime matches | All workflows match approved versions |
| `DRIFT_DETECTED` | Baseline exists, runtime differs | One or more workflows differ from approved |
| `GIT_UNAVAILABLE` | Git repo inaccessible | Repository deleted, forbidden, or unreachable |
| `ERROR` | Exception during detection | Check failed; see error details |
| `UNKNOWN` | Never checked | Initial state before first detection |

> **See also:** `14_terminology_and_rules.md` for complete state definitions, recovery paths, and action gating.

### NEW Environment Gate

When `is_env_onboarded()` returns `False`, drift detection **short-circuits immediately**:

```python
# drift_detection_service.py:detect_drift()
if not await git_snapshot_service.is_env_onboarded(tenant_id, environment_id):
    drift_status = DriftStatus.NEW
    return  # No per-workflow comparison runs
```

**Implications:**
- No `affected_workflows` computed
- No Git reads or comparisons performed
- Per-workflow status shows "Runtime only"

### UI Labels by Environment Class

| DriftStatus | DEV Label | STAGING/PROD Label |
|-------------|-----------|-------------------|
| `NEW` | "No baseline" | "Not onboarded" |
| `IN_SYNC` | "Matches baseline" | "Matches approved" |
| `DRIFT_DETECTED` | "Different from baseline" | "Drift detected" |
| `GIT_UNAVAILABLE` | "Git unavailable" | "Git unavailable" |
| `ERROR` | "Error" | "Error" |
| `UNKNOWN` | "Unknown" | "Unknown" |

### Action Gating

| Action | Condition | Rationale |
|--------|-----------|-----------|
| **Revert** | `isOnboarded === true` AND Git accessible | Cannot revert without baseline or Git access |
| **Keep Hotfix** | `isOnboarded === true` AND Git accessible | Cannot mark hotfix without baseline or Git access |
| **Save as Approved** | Git accessible | Creates or updates baseline (requires Git write) |
| **Promote** | Source `isOnboarded === true` AND Git accessible | Must have baseline and Git access to promote |

> **Note:** When `GIT_UNAVAILABLE`, all Git-dependent actions are blocked. See `14_terminology_and_rules.md` for full action matrix.

### Workflow Row Behavior

When environment is NEW (`isOnboarded === false`):
- All workflow rows show "Runtime only" badge
- No sync status comparison displayed
- Workflow count visible, but no drift categorization
