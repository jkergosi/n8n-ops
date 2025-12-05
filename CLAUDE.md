# N8N Ops Platform - Architecture & Developer Guide

## Project Overview

N8N Ops is a multi-tenant workflow governance platform for managing n8n workflows across multiple environments (dev, staging, production). It provides version control, deployment tracking, GitHub integration, and centralized workflow management.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                           │
│  React + TypeScript + Vite + TailwindCSS + shadcn/ui            │
│  • TanStack Query (data fetching/caching)                       │
│  • Zustand (global state)                                       │
│  • React Router (routing)                                       │
└──────────────────────┬──────────────────────────────────────────┘
                       │ REST API (axios)
┌──────────────────────▼──────────────────────────────────────────┐
│                         Backend Layer                            │
│  FastAPI + Python 3.9+ + Pydantic                               │
│  • N8N API Client (httpx)                                       │
│  • GitHub Service (PyGithub)                                    │
│  • Stripe Service (billing)                                     │
│  • Database Service (Supabase client)                           │
└──────┬────────────────────────────────┬─────────────────────────┘
       │                                │
┌──────▼────────┐              ┌────────▼────────┐
│   Supabase    │              │   N8N Instance  │
│  PostgreSQL   │              │   REST API      │
│  (Database)   │              │                 │
└───────────────┘              └─────────────────┘
                                        │
                              ┌─────────▼─────────┐
                              │  GitHub Repository│
                              │  (Version Control)│
                              └───────────────────┘
