# ADR-010: UI Terminology - Refresh Not Sync

**Status**: Accepted

**Date**: 2025-01-16

## Context

The application originally used "Sync" terminology throughout the user interface to describe operations that update data from n8n instances to the WorkflowOps database. This terminology was inconsistent and potentially confusing:

1. **Ambiguity**: "Sync" can imply bidirectional synchronization, when the operation is actually a one-way refresh from the source
2. **User Confusion**: Users might expect "sync" to mean keeping two systems identical, rather than pulling the latest state
3. **Consistency**: Legacy code contained mixed terminology with some instances using sync-related terms

The goal was to establish clear, consistent terminology that accurately reflects the operation being performed: refreshing the WorkflowOps state with the latest data from n8n.

## Decision

All user-facing text in the application will use **"Refresh"** terminology instead of **"Sync"** terminology.

### Scope of Changes

**Applies to**:
- Button labels (e.g., "Refresh Workflows", "Refresh Git")
- Status messages (e.g., "Refreshing environment state", "Refresh completed")
- Toast notifications (e.g., "Refreshed 47 workflows from N8N")
- Error messages (e.g., "Failed to refresh environment")
- Tooltips and aria-labels
- Empty state messages
- Progress indicators
- Badge labels (e.g., "Up to Date" instead of "In Sync")

**Does NOT apply to**:
- Variable names (e.g., `syncStatus`, `lastSyncAt`)
- Function names (e.g., `syncEnvironment()`, `handleSync()`)
- API endpoints (e.g., `/api/environments/sync`)
- Backend references and database fields
- Code comments and internal documentation
- Type definitions and interfaces

### Terminology Mapping

| Old Term | New Term | Context |
|----------|----------|---------|
| Sync | Refresh | Action/button label |
| Syncing | Refreshing | In-progress status |
| Synced | Refreshed | Completed status |
| In Sync | Up to Date | Status badge |
| Synchronization | Refresh | General noun |
| Last Synced | Last Refreshed | Timestamp label |

## Consequences

### Positive

1. **Clarity**: "Refresh" more accurately describes the one-way operation of updating WorkflowOps state from n8n
2. **Consistency**: All user-facing text follows the same terminology convention
3. **User Experience**: Users have a clearer understanding of what actions do
4. **Future Maintenance**: Clear guidelines for all future UI development

### Negative

1. **Migration Effort**: Existing users familiar with "Sync" terminology will need to adapt to new labels
2. **Code-UI Mismatch**: Internal code still uses "sync" terminology, which could cause minor confusion for developers
3. **Documentation Updates**: May require updates to user documentation and tutorials

### Neutral

1. **Backend Unchanged**: API endpoints and backend logic remain unchanged to avoid breaking changes
2. **Incremental Adoption**: Can be applied gradually to new features without requiring immediate full codebase refactor

## Implementation

The terminology change was implemented across the following areas:

1. **Component Files**: BackgroundJobProgress, EnvironmentStatusBadge, empty-states
2. **Page Files**: All major pages including Environments, Workflows, Activity Center, Credentials, etc.
3. **Utility Files**: environment-utils tooltips and helper text
4. **Demo Pages**: LoadingStatesDemo updated to match new terminology

All changes were made using automated search-and-replace with careful review to ensure only user-facing text was modified.

## Notes

- This ADR documents a UI-only change and does not affect API contracts or backend behavior
- Future features should follow this terminology convention for consistency
- If bidirectional synchronization is ever implemented, new terminology (e.g., "Sync") could be reintroduced for that specific use case
