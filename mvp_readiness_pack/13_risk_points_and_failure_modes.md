# Section 13: Risk Points and Failure Modes

**Purpose**: Document identified risk points, failure modes, edge cases, and potential data inconsistency scenarios across the WorkflowOps system based on code analysis.

---

## 1. Drift Detection Risks

### 1.1 Git Configuration Failures

**Location**: `app/services/drift_detection_service.py:106-156`

**Risk**: Environment with missing or invalid Git credentials returns UNKNOWN status silently
- If `git_repo_url` or `git_pat` is missing → status = UNKNOWN, no error raised
- If GitHub service cannot authenticate → status = UNKNOWN
- Frontend may not distinguish between "not configured" and "temporarily failing"

**Impact**: Silent failure prevents visibility into configuration issues

**Mitigation**:
- Error field in `EnvironmentDriftSummary` provides some context
- Cached status from `environments.drift_status` may be stale

### 1.2 Provider Fetch Failures

**Location**: `app/services/drift_detection_service.py:158-178`

**Risk**: If n8n API is unreachable or returns errors during `adapter.get_workflows()`:
- Status set to ERROR
- `affected_workflows` list will be empty
- Last known drift status may become stale

**Impact**: Drift status becomes unreliable during n8n outages

**Edge Case**: Partial failures (some workflows fetch, others timeout) not explicitly handled

### 1.3 GitHub Fetch Failures

**Location**: `app/services/drift_detection_service.py:201-221`

**Risk**: GitHub API failures during `get_all_workflows_from_github()`:
- Status set to ERROR
- No diff comparison performed
- Last drift detection timestamp updated even though no real check occurred

**Impact**: False sense of "checked recently" when check actually failed

### 1.4 UNTRACKED vs DRIFT_DETECTED Logic

**Location**: `app/services/drift_detection_service.py:283-296`

**Risk**: Status determination depends on `tracked_workflows` count:
```python
if len(tracked_workflows) == 0:
    drift_status = DriftStatus.UNTRACKED
else:
    drift_status = DRIFT_DETECTED if has_drift else IN_SYNC
```

**Edge Case**: If all workflows are manually unlinked but still exist in n8n:
- Environment marked UNTRACKED
- Drift incidents won't be created (scheduler skips UNTRACKED environments)
- Actual drift may be hidden

**Impact**: Manual unlinking can mask real drift

### 1.5 DEV Environment Exclusion

**Location**: `app/services/drift_scheduler.py:33-67`

**Risk**: DEV environments excluded from drift checks entirely:
```python
.neq("environment_class", "dev")
```

**Rationale**: n8n is source of truth for DEV
**Edge Case**: If environment_class is misconfigured or NULL, drift checks may not run

---

## 2. Sync Service Risks

### 2.1 Environment Sync Batch Processing

**Location**: `app/services/canonical_env_sync_service.py:179-285`

**Risk**: Batch processing with checkpoints:
- Each batch is `BATCH_SIZE = 25` workflows
- If job crashes mid-batch, work is lost until next checkpoint
- Transaction boundary is per-workflow (line 232: "Each workflow in batch has error isolation")

**Failure Mode**:
1. Batch starts processing workflows 0-24
2. Workflow #20 causes Python crash (OOM, segfault)
3. Workflows 0-19 were processed but checkpoint not saved yet
4. On retry, workflows 0-24 reprocessed (duplicate work)

**Impact**: Inefficiency, potential duplicate logging, but data consistency preserved via upsert

### 2.2 Short-Circuit Optimization Failure

**Location**: `app/services/canonical_env_sync_service.py:370-376`

**Risk**: Short-circuit relies on `n8n_updated_at` comparison:
```python
if existing_n8n_updated_at and n8n_updated_at:
    if _normalize_timestamp(existing_n8n_updated_at) == _normalize_timestamp(n8n_updated_at):
        # Workflow unchanged - skip processing
        batch_results["skipped"] += 1
```

**Edge Cases**:
- n8n doesn't update `updatedAt` for certain changes (e.g., credential reassignment without workflow modification)
- Timestamp normalization strips timezone info → potential false equality across DST boundaries
- If `n8n_updated_at` is NULL in response, short-circuit fails → full processing every time

