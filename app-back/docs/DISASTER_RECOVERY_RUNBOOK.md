# Disaster Recovery Runbook for Workflow Ops

**Last Updated:** 2026-01-08
**Version:** 1.0
**Owner:** Platform Operations Team
**Severity Classification:** CRITICAL - P1 Incident Response

---

## Table of Contents

1. [Overview](#overview)
2. [Emergency Contacts](#emergency-contacts)
3. [Pre-Incident Preparation](#pre-incident-preparation)
4. [Database Restore Procedures](#database-restore-procedures)
5. [Snapshot Restore Procedures](#snapshot-restore-procedures)
6. [Promotion Rollback Procedures](#promotion-rollback-procedures)
7. [Drift Incident Recovery](#drift-incident-recovery)
8. [Impersonation Safety & Audit Response](#impersonation-safety--audit-response)
9. [Post-Incident Activities](#post-incident-activities)
10. [Appendix: Common Error Codes](#appendix-common-error-codes)

---

## Overview

This runbook provides step-by-step procedures for recovering from critical failures in the Workflow Ops platform. The system is built on Supabase PostgreSQL with Git-backed snapshot storage and uses atomic rollback mechanisms for data integrity.

### System Architecture Overview

- **Database:** Supabase PostgreSQL with JWT authentication
- **Snapshots:** Git-backed storage in GitHub repository
- **Authentication:** SERVICE_KEY (backend) bypasses RLS, ANON_KEY (frontend) enforces RLS
- **Key Tables:** 76 total tables, 12 with RLS enabled
- **Execution Retention:** Default 7 days with automated cleanup

### Critical Invariants

- **T002:** Pre-promotion snapshots MUST be created before ANY target environment mutations
- **T003:** Promotions are atomic (all-or-nothing) with automatic rollback on any failure
- **T004:** Workflow comparisons use normalized content hashing (excludes metadata)
- **T005/T006:** Conflict policies enforce drift TTLs and block promotions on active drift

---

## Emergency Contacts

### Platform Team
- **On-Call Engineer:** [Contact via PagerDuty rotation]
- **Database Administrator:** [Contact info]
- **Security Team Lead:** [Contact info]
- **Engineering Manager:** [Contact info]

### External Services
- **Supabase Support:** https://supabase.com/support
- **GitHub Support:** (for snapshot repository issues)
- **PagerDuty Escalation Policy:** [Policy link]

---

## Pre-Incident Preparation

### Required Access & Credentials

1. **Database Access:**
   ```bash
   # Ensure you have Supabase credentials
   export SUPABASE_URL="your-project-url"
   export SUPABASE_SERVICE_KEY="your-service-key"
   ```

2. **Application Access:**
   - Platform admin credentials
   - SSH access to production servers
   - GitHub repository access (for snapshots)

3. **Monitoring Tools:**
   - Supabase Dashboard access
   - Application logs (CloudWatch/equivalent)
   - SSE event stream monitoring

### Health Check Commands

```bash
# Check API health
curl https://your-domain.com/health

# Check database connectivity
psql $DATABASE_URL -c "SELECT COUNT(*) FROM tenants;"

# Check background job service
curl https://your-domain.com/api/v1/background-jobs/status

# Check SSE streams
curl -N https://your-domain.com/api/v1/sse/deployments
```

---

## Database Restore Procedures

### Scenario 1: Database Corruption or Data Loss

**Severity:** P1 - CRITICAL
**RTO:** 4 hours
**RPO:** 1 hour (based on backup frequency)

#### Step 1: Assess the Damage

```bash
# Check table counts and recent modifications
psql $DATABASE_URL << EOF
SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del
FROM pg_stat_user_tables
ORDER BY n_tup_upd DESC
LIMIT 20;
EOF

# Identify affected tenants
psql $DATABASE_URL << EOF
SELECT t.id, t.name, COUNT(DISTINCT e.id) as env_count
FROM tenants t
LEFT JOIN environments e ON t.id = e.tenant_id
GROUP BY t.id, t.name;
EOF
```

#### Step 2: Initiate Point-in-Time Recovery (PITR)

Supabase provides automatic backups. Use the Supabase Dashboard for PITR:

1. Navigate to **Database** → **Backups** in Supabase Dashboard
2. Select the restore point (choose time before corruption)
3. Review restore preview and affected data
4. **CRITICAL:** Notify all users of incoming downtime
5. Execute restore operation

**CLI Alternative (if available):**
```bash
# Using Supabase CLI
supabase db restore --project-ref your-project-ref --backup-id backup-id
```

#### Step 3: Verify Database Integrity Post-Restore

```bash
# Check tenant isolation
psql $DATABASE_URL << EOF
SELECT tenant_id, COUNT(*)
FROM environments
GROUP BY tenant_id
HAVING COUNT(*) > 10; -- Identify anomalies
EOF

# Verify critical constraints
psql $DATABASE_URL << EOF
SELECT conname, contype, confupdtype, confdeltype
FROM pg_constraint
WHERE conrelid = 'tenants'::regclass;
EOF

# Check RLS policies are active
psql $DATABASE_URL << EOF
SELECT schemaname, tablename, policyname, cmd, qual
FROM pg_policies
WHERE tablename IN ('tenants', 'platform_admins', 'platform_impersonation_sessions');
EOF
```

#### Step 4: Resume Services

```bash
# Restart application servers
systemctl restart app-back

# Verify health endpoints
curl https://your-domain.com/health

# Check background job service recovery
curl https://your-domain.com/api/v1/background-jobs/status
```

#### Step 5: Data Validation

```bash
# Verify execution counts match expected ranges
psql $DATABASE_URL << EOF
SELECT
  DATE(started_at) as date,
  COUNT(*) as execution_count
FROM executions
WHERE started_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(started_at)
ORDER BY date DESC;
EOF

# Verify workflow_env_map consistency
psql $DATABASE_URL << EOF
SELECT
  wem.status,
  COUNT(*) as count
FROM workflow_env_map wem
GROUP BY wem.status;
EOF
```

---

### Scenario 2: Table-Level Data Corruption

**Severity:** P2 - HIGH
**RTO:** 2 hours
**RPO:** Based on last known good snapshot

#### Step 1: Identify Corrupted Tables

```bash
# Check for orphaned records
psql $DATABASE_URL << EOF
-- Find environments without valid tenants
SELECT e.id, e.name, e.tenant_id
FROM environments e
LEFT JOIN tenants t ON e.tenant_id = t.id
WHERE t.id IS NULL;

-- Find workflow_env_map entries without valid environments
SELECT wem.id, wem.environment_id
FROM workflow_env_map wem
LEFT JOIN environments e ON wem.environment_id = e.id
WHERE e.id IS NULL;
EOF
```

#### Step 2: Extract Clean Data from Snapshots

```bash
# Query recent snapshots
psql $DATABASE_URL << EOF
SELECT
  s.id,
  s.environment_id,
  s.snapshot_type,
  s.git_commit_sha,
  s.created_at,
  e.name as environment_name
FROM snapshots s
JOIN environments e ON s.environment_id = e.id
WHERE s.created_at > NOW() - INTERVAL '24 hours'
ORDER BY s.created_at DESC;
EOF

# Extract snapshot data (example for environment)
psql $DATABASE_URL << EOF
SELECT
  snapshot_type,
  workflows::jsonb as workflow_data,
  created_at
FROM snapshots
WHERE environment_id = 'target-environment-id'
  AND snapshot_type = 'pre_promotion'
ORDER BY created_at DESC
LIMIT 1;
EOF
```

#### Step 3: Reconstruct Data Using Restore API

Use the Restore API to rebuild from snapshots:

```bash
# Preview restore operation
curl -X GET "https://your-domain.com/api/v1/restore/{environment_id}/preview?snapshot_id={snapshot_id}" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json"

# Execute restore (creates/updates workflows)
curl -X POST "https://your-domain.com/api/v1/restore/{environment_id}/execute" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "snapshot_id": "snapshot-uuid",
    "dry_run": false,
    "overwrite_existing": true
  }'
```

#### Step 4: Verify Data Consistency

```bash
# Compare workflow counts before/after
psql $DATABASE_URL << EOF
SELECT
  e.name,
  COUNT(DISTINCT wem.canonical_workflow_id) as workflow_count
FROM environments e
LEFT JOIN workflow_env_map wem ON e.id = wem.environment_id
WHERE e.id = 'restored-environment-id'
GROUP BY e.name;
EOF
```

---

## Snapshot Restore Procedures

### Scenario 1: Environment Workflow Restore from Snapshot

**Use Case:** Accidental workflow deletions, corrupted workflows, or need to revert to known-good state

#### Step 1: List Available Snapshots

```bash
# List snapshots for environment
curl -X GET "https://your-domain.com/api/v1/snapshots?environment_id={environment_id}&limit=20" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" | jq '.snapshots[] | {id, type: .snapshot_type, created_at, git_sha: .git_commit_sha}'

# Filter by snapshot type
curl -X GET "https://your-domain.com/api/v1/snapshots?environment_id={env_id}&snapshot_type=manual_backup" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json"
```

#### Step 2: Preview Restore Impact

```bash
# Preview what will change
curl -X GET "https://your-domain.com/api/v1/restore/{environment_id}/preview?snapshot_id={snapshot_id}" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" | jq '{
    new_workflows: .preview.new_workflows | length,
    updated_workflows: .preview.updated_workflows | length,
    unchanged_workflows: .preview.unchanged_workflows | length
  }'
```

**Review Output:**
- `new_workflows`: Workflows that don't exist in target (will be created)
- `updated_workflows`: Workflows that differ (will be updated)
- `unchanged_workflows`: Workflows already matching snapshot

#### Step 3: Create Pre-Restore Backup

**CRITICAL:** Always create a snapshot before restore operation:

```bash
# Create manual backup snapshot
curl -X POST "https://your-domain.com/api/v1/snapshots" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "environment_id": "target-environment-id",
    "snapshot_type": "manual_backup",
    "description": "Pre-restore backup - $(date +%Y%m%d_%H%M%S)"
  }'
```

**Verify Backup Created:**
```bash
# Confirm snapshot exists with workflows payload
curl -X GET "https://your-domain.com/api/v1/snapshots/{new_snapshot_id}" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" | jq '.snapshot.workflows | length'
```

#### Step 4: Execute Restore

```bash
# Dry run first (no changes, validation only)
curl -X POST "https://your-domain.com/api/v1/restore/{environment_id}/execute" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "snapshot_id": "source-snapshot-id",
    "dry_run": true,
    "overwrite_existing": true
  }'

# If dry run succeeds, execute actual restore
curl -X POST "https://your-domain.com/api/v1/restore/{environment_id}/execute" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "snapshot_id": "source-snapshot-id",
    "dry_run": false,
    "overwrite_existing": true,
    "skip_validation": false
  }'
```

#### Step 5: Verify Restore Success

```bash
# Check workflow counts match snapshot
psql $DATABASE_URL << EOF
SELECT
  COUNT(*) as current_workflow_count
FROM workflow_env_map
WHERE environment_id = 'restored-environment-id'
  AND status != 'deleted';
EOF

# Compare with snapshot workflow count
curl -X GET "https://your-domain.com/api/v1/snapshots/{snapshot_id}" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" | jq '.snapshot.workflows | length'

# Verify workflow content hashes
psql $DATABASE_URL << EOF
SELECT
  canonical_workflow_id,
  git_content_hash,
  env_content_hash,
  CASE WHEN git_content_hash = env_content_hash THEN 'MATCH' ELSE 'DRIFT' END as status
FROM workflow_env_map
WHERE environment_id = 'restored-environment-id';
EOF
```

---

### Scenario 2: Git-Backed Snapshot Recovery

**Use Case:** Snapshot table corruption, need to recover from GitHub repository

#### Step 1: Access Git Repository

```bash
# Clone snapshots repository
git clone https://github.com/your-org/n8n-ops-snapshots.git
cd n8n-ops-snapshots

# List available snapshots
git log --oneline --all | head -20

# Find snapshot by commit SHA
git show {commit_sha}:snapshots/{environment_id}/{snapshot_id}.json
```

#### Step 2: Extract Snapshot Data

```bash
# Export snapshot to file
git show {commit_sha}:snapshots/{environment_id}/{snapshot_id}.json > /tmp/snapshot_recovery.json

# Validate JSON structure
jq '.workflows | length' /tmp/snapshot_recovery.json
jq '.snapshot_type, .created_at, .git_commit_sha' /tmp/snapshot_recovery.json
```

#### Step 3: Restore to Database

```bash
# Insert snapshot back into database
psql $DATABASE_URL << EOF
INSERT INTO snapshots (
  id,
  environment_id,
  snapshot_type,
  workflows,
  git_commit_sha,
  created_by,
  created_at
)
SELECT
  (data->>'id')::uuid,
  (data->>'environment_id')::uuid,
  (data->>'snapshot_type')::snapshot_type,
  data->'workflows',
  data->>'git_commit_sha',
  (data->>'created_by')::uuid,
  (data->>'created_at')::timestamptz
FROM (
  SELECT '$(cat /tmp/snapshot_recovery.json)'::jsonb as data
) subquery;
EOF
```

#### Step 4: Verify and Use Recovered Snapshot

```bash
# Confirm snapshot accessible via API
curl -X GET "https://your-domain.com/api/v1/snapshots/{snapshot_id}" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json"

# Now use standard restore procedure (see Scenario 1, Step 4)
```

---

## Promotion Rollback Procedures

### Scenario 1: Failed Promotion with Automatic Rollback

**Trigger:** Promotion fails during execution, automatic rollback initiated

#### Step 1: Identify Failed Promotion

```bash
# Query recent failed promotions
psql $DATABASE_URL << EOF
SELECT
  p.id,
  p.name,
  p.status,
  p.source_environment_id,
  p.target_environment_id,
  p.execution_result->'error' as error_details,
  p.execution_result->'rollback_result' as rollback_status,
  p.updated_at
FROM promotions p
WHERE p.status = 'FAILED'
  AND p.updated_at > NOW() - INTERVAL '1 hour'
ORDER BY p.updated_at DESC;
EOF
```

#### Step 2: Verify Automatic Rollback Completed

```bash
# Check rollback result in execution metadata
psql $DATABASE_URL << EOF
SELECT
  id,
  name,
  execution_result->'rollback_result'->>'status' as rollback_status,
  execution_result->'rollback_result'->>'workflows_rolled_back' as rollback_count,
  execution_result->'rollback_result'->>'snapshot_id' as snapshot_used
FROM promotions
WHERE id = 'failed-promotion-id';
EOF
```

**Expected Rollback Status:**
- `success`: All workflows restored from pre-promotion snapshot
- `partial`: Some workflows restored, manual intervention needed
- `failed`: Rollback failed, immediate action required

#### Step 3: Validate Target Environment State

```bash
# Compare workflow states with pre-promotion snapshot
curl -X GET "https://your-domain.com/api/v1/snapshots/{pre_promotion_snapshot_id}" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" > /tmp/pre_promotion.json

# Check current environment state
curl -X GET "https://your-domain.com/api/v1/environments/{target_environment_id}/workflows" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" > /tmp/current_state.json

# Compare counts
echo "Pre-promotion workflows: $(jq '.snapshot.workflows | length' /tmp/pre_promotion.json)"
echo "Current workflows: $(jq '.workflows | length' /tmp/current_state.json)"
```

#### Step 4: Manual Verification (if rollback status = partial/failed)

```bash
# Identify workflows that failed to rollback
psql $DATABASE_URL << EOF
SELECT
  wem.canonical_workflow_id,
  wem.env_workflow_id,
  wem.status,
  cw.name as workflow_name
FROM workflow_env_map wem
JOIN canonical_workflows cw ON wem.canonical_workflow_id = cw.id
WHERE wem.environment_id = 'target-environment-id'
  AND wem.updated_at > (
    SELECT created_at
    FROM promotions
    WHERE id = 'failed-promotion-id'
  );
EOF

# Check for 404 errors (workflow doesn't exist in target)
# These require manual creation from snapshot
```

#### Step 5: Manual Rollback (if automatic rollback failed)

```bash
# Force rollback using rollback API
curl -X POST "https://your-domain.com/api/v1/promotions/{promotion_id}/rollback" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "force": true,
    "snapshot_id": "pre-promotion-snapshot-id"
  }'
```

**Alternative: Direct Snapshot Restore**

If rollback API fails, use snapshot restore procedure (see [Snapshot Restore Procedures](#snapshot-restore-procedures)):

```bash
# Use pre-promotion snapshot for restore
curl -X POST "https://your-domain.com/api/v1/restore/{environment_id}/execute" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "snapshot_id": "pre-promotion-snapshot-id",
    "dry_run": false,
    "overwrite_existing": true
  }'
```

---

### Scenario 2: Manual Promotion Rollback (Regression Detected Post-Deployment)

**Use Case:** Promotion completed successfully but regression discovered hours/days later

#### Step 1: Identify Promotion to Rollback

```bash
# Find recent successful promotions for environment
psql $DATABASE_URL << EOF
SELECT
  p.id,
  p.name,
  p.status,
  p.created_at,
  p.execution_result->'snapshot_ids'->>'pre_promotion' as pre_snapshot_id,
  p.execution_result->'snapshot_ids'->>'post_promotion' as post_snapshot_id,
  se.name as source_env,
  te.name as target_env
FROM promotions p
JOIN environments se ON p.source_environment_id = se.id
JOIN environments te ON p.target_environment_id = te.id
WHERE p.target_environment_id = 'target-environment-id'
  AND p.status = 'COMPLETED'
  AND p.created_at > NOW() - INTERVAL '7 days'
ORDER BY p.created_at DESC;
EOF
```

#### Step 2: Create Current State Snapshot (Safety Net)

```bash
# Create snapshot of current state before rollback
curl -X POST "https://your-domain.com/api/v1/snapshots" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "environment_id": "target-environment-id",
    "snapshot_type": "manual_backup",
    "description": "Pre-rollback safety snapshot - Regression found in promotion {promotion_id}"
  }' | jq -r '.snapshot.id'

# Save snapshot ID for potential re-rollback
export SAFETY_SNAPSHOT_ID="returned-snapshot-id"
```

#### Step 3: Execute Rollback to Pre-Promotion State

```bash
# Get pre-promotion snapshot ID from promotion record
export PRE_PROMO_SNAPSHOT=$(psql $DATABASE_URL -t -c "SELECT execution_result->'snapshot_ids'->>'pre_promotion' FROM promotions WHERE id = 'promotion-id-to-rollback';" | tr -d ' ')

# Preview rollback impact
curl -X GET "https://your-domain.com/api/v1/restore/{environment_id}/preview?snapshot_id=${PRE_PROMO_SNAPSHOT}" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" | jq

# Execute rollback restore
curl -X POST "https://your-domain.com/api/v1/restore/{environment_id}/execute" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"snapshot_id\": \"${PRE_PROMO_SNAPSHOT}\",
    \"dry_run\": false,
    \"overwrite_existing\": true
  }"
```

#### Step 4: Verify Rollback Success

```bash
# Check workflow versions match pre-promotion state
psql $DATABASE_URL << EOF
SELECT
  cw.name,
  wem.git_content_hash as current_hash,
  wem.status,
  wem.updated_at
FROM workflow_env_map wem
JOIN canonical_workflows cw ON wem.canonical_workflow_id = cw.id
WHERE wem.environment_id = 'target-environment-id'
ORDER BY wem.updated_at DESC;
EOF

# Test critical workflows
curl -X POST "https://your-domain.com/api/v1/workflows/{workflow_id}/test" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json"
```

#### Step 5: Update Promotion Status and Document

```bash
# Mark promotion as rolled back in database
psql $DATABASE_URL << EOF
UPDATE promotions
SET
  status = 'FAILED',
  execution_result = jsonb_set(
    COALESCE(execution_result, '{}'::jsonb),
    '{manual_rollback}',
    jsonb_build_object(
      'rolled_back_at', NOW(),
      'reason', 'Regression detected in production',
      'rolled_back_by', 'ops-engineer-id',
      'safety_snapshot_id', '${SAFETY_SNAPSHOT_ID}'
    )
  )
WHERE id = 'promotion-id-to-rollback';
EOF

# Create incident record
curl -X POST "https://your-domain.com/api/v1/incidents" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "promotion_rollback",
    "severity": "high",
    "description": "Manual rollback executed due to regression",
    "promotion_id": "promotion-id-to-rollback",
    "resolution": "Rolled back to pre-promotion snapshot"
  }'
```

---

## Drift Incident Recovery

### Scenario 1: Critical Drift Detected in Production Environment

**Trigger:** Drift detection job identifies unauthorized changes in production

#### Step 1: Assess Drift Incident

```bash
# Query recent drift incidents
psql $DATABASE_URL << EOF
SELECT
  di.id,
  di.severity,
  di.incident_state,
  di.created_at,
  e.name as environment_name,
  cw.name as workflow_name,
  di.drift_snapshot->'diff_summary' as changes
FROM drift_incidents di
JOIN workflow_env_map wem ON di.workflow_env_map_id = wem.id
JOIN environments e ON wem.environment_id = e.id
JOIN canonical_workflows cw ON wem.canonical_workflow_id = cw.id
WHERE di.incident_state NOT IN ('CLOSED', 'RECONCILED')
  AND di.created_at > NOW() - INTERVAL '24 hours'
ORDER BY
  CASE di.severity
    WHEN 'critical' THEN 1
    WHEN 'high' THEN 2
    WHEN 'medium' THEN 3
    WHEN 'low' THEN 4
  END,
  di.created_at DESC;
EOF
```

#### Step 2: Review Drift Details

```bash
# Get detailed drift information
curl -X GET "https://your-domain.com/api/v1/incidents/{incident_id}" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" | jq '{
    severity: .incident.severity,
    state: .incident.incident_state,
    workflow: .incident.workflow_name,
    environment: .incident.environment_name,
    detected_at: .incident.created_at,
    ttl_expires_at: .incident.ttl_expires_at,
    changes: .incident.drift_snapshot.diff_summary
  }'

# View full drift diff
curl -X GET "https://your-domain.com/api/v1/incidents/{incident_id}" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" | jq '.incident.drift_snapshot.full_diff'
```

#### Step 3: Determine Recovery Strategy

**Option A: Reconcile (Accept Changes)**
- Use when drift is authorized (emergency hotfix, approved change)
- Updates canonical workflow to match environment state

**Option B: Stabilize (Revert to Canonical)**
- Use when drift is unauthorized
- Restores environment workflow to canonical Git state

**Option C: Acknowledge + Monitor**
- Use when investigation needed
- Marks incident as acknowledged, doesn't change workflows

#### Step 4: Execute Recovery Action

**Option A: Reconcile Drift (Accept Changes)**

```bash
# Reconcile workflow (updates canonical to match environment)
curl -X POST "https://your-domain.com/api/v1/incidents/{incident_id}/reconcile" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "comment": "Authorized emergency hotfix - reconciling to canonical",
    "update_git": true,
    "create_promotion_record": true
  }'

# Verify reconciliation
psql $DATABASE_URL << EOF
SELECT
  wem.git_content_hash,
  wem.env_content_hash,
  wem.status,
  di.incident_state
FROM drift_incidents di
JOIN workflow_env_map wem ON di.workflow_env_map_id = wem.id
WHERE di.id = 'incident-id';
-- Should show git_content_hash = env_content_hash after reconciliation
EOF
```

**Option B: Stabilize Drift (Revert to Canonical)**

```bash
# Create safety snapshot before stabilization
curl -X POST "https://your-domain.com/api/v1/snapshots" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "environment_id": "affected-environment-id",
    "snapshot_type": "manual_backup",
    "description": "Pre-stabilization snapshot - Incident {incident_id}"
  }'

# Stabilize workflow (reverts environment to canonical Git state)
curl -X POST "https://your-domain.com/api/v1/incidents/{incident_id}/stabilize" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "comment": "Reverting unauthorized changes",
    "force": false
  }'

# Verify stabilization
curl -X GET "https://your-domain.com/api/v1/incidents/{incident_id}" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" | jq '.incident.incident_state'
# Should return "STABILIZED"
```

**Option C: Acknowledge for Investigation**

```bash
# Acknowledge incident (marks as under investigation)
curl -X POST "https://your-domain.com/api/v1/incidents/{incident_id}/acknowledge" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "comment": "Under investigation - holding for review",
    "assigned_to": "engineer-user-id"
  }'
```

#### Step 5: Verify Recovery and Close Incident

```bash
# Check workflow state matches expected
psql $DATABASE_URL << EOF
SELECT
  cw.name,
  wem.git_content_hash,
  wem.env_content_hash,
  CASE
    WHEN wem.git_content_hash = wem.env_content_hash THEN 'NO_DRIFT'
    ELSE 'DRIFT_DETECTED'
  END as drift_status
FROM workflow_env_map wem
JOIN canonical_workflows cw ON wem.canonical_workflow_id = cw.id
WHERE wem.id = (
  SELECT workflow_env_map_id
  FROM drift_incidents
  WHERE id = 'incident-id'
);
EOF

# Close incident if resolved
curl -X POST "https://your-domain.com/api/v1/incidents/{incident_id}/close" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "comment": "Drift resolved via [reconciliation|stabilization]",
    "resolution_type": "reconciled"
  }'
```

---

### Scenario 2: Bulk Drift Recovery (Multiple Workflows)

**Use Case:** System-wide drift detected across multiple workflows/environments

#### Step 1: Identify All Active Drift Incidents

```bash
# Export all active incidents
psql $DATABASE_URL << EOF
COPY (
  SELECT
    di.id,
    e.name as environment,
    cw.name as workflow,
    di.severity,
    di.incident_state,
    di.created_at,
    di.ttl_expires_at
  FROM drift_incidents di
  JOIN workflow_env_map wem ON di.workflow_env_map_id = wem.id
  JOIN environments e ON wem.environment_id = e.id
  JOIN canonical_workflows cw ON wem.canonical_workflow_id = cw.id
  WHERE di.incident_state NOT IN ('CLOSED', 'RECONCILED')
  ORDER BY di.severity, di.created_at
) TO '/tmp/active_drift_incidents.csv' WITH CSV HEADER;
EOF
```

#### Step 2: Create Bulk Safety Snapshots

```bash
# Get unique environment IDs with drift
psql $DATABASE_URL -t -c "
  SELECT DISTINCT wem.environment_id
  FROM drift_incidents di
  JOIN workflow_env_map wem ON di.workflow_env_map_id = wem.id
  WHERE di.incident_state NOT IN ('CLOSED', 'RECONCILED')
" | while read -r env_id; do
  echo "Creating snapshot for environment: $env_id"

  curl -X POST "https://your-domain.com/api/v1/snapshots" \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
      \"environment_id\": \"${env_id}\",
      \"snapshot_type\": \"manual_backup\",
      \"description\": \"Bulk drift recovery safety snapshot - $(date)\"
    }"

  sleep 2 # Rate limiting
done
```

#### Step 3: Execute Bulk Stabilization

```bash
# Stabilize all critical severity incidents first
psql $DATABASE_URL -t -c "
  SELECT id
  FROM drift_incidents
  WHERE incident_state NOT IN ('CLOSED', 'RECONCILED')
    AND severity = 'critical'
" | while read -r incident_id; do
  echo "Stabilizing incident: $incident_id"

  curl -X POST "https://your-domain.com/api/v1/incidents/${incident_id}/stabilize" \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
      "comment": "Bulk stabilization - critical drift recovery",
      "force": false
    }'

  sleep 1 # Rate limiting
done

# Repeat for high, medium, low severities
```

#### Step 4: Verify Bulk Recovery Status

```bash
# Check recovery progress
psql $DATABASE_URL << EOF
SELECT
  di.severity,
  di.incident_state,
  COUNT(*) as count
FROM drift_incidents di
WHERE di.created_at > NOW() - INTERVAL '1 day'
GROUP BY di.severity, di.incident_state
ORDER BY
  CASE di.severity
    WHEN 'critical' THEN 1
    WHEN 'high' THEN 2
    WHEN 'medium' THEN 3
    WHEN 'low' THEN 4
  END,
  di.incident_state;
EOF

# Identify any failed stabilizations
psql $DATABASE_URL << EOF
SELECT
  di.id,
  e.name as environment,
  cw.name as workflow,
  di.incident_state
FROM drift_incidents di
JOIN workflow_env_map wem ON di.workflow_env_map_id = wem.id
JOIN environments e ON wem.environment_id = e.id
JOIN canonical_workflows cw ON wem.canonical_workflow_id = cw.id
WHERE di.incident_state = 'ACKNOWLEDGED'
  AND di.updated_at < NOW() - INTERVAL '1 hour';
-- These may require manual intervention
EOF
```

---

### Scenario 3: Drift TTL Enforcement (Blocking Promotions)

**Trigger:** Promotion blocked due to active drift with expired TTL

#### Step 1: Identify Blocking Drift

```bash
# Find drift incidents blocking promotions
psql $DATABASE_URL << EOF
SELECT
  di.id,
  di.severity,
  di.ttl_expires_at,
  NOW() - di.ttl_expires_at as overdue_duration,
  e.name as environment,
  cw.name as workflow,
  dp.enforce_ttl,
  dp.block_on_active_drift
FROM drift_incidents di
JOIN workflow_env_map wem ON di.workflow_env_map_id = wem.id
JOIN environments e ON wem.environment_id = e.id
JOIN canonical_workflows cw ON wem.canonical_workflow_id = cw.id
JOIN drift_policies dp ON e.tenant_id = dp.tenant_id
WHERE di.incident_state NOT IN ('CLOSED', 'RECONCILED')
  AND di.ttl_expires_at < NOW()
  AND dp.enforce_ttl = true;
EOF
```

#### Step 2: Resolve Blocking Incidents

**Fast Resolution Path (if drift is acceptable):**

```bash
# Reconcile expired drift to unblock promotions
curl -X POST "https://your-domain.com/api/v1/incidents/{incident_id}/reconcile" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "comment": "TTL expired - reconciling to unblock promotion",
    "update_git": true
  }'
```

**Strict Resolution Path (if drift must be reverted):**

```bash
# Stabilize to canonical state
curl -X POST "https://your-domain.com/api/v1/incidents/{incident_id}/stabilize" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "comment": "TTL expired - reverting to canonical",
    "force": false
  }'
```

#### Step 3: Retry Promotion

```bash
# Verify no blocking drift remains
curl -X GET "https://your-domain.com/api/v1/promotions/compare?source_env_id={src}&target_env_id={tgt}" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" | jq '.blocking_drift_incidents'

# Execute promotion
curl -X POST "https://your-domain.com/api/v1/promotions/execute/{promotion_id}" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json"
```

---

## Impersonation Safety & Audit Response

### Security Model Overview

**Platform Admin Impersonation** allows platform administrators to access tenant contexts for support purposes. Critical safety guardrails:

1. **Cannot impersonate other platform admins** (prevents privilege escalation)
2. **No nested impersonation** (one active session per actor)
3. **Full audit trail** (all actions logged with actor + impersonated context)
4. **Write operation logging** (middleware captures all mutations during impersonation)

---

### Scenario 1: Suspicious Impersonation Activity Detected

**Trigger:** Security alert for unusual impersonation session

#### Step 1: Query Active Impersonation Sessions

```bash
# List all active impersonation sessions
psql $DATABASE_URL << EOF
SELECT
  pis.id as session_id,
  pis.actor_user_id,
  au.email as actor_email,
  pis.impersonated_user_id,
  iu.email as impersonated_email,
  pis.impersonated_tenant_id,
  t.name as tenant_name,
  pis.started_at,
  pis.ended_at,
  pis.ip_address,
  pis.user_agent
FROM platform_impersonation_sessions pis
JOIN users au ON pis.actor_user_id = au.id
JOIN users iu ON pis.impersonated_user_id = iu.id
JOIN tenants t ON pis.impersonated_tenant_id = t.id
WHERE pis.ended_at IS NULL
ORDER BY pis.started_at DESC;
EOF
```

#### Step 2: Review Impersonation Audit Trail

```bash
# Query all actions performed during suspicious session
psql $DATABASE_URL << EOF
SELECT
  al.id,
  al.action,
  al.resource_type,
  al.resource_id,
  al.details,
  al.created_at,
  al.ip_address
FROM audit_logs al
WHERE al.actor_user_id = 'suspicious-actor-id'
  AND al.impersonated_user_id IS NOT NULL
  AND al.created_at > 'session-start-time'
ORDER BY al.created_at DESC;
EOF

# Filter write operations during impersonation
psql $DATABASE_URL << EOF
SELECT
  al.action,
  al.resource_type,
  al.details->'request_body' as payload,
  al.details->'response_status' as status,
  al.created_at
FROM audit_logs al
WHERE al.actor_user_id = 'suspicious-actor-id'
  AND al.impersonated_user_id IS NOT NULL
  AND al.action IN ('CREATE', 'UPDATE', 'DELETE')
ORDER BY al.created_at DESC;
EOF
```

#### Step 3: Terminate Active Session Immediately

```bash
# Force end impersonation session
curl -X POST "https://your-domain.com/api/v1/platform/impersonate/stop" \
  -H "Authorization: Bearer ${PLATFORM_ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "suspicious-session-id",
    "force": true,
    "reason": "Security incident - unauthorized activity detected"
  }'

# Verify session terminated
psql $DATABASE_URL << EOF
SELECT
  id,
  ended_at,
  EXTRACT(EPOCH FROM (ended_at - started_at)) as duration_seconds
FROM platform_impersonation_sessions
WHERE id = 'suspicious-session-id';
EOF
```

#### Step 4: Assess Impact and Damage

```bash
# Identify all resources modified during session
psql $DATABASE_URL << EOF
SELECT
  al.resource_type,
  al.action,
  COUNT(*) as modification_count,
  array_agg(DISTINCT al.resource_id) as affected_resources
FROM audit_logs al
WHERE al.actor_user_id = 'suspicious-actor-id'
  AND al.impersonated_user_id = 'impersonated-user-id'
  AND al.created_at BETWEEN 'session-start' AND 'session-end'
  AND al.action IN ('CREATE', 'UPDATE', 'DELETE')
GROUP BY al.resource_type, al.action;
EOF
```

**Critical Resources to Check:**
- `workflows`: Unauthorized workflow modifications
- `promotions`: Unapproved promotions executed
- `environments`: Environment configuration changes
- `users`: User permission modifications
- `tenants`: Tenant settings changes

#### Step 5: Rollback Unauthorized Changes

**For Workflow Changes:**

```bash
# Create snapshot of current (compromised) state
curl -X POST "https://your-domain.com/api/v1/snapshots" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "environment_id": "affected-environment-id",
    "snapshot_type": "manual_backup",
    "description": "Compromised state snapshot - Security incident"
  }'

# Find last good snapshot before impersonation session
psql $DATABASE_URL << EOF
SELECT
  s.id,
  s.snapshot_type,
  s.created_at,
  e.name as environment_name
FROM snapshots s
JOIN environments e ON s.environment_id = e.id
WHERE s.environment_id = 'affected-environment-id'
  AND s.created_at < 'impersonation-session-start'
ORDER BY s.created_at DESC
LIMIT 5;
EOF

# Restore to last good snapshot
curl -X POST "https://your-domain.com/api/v1/restore/{environment_id}/execute" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "snapshot_id": "last-good-snapshot-id",
    "dry_run": false,
    "overwrite_existing": true
  }'
```

**For Database Changes:**

```bash
# Review and manually revert using audit log details
psql $DATABASE_URL << EOF
-- Example: Revert user permission changes
UPDATE users
SET role = (
  SELECT details->'previous_value'->>'role'
  FROM audit_logs
  WHERE resource_type = 'users'
    AND resource_id = users.id
    AND action = 'UPDATE'
    AND actor_user_id = 'suspicious-actor-id'
  ORDER BY created_at DESC
  LIMIT 1
)
WHERE id IN (
  SELECT resource_id::uuid
  FROM audit_logs
  WHERE resource_type = 'users'
    AND action = 'UPDATE'
    AND actor_user_id = 'suspicious-actor-id'
);
EOF
```

#### Step 6: Revoke Platform Admin Access

```bash
# Remove platform admin privileges
curl -X DELETE "https://your-domain.com/api/v1/platform/admins/{suspicious-user-id}" \
  -H "Authorization: Bearer ${SUPER_ADMIN_TOKEN}" \
  -H "Content-Type: application/json"

# Verify removal
psql $DATABASE_URL << EOF
SELECT user_id, created_at
FROM platform_admins
WHERE user_id = 'suspicious-user-id';
-- Should return no rows
EOF

# Invalidate all sessions for user
psql $DATABASE_URL << EOF
-- Implementation depends on session storage (JWT/Redis/DB)
-- Example for DB-stored sessions:
DELETE FROM user_sessions WHERE user_id = 'suspicious-user-id';
EOF
```

---

### Scenario 2: Impersonation Safety Guardrail Violation

**Trigger:** Attempt to impersonate another platform admin (blocked by system)

#### Step 1: Identify Blocked Attempt

```bash
# Query IMPERSONATION_BLOCKED audit logs
psql $DATABASE_URL << EOF
SELECT
  al.id,
  al.actor_user_id,
  au.email as actor_email,
  al.details->'target_user_id' as attempted_target,
  al.details->'reason' as block_reason,
  al.created_at,
  al.ip_address
FROM audit_logs al
JOIN users au ON al.actor_user_id = au.id
WHERE al.action = 'IMPERSONATION_BLOCKED'
ORDER BY al.created_at DESC
LIMIT 20;
EOF
```

#### Step 2: Verify Platform Admin Status of Target

```bash
# Confirm target was indeed a platform admin (guardrail working correctly)
psql $DATABASE_URL << EOF
SELECT
  u.id,
  u.email,
  pa.created_at as platform_admin_since
FROM users u
JOIN platform_admins pa ON u.id = pa.user_id
WHERE u.id = 'attempted-target-user-id';
EOF
```

#### Step 3: Investigate Actor Intent

**Legitimate Scenario:**
- Actor didn't realize target was platform admin
- Misunderstanding of system capabilities

**Malicious Scenario:**
- Privilege escalation attempt
- Compromised account

**Investigation Steps:**

```bash
# Check actor's recent impersonation history
psql $DATABASE_URL << EOF
SELECT
  pis.impersonated_user_id,
  iu.email as impersonated_email,
  pis.impersonated_tenant_id,
  t.name as tenant_name,
  pis.started_at,
  pis.ended_at
FROM platform_impersonation_sessions pis
JOIN users iu ON pis.impersonated_user_id = iu.id
JOIN tenants t ON pis.impersonated_tenant_id = t.id
WHERE pis.actor_user_id = 'actor-user-id'
ORDER BY pis.started_at DESC
LIMIT 10;
EOF

# Check for multiple blocked attempts (indicator of malicious intent)
psql $DATABASE_URL << EOF
SELECT COUNT(*) as blocked_attempts
FROM audit_logs
WHERE action = 'IMPERSONATION_BLOCKED'
  AND actor_user_id = 'actor-user-id'
  AND created_at > NOW() - INTERVAL '24 hours';
EOF
```

#### Step 4: Take Appropriate Action

**If Legitimate:**
- Document incident
- Provide training to actor on impersonation guardrails

**If Suspicious:**
- Follow [Scenario 1: Suspicious Impersonation Activity](#scenario-1-suspicious-impersonation-activity-detected)
- Consider revoking platform admin access
- Escalate to security team

---

### Scenario 3: Impersonation Audit Compliance Report

**Use Case:** Generate compliance report for all impersonation activity

#### Generate Comprehensive Audit Report

```bash
# Export all impersonation sessions (last 90 days)
psql $DATABASE_URL << EOF
COPY (
  SELECT
    pis.id as session_id,
    au.email as actor_email,
    au.name as actor_name,
    iu.email as impersonated_email,
    iu.name as impersonated_name,
    t.name as tenant_name,
    pis.started_at,
    pis.ended_at,
    EXTRACT(EPOCH FROM (COALESCE(pis.ended_at, NOW()) - pis.started_at))/60 as duration_minutes,
    pis.ip_address,
    pis.user_agent,
    (
      SELECT COUNT(*)
      FROM audit_logs al
      WHERE al.actor_user_id = pis.actor_user_id
        AND al.impersonated_user_id = pis.impersonated_user_id
        AND al.created_at BETWEEN pis.started_at AND COALESCE(pis.ended_at, NOW())
        AND al.action IN ('CREATE', 'UPDATE', 'DELETE')
    ) as write_operations_count
  FROM platform_impersonation_sessions pis
  JOIN users au ON pis.actor_user_id = au.id
  JOIN users iu ON pis.impersonated_user_id = iu.id
  JOIN tenants t ON pis.impersonated_tenant_id = t.id
  WHERE pis.started_at > NOW() - INTERVAL '90 days'
  ORDER BY pis.started_at DESC
) TO '/tmp/impersonation_audit_report.csv' WITH CSV HEADER;
EOF

# Generate summary statistics
psql $DATABASE_URL << EOF
SELECT
  au.email as actor,
  COUNT(DISTINCT pis.id) as total_sessions,
  COUNT(DISTINCT pis.impersonated_tenant_id) as tenants_accessed,
  SUM(EXTRACT(EPOCH FROM (COALESCE(pis.ended_at, NOW()) - pis.started_at))/3600) as total_hours,
  MAX(pis.started_at) as last_session
FROM platform_impersonation_sessions pis
JOIN users au ON pis.actor_user_id = au.id
WHERE pis.started_at > NOW() - INTERVAL '90 days'
GROUP BY au.email
ORDER BY total_sessions DESC;
EOF
```

---

## Post-Incident Activities

### Incident Closure Checklist

After resolving any disaster recovery scenario, complete the following:

#### 1. Verify System Health

```bash
# Run comprehensive health checks
curl https://your-domain.com/health | jq

# Check all critical services
for service in "promotions" "drift_detection" "snapshots" "restore"; do
  echo "Checking $service..."
  curl -X GET "https://your-domain.com/api/v1/${service}/healthz" \
    -H "Authorization: Bearer ${API_TOKEN}"
done

# Verify database integrity
psql $DATABASE_URL << EOF
-- Check for orphaned records
SELECT 'Orphaned environments' as check_type, COUNT(*) as count
FROM environments e LEFT JOIN tenants t ON e.tenant_id = t.id WHERE t.id IS NULL
UNION ALL
SELECT 'Orphaned workflow_env_map' as check_type, COUNT(*) as count
FROM workflow_env_map wem LEFT JOIN environments e ON wem.environment_id = e.id WHERE e.id IS NULL
UNION ALL
SELECT 'Active impersonation sessions' as check_type, COUNT(*) as count
FROM platform_impersonation_sessions WHERE ended_at IS NULL;
EOF
```

#### 2. Create Post-Recovery Snapshot

```bash
# Snapshot all affected environments
for env_id in "${AFFECTED_ENV_IDS[@]}"; do
  curl -X POST "https://your-domain.com/api/v1/snapshots" \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
      \"environment_id\": \"${env_id}\",
      \"snapshot_type\": \"manual_backup\",
      \"description\": \"Post-recovery snapshot - Incident ${INCIDENT_ID}\"
    }"
done
```

#### 3. Document Incident

Create incident report with:
- **Incident ID and Severity**
- **Detection Time and Resolution Time** (calculate RTO achieved)
- **Root Cause Analysis**
- **Recovery Actions Taken** (reference this runbook procedures)
- **Data Loss Assessment** (calculate RPO achieved)
- **Affected Tenants/Environments**
- **Lessons Learned**

#### 4. Update Monitoring and Alerts

```bash
# Create alert rules for similar incidents
curl -X POST "https://your-domain.com/api/v1/alert-rules" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "High Drift Incident Rate",
    "condition": "drift_incidents_per_hour > 10",
    "severity": "high",
    "notification_channels": ["ops-slack", "pagerduty"]
  }'
```

#### 5. Communicate with Stakeholders

**Internal Communication:**
- Engineering team debrief
- Post-mortem meeting scheduling
- Knowledge base article creation

**External Communication (if customer-facing):**
- Status page update
- Customer notification email
- Support ticket responses

#### 6. Review and Update Runbook

Based on incident experience:
- Add new scenarios encountered
- Update timings (RTO/RPO)
- Document any manual workarounds used
- Add automation opportunities identified

---

## Appendix: Common Error Codes

### Promotion Errors

| Error Code | Description | Recovery Procedure |
|------------|-------------|-------------------|
| `PROMO_001` | Pre-promotion snapshot creation failed | Check Git repository connectivity, retry with manual snapshot |
| `PROMO_002` | Workflow update failed during promotion | Automatic rollback triggered, verify rollback success |
| `PROMO_003` | Conflict policy violation (active drift blocks promotion) | Resolve drift incidents, retry promotion |
| `PROMO_004` | Target environment locked (concurrent promotion) | Wait for existing promotion to complete or abort |
| `PROMO_005` | Rollback failed - partial state | Execute manual snapshot restore to pre-promotion state |

### Snapshot/Restore Errors

| Error Code | Description | Recovery Procedure |
|------------|-------------|-------------------|
| `SNAP_001` | Snapshot creation failed (Git push error) | Check GitHub credentials and repository permissions |
| `SNAP_002` | Snapshot retrieval failed (missing from Git) | Use database snapshot table fallback, reconstruct from audit logs |
| `REST_001` | Restore preview failed (workflow not found) | Verify snapshot integrity, check environment connectivity |
| `REST_002` | Restore execution failed (API timeout) | Retry with smaller batch size, check n8n API health |
| `REST_003` | Workflow create/update failed (404 in target) | Use fallback: create instead of update for missing workflows |

### Drift Detection Errors

| Error Code | Description | Recovery Procedure |
|------------|-------------|-------------------|
| `DRIFT_001` | Drift detection failed (environment unreachable) | Check environment credentials and connectivity |
| `DRIFT_002` | Stabilization failed (workflow update error) | Retry stabilization with force flag, check n8n API logs |
| `DRIFT_003` | Reconciliation failed (Git commit error) | Verify Git credentials, manually commit workflow changes |
| `DRIFT_004` | TTL expired but drift unresolvable | Override policy temporarily or force reconciliation |

### Impersonation Errors

| Error Code | Description | Recovery Procedure |
|------------|-------------|-------------------|
| `IMP_001` | Impersonation blocked (target is platform admin) | Expected behavior - document attempt, investigate if repeated |
| `IMP_002` | Nested impersonation prevented | End current session first, then start new session |
| `IMP_003` | Session not found (expired or invalid) | Re-authenticate and create new session |
| `IMP_004` | Unauthorized audit log access | Verify user has platform admin privileges |

### Database Errors

| Error Code | Description | Recovery Procedure |
|------------|-------------|-------------------|
| `DB_001` | Tenant isolation violation detected | Review tenant_id WHERE clause in query, verify RLS policies |
| `DB_002` | Foreign key constraint violation | Check for orphaned records, restore referential integrity |
| `DB_003` | Unique constraint violation | Identify duplicate records, resolve conflicts manually |
| `DB_004` | Connection pool exhausted | Scale up database connections or restart application |

---

## Quick Reference: Emergency Commands

### Stop All Background Jobs

```bash
# Mark all running jobs as failed (emergency stop)
psql $DATABASE_URL << EOF
UPDATE background_jobs
SET status = 'FAILED',
    error_message = 'Emergency stop executed',
    ended_at = NOW()
WHERE status = 'RUNNING';
EOF
```

### Disable Drift Detection System-Wide

```bash
# Stop all drift schedulers
curl -X POST "https://your-domain.com/api/v1/drift/schedulers/stop-all" \
  -H "Authorization: Bearer ${PLATFORM_ADMIN_TOKEN}" \
  -H "Content-Type: application/json"

# Verify all schedulers stopped
psql $DATABASE_URL << EOF
SELECT tenant_id, is_running
FROM drift_schedulers;
EOF
```

### Force End All Impersonation Sessions

```bash
# Terminate all active sessions
psql $DATABASE_URL << EOF
UPDATE platform_impersonation_sessions
SET ended_at = NOW()
WHERE ended_at IS NULL;
EOF
```

### Emergency Database Backup

```bash
# Create full database dump
pg_dump $DATABASE_URL > /tmp/emergency_backup_$(date +%Y%m%d_%H%M%S).sql

# Create compressed backup
pg_dump $DATABASE_URL | gzip > /tmp/emergency_backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Upload to safe location
aws s3 cp /tmp/emergency_backup_*.sql.gz s3://your-backup-bucket/emergency/
```

### Check System Resource Usage

```bash
# Database connections
psql $DATABASE_URL << EOF
SELECT
  count(*) as total_connections,
  count(*) FILTER (WHERE state = 'active') as active_connections,
  count(*) FILTER (WHERE state = 'idle') as idle_connections
FROM pg_stat_activity;
EOF

# Table sizes
psql $DATABASE_URL << EOF
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
EOF
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-08 | Platform Ops Team | Initial runbook creation based on MVP system architecture |

---

## Support Resources

- **Internal Documentation:** `/docs/mvp-readiness/` directory
- **RLS Policies:** `/docs/security/RLS_POLICIES.md`
- **API Reference:** `/docs/API_ERROR_REFERENCE.md`
- **Security Audit:** `/docs/SECURITY_AUDIT_RESULTS.md`
- **Tenant Isolation:** `/docs/TENANT_ISOLATION_SCANNER.md`

**For emergency support, contact the Platform On-Call Engineer via PagerDuty.**

---

*This runbook is a living document. Update after each incident with lessons learned and improved procedures.*
