# N8N Ops – Admin / Superuser Functional Spec

This document defines the **Admin → Superuser** functionality for the N8N Ops platform. It assumes:

- Auth0 for authentication and tenant-scoped authorization
- Stripe for billing (Free / Pro / Agency / Enterprise plans)
- Supabase (or equivalent) for Postgres
- Feature flags and plan-based entitlements are already implemented
- Observability (metrics, logs, alerts) is already baked in

The goal: give the platform superuser a single place to manage **tenants, users, plans, billing, usage, and system settings**.

---

## Current Implementation Status

### Already Implemented

| Component | Route | Status | Notes |
|-----------|-------|--------|-------|
| **Tenant List** | `/admin/tenants` | Partial | Basic CRUD exists, missing filters/pagination/MRR |
| **Feature Matrix** | `/admin/feature-matrix` | Complete | Edit plan-feature values with audit logging |
| **Tenant Overrides** | `/admin/tenant-overrides` | Complete | Create/edit/delete per-tenant feature overrides |
| **Entitlements Audit** | `/admin/entitlements-audit` | Partial | Page exists, needs enhancement |
| **Audit Logs** | `/admin/audit-logs` | Mock Only | UI exists with hardcoded sample data |
| **System Billing** | `/admin/billing` | Mock Only | UI exists with hardcoded revenue metrics |
| **Settings** | `/admin/settings` | Mock Only | General/Database/Email settings, all simulated |

### Not Yet Implemented

| Component | Route | Priority |
|-----------|-------|----------|
| **Tenant Detail Page** | `/admin/tenants/:tenantId` | Phase 1 |
| **Plans Management UI** | `/admin/plans` | Phase 1 |
| **Real Stripe Integration** | Various | Phase 1 |
| **Real Audit Logs Backend** | `/admin/audit-logs` | Phase 1 |
| **Usage & Limits** | `/admin/usage`, per-tenant | Phase 2 |
| **Auth0 Settings Tab** | `/admin/settings/auth` | Phase 2 |
| **Stripe Settings Tab** | `/admin/settings/payments` | Phase 2 |

---

## 1. Roles and Scope

### 1.1 Roles

- **End User** – normal user within a tenant; no access to Admin menu.
- **Tenant Admin** – manages users and settings within their own tenant.
- **Superuser (Platform Admin)** – global admin with access to the Admin menu.

### 1.2 Superuser Capabilities

Superuser can:

- View and manage **all tenants**
- View and adjust **plans, billing, and usage**
- Configure **global system settings** (Auth0, Stripe, email)
- View **audit logs** and perform sensitive operations (suspend tenant, etc.)

Superuser actions must be fully audited.

---

## 2. Admin Navigation Structure

Under the main **Admin** menu in N8N Ops, the following sections exist (visible only to superusers):

**Current Routes (in `AppLayout.tsx`):**
1. `/admin/tenants` - Tenants
2. `/admin/billing` - System Billing
3. `/admin/feature-matrix` - Feature Matrix
4. `/admin/tenant-overrides` - Tenant Overrides
5. `/admin/entitlements-audit` - Entitlements Audit
6. `/admin/audit-logs` - Audit Logs
7. `/admin/settings` - Settings

**Proposed Final Structure:**
1. **Tenants** (`/admin/tenants`)
2. **Plans & Billing** (`/admin/plans`, `/admin/billing`)
3. **Usage & Limits** (`/admin/usage`)
4. **System Settings** (`/admin/settings` with tabs)
5. **Audit Logs** (`/admin/audit-logs`)
6. **Entitlements** (existing: Feature Matrix, Tenant Overrides, Entitlements Audit)

---

## 3. Tenants

### 3.1 Tenants List (Enhance Existing)

**Route:** `/admin/tenants`

**Current State:** Basic list with search, stats cards, CRUD dialogs. Uses real data via `apiClient.getTenants()`.

**File:** `n8n-ops-ui/src/pages/admin/TenantsPage.tsx`