**Impact**: Missed updates or unnecessary processing

### 2.3 Hash Collision Detection

**Location**: `app/services/canonical_env_sync_service.py:27-77`

**Risk**: Hash collisions detected but only logged as warnings:
```python
logger.warning(f"Hash collision detected during env sync: {warning['message']}")
```

**Failure Mode**:
- Two different workflows hash to same value (SHA-256 collision extremely unlikely but theoretically possible)
- Both workflows treated as "same canonical workflow"
- Promotion/linking logic may overwrite one with the other

**Impact**: Silent data corruption in canonical workflow registry

**Mitigation**: Warnings collected in `collision_warnings` array but no blocking behavior

### 2.4 Missing Workflow Marking Race Condition

**Location**: `app/services/canonical_env_sync_service.py:727-785`

**Risk**: Workflows marked "missing" if not in current n8n fetch:
```python
for mapping in (response.data or []):
    n8n_id = mapping.get("n8n_workflow_id")
    if n8n_id and n8n_id not in existing_n8n_ids:
        # Mark as missing
```

**Race Condition**:
1. Sync starts, fetches workflows from n8n
2. User deletes workflow in n8n mid-sync
3. Sync completes, marks workflow as missing
4. User re-creates workflow with same ID before next sync
5. Next sync treats it as "reappeared" → status transition logic (line 388-393)

**Impact**: Transient "missing" state for workflows that were briefly deleted and recreated

### 2.5 Auto-Link Conflicts

**Location**: `app/services/canonical_env_sync_service.py:495-554`

**Risk**: Auto-link by hash can fail if canonical_id already linked to different n8n_workflow_id:
```python
if existing_n8n_id and existing_n8n_id != n8n_workflow_id:
    logger.warning(f"Cannot auto-link {n8n_workflow_id} to canonical {canonical_id}")
    return None
```

**Failure Mode**:
1. Workflow A linked to canonical_id X in environment
2. Workflow B (different n8n ID) has same content hash as A
3. Auto-link fails for B → remains UNTRACKED
4. B is functionally identical to A but not tracked in promotions

**Impact**: Duplicate workflows not automatically reconciled

---

## 3. Promotion Service Risks

### 3.1 Rollback on Partial Failure

**Location**: `app/services/promotion_service.py:49` (comment indicates implementation)

**Risk**: Rollback mechanism relies on pre-promotion snapshot:
- Snapshot created BEFORE any mutations (line 234-239)
- On first failure, all successfully promoted workflows restored from snapshot
- Snapshot stored as Git commit SHA

**Failure Modes**:
1. **Snapshot creation fails**: If GitHub API fails during snapshot commit → promotion cannot proceed safely
2. **Rollback fetch fails**: If snapshot commit SHA inaccessible during rollback → partial state left in target
3. **Rollback write fails**: If n8n API fails during restore → some workflows rolled back, others not

**Impact**: Target environment left in inconsistent state if rollback itself fails

**Mitigation**: Audit log captures all state transitions (line 222)

### 3.2 Credential Rewriting Errors

**Location**: `app/services/promotion_service.py` (implementation not shown in excerpt)

**Risk**: Credential mappings applied during promotion:
- If mapping missing for required credential → promotion fails
- If credential name in target doesn't match mapping → workflow broken post-promotion
- No validation of credential existence in target before promotion

**Edge Case**: Workflow uses credential deleted in target between gate check and execution

**Impact**: Promoted workflow appears successful but fails at runtime due to missing credentials

### 3.3 Idempotency Check False Positives

**Location**: `app/services/promotion_service.py:44` (indicates implementation)

**Risk**: Idempotency uses content hash comparison:
- If two workflows normalize to same hash (after excluding metadata) → treated as duplicate
- Promotion skipped even if workflow names differ

**Edge Case**: Workflow renamed but content unchanged → idempotency check prevents re-promotion under new name

**Impact**: Unintended deduplication of legitimately different workflows

### 3.4 Transient Provider Errors

**Location**: `app/services/promotion_service.py:283-295`

**Risk**: Retry logic for transient errors:
```python
if status_code in (408, 429) or (status_code is not None and 500 <= status_code < 600):
    return True
```

