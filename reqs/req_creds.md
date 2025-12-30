# Credential Management Enhancement Plan

## Overview

Enhance the credential management system to provide a unified view of credentials across environments, simplify mapping workflows, and improve the promotion experience.

## Current State

### Existing Infrastructure
- **Physical Credentials** (`CredentialsPage.tsx`) - CRUD on N8N credentials per environment
- **Logical Credentials** (`CredentialHealthPage.tsx`) - Abstract aliases managed in admin
- **Credential Mappings** - Links logical → physical per environment
- **Preflight Validation** (`admin_credentials.py`) - Validates mappings before promotion
- **Database Tables**: `credentials`, `logical_credentials`, `credential_mappings`, `workflow_credential_dependencies`

### Current Limitations
1. Physical credentials and logical mappings are on separate pages
2. Manual entry of physical credential IDs (no dropdown selection)
3. No auto-discovery of credentials from workflows
4. No health check to validate mappings are still valid
5. Credential matrix view not available

---

## Implementation Plan

### Phase 1: Backend Enhancements

#### 1.1 Add Credential Lookup Endpoint
**File**: `n8n-ops-backend/app/api/endpoints/credentials.py`

Add endpoint to fetch credentials from N8N for a specific environment (for dropdown population):

```python
@router.get("/by-environment/{environment_id}")
async def get_credentials_by_environment(environment_id: str):
    """Get all credentials from N8N for a specific environment.
    Used for populating dropdowns when creating mappings.
    """
```

**Implementation**:
- Get environment config
- Create adapter for environment
- Call `adapter.get_credentials()`
- Return list with id, name, type for dropdown use

#### 1.2 Add Credential Discovery Endpoint
**File**: `n8n-ops-backend/app/api/endpoints/admin_credentials.py`

Add endpoint to discover credentials from workflows:

```python
@router.post("/discover/{environment_id}")
async def discover_credentials_from_workflows(environment_id: str):
    """Scan all workflows in environment and return unique credential references.
    Returns list of {type, name, logical_key, workflows_using} for each credential found.
    """
```

**Implementation**:
- Get all workflows from environment cache
- For each workflow, call `N8NProviderAdapter.extract_logical_credentials()`
- Aggregate and deduplicate
- Return with workflow counts and existing mapping status

#### 1.3 Add Mapping Health Check Endpoint
**File**: `n8n-ops-backend/app/api/endpoints/admin_credentials.py`

Add endpoint to validate all mappings:

```python
@router.post("/mappings/validate")
async def validate_credential_mappings(environment_id: Optional[str] = None):
    """Validate that all credential mappings still resolve to valid N8N credentials.
    Updates status field and returns validation report.
    """
```

**Implementation**:
- Get all mappings (optionally filtered by environment)
- For each mapping, fetch credentials from target environment
- Check if physical_credential_id exists
- Update mapping status: "valid" | "invalid" | "stale"
- Return summary report

#### 1.4 Add Credential Matrix Endpoint
**File**: `n8n-ops-backend/app/api/endpoints/admin_credentials.py`

Add endpoint to get cross-environment credential matrix:

```python
@router.get("/matrix")
async def get_credential_matrix():
    """Get a matrix view of all logical credentials and their mappings across environments.
    Returns: {
        logical_credentials: [...],
        environments: [...],
        matrix: { [logical_id]: { [env_id]: mapping | null } }
    }
    """
```

**Implementation**:
- Get all environments
- Get all logical credentials
- Get all mappings
- Build matrix structure grouping mappings by logical credential and environment

---

### Phase 2: Frontend - Credential Matrix View

#### 2.1 Create Credential Matrix Component
**File**: `n8n-ops-ui/src/components/credentials/CredentialMatrix.tsx`

Create a table component showing logical credentials vs environments:

```tsx
interface CredentialMatrixProps {
  onCreateMapping: (logicalId: string, envId: string) => void;
  onEditMapping: (mapping: CredentialMapping) => void;
}
```

**Features**:
- Table with logical credentials as rows, environments as columns
- Cell shows: ✅ mapped (with name), ⚠️ invalid, ❌ missing
- Click cell to create/edit mapping
- Row actions: edit logical credential, delete
- Column header shows environment name and type badge

#### 2.2 Create Unified Credentials Page
**File**: `n8n-ops-ui/src/pages/CredentialsPage.tsx` (refactor)

Refactor to include tabs:

