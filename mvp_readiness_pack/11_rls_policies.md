# 11 - RLS Policies

**Generated:** 2026-01-08
**Evidence-Based:** Repository scan only

## RLS Documentation Status

**Status:** ✅ **RLS EXPORT COMPLETED** (2026-01-08)

**Evidence:** `app-back/docs/security/` directory contains 7 RLS-related documentation files:

1. **RLS_POLICIES.md** (1416 lines)
   - Complete inventory of all 76 tables
   - Documents 12 tables with RLS enabled (15.8%)
   - Documents 64 tables without RLS (84.2%)
   - Policy patterns and recommendations
   - Migration plan

2. **RLS_VERIFICATION.md**
   - Verification procedures
   - How to check RLS status

3. **RLS_CHANGE_CHECKLIST.md**
   - Developer guide for adding/modifying RLS policies

4. **RLS_SUMMARY.md**
   - Executive summary

5. **IMPLEMENTATION_REPORT.md**
   - Implementation status report

6. **QUICK_START.md**
   - Quick reference

7. **README.md**
   - Overview of security documentation

## Current RLS Posture

**Evidence:** `app-back/docs/security/RLS_POLICIES.md:5-6`

- **Total Tables:** 76
- **Tables with RLS:** 12 (15.8%)
- **Tables without RLS:** 64 (84.2%)

### Backend Service Key Usage

**Evidence:** `app-back/app/core/config.py:13` - `SUPABASE_SERVICE_KEY` defined

**Evidence:** `app-back/docs/security/RLS_POLICIES.md:55` - "Backend uses SERVICE_KEY which bypasses RLS"

**Implication:** 
- Backend queries bypass RLS policies entirely
- Application-layer tenant isolation is the primary enforcement mechanism
- RLS serves as a secondary defense layer for frontend direct access

**Architecture:**
```
Frontend (ANON_KEY) → RLS enforced (12 tables) / Not enforced (64 tables)
Backend (SERVICE_KEY) → RLS bypassed (all tables)
```

## Tables WITH RLS Enabled

**Evidence:** `app-back/docs/security/RLS_POLICIES.md:78-1416`

1. `canonical_workflow_git_state` - Tenant isolation policy
2. `canonical_workflows` - Tenant isolation policy
3. `workflow_mappings` - Tenant isolation policy
4. `drift_incidents` - Tenant isolation policy
5. `drift_policies` - Tenant isolation policy
6. `drift_approvals` - Tenant isolation policy
7. `snapshots` - Tenant isolation policy
8. `deployments` - Tenant isolation policy
9. `deployment_workflows` - Tenant isolation policy
10. `promotions` - Tenant isolation policy
11. `pipelines` - Tenant isolation policy
12. `background_jobs` - Tenant isolation policy

**Policy Pattern:** All use `tenant_id = (current_setting('app.tenant_id', true))::uuid`

## Tables WITHOUT RLS (Critical Gaps)

**Evidence:** `app-back/docs/security/RLS_POLICIES.md` - Sections for each category

### Core Tables (No RLS)
- `tenants` - **CRITICAL**: Core tenant table
- `users` - **CRITICAL**: User accounts
- `environments` - **CRITICAL**: Environment configurations

### Workflow Tables (No RLS)
- `workflows` - Workflow definitions
- `workflow_tags` - Tag associations

### Operations Tables (No RLS)
- `executions` - Execution history
- `audit_logs` - Audit trail

### Credential Tables (No RLS)
- `logical_credentials` - Logical credential definitions
- `credential_mappings` - Environment credential mappings

### Billing Tables (No RLS)
- `tenant_provider_subscriptions` - Active subscriptions
- `subscriptions` - Legacy subscription table
- `payment_history` - Payment records

### Platform Admin Tables (No RLS)
- `platform_admins` - Platform admin designations
- `platform_impersonation_sessions` - Impersonation sessions

**Note:** Platform admin tables may intentionally lack RLS as they are cross-tenant by design.

## RLS Policy Patterns

**Evidence:** `app-back/docs/security/RLS_POLICIES.md` - Policy examples

**Standard Pattern:**
```sql
CREATE POLICY "{table}_tenant_isolation" ON {table}
FOR ALL
USING (tenant_id = (current_setting('app.tenant_id', true))::uuid)
WITH CHECK (tenant_id = (current_setting('app.tenant_id', true))::uuid);
```

**Requires:** `app.tenant_id` session variable to be set (typically by application layer)

## Recommendations

**Evidence:** `app-back/docs/security/RLS_POLICIES.md` - Migration plan section

1. **Priority 1:** Enable RLS on `tenants`, `users`, `environments` (core tables)
2. **Priority 2:** Enable RLS on `workflows`, `executions`, `audit_logs` (high-volume tables)
3. **Priority 3:** Enable RLS on billing tables (sensitive financial data)

**Risk Assessment:**
- **Current Risk:** LOW (backend bypasses RLS via SERVICE_KEY)
- **Future Risk:** HIGH if frontend switches to direct Supabase access or SERVICE_KEY is compromised
- **Compliance Risk:** MEDIUM (RLS considered best practice for SaaS multi-tenancy)

## Verification

**Evidence:** `app-back/docs/security/RLS_VERIFICATION.md`

To verify RLS status:
```sql
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;
```

To list policies:
```sql
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual 
FROM pg_policies 
WHERE schemaname = 'public';
```

## Unknowns

- **RLS enforcement in production:** Unknown if frontend uses ANON_KEY or SERVICE_KEY
- **Session variable setting:** Unknown if `app.tenant_id` is set by application layer or middleware
- **RLS testing:** Unknown if RLS policies are tested in test suite

**Search Locations:**
- `app-back/app/services/database.py` - Check if session variables are set
- `app-front/src/lib/supabase.ts` - Check which key is used
- `app-back/tests/` - Search for RLS-related tests