**Current Columns:**
- Tenant (Name + Email)
- Plan (badge)
- Status (badge)
- Workflows count
- Environments count
- Users count
- Created date
- Actions dropdown

**Enhancements Needed:**

1. **Additional Filters:**
   - Plan dropdown (All / Free / Pro / Agency / Enterprise)
   - Status dropdown (All / Active / Trial / Suspended / Cancelled / Archived)
   - Created date range picker (from date / to date)

2. **Additional Columns:**
   - Tenant ID (slug/identifier, monospace)
   - MRR (Monthly Recurring Revenue) - requires Stripe integration
   - Primary Contact (currently shows email in tenant column)

3. **Pagination:**
   - Current: No pagination (loads all tenants)
   - Needed: Paginated table (25/50/100 per page)
   - Backend: Add `page` and `page_size` params to `GET /api/v1/tenants`

4. **Click to Detail:**
   - Current: No tenant detail page
   - Needed: Click tenant name → navigate to `/admin/tenants/:tenantId`

**Backend Changes Required:**
```python
# In app/api/endpoints/tenants.py
@router.get("/", response_model=TenantListResponse)
async def get_tenants(
    search: Optional[str] = Query(None),
    plan: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    created_from: Optional[datetime] = Query(None),
    created_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    ...
```

### 3.2 Tenant Detail Page (NEW)

**Route:** `/admin/tenants/:tenantId`

**Purpose:** Comprehensive tenant management with all relevant information and actions in tabbed interface.

**File to Create:** `n8n-ops-ui/src/pages/admin/TenantDetailPage.tsx`

**Layout:** Tabs at top, content area below. Each tab contains relevant sections and actions.

#### 3.2.1 Overview Tab

**Purpose:** Basic tenant information and lifecycle management actions.

**Display Sections:**

- **Tenant Information Card:**
  - Tenant name (editable text field with save button)
  - Tenant ID / slug (read-only, displayed as monospace code)
  - Status badge (dropdown to change status: Active / Trial / Suspended / Cancelled / Archived)
  - Created at (read-only, formatted)
  - Last active timestamp (read-only, formatted, with "Never" if no activity)

- **Contact Information Card:**
  - Primary contact name (editable)
  - Primary contact email (editable)
  - Contact email validation required

**Action Buttons (in prominent action area):**

- **Suspend Tenant:**
  - Opens confirmation dialog explaining what suspension means (soft lock access, preserve data)
  - Changes status to "Suspended"
  - Logged in audit log

- **Reactivate Tenant:**
  - Only visible when status is Suspended
  - Changes status back to "Active"
  - Logged in audit log

- **Cancel Tenant:**
  - Opens confirmation dialog with warning about subscription cancellation
  - Cancels Stripe subscription (via API)
  - Changes tenant status to "Cancelled"
  - Logged in audit log

- **Schedule Deletion:**
  - Opens dialog with:
    - Retention period selector (30 / 60 / 90 days)
    - Planned deletion date display (calculated from selected period)
    - Warning message about data loss
  - Creates scheduled deletion record
  - Status changes to "Archived" (or similar)
  - Logged in audit log

- **Export Tenant Data:**
  - Button that initiates export job
  - Shows progress indicator
  - When complete, provides download link or S3 link
  - Export should include all tenant data (workflows, users, environments, execution history, etc.)

**Backend Changes Required:**
- Add `status` column to tenants table if not present (currently simulated)
- Add `scheduled_deletion_at` column
- Create `POST /api/v1/tenants/{tenant_id}/suspend`
- Create `POST /api/v1/tenants/{tenant_id}/reactivate`
- Create `POST /api/v1/tenants/{tenant_id}/schedule-deletion`
- Create `POST /api/v1/tenants/{tenant_id}/export`

#### 3.2.2 Users & Roles Tab

**Purpose:** Manage users within the tenant, including roles and access control.

**Data Source:** Combined data from Auth0 and local user table (`users` table in database).

**Current Backend:** `GET /api/v1/teams` returns team members for a tenant.

**Display Table Columns:**

