# T007: Identity and Mapping Rules from Canonical Services

**Task**: Extract identity and mapping rules from canonical services
**Primary File**: `app/services/canonical_workflow_service.py`
**Status**: ✅ COMPLETED
**Date**: 2026-01-14

---

## Executive Summary

This document extracts and documents the **identity and mapping rules** that govern how workflows are tracked, identified, and linked across the canonical workflow system. The canonical system establishes a "single source of truth" for workflows by creating persistent **canonical IDs** that are independent of environment-specific workflow IDs (n8n_workflow_id).

**Key Insights**:
- **Canonical ID** is the stable, cross-environment identifier (UUID)
- **Content Hash** (SHA256) is the fingerprint used for identity resolution
- **Status Precedence Rules** determine workflow state across 5 distinct statuses
- **Auto-linking** uses exact hash matches for zero-touch workflow mapping
- **Hash Collision Detection** with deterministic fallback strategies

---

## 1. Core Identity Model

### 1.1 Identity Architecture

The canonical system establishes a **three-layer identity model**:

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: Canonical Identity (Cross-Environment)         │
│   - canonical_id (UUID)                                  │
│   - Stable across all environments                       │
│   - Created once, never changes                          │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 2: Git State (Per-Environment Source of Truth)    │
│   - git_content_hash (SHA256)                            │
│   - git_path                                              │
│   - git_commit_sha                                        │
│   - Tracked in: canonical_workflow_git_state             │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 3: Runtime Mapping (Per-Environment Instance)     │
│   - n8n_workflow_id (provider-specific ID)               │
│   - env_content_hash (SHA256)                            │
│   - status (LINKED/UNTRACKED/MISSING/IGNORED/DELETED)    │
│   - Tracked in: workflow_env_map                         │
└─────────────────────────────────────────────────────────┘
```

**File References**:
- `app/services/canonical_workflow_service.py` (Lines 1-424)
- `app/schemas/canonical_workflow.py` (Lines 1-356)
- Migration: `alembic/versions/dcd2f2c8774d_create_canonical_workflow_tables.py`

---

## 2. Canonical ID Generation and Management

### 2.1 Canonical ID Assignment

**Source**: `canonical_workflow_service.py:create_canonical_workflow()` (Lines 244-281)

**Rules**:
1. **Explicit Assignment**: If canonical_id provided, use it (migration/import scenarios)
2. **Auto-Generation**: If not provided, generate UUIDv4: `str(uuid4())`
3. **Uniqueness**: Enforced by composite primary key `(tenant_id, canonical_id)`

```python
# From canonical_workflow_service.py (Lines 262-263)
if not canonical_id:
    canonical_id = str(uuid4())
```

**Table**: `canonical_workflows`
```sql
CREATE TABLE canonical_workflows (
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    canonical_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by_user_id UUID NULL,
    display_name TEXT NULL,
    deleted_at TIMESTAMPTZ NULL,
    PRIMARY KEY (tenant_id, canonical_id)
);
```

### 2.2 Canonical Workflow Lifecycle

**Creation**:
- Triggered by: Onboarding inventory, repo sync, manual creation
- Creates row in `canonical_workflows` table
- Assigns stable canonical_id
- Optional display_name cache for UI performance

**Soft Delete**:
- Sets `deleted_at` timestamp (Line 360)
- Preserves historical record
- Filtered from active queries: `WHERE deleted_at IS NULL`

---

## 3. Content Hash System

### 3.1 Hash Computation Algorithm

**Source**: `canonical_workflow_service.py:compute_workflow_hash()` (Lines 75-156)

**Algorithm**:
```python
# Step 1: Normalize workflow (remove metadata)
normalized = normalize_workflow_for_comparison(workflow)

# Step 2: Serialize with sorted keys
json_str = json.dumps(normalized, sort_keys=True)

