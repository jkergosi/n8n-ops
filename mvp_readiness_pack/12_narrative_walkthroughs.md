# 12 - Narrative Walkthroughs

**Generated:** 2026-01-14
**Purpose:** Step-by-step walkthroughs of key scenarios with code flow tracing

This document provides detailed narrative walkthroughs for the most critical user journeys through the WorkflowOps system, tracing the exact code paths, service calls, database mutations, and API interactions.

> **Terminology Note:** This document uses internal technical terms (e.g., "canonical", `/canonical/` API paths) alongside code references. For user-facing terminology mapping, see `14_terminology_and_rules.md`:
> - **User-facing:** "Source-Managed Workflow" = **Internal:** "Canonical Workflow"
> - **User-facing:** "Unmanaged Workflow" = **Internal:** "Unmapped Workflow"
> - API paths and database tables retain internal naming (e.g., `/canonical/`, `canonical_workflows`)

---

## Scenario 1: First-Time Environment Setup with Git Sync

**User Story:** An admin creates a new staging environment and performs the first sync to discover workflows from n8n and Git.

### Initial State
- Environment record created in DB (`environments` table)
- Git repo configured: `git_repo_url`, `git_pat`, `git_branch`, `git_folder`
- n8n instance configured: `n8n_url`, `n8n_api_key`
- No workflows yet in `workflow_env_map` for this environment

### Step-by-Step Flow

#### 1. User Triggers Manual Sync

**UI Action:**
User clicks "Sync Now" button in Environments page

**API Call:**
```http
POST /api/v1/canonical/sync/request
{
  "environment_id": "env-staging-123",
  "trigger": "manual"
}
```

**File:** `app-back/app/api/endpoints/canonical_workflows.py:request_sync()`

**Code Path:**
```python
# Line ~150: Endpoint handler
async def request_sync(request: SyncRequest, ...):
    # Calls sync orchestrator
    job, is_new = await SyncOrchestratorService.request_sync(
        tenant_id=tenant_id,
        environment_id=request.environment_id,
        created_by=current_user_id
    )
```

---

#### 2. Sync Orchestrator Creates Background Job

**File:** `app-back/app/services/sync_orchestrator_service.py:request_sync()`
**Lines:** 83-149

**Logic:**
1. **Check for active job** (lines 106-116)
   - Query: `SELECT * FROM background_jobs WHERE environment_id = ? AND status IN ('pending', 'running')`
   - If exists → return existing job (idempotency)
   - If not → continue

2. **Update sync timestamp** (line 119-123)
   - Prevents duplicate scheduler triggers
   - Updates: `environments.last_sync_attempted_at = NOW()`

3. **Create atomic background job** (line 128-133)
   - Job type: `CANONICAL_ENV_SYNC`
   - Status: `PENDING`
   - Database constraint prevents duplicates

**Database Mutations:**
```sql
-- Update environment
UPDATE environments
SET last_sync_attempted_at = NOW()
WHERE id = 'env-staging-123';

-- Create job
INSERT INTO background_jobs (
  id, tenant_id, environment_id,
  job_type, status, created_at
) VALUES (
  'job-abc123', 'tenant-1', 'env-staging-123',
  'canonical_env_sync', 'pending', NOW()
);
```

**Response to UI:**
```json
{
  "job_id": "job-abc123",
  "status": "pending",
  "is_new": true
}
```

---

#### 3. Background Worker Picks Up Job

**File:** `app-back/app/services/background_job_service.py:_process_job()`

**Worker Logic:**
1. Poll `background_jobs` table for `PENDING` jobs
2. Update status: `PENDING` → `RUNNING`
3. Dispatch to handler based on `job_type`

**For `CANONICAL_ENV_SYNC`:**

**File:** `app-back/app/services/canonical_env_sync_service.py:sync_environment()`
**Lines:** 92-300+

---

#### 4. Phase 1: Discover Workflows from n8n

**Service:** `CanonicalEnvSyncService.sync_environment()`
**Lines:** 133-149

**SSE Progress Event:**
```json
{
  "job_id": "job-abc123",
  "environment_id": "env-staging-123",
  "status": "running",
  "current_step": "discovering_workflows",
  "message": "Discovering workflows from n8n..."
}
```

**n8n API Call:**
```python
# Line ~150+: Fetch all workflows from n8n
adapter = ProviderRegistry.get_adapter_for_environment(environment)
workflows = await adapter.get_all_workflows()
# GET https://staging.n8n.example.com/api/v1/workflows
```

**Response Example:**
```json
[
  {
    "id": "wf-001",
    "name": "Customer Onboarding",
    "active": true,
    "updatedAt": "2026-01-10T14:30:00.000Z",
    "nodes": [...],
    "connections": {...}
  },
  {
    "id": "wf-002",
    "name": "Invoice Processing",
    "active": false,
    "updatedAt": "2026-01-09T10:15:00.000Z",
    "nodes": [...],
    "connections": {...}
  }
]
```

---

#### 5. Phase 2: Process Each Workflow (Batched)

**File:** `canonical_env_sync_service.py` (lines 150-280)

**For each workflow (batch size = 25):**

##### 5a. Normalize and Hash Workflow

```python
# Normalize workflow (remove metadata)
normalized = normalize_workflow_for_comparison(workflow)

# Compute content hash
env_content_hash = compute_workflow_hash(workflow)
# SHA256 of normalized JSON → "a1b2c3d4e5f6..."
```

**File:** `app/services/canonical_workflow_service.py:compute_workflow_hash()`
**File:** `app/services/promotion_service.py:normalize_workflow_for_comparison()`

**Normalization removes:**
- `id`, `createdAt`, `updatedAt`, `versionId`
- `active`, `tags`, `shared`, `scopes`
- Node positions, credential IDs (keeps names only)

##### 5b. Check for Existing Mapping

```sql
SELECT * FROM workflow_env_map
WHERE environment_id = 'env-staging-123'
  AND n8n_workflow_id = 'wf-001';
```

**If NOT found → Create UNMAPPED workflow:**

```python
# Check for canonical match by hash
canonical = await db_service.find_canonical_by_hash(env_content_hash)

if canonical:
    # Auto-link: Found exact match
    status = WorkflowMappingStatus.LINKED
    canonical_id = canonical['id']
else:
    # No match: Create as unmapped
    status = WorkflowMappingStatus.UNMAPPED
    canonical_id = None
```

**Database Mutation:**
```sql
INSERT INTO workflow_env_map (
  id, tenant_id, environment_id,
  n8n_workflow_id, canonical_id, status,
  workflow_name, workflow_data,
  env_content_hash, n8n_updated_at,
  created_at, updated_at
) VALUES (
  'map-001', 'tenant-1', 'env-staging-123',
  'wf-001', NULL, 'unmapped',
  'Customer Onboarding', {...},
  'a1b2c3d4e5f6...', '2026-01-10T14:30:00Z',
  NOW(), NOW()
);
```

**If FOUND → Update existing mapping:**

```python
# Check if anything changed
if existing['n8n_updated_at'] == workflow['updatedAt']:
    # Short-circuit: No changes
    results['workflows_skipped'] += 1
    continue

# Update mapping
await db_service.update_workflow_mapping(
    mapping_id=existing['id'],
    workflow_data=workflow,
    env_content_hash=env_content_hash,
    n8n_updated_at=workflow['updatedAt']
)
```

##### 5c. Checkpoint After Each Batch

**Every 25 workflows:**

```python
# Save checkpoint data to job metadata
checkpoint = {
    "last_processed_index": 25,
    "workflows_synced": 20,
    "workflows_skipped": 5,
    "errors": []
}

await background_job_service.update_job_progress(
    job_id=job_id,
    progress_percent=25,
    metadata=checkpoint
)
```