```

### Technology Stack

#### Frontend (`n8n-ops-ui/`)
- **Framework**: React 19.2.0 + TypeScript
- **Build Tool**: Vite 7.2.4
- **Styling**: TailwindCSS 3.4.18 + shadcn/ui components
- **State Management**:
  - Zustand 5.0.9 (global state)
  - TanStack Query 5.90.11 (server state, caching)
- **Routing**: React Router DOM 7.9.6
- **UI Components**: Radix UI primitives + custom components
- **Validation**: Zod 4.1.13
- **Notifications**: Sonner 2.0.7

#### Backend (`n8n-ops-backend/`)
- **Framework**: FastAPI 0.109.0
- **Runtime**: Python 3.9+
- **ASGI Server**: Uvicorn 0.27.0
- **Database Client**: Supabase 2.9.0 (PostgreSQL)
- **HTTP Client**: httpx 0.27.0 (async)
- **Integrations**:
  - PyGithub 2.1.1 (GitHub API)
  - Stripe 7.9.0 (payments)
  - GitPython 3.1.41 (Git operations)
- **Validation**: Pydantic 2.5.3
- **Auth**: python-jose 3.3.0 + passlib 1.7.4



## Project Structure

```
n8n-ops/
├── n8n-ops-backend/              # FastAPI Backend
│   ├── app/
│   │   ├── main.py               # FastAPI app entry point
│   │   ├── api/
│   │   │   └── endpoints/        # API route handlers
│   │   │       ├── billing.py    # Stripe billing integration
│   │   │       ├── environments.py # Environment management
│   │   │       ├── executions.py # Workflow execution history
│   │   │       ├── n8n_users.py  # N8N user management
│   │   │       ├── tags.py       # Workflow tags
│   │   │       ├── teams.py      # Team member management
│   │   │       └── workflows.py  # Workflow CRUD + sync
│   │   ├── core/
│   │   │   └── config.py         # Settings (Pydantic BaseSettings)
│   │   ├── schemas/              # Pydantic models (request/response)
│   │   │   ├── billing.py
│   │   │   ├── environment.py
│   │   │   ├── execution.py
│   │   │   ├── tag.py
│   │   │   ├── team.py
│   │   │   └── workflow.py
│   │   └── services/             # Business logic
│   │       ├── database.py       # Supabase database operations
│   │       ├── github_service.py # GitHub sync operations
│   │       ├── n8n_client.py     # N8N API client
│   │       └── stripe_service.py # Stripe integration
│   ├── requirements.txt          # Python dependencies
│   └── .env.example              # Environment variables template
│
├── n8n-ops-ui/                   # React Frontend
│   ├── src/
│   │   ├── main.tsx              # React app entry point
│   │   ├── App.tsx               # Route configuration
│   │   ├── components/
│   │   │   ├── AppLayout.tsx     # Main layout with sidebar
│   │   │   ├── ThemeProvider.tsx # Dark/light theme
│   │   │   ├── ThemeToggle.tsx   # Theme switcher
│   │   │   └── ui/               # shadcn/ui components
│   │   │       ├── badge.tsx
│   │   │       ├── button.tsx
│   │   │       ├── card.tsx
│   │   │       ├── dialog.tsx
│   │   │       ├── dropdown-menu.tsx
│   │   │       ├── input.tsx
│   │   │       ├── label.tsx
│   │   │       ├── multi-select.tsx
│   │   │       ├── table.tsx
│   │   │       └── tabs.tsx
│   │   ├── pages/                # Page components
│   │   │   ├── BillingPage.tsx
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── DeploymentsPage.tsx
│   │   │   ├── EnvironmentsPage.tsx
│   │   │   ├── ExecutionsPage.tsx
│   │   │   ├── LoginPage.tsx
│   │   │   ├── N8NUsersPage.tsx
│   │   │   ├── ObservabilityPage.tsx
│   │   │   ├── OnboardingPage.tsx
│   │   │   ├── SnapshotsPage.tsx
│   │   │   ├── TagsPage.tsx
│   │   │   ├── TeamPage.tsx
│   │   │   └── WorkflowsPage.tsx
│   │   ├── lib/
│   │   │   ├── api-client.ts     # Axios API client
│   │   │   ├── api.ts            # API helper functions
│   │   │   ├── auth.tsx          # Auth context/provider
│   │   │   ├── mock-api.ts       # Mock data for development
│   │   │   └── utils.ts          # Utility functions
│   │   ├── store/
│   │   │   └── use-app-store.ts  # Zustand global state
│   │   └── types/
│   │       └── index.ts          # TypeScript type definitions
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── .env.example
│
├── CLAUDE.md                     # This file
├── SETUP_GUIDE.md                # Detailed setup instructions
├── TODO.md                       # Current task list
└── [Feature Documentation]/      # Additional setup guides
```

## Key Files & Their Responsibilities

### Backend

#### `app/main.py`
FastAPI application entry point. Configures CORS, registers all API routers, provides health check endpoints.

#### `app/core/config.py`
Configuration management using Pydantic Settings. Loads environment variables for:
- N8N instance credentials
- Supabase database connection
- GitHub integration
- Stripe billing
- JWT authentication

#### `app/api/endpoints/environments.py` (604 lines)
Environment management endpoints:
- CRUD operations for N8N environments
- Connection testing (N8N + GitHub)
- Full sync (workflows, executions, credentials, users, tags)
- Individual sync endpoints for each resource type

Key endpoints:
- `GET /api/v1/environments` - List all environments
- `POST /api/v1/environments` - Create environment
- `POST /api/v1/environments/test-connection` - Test N8N connection
- `POST /api/v1/environments/{id}/sync` - Full sync from N8N
- `POST /api/v1/environments/{id}/sync-users` - Sync users only

#### `app/api/endpoints/workflows.py` (895 lines)
Workflow management endpoints:
- Fetch workflows from N8N API (with caching)
- Upload workflows (JSON/ZIP files)
- Activate/deactivate workflows
- Delete workflows
- GitHub sync (bidirectional)
- Download all workflows as ZIP

Key endpoints:
- `GET /api/v1/workflows?environment=dev&force_refresh=false`
- `POST /api/v1/workflows/upload` - Upload JSON/ZIP files
- `POST /api/v1/workflows/sync-to-github` - Backup to GitHub
- `POST /api/v1/workflows/sync-from-github` - Import from GitHub
- `GET /api/v1/workflows/download?environment_id={id}` - Download as ZIP
- `DELETE /api/v1/workflows/{id}?environment=dev`

#### `app/services/n8n_client.py` (220 lines)
HTTP client for N8N REST API. Key methods:
- `get_workflows()` - Fetch all workflows
- `get_workflow(id)` - Fetch single workflow
- `create_workflow(data)` - Create new workflow
- `update_workflow(id, data)` - Update workflow (carefully filters fields)
- `delete_workflow(id)` - Delete workflow
- `activate_workflow(id)` / `deactivate_workflow(id)` - Toggle active state
- `update_workflow_tags(id, tag_ids)` - Assign tags
- `get_executions()` - Fetch execution history
- `get_credentials()` - Fetch credential metadata
- `get_users()` - Fetch N8N users
- `get_tags()` - Fetch available tags
- `test_connection()` - Health check

#### `app/services/database.py`
Supabase database client. Provides async methods for:
- Environments CRUD
- Workflow snapshots (versioning)
- Deployments tracking
- Team member management
- Billing/subscription data
- Sync operations (upsert workflows from N8N)

#### `app/services/github_service.py`
GitHub integration using PyGithub:
- `sync_workflow_to_github()` - Push workflow JSON to repo
- `get_all_workflows_from_github()` - Pull all workflows from repo
- Uses `workflows/` directory in repository
- Supports custom branches

### Frontend

#### `src/main.tsx`
React app entry point. Renders the App component.

#### `src/App.tsx` (111 lines)
Application router and providers:
- QueryClientProvider (TanStack Query)
- AuthProvider (authentication context)
- ThemeProvider (dark/light mode)
- Protected routes with onboarding check
- Route definitions for all pages

#### `src/lib/api-client.ts` (453 lines)
Axios-based API client with typed methods for all endpoints:
- Automatic auth token injection (request interceptor)
- Error handling with 401 redirect (response interceptor)
- Snake_case to camelCase transformation
- Methods for all API endpoints (environments, workflows, billing, teams, etc.)

Example:
```typescript
await apiClient.getWorkflows('dev', forceRefresh);
await apiClient.uploadWorkflows(files, 'dev', syncToGithub);
await apiClient.syncEnvironment(environmentId);
```

#### `src/store/use-app-store.ts` (29 lines)
Zustand global state store:
- `selectedEnvironment` - Current environment filter
- `sidebarOpen` - Sidebar visibility
- `theme` - Light/dark theme preference

#### `src/pages/WorkflowsPage.tsx`
Workflow management UI:
- Environment selector dropdown
- Search by name/description
- Filter by tags
- Sort all columns
- Upload workflows (JSON/ZIP)
- Edit in N8N (opens new window)
- Delete workflows
- Activate/deactivate toggle

#### `src/pages/EnvironmentsPage.tsx`
Environment management UI:
- List all environments (dev, staging, production)
- Add/Edit/Delete environments
- Test N8N connection
- Test GitHub connection
- Sync from N8N (full or incremental)
- Backup to GitHub
- Download workflows as ZIP
- Display workflow count (clickable → filters WorkflowsPage)

## Database Schema (Supabase PostgreSQL)

### Core Tables

#### `tenants`
Multi-tenant isolation. Each organization gets a tenant record.
- `id` (UUID, primary key)
- `name` (text)
- `email` (text, unique)
- `subscription_plan` (enum: free, pro, enterprise)
- `created_at`, `updated_at` (timestamp)

#### `environments`
N8N instance configurations.
- `id` (UUID, primary key)
- `tenant_id` (UUID, foreign key → tenants)
- `name` (text)
- `type` (enum: dev, staging, production)
- `base_url` (text) - N8N instance URL
- `api_key` (text) - N8N API key
- `is_active` (boolean)
- `workflow_count` (integer) - Cached count
- `last_connected` (timestamp)
- `git_repo_url`, `git_branch`, `git_pat` (text) - GitHub config
- `created_at`, `updated_at` (timestamp)

#### `workflows`
Cached workflow data from N8N.
- `id` (UUID, primary key)
- `tenant_id` (UUID, foreign key)
- `environment_id` (UUID, foreign key)
- `n8n_workflow_id` (text) - ID from N8N
- `name` (text)
- `active` (boolean)
- `tags` (text[])
- `workflow_data` (JSONB) - Full workflow definition
- `last_synced_at` (timestamp)
- `created_at`, `updated_at` (timestamp)

#### `workflow_snapshots`
Version history for workflows before deployments.
- `id` (UUID, primary key)
- `tenant_id` (UUID, foreign key)
- `workflow_id` (text)
- `workflow_name` (text)
- `version` (integer)
- `data` (JSONB) - Workflow definition at this version
- `trigger` (text) - What triggered snapshot (manual, deployment, etc.)
- `created_at` (timestamp)

#### `deployments`
Deployment tracking across environments.
- `id` (UUID, primary key)
- `tenant_id` (UUID, foreign key)
- `workflow_id` (text)
- `source_environment` (text)
- `target_environment` (text)
- `status` (enum: pending, running, success, failed)
- `error_message` (text)
- `deployed_by` (UUID, foreign key → users)
- `created_at`, `updated_at` (timestamp)

#### `users`
Team members with role-based access.
- `id` (UUID, primary key)
- `tenant_id` (UUID, foreign key)
- `email` (text, unique)
- `name` (text)
- `role` (enum: admin, developer, viewer)
- `created_at`, `updated_at` (timestamp)

## API Conventions

### Endpoint Patterns

```
/api/v1/{resource}              # List all
/api/v1/{resource}/{id}         # Get/Update/Delete specific
/api/v1/{resource}/test-*       # Test operations
/api/v1/{resource}/{id}/sync    # Sync operations
```

### Request/Response Format

All endpoints return JSON. Error responses include:
```json
{
  "detail": "Error message here"
}
```

Success responses vary by endpoint but typically:
```json
{
  "success": true,
  "data": { ... }
}
```

### Query Parameters

- `environment` - Environment type (dev, staging, production)
- `environment_id` - Environment UUID
- `force_refresh` - Skip cache, fetch fresh data (boolean)
- `limit` - Pagination limit (integer)

### Authentication

- Token stored in `localStorage.getItem('auth_token')`
- Sent as `Authorization: Bearer {token}` header
- 401 responses redirect to `/login`

### Multi-Tenancy

- All requests filtered by `tenant_id`
- Currently using mock tenant ID: `00000000-0000-0000-0000-000000000000`
- TODO: Replace with actual authenticated user's tenant ID

## Coding Conventions

### Backend (Python)

#### File Naming
- `snake_case.py` for all files
- Services end with `_service.py` or `_client.py`

#### Code Style
- FastAPI route handlers are async
- Type hints on all function signatures
- Pydantic models for request/response validation
- HTTPException for error handling

Example:
```python
@router.get("/", response_model=List[EnvironmentResponse])
async def get_environments():
    """Get all environments for the current tenant"""
    try:
        environments = await db_service.get_environments(MOCK_TENANT_ID)
        return environments
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch environments: {str(e)}"
        )
