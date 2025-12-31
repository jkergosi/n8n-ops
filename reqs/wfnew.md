# Workflows Page Refactor - Implementation Guide

## Overview

This document provides detailed implementation instructions for refactoring the Workflows page to be governance-first and environment-aware, based on the requirements in `wf.md`.

---

## Design Decisions (Confirmed)

| Question | Decision | Rationale |
|----------|----------|-----------|
| **Soft vs Hard Delete** | Dev defaults to soft delete (archive); hard delete admin-only with explicit "Permanently delete" confirmation | Preserves auditability and reversibility without blocking work |
| **Environment Type** | Standardize as enum (`dev` \| `staging` \| `production`); allow free-form labels/aliases separately | Fuzzy matching is brittle; env type must be deterministic for safety rules |
| **Agency+** | Refers to both Agency AND Enterprise tiers | "Agency+" = any plan with Drift Incident Management |
| **Enterprise Overrides** | Defer to later phase; design interfaces now but don't implement | Too much complexity; core workflows must stabilize first |
| **Upload Button** | Rename to "Backup to GitHub"; route to Deployments in staging/prod; direct backup only in dev | Mismatched naming destroys trust; ungoverned uploads bypass governance |
| **Drift Incidents** | Flexible, policy-driven: Free/Pro=optional, Agency+=required by policy default, Enterprise=can auto-create | Strict enforcement too early causes friction; scales with maturity |

---

## Current State Analysis

### What "Edit" Does Today (`WorkflowsPage.tsx:163-221`)
- Opens a dialog to edit **name, active status, and tags**
- Calls `api.updateWorkflow()` which updates **directly in N8N**
- **Creates drift** - edits N8N without touching Git
- No warning about drift implications

### What "Delete" Does Today (`WorkflowsPage.tsx:223-237`)
- Calls `api.deleteWorkflow()` which **hard deletes from N8N**
- Removes from database cache
- Does NOT delete from Git
- **Creates drift** if workflow was in Git

### What "Upload Workflow" Does Today (`WorkflowsPage.tsx:416-487`)
- **Misleading name** - Actually backs up workflows TO GitHub (not upload to N8N)
- Calls `api.syncWorkflowsToGithub()`
- Dialog correctly says "Backup Workflows to GitHub"
- Recommendation: Rename button to match actual behavior

### What "Refresh from N8N" Does Today
- Calls `api.getWorkflows(selectedEnvironment, true)` with `force_refresh=true`
- Read-only operation, safe
- No changes needed

### Current Actions Column (`WorkflowsPage.tsx:752-780`)
```tsx
<Button onClick={() => openInN8N(workflow.id)}>n8n</Button>
<Button onClick={() => handleEditClick(workflow)}>Edit</Button>
<Button onClick={() => handleDeleteClick(workflow)}>Delete</Button>
```

---

## Gap Analysis: Requirements vs. Current State

| Requirement | Current State | Gap |
|-------------|---------------|-----|
| Actions dropdown menu | Per-row Edit/Delete buttons | Need to implement dropdown |
| Environment-type gating | No environment-type awareness | Need policy system |
| Plan-based gating | Features exist but not applied | Need to apply to actions |
| Direct edit warning modal | No drift warning | Need confirmation dialog |
| "Managed By" indicator | Not shown | Need new column/badge |
| Create Deployment action | Not available | Need to add |
| Drift Incident integration | Incidents exist, not linked | Need to add action |
| Backend policy enforcement | No server-side checks | Need policy endpoint |

---

## Existing Infrastructure to Leverage

### 1. Features System (`n8n-ops-ui/src/lib/features.tsx`)
```typescript
// Plan tiers with features
PLAN_FEATURES: { free, pro, agency, enterprise }

// Key features for this refactor:
- drift_incidents: boolean (agency+)
- workflow_ci_cd: boolean (pro+)
- deployments: boolean (pro+)

// Usage
const { canUseFeature, planName } = useFeatures();
if (canUseFeature('drift_incidents')) { ... }
```

### 2. Permissions System (`n8n-ops-ui/src/lib/permissions.ts`)
```typescript
type Role = 'user' | 'admin' | 'agency' | 'superuser';
// Currently role-based only, not environment-type aware
```

### 3. Environment Type (`n8n-ops-ui/src/types/index.ts:88-111`)
```typescript
// CURRENT (free-form):
interface Environment {
  type?: string;  // Free-form: 'dev', 'staging', 'production', 'qa', etc.
  driftStatus?: 'IN_SYNC' | 'DRIFT_DETECTED' | 'DRIFT_INCIDENT_ACTIVE';
  // ...
}

// REQUIRED CHANGE: Standardize to enum + display label
interface Environment {
  environmentClass: 'dev' | 'staging' | 'production';  // NEW: Deterministic for policy
  displayLabel?: string;  // Optional: Free-form for UI display (e.g., "QA-US-West")
  driftStatus?: 'IN_SYNC' | 'DRIFT_DETECTED' | 'DRIFT_INCIDENT_ACTIVE';
  // ...
}
```

### 4. Drift Incidents (`n8n-ops-ui/src/types/index.ts:416-467`)
```typescript
type DriftIncidentStatus = 'detected' | 'acknowledged' | 'stabilized' | 'reconciled' | 'closed';
interface DriftIncident { ... }
// Pages: IncidentsPage.tsx, IncidentDetailPage.tsx
```

### 5. Deployments System
- Pages: `DeploymentsPage.tsx`, `DeploymentDetailPage.tsx`
- API: `api.initiatePromotion()`, `api.executePromotion()`
- Types: `Deployment`, `DeploymentStatus`

---

## Implementation Plan

### Phase 0: Schema Changes (Prerequisites)

**These changes must be implemented first before UI work.**

#### 0.1 Database Migration: Environment Class
**File:** `n8n-ops-backend/alembic/versions/add_environment_class.py`

**CRITICAL:** Use the environment `name` field (user-provided display name), NOT `n8n_type` which is a provider identifier.

```python
"""Add environment_class to environments table

Revision ID: xxx

IMPORTANT: environment_class is the ONLY source of truth for policy enforcement.
After this migration, NEVER infer environment class at runtime.
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add environment_class enum column
    op.add_column('environments', sa.Column(
        'environment_class',
        sa.Enum('dev', 'staging', 'production', name='environment_class_enum'),
        nullable=False,
        server_default='dev'
    ))

    # Migrate existing data based on environment NAME field (not n8n_type!)
    # n8n_type is a provider type, not an environment classification
    op.execute("""
        UPDATE environments
        SET environment_class = CASE
            WHEN LOWER(name) LIKE '%prod%' OR LOWER(name) = 'live' THEN 'production'
            WHEN LOWER(name) LIKE '%stag%' OR LOWER(name) = 'uat' OR LOWER(name) = 'qa' THEN 'staging'
            ELSE 'dev'
        END
    """)

    # NOTE: After migration, users should verify environment_class is correct
    # via admin UI. The inferred value may need manual correction.

def downgrade():
    op.drop_column('environments', 'environment_class')
    op.execute("DROP TYPE IF EXISTS environment_class_enum")
```

