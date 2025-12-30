# environmentdetailsupdate.md — Environment Details Page Refactor (Drift-First, Incident-Centered)

## Objective
Refactor the Environment Details UI so it becomes a **status + navigation** surface, not an operational control plane. Centralize all drift handling into a **Drift Incident workspace** and move high-impact actions into the correct dedicated surfaces (Incidents, Deployments, Settings).

This update must:
- Reduce cognitive load and unsafe actions
- Remove “drift splatter” across tabs
- Align with GitHub as source of truth (declarative workflows)
- Support plan-based gating and environment-based safety (prod stricter)
- Be implementable iteratively

---

## Guiding Principles (Non-Negotiable)
1. **Environment Details page is read-first**
   - It explains state and routes the user to the correct process.
2. **Drift is a process, not a badge**
   - Deep drift UX occurs only in the Drift Incident workspace.
3. **High-impact actions require scoped context**
   - Restore, delete, and reconciliation cannot be top-level buttons.
4. **Normal path vs incident path**
   - Normal changes → Deployments (enforced path)
   - Exceptions → Drift Incident (break-glass path)
5. **Plan gating is server-enforced**
   - UI hides/limits features, but APIs must enforce.

---

## Current-State Assessment (Required Before Changes)
### Inventory existing behavior
- Where drift is currently computed and displayed (all locations)
- Where actions exist that imply drift handling (Restore, Sync, etc.)
- What the “Sync” job actually does today (directionality, artifacts)
- Snapshot semantics (what “commit SHA” means; restore side effects)
- Audit log types and where “Activity Center” is sourced from

### Outcome
Produce a short “as-is map” listing:
- UI components/pages showing drift
- Back-end endpoints/services involved
- Data models storing sync/backup/restore state

**Exit criteria:** You can point to every drift-related UI element and the code path behind it.

---

## Target UX Changes (Clean List)

### A) Global Environment Details Page (Header + Actions)
#### 1) Remove global action bar
Remove from the top of the page:
- Sync
- Backup
- Restore
- Download
- Test Connection
- Edit
- Delete

#### 2) Add a single “Environment State” indicator
Add one canonical state badge near the title:
- `In Sync`
- `Drift Detected`
- `Drift Incident Active`

#### 3) Add a single CTA when drift exists
- If `Drift Incident Active` → **View Drift Incident**
- If `Drift Detected`:
  - Pro+ → **Create Drift Incident**
  - Free → **View Drift Summary** + upgrade CTA (no incident workflow)

**Rule:** No other drift CTAs appear across tabs.

---

### B) Tabs (What to Keep vs Change)

#### 1) Overview Tab
Keep:
- Workflows count
- Active workflows count
- Credentials count
- Recent activity preview (summary only)

Change:
- Add **Drift Summary Card** (top section)
  - Drift state
  - Last detected time
  - Affected workflow count (summary only)
  - CTA → Drift Incident (if allowed)

- Replace “Recent Activity” framing with **Recent Events**
  - Include: syncs, backups, restores, drift acknowledgements, reconciliations
  - Keep “View All Activity” as link to Activity tab or Activity Center

Remove:
- Any operational actions or “fix now” workflows from Overview

---

#### 2) Workflows Tab
Keep:
- Table/list of workflows
- Status (active/inactive)
- Last updated
- View action

Change:
- Label as **read-only**
- Optional: add search/filter controls (not drift-related)

Remove:
- Any sync/upload/restore affordances from this tab

---

#### 3) Snapshots Tab
Keep:
- Snapshot list
- Created timestamp, type, commit SHA, notes

Change:
- Replace **Restore** button with plan-gated alternatives:
  - Agency+ (or plans with Drift Incidents): **Use in Drift Incident**
  - All plans: **View Snapshot Details**
- If you must keep Restore for backward compatibility:
  - Hide behind a “Danger Zone” sub-section and admin-only gating
  - Strongly discourage and route to Drift Incident when available

Rule:
- Snapshots are **inputs** to recovery, not the recovery workflow itself.

---

#### 4) Sync History Tab → Rename to “Activity”
Change:
- Rename tab label to **Activity**
- Expand entries beyond sync:
  - Syncs
  - Backups
  - Restores
  - Drift acknowledgements
  - Reconciliations
- Keep “View” details per item

Remove:
- “Sync-only” framing; this tab is audit/activity.

---

#### 5) Credentials Tab
Keep:
- Credential health summary
- Empty-state messaging

Change:
- Make explicit **read-only**
- Provide navigation to central credential management (if applicable)
- Improve empty state:
  - “No credentials cached. Run a sync via Deployments (or Admin) to fetch metadata.”