```tsx
<Tabs defaultValue="physical">
  <TabsList>
    <TabsTrigger value="physical">Physical Credentials</TabsTrigger>
    <TabsTrigger value="matrix">Credential Matrix</TabsTrigger>
    <TabsTrigger value="discover">Discover</TabsTrigger>
  </TabsList>
  <TabsContent value="physical">
    {/* Existing credentials table */}
  </TabsContent>
  <TabsContent value="matrix">
    <CredentialMatrix />
  </TabsContent>
  <TabsContent value="discover">
    <CredentialDiscovery />
  </TabsContent>
</Tabs>
```

---

### Phase 3: Frontend - Smart Mapping Dialog

#### 3.1 Create Credential Picker Component
**File**: `n8n-ops-ui/src/components/credentials/CredentialPicker.tsx`

Dropdown that fetches and displays credentials from a specific environment:

```tsx
interface CredentialPickerProps {
  environmentId: string;
  filterType?: string;  // Filter by credential type
  value: string;
  onChange: (credentialId: string, credential: Credential) => void;
}
```

**Features**:
- Fetches credentials from `/credentials/by-environment/{envId}` on mount
- Filters by type if `filterType` provided
- Shows credential name and type in dropdown
- Auto-selects if name matches (smart suggestion)

#### 3.2 Update Mapping Dialog
**File**: `n8n-ops-ui/src/pages/admin/CredentialHealthPage.tsx` (or new component)

Replace manual ID input with `CredentialPicker`:

```tsx
// Before:
<Input
  id="physicalId"
  value={mappingPhysicalId}
  onChange={(e) => setMappingPhysicalId(e.target.value)}
  placeholder="ID from n8n"
/>

// After:
<CredentialPicker
  environmentId={mappingEnvId}
  filterType={selectedLogical?.required_type}
  value={mappingPhysicalId}
  onChange={(id, cred) => {
    setMappingPhysicalId(id);
    setMappingPhysicalName(cred.name);
    setMappingPhysicalType(cred.type);
  }}
/>
```

---

### Phase 4: Frontend - Credential Discovery

#### 4.1 Create Discovery Component
**File**: `n8n-ops-ui/src/components/credentials/CredentialDiscovery.tsx`

Component to discover and create logical credentials from workflows:

```tsx
interface DiscoveredCredential {
  type: string;
  name: string;
  logicalKey: string;  // "type:name"
  workflowCount: number;
  workflows: { id: string; name: string }[];
  hasLogical: boolean;
  hasMapping: boolean;
}
```

**Features**:
- Environment selector
- "Scan Workflows" button
- Table showing discovered credentials
- Columns: Type, Name, Used By (workflow count), Status (mapped/unmapped)
- Actions: "Create Logical", "Create Mapping"
- Bulk action: "Create All Missing"

#### 4.2 Add API Client Methods
**File**: `n8n-ops-ui/src/lib/api-client.ts`

Add methods:

```typescript
async discoverCredentials(environmentId: string): Promise<{ data: DiscoveredCredential[] }> {
  const response = await this.client.post(`/admin/credentials/discover/${environmentId}`);
  return { data: response.data };
}

async getCredentialsByEnvironment(environmentId: string): Promise<{ data: Credential[] }> {
  const response = await this.client.get(`/credentials/by-environment/${environmentId}`);
  return { data: response.data };
}

async validateMappings(environmentId?: string): Promise<{ data: ValidationReport }> {
  const response = await this.client.post('/admin/credentials/mappings/validate', {
    params: environmentId ? { environment_id: environmentId } : {}
  });
  return { data: response.data };
}

async getCredentialMatrix(): Promise<{ data: CredentialMatrixData }> {
  const response = await this.client.get('/admin/credentials/matrix');
  return { data: response.data };
}
```

---

### Phase 5: Health Check & Validation

#### 5.1 Add Validation UI
**File**: `n8n-ops-ui/src/components/credentials/MappingHealthCheck.tsx`

Component showing mapping health:

```tsx
interface ValidationReport {
  total: number;
  valid: number;
  invalid: number;
  stale: number;
  issues: {
    mappingId: string;
    logicalName: string;
    environmentName: string;
    issue: string;
  }[];
}
```

**Features**:
- "Validate All Mappings" button
- Summary cards: Total, Valid, Invalid, Stale
- Issues table with actions to fix
- Environment filter

#### 5.2 Add Status Badges to Matrix
Update `CredentialMatrix.tsx` to show validation status:

```tsx
const getStatusBadge = (mapping: CredentialMapping | null) => {
  if (!mapping) return <Badge variant="destructive">Missing</Badge>;
  if (mapping.status === 'valid') return <Badge variant="default">✓ {mapping.physical_name}</Badge>;
  if (mapping.status === 'invalid') return <Badge variant="warning">⚠️ Invalid</Badge>;
  return <Badge variant="outline">? Unknown</Badge>;
};
```