**Post-Migration UI Requirement:** Add environment class selector to EnvironmentSetupPage so users can explicitly set/correct the value. This is the ONLY place classification should be set.

#### 0.2 Database Migration: Workflow Archive
**File:** `n8n-ops-backend/alembic/versions/add_workflow_archive.py`

```python
"""Add is_archived to workflows table

Revision ID: xxx
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('workflows', sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('workflows', sa.Column('archived_at', sa.DateTime(), nullable=True))
    op.add_column('workflows', sa.Column('archived_by', sa.String(36), nullable=True))

def downgrade():
    op.drop_column('workflows', 'archived_by')
    op.drop_column('workflows', 'archived_at')
    op.drop_column('workflows', 'is_archived')
```

#### 0.3 Update TypeScript Types
**File:** `n8n-ops-ui/src/types/index.ts`

```typescript
// Add to Environment interface
export type EnvironmentClass = 'dev' | 'staging' | 'production';

export interface Environment {
  // ... existing fields ...
  environmentClass: EnvironmentClass;  // NEW: Required for policy
  displayLabel?: string;               // NEW: Optional display name
}

// Add to Workflow interface
export interface Workflow {
  // ... existing fields ...
  isArchived?: boolean;    // NEW: Soft delete flag
  archivedAt?: string;     // NEW: Archive timestamp
}
```

#### 0.4 Update Backend Schemas
**File:** `n8n-ops-backend/app/schemas/environment.py`

```python
from enum import Enum

class EnvironmentClass(str, Enum):
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"

class EnvironmentBase(BaseModel):
    # ... existing fields ...
    environment_class: EnvironmentClass = EnvironmentClass.DEV
    display_label: Optional[str] = None

class EnvironmentResponse(EnvironmentBase):
    # ... existing fields ...
    environment_class: EnvironmentClass
```

#### 0.5 Add Archive Database Methods
**File:** `n8n-ops-backend/app/services/database.py`

```python
async def archive_workflow(
    self,
    tenant_id: str,
    environment_id: str,
    workflow_id: str,
    archived_by: str = None
) -> Dict[str, Any]:
    """Soft delete a workflow by marking it as archived"""
    result = await self.client.table("workflows").update({
        "is_archived": True,
        "archived_at": datetime.utcnow().isoformat(),
        "archived_by": archived_by
    }).eq("tenant_id", tenant_id).eq("environment_id", environment_id).eq("n8n_workflow_id", workflow_id).execute()
    return result.data[0] if result.data else None

async def unarchive_workflow(
    self,
    tenant_id: str,
    environment_id: str,
    workflow_id: str
) -> Dict[str, Any]:
    """Restore an archived workflow"""
    result = await self.client.table("workflows").update({
        "is_archived": False,
        "archived_at": None,
        "archived_by": None
    }).eq("tenant_id", tenant_id).eq("environment_id", environment_id).eq("n8n_workflow_id", workflow_id).execute()
    return result.data[0] if result.data else None

async def get_workflows(
    self,
    tenant_id: str,
    environment_id: str,
    include_archived: bool = False  # NEW: Filter param
) -> List[Dict[str, Any]]:
    """Get workflows for environment, excluding archived by default"""
    query = self.client.table("workflows").select("*").eq("tenant_id", tenant_id).eq("environment_id", environment_id)
    if not include_archived:
        query = query.eq("is_archived", False)
    result = await query.execute()
    return result.data
```

---

### Phase 1: UI De-clutter (Actions Menu)

#### 1.1 Create Actions Dropdown Component
**File:** `n8n-ops-ui/src/components/workflow/WorkflowActionsMenu.tsx`

```typescript
import { useWorkflowActionPolicy } from '@/hooks/useWorkflowActionPolicy';
import { useFeatures } from '@/lib/features';

interface WorkflowActionsMenuProps {
  workflow: Workflow;
  environment: Environment | null;
  onViewDetails: () => void;
  onEdit: () => void;
  onSoftDelete: () => void;       // Archive workflow
  onHardDelete: () => void;       // Permanently delete (admin-only)
  onOpenInN8N: () => void;
  onCreateDeployment: () => void;
  onViewDriftIncident?: () => void;
  onCreateDriftIncident?: () => void;
}

export function WorkflowActionsMenu({
  workflow,
  environment,
  onViewDetails,
  onEdit,
  onSoftDelete,
  onHardDelete,
  onOpenInN8N,
  onCreateDeployment,
  onViewDriftIncident,
  onCreateDriftIncident,
}: WorkflowActionsMenuProps) {
  const policy = useWorkflowActionPolicy(environment, workflow);
  const { canUseFeature } = useFeatures();

  const hasDrift = workflow.syncStatus === 'local_changes' || workflow.syncStatus === 'conflict';
  const hasActiveIncident = environment?.driftStatus === 'DRIFT_INCIDENT_ACTIVE';

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm">
          Actions <ChevronDown className="h-3 w-3 ml-1" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {/* =============================================
            ALWAYS AVAILABLE
            ============================================= */}
        <DropdownMenuItem onClick={onViewDetails}>
          <Eye className="h-4 w-4 mr-2" />
          View Details
        </DropdownMenuItem>
        <DropdownMenuItem onClick={onOpenInN8N}>
          <ExternalLink className="h-4 w-4 mr-2" />
          Open in n8n
        </DropdownMenuItem>
        <DropdownMenuSeparator />

        {/* =============================================
            GOVERNANCE PATH (Primary)
            ============================================= */}
        <DropdownMenuItem onClick={onCreateDeployment}>
          <Rocket className="h-4 w-4 mr-2" />
          Create Deployment
        </DropdownMenuItem>

        {/* =============================================
            DRIFT INCIDENT PATH
            ============================================= */}
        {policy.canCreateDriftIncident && hasDrift && !hasActiveIncident && (
          <DropdownMenuItem onClick={onCreateDriftIncident}>
            <AlertTriangle className="h-4 w-4 mr-2" />
            Create Drift Incident
            {policy.driftIncidentRequired && (
              <Badge variant="outline" className="ml-2 text-xs">Required</Badge>
            )}
          </DropdownMenuItem>
        )}
        {hasActiveIncident && (
          <DropdownMenuItem onClick={onViewDriftIncident}>
            <AlertCircle className="h-4 w-4 mr-2" />
            View Drift Incident
          </DropdownMenuItem>
        )}

        {/* =============================================
            DIRECT MUTATION (Gated)
            ============================================= */}
        {(policy.canEditDirectly || policy.canSoftDelete || policy.canHardDelete) && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuLabel className="text-xs text-muted-foreground">
              Direct Actions (creates drift)
            </DropdownMenuLabel>
          </>
        )}

        {policy.canEditDirectly && (
          <DropdownMenuItem onClick={onEdit}>
            <Edit className="h-4 w-4 mr-2" />
            Edit Directly
          </DropdownMenuItem>
        )}

        {policy.canSoftDelete && (
          <DropdownMenuItem onClick={onSoftDelete}>
            <Archive className="h-4 w-4 mr-2" />
            Archive Workflow
          </DropdownMenuItem>
        )}

        {policy.canHardDelete && (
          <DropdownMenuItem onClick={onHardDelete} className="text-destructive">
            <Trash2 className="h-4 w-4 mr-2" />
            Permanently Delete
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

#### 1.2 Replace Buttons in WorkflowsPage.tsx
**File:** `n8n-ops-ui/src/pages/WorkflowsPage.tsx`

Replace lines 752-780:
```tsx
// Before:
<div className="flex gap-2">
  <Button size="sm" variant="outline" onClick={() => openInN8N(workflow.id)}>
    <ExternalLink className="h-3 w-3 mr-1" /> n8n
  </Button>
  <Button size="sm" variant="outline" onClick={() => handleEditClick(workflow)}>
    <Edit className="h-3 w-3 mr-1" /> Edit
  </Button>
  <Button size="sm" variant="outline" onClick={() => handleDeleteClick(workflow)}>
    <Trash2 className="h-3 w-3 mr-1" /> Delete
  </Button>
