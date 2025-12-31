# workflowspageupdate.md — Workflows Page Refactor (Governance-First, Environment-Aware)

## Objective
Refactor the Workflows page so it becomes an **inventory + navigation** surface with **environment-aware** and **plan-aware** action gating. Reduce casual mutation (Edit/Delete) that bypasses Git and deployments, especially in production. Align workflow changes with the two canonical paths:
- **Normal path:** Deployments (Git → deploy → environment)
- **Exception path:** Drift Incident (incident workflow with reconciliation)

This update must:
- Prevent accidental production changes
- Reduce drift caused by inline edits/deletes
- Keep dev iteration unblocked (within reason)
- Preserve clear UX: “view here, change elsewhere”
- Be implementable iteratively

---

## Guiding Principles (Non-Negotiable)
1. **Workflows page is read-first**
   - Inventory, status, navigation, and drill-down.
2. **Mutations require intent**
   - Editing/deleting workflows should not be a casual inline action, especially in staging/prod.
3. **Environment-aware affordances**
   - Dev allows more direct actions; production is locked down.
4. **Plan- and role-aware gating**
   - Enforcement and incident handling deepen with higher tiers.
5. **Drift is handled in Drift Incident workspace**
   - No “drift fixing” logic scattered across the Workflows page.

---

## Current-State Assessment (Required Before Changes)
### Inventory existing behavior
- What “Edit” does today (does it edit in n8n, in Git, or in WorkflowOps?)
- What “Delete” does today (soft delete vs hard delete in n8n vs Git delete)
- What “Upload Workflow” does today (destination, validation, auditability)
- What “Refresh from n8n” does today (scope, caching, rate limits)
- How “Sync Status” is calculated at workflow level
- Which endpoints/jobs are triggered by each action

**Exit criteria:** You can describe the exact state changes for Edit/Delete/Upload/Refresh and whether they create drift.

---

## Target Behavior (High-Level)
The Workflows page becomes:
- A searchable list of workflows in a selected environment
- A read-only status surface with controlled entry points into:
  - Workflow details
  - Deployments (normal changes)
  - Drift Incidents (exception handling)

Inline mutation is removed or heavily gated based on environment, role, and plan.

---

## UI / Interaction Changes

### 1) Replace Inline Edit/Delete With a Single “Actions” Menu
**Change**
- Replace per-row buttons:
  - Edit
  - Delete
- With one control:
  - `Actions ▾`

**Why**
- Reduces visual noise
- Allows environment/plan gating without clutter
- Prevents “accidental click” destructive actions

---

### 2) Environment-Aware Action Policy (Core Matrix)
This is the default policy. Enterprise can override via org policy.

#### Allowed Actions by Environment Type
| Action | Dev | Staging | Production |
|---|---:|---:|---:|
| View details | ✅ | ✅ | ✅ |
| Open in n8n | ✅ | ✅ | ✅ |
| Create Deployment | ✅ | ✅ | ✅ |
| Edit directly (creates drift) | ✅ (warn) | ⚠️ (admin + confirm) | ❌ |
| Delete directly | ⚠️ (soft-delete only) | ❌ (route) | ❌ |
| Create Drift Incident | ⚠️ (if drift) | ✅ (if drift) | ✅ (if drift) |

Legend:
- ✅ allowed
- ⚠️ allowed with explicit confirmation + logging
- ❌ not shown / not allowed (server-enforced)

**Rules**
- Production NEVER shows direct Edit/Delete on the Workflows list.
- Staging avoids direct Delete and gates Edit heavily.
- Dev can allow Edit/Delete but must warn that it creates drift.

---

### 3) Plan-Based Gating (Orthogonal Layer)
#### Free
- Drift detection/visibility only (no incident workflow)
- Dev: allow direct edit/delete (warn + record) if you want low-friction adoption
- Prod: block direct edit/delete

#### Pro
- Enable Drift Incident creation (limited scope)
- Dev: direct edit allowed with warning
- Staging: gated edit
- Prod: no direct edits

#### Agency+
- Drift Incident management is first-class
- Default policies stricter:
  - No direct edits/deletes in prod
  - Stronger warnings in staging
  - “Create Deployment” promoted over “Edit”

#### Enterprise
- Org policy controls everything
- Can disable even dev direct edits
- Approvals can be required for drift acceptance

---

## Top-of-Page Controls (Header Actions)

### Current
- “Refresh from n8n”
- “Upload Workflow”

### Recommended
1. **Refresh from n8n**
   - Keep, but reframe as read-only refresh:
     - “Refresh inventory”
   - Gate by role if it triggers heavy jobs
   - Show last refresh time

2. **Upload Workflow**
   - Rename to reflect governance:
     - `Create Deployment` (preferred)
   - If “Upload” remains:
     - Dev-only by default
     - In staging/prod, route to Deployments:
       - “Uploads to staging/prod require a deployment”

