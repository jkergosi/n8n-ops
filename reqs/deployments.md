# Claude Code Instructions: Refactor Deployments into an Azure-style Promotion + Semantic Diff Flow

## Objective
Evaluate the existing **Deployment** functionality end-to-end (backend + frontend) and refactor it into a clean, low-overhead **Promotion Plan → Review → Deploy** flow with:
- **Single authoritative diff computation on the backend**
- **Correct diff statuses** (Added/Modified/Deleted/Unchanged + Target Hotfix)
- **Unchanged hidden by default**
- **No “Will Update” language in diff phase**
- **No auto-execution on create**
- **AI high-level summary** (derived strictly from structured diff facts) + drill-down lenses (Nodes/Flow/Settings/Raw)

Everything is test data; prioritize correctness and UX clarity over backward-compat.

---

## Current Problems to Confirm (Do Not Assume; Verify in Code)
1. Frontend currently marks any workflow that exists in target as `changed` (heuristic), creating many false “Will Update”.
2. Backend diff logic already normalizes and finds real differences, but frontend isn’t using it for the selection table.
3. The “New Deployment” page behaves like “create + run” instead of “plan + explicit execute”.
4. Inline diff is being used as a primary decision mechanism; JSON diffs are too low-level for approvals.

You must verify these by finding the actual files and execution paths in repo.

---

## Definitions (Use These Throughout)
### Promotion Plan (Planning Phase)
A **non-executing** comparison of source and target environments that produces:
- high-level summary counts and risk
- per-workflow diff status
- optional workflow selection list

### Deployment (Execution Phase)
An immutable execution record created **only when the user confirms**:
- Run now / schedule
- selected workflows to apply
- source→target environment transition

### Diff Status (Azure/GitHub aligned)
Use these canonical internal values:
- `added` (exists only in source)
- `modified` (exists in both, semantic content differs)
- `deleted` (exists only in target) — optional to support in promotions
- `unchanged` (semantic content identical)
- `target_hotfix` (target newer than source OR target differs and is considered authoritative)

**UI labels:**
- Added, Modified, Deleted, Unchanged, Target Modified (Hotfix)

**Hard rule:** Remove “Will Update” and any predictive deployment language from diff statuses.

---

## Deliverable Summary
You will produce:
1. Refactored backend endpoints/services for **compare → plan → deploy**
2. Refactored frontend to:
   - show **Promotion Plan** first
   - show only changed by default
   - use backend-provided statuses
3. Semantic diff output shape (facts + risk categories)
4. AI Summary generation endpoint (optional but recommended) that is:
   - grounded strictly in structured diff facts
   - cached by diff hash
5. Tests + acceptance criteria implemented

---

## Phase 1 — Code Recon & Inventory (Must Do First)
### 1. Identify the full deployment flow
Locate and map:
- Backend endpoints involved in “New Deployment” creation and execution
- Any service modules responsible for:
  - workflow fetch
  - normalization
  - diff computation
  - execution/apply (writing workflows to target)
- DB tables used:
  - deployments / deployment_workflows
  - pipeline/stage config
  - anything related to comparisons

### 2. Identify frontend pages/components
Find:
- New deployment page component (e.g., `NewDeploymentPage.tsx` or equivalent)
- Diff modal/view component
- API client methods called during page load and on “Create Deployment”
- Any feature gating that might hide/show deployments

**Output:** add a brief internal notes section in code comments or a short `/docs/dev/deployments_refactor_notes.md` (optional) describing discovered flows and where changes will be applied.

---

## Phase 2 — Backend: Make Comparison Authoritative and Cheap
### 1. Implement/standardize a single compare service
There must be exactly one backend service responsible for comparison:
- Input: `(tenant_id, source_env_id, target_env_id, pipeline_id, stage_id)`
- Output: `PromotionPlanCompareResult` (see schema below)

If comparison logic exists in multiple places, consolidate.

### 2. Active comparison rules (must match UI expectations)
- Normalize workflows for comparison (ignore UI metadata: positions, internal ids, timestamps)
- Compare:
  - nodes (added/removed/modified)
  - connections
  - settings (execution-relevant)
- Determine `diff_status` using normalized equality + timestamp rules:
  - if no target: `added`
  - if normalized equal: `unchanged`
  - if normalized differs and source newer or no timestamps: `modified`
  - if normalized differs and target newer: `target_hotfix`