- Name (full name from Auth0/local)
- Email (primary identifier)
- Role (Tenant Admin / Member / Read-only, etc.) - editable dropdown per row
- Status (Active / Invited / Disabled) - badge with color coding
- Last login (formatted timestamp, "Never" if no login)
- Actions (dropdown menu per row)

**Per-Row Actions Menu:**

- **Promote to Admin / Demote from Admin:**
  - Changes role in both Auth0 and local database
  - Confirmation required for demotion
  - Logged in audit log

- **Disable User / Re-enable User:**
  - Disables in Auth0 (blocks login)
  - Updates status in local database
  - Confirmation required for disable action
  - Logged in audit log

- **Resend Invite:**
  - Sends invitation email to user
  - Only available if status is "Invited"
  - Shows success/error notification

- **Force Logout / Revoke Sessions:**
  - Revokes all Auth0 sessions for user
  - User must re-authenticate
  - Confirmation required
  - Logged in audit log

- **Open in Auth0:**
  - Opens new tab to Auth0 dashboard with user pre-selected
  - Deep link format: `https://[domain].auth0.com/users/[user_id]`

**Backend Changes Required:**
- Add `auth0_id` to users table (if not present) for Auth0 deep linking
- Create `POST /api/v1/teams/{member_id}/disable`
- Create `POST /api/v1/teams/{member_id}/revoke-sessions`

#### 3.2.3 Plan & Features Tab

**Purpose:** View and manage tenant's plan, billing cycle, trial status, and feature overrides.

**Leverage Existing:** Link to Feature Matrix and Tenant Overrides pages that already exist.

**Display Sections:**

- **Plan Summary Card:**
  - Current plan name (large, prominent)
  - Billing interval (Monthly / Annual) - badge
  - Trial status indicator (if applicable):
    - "Trial active until [date]"
    - "Trial expired on [date]"
    - "No trial"
  - Plan change dropdown (select new plan with confirmation)

- **Plan-Based Features Section:**
  - Table or card layout showing features from plan
  - Feature name, type (flag/limit), current value
  - Derived from plan's feature profile (use existing `entitlements_service`)
  - Read-only display (plan features come from plan definition)

- **Tenant Overrides Section:**
  - List of per-tenant feature overrides
  - Display format: Feature name → Override value → Reason → Actions
  - Example rows:
    - `feature.n8n_backups` → Enabled (override) → "Beta program" → [Edit] [Remove]
    - `limit.max_workflows` → 200 (override) → "Enterprise agreement" → [Edit] [Remove]
  - "Add Override" button opens dialog
  - "Manage All Overrides" link → `/admin/tenant-overrides` (pre-filtered to this tenant)

**Existing APIs to Use:**
- `GET /api/v1/tenants/{tenant_id}/overrides` - already exists
- `POST/PATCH/DELETE /api/v1/tenants/{tenant_id}/overrides` - already exist

**Action Buttons:**

- **Change Plan:**
  - Dropdown with available plans
  - Confirmation dialog showing:
    - Current plan → New plan
    - Proration information
    - Impact on features
  - Updates Stripe subscription (via API)
  - Updates tenant plan assignment
  - Logged in audit log

- **Manage Trial:**
  - Button opens trial management dialog
  - Options:
    - Start trial (if no active trial)
    - Extend trial (add days)
    - Cancel trial (end immediately)
  - Updates Stripe subscription trial dates
  - Logged in audit log

#### 3.2.4 Billing Tab

**Purpose:** Complete billing and subscription management for the tenant.

See Section 4.2 for detailed requirements. This tab should display all billing information and actions.

**Key Elements:**
- Subscription summary with Stripe links
- Invoice history with download links
- Payment method display
- Subscription management actions (cancel, change interval, etc.)

**Existing Backend (needs tenant context):**
- `GET /api/v1/billing/subscription` - currently uses mock TENANT_ID
- `GET /api/v1/billing/invoices` - currently uses mock TENANT_ID
- These need to be modified to accept `tenant_id` parameter for admin use

#### 3.2.5 Usage Tab

**Purpose:** View tenant's current usage versus plan limits.

See Section 5.1 for detailed requirements.