**Goal:** Stop “Upload” from becoming an ungoverned change path.

---

## Columns / Data Presentation Changes

### 1) Keep “Sync Status” But Rename for Clarity
Current: “Sync Status”
Recommended: **“Git Status”** or **“Drift Status”** (read-only)

States:
- In Sync
- Drift Detected (link to create/view incident where allowed)
- Unknown (needs refresh)

**Rule:** No mutating actions from this column. Only navigation.

---

### 2) Add “Managed By” (Optional, High Value)
Add a small indicator per workflow:
- `Git`
- `Manual`
- `Unknown`

This helps agencies identify client-managed workflows quickly.

---

## Workflow Row Actions (Actions Menu Spec)

### Always available (all envs)
- View details
- Open in n8n

### Governance path
- Create Deployment (pre-filled with workflow selection)

### Incident path (only when drift exists and plan allows)
- View Drift Incident
- Create Drift Incident (if drift detected but no active incident)

### Direct mutation (dev/staging only per policy)
- Edit directly (warn + record)
- Archive / Soft delete (dev only; prefer soft-delete)

### Remove entirely from Workflows list (production)
- Direct Edit
- Direct Delete

---

## Warning / Confirmation Requirements (If direct edit exists)
If you allow “Edit directly” in dev/staging:
- Modal required:
  - “Direct edits create drift from Git.”
  - “Recommended: create a deployment instead.”
- Confirm checkbox:
  - “I understand this will create drift.”
- Logged audit event:
  - actor, env, workflow, timestamp, reason (optional)

---

## Routing & Deep Links (Critical)
### Workflows page should route to:
- Workflow details (read-only)
- Deployments (new deployment run pre-filled)
- Drift Incident workspace (if applicable)

It should NOT embed:
- Diff viewer
- Reconciliation steps
- Restore mechanics

---

## Backend / Data Requirements

### 1) Per-workflow drift calculation
- Ensure “Git status” per workflow can be computed or approximated:
  - in-sync vs drifted vs unknown
- Avoid comparing runtime-only fields (executions/history)

### 2) Audit events
Add/ensure activity events exist for:
- workflow_edit_direct
- workflow_delete_direct
- deployment_created_from_workflow
- drift_incident_created_from_workflow

### 3) Policy evaluation (server-side)
Implement a policy check for:
- env_type (dev/staging/prod)
- plan tier
- role (tenant admin vs editor vs viewer)
- optional enterprise policy overrides

Server must enforce; UI must reflect.

---

## Implementation Steps (Iterative)

### Phase 1 — UI De-clutter (Actions Menu)
- Replace per-row Edit/Delete with `Actions ▾`
- Keep View and Open in n8n
- Keep existing behavior behind menu temporarily (dev only)
**Exit:** Reduced accidental clicks; centralized gating point exists.

### Phase 2 — Environment-Based Gating
- Hide/disable direct Edit/Delete in production
- Gate staging edits with confirm + role checks
- Keep dev permissive
**Exit:** Production workflow list is safe by default.

### Phase 3 — Route Changes Through Deployments
- Add “Create Deployment” action for all envs
- Make it the recommended path in UI copy
- Reframe “Upload Workflow” → “Create Deployment” (or route upload)
**Exit:** Normal change path becomes discoverable and dominant.

### Phase 4 — Integrate Drift Incident Entry Points
- If drift exists:
  - show “View/Create Drift Incident” in Actions menu
- No diff UI here; link out only
**Exit:** Workflows list participates in incident routing without becoming incident UI.

### Phase 5 — Remove / Deprecate Direct Mutation Paths (Optional tightening)
- For Agency+ defaults:
  - Disable direct edits even in staging
  - Encourage dev edits only
- For Enterprise:
  - Policy-driven disable for dev too
**Exit:** Governance hardens as tenants mature.

---

## Acceptance Criteria
1. No inline Edit/Delete buttons exist on workflow rows; a single Actions menu is used.
2. Production environment never allows direct Edit/Delete from the Workflows page (server-enforced).
3. Staging direct edits are gated by role + explicit confirmation (if enabled at all).
4. “Create Deployment” is available from each workflow row and is the primary recommended path.
5. Drift-related actions on workflows are navigation-only (to Drift Incident workspace), not embedded handling.
6. “Upload Workflow” does not bypass governance in staging/prod; it routes to Deployments or is gated.

---

## Notes / Risks
- If existing users rely on inline edits, dev-only permissive policies reduce churn.
- If “Edit” currently edits in Git (not n8n), rename it to avoid confusion:
  - “Edit in Git” vs “Edit in n8n”
- Ensure any removed actions still exist somewhere appropriate (Deployments, Drift Incidents, Settings).