```

#### Error Handling
- Catch specific exceptions first
- Re-raise HTTPException from dependencies
- Wrap unknown errors in 500 response
- Include descriptive error messages

#### Database Operations
- All database calls through `db_service`
- Use async methods
- Return dicts (not Pydantic models) from database layer

### Frontend (TypeScript/React)

#### File Naming
- `PascalCase.tsx` for components
- `kebab-case.ts` for utilities
- `camelCase.ts` for non-component TypeScript files

#### Component Structure
- Functional components with hooks
- Props typed with TypeScript interfaces
- Use TanStack Query for data fetching
- Use Zustand for global state
- Use React Context for scoped state (auth, theme)

Example:
```typescript
export function WorkflowsPage() {
  const { selectedEnvironment } = useAppStore();
  const { data: workflows, isLoading } = useQuery({
    queryKey: ['workflows', selectedEnvironment],
    queryFn: () => apiClient.getWorkflows(selectedEnvironment),
  });

  if (isLoading) return <div>Loading...</div>;

  return (
    <div className="space-y-6">
      {/* Component content */}
    </div>
  );
}
```

#### State Management
- **Server state**: TanStack Query (caching, refetching, background updates)
- **Global UI state**: Zustand (sidebar, theme, selected environment)
- **Local component state**: React useState
- **Form state**: Controlled components with useState or React Hook Form

#### Styling
- TailwindCSS utility classes
- shadcn/ui components for UI primitives
- Custom components in `components/ui/`
- Responsive design with Tailwind breakpoints

Example:
```tsx
<div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
  {environments.map((env) => (
    <Card key={env.id}>
      <CardHeader>
        <CardTitle>{env.name}</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Content */}
      </CardContent>
    </Card>
  ))}
