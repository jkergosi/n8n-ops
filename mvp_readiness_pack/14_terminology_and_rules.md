# 14 - Terminology, States, and Rules

**Generated:** 2026-01-15
**Purpose:** Authoritative reference for user-facing terminology, workflow states, environment rules, and enforcement guarantees

---

## 1. User-Facing Terminology Mapping

### Proposed User Term: **Source-Managed**

**Rationale:** Conveys that workflows are managed via source control (Git) as the single source of truth.

### Terminology Mapping Table

| User-Facing Term | Internal Term | Definition |
|------------------|---------------|------------|
| **Source-Managed Workflow** | Canonical Workflow | A workflow tracked in Git with a single source of truth |
| **Source-Managed** (adjective) | Canonical | Pertaining to Git-backed workflow governance |
| **Source Management** | Canonical System | The system for tracking workflows via Git |
| **Unmanaged Workflow** | Unmapped Workflow | A workflow not yet linked to a Source-Managed definition |
| **Managed** (verb) | Linked | The act of associating an unmanaged workflow with a Source-Managed definition |

### Where Each Term Applies

| Context | Use User Term | Use Internal Term |
|---------|---------------|-------------------|
| UI labels and buttons | ✅ | ❌ |
| User-facing documentation | ✅ | ❌ |
| Narrative walkthroughs | ✅ | ❌ |
| API endpoint paths | ❌ | ✅ (e.g., `/canonical/`) |
| Database table names | ❌ | ✅ (e.g., `canonical_workflows`) |
| Schema/class names | ❌ | ✅ (e.g., `CanonicalWorkflow`) |
| Code comments (internal) | ❌ | ✅ |
| Technical architecture docs | ❌ | ✅ |

### UI Copy Examples

| Context | Copy |
|---------|------|
| Workflow list header | "Source-Managed Workflows" |
| Unmanaged workflow badge | "Unmanaged" |
| Button to link workflow | "Manage Workflow" |
| Success message | "Workflow is now Source-Managed" |
| Tooltip | "This workflow is tracked via Git source control" |

---

## 2. Unmanaged Workflow Decision Flow

### Entry Conditions

A workflow enters the **Unmanaged** state when:

1. **New workflow detected** during environment sync that has no matching Source-Managed definition
2. **Imported workflow** via n8n that was not promoted through WorkflowOps
3. **First sync** of an environment discovers pre-existing n8n workflows

### Decision Table

| Current State | User Action | Result State | DB Mutation | Drift Eligible | Notes |
|---------------|-------------|--------------|-------------|----------------|-------|
| Unmanaged | **Manage** (link to existing) | Linked | `workflow_env_map.canonical_id = <id>`, `status = 'linked'` | ✅ Yes | Associates with existing Source-Managed workflow |
| Unmanaged | **Manage** (create new) | Linked | Creates `canonical_workflows` row, updates `workflow_env_map` | ✅ Yes | Creates new Source-Managed definition from workflow |
| Unmanaged | **Snapshot Only** | Unmanaged | No change (snapshot stored in Git as backup) | ❌ No | Backup without governance; workflow stays unmanaged |
| Unmanaged | **Ignore** | Ignored | `workflow_env_map.status = 'ignored'` | ❌ No | Explicitly excluded from tracking |
| Ignored | **Unignore** | Unmanaged | `workflow_env_map.status = 'unmapped'` | ❌ No | Returns to unmanaged pool |
| Linked | **Unlink** | Unmanaged | `workflow_env_map.canonical_id = NULL`, `status = 'unmapped'` | ❌ No | Removes from Source-Management |

### Actions by Environment Class

| Action | DEV | STAGING | PROD |
|--------|-----|---------|------|
| **Manage** (link to existing) | ✅ Allowed | ✅ Allowed | ⚠️ Warning (should use promotion) |
| **Manage** (create new) | ✅ Allowed | ❌ Blocked | ❌ Blocked |
| **Snapshot Only** | ✅ Allowed | ✅ Allowed | ✅ Allowed |
| **Ignore** | ✅ Allowed | ✅ Allowed | ✅ Allowed |
| **Unlink** | ✅ Allowed | ⚠️ Warning | ❌ Blocked |

### Workflow States Summary

```
                    ┌─────────────────┐
                    │   UNMANAGED     │
                    │  (unmapped)     │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
            ▼                ▼                ▼
    ┌───────────┐    ┌───────────┐    ┌───────────┐
    │  MANAGED  │    │  IGNORED  │    │  SNAPSHOT │
    │  (linked) │    │           │    │   ONLY    │
    └───────────┘    └───────────┘    └───────────┘
         │
         │ (drift detection applies)
         ▼
    ┌───────────┐
    │ IN_SYNC / │
    │  DRIFTED  │
    └───────────┘
```

---

## 3. Missing/Deleted Git Repository State

### State Definition: `GIT_UNAVAILABLE`

When the configured Git repository becomes inaccessible (deleted, permissions revoked, network issues), the environment enters a degraded state.

### Detection Mechanism

