# T008: State Machines for Environments and Workflows

**Task ID:** T008
**Status:** ✅ Completed
**Created:** 2024-01-14
**Primary Files:**
- `app-back/app/schemas/canonical_workflow.py`
- `app-back/app/schemas/drift_incident.py`
- `app-back/app/schemas/promotion.py`
- `app-back/app/schemas/deployment.py`
- `app-back/app/schemas/environment.py`
- `app-back/app/services/drift_incident_service.py`

---

## Executive Summary

This document provides comprehensive state machine documentation for the WorkflowOps system. The system employs multiple state machines to track:

1. **Workflow Mapping Status** - Lifecycle of workflow-environment mappings (LINKED, UNTRACKED, MISSING, IGNORED, DELETED)
2. **Drift Incident Status** - Lifecycle of drift incidents (detected → acknowledged → stabilized → reconciled → closed)
3. **Promotion Status** - Lifecycle of workflow promotions between environments
4. **Deployment Status** - Lifecycle of scheduled deployments
5. **Environment Drift Status** - Overall drift state of environments (IN_SYNC, DRIFT_DETECTED, etc.)

Each state machine has explicit transition rules, validation logic, and enforcement mechanisms documented below.

---

## Section 1: Workflow Mapping Status State Machine

### 1.1 State Definitions

**File:** `app-back/app/schemas/canonical_workflow.py` (Lines 7-80)

```python
class WorkflowMappingStatus(str, Enum):
    LINKED = "linked"
    IGNORED = "ignored"
    DELETED = "deleted"
    UNTRACKED = "untracked"
    MISSING = "missing"
```

#### States Explained:

| State | Meaning | Conditions | Database State |
|-------|---------|------------|----------------|
| **LINKED** | Workflow is canonically mapped and tracked | `canonical_id IS NOT NULL AND n8n_workflow_id IS NOT NULL AND workflow present in n8n` | Normal operational state |
| **UNTRACKED** | Workflow exists in n8n but lacks canonical mapping | `n8n_workflow_id IS NOT NULL AND canonical_id IS NULL` | Requires linking (manual or auto) |
| **MISSING** | Previously mapped workflow disappeared from n8n | `(canonical_id IS NOT NULL OR n8n_workflow_id IS NOT NULL) AND workflow not found in n8n sync` | Audit trail retained |
| **IGNORED** | Explicitly marked to be ignored by system | User action sets status to IGNORED | Not tracked or managed |
| **DELETED** | Mapping has been soft-deleted | User or system deleted the mapping | Historical record retained |

### 1.2 State Transition Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Workflow Mapping State Machine                │
└─────────────────────────────────────────────────────────────────┘

    [New Workflow Detected]
            │
            ├──[Has Match]────► LINKED
            │
            └──[No Match]─────► UNTRACKED
                                    │
                                    │ [User Links]
                                    ▼
                               LINKED ◄────────┐
                                    │          │
                      [Workflow]    │          │ [Workflow]
                      [Disappears]  │          │ [Reappears]
                                    ▼          │
                               MISSING ────────┘

            [User Marks Ignored]
            ───────────────────────────► IGNORED

            [User/System Deletes]
            ───────────────────────────► DELETED (Terminal)
```

### 1.3 Transition Rules and Precedence

**Precedence Order** (highest to lowest):

1. **DELETED** - Takes precedence over all other states. Once deleted, mapping is inactive.
2. **IGNORED** - User-explicit override takes precedence over system-computed states.
3. **MISSING** - Disappearance from n8n overrides LINKED/UNTRACKED states.
4. **UNTRACKED** - No canonical_id takes precedence over LINKED.
5. **LINKED** - Default operational state when both IDs exist and workflow present.

**Transition Logic** (from `canonical_env_sync_service.py`, lines 690-750):

```python
# Pseudo-code from sync service
if workflow_in_n8n:
    if has_canonical_id:
        status = LINKED
    else:
        status = UNTRACKED
else:
    if previously_tracked:
        status = MISSING
```

### 1.4 Derived Display States

**Note:** These are **computed at query time**, not persisted in the database.

| Display State | Computation | Underlying DB Status |
|---------------|-------------|----------------------|
| **DRIFT** | `LINKED AND env_content_hash ≠ git_content_hash` | LINKED |
| **OUT_OF_DATE** | `LINKED AND git_updated_at > env_updated_at` | LINKED |

**File Reference:** `canonical_workflow.py` lines 64-73

---

## Section 2: Drift Incident Status State Machine

### 2.1 State Definitions

**File:** `app-back/app/schemas/drift_incident.py` (Lines 8-14)

```python
class DriftIncidentStatus(str, Enum):
    detected = "detected"
    acknowledged = "acknowledged"
    stabilized = "stabilized"
    reconciled = "reconciled"
    closed = "closed"