# Step 3: Compute SHA256
content_hash = hashlib.sha256(json_str.encode()).hexdigest()
```

**Normalization** (from `promotion_service.py:normalize_workflow_for_comparison()`, Lines 90-161):

**Excluded Fields** (Line 99-111):
```python
exclude_fields = [
    'id', 'createdAt', 'updatedAt', 'versionId',
    'triggerCount', 'staticData', 'meta', 'hash',
    'executionOrder', 'homeProject', 'sharedWithProjects',
    '_comment', 'pinData',
    'active',  # Active state may differ between environments
    'tags', 'tagIds',  # Tags have different IDs per environment
    'shared', 'scopes', 'usedCredentials',
]
```

**Node Normalization** (Lines 131-154):
- Remove `position`, `positionAbsolute`, `selected`, `executionData`, `typeVersion`, `id`, `webhookId`
- **Credentials**: Compare by **name only** (ID differs per environment)
  ```python
  # Line 143-150
  if isinstance(cred_ref, dict):
      normalized_creds[cred_type] = {'name': cred_ref.get('name')}
  ```
- Sort nodes by name for consistent comparison

**Result**: Content hash that is:
- Environment-agnostic (excludes runtime IDs, timestamps)
- Deterministic (same workflow → same hash)
- Credential-name-aware (maps credentials correctly)

### 3.2 Hash Collision Detection

**Source**: `canonical_workflow_service.py` (Lines 18-157)

**Registry Architecture**:
```python
# In-memory registry for collision detection (Lines 18-20)
_hash_collision_registry: Dict[str, Dict[str, Any]] = {}
# Key: content_hash (str)
# Value: normalized workflow payload (Dict[str, Any])
```

**Detection Logic** (Lines 106-116):
```python
registered_payload = get_registered_payload(content_hash)

if registered_payload is not None:
    if registered_payload != normalized:
        # COLLISION DETECTED: Same hash, different payload
        logger.warning(f"Hash collision detected! Hash '{content_hash}'...")
```

**Collision Resolution Strategy** (Lines 118-156):

1. **Deterministic Fallback** (Lines 119-139):
   - If `canonical_id` is provided:
     ```python
     fallback_content = {
         **normalized,
         "__canonical_id__": canonical_id  # Append to content
     }
     fallback_hash = hashlib.sha256(fallback_json_str.encode()).hexdigest()
     ```
   - Register fallback hash to prevent future collisions
   - Return unique fallback hash

2. **Unresolved Collision** (Lines 141-147):
   - If no `canonical_id` provided:
     ```python
     logger.error("Hash collision detected but no canonical_id provided...")
     return content_hash  # Return colliding hash (unresolved)
     ```

**Collision Tracking**:
- Detected during env sync: `canonical_env_sync_service.py:_detect_hash_collision()` (Lines 27-77)
- Detected during repo sync: `canonical_repo_sync_service.py:_detect_hash_collision()` (Lines 25-76)
- Warnings stored in sync results: `results["collision_warnings"]`

**Example Collision Warning**:
```python
{
    "n8n_workflow_id": "123",
    "workflow_name": "Customer Onboarding",
    "content_hash": "abc123def456...",
    "canonical_id": "uuid-xxxx-yyyy",
    "message": "Hash collision detected for workflow 'Customer Onboarding'..."
}
```

---

## 4. Workflow Mapping Status Rules

### 4.1 Status Enum

**Source**: `schemas/canonical_workflow.py:WorkflowMappingStatus` (Lines 7-79)

```python
class WorkflowMappingStatus(str, Enum):
    LINKED = "linked"       # Has canonical_id, tracked
    UNTRACKED = "untracked" # No canonical_id, needs onboarding
    MISSING = "missing"     # Was linked/untracked, now gone from n8n
    IGNORED = "ignored"     # Explicitly ignored by user
    DELETED = "deleted"     # Soft-deleted
```

### 4.2 Status Precedence Rules

**Source**: `canonical_workflow_service.py:compute_workflow_mapping_status()` (Lines 159-237)

**Precedence Hierarchy** (Highest → Lowest):

```
1. DELETED    ─────► Overrides ALL states (permanent)
        │
        ▼
2. IGNORED    ─────► Overrides operational states
        │
        ▼
3. MISSING    ─────► Workflow disappeared from n8n
        │
        ▼
4. UNTRACKED  ─────► No canonical_id assigned
        │
        ▼