</div>

// After - props MUST match component interface exactly:
<WorkflowActionsMenu
  workflow={workflow}
  environment={currentEnvironment}
  onViewDetails={() => navigate(`/workflows/${workflow.id}`)}
  onEdit={() => handleEditClick(workflow)}
  onSoftDelete={() => handleSoftDelete(workflow)}
  onHardDelete={() => handleHardDeleteClick(workflow)}
  onOpenInN8N={() => openInN8N(workflow.id)}
  onCreateDeployment={() => handleCreateDeployment(workflow)}
  onViewDriftIncident={() => handleViewDriftIncident(workflow)}
  onCreateDriftIncident={() => handleCreateDriftIncident(workflow)}
/>
```

---

### Phase 2: Environment-Based Action Policy

#### 2.1 Create Action Policy Types
**File:** `n8n-ops-ui/src/lib/workflow-action-policy.ts`

```typescript
// Standardized environment class enum (no fuzzy matching)
export type EnvironmentClass = 'dev' | 'staging' | 'production';

export type DeleteMode = 'soft' | 'hard' | 'none';

export interface WorkflowActionPolicy {
  canViewDetails: boolean;
  canOpenInN8N: boolean;
  canCreateDeployment: boolean;
  canEditDirectly: boolean;
  canSoftDelete: boolean;        // Archive/hide workflow
  canHardDelete: boolean;        // Permanently remove (admin-only with confirmation)
  canCreateDriftIncident: boolean;
  driftIncidentRequired: boolean; // Agency+: must create incident to resolve drift
  editRequiresConfirmation: boolean;
  editRequiresAdmin: boolean;
}

// NO fuzzy matching - environment must have explicit environmentClass field
// Migration helper only (for existing data without environmentClass):
export function inferEnvironmentClass(legacyType?: string): EnvironmentClass {
  console.warn('inferEnvironmentClass: Legacy type field used. Migrate to environmentClass.');
  if (!legacyType) return 'dev'; // Safe default
  const normalized = legacyType.toLowerCase();

  if (normalized.includes('prod') || normalized === 'live') return 'production';
  if (normalized.includes('stag') || normalized === 'uat') return 'staging';
  return 'dev';
}

// Default action policy matrix
const DEFAULT_POLICY_MATRIX: Record<EnvironmentClass, WorkflowActionPolicy> = {
  dev: {
    canViewDetails: true,
    canOpenInN8N: true,
    canCreateDeployment: true,
    canEditDirectly: true,
    canSoftDelete: true,          // Default delete = soft (archive)
    canHardDelete: false,         // Hard delete requires explicit admin action
    canCreateDriftIncident: true, // Plan-gated below
    driftIncidentRequired: false, // Plan-gated below
    editRequiresConfirmation: true, // Warn about drift
    editRequiresAdmin: false,
  },
  staging: {
    canViewDetails: true,
    canOpenInN8N: true,
    canCreateDeployment: true,
    canEditDirectly: true,        // Admin-gated below
    canSoftDelete: false,         // Route to deployment
    canHardDelete: false,         // Never in staging
    canCreateDriftIncident: true,
    driftIncidentRequired: false, // Plan-gated below
    editRequiresConfirmation: true,
    editRequiresAdmin: true,      // Admin only
  },
  production: {
    canViewDetails: true,
    canOpenInN8N: true,
    canCreateDeployment: true,
    canEditDirectly: false,       // Never in production
    canSoftDelete: false,         // Never in production
    canHardDelete: false,         // Never in production
    canCreateDriftIncident: true,
    driftIncidentRequired: true,  // Always required in production
    editRequiresConfirmation: false, // N/A
    editRequiresAdmin: false,     // N/A
  },
};

export function getWorkflowActionPolicy(
  environment: Environment | null,
  planName: string,
  userRole: string,
  hasDrift: boolean
): WorkflowActionPolicy {
  // Use environmentClass if available, otherwise infer from legacy type field
  const envClass = environment?.environmentClass ||
    inferEnvironmentClass(environment?.type);
  const basePolicy = { ...DEFAULT_POLICY_MATRIX[envClass] };
  const planTier = planName.toLowerCase();
  const isAgencyPlus = planTier === 'agency' || planTier === 'enterprise';
  const isAdmin = userRole === 'admin' || userRole === 'superuser';

  // =============================================
  // PLAN-BASED RESTRICTIONS
  // =============================================

  // Free tier: No drift incident workflow at all
  if (planTier === 'free') {
    basePolicy.canCreateDriftIncident = false;
    basePolicy.driftIncidentRequired = false;
  }

  // Pro tier: Drift incidents optional (not required)
  if (planTier === 'pro') {
    basePolicy.driftIncidentRequired = false;
  }

  // Agency+: Drift incidents required by default in staging/production
  if (isAgencyPlus) {
    if (envClass === 'staging') {
      basePolicy.canEditDirectly = false; // Even stricter for agency+
      basePolicy.driftIncidentRequired = true;
    }
    // Production already has driftIncidentRequired = true
  }

  // Enterprise: Placeholder for org policy overrides (DEFERRED)
  // TODO: Interface design only - implementation in future phase
  // if (planTier === 'enterprise' && orgPolicy) {
  //   applyOrgPolicyOverrides(basePolicy, orgPolicy);
  // }

  // =============================================
  // ROLE-BASED RESTRICTIONS
  // =============================================

  // Admin-gated actions
  if (basePolicy.editRequiresAdmin && !isAdmin) {
    basePolicy.canEditDirectly = false;
  }

  // Hard delete: Admin-only in dev, never elsewhere
  if (envClass === 'dev' && isAdmin) {
    basePolicy.canHardDelete = true; // Unlocks "Permanently delete" option
  }

  // =============================================
  // DRIFT STATE RESTRICTIONS
  // =============================================

  // Drift incident only if drift exists
  if (!hasDrift) {
    basePolicy.canCreateDriftIncident = false;
    basePolicy.driftIncidentRequired = false;
  }

  return basePolicy;
}
```

#### 2.2 Create Policy Hook
**File:** `n8n-ops-ui/src/hooks/useWorkflowActionPolicy.ts`

```typescript
import { useMemo } from 'react';
import { useFeatures } from '@/lib/features';
import { useAuth } from '@/lib/auth';
import { getWorkflowActionPolicy, WorkflowActionPolicy } from '@/lib/workflow-action-policy';
import type { Environment, Workflow } from '@/types';