**Key Elements:**
- Metrics cards (workflows, executions, API calls, seats, storage)
- Current value vs plan limit for each metric
- Percentage usage indicators with color coding (green/yellow/red)
- Override management links

#### 3.2.6 Notes Tab

**Purpose:** Internal notes and history about the tenant (never visible to tenant users).

**Display:**

- **Timeline View:** Chronological list of notes (newest first)
  - Each note shows:
    - Date and time
    - Author (superuser name/email)
    - Note content (freeform text, supports multi-line)
    - Delete button (only for note author or superuser)

- **Add Note Section:**
  - Text area for note input
  - "Add Note" button
  - Character limit (e.g., 2000 characters)
  - Auto-save draft (optional)

**Backend Changes Required:**
- Create `tenant_notes` table
- Create CRUD endpoints for tenant notes

---

## 4. Plans & Billing

### 4.1 Plans Management (NEW)

**Route:** `/admin/plans`

**Purpose:** Create, edit, and manage subscription plans and their Stripe mappings.

**Current State:** Plans exist in database (queried via admin_entitlements endpoints) but there's no dedicated admin UI for managing them. The Feature Matrix page shows plans but doesn't allow plan-level management.

**File to Create:** `n8n-ops-ui/src/pages/admin/PlansPage.tsx`

**List View Table:**

**Columns:**
- Plan name (Free / Pro / Agency / Enterprise)
- Display name (user-facing name)
- Internal plan ID (UUID)
- Stripe Product ID (with copy button)
- Stripe Price IDs (Monthly / Annual as separate columns, with copy buttons)
- Status badge (Active / Deprecated)
- Base price display (Monthly price, Annual price)
- Tenant count (how many tenants on this plan)
- Actions column (Edit, Deprecate/Reactivate)

**Existing Backend:**
- `GET /api/v1/admin/entitlements/plans` - returns plans with tenant counts

**Backend Changes Required:**
- Add Stripe IDs to plans table or create `plan_stripe_mappings` table
- Create `POST /api/v1/admin/plans` for creating new plans
- Create `PATCH /api/v1/admin/plans/{plan_id}` for updating plans
- Create `POST /api/v1/admin/plans/{plan_id}/deprecate`

### 4.2 Tenant Billing (Per-Tenant Subscription)

**Route:** `/admin/tenants/:tenantId/billing` (also accessible as tab in tenant detail)

**Purpose:** Complete view of tenant's subscription, invoices, and payment information with management actions.

**Current State:** Billing endpoints exist (`/api/v1/billing/*`) but use hardcoded mock `TENANT_ID`. Need to add admin-mode endpoints that accept `tenant_id` parameter.

**Display Sections:**

- **Subscription Summary Card:**
  - Current plan name and billing interval (Monthly/Annual)
  - Subscription status badge with color:
    - Active (green)
    - Trialing (blue)
    - Past Due (yellow)
    - Cancelled (red)
    - Incomplete (orange)
  - Trial information (if applicable):
    - "Trial ends on [date]"
    - Days remaining display
  - Stripe Customer ID (with copy button and deep link)
  - Stripe Subscription ID (with copy button and deep link)
  - Deep links format: `https://dashboard.stripe.com/customers/[customer_id]`

- **Invoices Table:**
  - Columns: Date, Invoice #, Amount, Status, Actions
  - Status badges: Paid, Open, Void, Uncollectible
  - Amount displayed with currency symbol
  - "View" action opens Stripe-hosted invoice in new tab
  - "Download PDF" action (if available from Stripe)
  - Paginated table
  - Sort by date (newest first)

- **Payment Method Card:**
  - Card brand icon (Visa, Mastercard, etc.)
  - Last 4 digits of card
  - Expiry date (MM/YY format)
  - Read-only display (cannot edit in admin UI)
  - Note: "Update payment method in Stripe customer portal"
  - Link to open Stripe customer portal

**Existing Backend Services:**
- `app/services/stripe_service.py` - has methods for customer, subscription, invoices