5. LINKED     ─────► Normal operational state (has both IDs)
```

**Computation Logic**:

```python
# Lines 207-237 (simplified)
def compute_workflow_mapping_status(
    canonical_id: Optional[str],
    n8n_workflow_id: Optional[str],
    is_present_in_n8n: bool,
    is_deleted: bool = False,
    is_ignored: bool = False
) -> WorkflowMappingStatus:

    # Precedence 1: DELETED overrides everything
    if is_deleted:
        return WorkflowMappingStatus.DELETED

    # Precedence 2: IGNORED overrides operational states
    if is_ignored:
        return WorkflowMappingStatus.IGNORED

    # Precedence 3: MISSING if workflow was mapped but disappeared
    if not is_present_in_n8n and n8n_workflow_id:
        return WorkflowMappingStatus.MISSING

    # Precedence 4: UNTRACKED if no canonical_id but exists in n8n
    if not canonical_id and is_present_in_n8n:
        return WorkflowMappingStatus.UNTRACKED

    # Precedence 5: LINKED as default operational state
    if canonical_id and is_present_in_n8n:
        return WorkflowMappingStatus.LINKED

    # Edge case: inconsistent state → default to UNTRACKED
    logger.warning("Inconsistent workflow mapping state...")
    return WorkflowMappingStatus.UNTRACKED
```

### 4.3 Status Transition Rules

**Source**: `schemas/canonical_workflow.py` (Lines 55-62)

```
State Transitions:
──────────────────
- New workflow detected → UNTRACKED (if no match) or LINKED (if auto-linked)
- User links untracked   → UNTRACKED → LINKED
- Workflow disappears    → LINKED/UNTRACKED → MISSING
- Missing reappears      → MISSING → LINKED (if canonical_id) or UNTRACKED
- User marks ignored     → any state → IGNORED
- Workflow/mapping deleted → any state → DELETED
```

**Reappearance Logic** (from `canonical_env_sync_service.py`, Lines 388-393):
```python
# Workflow reappeared - transition based on canonical_id
if existing_status == "missing":
    if existing_canonical_id:
        new_status = WorkflowMappingStatus.LINKED
    else:
        new_status = WorkflowMappingStatus.UNTRACKED
```

---

## 5. Auto-Linking Rules

### 5.1 Auto-Link By Hash

**Source**: `canonical_env_sync_service.py:_try_auto_link_by_hash()` (Lines 494-554)

**Conditions for Auto-Link** (ALL must be satisfied):

1. **Exact Hash Match**: `env_content_hash == git_content_hash`
2. **Unique Match**: Exactly ONE canonical workflow has this hash
3. **No Conflict**: canonical_id not already linked to different n8n_workflow_id in same environment

**Algorithm**:

```python
# Step 1: Find canonical workflows with matching Git content hash
git_state_response = (
    db_service.client.table("canonical_workflow_git_state")
    .select("canonical_id")
    .eq("tenant_id", tenant_id)
    .eq("environment_id", environment_id)
    .eq("git_content_hash", content_hash)  # Exact match required
    .execute()
)

matching_canonical_ids = [row["canonical_id"] for row in git_state_response.data]

# Step 2: Only auto-link if exactly one match
if len(matching_canonical_ids) != 1:
    return None  # Ambiguous or no match

canonical_id = matching_canonical_ids[0]

# Step 3: Check for conflict (already linked to different workflow)
existing_mapping_response = (
    db_service.client.table("workflow_env_map")
    .select("n8n_workflow_id")
    .eq("canonical_id", canonical_id)
    .neq("status", "missing")
    .execute()
)

for mapping in existing_mapping_response.data:
    if existing_n8n_id != n8n_workflow_id:
        logger.warning("Cannot auto-link: already linked to different workflow")
        return None  # Conflict detected