export function useWorkflowActionPolicy(
  environment: Environment | null,
  workflow?: Workflow
): WorkflowActionPolicy {
  const { planName } = useFeatures();
  const { user } = useAuth();

  return useMemo(() => {
    const hasDrift = workflow?.syncStatus === 'local_changes' ||
                     workflow?.syncStatus === 'conflict';

    return getWorkflowActionPolicy(
      environment,
      planName,
      user?.role || 'user',
      hasDrift
    );
  }, [environment, planName, user?.role, workflow?.syncStatus]);
}
```

---

### Phase 3: Direct Edit Warning Dialog

#### 3.1 Create Drift Warning Dialog
**File:** `n8n-ops-ui/src/components/workflow/DirectEditWarningDialog.tsx`

```typescript
import { useState } from 'react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Checkbox } from '@/components/ui/checkbox';
import { AlertTriangle } from 'lucide-react';

interface DirectEditWarningDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workflowName: string;
  environmentType: string;
  onConfirm: () => void;
}

export function DirectEditWarningDialog({
  open,
  onOpenChange,
  workflowName,
  environmentType,
  onConfirm,
}: DirectEditWarningDialogProps) {
  const [acknowledged, setAcknowledged] = useState(false);

  const handleConfirm = () => {
    if (acknowledged) {
      onConfirm();
      setAcknowledged(false);
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            Direct Edit Warning
          </AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="space-y-4">
              <p>
                You are about to directly edit <strong>{workflowName}</strong> in the{' '}
                <strong>{environmentType}</strong> environment.
              </p>

              <div className="bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-md p-3 text-sm">
                <p className="font-medium text-amber-800 dark:text-amber-200">
                  Direct edits create drift from Git.
                </p>
                <p className="mt-1 text-amber-700 dark:text-amber-300">
                  Recommended: Create a deployment instead to maintain version control and auditability.
                </p>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="acknowledge-drift"
                  checked={acknowledged}
                  onCheckedChange={(checked) => setAcknowledged(checked === true)}
                />
                <label
                  htmlFor="acknowledge-drift"
                  className="text-sm font-medium leading-none cursor-pointer"
                >
                  I understand this will create drift
                </label>
              </div>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={() => setAcknowledged(false)}>
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            disabled={!acknowledged}
            className="bg-amber-600 hover:bg-amber-700"
          >
            Edit Anyway
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

#### 3.2 Create Hard Delete Confirmation Dialog
**File:** `n8n-ops-ui/src/components/workflow/HardDeleteConfirmDialog.tsx`

```typescript
import { useState } from 'react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Input } from '@/components/ui/input';
import { Trash2 } from 'lucide-react';

interface HardDeleteConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workflowName: string;
  onConfirm: () => void;
}

export function HardDeleteConfirmDialog({
  open,
  onOpenChange,
  workflowName,
  onConfirm,
}: HardDeleteConfirmDialogProps) {
  const [confirmText, setConfirmText] = useState('');
  const expectedText = 'DELETE';

  const handleConfirm = () => {
    if (confirmText === expectedText) {
      onConfirm();
      setConfirmText('');
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2 text-destructive">
            <Trash2 className="h-5 w-5" />
            Permanently Delete Workflow
          </AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="space-y-4">
              <p>
                You are about to <strong>permanently delete</strong>{' '}
                <strong>{workflowName}</strong>.
              </p>

              <div className="bg-destructive/10 border border-destructive/20 rounded-md p-3 text-sm">
                <p className="font-medium text-destructive">
                  This action cannot be undone.
                </p>
                <ul className="mt-2 list-disc list-inside text-destructive/80 space-y-1">
                  <li>The workflow will be removed from N8N</li>
                  <li>Execution history may be lost or become inaccessible</li>
                  <li>The workflow cannot be recovered from this system</li>
                  <li>This will create permanent drift from Git</li>
                </ul>
              </div>

              <div className="space-y-2">
                <label htmlFor="confirm-delete" className="text-sm font-medium">
                  Type <code className="bg-muted px-1 rounded">{expectedText}</code> to confirm:
                </label>
                <Input
                  id="confirm-delete"
                  value={confirmText}
                  onChange={(e) => setConfirmText(e.target.value.toUpperCase())}
                  placeholder="Type DELETE"
                  className="font-mono"
                />
              </div>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={() => setConfirmText('')}>
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            disabled={confirmText !== expectedText}
            className="bg-destructive hover:bg-destructive/90"
          >
            Delete Permanently
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

#### 3.3 Integrate Dialogs and Handlers into WorkflowsPage
**In `WorkflowsPage.tsx`:**

**CRITICAL FIX:** Do NOT call hooks inside event handlers. Use pure function `getWorkflowActionPolicy()` instead of the hook when computing policy in handlers.

```typescript
import { DirectEditWarningDialog } from '@/components/workflow/DirectEditWarningDialog';
import { HardDeleteConfirmDialog } from '@/components/workflow/HardDeleteConfirmDialog';
import { WorkflowActionsMenu } from '@/components/workflow/WorkflowActionsMenu';
import { getWorkflowActionPolicy } from '@/lib/workflow-action-policy';
import { useFeatures } from '@/lib/features';
import { useAuth } from '@/lib/auth';

// Get plan and role at component level (valid hook usage)
const { planName } = useFeatures();
const { user } = useAuth();

// State for dialogs
const [driftWarningOpen, setDriftWarningOpen] = useState(false);
const [hardDeleteOpen, setHardDeleteOpen] = useState(false);
const [pendingEditWorkflow, setPendingEditWorkflow] = useState<Workflow | null>(null);
const [pendingDeleteWorkflow, setPendingDeleteWorkflow] = useState<Workflow | null>(null);

// Archive mutation (soft delete) - uses NEW dedicated endpoint
const archiveMutation = useMutation({
  mutationFn: (workflowId: string) =>
    apiClient.archiveWorkflow(workflowId, selectedEnvironment!),
  onSuccess: () => {
    toast.success('Workflow archived successfully');
    queryClient.invalidateQueries(['workflows', selectedEnvironment]);
  },
  onError: (error: Error) => {
    toast.error(`Failed to archive: ${error.message}`);
  },
});

// Hard delete mutation - uses DELETE with permanent=true
const hardDeleteMutation = useMutation({
  mutationFn: (workflowId: string) =>
    apiClient.permanentlyDeleteWorkflow(workflowId, selectedEnvironment!),
  onSuccess: () => {
    toast.success('Workflow permanently deleted');
    queryClient.invalidateQueries(['workflows', selectedEnvironment]);
  },
  onError: (error: Error) => {
    toast.error(`Failed to delete: ${error.message}`);
  },
});

// Handlers - use PURE FUNCTION, not hook
const handleEditClick = (workflow: Workflow) => {
  // Use pure function (NOT hook) inside event handler
  const hasDrift = workflow.syncStatus === 'local_changes' || workflow.syncStatus === 'conflict';
  const policy = getWorkflowActionPolicy(
    currentEnvironment,
    planName,
    user?.role || 'user',
    hasDrift
  );

  if (policy.editRequiresConfirmation) {
    setPendingEditWorkflow(workflow);
    setDriftWarningOpen(true);
  } else {
    openEditDialog(workflow);
  }
};

const handleDriftWarningConfirm = () => {
  if (pendingEditWorkflow) {
    openEditDialog(pendingEditWorkflow);
    setPendingEditWorkflow(null);
  }
  setDriftWarningOpen(false);
};

const handleSoftDelete = (workflow: Workflow) => {
  archiveMutation.mutate(workflow.id);
};

const handleHardDeleteClick = (workflow: Workflow) => {
  setPendingDeleteWorkflow(workflow);
  setHardDeleteOpen(true);
};

const handleHardDeleteConfirm = () => {
  if (pendingDeleteWorkflow) {
    hardDeleteMutation.mutate(pendingDeleteWorkflow.id);
    setPendingDeleteWorkflow(null);
  }
  setHardDeleteOpen(false);
};

// In render - Dialogs at page level:
<>
  <DirectEditWarningDialog
    open={driftWarningOpen}
    onOpenChange={setDriftWarningOpen}
    workflowName={pendingEditWorkflow?.name || ''}
    environmentType={currentEnvironment?.environmentClass || 'dev'}
    onConfirm={handleDriftWarningConfirm}
  />
  <HardDeleteConfirmDialog
    open={hardDeleteOpen}
    onOpenChange={setHardDeleteOpen}
    workflowName={pendingDeleteWorkflow?.name || ''}
    onConfirm={handleHardDeleteConfirm}
  />
</>

// In table row - Replace buttons with actions menu
// NOTE: Props MUST match component definition (onSoftDelete, onHardDelete - NOT onDelete)
<WorkflowActionsMenu
  workflow={workflow}
  environment={currentEnvironment}
  onViewDetails={() => navigate(`/workflows/${workflow.id}`)}
  onEdit={() => handleEditClick(workflow)}
  onSoftDelete={() => handleSoftDelete(workflow)}
  onHardDelete={() => handleHardDeleteClick(workflow)}
  onOpenInN8N={() => openInN8N(workflow.id)}
  onCreateDeployment={() => handleCreateDeployment(workflow)}
  onViewDriftIncident={() => handleViewDriftIncident(workflow)}
  onCreateDriftIncident={() => handleCreateDriftIncident(workflow)}
/>
```

---

### Phase 4: Route Changes Through Deployments

#### 4.1 Add "Create Deployment" Handler
**In `WorkflowsPage.tsx`:**

**IMPORTANT:** Use structured state instead of query params where possible. Verify actual route exists before implementing.

```typescript
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '@/store/use-app-store';

const navigate = useNavigate();

const handleCreateDeployment = (workflow: Workflow) => {
  // Option 1: Use Zustand store for structured state (preferred)
  // Avoids fragile query param parsing
  useAppStore.getState().setPromotionContext({
    workflowId: workflow.id,
    sourceEnvironmentId: currentEnvironment?.id,
  });
  navigate('/promote');

  // Option 2: If store approach not feasible, use query params
  // But verify /promote route actually accepts these params
  // navigate(`/promote?workflow=${workflow.id}&source=${currentEnvironment?.id}`);
};
```

**NOTE:** Before implementing, verify the actual Deployments/Promote route structure in `App.tsx`.

#### 4.2 Rename "Upload Workflow" Button (Decision: Rename + Policy-Gate)
**In `WorkflowsPage.tsx`:**

The current "Upload Workflow" button actually backs up to GitHub. **Decision:**
- Rename to "Backup to GitHub" to match actual behavior
- **Policy is the source of truth** - derive visibility from policy, NOT separate `allowUpload` flag
- **Dev:** Allow direct backup
- **Staging/Production:** Redirect to Deployments page

```typescript
// Use policy as single source of truth - no separate allowUpload flag
const envClass = currentEnvironment?.environmentClass || 'dev';

// Compute policy at component level (valid hook usage)
const hasDrift = false; // Backup button not workflow-specific
const policy = useMemo(
  () => getWorkflowActionPolicy(currentEnvironment, planName, user?.role || 'user', hasDrift),
  [currentEnvironment, planName, user?.role]
);

const handleBackupClick = () => {
  if (envClass === 'dev') {
    // Allow direct backup in dev
    handleUploadClick(); // Existing backup logic
  } else {
    // Redirect to deployments in staging/prod
    toast.info('Direct backups are not allowed in staging/production. Use deployments instead.');
    navigate('/deployments');
  }
};

// In render - derive from policy, not separate flag:
{policy.canEditDirectly && currentEnvironment?.gitConfig && (
  <Button onClick={handleBackupClick} variant="outline">
    {envClass === 'dev' ? (
      <>
        <GitBranch className="h-4 w-4 mr-2" />
        Backup to GitHub
      </>
    ) : (
      <>
        <Rocket className="h-4 w-4 mr-2" />
        Go to Deployments
      </>
    )}
  </Button>
)}
```

**NOTE:** Remove `allowUpload` feature flag - it's redundant with policy-based gating.

---

### Phase 5: Integrate Drift Incident Entry Points

#### 5.1 Add Drift Incident Navigation
**In `WorkflowsPage.tsx`:**

```typescript
const handleCreateDriftIncident = (workflow: Workflow) => {
  // Navigate to create drift incident page with workflow context
  navigate(`/incidents/new?environment=${currentEnvironment?.id}&workflow=${workflow.id}`);
};

const handleViewDriftIncident = (workflow: Workflow) => {
  // If environment has active drift incident, navigate to it
  if (currentEnvironment?.activeDriftIncidentId) {
    navigate(`/incidents/${currentEnvironment.activeDriftIncidentId}`);
  }
};
```

#### 5.2 Sync Status Column (Read-Only)

**IMPORTANT:** Status columns must be READ-ONLY. All actions belong in the Actions menu.

```typescript
// Status column shows ONLY informational badge - NO buttons/actions
const getSyncStatusDisplay = (workflow: Workflow, environment: Environment | null) => {
  const status = workflow.syncStatus;
  const hasDrift = status === 'local_changes' || status === 'conflict';
  const hasActiveIncident = environment?.driftStatus === 'DRIFT_INCIDENT_ACTIVE';

  // Determine badge variant
  let variant: 'default' | 'secondary' | 'destructive' | 'outline' = 'default';
  let label = 'In Sync';

  if (status === 'local_changes') {
    variant = 'secondary';
    label = 'Local Changes';
  } else if (status === 'conflict') {
    variant = 'destructive';
    label = 'Conflict';
  } else if (status === 'update_available') {
    variant = 'outline';
    label = 'Update Available';
  }

  return (
    <div className="flex items-center gap-2">
      <Badge variant={variant}>{label}</Badge>

      {/* Show indicator if incident exists - but NO action buttons */}
      {hasDrift && hasActiveIncident && (
        <AlertCircle className="h-4 w-4 text-amber-500" title="Drift incident active" />
      )}
    </div>
  );
};

// All drift incident actions are in the Actions dropdown menu (Phase 1)
// NOT in the status column
```

---

### Phase 6: Backend Policy Enforcement

#### 6.1 Create Canonical Policy Schema

**CRITICAL:** Define ONE policy schema shared between frontend and backend. Field names MUST match exactly.

**File:** `n8n-ops-backend/app/schemas/workflow_policy.py`

```python
"""
Canonical WorkflowActionPolicy schema - used by both frontend and backend.
Field names must match TypeScript interface in workflow-action-policy.ts
"""
from pydantic import BaseModel
from enum import Enum
from typing import Optional

class EnvironmentClass(str, Enum):
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"

class WorkflowActionPolicy(BaseModel):
    """Canonical policy schema - matches frontend exactly"""
    can_view_details: bool = True
    can_open_in_n8n: bool = True
    can_create_deployment: bool = True
    can_edit_directly: bool = False
    can_soft_delete: bool = False       # Archive workflow
    can_hard_delete: bool = False       # Permanently remove (admin-only)
    can_create_drift_incident: bool = False
    drift_incident_required: bool = False
    edit_requires_confirmation: bool = True
    edit_requires_admin: bool = False

class WorkflowPolicyResponse(BaseModel):
    environment_id: str
    environment_class: EnvironmentClass
    plan: str
    role: str
    policy: WorkflowActionPolicy
```

**File:** `n8n-ops-backend/app/api/endpoints/workflow_policy.py`

```python
from fastapi import APIRouter, HTTPException, Depends
from app.schemas.workflow_policy import (
    EnvironmentClass, WorkflowActionPolicy, WorkflowPolicyResponse
)
from app.services.database import db_service
from app.services.auth_service import get_current_user

router = APIRouter()

@router.get("/policy/{environment_id}", response_model=WorkflowPolicyResponse)
async def get_workflow_action_policy(
    environment_id: str,
    user_info: dict = Depends(get_current_user)
) -> WorkflowPolicyResponse:
    """
    Get the workflow action policy for an environment.
    Returns what actions are allowed based on environment class, plan, and role.
    """
    tenant = user_info.get("tenant", {})
    user = user_info.get("user", {})
    tenant_id = tenant.get("id")  # ALWAYS use authenticated tenant_id

    # Get environment
    env = await db_service.get_environment(environment_id, tenant_id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")

    # Get tenant plan and user role
    plan = tenant.get("subscription_tier", "free")
    role = user.get("role", "user")

    # Use environment_class from DB - NEVER infer at runtime
    env_class_str = env.get("environment_class", "dev")
    try:
        env_class = EnvironmentClass(env_class_str)
    except ValueError:
        env_class = EnvironmentClass.DEV  # Safe fallback

    # Build policy
    policy = build_policy(env_class, plan, role)

    return WorkflowPolicyResponse(
        environment_id=environment_id,
        environment_class=env_class,
        plan=plan,
        role=role,
        policy=policy
    )

def build_policy(
    env_class: EnvironmentClass,
    plan: str,
    role: str,
    has_drift: bool = False
) -> WorkflowActionPolicy:
    """Build policy based on environment class, plan, and role."""
    is_admin = role in ['admin', 'superuser']
    is_agency_plus = plan in ['agency', 'enterprise']

    # Base policies by environment class
    if env_class == EnvironmentClass.PRODUCTION:
        policy = WorkflowActionPolicy(
            can_edit_directly=False,
            can_soft_delete=False,
            can_hard_delete=False,
            can_create_drift_incident=True,
            drift_incident_required=True,
            edit_requires_confirmation=False,
            edit_requires_admin=False,
        )
    elif env_class == EnvironmentClass.STAGING:
        policy = WorkflowActionPolicy(
            can_edit_directly=is_admin and not is_agency_plus,
            can_soft_delete=False,
            can_hard_delete=False,
            can_create_drift_incident=True,
            drift_incident_required=is_agency_plus,
            edit_requires_confirmation=True,
            edit_requires_admin=True,
        )
    else:  # DEV
        policy = WorkflowActionPolicy(
            can_edit_directly=True,
            can_soft_delete=True,
            can_hard_delete=is_admin,
            can_create_drift_incident=is_agency_plus,
            drift_incident_required=False,
            edit_requires_confirmation=True,
            edit_requires_admin=False,
        )

    # Plan-based overrides
    if plan == 'free':
        policy.can_create_drift_incident = False
        policy.drift_incident_required = False

    return policy
```

#### 6.2 Enforce Policy on Mutation Endpoints
**File:** `n8n-ops-backend/app/api/endpoints/workflows.py`

**CRITICAL FIXES:**
1. Use authenticated `tenant_id` from `user_info` - NEVER use `MOCK_TENANT_ID`
2. Keep `DELETE` endpoint with ORIGINAL behavior (hard delete) for backward compatibility
3. Add NEW `/archive` endpoint for soft delete
4. Use canonical policy schema with correct field names

```python
from app.schemas.workflow_policy import EnvironmentClass
from app.api.endpoints.workflow_policy import build_policy

@router.put("/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    workflow_data: Dict[str, Any],
    environment_id: Optional[str] = None,
    environment: Optional[str] = None,
    user_info: dict = Depends(require_entitlement("workflow_push"))
):
    """Update a workflow (name, active status, tags)"""
    env_config = await resolve_environment_config(environment_id, environment)

    # Extract tenant_id from authenticated user - NEVER hardcode
    tenant = user_info.get("tenant", {})
    user = user_info.get("user", {})
    tenant_id = tenant.get("id")
    plan = tenant.get("subscription_tier", "free")
    role = user.get("role", "user")

    # Get environment class from DB - NEVER infer
    env_class_str = env_config.get("environment_class", "dev")
    try:
        env_class = EnvironmentClass(env_class_str)
    except ValueError:
        env_class = EnvironmentClass.DEV

    # Build and check policy
    policy = build_policy(env_class, plan, role)

    if not policy.can_edit_directly:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Direct edits are not allowed in {env_class.value} environments. Please use deployments."
        )

    # Continue with existing logic using tenant_id...

# NEW: Dedicated archive endpoint for soft delete
@router.post("/{workflow_id}/archive")
async def archive_workflow(
    workflow_id: str,
    environment_id: Optional[str] = None,
    environment: Optional[str] = None,
    user_info: dict = Depends(require_entitlement("workflow_push"))
):
    """Soft delete (archive) a workflow - hides but doesn't remove from N8N"""
    env_config = await resolve_environment_config(environment_id, environment)

    # Extract from authenticated user
    tenant = user_info.get("tenant", {})
    user = user_info.get("user", {})
    tenant_id = tenant.get("id")
    user_id = user.get("id")
    plan = tenant.get("subscription_tier", "free")
    role = user.get("role", "user")

    # Get environment class from DB
    env_class_str = env_config.get("environment_class", "dev")
    try:
        env_class = EnvironmentClass(env_class_str)
    except ValueError:
        env_class = EnvironmentClass.DEV

    # Build and check policy
    policy = build_policy(env_class, plan, role)

    if not policy.can_soft_delete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Archiving workflows is not allowed in {env_class.value} environments."
        )

    # Mark as archived in database
    await db_service.archive_workflow(
        tenant_id=tenant_id,
        environment_id=env_config.get("id"),
        workflow_id=workflow_id,
        archived_by=user_id
    )

    # Create audit log
    await create_audit_log(
        action_type=AuditActionType.WORKFLOW_ARCHIVED,
        action=f"Archived workflow",
        tenant_id=tenant_id,
        resource_type="workflow",
        resource_id=workflow_id,
        metadata={"environment_class": env_class.value, "creates_drift": True}
    )

    return {"status": "archived", "workflow_id": workflow_id}

# KEEP DELETE with ORIGINAL behavior (hard delete) for backward compatibility
# Frontend uses /archive for soft delete, DELETE only for permanent
@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    environment_id: Optional[str] = None,
    environment: Optional[str] = None,
    user_info: dict = Depends(require_entitlement("workflow_push"))
):
    """
    Permanently delete a workflow from N8N.

    BREAKING CHANGE AVOIDED: This endpoint retains original hard-delete behavior.
    For soft delete (archive), use POST /{workflow_id}/archive instead.
    """
    env_config = await resolve_environment_config(environment_id, environment)

    # Extract from authenticated user
    tenant = user_info.get("tenant", {})
    user = user_info.get("user", {})
    tenant_id = tenant.get("id")
    plan = tenant.get("subscription_tier", "free")
    role = user.get("role", "user")

    # Get environment class from DB
    env_class_str = env_config.get("environment_class", "dev")
    try:
        env_class = EnvironmentClass(env_class_str)
    except ValueError:
        env_class = EnvironmentClass.DEV

    # Build and check policy - must have hard delete permission
    policy = build_policy(env_class, plan, role)

    if not policy.can_hard_delete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permanent deletion requires admin role in dev environment only."
        )

    # Hard delete from N8N
    adapter = ProviderRegistry.get_adapter_for_environment(env_config)
    await adapter.delete_workflow(workflow_id)

    # Remove from cache
    await db_service.delete_workflow_from_cache(
        tenant_id, env_config.get("id"), workflow_id
    )

    # Create audit log
    await create_audit_log(
        action_type=AuditActionType.WORKFLOW_HARD_DELETED,
        action=f"Permanently deleted workflow",
        tenant_id=tenant_id,
        resource_type="workflow",
        resource_id=workflow_id,
        metadata={"environment_class": env_class.value, "permanent": True}
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

#### 6.3 Add Audit Events for Direct Actions
**In workflows.py, add to update/delete handlers:**

```python
# In update_workflow, after successful update:
await create_audit_log(
    action_type=AuditActionType.WORKFLOW_EDIT_DIRECT,
    action=f"Direct edit on workflow '{workflow.get('name')}' in {env_class} environment",
    tenant_id=tenant_id,
    resource_type="workflow",
    resource_id=workflow_id,
    resource_name=workflow.get("name"),
    provider=env_config.get("provider", "n8n"),
    metadata={
        "environment_id": env_config.get("id"),
        "environment_class": env_class,
        "creates_drift": True
    }
)

# In delete_workflow, after successful delete:
await create_audit_log(
    action_type=AuditActionType.WORKFLOW_DELETE_DIRECT,
    action=f"Direct delete of workflow '{workflow_name}' in {env_class} environment",
    tenant_id=tenant_id,
    resource_type="workflow",
    resource_id=workflow_id,
    resource_name=workflow_name,
    provider=env_config.get("provider", "n8n"),
    metadata={
        "environment_id": env_config.get("id"),
        "environment_class": env_class,
        "creates_drift": True
    }
)
```

---

### Phase 7: Update API Client Methods

**File:** `n8n-ops-ui/src/lib/api-client.ts`

Add new methods for policy, archive, and delete operations:

```typescript
// Get workflow action policy for environment
async getWorkflowPolicy(environmentId: string): Promise<WorkflowPolicyResponse> {
  const response = await this.client.get(`/workflows/policy/${environmentId}`);
  return response.data;
}

// Archive (soft delete) a workflow - NEW endpoint
async archiveWorkflow(
  workflowId: string,
  environmentId: string
): Promise<{ status: string; workflow_id: string }> {
  const response = await this.client.post(
    `/workflows/${workflowId}/archive`,
    null,
    { params: { environment_id: environmentId } }
  );
  return response.data;
}

// Unarchive (restore) a workflow
async unarchiveWorkflow(
  workflowId: string,
  environmentId: string
): Promise<{ status: string; workflow_id: string }> {
  const response = await this.client.post(
    `/workflows/${workflowId}/unarchive`,
    null,
    { params: { environment_id: environmentId } }
  );
  return response.data;
}

// Permanently delete workflow (hard delete) - admin only in dev
// NOTE: This is the ORIGINAL DELETE behavior, kept for backward compatibility
async permanentlyDeleteWorkflow(
  workflowId: string,
  environmentId: string
): Promise<void> {
  await this.client.delete(`/workflows/${workflowId}`, {
    params: {
      environment_id: environmentId,
    },
  });
}

// Get workflows with optional archived filter
async getWorkflows(
  environmentId: string,
  forceRefresh: boolean = false,
  includeArchived: boolean = false
): Promise<Workflow[]> {
  const response = await this.client.get('/workflows/', {
    params: {
      environment_id: environmentId,
      force_refresh: forceRefresh,
      include_archived: includeArchived,
    },
  });
  return response.data;
}
```

Add types (matching backend canonical schema):

```typescript
// In types/index.ts - MUST match backend WorkflowActionPolicy exactly
export interface WorkflowActionPolicy {
  can_view_details: boolean;
  can_open_in_n8n: boolean;
  can_create_deployment: boolean;
  can_edit_directly: boolean;
  can_soft_delete: boolean;
  can_hard_delete: boolean;
  can_create_drift_incident: boolean;
  drift_incident_required: boolean;
  edit_requires_confirmation: boolean;
  edit_requires_admin: boolean;
}

export interface WorkflowPolicyResponse {
  environment_id: string;
  environment_class: 'dev' | 'staging' | 'production';
  plan: string;
  role: string;
  policy: WorkflowActionPolicy;
}
```

---

### Phase 8: Add "Managed By" Indicator (Optional)

**NOTE:** This phase is optional and requires schema changes. Consider deferring if not critical.

#### 8.1 Determine Management Source (Reliable Approach)

**PROBLEM:** Using `lastSyncedAt` is unreliable - new Git-managed workflows may not have been synced yet.

**SOLUTION:** Base on persisted linkage, not sync timestamps:

**Schema Change Required:**
```sql
-- Add to workflows table
ALTER TABLE workflows ADD COLUMN git_path VARCHAR(255);     -- e.g., "workflows/my-workflow.json"
ALTER TABLE workflows ADD COLUMN git_commit_sha VARCHAR(40); -- Last known commit
ALTER TABLE workflows ADD COLUMN managed_by VARCHAR(20) DEFAULT 'manual';  -- 'git' | 'manual'
```

**In `WorkflowsPage.tsx`:**

```typescript
function getManagedBy(workflow: Workflow): 'git' | 'manual' | 'unknown' {
  // Use explicit managed_by field if available (most reliable)
  if (workflow.managedBy) {
    return workflow.managedBy;
  }

  // Fallback: Check for Git linkage (has git path = Git managed)
  if (workflow.gitPath || workflow.gitCommitSha) {
    return 'git';
  }

  // No Git linkage = manual
  return 'manual';
}
```

**NOTE:** The `lastSyncedAt` heuristic is unreliable because:
1. New Git-managed workflows may not have been synced yet
2. A workflow synced once and never touched is still "Git managed"
3. Import from Git doesn't always set sync timestamp

#### 8.2 Add Column/Badge
```tsx
<TableHead>Managed By</TableHead>
// ...
<TableCell>
  <Badge variant="outline" className="text-xs">
    {getManagedBy(workflow) === 'git' ? (
      <><GitBranch className="h-3 w-3 mr-1" /> Git</>
    ) : getManagedBy(workflow) === 'manual' ? (
      <><User className="h-3 w-3 mr-1" /> Manual</>
    ) : (
      <>Unknown</>
    )}
  </Badge>
</TableCell>
```

---

## File Changes Summary

### New Files to Create
| File | Purpose |
|------|---------|
| `n8n-ops-ui/src/components/workflow/WorkflowActionsMenu.tsx` | Actions dropdown component |
| `n8n-ops-ui/src/components/workflow/DirectEditWarningDialog.tsx` | Drift warning modal |
| `n8n-ops-ui/src/components/workflow/HardDeleteConfirmDialog.tsx` | Admin-only permanent delete confirmation |
| `n8n-ops-ui/src/lib/workflow-action-policy.ts` | Policy types and logic |
| `n8n-ops-ui/src/hooks/useWorkflowActionPolicy.ts` | Policy hook |
| `n8n-ops-backend/app/api/endpoints/workflow_policy.py` | Backend policy endpoint |
| `n8n-ops-backend/alembic/versions/xxx_add_environment_class.py` | DB migration for env class |
| `n8n-ops-backend/alembic/versions/xxx_add_workflow_archive.py` | DB migration for soft delete |

### Files to Modify
| File | Changes |
|------|---------|
| `n8n-ops-ui/src/pages/WorkflowsPage.tsx` | Replace buttons with actions menu, add dialogs, add handlers |
| `n8n-ops-ui/src/types/index.ts` | Add `environmentClass` field to Environment, add `isArchived` to Workflow |
| `n8n-ops-backend/app/api/endpoints/workflows.py` | Add policy checks, soft/hard delete, archive endpoint |
| `n8n-ops-backend/app/schemas/environment.py` | Add `environment_class` enum field |
| `n8n-ops-backend/app/services/database.py` | Add `archive_workflow()` method |
| `n8n-ops-backend/app/main.py` | Register workflow_policy router |
| `n8n-ops-ui/src/lib/api-client.ts` | Add policy API, archive, permanent delete methods |
| `n8n-ops-backend/app/api/endpoints/admin_audit.py` | Add new audit action types |

### Database Migration Required
| Table | Change |
|-------|--------|
| `environments` | Add `environment_class ENUM('dev', 'staging', 'production') NOT NULL DEFAULT 'dev'` |
| `workflows` | Add `is_archived BOOLEAN DEFAULT FALSE`, `archived_at TIMESTAMP` |

---

## Testing Checklist

### Phase 1: Actions Menu
- [ ] Actions dropdown appears on each workflow row
- [ ] All existing actions accessible via menu
- [ ] Menu styling consistent with app design
- [ ] Icons display correctly for each action

### Phase 2: Environment Gating
- [ ] Production: Edit/Delete hidden (not just disabled)
- [ ] Staging: Edit visible only for admin, Delete hidden
- [ ] Dev: Edit/Archive available with warning, Hard Delete admin-only
- [ ] Policy uses `environmentClass` field (not fuzzy matching)
- [ ] Legacy environments without `environmentClass` fall back safely to 'dev'

### Phase 3: Warning Dialog
- [ ] Warning appears before editing in dev
- [ ] Checkbox must be checked to proceed
- [ ] Cancel returns without changes
- [ ] Audit log created when proceeding with direct edit

### Phase 4: Deployment Route
- [ ] "Create Deployment" navigates to promote page with workflow pre-selected
- [ ] "Backup to GitHub" button shows only in dev environments
- [ ] Staging/prod shows "Go to Deployments" button instead
- [ ] Toast notification explains why direct backup not allowed

### Phase 5: Drift Incidents
- [ ] "Create Drift Incident" appears when drift detected
- [ ] Free/Pro: Option shown without "Required" badge
- [ ] Agency+: Option shown with "Required" badge in staging/prod
- [ ] Links to incidents page with environment/workflow context

### Phase 6: Delete Behavior
- [ ] Default delete in dev = soft delete (archive)
- [ ] Archived workflows hidden from main list but recoverable
- [ ] "Permanently Delete" option appears only for admin in dev
- [ ] Hard delete confirmation dialog requires explicit acknowledgment
- [ ] Staging/prod: No delete options available

### Phase 7: Backend Enforcement
- [ ] 403 returned for disallowed actions with clear message
- [ ] Audit logs created for all direct mutations
- [ ] `DELETE /workflows/{id}` defaults to soft delete
- [ ] `DELETE /workflows/{id}?permanent=true` requires admin + dev env
- [ ] `POST /workflows/{id}/archive` endpoint works correctly
- [ ] Policy endpoint returns correct policy for all env/plan/role combos

### Database Migration
- [ ] `environments.environment_class` column added with default 'dev'
- [ ] `workflows.is_archived` and `workflows.archived_at` columns added
- [ ] Existing environments migrated to appropriate `environment_class` values
- [ ] Archived workflows excluded from default list queries
