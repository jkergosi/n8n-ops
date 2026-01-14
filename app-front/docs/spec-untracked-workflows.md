# Specification: Untracked Workflow Detection (v2)

## 1. Problem
When workflows exist in n8n environments but are not tracked in the canonical workflow system, users have no visibility into these "orphan" workflows. This creates gaps in workflow governance, as untracked workflows won't be managed through the promotion pipeline or have proper environment mappings.

## 2. Solution
Create a dedicated Untracked Workflows feature with:
1. **Backend API**: Endpoints to scan connected n8n environments, diff against canonical mappings, and onboard selected workflows safely.
2. **Frontend UI**: A page to display untracked workflows grouped by environment, with selective onboarding capability.

## 3. Definition: What is an "Untracked Workflow"?

A workflow is considered **untracked** if:
- It exists in an n8n environment **AND**
- There is **no canonical environment mapping** for `(env_id, n8n_workflow_id)` **OR**
- The mapping has `status = 'untracked'` in `workflow_env_map`

### Explicit Non-Goals (MVP)
- No name-based auto-matching
- No inference or merge logic
- No automatic attachment to existing canonical workflows

Onboarding is **always explicit** in MVP. Each onboarded workflow creates a new canonical workflow record.

## 4. Acceptance Criteria

- **AC1**: GIVEN a user navigates to the Untracked Workflows page, WHEN environments have workflows not in the canonical system, THEN these workflows are displayed grouped by environment with their n8n workflow ID and name.

- **AC2**: GIVEN the untracked workflows list is displayed, WHEN the user selects workflows and clicks "Onboard Selected", THEN new canonical workflow records are created with environment mappings for the selected workflows atomically.

- **AC3**: GIVEN the user wants to scan for untracked workflows, WHEN they click "Scan Environments", THEN all active environments are scanned and the list refreshes with current data.

- **AC4**: GIVEN an untracked workflow is onboarded, WHEN the user views the Canonical Workflows page, THEN the newly onboarded workflow appears with the correct environment mapping.

- **AC5**: GIVEN a uniqueness constraint on `(tenant_id, environment_id, n8n_workflow_id)` in `workflow_env_map`, WHEN the user attempts to onboard a workflow that is already mapped, THEN the API returns an appropriate error.

## 5. API Contract

### 5.1 GET /api/v1/canonical/untracked

Retrieve all untracked workflows across environments for the current tenant.

**Request**: None (uses auth token to determine tenant)

**Response**:
```json
{
  "environments": [
    {
      "environment_id": "uuid",
      "environment_name": "Production",
      "environment_class": "production",
      "untracked_workflows": [
        {
          "n8n_workflow_id": "123",
          "name": "My Workflow",
          "active": true,
          "created_at": "2024-01-01T00:00:00Z",
          "updated_at": "2024-01-15T00:00:00Z"
        }
      ]
    }
  ],
  "total_untracked": 5
}
```

### 5.2 POST /api/v1/canonical/untracked/onboard

Onboard selected untracked workflows into the canonical system.

**Request**:
```json
{
  "workflows": [
    {
      "environment_id": "uuid",
      "n8n_workflow_id": "123"
    }
  ]
}
```

**Response** (success):
```json
{
  "onboarded": [
    {
      "environment_id": "uuid",
      "n8n_workflow_id": "123",
      "canonical_id": "new-canonical-uuid",
      "display_name": "My Workflow"
    }
  ],
  "failed": [],
  "total_onboarded": 1,
  "total_failed": 0
}
```

**Response** (partial failure):
```json
{
  "onboarded": [...],
  "failed": [
    {
      "environment_id": "uuid",
      "n8n_workflow_id": "456",
      "error": "Workflow already has canonical mapping"
    }
  ],
  "total_onboarded": 1,
  "total_failed": 1
}
```

### 5.3 POST /api/v1/canonical/untracked/scan

Trigger a scan of all active environments to refresh untracked workflow data.

**Request**: None

**Response**:
```json
{
  "job_id": "uuid",
  "status": "pending",
  "message": "Scan job started"
}
```

## 6. Files to Modify

### Backend Files

| File | Purpose | Action |
|------|---------|--------|
| `app-back/app/api/endpoints/untracked_workflows.py` | API endpoints for scan + onboarding | create |
| `app-back/app/services/untracked_workflows_service.py` | Business logic: scan n8n, detect untracked | create |
| `app-back/app/schemas/untracked_workflow.py` | Pydantic schemas for API request/response | create |
| `app-back/app/services/n8n_client.py` | List workflows per environment (existing `get_workflows()` method) | no change needed |
| `app-back/app/services/database.py` | Add method for atomic canonical+mapping creation | modify |
| `app-back/app/main.py` | Register new router | modify |

### Frontend Files

| File | Purpose | Action |
|------|---------|--------|
| `app-front/src/pages/UntrackedWorkflowsPage.tsx` | Main page for viewing and onboarding untracked workflows | create |
| `app-front/src/lib/api-client.ts` | Add API methods for untracked workflow detection | modify |
| `app-front/src/types/index.ts` | Add types for untracked workflow responses | modify |
| `app-front/src/App.tsx` | Add route for the new page | modify |
| `app-front/src/components/AppLayout.tsx` | Add navigation link to the page | modify |