**Backend Changes Required:**
- Create admin billing endpoints that accept `tenant_id`:
  - `GET /api/v1/admin/tenants/{tenant_id}/subscription`
  - `GET /api/v1/admin/tenants/{tenant_id}/invoices`
  - `POST /api/v1/admin/tenants/{tenant_id}/subscription/change-plan`
  - `POST /api/v1/admin/tenants/{tenant_id}/subscription/cancel`
  - `POST /api/v1/admin/tenants/{tenant_id}/trial/extend`

### 4.3 Global Billing Dashboard (Enhance Existing)

**Route:** `/admin/billing`

**Purpose:** System-wide view of revenue, subscriptions, and billing health.

**Current State:** UI exists but uses hardcoded mock data in `SystemBillingPage.tsx`.

**File:** `n8n-ops-ui/src/pages/admin/SystemBillingPage.tsx`

**Current Mock Data (needs real Stripe integration):**
```typescript
const revenueMetrics: RevenueMetric[] = [
  { label: 'Monthly Recurring Revenue', value: '$12,450', ... },
  { label: 'Annual Recurring Revenue', value: '$149,400', ... },
  ...
];

const recentTransactions: Transaction[] = [
  { id: '1', tenant: 'Acme Corp', type: 'subscription', ... },
  ...
];
```

**Backend Changes Required:**
- Create `GET /api/v1/admin/billing/metrics` returning:
  - MRR, ARR (calculated from Stripe subscriptions)
  - New subscriptions (last 30 days)
  - Churned subscriptions (last 30 days)
  - Active paying tenants count
  - Active trials count
- Create `GET /api/v1/admin/billing/recent-charges` returning recent successful payments
- Create `GET /api/v1/admin/billing/failed-payments` returning recent failures
- Create `GET /api/v1/admin/billing/dunning` returning tenants in dunning state

---

## 5. Usage & Limits

### 5.1 Tenant Usage View (NEW)

**Route:** `/admin/tenants/:tenantId/usage` (also accessible as tab in tenant detail)

**Purpose:** View tenant's current usage metrics compared to plan limits.

**File to Create:** Part of `TenantDetailPage.tsx` (Usage tab)

**Display Format:**

**Metrics Cards Grid (2-3 columns):**

Each metric displayed as a card with:
- Metric name (e.g., "Workflows", "Executions", "API Calls")
- Icon or visual indicator
- Large current value number
- Plan limit (with "Unlimited" if -1 or very high)
- Progress bar showing % usage
- Color coding:
  - Green: 0-75% usage
  - Yellow: 75-90% usage
  - Red: 90%+ usage or over limit
- Warning indicator if over limit

**Metrics to Display:**

1. **Workflows:**
   - Current: Count of active workflows (not deleted)
   - Limit: From plan entitlements
   - % Usage: Current / Limit

2. **Executions:**
   - Current: Executions in current period (day/month, configurable)
   - Limit: From plan (if applicable)
   - Period selector: "Today", "This Month", "Last Month"

3. **Seats (Users):**
   - Current: Active user count
   - Limit: From plan
   - % Usage: Current / Limit

4. **Environments:**
   - Current: Environment count
   - Limit: From plan
   - % Usage: Current / Limit

**Existing Data Sources:**
- Workflow count: `GET /api/v1/tenants/{tenant_id}` returns `workflow_count`
- Environment count: Already returned
- User count: Already returned
- Limits: Use `entitlements_service.get_tenant_entitlements(tenant_id)`

**Backend Changes Required:**
- Create `GET /api/v1/admin/tenants/{tenant_id}/usage` returning aggregated usage data
- Add execution counting per tenant

### 5.2 Global Usage Overview (NEW)

**Route:** `/admin/usage`

**Purpose:** Identify heavy users, usage trends, and upsell opportunities.

**File to Create:** `n8n-ops-ui/src/pages/admin/UsagePage.tsx`

**Display Sections:**

- **Top Tenants Tables (Tabs or Accordion):**
  - **By Executions:** Rank, Tenant, Plan, Executions (period), % of total, Trend
  - **By Workflows:** Rank, Tenant, Plan, Workflow count, Trend
  - **By Seats:** Rank, Tenant, Plan, User count, Limit, % usage

