# drift.md — Drift as a First-Class Incident System (Iterative Plan)

## Goal
Refactor “drift” from a scattered UI signal into a **first-class, incident-based process** that:
- Treats drift as an **incident with lifecycle**
- Prevents **orphaned hotfixes** (no change disappears without an explicit decision)
- Keeps GitHub as the **source of truth** (declarative workflow state)
- Cleanly gates drift capabilities by **plan tier**
- Removes drift logic from being “splashed” across unrelated pages by centralizing it into a **Drift Incident workspace**

---

## Definitions (Non-Negotiable)
### Source of Truth
- **GitHub** is authoritative for **declarative workflow definitions**.
- Runtime/operational data (executions, history, queues) is NOT drift.

### Drift
A difference between:
- Declarative state in **n8n environment**, and
- Declarative state in **GitHub** (or derived artifact from Git)

### Drift Incident
A first-class object that represents a drift occurrence tied to **exactly one environment** and a controlled lifecycle:
`Detected → Acknowledged → Stabilized → Reconciled → Closed`

---

## Plan Gating (Product Model)
Drift is split into:
1) **Drift Detection & Visibility** (safety/ honesty; always on)
2) **Drift Incident Management** (governance/ resolution workflow; paid tiers)

### Tier Capabilities
| Capability | Free | Pro | Agency | Enterprise |
|---|---:|---:|---:|---:|
| Drift detection (declarative only) | ✅ | ✅ | ✅ | ✅ |
| Drift visibility banners | ✅ | ✅ | ✅ | ✅ |
| Basic drift summary (counts, affected workflows) | ✅ | ✅ | ✅ | ✅ |
| Manual override / ignore (recorded) | ✅ | ✅ | ⚠️ limited | ❌ (policy-based) |
| Drift incident creation/workspace | ❌ | ✅ (single env scope) | ✅ | ✅ |
| Full diff visualization | ❌ | ⚠️ limited | ✅ | ✅ |
| Incident lifecycle states | ❌ | ✅ basic | ✅ full | ✅ full + approvals |
| Ownership, reason, ticket link | ❌ | ⚠️ limited | ✅ | ✅ |
| TTL / SLA enforcement | ❌ | ❌ | ✅ | ✅ |
| Deployment blocking on expired drift | ❌ | ❌ | ✅ | ✅ |
| Org-wide policies | ❌ | ❌ | ❌ | ✅ |
| Compliance reporting / long retention | ❌ | ❌ | ⚠️ | ✅ |

⚠️ = constrained scope/limits (configured by product decision)

**Principle:** Free users can *see* drift; paid users can *manage* drift.

---

## UX Architecture (Separation of Concerns)
### Before (current problem)
- Drift indicators and “what to do next” logic appears across multiple pages.
- Actions (sync/restore/backup) are overloaded with drift meaning.

### After (target)
- Environment surfaces show only:
  - **Status**: In Sync / Drift Detected / Drift Incident Active
  - A single CTA: **“View Drift”** (routes to Drift workspace)
- Drift logic (diff, acknowledgment, TTL, resolution) lives ONLY in:
  - **Drift Incident workspace/page**

**Result:** Drift is centralized, consistent, and policy-driven.

---

## Lifecycle & Enforcement Model
### Normal Mode (default)
- Deployments are enforced (Git → deploy → environment)
- Drift should not persist

### Incident Mode (exception)
- Drift is tolerated temporarily to stabilize production
- Governance is paused for recovery, not removed
- Drift must be reconciled and closed

### Closure Rule
A Drift Incident closes only when:
- Environment declarative state matches selected Git ref/artifact, AND
- A resolution path is recorded (promote/revert/replace)

---

## Resolution Paths (No PR UI Exposure)
WorkflowOps UI does NOT expose PRs. It tracks **Reconciliation Artifacts**.

### Resolution Options
1. **Promote to Source of Truth**
   - Backend creates commit/PR, merges, and records outcome
   - UI shows: “Promoted to Git” + status (Pending/Merged/Failed)
2. **Revert to Source of Truth**
   - Redeploy Git state over environment; drift discarded
3. **Replace**
   - Different fix in Git supersedes hotfix; deploy replaces drifted state

**Key:** Mandatory resolution decision, not mandatory “commit the hotfix exactly as-is”.

---

## Implementation Plan (Iterative, Multi-Step)