**Failure Mode**:
- n8n API returns 502 (Bad Gateway) during promotion
- Retry logic triggers (implementation not shown)
- If retries exhausted → promotion fails, rollback triggered
- If rollback also hits transient error → stuck in partial state

**Impact**: Transient network issues can cause full promotion rollback

### 3.5 Normalization Drift

**Location**: `app/services/promotion_service.py:90-161`

**Risk**: Workflow normalization removes fields for comparison:
```python
exclude_fields = ['id', 'createdAt', 'updatedAt', 'active', 'tags', ...]
```

**Edge Case**:
- Field added to n8n API response in new version
- Not added to `exclude_fields` list
- Workflows appear different even when functionally identical
- False drift detected, promotions blocked

**Impact**: Version upgrades break drift detection/promotion logic

---

## 4. GitHub Service Risks

### 4.1 Repository Access Failures

**Location**: `app/services/github_service.py:29-37`

**Risk**: Lazy repo connection:
```python
try:
    self._repo = self.github.get_repo(f"{self.repo_owner}/{self.repo_name}")
except Exception:
    pass  # Return None if repo can't be accessed
```

**Failure Mode**: Silently returns None if repo inaccessible
- Downstream code may not check `repo` property before use
- NoneType errors in sync operations

**Impact**: Sync failures without clear error messages

### 4.2 Branch Protection Bypass

**Location**: `app/services/github_service.py:124-145`

**Risk**: Direct commits to branch without PR workflow:
```python
self.repo.update_file(path=file_path, message=commit_message, content=content, ...)
```

**Edge Case**: If branch has protection rules (require PR, code review):
- Commits may fail with 403 Forbidden
- No fallback to PR creation flow

**Impact**: Sync operations fail on protected branches

### 4.3 File Naming Collisions

**Location**: `app/services/github_service.py:43-52`

**Risk**: Filename sanitization:
```python
sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
```

**Edge Case**: Two workflows with names that normalize to same filename:
- "Workflow: Test" → "Workflow__Test.json"
- "Workflow/ Test" → "Workflow__Test.json"
- Second write overwrites first in Git

**Impact**: Workflow loss in Git repository

### 4.4 Commit SHA Staleness

**Location**: `app/services/github_service.py:153-221`

**Risk**: `get_all_workflows_from_github()` can fetch from specific commit SHA:
- If SHA provided is old, fetches stale data
- Drift detection compares runtime to old Git state
- False drift reported

**Impact**: Incorrect drift detection if SHA not from latest commit

---

## 5. Scheduler Risks

### 5.1 Drift Scheduler Overlapping Runs

**Location**: `app/services/drift_scheduler.py:28-31`

**Risk**: Drift check runs every 5 minutes (300 seconds):
```python
DRIFT_CHECK_INTERVAL_SECONDS = 300
```

**Failure Mode**:
1. Drift check for large environment takes 6 minutes to complete
2. Second drift check starts while first still running
3. Both checks write to same `environments.drift_status` field
4. Race condition → status may be overwritten by slower check

**Impact**: Inconsistent drift status, potential database deadlocks

**Mitigation**: Per-environment locking not evident in code

### 5.2 Canonical Sync Debounce Window

**Location**: `app/services/canonical_sync_scheduler.py:39-41`

**Risk**: Debounce prevents concurrent syncs:
```python
SYNC_DEBOUNCE_SECONDS = 60
```

**Edge Case**:
1. Sync starts at T=0
2. Sync completes successfully at T=10
3. User manually triggers sync at T=30
4. Manual sync blocked by debounce (still within 60 second window)
5. User sees "sync already in progress" even though completed 20 seconds ago

**Impact**: User confusion, manual syncs rejected

### 5.3 Deployment Scheduler Clock Skew

**Location**: `app/services/deployment_scheduler.py:68-74`

**Risk**: Scheduled deployment execution time check:
```python
if (now - scheduled_at).total_seconds() < -5:
    continue  # Not quite time yet
```

**Edge Case**: 5-second buffer for clock skew
- If server clock drifts more than 5 seconds ahead → deployments execute early
- If server clock drifts behind → deployments delayed

**Impact**: Unpredictable deployment timing

