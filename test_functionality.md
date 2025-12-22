# Functionality Test Checklist

## 1. Rerun Deployment Feature ✅

### Backend Tests:
- [x] Endpoint `POST /deployments/{id}/rerun` exists
- [x] Endpoint properly imports `_execute_promotion_background`
- [x] Validates deployment exists and is in terminal state
- [x] Reconstructs workflow selections from deployment_workflows
- [x] Maps deployment change_type to promotion change_type correctly
- [x] Creates new promotion and deployment
- [x] Creates audit log entry

### Frontend Tests:
- [x] `rerunDeployment` method exists in api-client.ts
- [x] Rerun button appears in DeploymentsPage for failed/canceled/success deployments
- [x] Rerun button appears in DeploymentDetailPage for terminal states
- [x] Confirmation modal shows correct summary
- [x] Modal shows pipeline, stage, workflow count, and gates
- [x] On success, navigates to new deployment

### Test Cases:
1. Rerun a failed deployment → Should create new deployment
2. Rerun a canceled deployment → Should create new deployment
3. Rerun a successful deployment → Should create new deployment (re-deploy)
4. Try to rerun a running deployment → Should show error
5. Try to rerun a deleted deployment → Should show error

## 2. Pipelines Tab Consolidation ✅

### Backend Tests:
- [x] Pipelines endpoint still works independently
- [x] No breaking changes to pipeline routes

### Frontend Tests:
- [x] Tabs component properly imported
- [x] Deployments tab shows deployment list
- [x] Pipelines tab shows pipeline list
- [x] Tab state synced with URL query params
- [x] Pipelines data lazy-loaded (only when tab active)
- [x] Redirect `/pipelines` → `/deployments?tab=pipelines` works
- [x] Pipeline editing routes still work (`/pipelines/new`, `/pipelines/:id`)

### Test Cases:
1. Navigate to `/deployments` → Should show Deployments tab by default
2. Navigate to `/deployments?tab=pipelines` → Should show Pipelines tab
3. Navigate to `/pipelines` → Should redirect to `/deployments?tab=pipelines`
4. Click Pipelines tab → Should load pipelines data
5. Switch back to Deployments tab → Pipelines query should not refetch unnecessarily

## 3. Executions Page Header Fix ✅

### Frontend Tests:
- [x] Header shows `currentEnvironment?.name` first
- [x] Falls back to `currentEnvironment?.type` if name missing
- [x] Falls back to `selectedEnvironment` if both missing
- [x] No longer shows raw UUID

### Test Cases:
1. View executions with environment that has name → Should show name
2. View executions with environment without name → Should show type (dev/staging/prod)
3. View executions with no environment → Should show selectedEnvironment

## 4. Executions Sync Fix ✅

### Backend Tests:
- [x] Limit increased from 100 to 1000
- [x] Better error handling and logging added
- [x] Response format handling improved
- [x] Connection test before sync

### Frontend Tests:
- [x] Sync button works
- [x] Shows correct synced count
- [x] Error messages displayed properly

### Test Cases:
1. Sync executions from N8N → Should fetch up to 1000 executions
2. Sync with no executions → Should show "Synced 0" but not error
3. Sync with connection error → Should show error message

## 5. Observability Page ✅

### Backend Tests:
- [x] Endpoint `/observability/overview` exists
- [x] Service uses real database queries
- [x] All data sources connected (executions, workflows, deployments, environments)

### Frontend Tests:
- [x] Page loads overview data
- [x] KPI cards display real data
- [x] Workflow performance table shows real data
- [x] Environment health shows real data
- [x] Promotion stats show real data

### Test Cases:
1. View observability page → Should load all metrics
2. Change time range → Should refetch with new range
3. Verify all cards show real numbers (not placeholders)

## 6. Alerts Page Username Fix ✅

### Frontend Tests:
- [x] `defaultSlackConfig.username` is empty string (not 'N8N Ops')
- [x] Form field starts empty
- [x] User can still enter username manually

### Test Cases:
1. Open "Add notification channel" → Username field should be empty
2. Enter username manually → Should work correctly

## 7. Credentials Sync Fix ✅

### Backend Tests:
- [x] Connection test before sync
- [x] Better error handling and logging
- [x] Response format handling improved
- [x] Handles empty credentials list gracefully

### Frontend Tests:
- [x] Sync button works
- [x] Shows correct synced count

### Test Cases:
1. Sync credentials → Should fetch and sync all credentials
2. Sync with no credentials → Should show "Synced 0" but not error
3. Sync with API permission error → Should show warning, not crash

## 8. N8N Users Sync Fix ✅

### Backend Tests:
- [x] Better error handling and logging
- [x] Response format handling improved
- [x] Handles 401/403/404 gracefully
- [x] Connection test before sync

### Frontend Tests:
- [x] Sync button works
- [x] Shows correct synced count

### Test Cases:
1. Sync users → Should fetch and sync all users
2. Sync with no users → Should show "Synced 0" but not error
3. Sync with API permission error → Should show warning, not crash

## 9. Audit Logs Page ✅

### Backend Tests:
- [x] Endpoint `/admin/audit-logs` exists
- [x] Filters and pagination work
- [x] Audit logs are written for relevant actions

### Frontend Tests:
- [x] Page loads audit logs
- [x] Filters work (action type, search)
- [x] Pagination works
- [x] Detail sheet opens on row click
- [x] Detail sheet shows all information

### Test Cases:
1. View audit logs → Should show list of logs
2. Filter by action type → Should filter correctly
3. Search logs → Should search in action/resource_name/actor_email
4. Click on a log row → Should open detail sheet
5. Detail sheet shows all fields → Actor, timestamp, before/after, metadata, etc.

## 10. Audit Log Detail View ✅

### Frontend Tests:
- [x] Sheet component imported
- [x] Sheet opens when row clicked
- [x] Shows actor information
- [x] Shows timestamp
- [x] Shows action type and action
- [x] Shows resource information
- [x] Shows tenant information
- [x] Shows request context (IP, metadata)
- [x] Shows before/after values (formatted JSON)
- [x] Shows reason if available
- [x] Handles large payloads (scrollable)

### Test Cases:
1. Click audit log row → Sheet should open
2. View log with old/new values → Should show formatted JSON
3. View log with large metadata → Should be scrollable
4. Close sheet → Should close properly