### 3. Add semantic categories per node change (facts, not AI)
Extend diff output so approvals can understand *what changed* without reading JSON.
For each changed node, compute `change_categories` (list):
- `node_added`, `node_removed`, `node_type_changed`
- `credentials_changed`
- `expressions_changed`
- `http_changed` (method/url/headers/body template)
- `trigger_changed` (schedule/webhook)
- `routing_changed` (IF/Switch paths)
- `error_handling_changed` (retry/continueOnFail)
- `settings_changed` (workflow-level)
- `rename_only` (low)

Also compute a deterministic `risk_level` per workflow:
- `low`, `medium`, `high`
Rules (suggested):
- High: credentials_changed, expressions_changed, trigger_changed, http_changed, code_changed, routing_changed
- Medium: error_handling_changed, settings_changed
- Low: rename_only, metadata-only

### 4. Compare endpoint (required)
Implement (or adjust) a backend endpoint that returns the full comparison result for a stage:
- `GET /promotions/compare?pipeline_id=...&stage_id=...` (or your routing convention)

**Hard rule:** Frontend must never infer “changed” based on existence; it must consume this endpoint.

---

## Phase 3 — Backend: Introduce Promotion Plans (Planning) vs Deployments (Execution)
### 1. Promotion Plan: no execution side effects
Implement a “plan” endpoint that persists a lightweight plan record (optional) OR returns ephemeral plan data:
- `POST /promotions/plan` with:
  - source env, target env, pipeline/stage
  - optional selected workflow ids/names
- returns:
  - plan_id (if persisted)
  - compare_result snapshot (or compare_hash reference)

**Recommendation:** Persist plan only if you need “drafts”. If not, treat compare result as ephemeral and only persist on execution.

### 2. Deployment creation must not auto-run
Refactor “Create Deployment” so that:
- Creating a deployment record does NOT start execution automatically.
- Execution starts only when explicitly triggered by the user:
  - `POST /deployments/{id}/run` (immediate)
  - or `POST /deployments/{id}/schedule` (schedule)

If you already have scheduling, ensure “Create” ≠ “Run”.

### 3. Deployment should store immutable selection + compare hash
When a deployment is created, store:
- source_env_id, target_env_id, pipeline_id, stage_id
- selected workflows
- compare hash used to decide
- created_by, timestamps
This supports audit and reproducibility.

---

## Phase 4 — Frontend: Redesign New Deployment into Promote → Deploy
### Required UX changes
1. Rename/position page as **Promote** (planning), not executing.
2. On selecting pipeline+stage:
   - Call backend compare endpoint once
   - Display summary counts:
     - total, added, modified, deleted, unchanged, target_hotfix
3. Default list view:
   - show only `added | modified | target_hotfix` (configurable)
   - hide unchanged behind toggle: “Show unchanged (N)”
4. Replace status badge “Will Update” with:
   - Added / Modified / Unchanged / Target Modified
5. Selection defaults:
   - Pre-select all **Added + Modified** by default
   - Do NOT pre-select unchanged
   - For `target_hotfix`, default selection should be OFF (user must opt-in to overwrite hotfix), unless your product chooses otherwise.
6. “View Diff” action should open a modal with tabs:
   - **Summary** (AI summary if enabled; otherwise deterministic summary)
   - Nodes
   - Flow
   - Settings
   - Raw JSON (escape hatch)

### Data flow (hard rules)
- The list table must be driven by backend compare results.
- The diff modal must be driven by backend diff results.
- Frontend should not compute statuses other than rendering.

### Minimal UI components to implement
- Summary header cards or inline text (counts)
- Filter tabs or chips:
  - Changed (default), Unchanged, Target Modified, All
- Toggle: show/hide unchanged
- Bulk actions:
  - Select all changed
  - Clear selection
- Execution area:
  - Run now / schedule
  - Button text should reflect execution: **Deploy** / **Promote**
  - Create deployment should not run automatically; if “Deploy” triggers create+run, it must be explicit and labeled accordingly.

---

## Phase 5 — AI Summary of Diffs (Recommended Default View)
### Purpose
Provide an approval-friendly narrative that explains “what changed” using structured diff facts.