**Trigger Points:**
1. **Drift detection cycle** - `git_snapshot_service.is_env_onboarded()` fails
2. **Promotion attempt** - Cannot read/write to target repo
3. **Manual sync** - GitHub API returns 404 or 403
4. **Scheduled health check** - Periodic repo accessibility test

**Detection Code Path:**
```python
# git_snapshot_service.py
async def _validate_repo_access(self, github_service) -> tuple[bool, str]:
    try:
        await github_service.get_repo_info()
        return (True, None)
    except GitHubNotFoundError:
        return (False, "REPO_DELETED")
    except GitHubForbiddenError:
        return (False, "PERMISSION_DENIED")
    except GitHubNetworkError:
        return (False, "NETWORK_ERROR")
```

### Environment State Table (Extended)

| DriftStatus | Git State | Condition | Description |
|-------------|-----------|-----------|-------------|
| `NEW` | N/A | No baseline exists | Environment not onboarded |
| `IN_SYNC` | Accessible | Runtime matches baseline | Normal operational state |
| `DRIFT_DETECTED` | Accessible | Runtime differs from baseline | Drift incident eligible |
| `GIT_UNAVAILABLE` | **Inaccessible** | Repo deleted/forbidden/unreachable | Degraded state |
| `ERROR` | Unknown | Exception during detection | Check failed |
| `UNKNOWN` | Unknown | Never checked | Initial state |

### UI Copy for GIT_UNAVAILABLE

| Environment Class | Label | Tooltip |
|-------------------|-------|---------|
| DEV | "Git unavailable" | "Cannot connect to Git repository. Check repository URL and credentials." |
| STAGING | "Git unavailable" | "Cannot connect to Git repository. Promotions and drift detection are blocked." |
| PROD | "Git unavailable" | "Cannot connect to Git repository. Contact administrator immediately." |

### Allowed/Blocked Actions

| Action | GIT_UNAVAILABLE | Rationale |
|--------|-----------------|-----------|
| **View workflows** | ✅ Allowed | Local data still accessible |
| **View drift status** | ⚠️ Stale | Shows last known state with warning |
| **Trigger sync** | ❌ Blocked | Cannot read from Git |
| **Save as Approved** | ❌ Blocked | Cannot write to Git |
| **Revert** | ❌ Blocked | Cannot read baseline from Git |
| **Keep Hotfix** | ❌ Blocked | Cannot write hotfix marker to Git |
| **Promote to** | ❌ Blocked | Cannot write to target |
| **Promote from** | ❌ Blocked | Cannot read source baseline |
| **Edit environment** | ✅ Allowed | May need to fix Git URL/credentials |
| **Delete environment** | ✅ Allowed | Cleanup path |

### Recovery Paths

| Recovery Action | Steps | Result |
|-----------------|-------|--------|
| **Relink repository** | Edit environment → Update Git URL/credentials → Save | Re-validates access, clears GIT_UNAVAILABLE if successful |
| **Recreate repository** | Create new repo → Copy Git URL → Edit environment | Requires re-onboarding (creates new baseline) |
| **Remove Git integration** | Edit environment → Clear Git fields → Save | Environment becomes non-Git-managed; loses all governance features |
| **Ignore (temporary)** | No action | System retries on next health check cycle |

---

## 4. DEV Environment Rules

### Consolidated DEV Behavior

This section is the **authoritative source** for all DEV environment rules. No DEV-specific behavior should be defined elsewhere.

### What DEV Participates In

| Feature | DEV Participation | Notes |
|---------|-------------------|-------|
| **Workflow discovery** | ✅ Yes | Sync discovers workflows from n8n |
| **Source Management** | ✅ Yes | Can create/link Source-Managed workflows |
| **Baseline creation** | ✅ Yes | "Save as Approved" creates baseline |
| **State comparison** | ✅ Yes | Compares runtime to baseline |
| **Snapshot/backup** | ✅ Yes | Can backup individual workflows |
| **Bulk backup** | ✅ Yes | Can backup all workflows |
| **Workflow matrix** | ✅ Yes | Visible in cross-environment view |
| **Promotion source** | ✅ Yes | Can promote TO staging |
| **Health monitoring** | ✅ Yes | n8n instance health tracked |

### What DEV Does NOT Participate In

| Feature | DEV Exclusion | Rationale |
|---------|---------------|-----------|
| **Drift incidents** | ❌ No | DEV drift is expected (active development) |
| **Drift SLA enforcement** | ❌ No | No time-based drift resolution requirements |
| **Drift notifications** | ❌ No | Would be noise during development |
| **Automatic revert** | ❌ No | Never auto-reverts DEV changes |
| **Promotion target** | ❌ No | Cannot promote TO dev (only FROM dev) |
| **Production safeguards** | ❌ No | No confirmation dialogs for DEV actions |
| **Approval workflows** | ❌ No | No gates for DEV deployments |

### DEV UI Label Differences

