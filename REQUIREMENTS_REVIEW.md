# Requirements vs Implementation Review

## reqs_pipelines.md - Pipeline UI Requirements

### ✅ COMPLETE - Required for v1

1. **Pipelines List Screen** ✅
   - ✅ List/table with Pipeline Name, Environment Path, Status, Last Modified
   - ✅ Create Pipeline button
   - ✅ Per-row actions: Edit, Duplicate, Activate/Deactivate, Delete
   - ✅ Clicking pipeline opens editor
   - ✅ Deactivated pipelines cannot be used (filtered in UI)

2. **Pipeline Editor Screen** ✅
   - ✅ Pipeline Header (name, description, status toggle)
   - ✅ Environment Sequence Editor (add/remove/reorder)
   - ✅ Stage Configuration Cards (collapsible)
   - ✅ Save/Cancel actions

3. **Pipeline Header** ✅
   - ✅ Name (required, validated)
   - ✅ Description (optional)
   - ✅ Status toggle (Active/Inactive)

4. **Environment Sequence Editor** ✅
   - ✅ Vertical list with reorder controls (up/down arrows)
   - ✅ Add environment dropdown
   - ✅ Remove environment
   - ✅ Visual path display (Dev → Staging → Prod)
   - ✅ Minimum 2 environments validation
   - ✅ No duplicates validation
   - ✅ Dynamic stage generation

5. **Stage Configuration** ✅
   - ✅ Stage Cards with expand/collapse
   - ✅ Title: `<Source> → <Target>`

6. **Stage Sections** ✅
   - ✅ **Basic Info** (read-only): Source/Target environments
   - ✅ **Gates**: All fields implemented
     - ✅ Require clean drift
     - ✅ Run pre-flight validation (with sub-options)
     - ✅ Credentials exist in target
     - ✅ Nodes supported in target
     - ✅ Webhooks available
     - ✅ Target environment healthy
     - ✅ Max allowed risk level dropdown
   - ✅ **Approvals**: All fields implemented
     - ✅ Require approval toggle
     - ✅ Approver role/group input
     - ✅ Required approvals (1 of N / All)
   - ✅ **Schedule Restrictions**: UI implemented
     - ✅ Restrict promotion times toggle
     - ✅ Allowed days multi-select
     - ✅ Start/End time inputs
   - ✅ **Policy Flags**: All fields implemented
     - ✅ Allow placeholder credentials
     - ✅ Allow overwriting hotfixes
     - ✅ Allow force promotion on conflicts

7. **Save & Validation** ✅
   - ✅ At least 2 environments validation
   - ✅ No duplicate environments validation
   - ✅ Pipeline metadata persistence
   - ✅ Ordered environment IDs persistence
   - ✅ Per-stage configuration persistence

### ⚠️ PARTIALLY COMPLETE

1. **Schedule Restrictions Enforcement** ⚠️
   - ✅ UI implemented
   - ❌ Backend enforcement logic not implemented
   - ❌ Time window checking not implemented

2. **Validation Rules** ⚠️
   - ✅ Basic validation implemented
   - ⚠️ Approval fields validation when toggle enabled (needs enhancement)
   - ⚠️ Schedule fields validation (needs enhancement)

### ❌ NOT IMPLEMENTED (Deferred per requirements)

- Advanced schedule behaviors (deferred)
- Conditional gates by tags/workflow attributes (deferred)
- Force-promotion overrides (deferred)
- Cross-pipeline analytics (deferred)

---

## reqs_pipeline_backend.md - Promotion Flow Requirements

### ✅ COMPLETE

1. **Promotion Entry** ✅
   - ✅ UI entry point (PromotionPage)
   - ✅ Pipeline selection
   - ✅ Active stage determination
   - ✅ Blocking if no pipeline exists

2. **Automatic Dev Backup** ✅
   - ✅ `create_snapshot()` method implemented
   - ✅ Exports all workflows from N8N
   - ✅ Writes to GitHub with commit
   - ✅ Saves snapshot ID
   - ✅ Fails promotion if backup fails

3. **Establish Comparison Baseline** ✅
   - ✅ GitHub → GitHub comparison
   - ✅ Source snapshot ID tracking
   - ✅ Target snapshot ID tracking

4. **Target Drift Detection** ✅
   - ✅ `check_drift()` method implemented
   - ✅ Compares runtime vs GitHub snapshot
   - ✅ Returns drift details
   - ⚠️ UI integration for "Sync to GitHub" action needs enhancement

5. **Compute Differences** ✅
   - ✅ `compare_workflows()` method implemented
   - ✅ Classifies workflows (New, Changed, Hotfix, Conflict, Unchanged)
   - ✅ Compares GitHub snapshots