### Phase 0 — Analysis of Existing Functionality (Required)
**Objective:** Create an accurate map of current drift-related behaviors and data.
1. Inventory current drift signals:
   - Where drift is computed
   - Where it is displayed
   - What actions it triggers (block, warn, etc.)
2. Inventory current action semantics:
   - “Sync”, “Backup”, “Restore” definitions and side effects
3. Identify existing persistence:
   - Any tables/fields already storing drift-like state
   - Any logs/audit records for sync/restore
4. Identify drift scope:
   - What is being compared today (workflow JSON, metadata, enabled state, etc.)
   - What must be excluded (executions/history)
5. Produce a short internal doc:
   - Current-state flows (as-is)
   - Gaps vs target model

**Exit criteria:** You can answer “where does drift exist today?” with a diagram and code entrypoints.

---

### Phase 1 — Always-On Drift Detection + Minimal Surfacing (All Plans)
**Objective:** Establish safe drift detection and a single consolidated indicator.
1. Implement/confirm drift detection pipeline (declarative only):
   - Pull environment workflow definitions from n8n
   - Pull Git “desired state” from repo artifact
   - Normalize (ignore benign differences: timestamps/order)
2. Persist minimal drift summary per environment:
   - drift_status: `IN_SYNC | DRIFT_DETECTED`
   - drift_summary: affected workflow count + last detected time
3. UI changes:
   - Environment list: add Drift status badge (no diff)
   - Environment details: show Drift banner with CTA “View Drift”
   - Remove other scattered drift callouts (defer deep removals to Phase 3)
4. Plan gating:
   - Everyone sees detection + banner
   - No incident workflow yet

**Exit criteria:** Drift detection runs reliably; UI shows one consistent entrypoint; no user is blind to drift.

---

### Phase 2 — Drift Incident Object + Workspace (Paid: Pro+)
**Objective:** Introduce the Drift Incident as first-class citizen and centralize drift UX.
1. Add Drift Incident domain object (DB + API)
2. Create Drift Incident workspace UI:
   - Incident header (env, status, detected time)
   - Affected workflows list
   - Basic diff view (Pro-limited)
   - Actions:
     - Acknowledge (with reason)
     - Choose resolution path (placeholders for Phase 4 execution)
3. Convert “drift detected” into “incident available” where supported:
   - On Pro+: allow “Create Drift Incident”
   - On Free: show “Upgrade to manage drift incidents”
4. Centralize drift interactions:
   - Remove any other drift action buttons outside workspace (begin cleanup)

**Exit criteria:** Drift is handled in one place; environment pages become shallow and consistent.

---

### Phase 3 — De-splash Drift From the UI (Refactor)
**Objective:** Remove drift logic from unrelated pages and reduce cognitive load.
1. Audit UI components where drift appears today
2. Replace with:
   - Drift status badge
   - “View Drift” link (to incident workspace)
3. Remove drift-driven branching from:
   - Sync button flows
   - Backup/restore pages
   - Random warnings in environment list
4. Ensure the only “deep drift UX” is the incident workspace.

**Exit criteria:** No duplicated drift UX; no scattered warnings; a single canonical drift workflow.

---

### Phase 4 — Reconciliation Execution + Orphan Prevention (Agency+)
**Objective:** Make reconciliation real and prevent orphaned hotfixes.
1. Implement resolution execution handlers:
   - Promote to Git (backend-only PR/merge) → record outcome
   - Revert to Git (deploy desired state) → record outcome
   - Replace (link to deployment that supersedes)
2. Add “Reconciliation Artifact” tracking (no PR UI):
   - artifact_type: `PROMOTE | REVERT | REPLACE`
   - artifact_status: `PENDING | SUCCESS | FAILED`
   - external_refs (commit SHA, PR URL hidden by default, deployment run id)
3. Enforce incident closure rule:
   - Cannot close until drift diff is zero and resolution recorded
4. Add “orphan prevention” invariant:
   - Any drifted change cannot vanish without an explicit resolution decision recorded

**Exit criteria:** Drift incidents reach actual closure; reconciliation is auditable; no silent loss.

---

### Phase 5 — TTL/SLA + Enforcement (Agency/Enterprise)
**Objective:** Turn drift management into governance with predictable behavior.
1. Add TTL/SLA fields to incidents:
   - acknowledged_at
   - expires_at
   - severity escalation rules
2. Enforcement:
   - On Agency+: block deployments when drift incident is **expired**
   - On Enterprise: policy-driven (who can acknowledge/extend TTL)