</div>
```

## Build & Development

### Backend Setup

1. **Install dependencies**:
   ```bash
   cd n8n-ops-backend
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Run development server**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

4. **Access API**:
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - OpenAPI: http://localhost:8000/api/v1/openapi.json

### Frontend Setup

1. **Install dependencies**:
   ```bash
   cd n8n-ops-ui
   npm install
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env:
   # VITE_API_BASE_URL=http://localhost:8000
   # VITE_USE_MOCK_API=false
   ```

3. **Run development server**:
   ```bash
   npm run dev
   ```

4. **Access app**:
   - UI: http://localhost:5173

5. **Build for production**:
   ```bash
   npm run build
   # Output in dist/
   ```

6. **Lint code**:
   ```bash
   npm run lint
   ```

### Environment Variables

#### Backend (`.env`)
```env
# N8N Configuration
N8N_API_URL=https://your-n8n-instance.com
N8N_API_KEY=your-api-key

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.your-project.supabase.co:5432/postgres

# GitHub (optional)
GITHUB_TOKEN=your-github-token
GITHUB_REPO_OWNER=your-org
GITHUB_REPO_NAME=your-repo
GITHUB_BRANCH=main

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Stripe (optional)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID_MONTHLY=price_...
STRIPE_PRO_PRICE_ID_YEARLY=price_...
```