**Purpose:** If job fails, resume from last checkpoint

---

#### 6. Phase 3: Sync from Git Repository

**File:** `canonical_repo_sync_service.py:sync_repository()`
**Lines:** 83-200+

**GitHub API Call:**
```python
github_service = GitHubService(
    token=environment['git_pat'],
    repo_owner="acme-corp",
    repo_name="workflows",
    branch="main"
)

# Fetch all .json files from git_folder
workflow_files = await github_service.get_all_workflow_files_from_github(
    git_folder="staging",
    commit_sha=None  # Latest
)
```

**GitHub API:**
```http
GET https://api.github.com/repos/acme-corp/workflows/contents/staging
Authorization: Bearer ghp_xxx
```

**Response:**
```json
[
  {
    "name": "customer_onboarding.json",
    "path": "staging/customer_onboarding.json",
    "sha": "abc123",
    "download_url": "https://raw.githubusercontent.com/.../customer_onboarding.json"
  },
  {
    "name": "invoice_processing.json",
    "path": "staging/invoice_processing.json",
    "sha": "def456",
    "download_url": "https://raw.githubusercontent.com/.../invoice_processing.json"
  }
]
```

**For each .json file:**

1. **Download workflow content**
   ```http
   GET https://raw.githubusercontent.com/.../customer_onboarding.json
   ```

2. **Check for sidecar metadata**
   ```http
   GET https://raw.githubusercontent.com/.../customer_onboarding.wfo.json
   ```

   **Sidecar format:**
   ```json
   {
     "canonical_id": "canon-uuid-001",
     "canonical_slug": "customer_onboarding",
     "tags": ["onboarding", "customers"],
     "created_by": "admin@example.com"
   }
   ```

3. **Compute git_content_hash**
   ```python
   normalized = normalize_workflow_for_comparison(git_workflow)
   git_content_hash = compute_workflow_hash(normalized)
   ```

4. **Upsert canonical_workflows**
   ```sql
   INSERT INTO canonical_workflows (
     id, tenant_id, canonical_slug, name,
     content_hash, workflow_definition,
     git_file_path, git_branch, git_commit_sha,
     created_at, updated_at
   ) VALUES (
     'canon-uuid-001', 'tenant-1', 'customer_onboarding',
     'Customer Onboarding',
     'a1b2c3d4e5f6...', {...},
     'staging/customer_onboarding.json', 'main', 'abc123',
     NOW(), NOW()
   )
   ON CONFLICT (id) DO UPDATE SET
     content_hash = EXCLUDED.content_hash,
     workflow_definition = EXCLUDED.workflow_definition,
     git_commit_sha = EXCLUDED.git_commit_sha,
     updated_at = NOW();
   ```

5. **Update workflow_env_map with git_content_hash**
   ```sql
   UPDATE workflow_env_map
   SET git_content_hash = 'a1b2c3d4e5f6...',
       git_last_synced_at = NOW()
   WHERE canonical_id = 'canon-uuid-001'
     AND environment_id = 'env-staging-123';
   ```

---

#### 7. Phase 4: Detect Drift

> **Note:** Drift detection only runs for **onboarded** environments (those with a valid `current.json` baseline). NEW environments (not yet onboarded) short-circuit before any comparison logic.

**Pre-check (NEW gate):**
```python
is_onboarded = await git_snapshot_service.is_env_onboarded(tenant_id, environment_id)
if not is_onboarded:
    # NEW environment - no baseline, skip drift comparison
    drift_status = DriftStatus.NEW
    return  # No per-workflow diffs computed
```

**For onboarded environments, after both n8n and Git syncs complete:**

**Logic:**
```python
# For each workflow in workflow_env_map
for mapping in all_mappings:
    if mapping['env_content_hash'] != mapping['git_content_hash']:
        # DRIFT DETECTED
        drift_status = "DRIFT_DETECTED"
    elif mapping['canonical_id'] is None:
        # NOT LINKED TO CANONICAL (unmapped) - no comparison possible
        # UI shows "Runtime only" for this workflow
        continue
    else:
        # IN SYNC
        drift_status = "IN_SYNC"
```

**Database Mutation:**
```sql
UPDATE workflow_env_map
SET drift_status = 'DRIFT_DETECTED'
WHERE id = 'map-001'
  AND env_content_hash != git_content_hash;
```

**If drift detected → Create drift incident:**

**File:** `drift_incident_service.py:create_incident()`

```sql
INSERT INTO drift_incidents (
  id, tenant_id, environment_id,
  status, severity, detected_at,
  drift_snapshot, affected_workflows
) VALUES (
  'incident-001', 'tenant-1', 'env-staging-123',
  'detected', 'medium', NOW(),
  {...},  -- Full snapshot of drift details
  [{"workflow_id": "wf-001", "drift_type": "modified"}]
);
```

---

#### 8. Job Completion & Final State

**File:** `canonical_env_sync_service.py` (end of sync_environment)

**SSE Progress Event:**
```json
{
  "job_id": "job-abc123",
  "status": "completed",
  "current_step": "finished",
  "progress_percent": 100,
  "message": "Sync completed successfully",
  "result": {
    "workflows_synced": 45,
    "workflows_skipped": 3,
    "workflows_linked": 30,
    "workflows_unmapped": 15,
    "workflows_missing": 0,
    "errors": []
  }
}
```

**Database Mutations:**
```sql
-- Update job status
UPDATE background_jobs
SET status = 'completed',
    completed_at = NOW(),
    result = {...}
WHERE id = 'job-abc123';

-- Update environment sync timestamps
UPDATE environments
SET last_sync_completed_at = NOW(),
    last_sync_succeeded = true,
    workflow_count = 45,
    drift_status = 'DRIFT_DETECTED'
WHERE id = 'env-staging-123';
```

**Final State:**
- **workflow_env_map:** 45 records created
  - 30 with `status = 'linked'` (matched to Git)
  - 15 with `status = 'unmapped'` (not in Git)
- **canonical_workflows:** 30 records (one per Git file)
- **drift_incidents:** 1 incident created (for workflows with drift)

---

## Scenario 2: Promoting a Workflow from Dev to Staging

**User Story:** Developer has tested a workflow in Dev, commits to Git, and wants to promote it to Staging through the UI.

### Initial State

**Dev Environment:**
- Workflow: "Order Processing v2" (`wf-dev-007`)
- Status: `LINKED` to canonical `order_processing`
- Git: Already committed to `dev/order_processing.json`
- Changes: Added new node for inventory check

**Staging Environment:**
- Old version exists: `wf-staging-005`
- Status: `LINKED` to same canonical
- No recent changes (in sync with Git)

**Pipeline:**
```json
{
  "id": "pipeline-001",
  "name": "Dev → Staging → Prod",
  "stages": [
    {
      "name": "dev",
      "environment_id": "env-dev-123",
      "gates": {"require_approval": false}
    },
    {
      "name": "staging",
      "environment_id": "env-staging-123",
      "gates": {
        "require_approval": true,
        "require_all_tests_passed": false
      }
    },
    {
      "name": "prod",
      "environment_id": "env-prod-123",
      "gates": {"require_approval": true}
    }
  ]
}
```

---

### Step-by-Step Flow

#### 1. User Initiates Promotion (UI)

**Action:** User clicks "Promote to Staging" button on workflow detail page

**API Call:**
```http
POST /api/v1/promotions/preview
{
  "pipeline_id": "pipeline-001",
  "source_stage": "dev",
  "target_stage": "staging",
  "workflow_selection": {
    "workflow_ids": ["wf-dev-007"],
    "selection_mode": "selected"
  }
}
```

