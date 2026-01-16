# N8N Ops Platform

Multi-tenant workflow governance platform for managing n8n workflows across environments (dev, staging, production).

## Testing Requirements (MANDATORY)

**IMPORTANT: Always test changes before telling the user to test them.**

Before reporting that a change is complete or asking the user to test:

1. **Backend changes**: Run `pytest` or relevant test file to verify no regressions
2. **Frontend changes**: Run `npm run build` to catch TypeScript/compilation errors
3. **API changes**: Use `curl` or test the endpoint directly to verify it works
4. **Full-stack changes**: Verify both backend and frontend compile/pass tests

If tests fail, fix the issues before reporting completion. Do not hand off broken code to the user.

## Server Restart Policy (MANDATORY)

**When changes require a server restart, ASK the user to restart:**

### Changes That Require Backend Restart:
- Installing new Python packages (`pip install`)
- Changes to `requirements.txt`
- Changes to `.env` files
- Changes to `app/main.py` router registration
- Database migration changes (though migrations auto-run on start)

### Changes That Require Frontend Restart:
- Installing new npm packages (`npm install`)
- Changes to `vite.config.ts`
- Changes to `package.json` scripts
- Changes to `.env` files

### Changes That DO NOT Require Restart (Hot-Reload):
- Backend: `.py` file changes, route modifications, schema updates
- Frontend: `.tsx`, `.ts`, `.css` file changes, component updates

**Format:** "This change requires a [backend/frontend] restart to take effect. Please restart the [backend/frontend] server when convenient."

## ADR Enforcement (MANDATORY)

**Before making architectural, pattern, or tooling decisions, check `/docs/adr/` for existing ADRs.**

### Rules
1. **If an ADR exists** for the topic, follow it without deviation
2. **If no ADR exists** and making a non-trivial decision, create a new ADR in `/docs/adr/` before proceeding
3. **Never contradict** an accepted ADR unless explicitly told to supersede it
4. **Use existing format** from `/docs/adr/` when creating new ADRs (see ADR-007 for full template)

### ADR Categories to Check
- Error handling and validation patterns
- Retry strategies and resilience
- Authentication/authorization patterns
- API design patterns
- State management approaches
- Credential and secrets handling
- Technology and library choices
- Naming conventions
- Component/node preferences
- Git and sync behavior

### Non-Trivial Decisions Requiring ADR
- Introducing new error handling patterns
- Changing retry/backoff strategies
- Adding new external integrations
- Modifying authentication flows
- Establishing new naming conventions
- Choosing between architectural approaches

### Decision Capture
After implementing any of the following, ask: **"Should I document this as an ADR in /docs/adr/?"**
- Choosing between multiple valid approaches
- Introducing a new library, tool, or dependency
- Establishing a pattern that should be consistent across the codebase
- Deviating from a common convention (and why)
- Setting up error handling, retry logic, or fallback behavior
- Defining API contracts or data structures
- Making trade-offs (performance vs readability, flexibility vs simplicity, etc.)

If yes, create the ADR immediately. If no, continue without documenting.

## Port Configuration

| Worktree | Frontend | Backend |
|----------|----------|---------|
| main     | 3000     | 4000    |
| f1       | 3001     | 4001    |
| f2       | 3002     | 4002    |
| f3       | 3003     | 4003    |
| f4       | 3004     | 4004    |

Port configuration is in `.env.local` (root) and should not be modified without user approval.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend: React + TanStack Query + Zustand + shadcn/ui         │
│  app-front/ (port 3000)                                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST API (axios)
┌──────────────────────────▼──────────────────────────────────────┐
│  Backend: FastAPI + Pydantic + httpx                            │
│  app-back/ (port 4000)                                   │
└──────┬─────────────────────┬─────────────────────┬──────────────┘
       │                     │                     │
