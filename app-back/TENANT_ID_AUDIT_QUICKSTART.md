# Tenant ID Source Audit - Quick Start Guide

## Purpose
Verify that `tenant_id` is never sourced from request path, query, or body parameters without proper platform admin authorization.

## Quick Check

Run the verification script:

```bash
# Quick summary
python scripts/verify_tenant_id_sources.py --summary

# Full report
python scripts/verify_tenant_id_sources.py

# Export JSON
python scripts/verify_tenant_id_sources.py --json results.json
```

## Exit Codes

- **0** = PASSED - No security violations found
- **1** = FAILED - Security violations detected
- **2** = ERROR - Script execution error

## Current Status

✅ **PASSED** - As of 2026-01-08

- **Total Endpoints:** 346
- **Endpoints with tenant_id in path:** 35
- **Legitimate (Platform Admin):** 35
- **VIOLATIONS:** 0

## What This Checks

### ❌ Unsafe Patterns (Violations)
```python
# BAD: tenant_id in path without admin auth
@router.get("/resources/{tenant_id}")
async def get_resource(tenant_id: str, user: dict = Depends(get_current_user)):
    # This allows users to access other tenants' data!
    pass
```

### ✅ Safe Patterns

**Option 1: Platform Admin Endpoints**
```python
# GOOD: tenant_id with platform admin authorization
@router.get("/platform/admin/tenants/{tenant_id}")
async def get_tenant(
    tenant_id: str,
    _: dict = Depends(require_platform_admin())
):
    # Platform admin can access any tenant
    pass
```

**Option 2: Extract from User Context**
```python
# GOOD: Extract tenant_id from authenticated user
@router.get("/resources")
async def get_resources(user_info: dict = Depends(get_current_user)):
    tenant_id = get_tenant_id(user_info)
    # Use tenant_id extracted from user's authentication token
    pass
```

## Files

- **`scripts/verify_tenant_id_sources.py`** - Dedicated verification script
- **`app/core/tenant_isolation.py`** - Core scanner library
- **`scan_tenant_isolation.py`** - General tenant isolation scanner
- **`TENANT_ID_SOURCE_AUDIT.md`** - Comprehensive audit report

## Maintenance

Run this audit:
- ✅ After adding new API endpoints
- ✅ Before production deployments
- ✅ As part of security review process
- ✅ Monthly security audits

## References

See `TENANT_ID_SOURCE_AUDIT.md` for:
- Complete list of all 35 legitimate platform admin endpoints
- Detailed security analysis
- Historical audit results
- Recommendations
