# Impersonation Security Quick Reference

**Last Verified**: 2026-01-08
**Status**: ✅ ALL SECURITY RULES VERIFIED

## Three Core Security Rules

### ✅ Rule 1: Platform Admins Cannot Impersonate Other Platform Admins

**Implementation**: `app/api/endpoints/platform_impersonation.py` (lines 48-60)

```python
if is_platform_admin(target_user_id):
    await create_audit_log(
        action_type="IMPERSONATION_BLOCKED",
        # ... logs the blocked attempt ...
    )
    raise HTTPException(status_code=400, detail="Cannot impersonate another Platform Admin")
```

**How to Test**:
```bash
# Attempt to impersonate another admin - should get HTTP 400
curl -X POST http://localhost:8000/api/v1/platform/impersonate \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"target_user_id": "<another-admin-id>"}'
```

---

### ✅ Rule 2: All Sessions Audited with Dual Attribution

**Implementation**: `app/services/audit_middleware.py` (lines 194-217)

Audit logs automatically capture:
- **actor_id** - Platform admin who initiated the action
- **actor_email** - Admin's email
- **impersonated_user_id** - User being impersonated
- **impersonated_user_email** - Impersonated user's email
- **impersonation_session_id** - Links to the session
- **tenant_id** - Effective tenant context

**How to Query**:
```sql
-- All actions by a specific admin while impersonating
SELECT
    timestamp,
    action,
    actor_email AS admin,
    impersonated_user_email AS target_user
FROM audit_logs
WHERE actor_id = '<admin-id>'
  AND impersonation_session_id IS NOT NULL
ORDER BY timestamp DESC;
```

---

### ✅ Rule 3: Blocked Attempts Are Logged

**Implementation**: `app/api/endpoints/platform_impersonation.py` (lines 49-59)

Every blocked impersonation attempt creates an audit log with:
- **action_type**: `IMPERSONATION_BLOCKED`
- **metadata.reason**: `target_is_platform_admin`
- **actor_id**: Who attempted the impersonation
- **resource_id**: Target user ID

**How to Query**:
```sql
-- All blocked impersonation attempts
SELECT
    timestamp,
    actor_email,
    metadata->>'target_user_id' AS attempted_target,
    metadata->>'reason' AS block_reason
FROM audit_logs
WHERE action_type = 'IMPERSONATION_BLOCKED'
ORDER BY timestamp DESC;
```

---

## Verification

### Run Security Verification Script

```bash
cd app-back
python scripts/verify_impersonation_security.py
```

**Expected Output**:
```
[PASS] Check 1/8: Admin-to-admin blocking logic implemented
[PASS] Check 2/8: Blocked attempts create audit log
[PASS] Check 3/8: Audit log schema supports dual attribution
[PASS] Check 4/8: Audit middleware logs impersonation context
[PASS] Check 5/8: IMPERSONATION_BLOCKED action type supported
[PASS] Check 6/8: Blocked attempts call create_audit_log
[PASS] Check 7/8: Impersonation sessions table exists
[PASS] Check 8/8: Audit log schema complete

Summary: Passed 8/8
[SUCCESS] All security checks passed!
```

### Run Security Tests

```bash
# Unit tests
pytest tests/security/test_impersonation_audit.py -v

# Expected: 27 passed
```

---

## Database Schema

### Required Tables

1. **platform_impersonation_sessions**
   - `id` (UUID, PK)
   - `actor_user_id` (UUID, FK to users)
   - `impersonated_user_id` (UUID, FK to users)
   - `impersonated_tenant_id` (UUID, FK to tenants)
   - `created_at` (timestamp)
   - `ended_at` (timestamp, nullable)

2. **audit_logs** (with impersonation columns)
   - `actor_id`, `actor_email`, `actor_name`
   - `impersonation_session_id` (UUID, nullable)
   - `impersonated_user_id` (UUID, nullable)
   - `impersonated_user_email` (VARCHAR, nullable)
   - `impersonated_tenant_id` (UUID, nullable)
   - `tenant_id` (effective context)

### Required Migrations

```bash
# Apply impersonation audit columns
alembic upgrade 20260108_audit_imp_cols

# Apply performance indexes
alembic upgrade 20260108_audit_imp_idx
```

---

## Common Queries

### Query 1: Complete Impersonation Session Audit Trail

```sql
SELECT
    pis.id AS session_id,
    pis.created_at AS session_start,
    pis.ended_at AS session_end,
    au.email AS admin_email,
    tu.email AS target_user_email,
    COUNT(al.id) AS actions_performed
FROM platform_impersonation_sessions pis
JOIN users au ON pis.actor_user_id = au.id
JOIN users tu ON pis.impersonated_user_id = tu.id
LEFT JOIN audit_logs al ON al.impersonation_session_id = pis.id
WHERE pis.id = '<session-id>'
GROUP BY pis.id, au.email, tu.email;
```

### Query 2: All Impersonation Activity by Admin

```sql
SELECT
    al.timestamp,
    al.action_type,
    al.action,
    al.impersonated_user_email,
    al.tenant_id
FROM audit_logs al
WHERE al.actor_id = '<admin-id>'
  AND al.impersonation_session_id IS NOT NULL
ORDER BY al.timestamp DESC;
```

### Query 3: Security Violations (Blocked Attempts)

```sql
SELECT
    al.timestamp,
    al.actor_email AS admin_who_tried,
    al.metadata->>'target_user_id' AS target_admin_id,
    al.ip_address,
    al.user_agent
FROM audit_logs al
WHERE al.action_type = 'IMPERSONATION_BLOCKED'
ORDER BY al.timestamp DESC;
```

---

## Compliance

This implementation supports compliance with:

- ✅ **SOC 2 Type II**: Complete audit trail of privileged access
- ✅ **GDPR**: Data access logging and attribution
- ✅ **HIPAA**: Administrative access controls and audit logs
- ✅ **ISO 27001**: Access control monitoring and review

---

## Support & Troubleshooting

### Issue: Audit logs missing impersonation context

**Solution**: Verify migrations are applied:
```bash
alembic current
# Should show: 20260108_audit_imp_idx
```

### Issue: Admin-to-admin impersonation not blocked

**Solution**: Check platform_admins table:
```sql
SELECT * FROM platform_admins WHERE user_id = '<user-id>';
```

### Issue: Performance degradation on audit queries

**Solution**: Verify indexes exist:
```sql
SELECT indexname FROM pg_indexes
WHERE tablename = 'audit_logs'
  AND indexname LIKE '%impersonation%';
```

---

## Reference Documentation

- **Full Verification Report**: `docs/IMPERSONATION_SECURITY_VERIFICATION.md`
- **MVP Readiness**: `mvp_readiness_pack/05_multitenancy_security_impersonation.md`
- **API Endpoint**: `app/api/endpoints/platform_impersonation.py`
- **Audit Middleware**: `app/services/audit_middleware.py`
- **Security Tests**: `tests/security/test_impersonation_audit.py`