```

#### States Explained:

| State | Meaning | Actor | Typical Action |
|-------|---------|-------|----------------|
| **detected** | New drift detected by scheduler | System | Automatic creation when drift found |
| **acknowledged** | Team aware of drift, tracking ongoing | User | User acknowledges incident with optional TTL |
| **stabilized** | Drift no longer changing, ready for resolution | User/System | Marks drift as stable (no new changes) |
| **reconciled** | Resolution action completed | User/System | Promotion, revert, or Git update completed |
| **closed** | Incident fully resolved and archived | User | Final closure with resolution notes |

### 2.2 State Transition Rules

**File:** `app-back/app/services/drift_incident_service.py` (Lines 29-36)

```python
VALID_TRANSITIONS = {
    DriftIncidentStatus.detected: [
        DriftIncidentStatus.acknowledged,
        DriftIncidentStatus.closed
    ],
    DriftIncidentStatus.acknowledged: [
        DriftIncidentStatus.stabilized,
        DriftIncidentStatus.reconciled,
        DriftIncidentStatus.closed
    ],
    DriftIncidentStatus.stabilized: [
        DriftIncidentStatus.reconciled,
        DriftIncidentStatus.closed
    ],
    DriftIncidentStatus.reconciled: [
        DriftIncidentStatus.closed
    ],
    DriftIncidentStatus.closed: [],  # Terminal state
}
```

### 2.3 State Transition Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                  Drift Incident State Machine                    │
└─────────────────────────────────────────────────────────────────┘

    [Drift Detected by Scheduler]
                │
                ▼
           DETECTED ────────────────────────────► CLOSED
                │                                   ▲
                │ [User Acknowledges]               │
                ▼                                   │
          ACKNOWLEDGED ────────────────────────────┤
                │                                   │
                │ [Drift Stabilized]                │
                ▼                                   │
           STABILIZED ──────────────────────────────┤
                │                                   │
                │ [Resolution Applied]              │
                ▼                                   │
          RECONCILED ──────────────────────────────┘
                │
                │ [User Closes]
                ▼
              CLOSED (Terminal)
```

### 2.4 Transition Validation Logic

**File:** `drift_incident_service.py` (Lines 411-433)

```python
def _validate_transition(
    self,
    current_status: str,
    new_status: DriftIncidentStatus,
    admin_override: bool = False
) -> bool:
    """Check if a status transition is valid.

    Args:
        current_status: Current incident status
        new_status: Desired new status
        admin_override: If True, allows any transition (admin bypass)

    Returns:
        True if transition is valid or admin override is enabled
    """
    # Admin override allows any transition except FROM closed state
    if admin_override:
        current = DriftIncidentStatus(current_status)
        # Still enforce that closed is terminal even for admins
        if current == DriftIncidentStatus.closed:
            return False
        return True

    current = DriftIncidentStatus(current_status)
    return new_status in VALID_TRANSITIONS.get(current, [])
```

**Key Rules:**
1. **Normal Flow:** Transitions must follow VALID_TRANSITIONS mapping
2. **Admin Override:** Allows any transition EXCEPT from `closed` state
3. **Terminal State:** `closed` is terminal - no transitions allowed (even for admins)
4. **Fast Paths:** Can skip states (e.g., detected → closed) per mapping

### 2.5 Transition Actions and Side Effects

#### Acknowledge Transition

**File:** `drift_incident_service.py` (Lines 435-534)

**Preconditions:**
- Current status must be `detected`
- Requires approval if drift policy mandates it (via `gated_action_service`)
- Admin override can bypass approval

**Side Effects:**
```python
update_data = {
    "status": DriftIncidentStatus.acknowledged.value,
    "acknowledged_at": datetime.utcnow().isoformat(),
    "acknowledged_by": user_id,
    "updated_at": datetime.utcnow().isoformat(),
    "reason": reason,  # Optional
    "owner_user_id": owner_user_id,  # Optional
    "ticket_ref": ticket_ref,  # Optional
    "expires_at": expires_at  # Optional (Agency+ TTL)
}
```

**Audit Log:** Gated action creates audit entry if approval required

#### Stabilize Transition

**File:** `drift_incident_service.py` (Lines 545-597)

**Preconditions:**
- Current status must be `acknowledged`
- No approval required for stabilization

**Side Effects:**
```python
update_data = {
    "status": DriftIncidentStatus.stabilized.value,
    "stabilized_at": datetime.utcnow().isoformat(),
    "stabilized_by": user_id,
    "updated_at": datetime.utcnow().isoformat(),
    "reason": reason  # Optional
}
```

#### Reconcile Transition

**File:** `drift_incident_service.py` (Lines 598-695)

**Preconditions:**
- Current status must be `acknowledged` or `stabilized`
- Must specify `resolution_type` (promote, revert, replace, acknowledge)
- Requires approval if drift policy mandates it

