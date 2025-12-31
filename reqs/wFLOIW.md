# Claude Code Instructions — Evaluate & Fix Environment Action Guards (WorkflowOps)

## Goal
Audit the current WorkflowOps codebase to ensure user actions are correctly **allowed/blocked per environment** (dev/staging/prod) and that the enforcement is done in the right layers:
- **Hard policy (server-side required)**
- **Feature flag / plan gating**
- **UI-only convenience gating** (never sufficient)

Then implement any missing or incorrect enforcement, end-to-end (API + UI), with tests.

---

## Ground Truth: Allowed Actions Matrix

Legend: ✓ allowed, ✗ blocked, ⚠ policy-dependent (default OFF)

### Dev
- Edit in N8N: ✓
- Sync Status: ✓
- Backup: ✓
- Manual Snapshot: ✓
- Diff/Compare: ✓
- Deploy Outbound (Dev→Staging): ✓
- Deploy Inbound (→Dev): ✗
- Restore/Rollback: ⚠

### Staging
- Edit in N8N: ✗
- Sync Status/Drift: ✓
- Backup: ✗
- Manual Snapshot: ⚠
- Diff/Compare: ✓
- Deploy Outbound (Staging→Prod): ✓
- Deploy Inbound (Dev→Staging): ✓
- Restore/Rollback: ✓

### Prod
- Edit in N8N: ✗
- Sync Status/Drift: ✓
- Backup: ✗
- Manual Snapshot: ✗
- Diff/Compare: ✓
- Deploy Outbound (Prod→*): ✗
- Deploy Inbound (Staging→Prod): ✓ (admin only)
- Restore/Rollback: ✓ (admin only)

---

## Step 1 — Identify All User-Facing Actions
Search the code for entry points:
- UI buttons/menus/routes for: Sync, Backup, Snapshot (manual), Deploy, Restore/Rollback, Diff/Compare, N8N edit link-out
- Backend endpoints/handlers/jobs for the same

Deliverable:
- A list mapping **Action → UI component(s) → API endpoint(s) → job/worker(s)**.

---

## Step 2 — Classify Each Guard: Policy vs Feature Flag vs UI Convenience

### 2.1 Policies (MUST be enforced server-side)
These must be enforced in backend authorization/validation (UI gating is not enough):
- Block Backup in staging/prod
- Block manual Snapshot in prod
- Block deploy outbound from prod
- Block deploy inbound to dev
- Block N8N edit actions for staging/prod (at least in WorkflowOps UI; cannot truly prevent direct n8n access)
- Require admin role for deploy into prod and rollback prod

Implementation expectation:
- Centralized guard function (e.g., `assertActionAllowed(env, action, role, orgPolicyFlags)`).
- Applies to both synchronous endpoints and background job starters.

### 2.2 Policy-Dependent (Default OFF) — Implement as Org/Env Policy Flags
These should be boolean org/env settings with defaults:
- Allow restore/rollback in dev (default false)
- Allow manual snapshot in staging (default false)

Implementation expectation:
- Stored in DB (org_settings or env_settings), returned to UI.
- Enforced server-side + reflected in UI.

### 2.3 Feature Flags / Plan Gating (Product tier)
Decide if these should be monetized via plan tiers. Provide recommendation and implement gating if desired:
- Scheduled deployments (already mentioned)
- Scheduled backups
- Rerun/cancel deployment (maybe)
- Snapshot retention / count limits
- Backup incremental vs forced full
- Diff/compare availability

Deliverable:
- A recommendation table: **Capability → Policy? → Plan gate? → Default?**
- If plan gating exists in code, wire these capabilities into the existing plan-check system.

---

## Step 3 — Verify Correctness (What to check)
For each action:
1. **UI gating**
   - Buttons disabled/hidden correctly based on env type + role + policy flags + plan.
2. **API enforcement**
   - Calling the endpoint directly must still be rejected with 403/422, with a clear error code.
3. **Job enforcement**
   - Background jobs must not start if disallowed.
4. **Consistency**
   - Same logic reused everywhere (no duplicated per-page rules).

Deliverable:
- A checklist with pass/fail per action per environment.
- Identify mismatches between UI and backend.

---

## Step 4 — Implement Fixes (Required)
### 4.1 Centralize guard rules
Create a single source of truth (backend first):
- `canPerformAction({ envType, role, action, orgPolicyFlags, plan }) -> boolean`
- `assertCanPerformAction(...)` throws a typed error `{ code, message }`

### 4.2 Apply guards in backend
- All relevant endpoints must call `assertCanPerformAction` early.
- Any job enqueue path must call the guard before enqueue.

### 4.3 Reflect in UI
- UI should call a “capabilities” endpoint or compute locally from envType + role + returned flags.
- The UI must mirror backend rules, but backend is authoritative.

---

## Step 5 — Tests (Required)
Add tests at minimum:
- Backend unit tests: guard function matrix tests
- Backend integration tests: endpoints reject disallowed calls
- Optional UI tests: smoke test that buttons are hidden/disabled for staging/prod actions

Include explicit test vectors:
- dev/editor allowed backup, staging/editor denied backup, prod/admin allowed deploy inbound, prod/editor denied deploy inbound, etc.

---

## Step 6 — Output
When done, provide:
1. A short summary of findings (what was wrong, where).
2. A list of code changes (files touched).
3. The final guard decision table (policy vs flag vs plan-gate).
4. How to manually verify in UI (3-5 quick steps).

---

## Non-Goals / Constraints
- Do not attempt to “secure” N8N itself; only enforce within WorkflowOps.
- Avoid duplicated logic; prefer centralized guard reuse.
- Default policy-dependent flags to OFF (safer).