3. Add dashboards:
   - Active incidents
   - Expired incidents
   - MTTR-like stats (optional)

**Exit criteria:** Drift cannot remain unresolved indefinitely; enforcement is fair and explainable.

---

### Phase 6 — Enterprise Policies & Approvals (Enterprise)
**Objective:** Compliance-grade controls.
- Approval workflows for acknowledging drift
- Role-based TTL extensions
- Org-wide policy templates
- Long retention + reporting export

**Exit criteria:** Large orgs can meet audit/compliance expectations.

---

## Database Migrations (Proposed Schema)
### New Tables
#### drift_incidents
- id (uuid)
- environment_id (uuid, FK)
- status (enum): DETECTED, ACKNOWLEDGED, STABILIZED, RECONCILED, CLOSED
- detected_at (ts)
- acknowledged_at (ts, nullable)
- stabilized_at (ts, nullable)
- reconciled_at (ts, nullable)
- closed_at (ts, nullable)
- owner_user_id (uuid, nullable)
- reason (text, nullable)
- ticket_ref (text, nullable)
- expires_at (ts, nullable)  // Agency+
- severity (enum, nullable)  // Agency+
- plan_snapshot (jsonb)      // optional: record plan at incident creation
- created_at, updated_at

#### drift_changes (optional; depends on diff storage strategy)
- id (uuid)
- incident_id (uuid, FK)
- workflow_id (text / uuid depending on n8n id)
- change_type (enum): ADDED, REMOVED, MODIFIED
- summary (text)
- diff_blob_ref (text or jsonb)  // store diff or pointer to object storage
- created_at

#### drift_reconciliation_artifacts
- id (uuid)
- incident_id (uuid, FK)
- type (enum): PROMOTE, REVERT, REPLACE
- status (enum): PENDING, SUCCESS, FAILED
- started_at, finished_at
- external_ref (jsonb) // commit sha, internal deployment run id, etc.
- error_message (text, nullable)
- created_at

### New Fields (existing tables)
#### environments
- drift_status (enum): IN_SYNC, DRIFT_DETECTED, DRIFT_INCIDENT_ACTIVE
- last_drift_detected_at (ts, nullable)
- last_drift_incident_id (uuid, nullable)

---

## API / Service Responsibilities
### Drift Detection Service
- Runs on schedule or event trigger
- Produces:
  - environment.drift_status
  - optional drift_incident auto-create (paid tier policy)

### Drift Incident Service
- CRUD incident lifecycle
- Enforces plan gates
- Enforces closure rules
- Produces reconciliation artifacts

### Deployment Service Integration
- Reads enforcement state:
  - Block deployments only for expired incidents (Agency+)
- Records REPLACE actions by linking to deployment runs (Phase 4+)

---

## Plan Gate Implementation Notes
- Gate at API boundary (server-side), not just UI.
- Ensure “detection + banner” cannot be disabled on any plan.
- If a plan does not support incident mgmt:
  - show drift status
  - provide manual remediation guidance
  - provide upgrade path
  - record manual override decisions (limited)

---

## Manual Remediation (Lower Plans)
When drift detected and incidents are unavailable:
- Show a clear choice:
  - “Manually resolve in n8n to match Git” (instructions + recheck button)
  - “Override/ignore” (recorded, visible, limited retention)
- Never hide drift.
- Never allow silent ignore.

---

## Success Metrics
- % drift incidents closed within SLA (Agency+)
- Reduction in “unknown drift” occurrences
- Reduction in repeated incidents from same root cause
- Rate of “override debt” accumulation on lower tiers
- Upgrade conversion from drift detection → drift management

---

## Deliverables by Phase (Checklist)
- Phase 0: Current-state analysis doc + code entrypoints list
- Phase 1: Drift status + banner + single entrypoint
- Phase 2: Drift Incident workspace + plan gating
- Phase 3: UI refactor removing drift splatter
- Phase 4: Reconciliation artifacts + closure enforcement
- Phase 5: TTL/SLA + expired drift enforcement
- Phase 6: Enterprise policy engine + approvals/reporting

---

## Guardrails (Must Hold Throughout)
1. Drift detection is always on.
2. Drift deep UX exists only in Drift Incident workspace.
3. Incidents are scoped to a single environment.
4. No incident can close without an explicit resolution path.
5. No change disappears without an explicit recorded decision.
6. Enforcement never blocks emergency recovery; it applies post-incident via TTL/SLA.
