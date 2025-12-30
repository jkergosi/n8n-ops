# Drift Implementation Plan

This document provides an actionable, iterative implementation plan for transforming drift from scattered UI signals into a first-class incident-based system.

---

## Current State Analysis (Phase 0 Complete)

### Existing Drift Infrastructure

#### Backend Services

| Service | Location | Purpose |
|---------|----------|---------|
| `diff_service.py` | `n8n-ops-backend/app/services/` | JSON comparison for workflow drift detection |
| `sync_status_service.py` | `n8n-ops-backend/app/services/` | Computes workflow sync status (in_sync, local_changes, update_available, conflict) |
| `promotion_service.py` | `n8n-ops-backend/app/services/` | Drift checks during promotion flow |
| `workflow_analysis_service.py` | `n8n-ops-backend/app/services/` | Placeholder drift analysis |

#### Key Data Structures (Already Exist)

```python
# diff_service.py
@dataclass
class DriftDifference:
    path: str
    git_value: Any
    runtime_value: Any
    diff_type: str  # 'added', 'removed', 'modified'

@dataclass
class DriftResult:
    has_drift: bool
    git_version: dict
    runtime_version: dict
    git_commit: Optional[str]
    differences: List[DriftDifference]
    summary: DriftSummary

# sync_status_service.py
class SyncStatus(str, Enum):
    in_sync = "in_sync"
    local_changes = "local_changes"
    update_available = "update_available"
    conflict = "conflict"
```

#### Database (Current Schema)

| Table | Drift-Related Fields | Notes |
|-------|---------------------|-------|
| `workflows` | `sync_status`, `last_synced_at` | Per-workflow sync state |
| `snapshots` | `git_commit_sha`, `type`, `metadata_json` | Git baseline for comparison |
| `environments` | None | **GAP: No drift_status field** |
| `deployments` | `status` | Tracks promotion outcomes |

#### API Endpoints (Current)

| Endpoint | Location | Purpose |
|----------|----------|---------|
| `GET /workflows/{id}/drift` | `workflows.py` | Check drift for single workflow |
| `POST /promotions/check-drift` | `promotions.py` | Pre-promotion drift validation |
| `POST /promotions/initiate` | `promotions.py` | Promotion with drift gates |

#### Frontend Components

| Component | Location | Current Drift UX |
|-----------|----------|------------------|
| `WorkflowDiffDialog.tsx` | `src/components/promotion/` | Detailed diff visualization |
| `EnvironmentsPage.tsx` | `src/pages/` | Drift column indicator |
| `EnvironmentDetailPage.tsx` | `src/pages/` | Drift summary section |
| `WorkflowDetailPage.tsx` | `src/pages/` | Per-workflow drift status |
| `DeploymentsPage.tsx` | `src/pages/` | Deployment with drift context |

### Identified Gaps

| Gap | Impact | Phase to Address |
|-----|--------|------------------|
| No `drift_incidents` table | Cannot track incident lifecycle | Phase 2 |
| No `drift_status` on environments | No environment-level drift state | Phase 1 |
| No `drift_reconciliation_artifacts` table | Cannot track resolution outcomes | Phase 4 |
| No dedicated Drift Incident workspace | Drift UX scattered across pages | Phase 2-3 |
| No TTL/SLA fields | Cannot enforce time-based policies | Phase 5 |
| No plan-gated drift features | All users see same drift UX | Phase 1-2 |

---

## Implementation Phases

### Phase 1: Always-On Drift Detection + Minimal Surfacing

**Objective**: Establish reliable drift detection and single consolidated indicator for ALL plans.

#### Step 1.1: Add drift_status to environments table

**Files to modify**:
- `n8n-ops-backend/migrations/` - New migration file

**Migration SQL**:
```sql
-- Add drift tracking fields to environments
ALTER TABLE environments ADD COLUMN drift_status VARCHAR(50) DEFAULT 'unknown';
ALTER TABLE environments ADD COLUMN last_drift_detected_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE environments ADD COLUMN drift_summary JSONB;

-- Create index for efficient drift queries
CREATE INDEX idx_environments_drift_status ON environments(drift_status);

-- Valid drift_status values: 'unknown', 'in_sync', 'drift_detected'
```

**Files to modify**:
- `n8n-ops-backend/app/schemas/environments.py` - Add fields to schema
- `n8n-ops-backend/app/services/database.py` - Add update methods

**Acceptance Criteria**:
- [ ] Migration runs without errors
- [ ] Environment schema includes drift_status, last_drift_detected_at, drift_summary
- [ ] Database methods exist: `update_environment_drift_status(env_id, status, summary)`

---

#### Step 1.2: Create Drift Detection Service

**New file**: `n8n-ops-backend/app/services/drift_detection_service.py`

**Purpose**: Centralized service for environment-level drift detection

**Key functions**:
```python
class DriftDetectionService:
    async def detect_drift(self, environment_id: str) -> DriftDetectionResult:
        """
        Compare all workflows in environment against GitHub source of truth.
        Returns aggregated drift status and summary.
        """

    async def get_environment_drift_summary(self, environment_id: str) -> DriftSummary:
        """
        Get cached drift summary for environment.
        """

    async def refresh_drift_status(self, environment_id: str) -> None:
        """
        Re-run drift detection and update environment drift_status.
        """
```

**Integration points**:
- Uses existing `diff_service.py` for workflow comparison
- Uses existing `sync_status_service.py` for normalization
- Updates environment drift_status via database service