return canonical_id  # Auto-link successful
```

**Invocation**: Called during env sync when new workflow is detected (Line 424-429)

**Result**:
- **Success**: Workflow created with `status=LINKED`, canonical_id set
- **Failure**: Workflow created with `status=UNTRACKED`, canonical_id=NULL

### 5.2 Auto-Link Failure Scenarios

1. **Multiple Matches**: More than one canonical workflow has the same hash
   - **Reason**: Hash collision or duplicate workflows in Git
   - **Resolution**: Manual linking required

2. **No Matches**: No canonical workflow has this hash
   - **Reason**: New workflow not yet in Git
   - **Resolution**: Remains UNTRACKED until Git sync

3. **Conflict**: canonical_id already linked to different n8n_workflow_id
   - **Reason**: Same canonical workflow already deployed to same environment
   - **Resolution**: Manual investigation (duplicate deployment?)

---

## 6. Database Mapping Tables

### 6.1 canonical_workflows

**Purpose**: Identity registry (stable IDs)

**Schema** (from migration `dcd2f2c8774d`, Lines 46-57):
```sql
CREATE TABLE canonical_workflows (
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    canonical_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by_user_id UUID NULL,
    display_name TEXT NULL,
    deleted_at TIMESTAMPTZ NULL,
    PRIMARY KEY (tenant_id, canonical_id)
);
```

**Key Columns**:
- `canonical_id`: Stable cross-environment identifier (UUID)
- `display_name`: Optional cached workflow name (for UI performance)
- `deleted_at`: Soft delete timestamp (NULL = active)

**Indexes**:
- `idx_canonical_workflows_tenant` on `tenant_id`
- `idx_canonical_workflows_created_at` on `created_at DESC`
- `idx_canonical_workflows_deleted_at` on `deleted_at` (partial, WHERE deleted_at IS NOT NULL)

### 6.2 canonical_workflow_git_state

**Purpose**: Per-environment Git state tracking

**Schema** (Lines 59-74):
```sql
CREATE TABLE canonical_workflow_git_state (
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    environment_id UUID NOT NULL REFERENCES environments(id) ON DELETE CASCADE,
    canonical_id UUID NOT NULL,
    git_path TEXT NOT NULL,
    git_commit_sha TEXT NULL,
    git_content_hash TEXT NOT NULL,
    last_repo_sync_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, environment_id, canonical_id),
    FOREIGN KEY (tenant_id, canonical_id) REFERENCES canonical_workflows
);
```

**Key Columns**:
- `git_path`: File path in Git repo (e.g., `workflows/dev/abc-123.json`)
- `git_commit_sha`: Git commit hash where this version exists
- `git_content_hash`: SHA256 of normalized workflow from Git
- `last_repo_sync_at`: Last time Git was synced

**Cardinality**: **One row per (canonical_id, environment_id)** – each environment has its own Git state

**Usage**:
- Updated by: `canonical_repo_sync_service.py:sync_repository()` (Lines 196-204)
- Queried by: Auto-link logic, drift detection, reconciliation

### 6.3 workflow_env_map

**Purpose**: Environment instance mappings

**Schema** (Lines 76-93):
```sql
CREATE TABLE workflow_env_map (
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    environment_id UUID NOT NULL REFERENCES environments(id) ON DELETE CASCADE,
    canonical_id UUID NOT NULL,
    n8n_workflow_id TEXT NULL,
    env_content_hash TEXT NOT NULL,
    last_env_sync_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    linked_at TIMESTAMPTZ NULL,
    linked_by_user_id UUID NULL,
    status TEXT NULL CHECK (status IN ('linked', 'ignored', 'deleted')),
    PRIMARY KEY (tenant_id, environment_id, canonical_id),
    FOREIGN KEY (tenant_id, canonical_id) REFERENCES canonical_workflows
);
```

**NOTE**: The migration shows limited status values. Later migrations extend this:
```sql
-- From later schema evolution (not in this migration)
ALTER TABLE workflow_env_map
ADD CONSTRAINT status_check
CHECK (status IN ('linked', 'untracked', 'missing', 'ignored', 'deleted'));

