# Snapshot API Error Reference

## 404 Not Found Errors

### Rollback Operations

#### Scenario 1: No Snapshot Available for Rollback
**Endpoint**: `GET /workflows/{workflow_id}/environments/{environment_id}/latest`

**When it occurs**:
- Environment has no snapshots at all
- Environment has snapshots, but none match the requested type (e.g., requesting PRE_PROMOTION but only MANUAL_BACKUP exists)
- First-time promotion scenario (no previous snapshots)

**Error Response**:
```json
{
  "detail": "No snapshot available for rollback in environment {environment_id}"
}
```

or with type filter:

```json
{
  "detail": "No snapshot available for rollback in environment {environment_id} with type {snapshot_type}"
}
```

**HTTP Status**: `404 NOT_FOUND`

**User Action**:
- For first-time promotions: This is expected. Proceed with promotion to create the first snapshot.
- For existing environments: Check if promotions have been executed. PRE_PROMOTION snapshots are only created during promotion operations.

---

#### Scenario 2: Snapshot Not Found
**Endpoint**: `POST /snapshots/{snapshot_id}/restore`

**When it occurs**:
- Provided snapshot_id doesn't exist in the database
- Snapshot_id belongs to a different tenant
- Snapshot was deleted
- User has a typo in the snapshot_id

**Error Response**:
```json
{
  "detail": "Snapshot {snapshot_id} not found"
}
```

**HTTP Status**: `404 NOT_FOUND`

**User Action**:
- Verify the snapshot_id is correct
- Use `GET /workflows/{workflow_id}/environments/{environment_id}/latest` to get the correct snapshot_id
- Check if the snapshot still exists using `GET /snapshots/{snapshot_id}`

---

#### Scenario 3: No Workflows in Snapshot
**Endpoint**: `POST /snapshots/{snapshot_id}/restore`

**When it occurs**:
- Snapshot record exists but GitHub commit has no workflows
- Corrupted snapshot (GitHub data missing)
- Commit SHA is invalid or points to empty state

**Error Response**:
```json
{
  "detail": "No workflows found in GitHub for commit {commit_sha}"
}
```

**HTTP Status**: `404 NOT_FOUND`

**User Action**:
- This indicates a data integrity issue
- Contact administrator to investigate GitHub repository state
- Check if the commit SHA still exists in the repository
- Consider using a different snapshot if available

---

## Other HTTP Error Codes

### 400 Bad Request
**Common scenarios**:
- GitHub not configured for environment
- Missing required environment type
- Invalid request parameters

### 403 Forbidden
**Common scenarios**:
- User lacks permission to perform rollback (via environment action guard)
- Rollback blocked by organizational policy

### 500 Internal Server Error
**Common scenarios**:
- Unexpected errors during snapshot creation or restore
- GitHub API failures
- Database connection issues
- Provider (N8N) API failures

---

## Testing 404 Errors

Run the comprehensive test suite:

```bash
pytest tests/test_t008_404_error_handling.py -v
```

Individual test scenarios:
```bash
# Test no snapshot exists
pytest tests/test_t008_404_error_handling.py::TestT008_404ErrorHandling::test_get_latest_snapshot_returns_404_when_no_snapshot_exists -v

# Test invalid snapshot ID
pytest tests/test_t008_404_error_handling.py::TestT008_404ErrorHandling::test_restore_snapshot_returns_404_when_snapshot_id_not_found -v

# Test no workflows in GitHub
pytest tests/test_t008_404_error_handling.py::TestT008_404ErrorHandling::test_restore_snapshot_returns_404_when_no_workflows_in_github -v
```

---

## Implementation Details

**File**: `app/api/endpoints/snapshots.py`

**Key Error Handling Locations**:
- Line 558-562: No snapshot available for rollback
- Line 612-615: Snapshot ID not found
- Line 709-712: No workflows in GitHub

**Documentation**:
- See `docs/T008_404_ERROR_HANDLING.md` for full implementation details
- See endpoint docstrings for complete error specifications