### 5.4 TTL Expiration Race

**Location**: `app/services/drift_scheduler.py:319-380`

**Risk**: TTL checker runs every 60 seconds:
- Incident expires at T=12:00:00
- TTL checker runs at T=12:00:30 (30 seconds late)
- Incident already expired for 30 seconds but still showing as "active"

**Impact**: Expired incidents not closed immediately

### 5.5 Promotion Lock Deadlock

**Location**: `app/services/deployment_scheduler.py:139-152`

**Risk**: Scheduled deployment checks for promotion lock:
```python
await promotion_lock_service.check_and_acquire_promotion_lock(...)
```

**Failure Mode**:
1. Promotion A starts for environment
2. Scheduled promotion B polls and sees lock
3. B retries on next cycle (30 seconds later)
4. If A takes hours (large deployment), B never executes
5. No timeout or max retry logic visible

**Impact**: Scheduled deployments indefinitely postponed

---

## 6. N8N Client Risks

### 6.1 Windows Errno 22 Handling

**Location**: `app/services/n8n_client.py:94-124`

**Risk**: Special handling for Windows-specific error:
```python
if hasattr(e, 'errno') and e.errno == 22:
    error_msg = f"Windows errno 22 (Invalid argument)"
```

**Edge Case**: Errno 22 on Windows indicates invalid characters in request
- Deep node inspection tries to identify problematic data (lines 104-113)
- If inspection itself throws exception → original error masked

**Impact**: Lost error context, difficult debugging

### 6.2 Workflow Data Cleaning Inconsistency

**Location**: `app/services/n8n_client.py:130-176`

**Risk**: `update_workflow()` cleans node fields aggressively:
```python
essential_fields = ["id", "name", "type", "typeVersion", ...]
for key in essential_fields:
    if key in node:
        clean_node[key] = node[key]
```

**Edge Case**: Custom node types with non-standard fields:
- Fields outside `essential_fields` filtered out if complex
- Node functionality may break post-update

**Impact**: Workflow corruption on update operations

### 6.3 JSON Serialization Pre-Check

**Location**: `app/services/n8n_client.py:64-71`

**Risk**: Pre-serialization test before API call:
```python
try:
    json_str = json.dumps(cleaned_data, default=str, ensure_ascii=False)
except (TypeError, ValueError) as json_error:
    raise ValueError(error_msg) from json_error
```

**Edge Case**: Data serializes successfully in test but fails in httpx due to encoding differences
- UTF-8 encoding errors (line 192-198) caught separately
- If encoding fails → no retry, promotion fails

**Impact**: Non-deterministic serialization failures

### 6.4 Timeout Configuration

**Location**: `app/services/n8n_client.py:23,35,81`

**Risk**: Fixed 30-second timeout for all operations:
```python
timeout=30.0
```

**Edge Case**: Large workflows (hundreds of nodes) may take longer to:
- Fetch (get_workflow)
- Create (create_workflow)
- Update (update_workflow)

**Impact**: Timeout during legitimate operations for large workflows

---

## 7. Database Consistency Risks

### 7.1 Workflow Mapping Unique Constraint

**Location**: `app/services/canonical_env_sync_service.py:619-645`

**Risk**: Upsert on `(tenant_id, environment_id, n8n_workflow_id)`:
```python
.upsert(mapping_data, on_conflict="tenant_id,environment_id,n8n_workflow_id")
```

**Edge Case**: If unique constraint doesn't exist or is misconfigured in database:
- Multiple mappings created for same n8n_workflow_id
- Query returns non-deterministic results
- Auto-link logic breaks

**Impact**: Data duplication, inconsistent state

### 7.2 Canonical ID Orphans

**Location**: `app/services/canonical_repo_sync_service.py:180-194`

**Risk**: Git sync creates canonical workflows if not exist:
```python
if not canonical:
    await CanonicalWorkflowService.create_canonical_workflow(...)
```