**File:** `app-back/app/api/endpoints/promotions.py:preview_promotion()`

---

#### 2. Promotion Service Validates & Previews

**File:** `app/services/promotion_service.py:preview_promotion()`
**Lines:** 200-400 (estimated)

##### 2a. Validate Pipeline Stages

```python
# Verify source and target exist in pipeline
pipeline = await db_service.get_pipeline(pipeline_id)
source_stage = next(s for s in pipeline['stages'] if s['name'] == 'dev')
target_stage = next(s for s in pipeline['stages'] if s['name'] == 'staging')

# Verify user has permission to promote
await rbac_service.check_permission(
    user_id=current_user_id,
    resource_type="promotion",
    action="create"
)
```

##### 2b. Fetch Source Workflow

```python
# Get workflow from Dev environment
dev_env = await db_service.get_environment(source_stage['environment_id'])
adapter = ProviderRegistry.get_adapter_for_environment(dev_env)

source_workflow = await adapter.get_workflow(workflow_id='wf-dev-007')
```

**n8n API Call:**
```http
GET https://dev.n8n.example.com/api/v1/workflows/wf-dev-007
Authorization: X-N8N-API-KEY: dev-api-key-xxx
```

**Response:**
```json
{
  "id": "wf-dev-007",
  "name": "Order Processing v2",
  "active": true,
  "nodes": [
    {
      "name": "Webhook Trigger",
      "type": "n8n-nodes-base.webhook",
      "parameters": {...},
      "credentials": {
        "httpAuth": {"id": "cred-dev-001", "name": "API Auth"}
      }
    },
    {
      "name": "Check Inventory",  // NEW NODE
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {"url": "{{$env.INVENTORY_API}}"}
    },
    {
      "name": "Create Order",
      "type": "n8n-nodes-base.postgres",
      "credentials": {
        "postgres": {"id": "cred-dev-005", "name": "Orders DB"}
      }
    }
  ],
  "connections": {...},
  "settings": {...}
}
```

##### 2c. Check for Target Workflow

```python
# Check if workflow already exists in staging
staging_env = await db_service.get_environment(target_stage['environment_id'])

# Query workflow_env_map for canonical match
target_mapping = await db_service.get_workflow_mapping_by_canonical(
    environment_id='env-staging-123',
    canonical_id='order_processing'
)

if target_mapping:
    # Workflow exists → UPDATE scenario
    change_type = WorkflowChangeType.UPDATED
    target_workflow_id = target_mapping['n8n_workflow_id']  # wf-staging-005
else:
    # Workflow doesn't exist → CREATE scenario
    change_type = WorkflowChangeType.CREATED
    target_workflow_id = None
```

##### 2d. Detect Conflicts

```python
# If UPDATE, fetch current target workflow
if change_type == WorkflowChangeType.UPDATED:
    adapter = ProviderRegistry.get_adapter_for_environment(staging_env)
    target_workflow = await adapter.get_workflow(target_workflow_id)

    # Compare normalized payloads
    source_normalized = normalize_workflow_for_comparison(source_workflow)
    target_normalized = normalize_workflow_for_comparison(target_workflow)

    if target_normalized != expected_from_git:
        # HOTFIX DETECTED
        conflict = {
            "type": "hotfix_in_target",
            "workflow_id": target_workflow_id,
            "message": "Target has uncommitted changes (hotfix)"
        }
```

**Conflict Detection Logic:**

**File:** `promotion_service.py` lines 600-800

```python
# Check if target has diverged from Git (hotfix)
git_hash = target_mapping['git_content_hash']
env_hash = compute_workflow_hash(target_workflow)

if env_hash != git_hash:
    # Target has local changes not in Git
    conflicts.append({
        "workflow_id": target_workflow_id,
        "conflict_type": "hotfix",
        "description": "Target environment has uncommitted changes"
    })
```

##### 2e. Generate Diff Summary

```python
# Use diff_service to generate detailed comparison
diff_result = compare_workflows(
    source=source_normalized,
    target=target_normalized
)

preview = {
    "change_type": "updated",
    "workflow_name": "Order Processing v2",
    "nodes_added": 1,      # "Check Inventory" node
    "nodes_removed": 0,
    "nodes_modified": 0,
    "connections_changed": True,  # New connections for inventory node
    "settings_changed": False,
    "conflicts": [],
    "diff_summary": diff_result
}
```

##### 2f. Check Gates

```python
# Evaluate promotion gates for target stage
gates = target_stage['gates']

gate_results = []

if gates.get('require_approval'):
    gate_results.append({
        "gate_type": "require_approval",
        "status": "pending",
        "message": "Requires approval from staging admins"
    })

if gates.get('require_all_tests_passed'):
    # Check if all tests passed in source
    tests_passed = await check_tests_status(workflow_id='wf-dev-007')
    gate_results.append({
        "gate_type": "require_all_tests_passed",
        "status": "passed" if tests_passed else "failed"
    })
```

**Response to UI:**
```json
{
  "promotion_id": null,  // Not created yet, just preview
  "pipeline_id": "pipeline-001",
  "source_stage": "dev",
  "target_stage": "staging",
  "workflows": [
    {
      "workflow_id": "wf-dev-007",
      "workflow_name": "Order Processing v2",
      "change_type": "updated",
      "target_workflow_id": "wf-staging-005",
      "nodes_added": 1,
      "nodes_removed": 0,
      "nodes_modified": 0,
      "connections_changed": true,
      "conflicts": [],
      "diff_summary": {...}
    }
  ],
  "gate_results": [
    {
      "gate_type": "require_approval",
      "status": "pending",
      "required": true
    }
  ],
  "can_proceed": false,  // Blocked by approval gate
  "estimated_impact": "low"
}
```

---

#### 3. User Confirms & Creates Promotion

**UI Action:** User reviews preview, clicks "Create Promotion"

**API Call:**
```http
POST /api/v1/promotions
{
  "pipeline_id": "pipeline-001",
  "source_stage": "dev",
  "target_stage": "staging",
  "workflow_selection": {
    "workflow_ids": ["wf-dev-007"]
  },
  "options": {
    "allow_overwriting_hotfixes": false,
    "allow_force_promotion_on_conflicts": false
  }
}
```

**File:** `app/api/endpoints/promotions.py:create_promotion()`

**Database Mutation:**
```sql
INSERT INTO promotions (
  id, tenant_id, pipeline_id,
  source_stage, target_stage,
  status, workflow_selection,
  created_by, created_at
) VALUES (
  'promo-001', 'tenant-1', 'pipeline-001',
  'dev', 'staging',
  'pending_approval', {...},  -- Requires approval
  'user-admin-1', NOW()
);
```

**Response:**
```json
{
  "promotion_id": "promo-001",
  "status": "pending_approval",
  "requires_approval": true,
  "approvers": ["admin@example.com", "lead@example.com"],
  "created_at": "2026-01-14T10:30:00Z"
}
```

---

#### 4. Approver Reviews & Approves

**UI Action:** Approver gets notification, reviews promotion, clicks "Approve"

**API Call:**
```http
POST /api/v1/promotions/promo-001/approve
{
  "comment": "Changes look good, inventory check is needed"
}
```

**File:** `app/api/endpoints/promotions.py:approve_promotion()`

**Validation:**
```python
# Check if user is authorized approver
pipeline = await db_service.get_pipeline(promotion['pipeline_id'])
is_approver = await rbac_service.is_pipeline_approver(
    user_id=current_user_id,
    pipeline_id=pipeline_id,
    stage_name='staging'
)

if not is_approver:
    raise HTTPException(403, "Not authorized to approve")
```