**Acceptance Criteria**:
- [ ] Service compares all environment workflows against GitHub
- [ ] Properly normalizes workflows (excludes runtime metadata)
- [ ] Persists drift_status and drift_summary to environments table
- [ ] Emits `drift.detected` event when drift found

---

#### Step 1.3: Add Drift Detection API Endpoint

**File to modify**: `n8n-ops-backend/app/api/endpoints/environments.py`

**New endpoints**:
```python
@router.get("/{environment_id}/drift")
async def get_environment_drift(environment_id: str):
    """Get drift status and summary for environment."""

@router.post("/{environment_id}/drift/refresh")
async def refresh_environment_drift(environment_id: str):
    """Trigger drift detection refresh."""
```

**Acceptance Criteria**:
- [ ] GET returns drift_status, last_drift_detected_at, drift_summary
- [ ] POST triggers fresh drift detection
- [ ] Both endpoints work for all plan tiers

---

#### Step 1.4: Update Frontend API Client

**File to modify**: `n8n-ops-ui/src/lib/api-client.ts`

**New methods**:
```typescript
async getEnvironmentDrift(environmentId: string): Promise<EnvironmentDriftResponse>
async refreshEnvironmentDrift(environmentId: string): Promise<void>
```

**Acceptance Criteria**:
- [ ] API client methods added and typed
- [ ] Error handling for drift endpoints

---

#### Step 1.5: Add Drift Status Badge to Environment List

**File to modify**: `n8n-ops-ui/src/pages/EnvironmentsPage.tsx`

**Changes**:
- Add "Drift Status" column to environments table
- Show badge: "In Sync" (green) | "Drift Detected" (yellow) | "Unknown" (gray)
- Badge links to environment detail page drift section

**Acceptance Criteria**:
- [ ] Drift status column visible in environment list
- [ ] Badge color-coded by status
- [ ] Clicking badge navigates to environment detail

---

#### Step 1.6: Add Drift Banner to Environment Detail

**File to modify**: `n8n-ops-ui/src/pages/EnvironmentDetailPage.tsx`

**Changes**:
- Add drift banner at top of page when drift_detected
- Banner shows: affected workflow count, last detected time
- Single CTA: "View Drift" (routes to drift section/workspace)
- For Phase 1: "View Drift" scrolls to drift summary section

**Acceptance Criteria**:
- [ ] Banner appears when drift_status === 'drift_detected'
- [ ] Banner shows affected workflow count
- [ ] CTA navigates to drift details

---

#### Step 1.7: Create Drift Summary Section

**File to modify**: `n8n-ops-ui/src/pages/EnvironmentDetailPage.tsx`

**New section** (within existing page):
- Drift summary card showing:
  - Total workflows with drift
  - List of affected workflows (name, drift type)
  - Last detected timestamp
  - "Refresh" button to re-check drift
- For free tier: Show summary + manual remediation guidance
- For paid tiers: Show summary + "Manage Drift" button (Phase 2)

**Acceptance Criteria**:
- [ ] Drift summary section renders in environment detail
- [ ] Shows affected workflow list
- [ ] Refresh button triggers drift detection
- [ ] Plan-gated CTA for incident management

---

#### Step 1.8: Add Plan Gating Utility

**File to modify**: `n8n-ops-backend/app/core/feature_gates.py`

**New feature flags**:
```python
DRIFT_FEATURES = {
    'drift_detection': ['free', 'pro', 'agency', 'enterprise'],  # All plans
    'drift_visibility': ['free', 'pro', 'agency', 'enterprise'],  # All plans
    'drift_incidents': ['pro', 'agency', 'enterprise'],  # Paid only
    'drift_full_diff': ['agency', 'enterprise'],  # Higher tiers
    'drift_ttl_sla': ['agency', 'enterprise'],  # Higher tiers
    'drift_policies': ['enterprise'],  # Enterprise only
}
```

**Acceptance Criteria**:
- [ ] Feature gate functions added
- [ ] Gates enforced at API boundary
- [ ] UI can check feature availability

---

### Phase 1 Exit Criteria

- [ ] Drift detection runs reliably for any environment
- [ ] Environment list shows drift status badge
- [ ] Environment detail shows drift banner + summary
- [ ] Single entry point for drift details (no scattered callouts)
- [ ] All users can see drift; no user is blind to drift
- [ ] Plan gating infrastructure in place

---

### Phase 2: Drift Incident Object + Workspace

**Objective**: Introduce Drift Incident as first-class citizen with centralized UX.

#### Step 2.1: Create drift_incidents Table

**New migration file**: `n8n-ops-backend/migrations/`

**Migration SQL**:
```sql
CREATE TABLE drift_incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    environment_id UUID NOT NULL REFERENCES environments(id),
    status VARCHAR(50) NOT NULL DEFAULT 'detected',
    -- Status values: detected, acknowledged, stabilized, reconciled, closed

    detected_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    stabilized_at TIMESTAMP WITH TIME ZONE,
    reconciled_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE,

    owner_user_id UUID REFERENCES users(id),
    reason TEXT,
    ticket_ref TEXT,

    -- Agency+ fields (nullable for lower tiers)
    expires_at TIMESTAMP WITH TIME ZONE,
    severity VARCHAR(20),

    -- Snapshot of affected workflows at detection time
    affected_workflows JSONB NOT NULL DEFAULT '[]',
    drift_snapshot JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_drift_incidents_tenant ON drift_incidents(tenant_id);
CREATE INDEX idx_drift_incidents_environment ON drift_incidents(environment_id);
CREATE INDEX idx_drift_incidents_status ON drift_incidents(status);

-- Add reference from environments to active incident
ALTER TABLE environments ADD COLUMN active_drift_incident_id UUID REFERENCES drift_incidents(id);
```