**Side Effects:**
```python
update_data = {
    "status": DriftIncidentStatus.reconciled.value,
    "reconciled_at": datetime.utcnow().isoformat(),
    "reconciled_by": user_id,
    "updated_at": datetime.utcnow().isoformat(),
    "resolution_type": resolution_type.value,
    "resolution_details": resolution_details,  # Optional
    "reason": reason  # Optional
}
```

**Resolution Types:**
- `promote` - Runtime changes promoted to Git
- `revert` - Runtime reverted to match Git
- `replace` - Git updated via external process
- `acknowledge` - Drift accepted (no reconciliation)

#### Close Transition

**File:** `drift_incident_service.py` (Lines 696-815)

**Preconditions:**
- Can transition from any state to `closed`
- If closing from `detected`, `acknowledged`, or `stabilized`: must provide `resolution_type` AND `reason`
- If closing from `reconciled`: only `reason` required (resolution already captured)

**Side Effects:**
```python
update_data = {
    "status": DriftIncidentStatus.closed.value,
    "closed_at": datetime.utcnow().isoformat(),
    "closed_by": user_id,
    "updated_at": datetime.utcnow().isoformat(),
    "reason": reason,  # Required
    "resolution_type": resolution_type  # Required if not from reconciled
}

# Also clears active drift incident from environment
environment_update = {
    "active_drift_incident_id": None,
    "drift_status": "IN_SYNC"  # May be set depending on actual state
}
```

### 2.6 Admin Override Behavior

**File:** `drift_incident_service.py` (Lines 424-430)

Admin override is supported on all transition operations via `admin_override: bool` parameter.

**Rules:**
1. ✅ Allows skipping required approvals
2. ✅ Allows any state transition EXCEPT from `closed`
3. ❌ Cannot reopen `closed` incidents (even with override)
4. 📝 Admin override actions are logged to audit trail

**Enforcement Point:** All transition methods (`acknowledge_incident`, `stabilize_incident`, `reconcile_incident`, `close_incident`) check `admin_override` before validation.

---

## Section 3: Promotion Status State Machine

### 3.1 State Definitions

**File:** `app-back/app/schemas/promotion.py` (Lines 7-15)

```python
class PromotionStatus(str, Enum):
    PENDING = "pending"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

#### States Explained:

| State | Meaning | System Behavior |
|-------|---------|-----------------|
| **PENDING** | Promotion created, pre-flight validation in progress | Validation checks running |
| **PENDING_APPROVAL** | Validation passed, awaiting approval | Blocked until approval granted |
| **APPROVED** | Approval granted, ready for execution | User can trigger execution |
| **REJECTED** | Approval denied | Terminal state (cannot execute) |
| **RUNNING** | Promotion executing, workflows being deployed | Active deployment in progress |
| **COMPLETED** | All workflows promoted successfully | Terminal success state |
| **FAILED** | Promotion failed, rollback may have occurred | Terminal failure state |
| **CANCELLED** | User cancelled before/during execution | Terminal cancelled state |

### 3.2 State Transition Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Promotion State Machine                       │
└─────────────────────────────────────────────────────────────────┘

    [User Initiates Promotion]
                │
                ▼
            PENDING
                │
                │ [Pre-flight Validation]
                │
                ├──[No Approval Required]─────► APPROVED
                │                                   │
                └──[Approval Required]──► PENDING_APPROVAL
                                              │         │
                                    [Approve] │         │ [Reject]
                                              ▼         ▼
                                          APPROVED  REJECTED (Terminal)
                                              │
                                              │ [Execute]
                                              ▼
                                          RUNNING
                                              │
                                    ┌─────────┼─────────┐
                                    │                   │
                              [Success]            [Failure]
                                    │                   │
                                    ▼                   ▼
                               COMPLETED            FAILED (Terminal)
                                 (Terminal)

            [User Cancels]
            ───────────────────────────► CANCELLED (Terminal)
```

### 3.3 Transition Rules

**Implicit Transitions** (system enforces via service logic, not explicit validation table):

| From State | To States | Trigger | File Reference |
|------------|-----------|---------|----------------|
| PENDING | APPROVED, PENDING_APPROVAL, CANCELLED | Validation completion | `promotion_service.py` |
| PENDING_APPROVAL | APPROVED, REJECTED, CANCELLED | User approval/rejection | `promotion_service.py` |
| APPROVED | RUNNING, CANCELLED | User executes | `promotion_service.py` |
| RUNNING | COMPLETED, FAILED | Execution outcome | `promotion_service.py` |

**Terminal States:** REJECTED, COMPLETED, FAILED, CANCELLED

### 3.4 Gate Results and Validation

**File:** `promotion.py` (Lines 136-149)

Before promotion transitions to PENDING_APPROVAL or APPROVED, gate checks are performed:

```python
class GateResult(BaseModel):
    require_clean_drift: bool
    drift_detected: bool
    drift_resolved: bool = False
    run_pre_flight_validation: bool
    credentials_exist: bool = True
    nodes_supported: bool = True
    webhooks_available: bool = True
    target_environment_healthy: bool = True
    risk_level_allowed: bool = True
    errors: List[str] = []
    warnings: List[str] = []
    credential_issues: List[Dict[str, Any]] = []
```