**Database Mutation:**
```sql
UPDATE promotions
SET status = 'approved',
    approved_by = 'user-approver-2',
    approved_at = NOW(),
    approval_comment = 'Changes look good, inventory check is needed'
WHERE id = 'promo-001';
```

**SSE Event to UI:**
```json
{
  "event_type": "promotion.approved",
  "promotion_id": "promo-001",
  "approved_by": "lead@example.com",
  "timestamp": "2026-01-14T10:35:00Z"
}
```

---

#### 5. User Triggers Execution

**API Call:**
```http
POST /api/v1/promotions/promo-001/execute
```

**File:** `app/services/promotion_service.py:execute_promotion()`
**Lines:** 800-1500

##### 5a. Pre-Execution Validation

**Lines 810-850:**
```python
# Verify promotion is approved
if promotion['status'] != 'approved':
    raise InvalidStateError("Promotion must be approved before execution")

# Check feature entitlement
await feature_service.check_entitlement(
    tenant_id=tenant_id,
    feature="workflow_ci_cd"
)

# Acquire promotion lock (prevent concurrent promotions)
lock_acquired = await promotion_lock_service.acquire_lock(
    environment_id=target_environment_id
)

if not lock_acquired:
    raise ConflictError("Another promotion is already running on this environment")
```

**Update status:**
```sql
UPDATE promotions
SET status = 'running',
    execution_started_at = NOW()
WHERE id = 'promo-001';
```

##### 5b. Create Pre-Promotion Snapshot

**Lines 860-920:**

**Critical Invariant (T002):** Snapshot MUST be created before ANY mutations

```python
# Snapshot all workflows in target environment
snapshot_id = await create_pre_promotion_snapshot(
    tenant_id=tenant_id,
    environment_id=target_environment_id,
    promotion_id='promo-001'
)

# Update promotion with snapshot reference
await db_service.update_promotion(
    promotion_id='promo-001',
    target_pre_snapshot_id=snapshot_id
)
```

**Snapshot Creation Process:**

**File:** `promotion_service.py:create_pre_promotion_snapshot()`

1. **Fetch all workflows from target**
   ```python
   adapter = ProviderRegistry.get_adapter_for_environment(staging_env)
   all_workflows = await adapter.get_all_workflows()
   ```

2. **Store snapshot in database**
   ```sql
   INSERT INTO snapshots (
     id, tenant_id, environment_id,
     promotion_id, snapshot_type,
     workflow_count, workflows_data,
     created_at
   ) VALUES (
     'snap-001', 'tenant-1', 'env-staging-123',
     'promo-001', 'pre_promotion',
     45, {...},  -- All 45 workflows serialized
     NOW()
   );
   ```

3. **Optionally commit to Git**
   ```python
   # Create Git tag: snapshots/promo-001-pre
   await github_service.create_snapshot_tag(
       tag_name=f"snapshots/promo-001-pre",
       message="Pre-promotion snapshot for promo-001"
   )
   ```

##### 5c. Transform Source Workflow for Target

**Lines 930-1100:**

**Credential Rewriting:**

**File:** `promotion_service.py:_rewrite_credentials()`

```python
def _rewrite_credentials(workflow, source_env, target_env):
    """
    Rewrite credential references from source to target environment.

    Strategy:
    1. Match by credential name
    2. If name match found → replace ID
    3. If no match → log warning, keep original name
    """
    for node in workflow['nodes']:
        if 'credentials' in node:
            for cred_type, cred_ref in node['credentials'].items():
                source_name = cred_ref['name']

                # Lookup target credential by name
                target_cred = await db_service.find_credential_by_name(
                    environment_id=target_env['id'],
                    credential_name=source_name
                )

                if target_cred:
                    # Replace with target credential ID
                    node['credentials'][cred_type] = {
                        'id': target_cred['id'],
                        'name': target_cred['name']
                    }
                else:
                    # No match: keep name, remove ID (will fail on runtime if not found)
                    logger.warning(f"Credential '{source_name}' not found in target")
                    node['credentials'][cred_type] = {
                        'name': source_name
                    }
```

**Environment Variable Substitution:**

```python
def _substitute_env_vars(workflow, target_env):
    """
    Replace environment-specific variables.

    Example:
      Dev:     {{$env.API_URL}} → "https://api-dev.example.com"
      Staging: {{$env.API_URL}} → "https://api-staging.example.com"
    """
    # Env vars are resolved at runtime by n8n, no transformation needed
    # unless explicitly specified in promotion options
    pass
```

**Transformed Workflow:**
```json
{
  "name": "Order Processing v2",
  "nodes": [
    {
      "name": "Webhook Trigger",
      "type": "n8n-nodes-base.webhook",
      "credentials": {
        "httpAuth": {
          "id": "cred-staging-010",  // REWRITTEN
          "name": "API Auth"
        }
      }
    },
    {
      "name": "Check Inventory",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "{{$env.INVENTORY_API}}"  // Will resolve to staging URL at runtime
      }
    },
    {
      "name": "Create Order",
      "type": "n8n-nodes-base.postgres",
      "credentials": {
        "postgres": {
          "id": "cred-staging-015",  // REWRITTEN
          "name": "Orders DB"
        }
      }
    }
  ],
  "connections": {...},
  "settings": {...}
}
```

##### 5d. Execute Promotion to Target

**Lines 1120-1250:**

**For UPDATE scenario:**

```python
# Update existing workflow in staging
adapter = ProviderRegistry.get_adapter_for_environment(staging_env)

try:
    result = await adapter.update_workflow(
        workflow_id='wf-staging-005',
        workflow_data=transformed_workflow
    )
except Exception as e:
    # FAILURE: Trigger rollback
    await _rollback_promotion(
        promotion_id='promo-001',
        snapshot_id='snap-001',
        failed_workflow='wf-staging-005',
        error=str(e)
    )
    raise
```

**n8n API Call:**
```http
PATCH https://staging.n8n.example.com/api/v1/workflows/wf-staging-005
Authorization: X-N8N-API-KEY: staging-api-key-xxx
Content-Type: application/json

{
  "name": "Order Processing v2",
  "nodes": [...],  // Transformed nodes with staging credentials
  "connections": {...}
}
```

**n8n Response:**
```json
{
  "id": "wf-staging-005",
  "name": "Order Processing v2",
  "updatedAt": "2026-01-14T10:40:15.000Z",
  "versionId": "v42"
}
```

##### 5e. Update workflow_env_map

```python
# Compute new hash after promotion
new_env_hash = compute_workflow_hash(transformed_workflow)

await db_service.update_workflow_mapping(
    environment_id='env-staging-123',
    n8n_workflow_id='wf-staging-005',
    workflow_data=transformed_workflow,
    env_content_hash=new_env_hash,
    n8n_updated_at='2026-01-14T10:40:15.000Z'
)
```

**Database Mutation:**
```sql
UPDATE workflow_env_map
SET workflow_data = {...},
    env_content_hash = 'f7g8h9i0j1k2...',  -- New hash
    n8n_updated_at = '2026-01-14T10:40:15Z',
    updated_at = NOW()
WHERE environment_id = 'env-staging-123'
  AND n8n_workflow_id = 'wf-staging-005';
```

##### 5f. Create Post-Promotion Snapshot

```python
snapshot_id_post = await create_post_promotion_snapshot(
    tenant_id=tenant_id,
    environment_id='env-staging-123',
    promotion_id='promo-001'
)

await db_service.update_promotion(
    promotion_id='promo-001',
    target_post_snapshot_id=snapshot_id_post
)
```

##### 5g. Mark Promotion as Complete

**Lines 1300-1350:**