#### Frontend (`.env`)
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_USE_MOCK_API=false
```

## Testing

### Current Status
- No automated tests implemented yet
- Manual testing through Swagger UI (http://localhost:8000/docs)
- Frontend testing via browser

### Recommended Testing Strategy

#### Backend
- Unit tests: pytest for service layer
- Integration tests: TestClient for API endpoints
- Example:
  ```python
  from fastapi.testclient import TestClient
  from app.main import app

  client = TestClient(app)

  def test_get_environments():
      response = client.get("/api/v1/environments")
      assert response.status_code == 200
  ```

#### Frontend
- Unit tests: Vitest + React Testing Library
- E2E tests: Playwright or Cypress
- Component tests: Storybook (optional)

## Common Workflows

### Adding a New Feature

1. **Backend**:
   - Create Pydantic schema in `app/schemas/`
   - Add endpoint in `app/api/endpoints/`
   - Register router in `app/main.py`
   - Add database methods in `app/services/database.py`

2. **Frontend**:
   - Add API method in `src/lib/api-client.ts`
   - Create page/component in `src/pages/` or `src/components/`
   - Add route in `src/App.tsx`
   - Add navigation item in `src/components/AppLayout.tsx`

### Syncing Workflows

1. **From N8N to Database**:
   - User clicks "Sync" on EnvironmentsPage
   - Frontend calls `POST /api/v1/environments/{id}/sync`
   - Backend fetches from N8N API
   - Backend upserts to `workflows` table
   - Frontend refreshes workflow list

2. **To GitHub**:
   - User clicks "Backup" on EnvironmentsPage
   - Frontend calls `POST /api/v1/workflows/sync-to-github`
   - Backend fetches workflows from N8N
   - Backend pushes JSON files to GitHub repo
   - Updates `last_backup` timestamp

3. **From GitHub**:
   - User triggers sync from GitHub
   - Frontend calls `POST /api/v1/workflows/sync-from-github`
   - Backend pulls JSON files from GitHub
   - Backend creates/updates workflows in N8N
   - Frontend refreshes workflow list

### Uploading Workflows

1. User selects JSON/ZIP files in WorkflowsPage
2. Frontend calls `POST /api/v1/workflows/upload`
3. Backend processes each file:
   - Parses JSON
   - Creates workflow in N8N
   - Creates snapshot in database
   - Optionally syncs to GitHub
4. Frontend displays success/error summary

## Troubleshooting

### Backend Issues

**Connection to N8N fails**:
- Verify `N8N_API_URL` is correct and accessible
- Check `N8N_API_KEY` is valid
- Test connection: `POST /api/v1/environments/test-connection`

**Database errors**:
- Verify Supabase credentials in `.env`
- Check database tables exist (run SQL setup script)
- Ensure `SUPABASE_SERVICE_KEY` has correct permissions

**GitHub sync fails**:
- Verify `GITHUB_TOKEN` has repo write access
- Check repository and branch exist
- Ensure repository URL format: `https://github.com/owner/repo`