**Gating Logic:**
- ❌ If any critical gate fails → Promotion cannot proceed (stays PENDING or transitions to FAILED)
- ⚠️ Warnings don't block promotion but are logged
- ✅ Admin bypass flag `bypass_validation` can override gates

---

## Section 4: Deployment Status State Machine

### 4.1 State Definitions

**File:** `app-back/app/schemas/deployment.py` (Lines 7-13)

```python
class DeploymentStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELED = "canceled"
```

#### States Explained:

| State | Meaning | Lifecycle Stage |
|-------|---------|-----------------|
| **PENDING** | Deployment created, not yet scheduled | Initial state |
| **SCHEDULED** | Deployment scheduled for future time | Awaiting scheduled_at time |
| **RUNNING** | Deployment executing workflows | Active execution |
| **SUCCESS** | All workflows deployed successfully | Terminal success |
| **FAILED** | Deployment failed | Terminal failure |
| **CANCELED** | User cancelled before/during execution | Terminal cancelled |

### 4.2 State Transition Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                   Deployment State Machine                       │
└─────────────────────────────────────────────────────────────────┘

    [Promotion Execute Called]
                │
                ├──[scheduled_at=null]─────► PENDING
                │                               │
                │                               │ [Execute Immediately]
                │                               ▼
                │                            RUNNING
                │
                └──[scheduled_at set]──────► SCHEDULED
                                               │
                                               │ [Scheduler Triggers]
                                               ▼
                                            RUNNING
                                               │
                                    ┌──────────┼──────────┐
                                    │                     │
                              [All Success]         [Any Failure]
                                    │                     │
                                    ▼                     ▼
                                SUCCESS              FAILED
                                (Terminal)          (Terminal)

            [User Cancels]
            ───────────────────────────► CANCELED (Terminal)
```

### 4.3 Workflow-Level State Tracking

**File:** `deployment.py` (Lines 31-36)

Each deployment tracks individual workflow statuses:

```python
class WorkflowStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    UNCHANGED = "unchanged"
```

**Rollup Logic:**
- Deployment status = SUCCESS only if ALL workflow statuses = SUCCESS
- Deployment status = FAILED if ANY workflow status = FAILED
- Deployment status = RUNNING while any workflow status = PENDING

---

## Section 5: Environment Drift Status

### 5.1 State Definitions

**File:** `app-back/app/schemas/environment.py` (Lines 81)

Environment-level drift status (stored as string, not enum):

```python
drift_status: str = "IN_SYNC"  # Default value
```

**Possible Values** (inferred from codebase):

| Value | Meaning | Trigger |
|-------|---------|---------|
| **IN_SYNC** | No drift detected | All workflows match Git |
| **DRIFT_DETECTED** | Active drift exists | Drift scheduler found differences |
| **DRIFT_INCIDENT_ACTIVE** | Drift incident created | Environment has active_drift_incident_id |

### 5.2 State Transition Logic

**File:** `drift_detection_service.py` (inferred from behavior)

```
┌─────────────────────────────────────────────────────────────────┐
│               Environment Drift Status Lifecycle                 │
└─────────────────────────────────────────────────────────────────┘

                        IN_SYNC
                           │
                           │ [Drift Scheduler Detects Drift]
                           ▼
                    DRIFT_DETECTED
                           │
                           │ [Incident Created]
                           ▼
                DRIFT_INCIDENT_ACTIVE
                           │
                           │ [Incident Closed]
                           ▼
                        IN_SYNC
```

**Side Effects:**

When drift incident is closed:
```python
# From drift_incident_service.py (lines 790-810)
environment_update = {
    "active_drift_incident_id": None,
    "drift_status": "IN_SYNC"  # Reset to IN_SYNC
}
```

**Note:** The exact transition logic for DRIFT_DETECTED vs DRIFT_INCIDENT_ACTIVE is not explicitly defined in a single place. Recommend consolidating this into an enum for type safety.

---

## Section 6: Environment Class State (Policy Enforcement)

### 6.1 Environment Class Enum

**File:** `app-back/app/schemas/environment.py` (Lines 17-20)

```python
class EnvironmentClass(str, Enum):
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"
```

**Purpose:** Deterministic classification for workflow action policies.

**Usage:**
- DEV: Source of truth is n8n runtime
- STAGING: Typically intermediate promotion target
- PRODUCTION: Highest protection, strictest policies

**State Machine:** This is NOT a state machine (no transitions). It's a static classification set during environment creation.

### 6.2 Legacy EnvironmentType (Deprecated)

**File:** `environment.py` (Lines 9-12)

```python
class EnvironmentType(str, Enum):
    dev = "dev"
    staging = "staging"
    production = "production"