┌──────▼──────┐    ┌─────────▼─────────┐   ┌──────▼──────┐
│  Supabase   │    │  N8N Instances    │   │   GitHub    │
│  PostgreSQL │    │  REST API         │   │   Repos     │
└─────────────┘    └───────────────────┘   └─────────────┘
```

## Key Features

- **Environments**: Manage multiple N8N instances (dev/staging/prod) with environment classes
- **Workflows**: View, upload, sync, activate/deactivate workflows with action policies
- **Credentials**: View and manage N8N credentials across environments
- **Executions**: Monitor workflow execution history
- **GitHub Sync**: Backup/restore workflows to Git repositories
- **Pipelines**: Define promotion flows between environments
- **Promotions**: Move workflows with gates, approvals, drift detection
- **Drift Detection**: Automated drift monitoring, incidents, and reconciliation
- **Drift Policies**: TTL/SLA-based governance with enterprise controls
- **Drift Reports**: Comprehensive drift reporting and history tracking
- **Drift Retention**: Configurable retention policies for drift data
- **Incident Management**: Lifecycle tracking for drift incidents (open/acknowledged/resolved)
- **Environment Capabilities**: Policy-based action guards per environment class
- **Snapshots**: Git-backed environment state versioning
- **Restore**: Restore workflows from snapshots
- **Deployments**: Track promotion history, scheduling, and rollback
- **Observability**: Health monitoring, alerts, execution analytics
- **Alerts**: Configurable alerting for workflow failures
- **Team Management**: Role-based access (admin, developer, viewer)
- **Billing**: Stripe integration with free/pro/enterprise tiers
- **Support**: Ticket system for user assistance
- **Entitlements**: Plan-based feature access with overrides
- **Admin Portal**: 16 admin pages for system management
- **Real-time Updates**: SSE-based live notifications
- **Canonical Workflows**: Repository-based workflow management with environment synchronization
- **Background Jobs**: Async task execution with progress tracking
- **Live Log Streaming**: SSE-based real-time log streaming for sync/backup/restore operations
- **Health Monitoring**: Automated health checks with heartbeat tracking for environments
- **Service Recovery**: Automatic detection and handling of backend connectivity issues
- **Bulk Operations**: Batch sync, backup, and restore across multiple environments
- **Git-Based Promotions**: Target-ownership snapshot system for DEV→STAGING→PROD workflow promotion
- **Workflow Matrix**: Cross-environment workflow status overview
- **Execution Analytics**: Advanced execution metrics and performance insights
- **Credential Health**: Monitoring and tracking of credential status across environments
- **Promotion Validation**: Pre-promotion validation with rollback state tracking

## Dev Mode Authentication

Auth0 is disabled for local development:
- Auto-login as first user in database
- Falls back to dummy dev user if no users exist
- Endpoints: `/api/v1/auth/dev/users`, `/api/v1/auth/dev/login-as/{id}`

## Project Structure

```
n8n-ops/
├── CLAUDE.md                    # This file (overview)
├── .env.local                   # Port configuration
├── app-back/             # FastAPI backend
│   ├── CLAUDE.md                # Backend-specific docs
│   ├── app/
│   │   ├── main.py              # App entry, router registration
│   │   ├── api/endpoints/       # 51 API routers
│   │   ├── services/            # 63 business logic services
│   │   ├── schemas/             # 28 Pydantic model files
│   │   └── core/                # Config, feature gates
│   ├── alembic/                 # Alembic migrations
│   ├── migrations/              # SQL migrations
│   └── tests/                   # 74 pytest test files
├── app-front/                  # React frontend
│   ├── CLAUDE.md                # Frontend-specific docs
│   └── src/
│       ├── pages/               # 66+ pages (core + support + admin)
│       ├── components/          # UI, workflow, pipeline components
│       ├── hooks/               # Custom React hooks
│       ├── lib/                 # API client, auth, features
│       ├── store/               # Zustand state
│       └── types/               # TypeScript definitions
└── docs/                        # Additional documentation
```

## API Conventions

- **Base URL**: `http://localhost:<BACKEND_PORT>/api/v1`
- **Auth Header**: `Authorization: Bearer <token>`
- **Multi-tenant**: All queries filtered by `tenant_id`
- **Errors**: `{ "detail": "Error message" }`

## Environment Files

| File | Purpose |
|------|---------|
| `.env.local` | Port configuration (root) |
| `app-back/.env` | Backend secrets (Supabase, Stripe, GitHub) |
| `app-front/.env` | Frontend config (`VITE_API_BASE_URL`) |

## Adding New Features

### Backend
1. Create schema in `app/schemas/`
2. Add endpoint in `app/api/endpoints/`
3. Register router in `app/main.py`
4. Add DB methods in `app/services/database.py`
5. Write tests in `tests/`

### Frontend
1. Add API method in `src/lib/api-client.ts`
2. Create page in `src/pages/`
3. Add route in `src/App.tsx`
4. Add nav item in `src/components/AppLayout.tsx`
5. Add types in `src/types/index.ts`

## Common Commands

```bash
# Backend testing
cd app-back && pytest                    # All tests
cd app-back && pytest tests/test_file.py # Specific test

# Frontend testing
cd app-front && npm test                       # Run tests
cd app-front && npm test -- --coverage         # With coverage
cd app-front && npm run build                  # Type check & build
cd app-front && npm run lint                   # Lint check
```

## Resources

- Backend docs: `app-back/CLAUDE.md`
- Frontend docs: `app-front/CLAUDE.md`
- API docs: `http://localhost:4000/docs`
- [FastAPI](https://fastapi.tiangolo.com/) | [N8N API](https://docs.n8n.io/api/) | [Supabase](https://supabase.com/docs) | [TanStack Query](https://tanstack.com/query) | [shadcn/ui](https://ui.shadcn.com/)
