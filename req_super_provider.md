# Admin/Superuser Provider-Aware Requirements

## Goal
Ensure all Admin/Superuser features remain correct and future-proof when multiple workflow providers exist (currently defaulting to `n8n`), without changing the user-facing flow.

---

## 1. Scope of Impact

### 1.1 Provider-Scoped Entities (Require `provider` column)

Per `req_provider_abstraction.md`, these entities are tied to a specific workflow provider and admin views must respect provider context:

| Entity | Admin Context | Notes |
|--------|---------------|-------|
| `environments` | Tenant Detail → Usage, Global Usage | Each environment belongs to one provider |
| `workflows` | Tenant Detail → Usage, Global Usage | Workflow counts must be provider-filtered |
| `executions` | Tenant Detail → Usage, Global Usage | Execution metrics scoped by provider |
| `credentials` | Not surfaced in admin UI | Provider-scoped but not admin-visible |
| `deployments` | Not surfaced in admin UI | Provider-scoped |
| `snapshots` | Not surfaced in admin UI | Provider-scoped |
| `pipelines` | Not surfaced in admin UI | Provider-scoped |
| `promotions` | Not surfaced in admin UI | Provider-scoped |
| `tags` | Not surfaced in admin UI | Provider-scoped |
| `provider_users` | Tenant Detail → Users tab (future) | n8n instance users, not platform users |
| `health_checks` | Tenant Detail → Usage (future) | Environment health is provider-specific |

### 1.2 Platform-Scoped Entities (NO `provider` column)

These remain provider-agnostic per `req_provider_abstraction.md`:

| Entity | Admin Context | Notes |
|--------|---------------|-------|
| `tenants` | Tenants List, Tenant Detail | Organization-level, spans all providers |
| `users` | Tenant Detail → Users & Roles | Platform users, not provider instance users |
| `plans` | Plans Management | Billing plans are provider-agnostic |
| `subscriptions` | Billing | Stripe subscriptions, provider-agnostic |
| `tenant_overrides` | Tenant Overrides | Feature overrides may reference provider-scoped features |
| `feature_config` | Feature Matrix | Feature definitions, provider-agnostic |
| `git_configs` | Not admin-visible | Tenant-level git configuration |
| `tenant_notes` | Tenant Detail → Notes | Internal notes, provider-agnostic |

### 1.3 Audit Logs (Special Case)

The `audit_logs` table is platform-scoped but must **record provider context** for actions on provider-scoped entities:

```sql
-- Per req_admin_superuser.md audit_logs table
-- Add provider column for context (nullable, only set for provider-scoped actions)
ALTER TABLE audit_logs ADD COLUMN provider TEXT;
```

---

## 2. Admin Pages: Provider Behavior Matrix

Cross-reference with `req_admin_superuser.md` pages:

### 2.1 Pages That Need Provider Awareness

| Page | Route | Provider Behavior |
|------|-------|-------------------|
| **Tenant Detail → Usage Tab** | `/admin/tenants/:id` (Usage tab) | Show provider filter when multi-provider; metrics grouped/filtered by provider |
| **Global Usage** | `/admin/usage` | Provider filter on all tables (Top by Executions, Top by Workflows, Near Limits) |
| **Audit Logs** | `/admin/audit-logs` | Provider filter; show provider column in results for provider-scoped actions |

### 2.2 Pages That Remain Provider-Agnostic

| Page | Route | Rationale |
|------|-------|-----------|
| **Tenants List** | `/admin/tenants` | Tenants span providers; counts shown are aggregates (with optional breakdown) |
| **Tenant Detail → Overview** | `/admin/tenants/:id` | Tenant metadata is provider-agnostic |
| **Tenant Detail → Users & Roles** | `/admin/tenants/:id` | Platform users, not provider users |
| **Tenant Detail → Plan & Features** | `/admin/tenants/:id` | Plans are provider-agnostic; overrides may have provider context |
| **Tenant Detail → Billing** | `/admin/tenants/:id` | Stripe subscription is provider-agnostic |
| **Tenant Detail → Notes** | `/admin/tenants/:id` | Internal notes, no provider scope |
| **Plans Management** | `/admin/plans` | Plans apply across providers |
| **System Billing** | `/admin/billing` | Revenue metrics are provider-agnostic (subscription-based) |
| **Feature Matrix** | `/admin/feature-matrix` | Feature definitions are provider-agnostic |
| **Tenant Overrides** | `/admin/tenant-overrides` | Overrides are provider-agnostic (features may be provider-specific) |
| **Settings** | `/admin/settings` | System settings are provider-agnostic |

---

## 3. API Endpoint Specifications

### 3.1 Endpoints Requiring `provider` Query Parameter

These endpoints must accept an optional `provider` query parameter:

```python
# Tenant Usage (per-tenant metrics)
GET /api/v1/admin/tenants/{tenant_id}/usage
    ?provider=n8n          # Filter to specific provider
    ?provider=all          # Aggregate across providers (default)

# Global Usage
GET /api/v1/admin/usage/top-tenants
    ?metric=executions|workflows|seats
    ?provider=n8n|make|all

GET /api/v1/admin/usage/near-limits
    ?provider=n8n|make|all

# Audit Logs
GET /api/v1/admin/audit-logs
    ?provider=n8n|make|all  # Filter by provider context
    # Other existing filters: start_date, end_date, actor_id, action_type, tenant_id
```

### 3.2 Endpoints Returning `provider` in Response

These endpoints must include `provider` field in response objects:

```python
# Tenant Usage Response
{
    "tenant_id": "uuid",
    "provider": "n8n",  # or "all" if aggregated
    "metrics": {
        "workflows": { "current": 45, "limit": 100 },
        "executions": { "current": 1250, "limit": 5000 },
        "environments": { "current": 3, "limit": 5 }
    },
    # When provider=all, include breakdown:
    "by_provider": {
        "n8n": { "workflows": 45, "executions": 1250, "environments": 3 },
        "make": { "workflows": 12, "executions": 500, "environments": 1 }
    }
}

# Audit Log Entry
{
    "id": "uuid",
    "timestamp": "2024-03-15T14:32:00Z",
    "actor_email": "admin@example.com",
    "tenant_name": "Acme Corp",
    "action": "workflow.delete",
    "resource_type": "workflow",
    "resource_id": "wf-123",
    "provider": "n8n",  # NULL for platform-scoped actions
    ...
}

# Global Usage - Top Tenants Response
{
    "metric": "executions",
    "provider": "n8n",  # or "all"
    "period": "last_30_days",
    "tenants": [
        {
            "tenant_id": "uuid",
            "tenant_name": "Acme Corp",
            "plan": "pro",
            "value": 15000,
            "provider": "n8n"  # Included when provider=all
        }
    ]
}
```

### 3.3 Endpoints That Stay Provider-Agnostic

No changes needed for:

```python
# Tenants CRUD
GET/POST/PATCH/DELETE /api/v1/tenants

# Tenant lifecycle actions
POST /api/v1/tenants/{tenant_id}/suspend
POST /api/v1/tenants/{tenant_id}/reactivate
POST /api/v1/tenants/{tenant_id}/schedule-deletion
POST /api/v1/tenants/{tenant_id}/export

# Plans management
GET/POST/PATCH /api/v1/admin/plans

# Billing
GET /api/v1/admin/billing/metrics
GET /api/v1/admin/tenants/{tenant_id}/subscription
GET /api/v1/admin/tenants/{tenant_id}/invoices

# Feature overrides
GET/POST/PATCH/DELETE /api/v1/tenants/{tenant_id}/overrides

# Team management
GET /api/v1/teams
POST /api/v1/teams/{member_id}/disable
```

---

## 4. UI/UX Specifications

### 4.1 Provider Visibility Rules

```typescript
// Pseudo-code for provider UI visibility
const showProviderControls = activeProviders.length > 1;

// If only n8n is active, hide all provider UI elements
// If multiple providers active, show filters and badges
```

### 4.2 Tenant Detail → Usage Tab

**Single Provider Mode:**
- Show metrics cards (Workflows, Executions, Seats, Environments) without provider labels
- No provider dropdown

**Multi-Provider Mode:**
- Add provider filter dropdown at top: `[All Providers ▼]` | `[n8n]` | `[Make]`
- Default: "All Providers"
- When filter = "All":
  - Show aggregate metrics
  - Add provider badge to each metric card showing breakdown
  - Example: "Workflows: 57 total (n8n: 45, Make: 12)"
- When filter = specific provider:
  - Show only that provider's metrics
  - Add subtle provider badge to header

### 4.3 Global Usage Page (`/admin/usage`)

**Single Provider Mode:**
- Show tables without provider column
- No provider filter

**Multi-Provider Mode:**
- Add provider filter dropdown at page level: `[All Providers ▼]`
- **Top Tenants by Executions table:**
  - Add "Provider" column when filter = "All"
  - Columns: Rank, Tenant, Plan, Provider, Executions, % of Total, Trend
- **Top Tenants by Workflows table:**
  - Add "Provider" column when filter = "All"
- **Tenants Near/Over Limits table:**
  - Add "Provider" column when filter = "All"
  - Columns: Tenant, Plan, Provider, Metric, Current, Limit, % Usage, Status

### 4.4 Audit Logs Page (`/admin/audit-logs`)

**Single Provider Mode:**
- No provider filter
- No provider column in table