```

**Status:** Deprecated in favor of `EnvironmentClass`. Kept for backward compatibility.

---

## Section 7: Link Suggestion Status State Machine

### 7.1 State Definitions

**File:** `app-back/app/schemas/canonical_workflow.py` (Lines 82-87)

```python
class LinkSuggestionStatus(str, Enum):
    OPEN = "open"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
```

#### States Explained:

| State | Meaning | User Action |
|-------|---------|-------------|
| **OPEN** | Suggestion awaiting user decision | System created suggestion |
| **ACCEPTED** | User accepted suggestion, workflow linked | User linked workflow |
| **REJECTED** | User rejected suggestion | User dismissed suggestion |
| **EXPIRED** | Suggestion timed out | System auto-expired (TTL) |

### 7.2 State Transition Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                Link Suggestion State Machine                     │
└─────────────────────────────────────────────────────────────────┘

    [Auto-Link Service Creates Suggestion]
                │
                ▼
              OPEN
                │
                ├──[User Accepts]───► ACCEPTED (Terminal)
                │
                ├──[User Rejects]───► REJECTED (Terminal)
                │
                └──[TTL Expires]────► EXPIRED (Terminal)
```

**Terminal States:** ACCEPTED, REJECTED, EXPIRED

---

## Section 8: Workflow Diff Status (Promotion Context)

### 8.1 State Definitions

**File:** `app-back/app/schemas/canonical_workflow.py` (Lines 90-97)

```python
class WorkflowDiffStatus(str, Enum):
    UNCHANGED = "unchanged"
    MODIFIED = "modified"
    ADDED = "added"
    TARGET_ONLY = "target_only"
    TARGET_HOTFIX = "target_hotfix"
    CONFLICT = "conflict"
```

**Note:** This is replaced by `DiffStatus` in promotion.py for new promotion flow.

### 8.2 New Authoritative Diff Status

**File:** `app-back/app/schemas/promotion.py` (Lines 22-31)

```python
class DiffStatus(str, Enum):
    """
    Canonical diff status for workflow comparison.
    Frontend must use these values directly - no local computation.
    """
    ADDED = "added"              # Exists only in source
    MODIFIED = "modified"        # Exists in both, content differs, source newer
    DELETED = "deleted"          # Exists only in target (target-only)
    UNCHANGED = "unchanged"      # Normalized content identical
    TARGET_HOTFIX = "target_hotfix"  # Content differs, target newer
```

**Usage:** Computed during promotion pre-flight comparison, used to display diff status in UI.

**State Machine:** NOT a state machine (no transitions). Represents **computed comparison result** at a point in time.

---

## Section 9: Reconciliation Status State Machine

### 9.1 State Definitions

**File:** `app-back/app/schemas/drift_incident.py` (Lines 187-192)

```python
class ReconciliationStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    success = "success"
    failed = "failed"
```

#### States Explained:

| State | Meaning | Lifecycle Stage |
|-------|---------|-----------------|
| **pending** | Reconciliation artifact created | Initial state |
| **in_progress** | Reconciliation executing | Active execution |
| **success** | Reconciliation completed successfully | Terminal success |
| **failed** | Reconciliation failed | Terminal failure |

### 9.2 State Transition Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│             Reconciliation Artifact State Machine                │
└─────────────────────────────────────────────────────────────────┘

    [User Triggers Reconciliation]
                │
                ▼
            PENDING
                │
                │ [Worker Starts]
                ▼
          IN_PROGRESS
                │
                ├──[Success]──────► SUCCESS (Terminal)
                │
                └──[Failure]──────► FAILED (Terminal)