**Acceptance Criteria**:
- [ ] Migration runs without errors
- [ ] Table supports full incident lifecycle
- [ ] Environment links to active incident

---

#### Step 2.2: Create Drift Incident Schema

**New file**: `n8n-ops-backend/app/schemas/drift_incidents.py`

**Schemas**:
```python
class DriftIncidentStatus(str, Enum):
    detected = "detected"
    acknowledged = "acknowledged"
    stabilized = "stabilized"
    reconciled = "reconciled"
    closed = "closed"

class DriftIncidentCreate(BaseModel):
    environment_id: str
    affected_workflows: List[AffectedWorkflow]
    drift_snapshot: Optional[dict]

class DriftIncidentUpdate(BaseModel):
    status: Optional[DriftIncidentStatus]
    owner_user_id: Optional[str]
    reason: Optional[str]
    ticket_ref: Optional[str]
    expires_at: Optional[datetime]
    severity: Optional[str]

class DriftIncidentResponse(BaseModel):
    id: str
    environment_id: str
    status: DriftIncidentStatus
    detected_at: datetime
    acknowledged_at: Optional[datetime]
    # ... all fields
    affected_workflows: List[AffectedWorkflow]
```

**Acceptance Criteria**:
- [ ] All lifecycle states defined
- [ ] Create/Update/Response schemas complete
- [ ] Affected workflow structure defined

---

#### Step 2.3: Create Drift Incident Service

**New file**: `n8n-ops-backend/app/services/drift_incident_service.py`

**Key methods**:
```python
class DriftIncidentService:
    async def create_incident(self, data: DriftIncidentCreate) -> DriftIncident:
        """Create new drift incident for environment."""

    async def acknowledge_incident(self, incident_id: str, user_id: str, reason: str) -> DriftIncident:
        """Acknowledge incident with reason."""

    async def update_status(self, incident_id: str, status: DriftIncidentStatus) -> DriftIncident:
        """Update incident status with validation."""

    async def close_incident(self, incident_id: str, resolution_artifact_id: str) -> DriftIncident:
        """Close incident (requires resolution artifact)."""

    async def get_active_incident(self, environment_id: str) -> Optional[DriftIncident]:
        """Get active (non-closed) incident for environment."""

    def _validate_status_transition(self, current: str, target: str) -> bool:
        """Validate allowed status transitions."""
```

**Status Transition Rules**:
```
detected -> acknowledged (requires reason)
acknowledged -> stabilized
stabilized -> reconciled (requires resolution started)
reconciled -> closed (requires drift resolved)
```

**Acceptance Criteria**:
- [ ] All lifecycle methods implemented
- [ ] Status transition validation enforced
- [ ] Plan gating enforced (Pro+ only)
- [ ] Emits events for status changes

---

#### Step 2.4: Create Drift Incident API Endpoints

**New file**: `n8n-ops-backend/app/api/endpoints/drift_incidents.py`

**Endpoints**:
```python
@router.post("/")
async def create_drift_incident(data: DriftIncidentCreate):
    """Create drift incident (Pro+ only)."""

@router.get("/{incident_id}")
async def get_drift_incident(incident_id: str):
    """Get incident details."""

@router.get("/environment/{environment_id}/active")
async def get_active_incident(environment_id: str):
    """Get active incident for environment."""

@router.put("/{incident_id}/acknowledge")
async def acknowledge_incident(incident_id: str, data: AcknowledgeRequest):
    """Acknowledge incident with reason."""

@router.put("/{incident_id}/status")
async def update_incident_status(incident_id: str, data: StatusUpdateRequest):
    """Update incident status."""

@router.get("/")
async def list_incidents(environment_id: Optional[str], status: Optional[str]):
    """List incidents with filters."""
```

**Register in main.py**:
```python
app.include_router(drift_incidents.router, prefix="/api/v1/drift-incidents", tags=["drift-incidents"])
```

**Acceptance Criteria**:
- [ ] All CRUD endpoints working
- [ ] Plan gating enforced (Pro+ for create/update)
- [ ] Proper error handling for invalid transitions

---

#### Step 2.5: Update Frontend API Client

**File to modify**: `n8n-ops-ui/src/lib/api-client.ts`

**New methods**:
```typescript
// Drift Incidents
async createDriftIncident(data: DriftIncidentCreate): Promise<DriftIncident>
async getDriftIncident(incidentId: string): Promise<DriftIncident>
async getActiveIncident(environmentId: string): Promise<DriftIncident | null>
async acknowledgeIncident(incidentId: string, reason: string): Promise<DriftIncident>
async updateIncidentStatus(incidentId: string, status: string): Promise<DriftIncident>
async listDriftIncidents(filters?: DriftIncidentFilters): Promise<DriftIncident[]>
```

**Acceptance Criteria**:
- [ ] All API methods typed and working
- [ ] Error handling for plan-gated operations

---

#### Step 2.6: Create Drift Incident Workspace Page

**New file**: `n8n-ops-ui/src/pages/DriftIncidentPage.tsx`