```sql
UPDATE promotions
SET status = 'completed',
    execution_completed_at = NOW(),
    execution_result = {
      "workflows_promoted": 1,
      "workflows_failed": 0,
      "credentials_rewritten": 2,
      "rollback_performed": false,
      "target_pre_snapshot_id": "snap-001",
      "target_post_snapshot_id": "snap-002"
    }
WHERE id = 'promo-001';
```

**Release promotion lock:**
```python
await promotion_lock_service.release_lock(
    environment_id='env-staging-123'
)
```

**SSE Event:**
```json
{
  "event_type": "promotion.completed",
  "promotion_id": "promo-001",
  "status": "completed",
  "workflows_promoted": 1,
  "execution_time_ms": 5430,
  "timestamp": "2026-01-14T10:40:20Z"
}
```

---

### Final State After Promotion

**Staging Environment:**
- Workflow `wf-staging-005` updated with new "Check Inventory" node
- Credentials rewritten to staging credential IDs
- `workflow_env_map.env_content_hash` updated
- Drift status: `IN_SYNC` (matches Git after sync)

**Database Records:**
- `promotions` table: 1 record (`status = 'completed'`)
- `snapshots` table: 2 records (pre and post)
- `audit_log` table: Entries for approval, execution, credential rewrites

**Git Repository:**
- No changes (source already in Git from dev workflow)
- Optional: Snapshot tags created

---

## Scenario 3: Drift Detection and Incident Resolution

**User Story:** A developer makes a hotfix directly in production n8n (bypassing Git), drift is detected automatically, and the team resolves it through the incident workflow.

### Initial State

**Production Environment:**
- Workflow: "Payment Gateway" (`wf-prod-042`)
- Status: `LINKED` to canonical `payment_gateway`
- Last sync: 2 hours ago
- Drift status: `IN_SYNC`

**Git Repository:**
- File: `prod/payment_gateway.json`
- Last commit: "Add fraud detection" (3 days ago)
- Commit SHA: `abc123def456`

**Drift Scheduler:**
- Runs every 30 minutes for production
- Next check: Due in 5 minutes

---

### Step-by-Step Flow

#### 1. Developer Makes Hotfix in Production

**Direct n8n UI Edit:**
- Developer logs into production n8n
- Edits "Payment Gateway" workflow
- **Change:** Updates API endpoint URL for payment processor (emergency fix)
- Saves workflow

**n8n Internal State:**
```json
{
  "id": "wf-prod-042",
  "name": "Payment Gateway",
  "updatedAt": "2026-01-14T15:22:00.000Z",  // NEW timestamp
  "nodes": [
    {
      "name": "Call Payment API",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "https://api-new.paymentprocessor.com/charge"  // CHANGED
        // Was: "https://api.paymentprocessor.com/charge"
      }
    }
  ]
}
```

**No Git commit made** (hotfix bypassed version control)

---

#### 2. Drift Scheduler Detects Change

**Scheduler Execution:**

**File:** `app/services/drift_scheduler.py:start_all_drift_schedulers()`
**Background Task:** Runs every 30 minutes

**Triggered at:** `2026-01-14T15:25:00Z`

**Scheduler Logic:**
```python
async def check_drift_for_environment(environment_id, tenant_id):
    # Call drift detection service
    result = await drift_detection_service.detect_drift(
        tenant_id=tenant_id,
        environment_id=environment_id,
        update_status=True  # Update env drift status
    )

    if result.with_drift > 0:
        # Drift detected → trigger incident creation
        await drift_incident_service.create_incidents_for_drift(
            tenant_id=tenant_id,
            environment_id=environment_id,
            drift_summary=result
        )
```

---

#### 3. Drift Detection Service Compares Workflow

**File:** `app/services/drift_detection_service.py:detect_drift()`
**Lines:** 73-150

##### 3a. Fetch Current Workflow from n8n

```python
# Get environment config
environment = await db_service.get_environment('env-prod-123', tenant_id)

# Create adapter
adapter = ProviderRegistry.get_adapter_for_environment(environment)

# Fetch all workflows
workflows = await adapter.get_all_workflows()
```

**n8n API Call:**
```http
GET https://prod.n8n.example.com/api/v1/workflows
Authorization: X-N8N-API-KEY: prod-api-key-xxx
```

**Response includes:**
```json
{
  "id": "wf-prod-042",
  "name": "Payment Gateway",
  "updatedAt": "2026-01-14T15:22:00.000Z",  // NEWER than last sync
  "nodes": [...]  // Contains hotfix change
}
```

##### 3b. Fetch Canonical Workflow from Git

```python
# Get GitHub service
github_service = GitHubService(
    token=environment['git_pat'],
    repo_owner="acme-corp",
    repo_name="workflows",
    branch="main"
)

# Fetch workflow from Git
git_workflow = await github_service.get_workflow_from_github(
    file_path="prod/payment_gateway.json"
)
```

**GitHub API:**
```http
GET https://api.github.com/repos/acme-corp/workflows/contents/prod/payment_gateway.json
```

**Git Version (OLD):**
```json
{
  "name": "Payment Gateway",
  "nodes": [
    {
      "name": "Call Payment API",
      "parameters": {
        "url": "https://api.paymentprocessor.com/charge"  // OLD URL
      }
    }
  ]
}
```

##### 3c. Normalize and Compare

```python
# Normalize both versions
runtime_normalized = normalize_workflow_for_comparison(workflows['wf-prod-042'])
git_normalized = normalize_workflow_for_comparison(git_workflow)

# Compute hashes
env_hash = compute_workflow_hash(runtime_normalized)
git_hash = compute_workflow_hash(git_normalized)

# Compare
if env_hash != git_hash:
    # DRIFT DETECTED
    drift_detected = True
```

**Hash Comparison:**
```
env_hash:  "x9y8z7w6v5u4..."  (runtime with hotfix)
git_hash:  "a1b2c3d4e5f6..."  (git without hotfix)
→ Hashes differ → DRIFT
```

##### 3d. Generate Drift Details

**File:** `app/services/diff_service.py:compare_workflows()`

```python
diff_result = compare_workflows(
    source=git_normalized,
    target=runtime_normalized
)
```

**Diff Result:**
```json
{
  "has_changes": true,
  "nodes_added": 0,
  "nodes_removed": 0,
  "nodes_modified": 1,
  "connections_changed": false,
  "settings_changed": false,
  "node_changes": [
    {
      "node_name": "Call Payment API",
      "change_type": "modified",
      "fields_changed": ["parameters.url"],
      "old_value": "https://api.paymentprocessor.com/charge",
      "new_value": "https://api-new.paymentprocessor.com/charge"
    }
  ]
}
```

##### 3e. Update Environment Drift Status

```sql
UPDATE environments
SET drift_status = 'DRIFT_DETECTED',
    last_drift_detected_at = NOW(),
    drift_summary = {...}
WHERE id = 'env-prod-123';
```

---

#### 4. Create Drift Incident

**File:** `app/services/drift_incident_service.py:create_incident()`

**Database Mutation:**
```sql
INSERT INTO drift_incidents (
  id, tenant_id, environment_id,
  status, severity, detected_at,
  drift_snapshot, affected_workflows,
  detection_method, created_at
) VALUES (
  'incident-042', 'tenant-1', 'env-prod-123',
  'detected', 'high',  -- High severity for PROD
  '2026-01-14T15:25:00Z',
  {
    "environment_name": "Production",
    "total_workflows_drifted": 1,
    "detection_timestamp": "2026-01-14T15:25:00Z",
    "git_branch": "main",
    "git_commit_sha": "abc123def456"
  },
  [
    {
      "workflow_id": "wf-prod-042",
      "workflow_name": "Payment Gateway",
      "drift_type": "modified",
      "nodes_modified": 1,
      "change_summary": {
        "node_name": "Call Payment API",
        "field": "parameters.url",
        "old_value": "https://api.paymentprocessor.com/charge",
        "new_value": "https://api-new.paymentprocessor.com/charge"
      }
    }
  ],
  'scheduled',  -- Detected by scheduler
  NOW()
);
```