- **Tenants Near or Over Limits Section:**
  - Table of tenants approaching or exceeding limits
  - Columns: Tenant, Plan, Metric, Current, Limit, % Usage, Status
  - Status badges: "At Limit", "Over Limit", "Near Limit" (90%+)
  - Actions: "View tenant", "Recommend upgrade"

---

## 6. System Settings

**Route:** `/admin/settings`

**Current State:** Basic settings page exists with General, Database, Email sections. All use mock data.

**File:** `n8n-ops-ui/src/pages/admin/SettingsPage.tsx`

### 6.1 General Settings Tab (Enhance Existing)

**Current Implementation:** Exists with app name, URL, support email, timezone, maintenance mode.

**Changes Needed:** Connect to real backend settings storage.

### 6.2 Auth Settings Tab (NEW)

**Route:** `/admin/settings/auth` (new tab in settings page)

**Purpose:** View and manage Auth0 configuration.

**Display Sections:**

- **Auth0 Connection Information:**
  - Auth0 domain (read-only, displayed)
  - Auth0 client ID (masked, e.g., `abc123...xyz789`, with show/hide toggle)
  - Connection status indicator (Connected / Disconnected)
  - Last synced timestamp

- **Auth0 URLs Configuration:**
  - Allowed callback URLs (read-only list)
  - Allowed logout URLs (read-only list)
  - Note: "To modify URLs, update in Auth0 dashboard"

**Actions:**

- **Open Auth0 Dashboard:** Button opens Auth0 Management Dashboard in new tab
- **Test Connection:** Button to test Auth0 API connectivity
- **Refresh Configuration:** Button to fetch latest Auth0 configuration

### 6.3 Stripe Settings Tab (NEW)

**Route:** `/admin/settings/payments` (new tab in settings page)

**Purpose:** View and manage Stripe configuration and test webhook connectivity.

**Display Sections:**

- **Stripe Mode:**
  - Large badge showing "Test Mode" or "Live Mode"
  - Warning banner when in test mode

- **Stripe Keys:**
  - Stripe Publishable Key (masked, with copy button)
  - Stripe Secret Key (masked, with show/hide toggle)
  - Note: "Keys are stored securely. Contact system administrator to change."

- **Webhook Configuration:**
  - Webhook endpoint URL (read-only, displayed with copy button)
  - Webhook signing secret (masked, with show/hide toggle)
  - Last webhook received timestamp
  - Webhook status indicator (Active / Inactive / Error)

**Actions:**

- **Test Webhook:** Button sends test webhook event from Stripe
- **Open Stripe Dashboard:** Button opens Stripe Dashboard in new tab
- **Refresh Webhook Status:** Button checks webhook endpoint health

### 6.4 Email / Notifications Tab (Enhance Existing)

**Current:** Email configuration exists in general settings with SMTP settings.

**Changes Needed:**
- Add email provider selection (SendGrid / AWS SES / Other)
- Add API key validation
- Connect "Send Test Email" to real backend

---

## 7. Audit Logs (Enhance Existing)

**Route:** `/admin/audit-logs`

**Current State:** UI exists with mock data in `AuditLogsPage.tsx`.

**File:** `n8n-ops-ui/src/pages/admin/AuditLogsPage.tsx`

**Current Mock Implementation:**
```typescript
const mockAuditLogs: AuditLog[] = [
  {
    id: '1',
    timestamp: '2024-03-15T14:32:00Z',
    user: 'John Doe',
    userEmail: 'john@acme.com',
    tenant: 'Acme Corp',
    action: 'workflow.create',
    ...
  },
  ...
];
```

**Backend Requirements:**

Create comprehensive audit logging system:

**Database Table:**
```sql
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  actor_id UUID REFERENCES users(id),
  actor_email TEXT,
  actor_name TEXT,
  tenant_id UUID REFERENCES tenants(id),
  tenant_name TEXT,
  action TEXT NOT NULL,
  action_type TEXT NOT NULL, -- TENANT_CREATED, USER_DISABLED, etc.
  resource_type TEXT,
  resource_id TEXT,
  resource_name TEXT,
  old_value JSONB,
  new_value JSONB,
  reason TEXT,
  ip_address TEXT,
  user_agent TEXT,
  metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_logs_tenant_id ON audit_logs(tenant_id);
CREATE INDEX idx_audit_logs_action_type ON audit_logs(action_type);
CREATE INDEX idx_audit_logs_actor_id ON audit_logs(actor_id);
```

**API Endpoints:**
```python
# GET /api/v1/admin/audit-logs
@router.get("/audit-logs")
async def get_audit_logs(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    actor_id: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    ...
```

**Action Types to Log:**
- TENANT_CREATED, TENANT_UPDATED, TENANT_SUSPENDED, TENANT_REACTIVATED
- TENANT_CANCELLED, TENANT_DELETION_SCHEDULED
- TENANT_PLAN_CHANGED
- USER_ROLE_CHANGED, USER_DISABLED, USER_ENABLED
- FEATURE_OVERRIDE_ADDED, FEATURE_OVERRIDE_REMOVED
- PLAN_CREATED, PLAN_UPDATED
- SUBSCRIPTION_CANCELLED
- TRIAL_STARTED, TRIAL_EXTENDED
- SETTINGS_UPDATED

**Note:** Partial audit logging exists in `feature_config_audit` table for entitlements changes. This needs to be expanded to cover all admin actions.

---

## 8. Non-Functional Requirements

### 8.1 Authorization

- Admin menu and all routes under `/admin` are restricted to superuser role.
- Tenant admins never see global admin sections.
- Role checks should be enforced at both frontend (menu visibility) and backend (API endpoints).

**Current Implementation:**
- Frontend: `RoleProtectedRoute` component in `App.tsx`
- Backend: Needs `require_superuser` decorator for admin endpoints

### 8.2 Auditability

- Any change to tenants, plans, billing adjustments, feature overrides, or system settings must be written to audit logs.
- Audit logs should capture:
  - Who performed the action (superuser)
  - When it was performed (timestamp)
  - What action was performed (action type)
  - What entity was affected (tenant, user, plan, etc.)
  - What changed (old value, new value)
  - Why it changed (notes/reason, if provided)

### 8.3 Safety

- Destructive actions must require confirmation:
  - Cancel subscription
  - Suspend tenant
  - Schedule deletion
  - Delete user
  - Force logout
- Confirmation dialogs should clearly explain consequences.

### 8.4 Data Security

- Never expose sensitive data in UI:
  - Full API keys or secrets (always mask)
  - Credit card numbers (never stored or displayed)
  - Passwords (never displayed)
- Use deep links to external providers (Auth0, Stripe) rather than embedding sensitive data.

### 8.5 Performance

- Large lists (tenants, audit logs, invoices) should be paginated.
- Consider caching for frequently accessed data (plan details, feature matrix).
- Background jobs for heavy operations (data export, usage aggregation).

---

## 9. Phased Delivery Plan

### Phase 1 — Core (Ship first)

**Scope:**
- Tenant Detail Page with all tabs (Overview, Users & Roles, Plan & Features, Billing, Usage, Notes)
- Plans Management UI
- Stripe integration (per-tenant billing + global billing) replacing all mock data
- Real Audit Logs backend + UI filters

**Files to Create/Modify:**

| File | Action | Description |
|------|--------|-------------|
| `TenantDetailPage.tsx` | Create | New page with tabbed interface |
| `PlansPage.tsx` | Create | Plans management UI |
| `TenantsPage.tsx` | Modify | Add click-through to detail, filters, pagination |
| `SystemBillingPage.tsx` | Modify | Replace mock data with real API calls |
| `AuditLogsPage.tsx` | Modify | Replace mock data with real API calls |
| `tenants.py` | Modify | Add pagination, filters, new endpoints |
| `admin_billing.py` | Create | New billing admin endpoints |
| `audit_logs.py` | Create | New audit log endpoints |