**Edge Case**: Canonical workflow created from Git file, but:
- No corresponding workflow_env_map entry (if n8n sync hasn't run)
- Canonical workflow exists but is "orphaned" (not linked to any environment)
- Orphans accumulate over time

**Impact**: Database bloat, unclear which canonical workflows are active

### 7.3 Environment Active Incident Staleness

**Location**: `app/services/drift_scheduler.py:297-299`

**Risk**: `environments.active_drift_incident_id` updated when incident created:
```python
db_service.client.table("environments").update({
    "active_drift_incident_id": incident_id
}).eq("id", environment_id).execute()
```

**Edge Case**: Incident closed manually via API, but:
- `active_drift_incident_id` not cleared
- Environment appears to have active incident that's actually closed
- New incident creation blocked (line 138-145 checks for active incident)

**Impact**: Incident creation halted until field manually cleared

### 7.4 Missing Status Transitions

**Location**: `app/services/canonical_env_sync_service.py:386-393`

**Risk**: Workflow marked "missing" if not in n8n, but transition back to linked/untracked on reappearance:
```python
if existing_status == "missing":
    if existing_canonical_id:
        new_status = WorkflowMappingStatus.LINKED
```

**Edge Case**: Workflow marked missing, then:
- Reappears with different content hash
- Status transitions to LINKED
- But no drift incident created for the content change

**Impact**: Silent content changes masked during missing→linked transition

---

## 8. External Dependency Risks

### 8.1 GitHub Rate Limiting

**Location**: Not explicitly handled in code

**Risk**: GitHub API has rate limits:
- 5000 requests/hour for authenticated users
- Large environments with frequent syncs may hit limit
- No exponential backoff or rate limit detection visible

**Impact**: Syncs fail with 403 Forbidden when rate limited

### 8.2 N8N API Version Skew

**Location**: No version checking in n8n_client.py

**Risk**: N8N API evolves between versions:
- New required fields added
- Field types changed
- Endpoints deprecated

**Impact**: Client breaks when n8n upgraded, no graceful degradation

### 8.3 Supabase Connection Pooling

**Location**: `app/services/database.py` (not shown in excerpts)

**Risk**: All services share `db_service.client` singleton
- No connection pool limits visible
- Under load, may exhaust database connections
- Queries timeout or fail with "too many connections"

**Impact**: Service-wide database failures under high load

---

## 9. Edge Cases and Boundary Conditions

### 9.1 Empty Environment Handling

**Scenario**: Environment with zero workflows

**Risks**:
- Drift detection: `total_workflows=0` but status set to IN_SYNC (line 280-296 logic may skip UNTRACKED check)
- Sync: Empty batch, no checkpoint created
- Promotion source: No workflows to promote

**Impact**: Edge case handling inconsistent across services

### 9.2 Extremely Large Workflows

**Scenario**: Workflow with 1000+ nodes

**Risks**:
- Hash computation performance (normalize entire workflow in memory)
- JSON serialization size exceeds httpx limits
- n8n API timeout (30 seconds may be insufficient)
- Git commit size limits (GitHub rejects commits >100MB)

**Impact**: Large workflows cannot be synced or promoted

### 9.3 Special Characters in Workflow Names

**Scenario**: Workflow named "Test: <script>alert('xss')</script>"

**Risks**:
- Filename sanitization (line 45-52) converts to "Test____script_alert__xss___script_"
- Git file path created successfully
- But workflow name in UI may appear different than file name
- Auto-link by hash may fail (name mismatch)

**Impact**: Confusion, potential security issues if names used in HTML without escaping

### 9.4 Null/Empty Canonical ID

**Scenario**: Untracked workflow has `canonical_id=NULL`

**Risks**:
- Queries filtering by `canonical_id` may not handle NULL correctly
- Auto-link logic (line 424-434) cannot match on NULL
- Promotion logic may crash if NULL not expected

**Impact**: Untracked workflows invisible to certain queries

### 9.5 Timezone Handling Inconsistencies

**Scenario**: Mixed timezone formats in timestamps

**Risks**:
- Some timestamps use 'Z' suffix (line 85: `replace("Z", "+00:00")`)
- Others use explicit timezone
- Comparison logic may fail across timezone boundaries
- Short-circuit optimization (line 371) strips timezone for comparison

**Impact**: False inequality, unnecessary re-processing

---

## 10. Operational Risks

### 10.1 Scheduler Startup Order

**Location**: Main application startup (not shown)

**Risk**: Schedulers start concurrently:
- Drift scheduler
- Sync scheduler
- Deployment scheduler

**Failure Mode**: If database not ready when schedulers start:
- Queries fail
- Schedulers crash or enter error loop
- No automatic recovery on database reconnection

**Impact**: Manual restart required after database outage

### 10.2 Log Flooding

**Location**: Multiple `logger.error()` calls in loops

**Risk**: Error in sync loop (e.g., bad environment config):
- Error logged every 5 minutes (drift scheduler)
- Log volume grows uncontrollably
- Disk fills, service crashes

**Impact**: Operational outage from logging

### 10.3 Audit Trail Completeness

**Location**: `app/services/promotion_service.py:222` (indicates audit logging)

**Risk**: Audit log writes may fail silently:
- If audit service unavailable
- If audit log table write fails
- Promotion continues without audit record

**Impact**: Compliance violations, inability to debug issues

### 10.4 Configuration Drift

**Risk**: Environment configuration (Git URL, PAT, n8n URL) changed manually in database:
- Cached connections (line 31: `self._repo`) become stale
- GitHub service still points to old repo
- Sync writes to wrong repository

**Impact**: Data written to unintended locations

### 10.5 Manual Data Modifications

**Risk**: Operator manually updates database records:
- Changes `workflow_env_map.status` directly
- Bypasses state transition logic
- Sync services overwrite changes on next run

**Impact**: Manual fixes undone automatically

---

## 11. Mitigation Recommendations Summary

### Critical Mitigations

1. **Add Promotion Lock Timeout**: Scheduled deployments need max retry limit
2. **Hash Collision Blocking**: Elevate collision warnings to errors, block operations
3. **Rollback Failure Handling**: Add secondary recovery mechanism if rollback itself fails
4. **Rate Limit Detection**: Implement exponential backoff for GitHub API calls
5. **Connection Pool Limits**: Configure Supabase client with max connections

### High Priority Mitigations

1. **Drift Scheduler Locking**: Per-environment locks to prevent overlapping drift checks
2. **Credential Validation**: Verify credential existence in target before promotion
3. **Git Branch Protection Detection**: Check for protected branches, use PR workflow if needed
4. **Audit Log Reliability**: Make audit writes synchronous, fail promotion if audit fails
5. **Timezone Normalization**: Use consistent UTC timezone handling across all timestamps

### Medium Priority Mitigations

1. **Filename Collision Detection**: Check for duplicates before writing to Git
2. **Large Workflow Handling**: Stream processing for workflows >1000 nodes
3. **Version Skew Detection**: Check n8n API version compatibility on startup
4. **Empty Environment Handling**: Explicit logic for zero-workflow environments
5. **Debounce Window Visibility**: Surface debounce reason to users

### Monitoring Recommendations

1. **Alert on Hash Collisions**: Any collision_warning should trigger alert
2. **Track Rollback Failures**: Count and alert on promotion rollback errors
3. **Monitor Scheduler Lag**: Alert if drift check or sync takes >2x interval time
4. **Watch Active Incident Staleness**: Alert if active_drift_incident_id points to closed incident
5. **Log GitHub Rate Limits**: Track remaining API quota, alert at 20% remaining

---

## 12. Testing Gaps Identified

Based on code analysis, the following scenarios likely lack explicit test coverage:

1. **Partial Batch Failure**: Sync crashes mid-batch, resume from checkpoint
2. **Rollback During Rollback**: Promotion rollback fails, leaving partial state
3. **Hash Collision**: Two workflows normalize to identical hash
4. **Overlapping Schedulers**: Two drift checks for same environment running concurrently
5. **Missing→Reappeared Workflow**: Workflow deleted and recreated with same ID but different content
6. **Credential Mapping Missing**: Promotion proceeds with unmapped credential
7. **Git Protected Branch**: Sync attempts to commit to protected branch
8. **N8N API Timeout**: Large workflow exceeds 30-second timeout
9. **Timezone Boundary**: Short-circuit comparison across DST transition
10. **Orphaned Canonical Workflows**: Git sync creates canonical but no env mapping exists

---

**Document Version**: 1.0
**Last Updated**: 2026-01-14
**Completion Status**: ✓ Complete
