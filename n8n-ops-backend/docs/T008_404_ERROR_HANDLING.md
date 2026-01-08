# T008: 404 Error Response for Rollback Operations

## Overview
This document details the implementation of Task T008, which ensures that appropriate 404 error responses are returned when no snapshot exists for rollback operations.

## Implementation Summary

### Endpoints Covered

#### 1. GET `/workflows/{workflow_id}/environments/{environment_id}/latest`
**Purpose**: Fetch the latest snapshot for rollback preparation

**404 Scenarios**:
- No snapshots exist for the environment at all
- No snapshots exist matching the specified type filter (e.g., PRE_PROMOTION)
- Environment exists but has never had a promotion (no PRE_PROMOTION snapshots)

**Error Message Format**:
```
No snapshot available for rollback in environment {environment_id} [with type {type}]
```

**Code Location**: `app/api/endpoints/snapshots.py:552-557`

#### 2. POST `/snapshots/{snapshot_id}/restore`
**Purpose**: Execute rollback by restoring a snapshot

**404 Scenarios**:
1. **Snapshot ID not found**: The provided snapshot_id doesn't exist in the database
   - Error: `Snapshot {snapshot_id} not found`
   - Code Location: `app/api/endpoints/snapshots.py:597-601`

2. **No workflows in GitHub**: Snapshot exists but contains no workflows at the commit SHA
   - Error: `No workflows found in GitHub for commit {commit_sha}`
   - Code Location: `app/api/endpoints/snapshots.py:694-698`

### Error Response Format

All 404 responses follow FastAPI's HTTPException pattern:

```json
{
  "detail": "No snapshot available for rollback in environment env-123 with type pre_promotion"
}
```

HTTP Status Code: `404 NOT_FOUND`

### User Experience

When users encounter these errors, they indicate:

1. **First-time promotion**: No previous snapshot exists because this is the first promotion to the environment
2. **Manual snapshot only**: Only MANUAL_BACKUP snapshots exist, but user is searching for PRE_PROMOTION
3. **Invalid snapshot ID**: User provided a snapshot ID that doesn't exist (typo, wrong tenant, deleted)
4. **Corrupted snapshot**: Snapshot record exists but GitHub commit has no workflows (data integrity issue)

### Testing

Comprehensive test suite: `tests/test_t008_404_error_handling.py`

Test coverage includes:
- ✅ No snapshot exists for environment
- ✅ No PRE_PROMOTION snapshot (only other types exist)
- ✅ Invalid snapshot ID on restore
- ✅ Snapshot exists but no workflows in GitHub
- ✅ No type filter with empty environment
- ✅ Error message clarity for rollback scenarios

All tests validate:
- Correct HTTP status code (404)
- Clear, actionable error messages
- Inclusion of relevant context (environment_id, snapshot_type, commit_sha)

### Integration with Existing Code

This task leveraged existing error handling patterns:

1. **Already implemented** (verified):
   - ✅ 404 on missing snapshot in `get_latest_snapshot_for_workflow_environment`
   - ✅ 404 on missing snapshot in `restore_snapshot`
   - ✅ 404 on empty workflows from GitHub

2. **Enhanced**:
   - 📝 Added comprehensive docstrings documenting all error scenarios
   - 📝 Created dedicated test suite for T008
   - 📝 Documented error handling patterns

### Code Quality

- **Error messages**: Clear, include relevant IDs, actionable
- **Logging**: Server-side errors logged before HTTPException raised
- **Consistency**: All endpoints use same HTTPException pattern
- **Type safety**: Uses FastAPI's status constants (status.HTTP_404_NOT_FOUND)

## Acceptance Criteria Met

✅ **Given**: Workflow in environment has no PRE_PROMOTION snapshot
✅ **When**: User attempts rollback
✅ **Then**: API returns 404 with "No snapshot available for rollback"

✅ **Given**: User provides invalid snapshot ID
✅ **When**: User triggers restore
✅ **Then**: API returns 404 with "Snapshot {id} not found"

✅ **Given**: Snapshot exists but GitHub has no workflows
✅ **When**: Restore is attempted
✅ **Then**: API returns 404 with "No workflows found in GitHub for commit {sha}"

## Related Tasks

- **T004**: Implemented the GET endpoint for latest snapshot
- **T005**: Implemented the restore endpoint for rollback
- **T006**: Added environment action guards for rollback
- **T007**: Added audit logging for rollback actions

## Future Enhancements (Out of Scope)

- Custom error codes for different 404 scenarios
- Suggested actions in error messages (e.g., "Run a promotion first to create a snapshot")
- Webhook notifications when 404 errors occur
- Retry mechanisms for transient GitHub API failures