| State | DEV Label | Non-DEV Label |
|-------|-----------|---------------|
| No baseline | "No baseline" | "Not onboarded" |
| Matches baseline | "Matches baseline" | "Matches approved" |
| Differs from baseline | "Different from baseline" | "Drift detected" |

### DEV Drift Semantics

**Key Distinction:** In DEV, "drift" is a **neutral informational state**, not an incident.

```
DEV: Runtime ≠ Baseline → "Different from baseline" (informational)
STAGING/PROD: Runtime ≠ Baseline → "Drift detected" (actionable incident)
```

### DEV Backup/Snapshot Expectations

| Operation | Behavior |
|-----------|----------|
| **Manual backup** | Allowed; creates Git snapshot |
| **Scheduled backup** | ❌ Not scheduled (user-triggered only) |
| **Auto-baseline** | ❌ No automatic baseline updates |
| **Snapshot retention** | Same as other environments (policy-based) |

---

## 5. Sync Removal Enforcement

### Definition of "Sync"

In this context, **sync** refers to:
- Automatic/scheduled synchronization between n8n runtime and Git
- Background processes that push/pull workflow definitions
- Any operation that modifies workflows without explicit user action

**NOT sync:**
- User-triggered "Sync Now" (discovery operation)
- User-triggered "Save as Approved" (explicit baseline update)
- User-triggered "Promote" (explicit promotion)

### Hard Guarantees (System-Enforced)

These are **physically prevented** by the system:

| Guarantee | Enforcement Point | Evidence |
|-----------|-------------------|----------|
| **No automatic Git→n8n push** | No code path exists | No service calls n8n write APIs on schedule |
| **No scheduled workflow deployment** | Deployment scheduler checks `scheduled_at` | Only deploys explicitly scheduled promotions |
| **No background baseline updates** | `save_as_approved` requires user context | API requires authenticated user, no scheduler calls it |
| **No auto-revert** | Revert endpoint requires user action | No background job calls revert APIs |
| **No drift auto-resolution** | Drift incidents require user action | Incident state machine requires explicit transitions |

### Soft Conventions (UX-Discouraged)

These are **discouraged by UX** but technically possible:

| Convention | Discouragement Method |
|------------|----------------------|
| Promoting to PROD without review | Warning dialog, requires confirmation |
| Linking workflows in PROD directly | Warning message suggests using promotion |
| Bulk operations on PROD | Additional confirmation step |

### Scheduled/Background Operations (Exhaustive List)

| Operation | Frequency | What It Does | What It Does NOT Do |
|-----------|-----------|--------------|---------------------|
| **Drift detection** | Configurable (default 5min) | Reads n8n + Git, computes diff | Does NOT modify n8n or Git |
| **Health check** | Configurable (default 1min) | Pings n8n API | Does NOT modify anything |
| **Deployment scheduler** | Every 30s | Executes scheduled deployments | Only processes user-scheduled items |
| **Retention cleanup** | Daily | Deletes old snapshots per policy | Does NOT modify active workflows |
| **Rollup aggregation** | Hourly | Pre-computes observability metrics | Does NOT modify workflow data |

### Confirmation: No Auto-Sync Paths

**Searched code paths for automatic sync:**

| Potential Path | Status | Evidence |
|----------------|--------|----------|
| `canonical_sync_scheduler.py` | ✅ Safe | Only triggers discovery (read), not deployment (write) |
| `drift_scheduler.py` | ✅ Safe | Only reads and compares, no writes |
| `deployment_scheduler.py` | ✅ Safe | Only deploys user-scheduled items |
| Background job workers | ✅ Safe | Job types don't include auto-sync |
| GitHub webhooks | ✅ Safe | Webhook handler doesn't auto-deploy |

### Enforcement Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                    WRITE OPERATIONS                              │
├─────────────────────────────────────────────────────────────────┤
│  n8n Runtime Modifications:                                     │
│    ✅ Promotion (user-triggered)                                │
│    ✅ Revert (user-triggered)                                   │
│    ❌ Auto-sync (does not exist)                                │
│    ❌ Scheduled push (does not exist)                           │
├─────────────────────────────────────────────────────────────────┤
│  Git Baseline Modifications:                                    │
│    ✅ Save as Approved (user-triggered)                         │
│    ✅ Keep Hotfix (user-triggered)                              │
│    ✅ Promotion snapshot (user-triggered)                       │
│    ❌ Auto-baseline (does not exist)                            │
│    ❌ Scheduled commit (does not exist)                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Acceptance Criteria Checklist

- [x] User-facing term defined: **Source-Managed**
- [x] Terminology mapping table provided
- [x] No "canonical" in user-facing contexts (use Source-Managed)
- [x] Unmanaged workflow decision table complete
- [x] Actions by environment class specified
- [x] `GIT_UNAVAILABLE` state formally defined
- [x] Detection mechanism documented
- [x] Recovery paths enumerated
- [x] DEV rules consolidated in single section
- [x] DEV participation/exclusion explicit
- [x] Hard guarantees vs soft conventions distinguished
- [x] All scheduled operations audited
- [x] No auto-sync paths confirmed