**Layout**:
```
┌─────────────────────────────────────────────────────────────────┐
│  Drift Incident: [Environment Name]           Status: [Badge]   │
│  Detected: [timestamp]    Owner: [user]       Expires: [time]   │
├─────────────────────────────────────────────────────────────────┤
│  TABS: Overview | Affected Workflows | Diff View | Timeline     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [Tab Content Area]                                             │
│                                                                  │
│  Overview Tab:                                                   │
│  - Incident summary                                             │
│  - Reason/ticket link (if acknowledged)                         │
│  - Resolution path selection (Phase 4)                          │
│                                                                  │
│  Affected Workflows Tab:                                        │
│  - List of workflows with drift                                 │
│  - Drift type per workflow (added/removed/modified)             │
│  - Click to see diff                                            │
│                                                                  │
│  Diff View Tab (Pro-limited, full on Agency+):                  │
│  - Side-by-side diff visualization                              │
│  - Uses existing WorkflowDiffDialog components                  │
│                                                                  │
│  Timeline Tab:                                                  │
│  - Incident lifecycle events                                    │
│  - Status changes with timestamps                               │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  Actions: [Acknowledge] [Update Status] [Choose Resolution]     │
└─────────────────────────────────────────────────────────────────┘
```

**Acceptance Criteria**:
- [ ] Page renders incident details
- [ ] Tabs work correctly
- [ ] Actions trigger appropriate API calls
- [ ] Plan-gated features show upgrade prompts

---

#### Step 2.7: Add Route and Navigation

**File to modify**: `n8n-ops-ui/src/App.tsx`

**Add route**:
```typescript
<Route path="/drift-incidents/:incidentId" element={<DriftIncidentPage />} />
```

**File to modify**: `n8n-ops-ui/src/pages/EnvironmentDetailPage.tsx`

**Update "View Drift" CTA**:
- If active incident exists: Navigate to `/drift-incidents/{incidentId}`
- If no incident (Pro+): Show "Create Incident" button
- If no incident (Free): Show manual remediation guidance

**Acceptance Criteria**:
- [ ] Route registered
- [ ] Navigation from environment detail works
- [ ] Plan-appropriate CTAs shown

---

#### Step 2.8: Update Environment Detail with Incident Status

**File to modify**: `n8n-ops-ui/src/pages/EnvironmentDetailPage.tsx`

**Changes**:
- Update drift banner to show incident status if active
- Status badge: "Drift Incident Active" (orange)
- CTA changes to "View Incident" when incident exists
- For Free tier: "Upgrade to Manage Drift Incidents"

**Acceptance Criteria**:
- [ ] Banner reflects incident state
- [ ] Plan-gated upgrade prompts work

---

### Phase 2 Exit Criteria

- [ ] Drift incidents can be created for environments (Pro+)
- [ ] Full lifecycle management works (detect -> acknowledge -> close)
- [ ] Dedicated incident workspace page exists
- [ ] Environment pages link to incident workspace
- [ ] Plan gating enforced on incident features

---

### Phase 3: De-splash Drift From UI

**Objective**: Remove drift logic from unrelated pages; establish single canonical drift workflow.

#### Step 3.1: Audit Existing Drift UI

**Files to audit**:
- `EnvironmentsPage.tsx` - Keep: status badge only
- `EnvironmentDetailPage.tsx` - Keep: banner + "View Drift" CTA
- `WorkflowDetailPage.tsx` - Replace: drift actions with link to incident
- `DeploymentsPage.tsx` - Replace: drift warnings with incident link
- `SnapshotsPage.tsx` - Remove: any drift-related warnings
- `RestorePage.tsx` - Remove: drift considerations (handled by incident)

**Acceptance Criteria**:
- [ ] Complete audit documented
- [ ] Each page's target state defined

---

#### Step 3.2: Simplify EnvironmentsPage Drift Display

**File to modify**: `n8n-ops-ui/src/pages/EnvironmentsPage.tsx`

**Target state**:
- Drift column shows ONLY: status badge
- No action buttons in this column
- Badge links to environment detail (not directly to incident)

**Remove**:
- Any "Sync Now" or "Fix Drift" buttons from list view
- Inline drift warnings or popovers

**Acceptance Criteria**:
- [ ] Drift column is status-only
- [ ] No drift actions in environment list

---

#### Step 3.3: Simplify WorkflowDetailPage Drift Display

**File to modify**: `n8n-ops-ui/src/pages/WorkflowDetailPage.tsx`

**Target state**:
- Show drift status indicator (in sync / drift detected)
- If drift: "This workflow has drift. View in Environment Drift Incident"
- Link to incident workspace, NOT inline diff or actions

**Remove**:
- Inline diff viewer (move to incident workspace)
- "Sync" or "Resolve Drift" buttons
- Per-workflow drift resolution actions

**Acceptance Criteria**:
- [ ] Workflow page shows status only
- [ ] Links to incident workspace for actions
- [ ] No duplicate diff views

---

#### Step 3.4: Simplify DeploymentsPage Drift Display

**File to modify**: `n8n-ops-ui/src/pages/DeploymentsPage.tsx`

**Target state**:
- If deployment blocked by drift: "Blocked: Drift Incident Active"
- Link to incident workspace to resolve
- No inline drift resolution

**Remove**:
- Drift-related action buttons
- Inline drift warnings with action CTAs

**Acceptance Criteria**:
- [ ] Deployment page shows drift as blocker status
- [ ] Resolution happens in incident workspace

---

#### Step 3.5: Update Promotion Flow Drift Handling

**Files to modify**:
- `n8n-ops-ui/src/pages/NewDeploymentPage.tsx`
- `n8n-ops-ui/src/components/promotion/` components