**Notification Sent:**

**File:** `app/services/notification_service.py:send_drift_alert()`

**Email to production admins:**
```
Subject: [DRIFT ALERT] Production environment has detected drift

Environment: Production
Workflows Affected: 1
  - Payment Gateway (modified)

Change Detected:
  Node: Call Payment API
  Field: parameters.url
  Old: https://api.paymentprocessor.com/charge
  New: https://api-new.paymentprocessor.com/charge

Detected At: 2026-01-14 15:25:00 UTC
Detection Method: Scheduled drift check

Action Required: Please review and resolve this incident.

View Incident: https://workflowops.example.com/incidents/incident-042
```

**SSE Event to UI:**
```json
{
  "event_type": "drift.detected",
  "incident_id": "incident-042",
  "environment_id": "env-prod-123",
  "severity": "high",
  "affected_workflows": 1,
  "timestamp": "2026-01-14T15:25:00Z"
}
```

---

#### 5. Team Acknowledges Incident

**UI Action:** On-call engineer receives alert, reviews incident, clicks "Acknowledge"

**API Call:**
```http
POST /api/v1/incidents/incident-042/acknowledge
{
  "acknowledged_by": "user-oncall-5",
  "comment": "Reviewing hotfix, will coordinate with team"
}
```

**File:** `app/api/endpoints/incidents.py:acknowledge_incident()`

**Validation:**
```python
# Check current status
incident = await db_service.get_drift_incident('incident-042')

if incident['status'] != DriftIncidentStatus.DETECTED:
    raise InvalidStateError("Can only acknowledge incidents in DETECTED state")

# Validate transition
await drift_incident_service.validate_state_transition(
    incident=incident,
    from_status='detected',
    to_status='acknowledged'
)
```

**Database Mutation:**
```sql
UPDATE drift_incidents
SET status = 'acknowledged',
    acknowledged_by = 'user-oncall-5',
    acknowledged_at = NOW(),
    acknowledgment_comment = 'Reviewing hotfix, will coordinate with team',
    updated_at = NOW()
WHERE id = 'incident-042';
```

**Audit Log:**
```sql
INSERT INTO audit_log (
  id, tenant_id, user_id, action,
  resource_type, resource_id,
  details, timestamp
) VALUES (
  'audit-001', 'tenant-1', 'user-oncall-5', 'incident.acknowledged',
  'drift_incident', 'incident-042',
  {
    "comment": "Reviewing hotfix, will coordinate with team",
    "previous_status": "detected",
    "new_status": "acknowledged"
  },
  NOW()
);
```

---

#### 6. Team Investigates and Stabilizes

**Context:** Team confirms hotfix was necessary (payment processor changed their API endpoint without notice). They decide to:
1. Commit the hotfix to Git (make it official)
2. Document the change
3. Mark incident as stabilized

**Actions:**

##### 6a. Commit Hotfix to Git

**Manual Git Workflow:**
```bash
# Developer pulls current state from n8n
curl https://prod.n8n.example.com/api/v1/workflows/wf-prod-042 \
  -H "X-N8N-API-KEY: xxx" \
  > prod/payment_gateway.json

# Commit change
git add prod/payment_gateway.json
git commit -m "Emergency hotfix: Update payment API endpoint

Payment processor migrated to new API domain without notice.
Updated endpoint from api.paymentprocessor.com to api-new.paymentprocessor.com.

Related incident: incident-042"

git push origin main
```

##### 6b. Mark Incident as Stabilized

**API Call:**
```http
POST /api/v1/incidents/incident-042/stabilize
{
  "stabilized_by": "user-lead-3",
  "reason": "Hotfix committed to Git, change documented",
  "assigned_to": "user-lead-3",
  "resolution_plan": "Git now matches production. Will sync other environments on next deployment."
}
```

**Database Mutation:**
```sql
UPDATE drift_incidents
SET status = 'stabilized',
    stabilized_by = 'user-lead-3',
    stabilized_at = NOW(),
    stabilization_reason = 'Hotfix committed to Git, change documented',
    assigned_to = 'user-lead-3',
    resolution_plan = 'Git now matches production...',
    updated_at = NOW()
WHERE id = 'incident-042';
```

---

#### 7. Sync Workflow to Resolve Drift

**Option 1: Trigger Manual Sync (Recommended)**

**API Call:**
```http
POST /api/v1/canonical/sync/request
{
  "environment_id": "env-prod-123"
}
```

**Sync Process:**

1. **Git → DB Sync**
   ```python
   # Fetch updated workflow from Git (with hotfix)
   git_workflow = await github_service.get_workflow_from_github(
       file_path="prod/payment_gateway.json"
   )

   # Compute new git_content_hash
   git_hash = compute_workflow_hash(git_workflow)

   # Update canonical_workflows
   await db_service.update_canonical_workflow(
       canonical_id='payment_gateway',
       content_hash=git_hash,
       workflow_definition=git_workflow,
       git_commit_sha='def789ghi012'  # NEW commit
   )
   ```

2. **Update workflow_env_map**
   ```sql
   UPDATE workflow_env_map
   SET git_content_hash = 'x9y8z7w6v5u4...',  -- Matches env_hash now
       git_last_synced_at = NOW()
   WHERE environment_id = 'env-prod-123'
     AND n8n_workflow_id = 'wf-prod-042';
   ```

3. **Recheck Drift Status**
   ```python
   # After sync
   if mapping['env_content_hash'] == mapping['git_content_hash']:
       drift_status = 'IN_SYNC'
   ```

4. **Update Environment Status**
   ```sql
   UPDATE environments
   SET drift_status = 'IN_SYNC',
       last_sync_completed_at = NOW()
   WHERE id = 'env-prod-123';
   ```

---

#### 8. Mark Incident as Reconciled

**API Call:**
```http
POST /api/v1/incidents/incident-042/reconcile
{
  "reconciled_by": "user-lead-3",
  "resolution_type": "accepted_runtime_changes",
  "resolution_details": "Git synchronized with production hotfix. All environments now aligned.",
  "lessons_learned": "Payment processor should notify us of API changes. Added monitoring for API endpoint changes."
}
```

**Database Mutation:**
```sql
UPDATE drift_incidents
SET status = 'reconciled',
    reconciled_by = 'user-lead-3',
    reconciled_at = NOW(),
    resolution_type = 'accepted_runtime_changes',
    resolution_details = 'Git synchronized with production hotfix...',
    lessons_learned = 'Payment processor should notify us...',
    updated_at = NOW()
WHERE id = 'incident-042';
```

---

#### 9. Close Incident

**API Call:**
```http
POST /api/v1/incidents/incident-042/close
{
  "closed_by": "user-lead-3",
  "closure_reason": "Drift resolved, all environments synchronized"
}
```

**Validation:**
```python
# Verify incident is in reconciled state
if incident['status'] != 'reconciled':
    raise InvalidStateError("Must reconcile before closing")

# Check drift status
environment = await db_service.get_environment('env-prod-123')
if environment['drift_status'] != 'IN_SYNC':
    # Warning but allow close
    logger.warning("Closing incident but drift still detected")
```

**Database Mutation:**
```sql
UPDATE drift_incidents
SET status = 'closed',
    closed_by = 'user-lead-3',
    closed_at = NOW(),
    closure_reason = 'Drift resolved, all environments synchronized',
    updated_at = NOW()
WHERE id = 'incident-042';
```