### Hard constraints
- AI input must be **structured diff facts**, not raw workflow JSON.
- AI must be instructed: **do not infer; only summarize provided facts**.
- If no functional differences exist, summary must say: “No functional differences detected” (or equivalent).

### Implementation
1. Add backend endpoint:
   - `POST /promotions/diff-summary`
   - input: workflow_id + envs OR the diff payload reference
   - output:
     - `bullets[]` (3–6 items)
     - `risk_level`
     - `evidence_map` mapping bullet→facts used (node ids/names/categories)
2. Cache summaries by `diff_hash`:
   - if `source_norm_hash == target_norm_hash`, skip AI and return deterministic “no functional changes”.
3. Failure behavior:
   - If AI fails, UI still shows deterministic semantic facts; never block.

### UI
- Default tab: “Summary”
- Each bullet expandable to show “Evidence” (nodes/categories counts)

---

## Phase 6 — Acceptance Criteria (Must Implement + Verify)
### Correctness
1. Workflow where backend diff finds no differences must show status **Unchanged** and must not be pre-selected.
2. “Changed” workflows must only be those where backend says `added|modified|target_hotfix`.
3. Counts shown in summary must match list contents.

### UX
4. Unchanged workflows hidden by default; toggle reveals them.
5. No “Will Update” language anywhere in diff UI.
6. Creating a deployment does not execute unless the user explicitly chooses “Deploy/Run”.

### Safety
7. `target_hotfix` workflows must never be overwritten silently. Require explicit selection (or confirm prompt).

### AI summary
8. AI summary must match structured facts and show “Evidence”.
9. AI summary must not mention changes not present in diff facts.

---

## Tests (Minimum)
Backend:
- Unit tests for diff_status resolution (added/unchanged/modified/target_hotfix)
- Unit tests for semantic category classification
- Unit tests for risk_level rules

Frontend:
- Component test or integration test that:
  - renders only changed by default
  - toggles unchanged
  - uses backend statuses for badges
  - preselects only added/modified

---

## Implementation Notes / Guardrails
- Avoid N+1 compare calls. Compare once per stage selection.
- Prefer stable identifiers for node matching:
  - node id if stable, else `name+type` with tie-breakers
- Do not treat UI-only metadata as a modification.
- Keep raw JSON diff available as an advanced view only.

---

## Suggested Response Schema (Backend → Frontend)
Use something close to this shape (adapt to your stack conventions):

```json
{
  "pipeline_id": "…",
  "stage_id": "…",
  "source_env_id": "…",
  "target_env_id": "…",
  "summary": {
    "total": 86,
    "added": 1,
    "modified": 3,
    "deleted": 0,
    "unchanged": 82,
    "target_hotfix": 0
  },
  "workflows": [
    {
      "workflow_id": "…",
      "name": "zOLD_s_prompt_eval",
      "diff_status": "unchanged",
      "risk_level": "low",
      "change_categories": [],
      "diff_hash": "…",
      "details_available": true
    }
  ]
}
```

Per-workflow detail endpoint (modal):
```json
{
  "workflow_id": "…",
  "name": "…",
  "diff_status": "modified",
  "risk_level": "high",
  "node_changes": [
    { "node": "HTTP Request", "type": "n8n-nodes-base.httpRequest", "categories": ["http_changed"], "before_preview": "POST https://api.foo/v1", "after_preview": "POST https://api.bar/v2" }
  ],
  "flow_changes": [
    { "kind": "edge_added", "from": "IF", "to": "Slack" }
  ],
  "settings_changes": [
    { "key": "errorWorkflow", "before": "none", "after": "NotifyOps" }
  ],
  "raw_available": true
}
```

---

## Execution Order (Do in This Order)
1. Recon & inventory
2. Backend compare endpoint + schema
3. Frontend table driven by backend compare
4. Hide unchanged + correct status labels + selection defaults
5. Separate create vs run semantics
6. Semantic categories + risk
7. AI summary endpoint + caching
8. Tests + acceptance verification

---

## Done Definition
This refactor is complete when:
- A workflow that produces “No differences found” in diff view is also **Unchanged** in the selection table.
- New promotion flow feels lightweight:
  - summary first, deltas only by default, details on demand
- Execution is explicit and auditable.