-- Additional columns added later
ALTER TABLE workflow_env_map ADD COLUMN n8n_updated_at TIMESTAMPTZ NULL;
ALTER TABLE workflow_env_map ADD COLUMN workflow_data JSONB NULL;
```

**Key Columns**:
- `canonical_id`: FK to canonical_workflows (NULL = UNTRACKED)
- `n8n_workflow_id`: Provider-specific workflow ID (e.g., "123")
- `env_content_hash`: SHA256 of workflow as it exists in n8n runtime
- `status`: Workflow mapping status (LINKED/UNTRACKED/MISSING/IGNORED/DELETED)
- `n8n_updated_at`: Last update timestamp from n8n (for short-circuit optimization)
- `workflow_data`: Cached workflow JSON (DEV environments only)

**Constraints** (from schema docs):
- Unique `(tenant_id, environment_id, n8n_workflow_id)` – one row per runtime workflow
- Unique `(tenant_id, canonical_id, environment_id)` WHERE canonical_id NOT NULL

**Cardinality**:
- **One row per n8n workflow instance**
- UNTRACKED workflows: `canonical_id = NULL`, `n8n_workflow_id` populated
- LINKED workflows: Both `canonical_id` and `n8n_workflow_id` populated

---

## 7. Identity Resolution Flows

### 7.1 Environment Sync (n8n → DB)

**Source**: `canonical_env_sync_service.py:sync_environment()` (Lines 92-309)

**Flow**:

```
┌────────────────────────────────────────────────────────────┐
│ Phase 1: Discovery                                         │
│   - Fetch all workflows from n8n API                       │
│   - Total workflows counted                                 │
└────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────┐
│ Phase 2: Batch Processing (25-30 workflows/batch)         │
│   For each workflow:                                        │
│   ┌────────────────────────────────────────────────────┐  │
│   │ 1. Check if mapping exists (by n8n_workflow_id)   │  │
│   └────────────────────────────────────────────────────┘  │
│                           │                                 │
│         ┌─────────────────┴─────────────────┐              │
│         ▼                                    ▼              │
│   ┌──────────┐                        ┌──────────┐         │
│   │ Exists   │                        │ New      │         │
│   └──────────┘                        └──────────┘         │
│         │                                    │              │
│         │ Short-circuit check:               │              │
│         │ n8n_updated_at unchanged?          │              │
│         │                                    │              │
│         ├─ YES → Skip (Line 371-376)        │              │
│         ├─ NO  → Continue                    │              │
│         │                                    │              │
│         ▼                                    ▼              │
│   ┌────────────────────────────────────────────────┐      │
│   │ Compute content_hash                            │      │
│   │   hash = compute_workflow_hash(workflow,        │      │
│   │                                 canonical_id)    │      │
│   └────────────────────────────────────────────────┘      │
│         │                                    │              │
│         ▼                                    ▼              │
│   ┌────────────────────────────────────────────────┐      │
│   │ Update mapping:                                 │      │
│   │   - env_content_hash = hash                     │      │
│   │   - workflow_data (if DEV)                      │      │
│   │   - n8n_updated_at                              │      │
│   │   - Status transition (if MISSING→LINKED)       │      │
│   └────────────────────────────────────────────────┘      │
│                                                             │
│                                    ┌────────────────────┐  │
│                                    │ Try Auto-Link:     │  │
│                                    │   canonical_id =   │  │
│                                    │   _try_auto_link_  │  │
│                                    │   by_hash()        │  │
│                                    └────────────────────┘  │
│                                           │                 │
│                                ┌──────────┴──────────┐     │
│                                ▼                      ▼     │
│                          ┌──────────┐          ┌──────────┐│
│                          │ Linked   │          │Untracked ││
│                          │status=   │          │canonical_││
│                          │LINKED    │          │id=NULL   ││
│                          └──────────┘          └──────────┘│
└────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────┐
│ Phase 3: Cleanup                                           │
│   - Mark workflows not seen as MISSING                      │
│   - Preserve n8n_workflow_id for audit trail               │
└────────────────────────────────────────────────────────────┘
```

**DEV vs Non-DEV Behavior** (Lines 228-230, 396-407):
- **DEV** (`environment_class = "dev"`):
  - Full sync: Store `workflow_data` in DB
  - Updates: `workflow_data` + `env_content_hash` + `n8n_updated_at`
- **Non-DEV** (staging, prod):
  - Observational sync: Only update `env_content_hash` + `n8n_updated_at`
  - `workflow_data` remains NULL (Git is source of truth)

**Short-Circuit Optimization** (Lines 368-376):
```python
# Skip processing if n8n_updated_at unchanged
if existing_status != "missing" and existing_n8n_updated_at and n8n_updated_at:
    if _normalize_timestamp(existing_n8n_updated_at) == _normalize_timestamp(n8n_updated_at):
        batch_results["skipped"] += 1
        continue  # No change in n8n, skip expensive hash computation