6. **Workflow Selection UI** ✅
   - ✅ Table with workflow name, change type, status
   - ✅ Badges for change types
   - ✅ Selectable/non-selectable based on policy
   - ✅ Conflict explanation

7. **Hotfix & Conflict Policy Enforcement** ✅
   - ✅ Policy flag checking in UI
   - ✅ Workflow selection disabled if policy blocks
   - ✅ Overwrite confirmation (structure ready)

8. **Pre-Promotion Snapshot** ✅
   - ✅ `create_snapshot()` can be called for target
   - ✅ Rollback point creation

9. **Execute Promotion** ✅
   - ✅ `execute_promotion()` method structure
   - ✅ Loads from snapshot
   - ✅ Applies enabled/disabled state
   - ✅ Writes to target N8N
   - ✅ Records success/failure
   - ⚠️ Partial success handling needs testing

10. **Post-Promotion Snapshot** ✅
    - ✅ Structure in place
    - ✅ Can create post-promotion snapshot

### ⚠️ PARTIALLY COMPLETE

1. **Dependency Detection** ⚠️
   - ❌ Not implemented
   - ❌ Workflow dependency analysis missing
   - ❌ "Also include Workflow B" functionality missing
   - ❌ Dependency warning UI missing

2. **Credentials & Environment Placeholders** ⚠️
   - ✅ Policy flag exists
   - ⚠️ Placeholder creation logic incomplete
   - ⚠️ Credential checking incomplete
   - ⚠️ Workflow forced disabled logic incomplete

3. **Pre-flight Validation Summary** ⚠️
   - ✅ Gate results structure exists
   - ⚠️ Per-workflow validation incomplete
   - ⚠️ Global validation summary incomplete
   - ⚠️ "Promote now" disable logic needs enhancement

4. **Approvals** ⚠️
   - ✅ Structure exists
   - ✅ Approval request/response models
   - ⚠️ Full approval workflow incomplete
   - ⚠️ Approver notification missing
   - ⚠️ Approval UI for approvers incomplete
   - ⚠️ Rejection comment requirement not enforced

5. **Scheduling Enforcement** ⚠️
   - ✅ Schedule configuration exists
   - ❌ Time window checking not implemented
   - ❌ Promotion blocking based on schedule not implemented

6. **Result & Audit** ⚠️
   - ✅ Execution result structure exists
   - ⚠️ Comprehensive audit logging incomplete
   - ⚠️ Result UI incomplete (success/failure summary)
   - ⚠️ Links to view workflow/diff/rollback missing

### ❌ NOT IMPLEMENTED

1. **Dependency Detection** (Section 8)
   - Workflow dependency analysis
   - "Also include Workflow B" functionality
   - Dependency warnings

2. **Scheduling Enforcement** (Section 12)
   - Time window checking
   - Promotion blocking outside allowed times

3. **Full Approval Workflow** (Section 11)
   - Approver notification system
   - Approval UI for approvers
   - Multi-approver support (1 of N / All)

4. **Comprehensive Audit Logging** (Section 16)
   - Full audit record with all metadata
   - Audit log storage and retrieval

---

## Summary

### Pipeline UI (reqs_pipelines.md)
**Status: ~95% Complete**

- All MVP requirements implemented
- Schedule restrictions UI complete, but enforcement logic missing
- Validation could be more comprehensive

### Promotion Flow (reqs_pipeline_backend.md)
**Status: ~70% Complete**

**Core Flow: ✅ Complete**
- Entry, backup, comparison, drift detection, execution

**Missing Critical Features:**
1. Dependency detection (Section 8)
2. Scheduling enforcement (Section 12)
3. Full approval workflow (Section 11)
4. Comprehensive audit logging (Section 16)

**Partially Complete:**
1. Credential/placeholder handling (Section 9)
2. Pre-flight validation summary (Section 10)
3. Result & audit UI (Section 16)

---

## Recommendations

### High Priority (Blocking for Production)
1. **Implement Dependency Detection** - Required for safe promotions
2. **Complete Scheduling Enforcement** - Required per requirements
3. **Enhance Approval Workflow** - Critical for enterprise features

### Medium Priority
1. **Complete Credential/Placeholder Logic** - Important for workflow promotion
2. **Enhance Pre-flight Validation** - Better user experience
3. **Complete Audit Logging** - Important for compliance

### Low Priority
1. **Result UI Enhancements** - Nice to have
2. **Validation Improvements** - Polish

---

## Database Requirements

**Missing Database Tables:**
- `pipelines` table (may exist, needs verification)
- `promotions` table (for storing promotion records)
- `promotion_snapshots` table (for tracking snapshots)
- `promotion_approvals` table (for approval workflow)

**Note:** Database methods exist in `database.py` but tables may need to be created in Supabase.

