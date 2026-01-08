# 00 - System Overview

**Generated:** 2026-01-XX  
**Evidence-Based:** Repository scan only

## Repository Structure

### Top-Level Structure

```
n8n-ops-trees/
├── n8n-ops-backend/          # FastAPI backend application
├── n8n-ops-ui/                # React frontend application
├── mvp_readiness_pack/        # This documentation pack
├── scripts/                   # Utility scripts (port management)
└── docs/                      # Root-level documentation
```

### Backend Structure (`n8n-ops-backend/`)

**Evidence:** `n8n-ops-backend/app/` directory structure

```
n8n-ops-backend/
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

### Frontend Structure (`n8n-ops-ui/`)

**Evidence:** `n8n-ops-ui/src/` directory structure

```
n8n-ops-ui/
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

**File:** `n8n-ops-backend/app/main.py`  
**Evidence:** Lines 16-20, 586-588

- **Entrypoint:** `app.main:app` (FastAPI instance)
- **Default Port:** 4000 (via uvicorn.run, line 588)
- **Router Prefix:** `/api/v1` (from `settings.API_V1_PREFIX`, line 18)

### Background Job Runners

**Evidence:** `n8n-ops-backend/app/main.py:startup_event()` (lines 403-451)

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

**Shutdown:** All schedulers stopped in `shutdown_event()` (lines 493-528)

### SSE Entrypoints

**Evidence:** `n8n-ops-backend/app/api/endpoints/sse.py`

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

**File:** `n8n-ops-ui/src/main.tsx`  
**Evidence:** Standard React entrypoint

- **Framework:** React 19.2.0 (from `package.json`)
- **Router:** React Router DOM 7.9.6
- **Build Tool:** Vite 7.2.4

### Key Routes (High-Level)

**Evidence:** `n8n-ops-ui/src/pages/` directory structure

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

**Admin Pages:** `n8n-ops-ui/src/pages/admin/` (39 files)

**Platform Pages:** `n8n-ops-ui/src/pages/platform/` (4 files)

### SSE Hooks

**Evidence:** `n8n-ops-ui/src/lib/`

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

**Evidence:** `n8n-ops-backend/app/core/config.py` (lines 11-13)

- **URL:** `SUPABASE_URL` (from env)
- **Keys:** `SUPABASE_KEY` (anon), `SUPABASE_SERVICE_KEY` (service role)
- **Usage:** 
  - Backend uses `SUPABASE_SERVICE_KEY` (bypasses RLS)
  - Frontend uses `SUPABASE_KEY` (enforces RLS when enabled)
- **Database:** PostgreSQL via Supabase
- **Auth:** JWT-based authentication via Supabase Auth

**RLS Status:** 12 of 76 tables have RLS enabled (15.8%)  
**Evidence:** `n8n-ops-backend/docs/security/RLS_POLICIES.md` (line 5)

### Stripe

**Evidence:** `n8n-ops-backend/app/core/config.py` (lines 46-51)

- **Secret Key:** `STRIPE_SECRET_KEY`
- **Publishable Key:** `STRIPE_PUBLISHABLE_KEY`
- **Webhook Secret:** `STRIPE_WEBHOOK_SECRET`
- **Price IDs:** `STRIPE_PRO_PRICE_ID_MONTHLY`, `STRIPE_PRO_PRICE_ID_YEARLY`
- **Service:** `app/services/stripe_service.py`
- **Webhook Handler:** `app/api/endpoints/billing.py:stripe_webhook()`

### GitHub

**Evidence:** `n8n-ops-backend/app/core/config.py` (lines 18-22)

- **Token:** `GITHUB_TOKEN`
- **Repo:** `GITHUB_REPO_OWNER` / `GITHUB_REPO_NAME`
- **Branch:** `GITHUB_BRANCH` (default: "main")
- **Service:** `app/services/github_service.py`
- **Webhook Handler:** `app/api/endpoints/github_webhooks.py`

### N8N Provider APIs

**Evidence:** `n8n-ops-backend/app/services/n8n_client.py`

- **Adapter Pattern:** `app/services/adapters/n8n_adapter.py`
- **Provider Registry:** `app/services/provider_registry.py`
- **Multi-Provider Support:** Architecture supports multiple workflow providers

### Notifications

**Evidence:** `n8n-ops-backend/app/services/notification_service.py`

- **Service:** `app/services/notification_service.py`
- **Email:** SMTP via `app/services/email_service.py`
- **Config:** `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` (lines 54-58 in config.py)

## API Router Registration

**Evidence:** `n8n-ops-backend/app/main.py` (lines 94-380)

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

**Evidence:** `n8n-ops-backend/app/main.py`

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

**Evidence:** `n8n-ops-backend/app/main.py:startup_event()` (lines 410-487)

- **Stale Job Cleanup:** `background_job_service.cleanup_stale_jobs(max_runtime_hours=24)` (line 412)
- **Stale Deployment Cleanup:** Marks `RUNNING` deployments >1hr old as `FAILED` (lines 454-487)
