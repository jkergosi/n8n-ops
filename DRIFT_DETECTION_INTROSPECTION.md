# WorkflowOps Drift Detection: Complete Introspection Report

**Generated:** 2026-01-13
**Last Updated:** 2026-01-14 (Enhanced with comprehensive truth tables - Task T006)
**Scope:** UNTRACKED vs DRIFT_DETECTED status assignment, matching logic, and scheduler behavior

---

## 📋 Quick Navigation

### Core Documentation
1. **[Status Definitions](#1-where-statuses-are-defined-source-of-truth)** - Enum definitions and source of truth
2. **[Exact Assignment Rules](#2-exact-rules-that-set-untracked-vs-drift_detected)** - Code-backed logic for status assignment
3. **[Original Truth Table](#3-truth-table-untracked-vs-drift_detected-assignment)** - High-level status scenarios

### 🆕 Enhanced Documentation (Task T006)
- **[Section 3.1: Extended Truth Tables](#31-extended-truth-tables-with-semantic-clarifications)** - Comprehensive per-workflow and environment-level tables
  - Per-Workflow Status Truth Table (11 scenarios)
  - Environment-Level Drift Status Truth Table (7 scenarios)
  - Combined Scenario Truth Table (11 real-world cases)
  - **Two Meanings of "UNTRACKED"** - Critical semantic distinction
  - Common Confusion Scenarios - FAQ-style troubleshooting

- **[Section 3.2: Visual Decision Trees](#32-visual-decision-trees)** - ASCII flowcharts for status determination
  - Environment-Level Status Decision Tree
  - Per-Workflow Status Decision Tree
  - Auto-Link Decision Tree (During Sync)

- **[Section 10: Quick Reference](#10-quick-reference-status-cheat-sheets)** - Practical cheat sheets
  - Status Quick Lookup Tables
  - Status Transition Matrix
  - Diagnostic SQL Queries
  - Common Troubleshooting Scenarios

### Additional Sections
4. **[Matching/Identity Logic](#4-matching--identity-how-runtime-workflows-are-paired-to-canonical)** - How workflows are paired to canonical
5. **[Normalization](#5-normalization-and-ignored-fields)** - Ignored fields and hash computation
6. **[Scheduler Logic](#6-scheduler--selection-logic)** - When drift detection runs
7. **[Known Issues](#7-observed-weirdness-candidates-code-backed)** - Code-backed weirdness scenarios
8. **[Reproduction Guide](#8-minimal-reproduction-guide-repo-only)** - Step-by-step debugging
9. **[Summary](#9-summary-of-key-findings)** - Key findings and decision trees

---

## 🎯 Key Insights (Task T006 Additions)

### Critical Understanding: Two Meanings of "UNTRACKED"

1. **Per-Workflow UNTRACKED** (`workflow_env_map.status = 'untracked'`)
   - Workflow exists in n8n but has no canonical identity (`canonical_id` = NULL)
   - Appears in UI with orange badge
   - Requires linking action

2. **Environment-Level UNTRACKED** (`environments.drift_status = 'UNTRACKED'`)
   - **ZERO workflows are tracked/linked in the entire environment**
   - NOT "some workflows are untracked"
   - Common source of confusion!

### Most Common Confusion
> "My environment shows DRIFT_DETECTED but I have 99 untracked workflows!"

**Explanation:** If even ONE workflow is tracked/linked, the environment status will be:
- `DRIFT_DETECTED` (if that 1 workflow has drift OR if other workflows aren't in Git)
- `IN_SYNC` (if that 1 workflow matches Git perfectly and no other workflows exist)

The environment only shows `UNTRACKED` when the tracked count is **exactly zero**.

---

## 1) Where Statuses Are Defined (Source of Truth)

### A. WorkflowMappingStatus (Database-Persisted, Per-Workflow Status)

**Location:** `app/schemas/canonical_workflow.py` (Lines 7-80)

**Symbol:** `WorkflowMappingStatus` (Enum)

**Definition:**
```python
class WorkflowMappingStatus(str, Enum):
    LINKED = "linked"
    IGNORED = "ignored"
    DELETED = "deleted"
    UNTRACKED = "untracked"
    MISSING = "missing"
```

**Documentation (Lines 13-26):**
> "UNTRACKED: Workflow exists in n8n but lacks a canonical mapping. Has an n8n_workflow_id but canonical_id is NULL. Requires manual linking or can be auto-linked if matching canonical workflow is found."

**Precedence Rules (Lines 33-53):**
1. DELETED - Highest precedence (soft-deleted)
2. IGNORED - User explicitly ignored
3. MISSING - Was mapped but disappeared from n8n
4. UNTRACKED - No canonical_id (NULL)
5. LINKED - Normal operational state (lowest precedence)

**Storage:** `workflow_env_map.status` column (TEXT type with CHECK constraint)

**Database Constraint:** Migration `94a957608da9_add_untracked_missing_status.py` (Lines 22-26):
```sql
op.create_check_constraint(
    'workflow_env_map_status_check',
    'workflow_env_map',
    "status IN ('linked', 'untracked', 'missing', 'ignored', 'deleted')"
)
```

---

### B. DriftStatus (Environment-Level Status)

**Location:** `app/services/drift_detection_service.py` (Lines 20-26)

**Symbol:** `DriftStatus` (Class with string constants)

**Definition:**
```python
class DriftStatus:
    """Drift status constants"""
    UNKNOWN = "UNKNOWN"
    IN_SYNC = "IN_SYNC"
    DRIFT_DETECTED = "DRIFT_DETECTED"
    UNTRACKED = "UNTRACKED"
    ERROR = "ERROR"
```

**Documentation:** None attached (only inline comment)

**Storage:** `environments.drift_status` column (TEXT type)

**Scope:** Environment-level aggregate status (not per-workflow)

---

### C. WorkflowEnvironmentStatus (Display-Only, Computed)

**Location:** `app/api/endpoints/workflow_matrix.py` (Lines 47-67)

**Symbol:** `WorkflowEnvironmentStatus` (Enum)

**Definition:**
```python
class WorkflowEnvironmentStatus(str, Enum):
    LINKED = "linked"
    UNTRACKED = "untracked"
    DRIFT = "drift"
    OUT_OF_DATE = "out_of_date"
```

**Documentation (Lines 50-61):**
> "Display status of a canonical workflow in a specific environment. These statuses are computed for the workflow matrix UI based on: 1. The persisted mapping status (from WorkflowMappingStatus with precedence rules) 2. Content hash comparisons to detect drift/out-of-date conditions"

**Scope:** UI display only (never persisted, computed at query time)

---

## 2) Exact Rules That Set UNTRACKED vs DRIFT_DETECTED

### A. Environment-Level UNTRACKED Status Assignment

**Location:** `app/services/drift_detection_service.py` (Lines 282-296)

**Function:** `detect_drift()`

**Exact Condition (Lines 290-296):**

```python
# Check if any workflows are tracked/linked for this environment
tracked_workflows = await db_service.get_workflows_from_canonical(
    tenant_id=tenant_id,
    environment_id=environment_id,
    include_deleted=False,
    include_ignored=False
)

# If no workflows are tracked, set status to untracked
if len(tracked_workflows) == 0:
    drift_status = DriftStatus.UNTRACKED
else:
    # Determine overall status based on drift detection
    has_drift = with_drift_count > 0 or not_in_git_count > 0
    drift_status = DriftStatus.DRIFT_DETECTED if has_drift else DriftStatus.IN_SYNC
```

**CRITICAL INSIGHT:** Environment-level `UNTRACKED` means **zero workflows are tracked/linked**, not "some workflows are untracked". This is the count of workflows with `canonical_id IS NOT NULL` in `workflow_env_map`.

**Inputs:**
- `tracked_workflows`: Result of `get_workflows_from_canonical()` which queries `workflow_env_map` WHERE `canonical_id IS NOT NULL` AND `status NOT IN ('deleted', 'ignored')`
- `with_drift_count`: Count of workflows where runtime differs from Git
- `not_in_git_count`: Count of workflows in runtime but not in Git

**Context Surrounding Lines 282-296:**
```python
280:                        in_sync_count += 1
281:
282:            # Check if any workflows are tracked/linked for this environment
283:            tracked_workflows = await db_service.get_workflows_from_canonical(
284:                tenant_id=tenant_id,
285:                environment_id=environment_id,
286:                include_deleted=False,
287:                include_ignored=False
288:            )
289:
290:            # If no workflows are tracked, set status to untracked
291:            if len(tracked_workflows) == 0:
292:                drift_status = DriftStatus.UNTRACKED
293:            else:
294:                # Determine overall status based on drift detection
295:                has_drift = with_drift_count > 0 or not_in_git_count > 0
296:                drift_status = DriftStatus.DRIFT_DETECTED if has_drift else DriftStatus.IN_SYNC
297:
298:            # Sort affected workflows: drift first, then not in git
299:            affected_workflows.sort(key=lambda x: (
300:                0 if x.get("hasDrift") else (1 if x.get("notInGit") else 2),
301:                x.get("name", "").lower()
302:            ))
```

---

### B. Per-Workflow UNTRACKED Status Assignment

**Location:** `app/services/canonical_workflow_service.py` (Lines 220-222)

**Function:** `compute_workflow_mapping_status()`

**Exact Condition (Lines 220-222):**

```python
# Precedence 4: UNTRACKED if no canonical_id but exists in n8n
if not canonical_id and is_present_in_n8n:
    return WorkflowMappingStatus.UNTRACKED
```

**Inputs:**
- `canonical_id`: The canonical workflow ID (None if not linked)
- `n8n_workflow_id`: The n8n workflow ID (None if not synced)
- `is_present_in_n8n`: Boolean - whether workflow currently exists in n8n environment
- `is_deleted`: Boolean - whether the mapping/workflow is soft-deleted
- `is_ignored`: Boolean - whether the workflow is explicitly marked as ignored

**Context Surrounding Lines 220-222:**
```python
210:    # Precedence 2: IGNORED overrides operational states
211:    if is_ignored:
212:        return WorkflowMappingStatus.IGNORED
213:
214:    # Precedence 3: MISSING if workflow was mapped but disappeared from n8n
215:    # A workflow is considered "was mapped" if it has n8n_workflow_id
216:    if not is_present_in_n8n and n8n_workflow_id:
217:        return WorkflowMappingStatus.MISSING
218:
219:    # Precedence 4: UNTRACKED if no canonical_id but exists in n8n
220:    if not canonical_id and is_present_in_n8n:
221:        return WorkflowMappingStatus.UNTRACKED
222:
223:    # Precedence 5: LINKED as default operational state
224:    # This requires both canonical_id and is_present_in_n8n
225:    if canonical_id and is_present_in_n8n:
226:        return WorkflowMappingStatus.LINKED
227:
228:    # Edge case: if we get here, the mapping is in an inconsistent state
229:    # This could happen during onboarding or partial sync operations
230:    # Default to UNTRACKED as the safest fallback
```

---

### C. Creation of UNTRACKED Workflows

**Location:** `app/services/canonical_env_sync_service.py` (Lines 451-464)

**Function:** `_process_workflow_batch()`

**Exact Condition (Lines 451-464):**

```python
else:
    # Untracked - create mapping row with canonical_id=NULL
    await CanonicalEnvSyncService._create_untracked_mapping(
        tenant_id,
        environment_id,
        n8n_workflow_id,
        content_hash,
        workflow_data=workflow if is_dev else None,
        n8n_updated_at=n8n_updated_at
    )
    batch_results["synced"] += 1
    batch_results["untracked"] += 1
    # Track newly created (untracked) workflows
    batch_results["created_workflow_ids"].append(n8n_workflow_id)
```

**Triggered When:** Auto-linking by hash fails (lines 424-429):
```python
# Try to auto-link by hash
canonical_id = await CanonicalEnvSyncService._try_auto_link_by_hash(
    tenant_id,
    environment_id,
    content_hash,
    n8n_workflow_id
)

if canonical_id:
    # Auto-linked [...]
else:
    # Untracked [...]
```

**Context Surrounding Lines 451-464:**
```python
441:                        tenant_id=tenant_id,
442:                        environment_id=environment_id,
443:                        canonical_id=canonical_id,
444:                        n8n_workflow_id=n8n_workflow_id,
445:                        content_hash=content_hash,
446:                        status=WorkflowMappingStatus.LINKED,
447:                        workflow_data=workflow if is_dev else None,
448:                        n8n_updated_at=n8n_updated_at
449:                    )
450:                    batch_results["synced"] += 1
451:                    batch_results["linked"] += 1
452:                else:
453:                    # Untracked - create mapping row with canonical_id=NULL
454:                    await CanonicalEnvSyncService._create_untracked_mapping(
455:                        tenant_id,
456:                        environment_id,
457:                        n8n_workflow_id,
458:                        content_hash,
459:                        workflow_data=workflow if is_dev else None,
460:                        n8n_updated_at=n8n_updated_at
461:                    )
462:                    batch_results["synced"] += 1
463:                    batch_results["untracked"] += 1
464:                    # Track newly created (untracked) workflows
465:                    batch_results["created_workflow_ids"].append(n8n_workflow_id)
466:
467:            except Exception as e:
468:                error_msg = f"Error processing workflow {workflow.get('id', 'unknown')}: {str(e)}"
469:                logger.error(error_msg)
470:                batch_results["errors"].append(error_msg)
```

---

## 3) Truth Table: UNTRACKED vs DRIFT_DETECTED Assignment

| Canonical Exists (Git/DB) | Runtime Exists (n8n) | Content Match | Canonical Mapping | Per-Workflow Status | Env-Level Status | Notes |
|---------------------------|---------------------|---------------|-------------------|---------------------|------------------|-------|
| ✅ Yes (Git) | ✅ Yes | ✅ Match | ✅ Linked | `LINKED` | `IN_SYNC` (if all match) | Normal state |
| ✅ Yes (Git) | ✅ Yes | ❌ Differ | ✅ Linked | `LINKED` | `DRIFT_DETECTED` | Runtime has changes not in Git |
| ✅ Yes (Git) | ❌ Missing | N/A | ✅ Was Linked | `MISSING` | `DRIFT_DETECTED` | Workflow disappeared from n8n |
| ❌ No (Git) | ✅ Yes | N/A | ❌ NULL canonical_id | `UNTRACKED` | `DRIFT_DETECTED`* or `UNTRACKED`** | *if other workflows tracked, **if zero workflows tracked |
| ❌ No (Git) | ❌ No | N/A | N/A | (No row) | `IN_SYNC` (if no other drift) | Workflow doesn't exist anywhere |
| ✅ Yes (DB mapping) | ✅ Yes | N/A | ❌ Import with new ID | `UNTRACKED` (new row) | `DRIFT_DETECTED` | Promotion/import creates new runtime ID |
| ✅ Yes (Git) | ✅ Yes (renamed) | ❌ Name differs | ❌ Match fails | `UNTRACKED` (or old `MISSING`) | `DRIFT_DETECTED` | Rename breaks name-based matching |
| N/A | N/A | N/A | N/A | N/A | `UNKNOWN` | Git not configured |
| N/A | N/A | N/A | N/A | N/A | `ERROR` | Sync/detection failed |

**Key Insight:** `DRIFT_DETECTED` at environment level means "at least one workflow has drift OR is not in Git", NOT "some workflows are untracked". Environment-level `UNTRACKED` only occurs when **zero workflows are tracked/linked**.

---

## 3.1) Extended Truth Tables with Semantic Clarifications

### A. Comprehensive Per-Workflow Status Truth Table

This table shows how **individual workflow status** is determined in `workflow_env_map.status`:

| # | Canonical ID | n8n Workflow ID | Present in n8n | Is Deleted | Is Ignored | Computed Status | Rationale |
|---|--------------|-----------------|----------------|------------|------------|-----------------|-----------|
| 1 | NULL | NULL | ❌ No | ❌ No | ❌ No | (No row exists) | Workflow doesn't exist in system |
| 2 | NULL | `wf_123` | ✅ Yes | ❌ No | ❌ No | **UNTRACKED** | Exists in n8n but not linked to canonical |
| 3 | NULL | `wf_123` | ❌ No | ❌ No | ❌ No | (Ephemeral) | Edge case: mapping exists but workflow gone |
| 4 | `can_abc` | NULL | ❌ No | ❌ No | ❌ No | (Inconsistent) | Edge case: canonical exists but no n8n ID |
| 5 | `can_abc` | `wf_123` | ✅ Yes | ❌ No | ❌ No | **LINKED** | Normal operational state |
| 6 | `can_abc` | `wf_123` | ❌ No | ❌ No | ❌ No | **MISSING** | Was mapped but disappeared from n8n |
| 7 | `can_abc` | `wf_123` | ✅ Yes | ❌ No | ✅ Yes | **IGNORED** | User explicitly ignored (overrides LINKED) |
| 8 | `can_abc` | `wf_123` | ❌ No | ❌ No | ✅ Yes | **IGNORED** | User explicitly ignored (overrides MISSING) |
| 9 | `can_abc` | `wf_123` | ✅ Yes | ✅ Yes | ❌ No | **DELETED** | Soft-deleted (highest precedence) |
| 10 | NULL | `wf_123` | ✅ Yes | ❌ No | ✅ Yes | **IGNORED** | Untracked but ignored |
| 11 | NULL | `wf_123` | ✅ Yes | ✅ Yes | ❌ No | **DELETED** | Deleted untracked workflow |

**Code Reference:** `app/services/canonical_workflow_service.py` lines 200-230 (`compute_workflow_mapping_status()`)

**Precedence Order (Highest to Lowest):**
1. DELETED - Soft-deleted flag overrides everything
2. IGNORED - User choice overrides operational states
3. MISSING - Was mapped (`n8n_workflow_id` exists) but disappeared from n8n
4. UNTRACKED - No `canonical_id` but exists in n8n
5. LINKED - Normal operational state

---

### B. Environment-Level Drift Status Truth Table

This table shows how **environment-level drift status** is determined in `environments.drift_status`:

| # | Git Configured | Tracked Workflows Count | Workflows with Drift | Not in Git Count | Computed Status | Displayed Meaning |
|---|----------------|------------------------|---------------------|------------------|-----------------|-------------------|
| 1 | ❌ No | N/A | N/A | N/A | **UNKNOWN** | Git not configured or PAT missing |
| 2 | ✅ Yes | 0 | N/A | N/A | **UNTRACKED** | Zero workflows are linked to canonical |
| 3 | ✅ Yes | > 0 | 0 | 0 | **IN_SYNC** | All tracked workflows match Git exactly |
| 4 | ✅ Yes | > 0 | > 0 | 0 | **DRIFT_DETECTED** | Some tracked workflows differ from Git |
| 5 | ✅ Yes | > 0 | 0 | > 0 | **DRIFT_DETECTED** | Some workflows not found in Git |
| 6 | ✅ Yes | > 0 | > 0 | > 0 | **DRIFT_DETECTED** | Both drift and missing workflows |
| 7 | ✅ Yes (error) | N/A | N/A | N/A | **ERROR** | Sync or detection failed |

**Code Reference:** `app/services/drift_detection_service.py` lines 282-296 (`detect_drift()`)

**Critical Logic (Lines 290-296):**
```python
# If no workflows are tracked, set status to untracked
if len(tracked_workflows) == 0:
    drift_status = DriftStatus.UNTRACKED
else:
    # Determine overall status based on drift detection
    has_drift = with_drift_count > 0 or not_in_git_count > 0
    drift_status = DriftStatus.DRIFT_DETECTED if has_drift else DriftStatus.IN_SYNC
```

**Key Insight:** Environment status `UNTRACKED` means **"zero workflows are tracked/linked"**, NOT "some workflows are untracked". This is a common source of confusion.

---

### C. Combined Scenario Truth Table (Per-Workflow + Environment)

This table shows realistic scenarios combining both levels:

| Scenario | Canonical in Git | Runtime in n8n | Content Match | Canonical Mapping | Per-Workflow Status | Env Status | Notes |
|----------|------------------|----------------|---------------|-------------------|---------------------|------------|-------|
| Fresh environment | ❌ No | ✅ Yes (100 workflows) | N/A | ❌ NULL | `UNTRACKED` (all) | `UNTRACKED` | Zero workflows linked yet |
| After first link | ✅ Yes | ✅ Yes | ✅ Match | ✅ Linked (1 wf) | `LINKED` (1), `UNTRACKED` (99) | `DRIFT_DETECTED` | 1 tracked, 99 not in Git |
| All synced, in sync | ✅ Yes (all) | ✅ Yes (all) | ✅ Match (all) | ✅ Linked (all) | `LINKED` (all) | `IN_SYNC` | Normal operational state |
| Developer made changes | ✅ Yes | ✅ Yes | ❌ Differ | ✅ Linked | `LINKED` | `DRIFT_DETECTED` | Runtime ahead of Git |
| Workflow renamed in n8n | ✅ Yes (old name) | ✅ Yes (new name) | ❌ Name differs | ✅ Linked (by mapping) | `LINKED` | `DRIFT_DETECTED`* | *False positive in drift report |
| Promotion creates new ID | ✅ Yes (Git) | ✅ Yes (new ID) | ✅ Match | ❌ NULL (new row) | `UNTRACKED` (new), `MISSING` (old) | `DRIFT_DETECTED` | Auto-link conflict (#1) |
| Workflow deleted | ✅ Yes (Git) | ❌ Missing | N/A | ✅ Was Linked | `MISSING` | `DRIFT_DETECTED` | Disappeared from n8n |
| User ignores workflow | ✅ Yes | ✅ Yes | N/A | ✅ Linked + Ignored | `IGNORED` | N/A (excluded from counts) | Explicitly ignored |
| Soft-deleted | ✅ Yes | ✅ Yes | N/A | ✅ Linked + Deleted | `DELETED` | N/A (excluded from counts) | Soft-deleted |
| Git not configured | N/A | ✅ Yes | N/A | ❌ NULL | `UNTRACKED` | `UNKNOWN` | Cannot determine drift |
| Sync error | ✅ Yes | ✅ Yes | N/A | ✅ Linked | `LINKED` | `ERROR` | Detection failed |

---

### D. Semantic Clarifications: Two Meanings of "UNTRACKED"

#### Per-Workflow UNTRACKED (`workflow_env_map.status = 'untracked'`)
**Meaning:** Workflow exists in n8n runtime but has no canonical identity mapping.

**Characteristics:**
- `canonical_id` column is NULL
- `n8n_workflow_id` column is populated
- Workflow is physically present in n8n environment
- Can be auto-linked if hash matches exactly one canonical workflow
- Requires manual linking if auto-link fails

**User Impact:**
- Workflow appears in workflow matrix with orange "untracked" badge
- Cannot be promoted to other environments
- Not included in drift detection comparisons
- Considered a "warning" state requiring attention

**Resolution Actions:**
1. Auto-link by hash (if exact match found)
2. Manual link via API/UI
3. Mark as ignored (if intentional)
4. Delete if no longer needed

---

#### Environment-Level UNTRACKED (`environments.drift_status = 'UNTRACKED'`)
**Meaning:** Environment has ZERO workflows linked to canonical identity.

**Characteristics:**
- Count of tracked workflows (`canonical_id IS NOT NULL`) equals zero
- Environment may have many workflows, but all are untracked
- Git is configured (otherwise status would be `UNKNOWN`)
- This is typically an onboarding or initial state

**User Impact:**
- Environment badge shows "untracked" status
- Indicates environment hasn't been fully onboarded yet
- Drift detection cannot run (no canonical baseline)
- Promotions from this environment will fail

**Resolution Actions:**
1. Run canonical sync to auto-link workflows by hash
2. Manually link at least one workflow
3. Once any workflow is linked, status changes to `IN_SYNC` or `DRIFT_DETECTED`

---

### E. Common Confusion Scenarios

#### Confusion #1: "Environment shows DRIFT_DETECTED but I see mostly untracked workflows"
**Explanation:** Environment-level `DRIFT_DETECTED` is set when:
- At least ONE workflow is tracked/linked (not zero)
- That tracked workflow has drift OR workflows exist that aren't in Git

**Example:**
- 100 workflows in n8n
- 1 workflow linked to canonical (tracked)
- 99 workflows untracked
- Environment status: `DRIFT_DETECTED` (because 1 tracked exists and 99 "not in Git")

---

#### Confusion #2: "I have untracked workflows but environment shows IN_SYNC"
**This scenario is IMPOSSIBLE.**

**Why:** Untracked workflows (per-workflow status) don't affect environment drift status because:
- They have `canonical_id IS NULL`
- Drift detection only considers tracked workflows (lines 283-288)
- Untracked workflows are excluded from `tracked_workflows` count

**What you're probably seeing:**
- Workflows marked as `IGNORED` or `DELETED` (excluded from drift)
- Workflows that haven't been synced yet (no mapping row)
- UI caching issue

---

#### Confusion #3: "Environment shows UNTRACKED but I have linked workflows"
**This scenario should NOT happen but can occur due to:**
1. Database inconsistency (mapping row exists but `canonical_id` is NULL)
2. Scheduler hasn't run yet after recent linking
3. Race condition during concurrent sync operations

**Resolution:**
- Trigger manual drift detection: `POST /api/environments/{id}/drift/detect`
- Check database: `SELECT COUNT(*) FROM workflow_env_map WHERE canonical_id IS NOT NULL`
- If count > 0 but status is `UNTRACKED`, this is a bug

---

## 3.2) Visual Decision Trees

### A. Environment-Level Status Decision Tree

```
┌─────────────────────────────────────────────────────────────────┐
│ START: Determine Environment Drift Status                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │ Is Git configured?     │
            │ (git_repo_url + PAT)   │
            └──┬─────────────────┬───┘
               │ No              │ Yes
               ▼                 ▼
        ┌──────────┐    ┌────────────────────────────┐
        │ UNKNOWN  │    │ Count tracked workflows:   │
        └──────────┘    │ SELECT COUNT(*) WHERE      │
                        │ canonical_id IS NOT NULL   │
                        │ AND status NOT IN          │
                        │ ('deleted', 'ignored')     │
                        └──┬─────────────────────┬───┘
                           │ Count = 0           │ Count > 0
                           ▼                     ▼
                    ┌─────────────┐    ┌────────────────────────┐
                    │  UNTRACKED  │    │ Compare Git vs Runtime │
                    │             │    │ for tracked workflows  │
                    │ (Zero       │    └──┬────────────────┬────┘
                    │  workflows  │       │                │
                    │  linked)    │       │                │
                    └─────────────┘       ▼                ▼
                                   ┌────────────┐  ┌──────────────┐
                                   │ with_drift │  │ not_in_git   │
                                   │ count > 0? │  │ count > 0?   │
                                   └──┬─────┬───┘  └──┬───────┬───┘
                                      │ Yes │         │ Yes   │ No
                                      ▼     │         ▼       │
                            ┌────────────────▼─────────┐      │
                            │  DRIFT_DETECTED          │      │
                            │                          │      │
                            │ (At least one tracked    │      │
                            │  workflow differs from   │      │
                            │  Git OR not in Git)      │      │
                            └──────────────────────────┘      │
                                                               ▼
                                                        ┌─────────┐
                                                        │ IN_SYNC │
                                                        │         │
                                                        │ (All    │
                                                        │  tracked│
                                                        │  match) │
                                                        └─────────┘
```

**Code Reference:** `app/services/drift_detection_service.py` lines 282-296

---

### B. Per-Workflow Status Decision Tree

```
┌─────────────────────────────────────────────────────────────────┐
│ START: Compute Workflow Mapping Status                         │
│ Input: canonical_id, n8n_workflow_id, is_present_in_n8n,      │
│        is_deleted, is_ignored                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │ Precedence 1:          │
            │ is_deleted == true?    │
            └──┬─────────────────┬───┘
               │ Yes             │ No
               ▼                 ▼
        ┌──────────┐    ┌────────────────────┐
        │ DELETED  │    │ Precedence 2:      │
        │          │    │ is_ignored == true?│
        │ (Highest │    └──┬──────────────┬──┘
        │  priority)│       │ Yes         │ No
        └──────────┘       ▼              ▼
                    ┌──────────┐    ┌───────────────────────────┐
                    │ IGNORED  │    │ Precedence 3:             │
                    │          │    │ !is_present_in_n8n AND    │
                    │          │    │ n8n_workflow_id exists?   │
                    └──────────┘    └──┬────────────────────┬───┘
                                       │ Yes                │ No
                                       ▼                    ▼
                                ┌──────────┐    ┌──────────────────────┐
                                │ MISSING  │    │ Precedence 4:        │
                                │          │    │ !canonical_id AND    │
                                │ (Was     │    │ is_present_in_n8n?   │
                                │  mapped  │    └──┬────────────────┬──┘
                                │  but     │       │ Yes            │ No
                                │  gone)   │       ▼                ▼
                                └──────────┘  ┌──────────┐  ┌──────────────┐
                                              │UNTRACKED │  │ Precedence 5:│
                                              │          │  │ canonical_id │
                                              │ (No      │  │ AND present? │
                                              │  mapping)│  └──┬───────┬───┘
                                              └──────────┘     │ Yes   │ No
                                                               ▼       ▼
                                                        ┌──────────┐ ┌────────┐
                                                        │ LINKED   │ │ Edge   │
                                                        │          │ │ case:  │
                                                        │ (Normal  │ │ return │
                                                        │  state)  │ │UNTRACK │
                                                        └──────────┘ └────────┘
```

**Code Reference:** `app/services/canonical_workflow_service.py` lines 200-230

---

### C. Auto-Link Decision Tree (During Sync)

```
┌─────────────────────────────────────────────────────────────────┐
│ START: New workflow found in n8n during sync                   │
│ Input: n8n_workflow_id, workflow content                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
            ┌────────────────────────────────┐
            │ Check existing mapping:        │
            │ workflow_env_map WHERE         │
            │ n8n_workflow_id = ?            │
            └──┬────────────────────────┬────┘
               │ Found                  │ Not Found
               ▼                        ▼
        ┌──────────────┐    ┌──────────────────────────┐
        │ Update       │    │ Compute content_hash     │
        │ existing     │    │ from normalized workflow │
        │ mapping      │    └──┬───────────────────────┘
        └──────────────┘       │
                               ▼
                    ┌──────────────────────────────┐
                    │ Try auto-link by hash:       │
                    │ Find canonical workflows     │
                    │ WHERE git_content_hash = ?   │
                    └──┬────────────────────────┬──┘
                       │ Exactly 1 match        │ 0 or 2+ matches
                       ▼                        ▼
            ┌──────────────────────┐    ┌─────────────────┐
            │ Check conflict:      │    │ Cannot auto-link│
            │ Is this canonical_id │    │ (no unique      │
            │ already linked to    │    │  match)         │
            │ different n8n ID?    │    │                 │
            └──┬────────────────┬──┘    │ ▼               │
               │ No conflict    │ Has   │ Create UNTRACKED│
               │                │ conflict mapping       │
               ▼                ▼       │                 │
        ┌──────────┐    ┌──────────────▼─────────────────┴──┐
        │ Create   │    │ Create UNTRACKED mapping:          │
        │ LINKED   │    │ - canonical_id = NULL              │
        │ mapping  │    │ - n8n_workflow_id = new ID         │
        │          │    │ - status = 'untracked'             │
        │          │    │ - env_content_hash = computed hash │
        └──────────┘    └────────────────────────────────────┘
```

**Code Reference:** `app/services/canonical_env_sync_service.py` lines 356-464

**Key Points:**
1. **Existing mapping takes precedence** - Database lookup happens first (line 356)
2. **Hash-based auto-link only for new workflows** - No existing mapping (lines 424-429)
3. **Conflict detection prevents duplicate links** - One canonical → one n8n ID per env (lines 541-549)
4. **Fallback to UNTRACKED** - When auto-link fails, create untracked mapping (lines 453-465)

---

## 4) Matching / Identity: How Runtime Workflows Are Paired to Canonical

### A. Matching Key Hierarchy (In Order of Precedence)

#### 1. Database Mapping (Highest Priority)

**Location:** `app/services/canonical_env_sync_service.py` (Lines 356-361)

**Key:** `(tenant_id, environment_id, n8n_workflow_id)` - Primary key lookup

**Code:**
```python
# Check if this n8n workflow is already mapped
existing_mapping = await CanonicalEnvSyncService._get_mapping_by_n8n_id(
    tenant_id,
    environment_id,
    n8n_workflow_id
)
```

**Field Source:** `n8n_workflow_id` from n8n API payload (runtime)

**Stability:** Unstable across export/import or promotion (new ID generated)

**Why Used:** Existing mappings take precedence to preserve user linking decisions

---

#### 2. Content Hash Auto-Linking (Fallback for New Workflows)

**Location:** `app/services/canonical_env_sync_service.py` (Lines 495-554)

**Key:** `env_content_hash` matched against `git_content_hash`

**Function:** `_try_auto_link_by_hash()`

**Exact Matching Logic (Lines 512-551):**
```python
# Find canonical workflows with matching Git content hash
git_state_response = (
    db_service.client.table("canonical_workflow_git_state")
    .select("canonical_id")
    .eq("tenant_id", tenant_id)
    .eq("environment_id", environment_id)
    .eq("git_content_hash", content_hash)
    .execute()
)

matching_canonical_ids = [row["canonical_id"] for row in (git_state_response.data or [])]

# Only auto-link if exactly one match
if len(matching_canonical_ids) != 1:
    return None

canonical_id = matching_canonical_ids[0]

# Check if this canonical_id is already linked to a different n8n_workflow_id in same environment
existing_mapping_response = (
    db_service.client.table("workflow_env_map")
    .select("n8n_workflow_id")
    .eq("tenant_id", tenant_id)
    .eq("environment_id", environment_id)
    .eq("canonical_id", canonical_id)
    .neq("status", "missing")
    .execute()
)

for mapping in (existing_mapping_response.data or []):
    existing_n8n_id = mapping.get("n8n_workflow_id")
    if existing_n8n_id and existing_n8n_id != n8n_workflow_id:
        # Conflict: canonical_id already linked to different n8n_workflow_id
        logger.warning(
            f"Cannot auto-link {n8n_workflow_id} to canonical {canonical_id}: "
            f"already linked to {existing_n8n_id}"
        )
        return None

return canonical_id
```

**Field Source:**
- `env_content_hash`: SHA256 of normalized workflow from n8n (runtime)
- `git_content_hash`: SHA256 of normalized workflow from Git (canonical)

**Stability:** Stable across rename but breaks on any content change

**Requirements for Auto-Link:**
- Exactly 1 canonical workflow with matching hash
- Canonical not already linked to different n8n workflow
- Hash computed using `compute_workflow_hash()` with normalization

**Context Surrounding Lines 495-554:**
```python
485:                .eq("environment_id", environment_id)
486:                .eq("n8n_workflow_id", n8n_workflow_id)
487:                .single()
488:                .execute()
489:            )
490:            return response.data if response.data else None
491:        except Exception:
492:            return None
493:
494:    @staticmethod
495:    async def _try_auto_link_by_hash(
496:        tenant_id: str,
497:        environment_id: str,
498:        content_hash: str,
499:        n8n_workflow_id: str
500:    ) -> Optional[str]:
501:        """
502:        Try to auto-link n8n workflow to canonical workflow by content hash.
503:
504:        Only links if:
505:        - Hash matches exactly
506:        - Match is unique (one canonical workflow with this hash)
507:        - canonical_id is not already linked to a different n8n_workflow_id in same environment
508:
509:        Returns canonical_id if linked, None otherwise.
510:        """
511:        try:
512:            # Find canonical workflows with matching Git content hash
513:            git_state_response = (
514:                db_service.client.table("canonical_workflow_git_state")
515:                .select("canonical_id")
516:                .eq("tenant_id", tenant_id)
517:                .eq("environment_id", environment_id)
518:                .eq("git_content_hash", content_hash)
519:                .execute()
520:            )
521:
522:            matching_canonical_ids = [row["canonical_id"] for row in (git_state_response.data or [])]
523:
524:            # Only auto-link if exactly one match
525:            if len(matching_canonical_ids) != 1:
526:                return None
527:
528:            canonical_id = matching_canonical_ids[0]
529:
530:            # Check if this canonical_id is already linked to a different n8n_workflow_id in same environment
531:            existing_mapping_response = (
532:                db_service.client.table("workflow_env_map")
533:                .select("n8n_workflow_id")
534:                .eq("tenant_id", tenant_id)
535:                .eq("environment_id", environment_id)
536:                .eq("canonical_id", canonical_id)
537:                .neq("status", "missing")
538:                .execute()
539:            )
540:
541:            for mapping in (existing_mapping_response.data or []):
542:                existing_n8n_id = mapping.get("n8n_workflow_id")
543:                if existing_n8n_id and existing_n8n_id != n8n_workflow_id:
544:                    # Conflict: canonical_id already linked to different n8n_workflow_id
545:                    logger.warning(
546:                        f"Cannot auto-link {n8n_workflow_id} to canonical {canonical_id}: "
547:                        f"already linked to {existing_n8n_id}"
548:                    )
549:                    return None
550:
551:            return canonical_id
552:        except Exception as e:
553:            logger.warning(f"Error in auto-link by hash: {str(e)}")
554:            return None
```

---

#### 3. Name-Based Matching (Drift Detection Only)

**Location:** `app/services/drift_detection_service.py` (Lines 223-241)

**Key:** Workflow `name` field

**Code:**
```python
# Create map of git workflows by name
git_by_name = {}
for wf_id, gw in git_workflows_map.items():
    name = gw.get("name", "")
    if name:
        git_by_name[name] = gw

# Compare each runtime workflow
for runtime_wf in runtime_workflows:
    wf_name = runtime_wf.get("name", "")
    wf_id = runtime_wf.get("id", "")
    active = runtime_wf.get("active", False)

    git_entry = git_by_name.get(wf_name)

    if git_entry is None:
        # Not in Git
        not_in_git_count += 1
```

**Field Source:** `name` field from n8n API and Git JSON files

**Stability:** Breaks on rename

**Context:** Used ONLY for drift detection comparison, NOT for canonical mapping

---

### B. Tables Used for Matching

#### workflow_env_map
- **Primary Key:** `(tenant_id, environment_id, n8n_workflow_id)`
- **Key Column for Linking:** `canonical_id` (NULL for UNTRACKED)
- **Purpose:** Maps runtime workflows to canonical identity

#### canonical_workflow_git_state
- **Primary Key:** `(tenant_id, environment_id, canonical_id)`
- **Key Column for Auto-Link:** `git_content_hash`
- **Purpose:** Stores Git-sourced workflow state per environment

#### canonical_workflows
- **Primary Key:** `(tenant_id, canonical_id)`
- **Purpose:** Stores canonical workflow identity (cross-environment)

---

## 5) Normalization and Ignored Fields

### A. Normalization Function

**Location:** `app/services/promotion_service.py` (Lines 90-161)

**Function:** `normalize_workflow_for_comparison()`

**Method:** Deep copy → Remove excluded fields → Sort nodes

---

### B. Workflow-Level Ignored Fields

**From diff_service.py (Lines 71-83):**
```python
IGNORED_FIELDS: Set[str] = {
    "id",
    "createdAt",
    "updatedAt",
    "versionId",
    "meta",
    "staticData",
    "triggerCount",
    "shared",
    "homeProject",
    "sharedWithProjects",
    "_comment"  # Added by our GitHub sync
}
```

**From promotion_service.py (Lines 99-111):**
```python
exclude_fields = [
    'id', 'createdAt', 'updatedAt', 'versionId',
    'triggerCount', 'staticData', 'meta', 'hash',
    'executionOrder', 'homeProject', 'sharedWithProjects',
    # GitHub/sync metadata
    '_comment', 'pinData',
    # Additional runtime fields
    'active',  # Active state may differ between environments
    # Tags have different IDs per environment
    'tags', 'tagIds',
    # Sharing/permission info differs
    'shared', 'scopes', 'usedCredentials',
]
```

**Removal:** Non-recursive (only top-level)

---

### C. Node-Level Ignored Fields

**From diff_service.py (Lines 86-90):**
```python
IGNORED_NODE_FIELDS: Set[str] = {
    "id",
    "webhookId",
    "notesInFlow"
}
```

**From promotion_service.py (Lines 133-140):**
```python
ui_fields = [
    'position', 'positionAbsolute', 'selected', 'selectedNodes',
    'executionData', 'typeVersion', 'onError', 'id',
    'webhookId', 'extendsCredential', 'notesInFlow',
]
```

**Removal:** Recursive (per-node)

---

### D. Settings-Level Ignored Fields

**From promotion_service.py (Lines 117-128):**
```python
settings_exclude = [
    'executionOrder', 'saveDataErrorExecution', 'saveDataSuccessExecution',
    'callerPolicy', 'timezone', 'saveManualExecutions',
    # n8n settings where null and false are semantically equivalent
    'availableInMCP',
]
```

---

### E. Credentials Normalization

**Location:** `app/services/promotion_service.py` (Lines 143-151)

**Code:**
```python
# Normalize credentials - only compare by name, not ID
if 'credentials' in node and isinstance(node['credentials'], dict):
    normalized_creds = {}
    for cred_type, cred_ref in node['credentials'].items():
        if isinstance(cred_ref, dict):
            # Keep only name for comparison (ID differs between envs)
            normalized_creds[cred_type] = {'name': cred_ref.get('name')}
        else:
            normalized_creds[cred_type] = cred_ref
    node['credentials'] = normalized_creds
```

**Key:** Credential IDs are stripped; only name is compared

---

### F. Comparison Method

**From canonical_workflow_service.py (Lines 101-103):**
```python
normalized = normalize_workflow_for_comparison(workflow)
json_str = json.dumps(normalized, sort_keys=True)
content_hash = hashlib.sha256(json_str.encode()).hexdigest()
```

**Method:**
1. Normalize workflow (remove ignored fields)
2. JSON stringify with `sort_keys=True` (deterministic order)
3. SHA256 hash

**Order Sensitivity:**
- Object keys: NOT sensitive (due to `sort_keys=True`)
- Array order: SENSITIVE unless explicitly sorted
- Nodes: Sorted by name (line 154: `sorted(normalized['nodes'], key=lambda n: n.get('name', ''))`)
- Connections: NOT sorted (relies on JSON key order)

---

## 6) Scheduler / Selection Logic

### A. Drift Detection Scheduler Query

**Location:** `app/services/drift_scheduler.py` (Lines 33-67)

**Function:** `_get_environments_for_drift_check()`

**Query (Lines 44-48):**
```python
response = db_service.client.table("environments").select(
    "id, tenant_id, n8n_name, git_repo_url, git_pat, n8n_type, environment_class"
).not_.is_("git_repo_url", "null").not_.is_("git_pat", "null").neq(
    "environment_class", "dev"
).execute()
```

**Filters:**
1. `git_repo_url IS NOT NULL`
2. `git_pat IS NOT NULL`
3. `environment_class != 'dev'`
4. Tenant has `drift_detection` feature enabled (lines 59-61)

**DEV Exclusion Reason (Lines 35-39):**
> "DEV environments are excluded because n8n is the source of truth for DEV, so there's no concept of 'drift' - changes in n8n ARE the canonical state."

**Context Surrounding Lines 33-67:**
```python
23:_retention_cleanup_task: Optional[asyncio.Task] = None
24:
25:# Configuration
26:DRIFT_CHECK_INTERVAL_SECONDS = 300  # 5 minutes
27:TTL_CHECK_INTERVAL_SECONDS = 60  # 1 minute
28:RETENTION_CLEANUP_INTERVAL_SECONDS = 86400  # 24 hours (daily)
29:
30:
31:async def _get_environments_for_drift_check() -> List[Dict[str, Any]]:
32:    """
33:    Get all non-DEV environments that have Git configured and belong to tenants
34:    with drift detection enabled.
35:
36:    DEV environments are excluded because n8n is the source of truth for DEV,
37:    so there's no concept of "drift" - changes in n8n ARE the canonical state.
38:    """
39:    try:
40:        # Get environments with Git configured, excluding DEV environments
41:        # DEV environments use n8n as source of truth, so drift detection doesn't apply
42:        response = db_service.client.table("environments").select(
43:            "id, tenant_id, n8n_name, git_repo_url, git_pat, n8n_type, environment_class"
44:        ).not_.is_("git_repo_url", "null").not_.is_("git_pat", "null").neq(
45:            "environment_class", "dev"
46:        ).execute()
47:
48:        environments = response.data or []
49:
50:        # Filter to environments where tenant has drift_detection feature
51:        eligible = []
52:        for env in environments:
53:            tenant_id = env.get("tenant_id")
54:            if not tenant_id:
55:                continue
56:
57:            can_use, _ = await feature_service.can_use_feature(tenant_id, "drift_detection")
58:            if can_use:
59:                eligible.append(env)
60:
61:        return eligible
62:
63:    except Exception as e:
64:        logger.error(f"Failed to get environments for drift check: {e}")
65:        return []
66:
67:
```

---

### B. Git Configuration Check

**Location:** `app/services/drift_detection_service.py` (Lines 105-123)

**Checks:**
```python
if not environment.get("git_repo_url") or not environment.get("git_pat"):
    summary = EnvironmentDriftSummary(...)
    if update_status:
        await self._update_environment_drift_status(
            tenant_id, environment_id, DriftStatus.UNKNOWN, summary
        )
    return summary
```

**Sets Status:** `UNKNOWN` if Git not configured

---

### C. Scheduler Intervals

**Location:** `app/services/drift_scheduler.py` (Lines 26-30)

```python
DRIFT_CHECK_INTERVAL_SECONDS = 300  # 5 minutes
TTL_CHECK_INTERVAL_SECONDS = 60  # 1 minute
RETENTION_CLEANUP_INTERVAL_SECONDS = 86400  # 24 hours (daily)
```

**Drift Detection:** Every 5 minutes
**TTL Check:** Every 1 minute
**Retention Cleanup:** Every 24 hours

---

### D. Ad-Hoc Drift Detection

**Location:** API endpoint exists but not shown in current files

**Inferred:** `POST /api/environments/{id}/drift/detect` (manual trigger)

---

## 7) Observed Weirdness Candidates (Code-Backed)

### #1: Promotion/Import Creates New Runtime IDs → UNTRACKED

**Code Path:** `canonical_env_sync_service.py` → `_process_workflow_batch()` → auto-link fails due to conflict

**Root Cause:**
- Promotion creates new `n8n_workflow_id` in target environment
- Old mapping points to old ID (now MISSING)
- New ID creates new mapping row
- Auto-link by hash fails because `canonical_id` already linked to old (missing) ID
- Result: New workflow marked UNTRACKED despite being same canonical workflow

**Code Evidence (Lines 541-549):**
```python
for mapping in (existing_mapping_response.data or []):
    existing_n8n_id = mapping.get("n8n_workflow_id")
    if existing_n8n_id and existing_n8n_id != n8n_workflow_id:
        # Conflict: canonical_id already linked to different n8n_workflow_id
        logger.warning(
            f"Cannot auto-link {n8n_workflow_id} to canonical {canonical_id}: "
            f"already linked to {existing_n8n_id}"
        )
        return None
```

**Exclusion Clause (Line 537):**
```python
.neq("status", "missing")
```

**BUT:** If old mapping is still "linked" (not yet marked missing), conflict still occurs!

---

### #2: Workflow Rename Breaks Drift Detection (But Not Canonical Mapping)

**Code Path:** `drift_detection_service.py` → name-based matching fails

**Root Cause:**
- Drift detection uses NAME to match runtime vs Git (lines 223-241)
- Canonical mapping uses `n8n_workflow_id` + hash (stable across rename)
- Renamed workflow appears as "not in Git" in drift report
- But canonical mapping remains LINKED

**Divergence:**
- `workflow_env_map.status` = "linked" (correct)
- `environments.drift_status` = "DRIFT_DETECTED" (false positive)
- Affected workflows show `notInGit: true` (incorrect)

---

### #3: Hash Collision Fallback Fails Without canonical_id

**Code Path:** `canonical_workflow_service.py` → `compute_workflow_hash()` → collision detected but no canonical_id

**Root Cause:**
- New workflow during sync doesn't have `canonical_id` yet (line 416)
- Hash collision detected (line 419)
- Fallback strategy requires `canonical_id` (line 119)
- Without it, returns original colliding hash (lines 141-147)
- Result: Two workflows with identical hashes, unresolvedconflict

**Code Evidence (Lines 419-421):**
```python
# Check for hash collision and track warning (before auto-link)
collision = _detect_hash_collision(workflow, content_hash, canonical_id=None)
if collision:
    batch_results["collision_warnings"].append(collision)
```

**Fallback Failure (Lines 141-147):**
```python
else:
    # No canonical_id provided - cannot apply fallback strategy
    logger.error(
        f"Hash collision detected but no canonical_id provided for fallback. "
        f"Hash: '{content_hash}'. Returning colliding hash (unresolved collision)."
    )
    # Return the colliding hash - collision remains unresolved
    return content_hash
```

---

### #4: Environment-Level UNTRACKED Misleading When Mixed State Exists

**Code Path:** `drift_detection_service.py` → lines 290-296

**Root Cause:**
- Environment has 100 workflows
- 99 are UNTRACKED (no canonical_id)
- 1 is LINKED (has canonical_id)
- `len(tracked_workflows) == 1` → Environment status = `DRIFT_DETECTED`
- User expects `UNTRACKED` because 99% are untracked

**Semantic Issue:** Status name "UNTRACKED" means "zero workflows tracked", not "most workflows untracked"

---

### #5: Short-Circuit Optimization Skips Missing→Reappeared Transitions

**Code Path:** `canonical_env_sync_service.py` → lines 369-376

**Root Cause:**
- Workflow temporarily disappears from n8n (status → MISSING)
- Workflow reappears with same `n8n_updated_at` timestamp
- Short-circuit skips processing (line 372)
- Status remains MISSING instead of transitioning to LINKED/UNTRACKED

**Code Evidence (Lines 369-376):**
```python
# Short-circuit optimization: skip if n8n_updated_at unchanged
# Only applies when workflow is not in "missing" state (reappeared workflows need full processing)
if existing_status != "missing" and existing_n8n_updated_at and n8n_updated_at:
    if _normalize_timestamp(existing_n8n_updated_at) == _normalize_timestamp(n8n_updated_at):
        # Workflow unchanged - skip processing
        batch_results["skipped"] += 1
        if existing_canonical_id:
            batch_results["linked"] += 1
        continue
```

**Protection Exists:** Line 370 checks `existing_status != "missing"` - BUT if timestamp truly unchanged, reappeared workflow won't be processed!

---

### #6: DEV vs Non-DEV Sync Asymmetry

**Code Path:** `canonical_env_sync_service.py` → lines 227-229, 405, 446, 458

**Root Cause:**
- DEV: Stores full `workflow_data` in `workflow_env_map`
- Non-DEV: Stores only `env_content_hash` (no workflow_data)
- Drift detection compares Git vs runtime using content
- If Git sync hasn't run, non-DEV has no Git state
- Auto-link by hash fails (no git_content_hash to compare)
- Result: All non-DEV workflows UNTRACKED until first Git sync

**Code Evidence (Lines 227-229):**
```python
# Determine environment class for sync behavior
env_class = environment.get("environment_class", "dev").lower()
is_dev = env_class == "dev"
```

**Conditional Storage (Line 405):**
```python
workflow_data=workflow if is_dev else None,  # Only store workflow_data in DEV
```

---

## 8) Minimal Reproduction Guide (Repo-Only)

### Scenario: Reproduce Unexpected UNTRACKED After Promotion

#### Step 1: Check Database State

**Inspect workflow_env_map:**
```sql
SELECT
  canonical_id,
  n8n_workflow_id,
  status,
  env_content_hash,
  last_env_sync_at,
  n8n_updated_at
FROM workflow_env_map
WHERE tenant_id = '<your-tenant-id>'
  AND environment_id = '<target-env-id>'
ORDER BY last_env_sync_at DESC;
```

**Look for:**
- Multiple rows with same `canonical_id` but different `n8n_workflow_id`
- Old row with status="missing", new row with status="untracked"
- Same `env_content_hash` on both rows

---

#### Step 2: Check Git State

**Inspect canonical_workflow_git_state:**
```sql
SELECT
  canonical_id,
  git_content_hash,
  last_repo_sync_at
FROM canonical_workflow_git_state
WHERE tenant_id = '<your-tenant-id>'
  AND environment_id = '<target-env-id>'
  AND canonical_id = '<the-untracked-workflow-canonical-id>';
```

**Look for:**
- `git_content_hash` matching the `env_content_hash` from step 1
- Recent `last_repo_sync_at` timestamp

---

#### Step 3: Check Environment Drift Status

**Inspect environments:**
```sql
SELECT
  id,
  n8n_name,
  drift_status,
  last_drift_detected_at,
  environment_class,
  git_repo_url IS NOT NULL as git_configured
FROM environments
WHERE tenant_id = '<your-tenant-id>';
```

**Look for:**
- `drift_status` = "UNTRACKED" (zero workflows tracked)
- `drift_status` = "DRIFT_DETECTED" (some workflows tracked, some have drift)

---

#### Step 4: Trigger Manual Sync (API Call)

**Endpoint:** `POST /api/canonical-workflows/environments/<env-id>/sync`

**Observe:**
- Check logs for "Cannot auto-link ... already linked to ..." warnings
- Watch for hash collision warnings
- Check `created_workflow_ids` in response (newly created UNTRACKED workflows)

---

#### Step 5: Enable Debug Logging

**Set environment variables:**
```bash
LOG_LEVEL=DEBUG
```

**Watch for log patterns:**
- `"Hash collision detected!"`
- `"Cannot auto-link ... already linked to ..."`
- `"Inconsistent workflow mapping state"`
- `"Workflow unchanged - skip processing"` (short-circuit)

**Logger names:**
- `app.services.canonical_env_sync_service`
- `app.services.canonical_workflow_service`
- `app.services.drift_detection_service`

---

#### Step 6: Reproduce via Promotion

**Preconditions:**
1. Workflow exists in DEV with canonical_id="abc123"
2. Workflow previously promoted to PROD (n8n_workflow_id="10")
3. PROD mapping: `canonical_id="abc123", n8n_workflow_id="10", status="linked"`

**Steps:**
1. Delete workflow in PROD n8n (id="10")
2. Run environment sync → status changes to "missing"
3. Promote workflow from DEV again
4. n8n creates new workflow with id="20" (new ID!)
5. Run environment sync
6. Observe: Auto-link by hash fails (canonical_id already linked to id="10")
7. Result: New row created with `canonical_id=NULL, n8n_workflow_id="20", status="untracked"`

**Expected DB State:**
```sql
-- Old mapping (should be cleaned up)
canonical_id='abc123', n8n_workflow_id='10', status='missing'

-- New mapping (incorrectly untracked)
canonical_id=NULL, n8n_workflow_id='20', status='untracked'
```

---

#### Step 7: Inspect Hash Collision Registry

**Not directly accessible (in-memory)**, but logged warnings indicate collisions.

**Search logs for:**
```
Hash collision detected! Hash '<hash>' maps to different payloads
```

**Trigger scenario:**
- Two workflows with identical content (after normalization)
- Both synced to same environment
- First one hashes successfully
- Second one detects collision

---

## 9) Summary of Key Findings

### Critical Distinction: Two Meanings of "UNTRACKED"

1. **Per-Workflow Status** (`workflow_env_map.status = 'untracked'`):
   - Workflow exists in n8n
   - No canonical_id mapping (NULL)
   - Requires manual linking or auto-link

2. **Environment-Level Status** (`environments.drift_status = 'UNTRACKED'`):
   - **Zero workflows are tracked/linked** in this environment
   - NOT "some workflows are untracked"
   - Misleading name when environment has mixed state

---

### DRIFT_DETECTED vs UNTRACKED Decision Tree

```
Is Git configured?
├─ No → UNKNOWN
└─ Yes
   └─ Are there tracked workflows (canonical_id NOT NULL)?
      ├─ No (count == 0) → UNTRACKED
      └─ Yes (count > 0)
         └─ Do any tracked workflows have drift?
            ├─ Yes → DRIFT_DETECTED
            └─ No
               └─ Are there workflows not in Git?
                  ├─ Yes → DRIFT_DETECTED
                  └─ No → IN_SYNC
```

---

### Most Likely Root Causes for "Weird UNTRACKED Behavior"

1. **Promotion creates new runtime ID** → auto-link conflict (#1)
2. **Workflow renamed** → drift detection false positive (#2)
3. **Git sync hasn't run yet** → no git_content_hash to compare (#6)
4. **Hash collision without canonical_id** → fallback fails (#3)
5. **Missing→Reappeared with unchanged timestamp** → short-circuit skips transition (#5)

---

## 10) Quick Reference: Status Cheat Sheets

### A. Per-Workflow Status Quick Lookup

| Status | Condition | Column Values | Typical Cause | Action Required |
|--------|-----------|---------------|---------------|-----------------|
| **LINKED** | Normal operation | `canonical_id` ≠ NULL, `is_present_in_n8n` = true, not deleted/ignored | Successfully synced and linked | None - monitor for drift |
| **UNTRACKED** | No canonical mapping | `canonical_id` = NULL, `is_present_in_n8n` = true, not deleted/ignored | Auto-link failed or never attempted | Link manually or wait for auto-link |
| **MISSING** | Disappeared from n8n | `n8n_workflow_id` ≠ NULL, `is_present_in_n8n` = false, not deleted/ignored | Workflow deleted in n8n or sync issue | Investigate deletion or re-import |
| **IGNORED** | User excluded | `is_ignored` = true | User marked as irrelevant | None - intentionally excluded |
| **DELETED** | Soft-deleted | `is_deleted` = true | User/system soft-delete | Restore or hard-delete |

---

### B. Environment-Level Status Quick Lookup

| Status | Condition | What It Means | User Action | Status Clears When |
|--------|-----------|---------------|-------------|-------------------|
| **IN_SYNC** | Git configured, tracked workflows > 0, all match Git | All tracked workflows match their Git source | None - healthy state | Workflow changes in n8n |
| **DRIFT_DETECTED** | Git configured, tracked workflows > 0, drift or not-in-git | Some tracked workflows differ from Git | Review drift report, sync to Git or revert | All workflows sync to Git |
| **UNTRACKED** | Git configured, tracked workflows = 0 | No workflows are linked to canonical yet | Link workflows or run auto-sync | At least 1 workflow linked |
| **UNKNOWN** | Git not configured | Cannot determine drift without Git | Configure Git repo and PAT | Git configured |
| **ERROR** | Detection failed | System error during drift check | Check logs, retry detection | Detection succeeds |

---

### C. Status Transition Matrix

This table shows valid state transitions for per-workflow status:

| From \ To | LINKED | UNTRACKED | MISSING | IGNORED | DELETED |
|-----------|--------|-----------|---------|---------|---------|
| **LINKED** | N/A | ❌ Invalid | ✅ Deleted in n8n | ✅ User ignores | ✅ Soft-delete |
| **UNTRACKED** | ✅ Auto/manual link | N/A | ❌ No n8n_id | ✅ User ignores | ✅ Soft-delete |
| **MISSING** | ✅ Reappears in n8n | ✅ Canonical unlinked | N/A | ✅ User ignores | ✅ Soft-delete |
| **IGNORED** | ✅ User un-ignores | ✅ User un-ignores | ✅ User un-ignores | N/A | ✅ Soft-delete |
| **DELETED** | ✅ Restore | ✅ Restore | ✅ Restore | ✅ Restore | N/A |

**Legend:**
- ✅ Valid transition (can occur during normal operations)
- ❌ Invalid transition (violates business rules)
- N/A Same state (no transition)

---

### D. Diagnostic SQL Queries

#### Count workflows by status for an environment:
```sql
SELECT
  status,
  COUNT(*) as count
FROM workflow_env_map
WHERE tenant_id = '<tenant-id>'
  AND environment_id = '<env-id>'
GROUP BY status
ORDER BY count DESC;
```

#### Find untracked workflows that could be auto-linked:
```sql
SELECT
  wem.n8n_workflow_id,
  wem.env_content_hash,
  cgs.canonical_id,
  cgs.git_content_hash
FROM workflow_env_map wem
JOIN canonical_workflow_git_state cgs
  ON wem.tenant_id = cgs.tenant_id
  AND wem.environment_id = cgs.environment_id
  AND wem.env_content_hash = cgs.git_content_hash
WHERE wem.tenant_id = '<tenant-id>'
  AND wem.environment_id = '<env-id>'
  AND wem.canonical_id IS NULL
  AND wem.status = 'untracked';
```

#### Find workflows with auto-link conflicts:
```sql
-- Find canonical workflows linked to multiple n8n IDs (should not happen)
SELECT
  canonical_id,
  COUNT(DISTINCT n8n_workflow_id) as n8n_id_count,
  array_agg(DISTINCT n8n_workflow_id) as n8n_ids
FROM workflow_env_map
WHERE tenant_id = '<tenant-id>'
  AND environment_id = '<env-id>'
  AND canonical_id IS NOT NULL
  AND status NOT IN ('deleted', 'missing')
GROUP BY canonical_id
HAVING COUNT(DISTINCT n8n_workflow_id) > 1;
```

#### Find environment drift summary:
```sql
SELECT
  e.n8n_name,
  e.environment_class,
  e.drift_status,
  e.last_drift_detected_at,
  COUNT(CASE WHEN wem.status = 'linked' THEN 1 END) as linked_count,
  COUNT(CASE WHEN wem.status = 'untracked' THEN 1 END) as untracked_count,
  COUNT(CASE WHEN wem.status = 'missing' THEN 1 END) as missing_count,
  COUNT(CASE WHEN wem.status = 'ignored' THEN 1 END) as ignored_count,
  COUNT(CASE WHEN wem.status = 'deleted' THEN 1 END) as deleted_count
FROM environments e
LEFT JOIN workflow_env_map wem
  ON e.tenant_id = wem.tenant_id
  AND e.id = wem.environment_id
WHERE e.tenant_id = '<tenant-id>'
GROUP BY e.id, e.n8n_name, e.environment_class, e.drift_status, e.last_drift_detected_at
ORDER BY e.environment_class;
```

---

### E. Common Troubleshooting Scenarios

#### Scenario: Environment shows UNTRACKED but has workflows
**Diagnosis:**
```sql
-- Check if any workflows are linked
SELECT COUNT(*) as tracked_count
FROM workflow_env_map
WHERE tenant_id = '<tenant-id>'
  AND environment_id = '<env-id>'
  AND canonical_id IS NOT NULL
  AND status NOT IN ('deleted', 'ignored');
```
**Expected:** If count = 0, environment status is correct
**Resolution:** Link at least one workflow to change status

---

#### Scenario: Workflow shows as UNTRACKED after promotion
**Diagnosis:**
```sql
-- Check for auto-link conflict
SELECT
  canonical_id,
  n8n_workflow_id,
  status,
  env_content_hash
FROM workflow_env_map
WHERE tenant_id = '<tenant-id>'
  AND environment_id = '<env-id>'
  AND env_content_hash = '<workflow-hash>'
ORDER BY created_at DESC;
```
**Expected:** Multiple rows with same hash, one MISSING, one UNTRACKED
**Resolution:** Manually link new workflow or clean up old MISSING mapping

---

#### Scenario: Drift detected but all workflows appear in sync
**Diagnosis:**
```sql
-- Check for renamed workflows
SELECT
  wem.n8n_workflow_id,
  wem.canonical_id,
  wem.env_content_hash,
  cgs.git_content_hash,
  wem.env_content_hash = cgs.git_content_hash as hashes_match
FROM workflow_env_map wem
JOIN canonical_workflow_git_state cgs
  ON wem.tenant_id = cgs.tenant_id
  AND wem.environment_id = cgs.environment_id
  AND wem.canonical_id = cgs.canonical_id
WHERE wem.tenant_id = '<tenant-id>'
  AND wem.environment_id = '<env-id>'
  AND wem.status = 'linked';
```
**Expected:** All `hashes_match` should be true
**Resolution:** If false, workflow has actual drift; if true, check drift detection logic

---

## 11) Files Referenced

| File | Purpose | Lines Analyzed |
|------|---------|----------------|
| `app/services/drift_detection_service.py` | Environment-level drift status assignment | 1-397 |
| `app/services/canonical_workflow_service.py` | Per-workflow status computation, hash logic | 1-425 |
| `app/services/canonical_env_sync_service.py` | Environment sync, auto-linking, UNTRACKED creation | 1-787 |
| `app/services/drift_scheduler.py` | Scheduler selection logic, DEV exclusion | 1-597 |
| `app/services/diff_service.py` | Workflow comparison, normalization, ignored fields | 1-611 |
| `app/schemas/canonical_workflow.py` | Status enum definitions, precedence rules | 1-356 |
| `app/api/endpoints/workflow_matrix.py` | Display status computation, UI logic | 1-438 |
| `app/services/promotion_service.py` | Normalization function (alternate version) | 1-200 |

---

**End of Report**