**Multi-Provider Mode:**
- Add provider filter dropdown: `[All Providers ▼]` | `[n8n]` | `[Make]` | `[Platform]`
  - "Platform" = actions on provider-agnostic entities (tenant CRUD, plan changes, etc.)
- Add "Provider" column to table (show "—" for platform-scoped actions)
- Filter logic:
  - "All" = show all entries
  - Specific provider = show entries where `provider = 'n8n'`
  - "Platform" = show entries where `provider IS NULL`

### 4.5 Tenants List Page (`/admin/tenants`)

**Counts Display (both modes):**
- Workflow count, Environment count shown are **aggregates across providers**
- No per-provider breakdown in list view (too noisy)
- Detail is available on Tenant Detail → Usage tab

**Multi-Provider Mode (future consideration):**
- Optionally add tooltip on counts: "45 workflows (n8n: 40, Make: 5)"
- No filter on this page (tenants are provider-agnostic)

---

## 5. Database Schema Additions

### 5.1 Audit Logs Provider Column

```sql
-- Add to audit_logs table (from req_admin_superuser.md)
ALTER TABLE audit_logs ADD COLUMN provider TEXT;

-- Index for provider filtering
CREATE INDEX idx_audit_logs_provider ON audit_logs(provider);
CREATE INDEX idx_audit_logs_provider_timestamp ON audit_logs(provider, timestamp DESC);
```

### 5.2 Usage Aggregation Indexes

```sql
-- Support efficient provider-filtered usage queries
CREATE INDEX idx_workflows_provider_tenant ON workflows(provider, tenant_id);
CREATE INDEX idx_executions_provider_tenant ON executions(provider, tenant_id);
CREATE INDEX idx_environments_provider_tenant ON environments(provider, tenant_id);

-- For global usage "top tenants" queries
CREATE INDEX idx_executions_provider_tenant_created ON executions(provider, tenant_id, created_at DESC);
```

---

## 6. Audit Logging Rules

### 6.1 Actions That Include `provider` Context

Log `provider` field when action affects provider-scoped entity:

| Action Type | Resource Type | Provider Logged |
|-------------|---------------|-----------------|
| `workflow.create` | workflow | Yes |
| `workflow.update` | workflow | Yes |
| `workflow.delete` | workflow | Yes |
| `workflow.activate` | workflow | Yes |
| `workflow.deactivate` | workflow | Yes |
| `environment.create` | environment | Yes |
| `environment.update` | environment | Yes |
| `environment.delete` | environment | Yes |
| `execution.viewed` | execution | Yes |
| `deployment.create` | deployment | Yes |
| `snapshot.create` | snapshot | Yes |
| `health_check.triggered` | health_check | Yes |

### 6.2 Actions That Omit `provider` (NULL)

| Action Type | Resource Type | Rationale |
|-------------|---------------|-----------|
| `tenant.create` | tenant | Platform-scoped |
| `tenant.update` | tenant | Platform-scoped |
| `tenant.suspend` | tenant | Platform-scoped |
| `tenant.reactivate` | tenant | Platform-scoped |
| `tenant.delete_scheduled` | tenant | Platform-scoped |
| `user.role_changed` | user | Platform users |
| `user.disabled` | user | Platform users |
| `plan.changed` | subscription | Provider-agnostic |
| `trial.extended` | subscription | Provider-agnostic |
| `subscription.cancelled` | subscription | Provider-agnostic |
| `override.added` | feature_override | Provider-agnostic |
| `override.removed` | feature_override | Provider-agnostic |
| `settings.updated` | system | Platform-scoped |

---

## 7. Frontend Type Updates

### 7.1 Admin-Specific Types

```typescript
// types/admin.ts

type Provider = "n8n" | "make";
type ProviderFilter = Provider | "all";
type ProviderOrPlatform = Provider | "platform"; // For audit log filtering

// Tenant Usage Response
interface TenantUsage {
  tenantId: string;
  provider: ProviderFilter;
  metrics: UsageMetrics;
  byProvider?: Record<Provider, UsageMetrics>; // Present when provider="all"
}

interface UsageMetrics {
  workflows: UsageMetric;
  executions: UsageMetric;
  environments: UsageMetric;
  seats: UsageMetric;
}

interface UsageMetric {
  current: number;
  limit: number;
  percentUsed: number;
}

// Audit Log Entry
interface AuditLogEntry {
  id: string;
  timestamp: string;
  actorId: string;
  actorEmail: string;
  actorName: string;
  tenantId: string;
  tenantName: string;
  action: string;
  actionType: string;
  resourceType: string;
  resourceId: string;
  resourceName: string;
  provider: Provider | null; // NULL for platform-scoped actions
  oldValue?: Record<string, any>;
  newValue?: Record<string, any>;
  reason?: string;
  ipAddress?: string;
}

// Global Usage - Top Tenant
interface TopTenant {
  tenantId: string;
  tenantName: string;
  plan: string;
  provider?: Provider; // Present when querying "all" providers
  value: number;
  percentOfTotal: number;
  trend: "up" | "down" | "stable";
}
```