```

### 7.2 Repository Sync (Git → DB)

**Source**: `canonical_repo_sync_service.py:sync_repository()` (Lines 83-247)

**Flow**:

```
┌────────────────────────────────────────────────────────────┐
│ Phase 1: Git Discovery                                     │
│   - Clone/fetch Git repository                             │
│   - Scan for *.json files in git_folder                    │
│   - Get current commit SHA                                 │
└────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────┐
│ Phase 2: File Processing                                   │
│   For each workflow file:                                  │
│   ┌────────────────────────────────────────────────────┐  │
│   │ 1. Extract canonical_id from filename              │  │
│   │    Format: workflows/{git_folder}/{canonical_id}.json│ │
│   │    canonical_id = file_path.split('/')[-1]          │  │
│   │                    .replace('.json', '')             │  │
│   └────────────────────────────────────────────────────┘  │
│         │                                                   │
│         ▼                                                   │
│   ┌────────────────────────────────────────────────────┐  │
│   │ 2. Compute content_hash                             │  │
│   │    hash = compute_workflow_hash(workflow_data,      │  │
│   │                                  canonical_id)       │  │
│   └────────────────────────────────────────────────────┘  │
│         │                                                   │
│         ▼                                                   │
│   ┌────────────────────────────────────────────────────┐  │
│   │ 3. Short-circuit check:                             │  │
│   │    existing_git_state.git_content_hash == hash?     │  │
│   │    - YES → Skip (Line 174-177)                      │  │
│   │    - NO  → Continue                                  │  │
│   └────────────────────────────────────────────────────┘  │
│         │                                                   │
│         ▼                                                   │
│   ┌────────────────────────────────────────────────────┐  │
│   │ 4. Get or create canonical_workflow                 │  │
│   │    - If not exists: Create with canonical_id        │  │
│   │    - Update display_name cache                       │  │
│   └────────────────────────────────────────────────────┘  │
│         │                                                   │
│         ▼                                                   │
│   ┌────────────────────────────────────────────────────┐  │
│   │ 5. Upsert canonical_workflow_git_state              │  │
│   │    - git_path = file_path                            │  │
│   │    - git_content_hash = hash                         │  │
│   │    - git_commit_sha = commit_sha                     │  │
│   │    - last_repo_sync_at = now()                       │  │
│   └────────────────────────────────────────────────────┘  │
│         │                                                   │
│         ▼                                                   │
│   ┌────────────────────────────────────────────────────┐  │
│   │ 6. Try to ingest sidecar file (optional)           │  │
│   │    Path: {workflow_file}.env-map.json               │  │
│   │    Contains: environment mappings with              │  │
│   │              n8n_workflow_id per environment        │  │
│   └────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

**Canonical ID Extraction** (Line 160):
```python
# Extract canonical_id from filename
# Format: workflows/{git_folder}/{canonical_id}.json
canonical_id = file_path.split('/')[-1].replace('.json', '')
```

**Git State Upsert** (Lines 196-204):
```python
await CanonicalWorkflowService.upsert_canonical_workflow_git_state(
    tenant_id=tenant_id,
    environment_id=environment_id,
    canonical_id=canonical_id,
    git_path=file_path,
    git_content_hash=content_hash,
    git_commit_sha=commit_sha
)
```

**Sidecar File Format** (Lines 258-271):
```json
{
  "canonical_workflow_id": "uuid-xxx",
  "workflow_name": "Customer Onboarding",
  "environments": {
    "env-uuid-1": {
      "environment_type": "prod",
      "n8n_workflow_id": "203",
      "content_hash": "sha256:abc123...",
      "last_seen_at": "2026-01-14T12:00:00Z"
    }
  }
}
```

**Purpose**: Pre-populate workflow_env_map with known mappings (migration scenarios)

---

## 8. Identity Resolution Edge Cases

### 8.1 Inconsistent Mapping States

**Source**: `canonical_workflow_service.py` (Lines 229-237)

**Scenario**: Workflow is in a state that doesn't match any precedence rule

**Example**:
```python
canonical_id = "abc-123"
n8n_workflow_id = None  # Missing n8n ID
is_present_in_n8n = True  # But claims to be present
is_deleted = False
is_ignored = False
```

**Resolution**:
```python
# Lines 232-237
logger.warning(
    f"Inconsistent workflow mapping state: canonical_id={canonical_id}, "
    f"n8n_workflow_id={n8n_workflow_id}, is_present_in_n8n={is_present_in_n8n}..."
)
return WorkflowMappingStatus.UNTRACKED  # Safest fallback
```