**Target state**:
- Pre-promotion drift check shows: "Drift detected. Resolve in incident workspace before promoting."
- Link to incident workspace
- Block promotion (don't offer inline resolution)

**Remove**:
- Inline "proceed anyway" options
- Promotion-embedded drift resolution

**Acceptance Criteria**:
- [ ] Promotion flow defers to incident workspace
- [ ] Clean separation of concerns

---

#### Step 3.6: Clean Up Sync/Backup/Restore Pages

**Files to modify**:
- `SnapshotsPage.tsx`
- `RestorePage.tsx`

**Target state**:
- These pages handle snapshots/restore, NOT drift
- If drift exists, show info banner: "Note: This environment has drift. Manage in Drift Incident."
- Don't block restore based on drift (incident handles that)

**Acceptance Criteria**:
- [ ] Snapshot/restore pages don't have drift logic
- [ ] Clear separation from drift incident workflow

---

### Phase 3 Exit Criteria

- [ ] Drift UX exists ONLY in:
  - Environment list: status badge
  - Environment detail: banner + CTA
  - Drift Incident workspace: full management
- [ ] No duplicate diff views
- [ ] No drift actions outside incident workspace
- [ ] All pages have consistent drift indicators

---

### Phase 4: Reconciliation Execution + Orphan Prevention

**Objective**: Implement resolution paths and prevent orphaned hotfixes.

#### Step 4.1: Create drift_reconciliation_artifacts Table

**New migration**:

```sql
CREATE TABLE drift_reconciliation_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID NOT NULL REFERENCES drift_incidents(id),

    type VARCHAR(20) NOT NULL,  -- 'promote', 'revert', 'replace'
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'pending', 'in_progress', 'success', 'failed'

    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE,

    -- External references (hidden from UI, but tracked)
    external_refs JSONB DEFAULT '{}',
    -- { commit_sha, pr_url, deployment_run_id, etc. }

    error_message TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_reconciliation_artifacts_incident ON drift_reconciliation_artifacts(incident_id);
```

**Acceptance Criteria**:
- [ ] Table created
- [ ] Supports all resolution types
- [ ] Tracks external references

---

#### Step 4.2: Create Reconciliation Artifact Schema

**File to modify**: `n8n-ops-backend/app/schemas/drift_incidents.py`

**Add schemas**:
```python
class ReconciliationType(str, Enum):
    promote = "promote"  # Push runtime to Git
    revert = "revert"    # Deploy Git state to runtime
    replace = "replace"  # Different fix supersedes hotfix

class ReconciliationStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    success = "success"
    failed = "failed"

class ReconciliationArtifactCreate(BaseModel):
    incident_id: str
    type: ReconciliationType

class ReconciliationArtifactResponse(BaseModel):
    id: str
    incident_id: str
    type: ReconciliationType
    status: ReconciliationStatus
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_message: Optional[str]
```

**Acceptance Criteria**:
- [ ] All types and statuses defined
- [ ] Create/Response schemas complete

---

#### Step 4.3: Implement Reconciliation Service

**New file**: `n8n-ops-backend/app/services/reconciliation_service.py`

**Key methods**:
```python
class ReconciliationService:
    async def start_reconciliation(
        self,
        incident_id: str,
        type: ReconciliationType
    ) -> ReconciliationArtifact:
        """Start reconciliation process."""

    async def execute_promote(self, artifact_id: str) -> ReconciliationArtifact:
        """
        Promote runtime state to Git.
        - Create branch
        - Commit workflow changes
        - Create PR (backend-only, no UI)
        - Auto-merge if configured
        - Record outcome
        """

    async def execute_revert(self, artifact_id: str) -> ReconciliationArtifact:
        """
        Revert runtime to Git state.
        - Deploy Git workflows to n8n
        - Verify deployment
        - Record outcome
        """

    async def execute_replace(
        self,
        artifact_id: str,
        deployment_id: str
    ) -> ReconciliationArtifact:
        """
        Link to deployment that replaces drifted state.
        - Record deployment reference
        - Verify drift resolved
        """

    async def verify_drift_resolved(self, incident_id: str) -> bool:
        """Check if drift is now zero."""
```

**Integration points**:
- `github_service.py` - For promote (commit/PR)
- `n8n_service.py` - For revert (deploy workflows)
- `deployment_service.py` - For replace (link deployment)

**Acceptance Criteria**:
- [ ] All three resolution types implemented
- [ ] External refs tracked (commit SHA, PR URL, deployment ID)
- [ ] Proper error handling and status updates

---

#### Step 4.4: Add Reconciliation API Endpoints

**File to modify**: `n8n-ops-backend/app/api/endpoints/drift_incidents.py`

**New endpoints**:
```python
@router.post("/{incident_id}/reconciliation")
async def start_reconciliation(incident_id: str, data: ReconciliationRequest):
    """Start reconciliation process."""

@router.get("/{incident_id}/reconciliation")
async def get_reconciliation_artifacts(incident_id: str):
    """Get reconciliation artifacts for incident."""

@router.post("/{incident_id}/reconciliation/{artifact_id}/execute")
async def execute_reconciliation(incident_id: str, artifact_id: str):
    """Execute pending reconciliation."""
```

**Acceptance Criteria**:
- [ ] Endpoints working
- [ ] Plan gating (Agency+ for full execution)

---

#### Step 4.5: Update Incident Workspace with Resolution UI

**File to modify**: `n8n-ops-ui/src/pages/DriftIncidentPage.tsx`

**Add to Overview tab**:
```
Resolution Section:
┌─────────────────────────────────────────────────────────────────┐
│  Choose Resolution Path:                                        │
│                                                                  │
│  [Promote to Git]  [Revert to Git]  [Link Deployment]          │
│   Push runtime      Deploy Git       Different fix             │
│   changes to Git    state to n8n     supersedes hotfix         │
│                                                                  │
│  Active Reconciliation:                                         │
│  Type: Promote | Status: In Progress | Started: [timestamp]    │
│                                                                  │
│  History:                                                       │
│  - Promote attempt failed (error message)                       │
│  - Revert attempt succeeded                                     │
└─────────────────────────────────────────────────────────────────┘
```

**Acceptance Criteria**:
- [ ] Resolution path selection works
- [ ] Shows reconciliation status
- [ ] Displays reconciliation history

---

#### Step 4.6: Enforce Incident Closure Rules

**File to modify**: `n8n-ops-backend/app/services/drift_incident_service.py`

**Closure validation**:
```python
async def close_incident(self, incident_id: str) -> DriftIncident:
    incident = await self.get_incident(incident_id)

    # Rule 1: Must have successful reconciliation artifact
    artifacts = await self.get_reconciliation_artifacts(incident_id)
    successful = [a for a in artifacts if a.status == 'success']
    if not successful:
        raise ValidationError("Cannot close incident without successful reconciliation")

    # Rule 2: Drift must be resolved (diff is zero)
    drift_resolved = await self.reconciliation_service.verify_drift_resolved(incident_id)
    if not drift_resolved:
        raise ValidationError("Cannot close incident: drift still detected")

    # Close incident
    return await self._update_status(incident_id, 'closed')
```

**Acceptance Criteria**:
- [ ] Cannot close without resolution artifact
- [ ] Cannot close if drift still exists
- [ ] Clear error messages for closure failures

---

#### Step 4.7: Implement Orphan Prevention

**Principle**: No drifted change can vanish without explicit recorded decision.

**Implementation**:
1. Drift detected -> Incident required (paid) or override recorded (free)
2. Incident cannot close without resolution
3. Override decisions are logged and visible
4. All resolution paths are recorded

**File to modify**: `n8n-ops-backend/app/services/drift_detection_service.py`

**Add override tracking for free tier**:
```python
async def record_drift_override(
    self,
    environment_id: str,
    workflow_id: str,
    override_type: str,  # 'ignore', 'manual_resolve'
    reason: str,
    user_id: str
) -> DriftOverrideRecord:
    """Record explicit decision to ignore/manually resolve drift."""
```

**New table** (optional, or use audit log):
```sql
CREATE TABLE drift_overrides (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    environment_id UUID NOT NULL,
    workflow_id TEXT,
    override_type VARCHAR(20),
    reason TEXT,
    user_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Acceptance Criteria**:
- [ ] All drift decisions recorded
- [ ] No silent drift disappearance
- [ ] Audit trail for overrides

---

### Phase 4 Exit Criteria

- [ ] All three resolution paths work (promote/revert/replace)
- [ ] Reconciliation artifacts tracked with external refs
- [ ] Incident closure enforced (resolution + zero drift)
- [ ] No orphaned hotfixes (all decisions recorded)
- [ ] Free tier override decisions logged

---

### Phase 5: TTL/SLA + Enforcement

**Objective**: Add time-based governance with predictable enforcement.

#### Step 5.1: Add TTL/SLA Fields

**Already in Phase 2 migration**, but now activate:
- `expires_at` - When incident must be resolved
- `severity` - Escalation level

**New configuration table**:
```sql
CREATE TABLE drift_policies (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,

    -- TTL settings by severity
    default_ttl_hours INTEGER DEFAULT 72,
    critical_ttl_hours INTEGER DEFAULT 24,

    -- Enforcement settings
    block_deployments_on_expired BOOLEAN DEFAULT false,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Acceptance Criteria**:
- [ ] TTL/SLA fields populated on incident creation
- [ ] Policy table exists for tenant configuration

---

#### Step 5.2: Implement TTL Calculation Service

**File to modify**: `n8n-ops-backend/app/services/drift_incident_service.py`

**Add methods**:
```python
async def calculate_expires_at(self, incident: DriftIncident, policy: DriftPolicy) -> datetime:
    """Calculate expiration based on severity and policy."""

async def check_expired_incidents(self, tenant_id: str) -> List[DriftIncident]:
    """Get all expired incidents for tenant."""

async def extend_ttl(self, incident_id: str, hours: int, reason: str, user_id: str) -> DriftIncident:
    """Extend TTL (role-based on Enterprise)."""
```

**Acceptance Criteria**:
- [ ] TTL calculated on incident creation
- [ ] Expiration checking works
- [ ] TTL extension logged

---

#### Step 5.3: Implement Deployment Blocking

**File to modify**: `n8n-ops-backend/app/services/deployment_service.py`

**Add enforcement check**:
```python
async def check_deployment_blockers(self, environment_id: str) -> List[DeploymentBlocker]:
    """Check for conditions that block deployment."""
    blockers = []

    # Check for expired drift incidents (Agency+)
    if self.plan_allows('drift_ttl_sla'):
        expired_incidents = await self.drift_incident_service.get_expired_incidents(environment_id)
        if expired_incidents:
            blockers.append(DeploymentBlocker(
                type='expired_drift_incident',
                message=f'Drift incident expired: {expired_incidents[0].id}',
                incident_id=expired_incidents[0].id
            ))

    return blockers
```

**Acceptance Criteria**:
- [ ] Deployments blocked when incident expired
- [ ] Clear error message with incident link
- [ ] Only enforced on Agency+

---

#### Step 5.4: Add Drift Dashboard

**New file**: `n8n-ops-ui/src/pages/DriftDashboardPage.tsx`

**Layout**:
```
┌─────────────────────────────────────────────────────────────────┐
│  Drift Dashboard                                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Summary Cards:                                                 │
│  [Active Incidents: 3] [Expired: 1] [Resolved (30d): 12]       │
│                                                                  │
│  Expired Incidents (Action Required):                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Environment    │ Detected   │ Expired    │ Action      │   │
│  │ production     │ 3 days ago │ 1 day ago  │ [View]      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Active Incidents:                                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Environment │ Status      │ Expires In │ Owner │ Action │   │
│  │ staging     │ Acknowledged│ 2 days     │ john  │ [View] │   │
│  │ dev         │ Detected    │ 3 days     │ -     │ [View] │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Stats (optional):                                              │
│  - Average time to resolve: 18 hours                            │
│  - Most common resolution: Revert (60%)                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Acceptance Criteria**:
- [ ] Dashboard shows all incidents
- [ ] Expired incidents highlighted
- [ ] Links to incident workspace

---

#### Step 5.5: Add Navigation and Feature Gate

**Files to modify**:
- `n8n-ops-ui/src/App.tsx` - Add route
- `n8n-ops-ui/src/components/AppLayout.tsx` - Add nav item (Agency+)

**Acceptance Criteria**:
- [ ] Dashboard accessible from nav (Agency+)
- [ ] Route works
- [ ] Lower tiers see upgrade prompt

---

### Phase 5 Exit Criteria

- [ ] TTL/SLA calculated and tracked
- [ ] Expired incidents block deployments (Agency+)
- [ ] Drift dashboard shows incident overview
- [ ] TTL extension works with audit trail

---

### Phase 6: Enterprise Policies & Approvals

**Objective**: Compliance-grade controls for large organizations.

#### Step 6.1: Approval Workflows

**New table**:
```sql
CREATE TABLE drift_approvals (
    id UUID PRIMARY KEY,
    incident_id UUID NOT NULL REFERENCES drift_incidents(id),
    approval_type VARCHAR(20),  -- 'acknowledge', 'extend_ttl', 'close'
    requested_by UUID NOT NULL,
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    approved_by UUID,
    approved_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'approved', 'rejected'
    notes TEXT
);
```

**Implementation**:
- Acknowledge requires approval on Enterprise
- TTL extension requires approval on Enterprise
- Configurable approval roles per action

---

#### Step 6.2: Role-Based TTL Extensions

**Policy configuration**:
```python
class EnterpriseDriftPolicy:
    ttl_extension_roles: List[str]  # Roles that can extend TTL
    acknowledge_roles: List[str]    # Roles that can acknowledge
    close_roles: List[str]          # Roles that can close
    max_ttl_extension_hours: int    # Maximum extension allowed
```

---

#### Step 6.3: Org-Wide Policy Templates

**New table**:
```sql
CREATE TABLE drift_policy_templates (
    id UUID PRIMARY KEY,
    name VARCHAR(100),
    description TEXT,
    policy_config JSONB,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Predefined templates**:
- "Strict" - 24h TTL, approval required, deployment blocking
- "Standard" - 72h TTL, no approval, deployment blocking
- "Relaxed" - 1 week TTL, no approval, no blocking

---

#### Step 6.4: Compliance Reporting

**New endpoint**: `GET /api/v1/reports/drift-compliance`

**Report content**:
- Incidents by status over time
- Average resolution time
- Override decisions audit
- SLA compliance percentage
- Export to CSV/PDF

---

### Phase 6 Exit Criteria

- [ ] Approval workflows implemented
- [ ] Role-based controls work
- [ ] Policy templates available
- [ ] Compliance reports exportable
- [ ] Long retention configured

---

## Testing Strategy

### Unit Tests (Per Phase)

| Phase | Test Files |
|-------|------------|
| 1 | `test_drift_detection_service.py` |
| 2 | `test_drift_incident_service.py` |
| 3 | (UI tests for component simplification) |
| 4 | `test_reconciliation_service.py` |
| 5 | `test_drift_ttl_enforcement.py` |
| 6 | `test_drift_approvals.py` |

### Integration Tests

- Drift detection end-to-end
- Incident lifecycle flow
- Reconciliation execution
- Deployment blocking

### Manual Testing Checklist

- [ ] Free tier sees drift but cannot create incidents
- [ ] Pro tier can create and manage incidents
- [ ] Agency tier has TTL/SLA enforcement
- [ ] Enterprise has approvals and policies

---

## File Change Summary

### New Files (Backend)

| File | Phase |
|------|-------|
| `app/services/drift_detection_service.py` | 1 |
| `app/schemas/drift_incidents.py` | 2 |
| `app/services/drift_incident_service.py` | 2 |
| `app/api/endpoints/drift_incidents.py` | 2 |
| `app/services/reconciliation_service.py` | 4 |
| `migrations/xxx_drift_incidents.sql` | 2 |
| `migrations/xxx_reconciliation_artifacts.sql` | 4 |
| `migrations/xxx_drift_policies.sql` | 5 |

### New Files (Frontend)

| File | Phase |
|------|-------|
| `src/pages/DriftIncidentPage.tsx` | 2 |
| `src/pages/DriftDashboardPage.tsx` | 5 |
| `src/types/drift.ts` | 2 |

### Modified Files (Backend)

| File | Phase | Changes |
|------|-------|---------|
| `app/schemas/environments.py` | 1 | Add drift fields |
| `app/services/database.py` | 1-4 | Add drift methods |
| `app/api/endpoints/environments.py` | 1 | Add drift endpoints |
| `app/core/feature_gates.py` | 1 | Add drift features |
| `app/main.py` | 2 | Register drift router |
| `app/services/deployment_service.py` | 5 | Add blocking logic |

### Modified Files (Frontend)

| File | Phase | Changes |
|------|-------|---------|
| `src/lib/api-client.ts` | 1-4 | Add drift API methods |
| `src/pages/EnvironmentsPage.tsx` | 1, 3 | Add badge, simplify |
| `src/pages/EnvironmentDetailPage.tsx` | 1, 3 | Add banner, simplify |
| `src/pages/WorkflowDetailPage.tsx` | 3 | Simplify drift UI |
| `src/pages/DeploymentsPage.tsx` | 3 | Simplify drift UI |
| `src/App.tsx` | 2, 5 | Add routes |
| `src/components/AppLayout.tsx` | 5 | Add nav items |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing sync functionality | Preserve existing sync_status_service; drift is additive |
| Plan gating inconsistencies | Gate at API boundary, not just UI |
| Migration failures | Test migrations on staging DB first |
| UI complexity | Phase 3 simplification reduces cognitive load |
| Performance (frequent drift checks) | Cache drift status; refresh on-demand or scheduled |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Drift incidents closed within SLA | > 80% |
| Reduction in "unknown drift" | > 90% |
| Override decisions recorded | 100% |
| User upgrade conversion (drift -> incident) | Track |

---

## Implementation Order

Execute phases sequentially. Each phase has clear exit criteria that must be met before proceeding.

```
Phase 0: Analysis ✓ (this document)
    ↓
Phase 1: Detection + Surfacing (ALL plans)
    ↓
Phase 2: Incident Object + Workspace (Pro+)
    ↓
Phase 3: UI De-splash (refactor)
    ↓
Phase 4: Reconciliation + Orphan Prevention (Agency+)
    ↓
Phase 5: TTL/SLA + Enforcement (Agency+)
    ↓
Phase 6: Enterprise Policies (Enterprise)
```

---

## Design Decisions

The following decisions establish **recommended defaults**, **rationale**, and **plan-based behavior**. These align with drift as a first-class incident, Git as source of truth, and safe governance without blocking recovery.

---

## 1. Drift Detection: Scheduled vs On-Demand

### Decision
**Hybrid approach (recommended).**

### Behavior
- **Scheduled detection**
  - Free: daily
  - Pro+: hourly (configurable per tenant on higher tiers)
- **On-demand detection**
  - Always available
  - Triggered when:
    - User opens Environment Details
    - User opens Drift Incident workspace
    - User clicks “Re-check drift”

### Rationale
- Scheduled detection catches client-side edits quickly (common for agencies).
- On-demand detection prevents stale decisions during incident handling.
- Hybrid avoids over-polling while maintaining correctness.

---

## 2. Free Tier Override Retention

### Decision
**7 days of override history + current override state retained indefinitely.**

### Data retained (Free tier)
- environment_id
- override_state (ignored / acknowledged)
- last_set_at
- actor
- short reason

### Data purged after 7 days
- Detailed history
- Change metadata

### Rationale
- Prevents users from being stranded
- Creates upgrade pressure without being punitive
- Controls storage and audit expectations on Free

---

## 3. Auto-Create Drift Incidents

### Decision
**Manual by default; auto-create only for Agency+.**

### Plan behavior
- **Free**: no incidents
- **Pro**: manual “Create Drift Incident”
- **Agency+**:
  - Policy option: auto-create on drift detection
  - Default: off
  - Often enabled for production environments
- **Enterprise**: policy-driven (org defaults)

### Rationale
- Prevents incident fatigue on Pro
- Agencies want automation once governance is accepted
- Keeps noise low while preserving safety

---

## 4. PR Visibility in WorkflowOps UI

### Decision
**PRs are metadata, not first-class UI.**

### UI behavior
- Show resolution status:
  - `Promoted to Git (Merged)`
  - `Promote failed`
- Optional **“Technical details”** (collapsed):
  - Commit SHA
  - Optional PR URL link (read-only)

### Explicitly not supported
- Browsing PRs
- Managing PRs
- Commenting or merging from WorkflowOps

### Rationale
- Keeps non-dev users safe
- Preserves auditability
- Avoids turning WorkflowOps into a Git client

---

## 5. Deployment Blocking Scope

### Decision
**Block deployments only to the affected environment.**

### Behavior
- If drift incident is **expired**:
  - Block deployments **to that environment only**
- Dev/staging remain deployable when prod is drifted

### Enterprise optional policy
- “Global freeze when prod drift expired” (off by default)

### Rationale
- Prevents deadlocks
- Matches real operational risk
- Avoids punishing unrelated workstreams

---

## 6. Drift Dashboard Location

### Decision
**Two surfaces: operational + administrative.**

### Locations
1. **Main navigation (Agency+)**
   - Section: **Incidents** (or Operations)
   - Shows:
     - Active drift incidents
     - Status, TTL, ownership
2. **Admin section (Enterprise / tenant admins)**
   - Drift policies
   - TTL defaults
   - Auto-create rules
   - Retention settings

### Rationale
- Incidents are operational, not just admin concerns
- Policies belong in admin
- Keeps navigation intuitive

---

## System Defaults (Recommended)

| Setting | Default |
|---|---|
| Detection schedule | Hourly (paid), Daily (free) |
| On-demand detection | Always enabled |
| Free override retention | 7 days history |
| Auto-create incidents | Off (Pro), Optional (Agency+) |
| PR visibility | Metadata only, collapsed |
| Deployment blocking | Environment-scoped |
| Dashboard | “Incidents” + Admin policies |

---

## Anchor Principles

- Drift detection is **always on**
- Drift management is **plan-gated**
- Incidents are **operational**
- Governance yields to recovery, then returns
- Nothing disappears without an explicit decision
