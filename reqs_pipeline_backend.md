# Dev → Staging Promotion (Full Flow — v1, Pipeline-Aware)

This document describes the **Dev → Staging promotion flow**, updated to align with the **v1 Pipeline UI requirements**.  
It assumes pipelines and stages are already defined and configured via the Pipeline UI.

---

## Core Invariants

- **Dev n8n is the source of change**
- **GitHub is the source of truth for state**
- **Promotion is directional**: Dev → Staging
- **Pipeline stage configuration controls behavior**
  - Gates
  - Approvals
  - Schedule
  - Policy flags
- Promotion always operates on **GitHub snapshots**, never unknown runtime state

---

## 1. Promotion Entry

### UI Entry Point
User initiates promotion from:
- Dev Environment page → **“Promote to…”**
- Workflow Details page (single-workflow variant)

### Required Context
- Selected **Pipeline**
- Active **Stage** = Dev → Staging

If no pipeline exists for Dev → Staging:
- Promotion is blocked
- User is instructed to configure a pipeline first

---

## 2. Automatic Dev Backup (Always First)

Before *any* checks or UI listing:

1. Export **all workflows** from Dev n8n runtime
2. Write to GitHub: /workflows/dev/*.json
3. Commit:
- Reason: “Auto backup before promotion”
- Metadata: actor, timestamp, environment
4. Save commit hash as: dev_snapshot_id

If this backup fails → **promotion stops immediately**

Purpose:
- Guarantees Dev GitHub == Dev runtime
- Ensures promotion source is deterministic

---

## 3. Establish Comparison Baseline (GitHub → GitHub)

Promotion comparison is strictly between GitHub snapshots:

- **Source snapshot**: `dev_snapshot_id`
- **Target snapshot**: latest known `staging_snapshot_id`

No runtime state is used for comparison.

---

## 4. Target Drift Detection (Stage Gate)

If the pipeline stage has **“Require clean drift before promotion”** enabled:

1. Export workflows from **Staging n8n runtime**
2. Compare with `staging_snapshot_id`

### If drift is detected:
- Stop promotion
- Show blocking error:
> “Staging has changes not tracked in GitHub.”

### User actions (exactly two):
1. **Sync Staging to GitHub** (recommended)
- Create new snapshot
- Update `staging_snapshot_id`
- Resume promotion
2. **Abort promotion**

No “ignore drift” option in v1.

---

## 5. Compute Dev vs Staging Differences

Compare:
- `/workflows/dev` @ `dev_snapshot_id`
- `/workflows/staging` @ `staging_snapshot_id`

Each workflow is classified as:

### Case A — Changed in Dev
- Dev JSON ≠ Staging JSON
- ✅ Eligible for promotion

### Case B — Changed in Staging only (Staging hotfix)
- Dev unchanged
- Staging modified independently
- ⚠️ Requires explicit decision (policy-controlled)

### Case C — Changed in both (Conflict)
- Dev and Staging both diverged
- ❌ Blocked in v1

---

## 6. Workflow Selection UI

### Default List
Shows only:
- **New in Dev**
- **Changed in Dev**

Each row shows:
- Workflow name
- Change type
- Enabled/disabled state in Dev
- Status in Staging

### Badges
- “Changed in Dev” — selectable
- “Staging hotfix” — selectable only if stage policy allows overwrite
- “Conflict” — not selectable; explanation shown

---

## 7. Hotfix & Conflict Policy Enforcement

Controlled by **Stage Policy Flags**.

### Staging Hotfix (Case B)

If **Allow overwriting target hotfixes = OFF**:
- Workflow cannot be selected
- Message:
> “This workflow was modified in Staging; overwrite not allowed by pipeline policy.”

If ON:
- User must explicitly confirm overwrite
- Action is recorded in audit log

---

### True Conflict (Case C)

Always blocked in v1:
- User must resolve manually in Dev
- Then retry promotion

---

## 8. Dependency Detection

After workflow selection:

1. Analyze selected workflows’ JSON
2. Detect referenced sub-workflows

If:
- Workflow A depends on Workflow B
- Workflow B differs between Dev and Staging
- Workflow B is not selected

Then:
- Show warning:
> “Workflow A depends on Workflow B, which differs in Staging.”
- Offer:
- “Also include Workflow B”
- “Proceed anyway” (if stage policy allows)

---

## 9. Credentials & Environment Placeholders

Governed by **Stage Policy Flags**.

### Credentials

For each selected workflow:
- If credential exists in Staging → OK
- If missing:
- If **Allow placeholder credentials = ON**:
 - Create placeholder credential
 - Mark incomplete
 - Warning shown
- If OFF:
 - Block promotion

### Enabled State Rule

- Default: **Preserve Dev enabled/disabled state**
- Exception:
- If placeholders were created:
 - Workflow is forced **disabled**
 - Reason shown in UI

---

## 10. Pre-flight Validation Summary

Driven by **Stage Gates**.

Per workflow:
- Change type
- Final enabled state
- Credential status
- Dependency warnings

Global:
- Drift resolved?
- Target environment health (if gate enabled)
- Risk threshold respected (if configured)

If any blocking gate fails:
- “Promote now” disabled

---

## 11. Approvals (If Required)

If **Require approval = ON** for this stage:

- Promotion becomes **“Request approval”**
- Approvers see:
- Workflow list
- Diffs
- Gate results
- Warnings

Approval result:
- Approved → proceed
- Rejected → promotion ends, reason recorded

---

## 12. Scheduling Enforcement

If **Schedule restriction** is configured:

- If current time is outside allowed window:
- Promotion blocked
- Message shown
- No auto-queueing in v1

---

## 13. Pre-Promotion Snapshot (Rollback Point)

Before writing anything:

1. Export Staging workflows
2. Commit to GitHub: staging_pre_promotion_snapshot_id
3. Reason: “Pre-promotion snapshot”

Failure → abort promotion

---

## 14. Execute Promotion

For each selected workflow:

1. Load JSON from `dev_snapshot_id`
2. Apply enabled/disabled transformation
3. Write to Staging via n8n API
4. Record success/failure

Partial success is allowed.

---

## 15. Post-Promotion Snapshot

After promotion completes:

1. Export Staging workflows
2. Commit: staging_post_promotion_snapshot_id
3. Reference `dev_snapshot_id` in commit metadata

GitHub is again the source of truth.

---

## 16. Result & Audit

### User sees:
- Workflow success/failure summary
- Final enabled states
- Placeholders created
- Links:
- View workflow in Staging
- View diff
- Rollback

### Audit record includes:
- Actor
- Pipeline ID
- Stage (Dev → Staging)
- Snapshot IDs
- Workflow decisions
- Gate results
- Overrides used

---

## One-Sentence Summary

Dev → Staging promotion snapshots Dev automatically, compares clean GitHub states, enforces pipeline-configured gates and policies, safely copies selected workflow JSON into Staging, and leaves a deterministic audit and rollback trail.

---

*This flow is reused verbatim for other stages by swapping the active pipeline stage and its configuration.*


