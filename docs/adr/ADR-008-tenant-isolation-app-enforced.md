# ADR-008 — Tenant Isolation Model (Application-Enforced)

**Status:** Accepted  
**Date:** 2026-01-16  
**Owner:** Workflow Ops  
**Scope:** Multi-tenancy, security, request handling

---

## Context

Workflow Ops is a multi-tenant system where strict tenant isolation is mandatory.
The system does **not** use database Row Level Security (RLS). Therefore, tenant
isolation must be enforced entirely in the application layer.

Code review revealed duplicated tenant ID extraction logic across many files,
indicating an undocumented and drifting architecture decision.

This ADR formalizes the tenant isolation model.

---

## Decision

1. **Tenant isolation is enforced in the application layer**, not the database.
2. **Every request must establish a TenantContext** containing at least:
   - tenant_id
   - user_id
   - role / permissions
3. **TenantContext is created in exactly one place** and reused everywhere.
4. **All data access must be explicitly tenant-scoped**.
5. **No endpoint or service may query tenant-owned tables without a tenant_id**.

---

## Tenant Context Creation

### Approach

Workflow Ops uses a **central FastAPI dependency**:

```python
TenantContext = Depends(get_tenant_context)
```

Responsibilities of `get_tenant_context()`:
- Authenticate the user
- Determine the active tenant (header, path param, or derived membership)
- Validate tenant membership and role
- Return a strongly-typed TenantContext object

Middleware-based tenant injection is explicitly not used to avoid hidden behavior.

---

## Data Access Rules (Critical)

Because there is no RLS:

- Repository/service methods **must require tenant_id** as an argument
- Endpoints must not execute raw queries directly
- Shared base repository patterns may be used to enforce this constraint

A missing tenant filter is considered a **security bug**.

---

## Testing Requirements

The following tests are mandatory:
- Tenant A cannot read Tenant B data
- Tenant A cannot modify Tenant B data
- Requests without a resolvable tenant are rejected
- Tenant selection rules are deterministic

---

## Non-Goals

- No database-enforced isolation (RLS)
- No implicit tenant selection
- No background tenant context mutation

---

## Consequences

### Positive
- Explicit, understandable security model
- No hidden middleware behavior
- Easier to reason about and test

### Trade-offs
- Requires discipline in repository patterns
- Higher responsibility on application code

---

## Status

This decision is **binding**.
Any introduction of RLS or alternative tenant isolation requires a new ADR.