### 7.2 API Client Methods

```typescript
// lib/api-client.ts additions

// Tenant Usage (provider-aware)
getTenantUsage(tenantId: string, provider?: ProviderFilter): Promise<TenantUsage>

// Global Usage (provider-aware)
getTopTenants(metric: "executions" | "workflows" | "seats", provider?: ProviderFilter): Promise<TopTenant[]>
getTenantsNearLimits(provider?: ProviderFilter): Promise<TenantLimitStatus[]>

// Audit Logs (provider-aware)
getAuditLogs(params: AuditLogParams & { provider?: ProviderOrPlatform }): Promise<AuditLogResponse>
```

---

## 8. Implementation Phases

Align with `req_admin_superuser.md` phased delivery:

### Phase 1: Core (No Provider UI)

- Add `provider` column to all provider-scoped tables (per `req_provider_abstraction.md`)
- Default all existing data to `provider = 'n8n'`
- Add `provider` column to `audit_logs` table
- Backend endpoints accept `provider` param but default to `'n8n'`
- **No UI changes** - single provider mode only
- Audit logs record provider for provider-scoped actions

### Phase 2: Provider-Aware Admin UI

- Add provider detection: `GET /api/v1/admin/providers/active` returns list of active providers
- Conditionally show provider filters when `activeProviders.length > 1`
- Implement Tenant Usage tab provider filter and breakdown
- Implement Global Usage page provider filter and columns
- Implement Audit Logs provider filter and column

### Phase 3: Multi-Provider Operations

- Support tenant having environments across multiple providers
- Usage aggregation across providers
- Provider-specific health checks and alerts
- Provider comparison views (future)

---

## 9. Non-Functional Requirements

### 9.1 Backward Compatibility
- Single-provider flows unchanged
- All endpoints default `provider='n8n'` when omitted
- Existing API consumers unaffected

### 9.2 Security
- No leakage of provider secrets (API keys, encryption keys)
- Only provider identifiers/labels surface in admin UI
- Provider config stored in `provider_config` JSONB (encrypted at rest)

### 9.3 Performance
- Provider filters must use indexed columns
- Avoid N+1 queries when aggregating across providers
- Consider materialized views for usage aggregation if needed

```sql
-- Example: Pre-aggregated usage per tenant/provider
CREATE MATERIALIZED VIEW tenant_usage_summary AS
SELECT
  tenant_id,
  provider,
  COUNT(DISTINCT w.id) as workflow_count,
  COUNT(DISTINCT e.id) as environment_count,
  (SELECT COUNT(*) FROM executions ex WHERE ex.tenant_id = t.id AND ex.provider = t.provider) as execution_count
FROM tenants t
LEFT JOIN workflows w ON w.tenant_id = t.id
LEFT JOIN environments e ON e.tenant_id = t.id
GROUP BY tenant_id, provider;
```

---

## 10. Success Criteria

### Single Provider Mode
- UX unchanged from current implementation
- No provider controls visible in any admin page
- Audit logs silently record `provider = 'n8n'` for provider-scoped actions

### Multi-Provider Mode
- Admin can filter usage data by provider on Tenant Usage and Global Usage pages
- Admin can filter audit logs by provider
- Metrics accurately reflect provider-scoped counts
- Provider badges/columns appear only when relevant (filter ≠ single provider)

### Data Integrity
- All provider-scoped entities have `provider` column populated
- All admin queries respect provider scope
- Audit entries include provider context for provider-scoped actions
- Aggregations correctly sum across providers when `provider = 'all'`

---

## 11. Open Questions / Decisions Needed

1. **Tenant Overrides**: Should feature overrides be provider-scoped?
   - Current assumption: No (features are plan-level, provider-agnostic)
   - Alternative: Allow `limit.max_workflows.n8n` vs `limit.max_workflows.make`

2. **Usage Limits Enforcement**: Are limits per-provider or aggregate?
   - Current assumption: Aggregate (tenant has 100 workflows total, not 100 per provider)
   - Alternative: Per-provider limits

3. **Provider Discovery**: How do we know which providers a tenant has?
   - Current assumption: Derived from environments table (`SELECT DISTINCT provider FROM environments WHERE tenant_id = ?`)
   - Alternative: Explicit `tenant_providers` junction table

4. **Billing Attribution**: Should revenue be attributed to providers?
   - Current assumption: No (subscription is provider-agnostic)
   - Alternative: Track usage-based billing per provider