**Audit Log Entry:**
```sql
INSERT INTO audit_log (
  id, tenant_id, user_id, action,
  resource_type, resource_id,
  details, timestamp
) VALUES (
  'audit-042-close', 'tenant-1', 'user-lead-3', 'incident.closed',
  'drift_incident', 'incident-042',
  {
    "resolution_type": "accepted_runtime_changes",
    "total_duration_hours": 2.5,
    "workflows_affected": 1
  },
  NOW()
);
```

**Final Notification:**

**Email to team:**
```
Subject: [RESOLVED] Drift incident closed - Production

Incident ID: incident-042
Environment: Production
Status: Closed

Resolution:
  Type: Accepted runtime changes
  Details: Git synchronized with production hotfix. All environments now aligned.

Timeline:
  Detected: 2026-01-14 15:25:00 UTC
  Acknowledged: 2026-01-14 15:30:00 UTC
  Stabilized: 2026-01-14 16:45:00 UTC
  Reconciled: 2026-01-14 17:15:00 UTC
  Closed: 2026-01-14 17:50:00 UTC
  Total Duration: 2h 25m

Lessons Learned:
  Payment processor should notify us of API changes. Added monitoring for API endpoint changes.
```

---

### Final State After Resolution

**Production Environment:**
- Drift status: `IN_SYNC`
- All workflows aligned with Git
- `workflow_env_map.env_content_hash == git_content_hash`

**Git Repository:**
- Updated with hotfix commit
- Commit: `def789ghi012`
- Message: "Emergency hotfix: Update payment API endpoint"

**Database:**
- `drift_incidents` table: 1 record (`status = 'closed'`)
- `audit_log` table: 5 entries (detected, acknowledged, stabilized, reconciled, closed)
- `environments.drift_status`: `IN_SYNC`

**Incident Metrics:**
- Total duration: 2 hours 25 minutes
- Time to acknowledge: 5 minutes
- Time to stabilize: 1 hour 15 minutes
- Time to reconcile: 30 minutes
- Time to close: 35 minutes

---

## Scenario 4: Unmapped Workflow Onboarding

**User Story:** A developer creates a new workflow directly in Dev n8n. The next sync detects it as UNMAPPED. The team decides to onboard it to Git and link it as a canonical workflow.

### Initial State

**Dev Environment:**
- 50 workflows already synced and linked
- New workflow created in n8n UI: "Customer Survey Automation"
- Not yet in Git
- Not in `workflow_env_map`

---

### Step-by-Step Flow

#### 1. Developer Creates Workflow in n8n UI

**n8n UI Actions:**
1. Clicks "Create Workflow"
2. Names it "Customer Survey Automation"
3. Adds nodes:
   - Webhook trigger
   - Email node
   - Google Sheets node
4. Saves and activates workflow

**n8n Internal State:**
```json
{
  "id": "wf-dev-051",
  "name": "Customer Survey Automation",
  "active": true,
  "createdAt": "2026-01-14T09:00:00.000Z",
  "updatedAt": "2026-01-14T09:15:00.000Z",
  "nodes": [
    {
      "name": "Survey Webhook",
      "type": "n8n-nodes-base.webhook",
      "parameters": {"path": "/survey"}
    },
    {
      "name": "Send Thank You Email",
      "type": "n8n-nodes-base.emailSend",
      "credentials": {"smtp": {"id": "cred-dev-020", "name": "Email SMTP"}}
    },
    {
      "name": "Log to Sheets",
      "type": "n8n-nodes-base.googleSheets",
      "credentials": {"googleSheetsOAuth2": {"id": "cred-dev-025", "name": "Google Sheets"}}
    }
  ],
  "connections": {...}
}
```

**Not yet in Git or WorkflowOps database**

---

#### 2. Scheduled Sync Discovers New Workflow

**Scheduler Trigger:** `canonical_sync_scheduler` runs every 15 minutes for Dev

**File:** `app/services/canonical_sync_scheduler.py:start_canonical_sync_schedulers()`

**Sync Request:**
```python
await SyncOrchestratorService.request_sync(
    tenant_id='tenant-1',
    environment_id='env-dev-123',
    created_by='system',
    metadata={'trigger': 'scheduled'}
)
```

---

#### 3. Sync Process Detects Unmapped Workflow

**File:** `app/services/canonical_env_sync_service.py:sync_environment()`

##### 3a. Fetch All Workflows from n8n

```python
adapter = ProviderRegistry.get_adapter_for_environment(dev_env)
workflows = await adapter.get_all_workflows()
# Returns 51 workflows (50 existing + 1 new)
```

**n8n API Response includes:**
```json
{
  "id": "wf-dev-051",
  "name": "Customer Survey Automation",
  "active": true,
  "updatedAt": "2026-01-14T09:15:00.000Z",
  "nodes": [...],
  "connections": {...}
}
```

##### 3b. Check for Existing Mapping

```sql
SELECT * FROM workflow_env_map
WHERE environment_id = 'env-dev-123'
  AND n8n_workflow_id = 'wf-dev-051';
-- Returns NO ROWS (new workflow)
```

##### 3c. Normalize and Hash

```python
normalized = normalize_workflow_for_comparison(workflow)
env_content_hash = compute_workflow_hash(normalized)
# → "p9q8r7s6t5u4..."
```

##### 3d. Check for Canonical Match by Hash

```sql
SELECT * FROM canonical_workflows
WHERE tenant_id = 'tenant-1'
  AND content_hash = 'p9q8r7s6t5u4...';
-- Returns NO ROWS (no match in Git)
```

##### 3e. Create UNMAPPED Workflow Mapping

```python
status = WorkflowMappingStatus.UNMAPPED
canonical_id = None  # Not linked yet
```

**Database Mutation:**
```sql
INSERT INTO workflow_env_map (
  id, tenant_id, environment_id,
  n8n_workflow_id, canonical_id, status,
  workflow_name, workflow_data,
  env_content_hash, git_content_hash,
  n8n_updated_at, created_at, updated_at
) VALUES (
  'map-051', 'tenant-1', 'env-dev-123',
  'wf-dev-051', NULL, 'unmapped',
  'Customer Survey Automation', {...},
  'p9q8r7s6t5u4...', NULL,  -- No git hash yet
  '2026-01-14T09:15:00Z', NOW(), NOW()
);
```

**Sync Result:**
```json
{
  "workflows_synced": 51,
  "workflows_skipped": 45,  // Unchanged
  "workflows_linked": 50,
  "workflows_unmapped": 1,  // NEW
  "created_workflow_ids": ["wf-dev-051"]
}
```

**SSE Event:**
```json
{
  "event_type": "sync.completed",
  "environment_id": "env-dev-123",
  "workflows_unmapped": 1,
  "new_unmapped_workflows": ["wf-dev-051"]
}
```

---

#### 4. UI Shows Unmapped Workflow Alert

**UI Notification:**
```
⚠️ 1 unmapped workflow detected in Dev environment

Workflow: Customer Survey Automation
Status: UNMAPPED (not linked to Git)

Action Required: Review and onboard to Git
```

**User Navigation:** Clicks notification → Redirected to Unmapped Workflows page

> **Note:** The `/canonical/untracked` endpoint and `untracked_workflows_service.py` have been **deprecated and removed**. Unmapped workflows are now visible via the workflow matrix view and canonical onboarding flow.

**Legacy API Call (Deprecated):**
```http
GET /api/v1/canonical/untracked?environment_id=env-dev-123
# ⚠️ DEPRECATED - Use workflow matrix or onboarding flow instead
```

**Database Query:**
```sql
SELECT * FROM workflow_env_map
WHERE tenant_id = 'tenant-1'
  AND environment_id = 'env-dev-123'
  AND status = 'unmapped'
  AND canonical_id IS NULL;
```