```

**Terminal States:** SUCCESS, FAILED

**Side Effects:**

```python
# From drift_incident.py (lines 202-213)
reconciliation_artifact = {
    "id": str(uuid4()),
    "tenant_id": tenant_id,
    "incident_id": incident_id,
    "type": resolution_type,  # promote, revert, replace, acknowledge
    "status": ReconciliationStatus.pending,
    "started_at": None,
    "started_by": None,
    "finished_at": None,
    "affected_workflows": workflow_list,
    "external_refs": {},  # PR URL, commit SHA, etc.
    "error_message": None
}
```

---

## Section 10: Summary Tables

### 10.1 All State Machines in WorkflowOps

| State Machine | File | Line Range | Terminal States | Enforcement Location |
|---------------|------|------------|-----------------|----------------------|
| WorkflowMappingStatus | `canonical_workflow.py` | 7-80 | DELETED | `canonical_env_sync_service.py` |
| DriftIncidentStatus | `drift_incident.py` | 8-14 | closed | `drift_incident_service.py` lines 29-36 |
| PromotionStatus | `promotion.py` | 7-15 | REJECTED, COMPLETED, FAILED, CANCELLED | `promotion_service.py` |
| DeploymentStatus | `deployment.py` | 7-13 | SUCCESS, FAILED, CANCELED | `deployment_scheduler.py` |
| LinkSuggestionStatus | `canonical_workflow.py` | 82-87 | ACCEPTED, REJECTED, EXPIRED | `canonical_workflow_service.py` |
| ReconciliationStatus | `drift_incident.py` | 187-192 | success, failed | (Background worker) |

### 10.2 Environment-Level State

| Property | Type | File | Purpose | Transitions |
|----------|------|------|---------|-------------|
| drift_status | string | `environment.py` line 81 | Track drift state | IN_SYNC ↔ DRIFT_DETECTED ↔ DRIFT_INCIDENT_ACTIVE |
| environment_class | Enum | `environment.py` lines 17-20 | Policy enforcement | **Static** (no transitions) |
| is_active | boolean | `environment.py` line 29 | Enable/disable environment | true ↔ false |

### 10.3 State Machine Properties Comparison

| Property | Workflow Mapping | Drift Incident | Promotion | Deployment |
|----------|------------------|----------------|-----------|------------|
| Has explicit transition table | ❌ No | ✅ Yes (VALID_TRANSITIONS) | ❌ No | ❌ No |
| Admin override supported | ❌ No | ✅ Yes | ✅ Yes (bypass_validation) | ❌ No |
| Requires approval | ❌ No | ✅ Yes (conditional) | ✅ Yes (conditional) | ❌ No |
| Audit logged | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| Soft-delete supported | ✅ Yes (DELETED) | ✅ Yes (is_deleted) | ❌ No | ✅ Yes (deleted_at) |

---

## Section 11: Validation Rules and Edge Cases

### 11.1 Drift Incident Validation

**Edge Case 1: Duplicate Incident Prevention**

**File:** `drift_incident_service.py` (Lines 131-198)

```python
async def _check_duplicate_incident(
    self,
    tenant_id: str,
    environment_id: str,
    affected_workflows: Optional[List[AffectedWorkflow]] = None,
    drift_snapshot: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Check if a duplicate incident exists based on content similarity.

    Returns the duplicate incident if found, None otherwise.

    Duplicate detection strategy:
    1. First check for active incidents (highest priority - prevent duplicates)
    2. Then check recent incidents (last 24 hours) with matching affected workflows
    3. Compare drift snapshots if available for exact match detection
    """
```

**Prevention Logic:**
1. ✅ Only one **active** (non-closed) incident per environment at a time
2. ✅ Recent incidents (last 24 hours) checked for matching affected workflows
3. ✅ Drift snapshot comparison for exact match detection
4. ❌ If duplicate check fails, don't block incident creation (fail-open)

**Edge Case 2: Reopening Closed Incidents**

**File:** `drift_incident_service.py` (Lines 424-430)

```python
# Admin override allows any transition except FROM closed state
if admin_override:
    current = DriftIncidentStatus(current_status)
    # Still enforce that closed is terminal even for admins
    if current == DriftIncidentStatus.closed:
        return False
    return True
```

**Rule:** Even with admin override, `closed` incidents **cannot** be reopened.

**Rationale:** Prevents audit trail corruption. If drift reoccurs, create a new incident.

### 11.2 Workflow Mapping Status Edge Cases

**Edge Case 1: Workflow Reappearance After MISSING**

**File:** `canonical_env_sync_service.py` (inferred from sync logic)

```python
# If workflow reappears in n8n after being MISSING:
if workflow_in_n8n:
    if has_canonical_id:
        status = LINKED  # Restore to LINKED
    else:
        status = UNTRACKED  # Restore to UNTRACKED
```

**Rule:** Workflow reappearance automatically restores operational status based on whether canonical_id exists.

**Edge Case 2: Hash Collision Detection**

**File:** `canonical_env_sync_service.py` (Lines 27-77)

```python
def _detect_hash_collision(
    workflow: Dict[str, Any],
    content_hash: str,
    canonical_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Detect if a hash collision occurred for a workflow.

    A collision occurs when:
    - The hash already exists in the registry
    - But the normalized payload is different
    """
```

**Detection:**
1. Check if `content_hash` already registered
2. Compare normalized payloads
3. If same hash but different payload → collision warning
4. ⚠️ Warning logged, but workflow still processed

**Edge Case 3: Conflicting Status Changes**

If during a sync, a workflow is both:
- Explicitly IGNORED by user
- Detected as MISSING by sync

**Resolution:** IGNORED takes precedence (per precedence rules in Section 1.3)

---

## Section 12: Audit and Observability Hooks

### 12.1 State Transition Audit Events

All state transitions generate audit events:

| State Machine | Audit Event | File Reference |
|---------------|-------------|----------------|
| Drift Incident | `gated_action_service.record_execution` | `drift_incident_service.py` lines 515-530, 673-688 |
| Promotion | `audit_service.log_promotion_event` | `promotion_service.py` (throughout) |
| Deployment | (Deployment record itself serves as audit) | `deployment.py` |
| Workflow Mapping | Sync job records | `canonical_env_sync_service.py` |

### 12.2 Environment-Level Observability

**File:** `environment.py` (Lines 76-84)

Environment state includes observability timestamps:

```python
last_connected: Optional[datetime] = None
last_backup: Optional[datetime] = None
last_heartbeat_at: Optional[datetime] = None
last_drift_check_at: Optional[datetime] = None
last_sync_at: Optional[datetime] = None
```

**Updated By:**
- `last_sync_at` - Updated by `canonical_env_sync_service`
- `last_drift_check_at` - Updated by `drift_scheduler`
- `last_heartbeat_at` - Updated by environment health check
- `last_connected` - Updated by n8n API connection test

---

## Section 13: Recommendations and Future Improvements

### 13.1 Missing State Machines

**Recommendation 1: Formalize Environment Drift Status**

Currently `drift_status` is a string field with no enum validation.

**Proposed:**
```python
class EnvironmentDriftStatus(str, Enum):
    IN_SYNC = "IN_SYNC"
    DRIFT_DETECTED = "DRIFT_DETECTED"
    DRIFT_INCIDENT_ACTIVE = "DRIFT_INCIDENT_ACTIVE"
```

**Benefit:** Type safety, explicit transition validation

**Recommendation 2: Add Promotion Transition Validation Table**

Promotion status transitions are implicit. Adding explicit validation would prevent invalid state changes.

**Proposed:**
```python
VALID_PROMOTION_TRANSITIONS = {
    PromotionStatus.PENDING: [
        PromotionStatus.PENDING_APPROVAL,
        PromotionStatus.APPROVED,
        PromotionStatus.CANCELLED
    ],
    PromotionStatus.PENDING_APPROVAL: [
        PromotionStatus.APPROVED,
        PromotionStatus.REJECTED,
        PromotionStatus.CANCELLED
    ],
    # ... etc
}
```

### 13.2 State Machine Visualization

**Recommendation 3: Generate Mermaid Diagrams Automatically**

Consider tooling to auto-generate state machine diagrams from code:

1. Parse VALID_TRANSITIONS dictionaries
2. Generate Mermaid.js syntax
3. Embed in API documentation

**Benefit:** Always-accurate diagrams, reduced maintenance burden

### 13.3 State Transition Logging

**Recommendation 4: Structured State Transition Logs**

Currently state transitions are logged via generic database updates. Consider:

```python
class StateTransitionEvent(BaseModel):
    entity_type: str  # "drift_incident", "promotion", etc.
    entity_id: str
    from_state: str
    to_state: str
    actor_id: str
    timestamp: datetime
    metadata: Dict[str, Any]
```

**Benefit:** Queryable state transition history, debugging support

---

## Section 14: Critical Invariants Summary

### 14.1 Drift Incident Invariants

1. ✅ **At most ONE active incident per environment** - Enforced by `_check_duplicate_incident`
2. ✅ **Closed is terminal** - Even admins cannot reopen closed incidents
3. ✅ **Approval required for sensitive transitions** - Enforced via `gated_action_service`
4. ✅ **Environment active_drift_incident_id cleared on close** - Maintains referential integrity

### 14.2 Workflow Mapping Invariants

1. ✅ **Status precedence order enforced** - DELETED > IGNORED > MISSING > UNTRACKED > LINKED
2. ✅ **MISSING status set if workflow disappears** - Maintains audit trail
3. ✅ **UNTRACKED created for unmapped workflows** - Ensures all workflows trackable
4. ✅ **Hash collision warnings logged** - Detects content hash issues

### 14.3 Promotion Invariants

1. ✅ **Snapshot created before mutation** - Pre-promotion snapshot enables rollback
2. ✅ **Atomic rollback on failure** - All-or-nothing promotion guarantee
3. ✅ **Idempotency via content hash** - Prevents duplicate promotions
4. ✅ **Terminal states immutable** - COMPLETED, FAILED, REJECTED cannot transition

### 14.4 Deployment Invariants

1. ✅ **Scheduled deployments execute at scheduled_at time** - Scheduler enforces timing
2. ✅ **Workflow-level status tracked** - Granular failure tracking
3. ✅ **Rollup logic: ANY failure → FAILED** - Conservative failure handling

---

## Section 15: File Reference Index

### 15.1 Schema Files

| File | Purpose | Key Enums |
|------|---------|-----------|
| `app/schemas/canonical_workflow.py` | Workflow mapping lifecycle | WorkflowMappingStatus, LinkSuggestionStatus, WorkflowDiffStatus |
| `app/schemas/drift_incident.py` | Drift incident lifecycle | DriftIncidentStatus, ReconciliationStatus, ResolutionType |
| `app/schemas/promotion.py` | Promotion lifecycle | PromotionStatus, DiffStatus, ValidationCheckStatus |
| `app/schemas/deployment.py` | Deployment lifecycle | DeploymentStatus, WorkflowStatus, SnapshotType |
| `app/schemas/environment.py` | Environment configuration | EnvironmentClass, EnvironmentType (deprecated) |

### 15.2 Service Files

| File | Purpose | Key State Transitions |
|------|---------|----------------------|
| `app/services/drift_incident_service.py` | Drift incident state management | acknowledge, stabilize, reconcile, close |
| `app/services/canonical_env_sync_service.py` | Workflow mapping state updates | LINKED, UNTRACKED, MISSING detection |
| `app/services/promotion_service.py` | Promotion execution | PENDING → APPROVED → RUNNING → COMPLETED |
| `app/services/deployment_scheduler.py` | Scheduled deployment execution | SCHEDULED → RUNNING → SUCCESS/FAILED |

---

## Appendix A: State Transition Truth Tables

### A.1 Drift Incident Transition Truth Table

| From \ To | detected | acknowledged | stabilized | reconciled | closed |
|-----------|----------|--------------|------------|------------|--------|
| **detected** | N/A | ✅ | ❌ | ❌ | ✅ |
| **acknowledged** | ❌ | N/A | ✅ | ✅ | ✅ |
| **stabilized** | ❌ | ❌ | N/A | ✅ | ✅ |
| **reconciled** | ❌ | ❌ | ❌ | N/A | ✅ |
| **closed** | ❌ | ❌ | ❌ | ❌ | N/A |

**Legend:**
- ✅ = Valid transition
- ❌ = Invalid transition
- N/A = Same state (no-op)

### A.2 Workflow Mapping Status Truth Table

| Current State | Workflow in n8n? | Has canonical_id? | New State | Notes |
|---------------|------------------|-------------------|-----------|-------|
| (none) | ✅ Yes | ✅ Yes | LINKED | Auto-linked match found |
| (none) | ✅ Yes | ❌ No | UNTRACKED | New untracked workflow |
| LINKED | ❌ No | ✅ Yes | MISSING | Workflow disappeared |
| UNTRACKED | ❌ No | ❌ No | MISSING | Untracked disappeared |
| MISSING | ✅ Yes | ✅ Yes | LINKED | Workflow reappeared |
| MISSING | ✅ Yes | ❌ No | UNTRACKED | Untracked reappeared |
| (any) | (any) | (any) | IGNORED | User marks ignored |
| (any) | (any) | (any) | DELETED | User/system deletes |

---

## Appendix B: Admin Override Matrix

### B.1 Operations Supporting Admin Override

| Operation | State Machine | Override Parameter | Bypass Approvals? | Bypass Transitions? | Terminal State Enforceable? |
|-----------|---------------|--------------------|--------------------|---------------------|----------------------------|
| acknowledge_incident | Drift Incident | `admin_override: bool` | ✅ Yes | ✅ Yes | ✅ Yes (closed still terminal) |
| stabilize_incident | Drift Incident | `admin_override: bool` | ✅ Yes | ✅ Yes | ✅ Yes |
| reconcile_incident | Drift Incident | `admin_override: bool` | ✅ Yes | ✅ Yes | ✅ Yes |
| close_incident | Drift Incident | `admin_override: bool` | ✅ Yes | ✅ Yes | ✅ Yes |
| initiate_promotion | Promotion | `bypass_validation: bool` | ✅ Yes | ⚠️ Partial | ❌ No |

**Notes:**
- Drift incident admin override: Cannot transition FROM closed state
- Promotion bypass: Skips gate validation, but state machine still enforced

---

## Completion Summary

**Task T008 Status:** ✅ **COMPLETED**

### Deliverables:

1. ✅ Comprehensive state machine documentation for:
   - Workflow Mapping Status (5 states)
   - Drift Incident Status (5 states, explicit transition table)
   - Promotion Status (8 states)
   - Deployment Status (6 states)
   - Link Suggestion Status (4 states)
   - Reconciliation Status (4 states)
   - Environment Drift Status (3 inferred states)

2. ✅ State transition diagrams (ASCII art for portability)

3. ✅ Validation rules and edge case handling

4. ✅ Audit hooks and observability integration

5. ✅ Truth tables for complex state machines

6. ✅ File reference index with line numbers

7. ✅ Recommendations for future improvements

### Key Insights:

1. **Drift Incident** has the most formal state machine (explicit VALID_TRANSITIONS table)
2. **Promotion** and **Deployment** rely on implicit transitions enforced by service logic
3. **Environment drift_status** lacks enum validation (improvement opportunity)
4. **Admin override** is well-designed with terminal state protection
5. **Workflow Mapping Status** uses precedence rules instead of explicit transitions

### Files Created:

- `T008_STATE_MACHINES_DOCUMENTATION.md` (this file)

### Next Steps (for T009+):

- Use this state machine documentation to create narrative walkthroughs
- Reference state transitions when identifying failure modes
- Include state machine diagrams in executive summary

---

**Document Version:** 1.0
**Last Updated:** 2024-01-14
**Author:** Claude (Task Executor)
**Review Status:** Ready for Review