**Success Criteria:**
- All admin routes gated to superuser; data loads from real APIs/DB
- Plan changes and trials flow through Stripe; audit logs written for every admin action
- Tenant detail tabs fully navigable and functional (CRUD where defined)

### Phase 2 — Visibility & Control

**Scope:**
- Usage & Limits views (tenant + global) with percent-of-limit visuals and upgrade prompts
- Enhanced System Settings tabs (Auth0, Stripe, Email/Notifications) with deep links and masking
- Enhanced Tenants List (filters for plan/status/date, MRR column, clickable to detail)

**Files to Create/Modify:**

| File | Action | Description |
|------|--------|-------------|
| `UsagePage.tsx` | Create | Global usage overview |
| `SettingsPage.tsx` | Modify | Add Auth0, Stripe tabs |
| `TenantsPage.tsx` | Modify | Add advanced filters, MRR column |

**Success Criteria:**
- Usage data sourced from real metrics; limits shown vs plan
- Settings surfaces live config readouts with test actions
- Tenant list filtering and navigation improve admin workflow

### Phase 3 — Polish & Analytics

**Scope:**
- CSV exports (tenants, audit logs, billing tables, usage tables)
- Advanced filtering/search across tables (e.g., action-type presets, dunning filters)
- Historical usage charts/graphs (optional if data available)

**Success Criteria:**
- Exports respect active filters
- Tables support richer search without regressions to perf
- Charts accurately reflect stored history where present

---

## 10. Integration Points

### Existing Systems to Leverage

- **Feature Matrix System:** Implemented at `/admin/feature-matrix` - use for plan features display
- **Tenant Overrides System:** Implemented at `/admin/tenant-overrides` - link from tenant detail Plan & Features tab
- **Entitlements Service:** `app/services/entitlements_service.py` - use for calculating effective entitlements
- **Stripe Service:** `app/services/stripe_service.py` - extend for admin billing actions
- **Auth Service:** `app/services/auth_service.py` - extend for user management actions
- **Audit Service:** `app/services/audit_service.py` - extend for comprehensive audit logging

### External Services

- **Stripe API:** For subscription management, invoices, payment methods, webhooks
- **Auth0 API:** For user management, session revocation, user lookups
- **Database:** Supabase/Postgres for tenant, user, plan, audit log storage

### API Client Methods to Add

```typescript
// In src/lib/api-client.ts

// Tenant Detail
getTenantById(tenantId: string): Promise<Tenant>
suspendTenant(tenantId: string): Promise<void>
reactivateTenant(tenantId: string): Promise<void>
scheduleTenantDeletion(tenantId: string, retentionDays: number): Promise<void>
exportTenantData(tenantId: string): Promise<{ jobId: string }>

// Tenant Billing (Admin)
getAdminTenantSubscription(tenantId: string): Promise<Subscription>
getAdminTenantInvoices(tenantId: string): Promise<Invoice[]>
changeAdminTenantPlan(tenantId: string, planId: string): Promise<void>
extendAdminTenantTrial(tenantId: string, days: number): Promise<void>

// Plans Management
getPlans(): Promise<Plan[]>
createPlan(plan: PlanCreate): Promise<Plan>
updatePlan(planId: string, plan: PlanUpdate): Promise<Plan>
deprecatePlan(planId: string): Promise<void>

// Global Billing
getBillingMetrics(): Promise<BillingMetrics>
getRecentCharges(): Promise<Charge[]>
getFailedPayments(): Promise<FailedPayment[]>
getDunningTenants(): Promise<DunningTenant[]>

// Audit Logs
getAuditLogs(params: AuditLogParams): Promise<AuditLogResponse>

// Usage
getTenantUsage(tenantId: string): Promise<TenantUsage>
getGlobalUsage(): Promise<GlobalUsage>
getTopTenants(metric: string): Promise<TopTenant[]>
```

---

This spec should be implemented as the **Admin / Superuser** area within N8N Ops, leveraging the existing routing, layout, and RBAC patterns already in the app.