**Response:**
```json
{
  "unmapped_workflows": [
    {
      "id": "map-051",
      "n8n_workflow_id": "wf-dev-051",
      "workflow_name": "Customer Survey Automation",
      "environment_id": "env-dev-123",
      "environment_name": "Dev",
      "status": "unmapped",
      "detected_at": "2026-01-14T09:30:00Z",
      "node_count": 3,
      "active": true
    }
  ],
  "total": 1
}
```

---

#### 5. User Initiates Onboarding

**UI Action:** User clicks "Onboard to Git" button

**Onboarding Form:**
```
Workflow: Customer Survey Automation
Environment: Dev

Canonical Settings:
  Canonical Slug: customer_survey_automation
  Description: Automates customer survey collection and logging
  Tags: surveys, automation, customers

Git Settings:
  Target File: dev/customer_survey_automation.json
  Commit Message: "Add customer survey automation workflow"
```

**API Call:**
```http
POST /api/v1/canonical/workflows/onboard
{
  "workflow_mapping_id": "map-051",
  "canonical_slug": "customer_survey_automation",
  "description": "Automates customer survey collection and logging",
  "tags": ["surveys", "automation", "customers"],
  "git_file_path": "dev/customer_survey_automation.json",
  "commit_message": "Add customer survey automation workflow",
  "commit_to_git": true
}
```

**File:** `app/api/endpoints/canonical_workflows.py:onboard_workflow()`

---

#### 6. Onboarding Service Processes Request

**File:** `app/services/canonical_workflow_service.py:onboard_unmapped_workflow()`

##### 6a. Validate Request

```python
# Check workflow exists and is unmapped
mapping = await db_service.get_workflow_mapping('map-051')

if mapping['status'] != WorkflowMappingStatus.UNMAPPED:
    raise InvalidStateError("Workflow must be UNMAPPED")

if mapping['canonical_id'] is not None:
    raise ConflictError("Workflow already linked")

# Validate canonical_slug uniqueness
existing = await db_service.find_canonical_by_slug('customer_survey_automation')
if existing:
    raise ConflictError("Canonical slug already exists")
```

##### 6b. Create Canonical Workflow Record

```python
# Generate canonical ID
canonical_id = str(uuid4())  # "canon-uuid-051"

# Fetch full workflow data
workflow_data = mapping['workflow_data']

# Compute hash
content_hash = compute_workflow_hash(workflow_data)
```

**Database Mutation:**
```sql
INSERT INTO canonical_workflows (
  id, tenant_id, canonical_slug, name,
  description, tags,
  content_hash, workflow_definition,
  git_file_path, git_branch,
  provider, created_at, updated_at
) VALUES (
  'canon-uuid-051', 'tenant-1', 'customer_survey_automation',
  'Customer Survey Automation',
  'Automates customer survey collection and logging',
  ARRAY['surveys', 'automation', 'customers'],
  'p9q8r7s6t5u4...', {...},
  'dev/customer_survey_automation.json', 'main',
  'n8n', NOW(), NOW()
);
```

##### 6c. Link Workflow Mapping to Canonical

```sql
UPDATE workflow_env_map
SET canonical_id = 'canon-uuid-051',
    status = 'linked',
    git_content_hash = 'p9q8r7s6t5u4...',  -- Same as env hash initially
    updated_at = NOW()
WHERE id = 'map-051';
```

##### 6d. Commit to Git (if requested)

**File:** `app/services/github_service.py:commit_workflow_to_github()`

**Steps:**

1. **Create workflow file**
   ```python
   await github_service.create_or_update_file(
       file_path="dev/customer_survey_automation.json",
       content=json.dumps(workflow_data, indent=2),
       message="Add customer survey automation workflow",
       branch="main"
   )
   ```

   **GitHub API Call:**
   ```http
   PUT https://api.github.com/repos/acme-corp/workflows/contents/dev/customer_survey_automation.json
   Authorization: Bearer ghp_xxx
   Content-Type: application/json

   {
     "message": "Add customer survey automation workflow",
     "content": "<base64-encoded workflow JSON>",
     "branch": "main"
   }
   ```

2. **Create sidecar metadata file**
   ```python
   sidecar = {
       "canonical_id": "canon-uuid-051",
       "canonical_slug": "customer_survey_automation",
       "tags": ["surveys", "automation", "customers"],
       "created_by": "user-dev-2",
       "created_at": "2026-01-14T10:00:00Z"
   }

   await github_service.create_or_update_file(
       file_path="dev/customer_survey_automation.wfo.json",
       content=json.dumps(sidecar, indent=2),
       message="Add metadata for customer survey automation",
       branch="main"
   )
   ```

3. **Update canonical with Git commit info**
   ```python
   # GitHub returns commit SHA
   commit_sha = "xyz789abc012"

   await db_service.update_canonical_workflow(
       canonical_id='canon-uuid-051',
       git_commit_sha=commit_sha,
       git_last_synced_at=datetime.utcnow()
   )
   ```

   **Database Mutation:**
   ```sql
   UPDATE canonical_workflows
   SET git_commit_sha = 'xyz789abc012',
       git_last_synced_at = NOW()
   WHERE id = 'canon-uuid-051';
   ```

---

#### 7. Onboarding Complete

**Response to UI:**
```json
{
  "canonical_workflow": {
    "id": "canon-uuid-051",
    "canonical_slug": "customer_survey_automation",
    "name": "Customer Survey Automation",
    "git_file_path": "dev/customer_survey_automation.json",
    "git_commit_sha": "xyz789abc012"
  },
  "workflow_mapping": {
    "id": "map-051",
    "status": "linked",
    "canonical_id": "canon-uuid-051"
  },
  "git_committed": true
}
```

**SSE Event:**
```json
{
  "event_type": "workflow.onboarded",
  "canonical_id": "canon-uuid-051",
  "environment_id": "env-dev-123",
  "workflow_name": "Customer Survey Automation"
}
```

**UI Success Message:**
```
✅ Workflow successfully onboarded!

Workflow: Customer Survey Automation
Canonical ID: canon-uuid-051
Git File: dev/customer_survey_automation.json
Status: LINKED

The workflow is now tracked in Git and can be promoted to other environments.
```

---

### Final State After Onboarding

**Database:**
- `canonical_workflows`: 1 new record created
- `workflow_env_map`: 1 record updated (`status: unmapped` → `linked`)
- Environment drift status: `IN_SYNC` (1 fewer unmapped)

**Git Repository:**
- New files:
  - `dev/customer_survey_automation.json`
  - `dev/customer_survey_automation.wfo.json`
- Commit: `xyz789abc012`
- Message: "Add customer survey automation workflow"

**Workflow Status:**
- Can now be promoted to Staging and Production
- Tracked in version control
- Drift detection enabled

---

## Summary

These four scenarios demonstrate the core workflows through the WorkflowOps system:

1. **First-Time Environment Setup** - Shows the complete sync process (n8n → DB, Git → DB, drift detection)
2. **Promotion Flow** - Demonstrates promotion gates, credential rewriting, snapshots, and rollback capabilities
3. **Drift Detection & Resolution** - Traces the full incident lifecycle from detection to closure
4. **Unmapped Onboarding** - Shows how new workflows are discovered and linked to Git

Each scenario includes:
- ✅ **API calls** with exact endpoints and payloads
- ✅ **Service function calls** with file paths and line numbers
- ✅ **Database mutations** with SQL statements
- ✅ **External API calls** (n8n, GitHub) with examples
- ✅ **State transitions** and validation logic
- ✅ **SSE events** for real-time UI updates
- ✅ **Error handling** and edge cases

---

**End of Narrative Walkthroughs**