---

### Phase 6: Integration with Promotion Flow

#### 6.1 Enhance Preflight Dialog
**File**: `n8n-ops-ui/src/components/promotion/CredentialPreflightDialog.tsx`

Improve the existing preflight dialog:

**Features**:
- Show credential matrix for selected workflows only
- Quick-create mapping from dialog (inline)
- Clear distinction between blocking issues and warnings
- "Map Now" action that opens mapping dialog pre-filled

#### 6.2 Add Credential Step to Promotion Wizard
If using a wizard flow, ensure credential mapping is a visible step:

```
Step 1: Select Workflows
Step 2: Credential Check  ← Show matrix for selected workflows
Step 3: Review Changes
Step 4: Confirm
```

---

## File Changes Summary

### New Files
- `n8n-ops-ui/src/components/credentials/CredentialMatrix.tsx`
- `n8n-ops-ui/src/components/credentials/CredentialPicker.tsx`
- `n8n-ops-ui/src/components/credentials/CredentialDiscovery.tsx`
- `n8n-ops-ui/src/components/credentials/MappingHealthCheck.tsx`

### Modified Files
- `n8n-ops-backend/app/api/endpoints/credentials.py` - Add by-environment endpoint
- `n8n-ops-backend/app/api/endpoints/admin_credentials.py` - Add discover, validate, matrix endpoints
- `n8n-ops-ui/src/pages/CredentialsPage.tsx` - Add tabs for matrix and discover views
- `n8n-ops-ui/src/pages/admin/CredentialHealthPage.tsx` - Replace ID input with picker
- `n8n-ops-ui/src/lib/api-client.ts` - Add new API methods
- `n8n-ops-ui/src/types/credentials.ts` - Add new types

---

## Types to Add

**File**: `n8n-ops-ui/src/types/credentials.ts`

```typescript
export interface DiscoveredCredential {
  type: string;
  name: string;
  logicalKey: string;
  workflowCount: number;
  workflows: { id: string; name: string }[];
  existingLogicalId?: string;
  mappingStatus: 'mapped' | 'unmapped' | 'partial';
}

export interface CredentialMatrixData {
  logicalCredentials: LogicalCredential[];
  environments: Environment[];
  matrix: Record<string, Record<string, CredentialMapping | null>>;
}

export interface MappingValidationReport {
  total: number;
  valid: number;
  invalid: number;
  stale: number;
  issues: MappingIssue[];
}

export interface MappingIssue {
  mappingId: string;
  logicalName: string;
  environmentId: string;
  environmentName: string;
  issue: 'credential_not_found' | 'type_mismatch' | 'name_changed';
  message: string;
}
```

---

## Implementation Order

1. **Phase 1.1**: Add `/credentials/by-environment/{id}` endpoint (enables Phase 3)
2. **Phase 3.1**: Create `CredentialPicker` component
3. **Phase 3.2**: Update mapping dialog to use picker
4. **Phase 1.4**: Add `/admin/credentials/matrix` endpoint
5. **Phase 2.1**: Create `CredentialMatrix` component
6. **Phase 2.2**: Add tabs to CredentialsPage
7. **Phase 1.2**: Add `/admin/credentials/discover/{id}` endpoint
8. **Phase 4.1**: Create `CredentialDiscovery` component
9. **Phase 1.3**: Add `/admin/credentials/mappings/validate` endpoint
10. **Phase 5.1**: Create `MappingHealthCheck` component
11. **Phase 5.2**: Add status badges to matrix
12. **Phase 6**: Enhance promotion preflight (if time permits)

---

## Testing Checklist

- [ ] Can fetch credentials by environment for dropdown
- [ ] CredentialPicker shows filtered credentials by type
- [ ] Creating mapping with picker populates all fields
- [ ] Matrix shows all logical credentials vs all environments
- [ ] Matrix cells show correct status (mapped/missing/invalid)
- [ ] Click matrix cell opens mapping dialog pre-filled
- [ ] Discovery scans workflows and finds credentials
- [ ] Discovery shows which credentials already have mappings
- [ ] Can create logical + mapping from discovery in one flow
- [ ] Validation detects deleted credentials in N8N
- [ ] Validation updates mapping status
- [ ] Preflight uses mapping data correctly during promotion

---

## Notes

- All credential secrets remain in N8N - we only store metadata locally
- Logical credentials use format `type:name` to match workflow references
- Mappings are per-environment and per-provider (supports future multi-provider)
- The existing preflight validation in `admin_credentials.py` already handles the promotion check - this plan improves the UX around creating and managing mappings