Remove:
- Any credential mutation here

---

#### 6) Settings Tab (Only place for mutation)
Move/Keep here:
- Test Connection
- Edit environment metadata
- Git configuration (repo + branch)
- Feature flags (but replace with policy concepts where possible)
- Delete environment (guarded)

Add:
- Plan-gated drift-related settings (lower plans only):
  - Drift handling behavior:
    - Warn only
    - Allow manual override (recorded)
    - Require manual attestation before continuing (soft gate)
- Agency+/Enterprise settings:
  - Deployment enforcement settings (read-only for non-admin)
  - Drift TTL/SLA policy (Enterprise org-level preferred)

Rule:
- If it changes configuration, it lives in Settings.

---

## Plan-Based Gating (Environment Details Page)
### Free
- Drift detection + banner only
- No incident creation/workspace
- No diffs (summary only)
- Manual override setting allowed (recorded)

### Pro
- Allow “Create Drift Incident” (single env)
- Limited diff (workflow-level)
- No TTL/SLA enforcement on page

### Agency+
- “View Drift Incident” visible when active
- Restore via Drift Incident only (prefer)
- Activity includes reconciliation events

### Enterprise
- Policy-driven gating; approvals may be required
- No override/ignore options unless policy allows

---

## Environment-Based Safety (Production vs Non-Prod)
Implement environment criticality behavior:
- Production:
  - No destructive actions visible outside incident workflows and Settings (admin-only)
  - Drift CTAs should default to “View Incident” with strong warning
  - Disable any “direct restore” affordance outside incident workspace
- Dev/Staging:
  - More permissive navigation; still keep operations out of the header

---

## Implementation Steps (Iterative)

### Phase 1 — UI De-clutter + Single Drift Entry Point
- Remove global action bar
- Add environment state indicator
- Add single drift CTA (View Incident / Create Incident / Upgrade)
- Keep existing tabs as-is, but remove drift references outside Overview
**Exit:** Page is calmer; drift is discoverable in one place.

### Phase 2 — Rename Sync History → Activity + Expand Event Types
- Rename tab label
- Ensure event model supports non-sync actions
- Update copy: “Audit log of operations”
**Exit:** Unified audit surface exists.

### Phase 3 — Snapshots Tab Adjustments
- Replace Restore button with “Use in Drift Incident” (plan gated)
- Keep restore only behind “Danger Zone” if required temporarily
**Exit:** Recovery operations are routed to incident process.

### Phase 4 — Settings Consolidation
- Move Test Connection / Edit / Delete into Settings
- Add plan-gated drift behavior settings (Free/Pro)
- Add prod safety restrictions
**Exit:** Mutation is centralized; fewer accidental actions.

### Phase 5 — Remove Residual Drift Splatter
- Search codebase for drift UI mentions outside:
  - Overview drift summary card
  - Global drift state badge + CTA
  - Drift Incident workspace
- Remove/replace with links
**Exit:** Drift UX is centralized.

---

## Data / Backend Requirements (For UI to Work)
### Add/Expose environment-level drift state fields
- drift_status: `IN_SYNC | DRIFT_DETECTED | DRIFT_INCIDENT_ACTIVE`
- last_drift_detected_at
- active_drift_incident_id (nullable)
- drift_summary (count + brief metadata)

### Activity feed must support event types
Ensure activity model includes:
- sync
- backup
- restore
- drift_acknowledged
- drift_reconciled
- drift_closed

### Plan gate endpoints
- `/me/plan` or tenant plan descriptor
- Feature flags: `drift_detection`, `drift_incidents`, `drift_diff`, `drift_ttl_enforcement`

---

## Acceptance Criteria
1. No global action bar exists on Environment Details.
2. Drift appears only as:
   - a single environment state badge, and
   - a single CTA to drift workspace.
3. Snapshots do not present “Restore” as a default action when Drift Incidents are available.
4. “Sync History” is renamed and expanded to “Activity”.
5. Settings is the only place where environment configuration is changed.
6. Production environments have stricter visibility and gating of destructive actions.
7. Plan gates are enforced server-side (UI is not the only gate).

---

## Notes / Risks
- Removing the action bar is a breaking UX change; mitigate with:
  - “Where did Sync go?” tooltip/empty-state pointers that route to Deployments or Drift Incident.
- If deployments UI does not yet exist, temporarily route:
  - Sync → “Activity Center / Operations” until Deployments is implemented,
  - but keep the Environment header free of operation buttons.