### Frontend Issues

**API calls fail**:
- Ensure backend is running on port 8000
- Check `VITE_API_BASE_URL` in `.env`
- Open browser DevTools → Network tab for detailed errors

**Uploads not working**:
- Only works in dev environment (by design)
- Check file format (must be .json or .zip)
- Verify N8N instance is accessible

**Stale data**:
- Click "Sync" to force refresh from N8N
- Check `force_refresh` parameter in API calls
- TanStack Query caches data for 5 minutes (configurable in `App.tsx`)

## Security Considerations

### Current Implementation
- Mock authentication (any credentials accepted)
- No JWT validation
- API keys stored in plaintext (environment variables)
- No rate limiting
- CORS allows all origins in development

### Production Recommendations
1. **Authentication**:
   - Implement Supabase Auth or Auth0
   - Validate JWT tokens on all endpoints
   - Store tokens securely (httpOnly cookies)

2. **API Keys**:
   - Encrypt N8N API keys in database
   - Use environment-specific credentials
   - Rotate keys regularly

3. **Rate Limiting**:
   - Add slowapi or similar middleware
   - Limit requests per user/tenant

4. **CORS**:
   - Restrict to production domains only
   - Use environment-specific CORS origins

5. **Input Validation**:
   - Already using Pydantic for request validation
   - Add additional business logic validation

6. **GitHub Tokens**:
   - Use OAuth apps instead of personal access tokens
   - Store encrypted in database

## Future Enhancements

### Planned Features
1. **Authentication**: Supabase Auth integration
2. **Snapshots**: UI for workflow version history
3. **Deployments**: Promote workflows between environments
4. **Observability**: Execution monitoring and alerts
5. **Scheduled Backups**: Cron jobs for Pro users
6. **Workflow Comparison**: Diff between environments
7. **Role-Based Permissions**: Enforce user roles
8. **Audit Logs**: Track all user actions
9. **Webhook Support**: N8N → N8N Ops event notifications
10. **Multi-Region**: Support for geographically distributed N8N instances

### Technical Debt
- Replace mock authentication with real auth
- Add comprehensive test coverage
- Implement proper error logging (Sentry)
- Add database migrations (Alembic)
- Optimize database queries (add indexes)
- Implement pagination for large datasets
- Add WebSocket support for real-time updates

## Resources

### Documentation
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [N8N API Docs](https://docs.n8n.io/api/)
- [Supabase Docs](https://supabase.com/docs)
- [TanStack Query](https://tanstack.com/query/latest)
- [shadcn/ui](https://ui.shadcn.com/)

### Project Files
- `SETUP_GUIDE.md` - Detailed setup instructions
- `TODO.md` - Current task list
- `BILLING_AND_TEAMS_SETUP.md` - Billing feature documentation
- `SYNC_FEATURE_SETUP.md` - Sync feature documentation
- `USER_SYNC_FEATURE_SETUP.md` - User sync documentation

## Contact & Support

For issues or questions:
- Check browser console for frontend errors
- Check backend logs for API errors
- Review Swagger docs at http://localhost:8000/docs
- Verify environment variables are set correctly