### Test Files

| File | Purpose | Action |
|------|---------|--------|
| `app-back/tests/test_untracked_workflows.py` | Unit tests for backend service | create |
| `app-front/tests/untracked-workflows.spec.ts` | Playwright E2E verification test | create |

## 7. Implementation Tasks

```tasks
- [ ] T001: Create Pydantic schemas for untracked workflows | File: app-back/app/schemas/untracked_workflow.py
- [ ] T002: Create UntrackedWorkflowsService with scan logic | File: app-back/app/services/untracked_workflows_service.py
- [ ] T003: Add atomic canonical+mapping creation method to database service | File: app-back/app/services/database.py
- [ ] T004: Create API endpoints for untracked workflows | File: app-back/app/api/endpoints/untracked_workflows.py
- [ ] T005: Register untracked workflows router in main.py | File: app-back/app/main.py
- [ ] T006: Add UntrackedWorkflow types to frontend types | File: app-front/src/types/index.ts
- [ ] T007: Add API client methods for untracked workflows | File: app-front/src/lib/api-client.ts
- [ ] T008: Create UntrackedWorkflowsPage component | File: app-front/src/pages/UntrackedWorkflowsPage.tsx
- [ ] T009: Add route for UntrackedWorkflowsPage | File: app-front/src/App.tsx
- [ ] T010: Add navigation link in sidebar | File: app-front/src/components/AppLayout.tsx
- [ ] T011: Create backend unit tests | File: app-back/tests/test_untracked_workflows.py
- [ ] T012: Create Playwright verification test | File: app-front/tests/untracked-workflows.spec.ts
- [ ] T013: Run verification test and delete test file | File: app-front/tests/untracked-workflows.spec.ts
```

## 8. Database Considerations

### Existing Tables Used
- `workflow_env_map`: Check for existing mappings; create new mappings on onboard
- `canonical_workflows`: Create new canonical workflow records on onboard
- `environments`: Get list of active environments for scanning

### Uniqueness Constraint
The `workflow_env_map` table should have a unique constraint on `(tenant_id, environment_id, n8n_workflow_id)` to prevent duplicate mappings. If this doesn't exist, a migration should be added.

### Atomic Onboarding Operation
When onboarding a workflow:
1. Create canonical workflow record in `canonical_workflows`
2. Create/update mapping in `workflow_env_map` with `status = 'linked'`

Both operations must succeed or fail together (use transaction or database function).

## 9. Service Implementation Details

### UntrackedWorkflowsService.scan_environments()

```python
async def scan_environments(tenant_id: str) -> List[Dict]:
    """
    Scan all active environments for untracked workflows.

    Algorithm:
    1. Get all active environments for tenant
    2. For each environment:
       a. Fetch workflows from n8n via N8NClient.get_workflows()
       b. Get existing mappings from workflow_env_map
       c. Diff: untracked = n8n_workflows - mapped_workflows
    3. Return grouped results
    """
```

### UntrackedWorkflowsService.onboard_workflows()

```python
async def onboard_workflows(
    tenant_id: str,
    user_id: str,
    workflows: List[OnboardRequest]
) -> OnboardResponse:
    """
    Onboard selected workflows to canonical system.

    For each workflow:
    1. Verify workflow exists in n8n (optional, can skip for MVP)
    2. Verify no existing mapping exists
    3. Create canonical_workflow record
    4. Create workflow_env_map record with status='linked'
    5. Return success/failure for each
    """
```

## 10. UI Implementation Details

### UntrackedWorkflowsPage Component

**State**:
- `environments`: Grouped untracked workflows by environment
- `selectedWorkflows`: Set of selected `{env_id, n8n_workflow_id}` tuples
- `isScanning`: Loading state for scan operation
- `isOnboarding`: Loading state for onboard operation

**Features**:
- Environment accordion/expandable sections
- Checkbox selection for individual workflows
- "Select All" per environment
- "Onboard Selected" button (disabled when nothing selected)
- "Scan Environments" button to refresh data
- Success/error toast notifications

## 11. Verification

1. Navigate to `/canonical/untracked` and verify the page loads
2. Click "Scan Environments" and verify environments are scanned
3. Verify untracked workflows are displayed grouped by environment
4. Select an untracked workflow and click "Onboard Selected"
5. Verify the workflow appears in the Canonical Workflows page with correct mapping
6. Verify the workflow no longer appears in the untracked list
7. Run Playwright test to verify core functionality

---

## Changelog

### v2 (Current)
- Added backend scope with service layer and API endpoints
- Defined "untracked workflow" precisely
- Added explicit API contracts with request/response schemas
- Added database considerations (uniqueness constraint, atomic operations)
- Added service implementation details
- Split tasks into backend and frontend sections
- Added unit test task for backend

### v1 (Previous)
- Initial frontend-only specification