### 8.2 Reappearing Workflows

**Source**: `canonical_env_sync_service.py` (Lines 388-393)

**Scenario**: Workflow with `status=MISSING` is detected again during env sync

**Resolution**:
```python
if existing_status == "missing":
    # Workflow reappeared - transition based on canonical_id
    if existing_canonical_id:
        new_status = WorkflowMappingStatus.LINKED  # Restore link
    else:
        new_status = WorkflowMappingStatus.UNTRACKED  # Remain untracked
```

**Behavior**:
- **Previously LINKED**: Automatically restored to LINKED
- **Previously UNTRACKED**: Remains UNTRACKED (no auto-promotion)

### 8.3 Duplicate Canonical IDs (Same Environment)

**Constraint**: `UNIQUE(tenant_id, canonical_id, environment_id)` WHERE canonical_id NOT NULL

**Scenario**: Attempt to link two different n8n workflows to the same canonical_id in same environment

**Result**: Database constraint violation → Operation fails

**Prevention**: Auto-link checks for existing mapping before linking (Lines 531-549)

### 8.4 Hash Collision with NULL canonical_id

**Source**: `canonical_workflow_service.py` (Lines 141-147)

**Scenario**: Hash collision detected but no canonical_id available for fallback

**Resolution**:
```python
logger.error(
    f"Hash collision detected but no canonical_id provided for fallback. "
    f"Hash: '{content_hash}'. Returning colliding hash (unresolved collision)."
)
return content_hash  # Return colliding hash - collision remains unresolved
```

**Impact**:
- Both workflows get same hash
- Auto-link fails (multiple matches)
- Requires manual investigation and linking

---

## 9. Key Observations and Risks

### 9.1 Observations

1. **Canonical ID Stability**: Once assigned, canonical_id never changes (even if workflow renamed)

2. **Hash-Based Identity**: Content hash is the primary mechanism for auto-linking and drift detection

3. **Status Precedence**: Clear, documented precedence rules prevent ambiguous states

4. **Soft Delete Pattern**: Workflows are never hard-deleted; deleted_at timestamp preserves history

5. **Environment Class Behavior**: DEV stores full workflow_data, non-DEV stores only hashes (Git is source)

6. **Short-Circuit Optimization**: Unchanged workflows (by n8n_updated_at or git_content_hash) are skipped

7. **Collision Detection**: In-memory registry detects hash collisions with deterministic fallback

### 9.2 Risks

**High Risk**:

1. **Hash Collision Registry is In-Memory**:
   - **Issue**: Registry cleared on service restart (Line 59: `_hash_collision_registry = {}`)
   - **Impact**: Collisions not detected across service restarts
   - **Mitigation**: Move registry to persistent storage (DB or Redis)

2. **Unresolved Hash Collisions**:
   - **Issue**: If collision occurs without canonical_id, returns colliding hash
   - **Impact**: Two different workflows treated as identical
   - **Mitigation**: Fail-fast instead of returning colliding hash

3. **Canonical ID Filename Extraction**:
   - **Issue**: Relies on specific file naming: `{canonical_id}.json` (Line 160)
   - **Impact**: Non-conforming filenames cause sync failures
   - **Mitigation**: Validate filename format before extraction

**Medium Risk**:

1. **Auto-Link Ambiguity**:
   - **Issue**: Multiple canonical workflows with same hash → auto-link fails
   - **Impact**: Workflows remain UNTRACKED even if Git match exists
   - **Mitigation**: Document expected Git structure (one canonical per hash)

2. **Inconsistent State Fallback**:
   - **Issue**: Defaults to UNTRACKED for ambiguous states (Line 237)
   - **Impact**: Could mask real issues (e.g., data corruption)
   - **Mitigation**: Log inconsistent states for investigation

3. **Sidecar File Failure Silently Ignored**:
   - **Issue**: Sidecar ingestion errors caught but not reported (Lines 222-224)
   - **Impact**: Mappings not restored from sidecar, remain UNTRACKED
   - **Mitigation**: Collect sidecar errors in sync results

**Low Risk**:

1. **Timestamp Normalization**:
   - **Issue**: Custom timestamp normalization (Line 85: removes 'Z', microseconds)
   - **Impact**: Could miss legitimate timestamp changes if logic incorrect
   - **Mitigation**: Use standard ISO8601 comparison

2. **Registry Statistics Unused**:
   - **Issue**: `get_registry_stats()` exists (Lines 63-72) but never called
   - **Impact**: No visibility into collision detection in production
   - **Mitigation**: Expose stats via monitoring endpoint

---

## 10. Code References

### Primary Files

| File | Lines | Purpose |
|------|-------|---------|
| `app/services/canonical_workflow_service.py` | 1-424 | Core identity, hash computation, status rules |
| `app/services/canonical_env_sync_service.py` | 1-787 | n8n → DB sync, auto-linking |
| `app/services/canonical_repo_sync_service.py` | 1-301 | Git → DB sync, sidecar ingestion |
| `app/schemas/canonical_workflow.py` | 1-356 | Status enum, models, precedence docs |
| `app/services/promotion_service.py` | 90-196 | Workflow normalization for hashing |

### Migrations

| Migration | Lines | Purpose |
|-----------|-------|---------|
| `dcd2f2c8774d_create_canonical_workflow_tables.py` | 1-282 | Table creation, constraints, indexes |

### Functions Reference

| Function | File | Lines | Purpose |
|----------|------|-------|---------|
| `compute_workflow_hash()` | canonical_workflow_service.py | 75-156 | Hash computation with collision detection |
| `compute_workflow_mapping_status()` | canonical_workflow_service.py | 159-237 | Status precedence logic |
| `_try_auto_link_by_hash()` | canonical_env_sync_service.py | 494-554 | Auto-link algorithm |
| `normalize_workflow_for_comparison()` | promotion_service.py | 90-161 | Workflow normalization |
| `_detect_hash_collision()` | canonical_env_sync_service.py | 27-77 | Collision detection during env sync |

---

## 11. Recommendations

### Immediate Actions (Pre-MVP)

1. **Persist Collision Registry**:
   - Move `_hash_collision_registry` from in-memory to database table
   - Create `workflow_hash_collisions` table with detection metadata
   - Query on startup to rebuild registry

2. **Fail-Fast on Unresolved Collisions**:
   - Change Line 147 to `raise ValueError("Hash collision without canonical_id")`
   - Force investigation instead of silent corruption

3. **Expose Collision Warnings in UI**:
   - Add collision_warnings to sync API responses
   - Display warnings in admin dashboard
   - Alert on first collision detection

### Post-MVP Improvements

1. **Automatic Collision Resolution**:
   - Append workflow name to normalized content for secondary hash
   - Use hierarchical hashing: `primary_hash + secondary_hash`

2. **Registry Statistics Dashboard**:
   - Expose `get_registry_stats()` via admin API
   - Monitor collision rate over time
   - Alert on unexpected registry growth

3. **Sidecar Error Reporting**:
   - Collect sidecar errors in `results["sidecar_errors"]`
   - Display in sync UI with retry option

4. **Canonical ID Validation**:
   - Add schema validation for canonical_id format (UUID)
   - Reject non-UUID canonical_ids early

---

## 12. Summary

The canonical workflow identity and mapping system establishes:

1. **Stable Identity**: canonical_id (UUID) as cross-environment identifier
2. **Content-Based Matching**: SHA256 hash for auto-linking and drift detection
3. **Status Precedence**: Clear rules for 5 workflow states (DELETED > IGNORED > MISSING > UNTRACKED > LINKED)
4. **Auto-Linking**: Zero-touch workflow mapping via exact hash matches
5. **Collision Detection**: In-memory registry with deterministic fallback strategies

**Critical Path**:
- Git Sync → canonical_workflow_git_state (git_content_hash)
- Env Sync → workflow_env_map (env_content_hash, auto-link by hash)
- Status Computation → precedence rules determine LINKED/UNTRACKED/MISSING/IGNORED/DELETED

**Success Metrics**:
- Auto-link rate: % of workflows linked without manual intervention
- Collision rate: Collisions detected per 10k workflows
- Status consistency: % of workflows in expected states

---

**Document Version**: 1.0
**Last Updated**: 2026-01-14
**Author**: Claude (Task Executor)
**Status**: ✅ Completed
