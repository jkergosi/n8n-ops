# WorkflowOps — Platform Support Console & Impersonation Spec (MVP)

## Purpose
Define the **Platform Support Console** and **User Impersonation** capabilities for WorkflowOps platform admins.

This spec enables safe, auditable, cross-tenant support without leaking platform powers into org-level UX.

This document is authoritative.

---

## Naming (LOCKED)

- **Platform Admin**: Global super user (already defined)
- **Impersonation**: Acting as an existing user within their tenant context

Never use:
- Super user
- Masquerade
- Switch user
- System admin

---

## Navigation Placement

Left sidebar → **Platform** section (conditional):

Platform  
- Overview  
- Tenants  
- Platform Admins  
- **Support Console**  
- Tenant Overrides  
- Support Requests  
- Settings  

Visibility:
- Entire Platform section visible only if `user.is_platform_admin === true`

---

## Route Definitions

Frontend routes:
```
/platform/console
```

API routes:
```
POST /platform/impersonate
POST /platform/impersonate/stop
```

---

## Support Console (`/platform/console`)

### Purpose
Provide a single workspace for platform admins to:
- Search tenants
- Search users
- Initiate impersonation

This page is platform-only and never tenant-scoped.

---

## Console Layout

### Section A — Tenant Search

Search inputs:
- Tenant name
- Tenant slug
- Tenant ID

Results table columns:
- Tenant Name
- Tenant ID
- Plan
- Status
- Actions

Actions:
- View Tenant (optional)
- List Users (filters user list below)

---

### Section B — User Search

Search inputs:
- Email
- Name
- User ID

Results table columns:
- Name
- Email
- Tenant
- Role
- Actions

Actions:
- **Impersonate**

Rules:
- Target user must already exist
- Do not allow impersonation of another platform admin

---

## Impersonation Behavior

### Session Model (Server-Side Only)

Maintain explicit session state:

- `session.user_id` → original platform admin
- `session.impersonated_user_id` → target user (nullable)
- `session.impersonated_tenant_id` → inferred from target user

Never rely on client-only switching.

---

## Impersonation Flow

### Start impersonation
1. Platform admin clicks **Impersonate**
2. `POST /platform/impersonate { target_user_id }`
3. Server validates:
   - Caller is platform_admin
   - Target is not platform_admin
4. Session updated with impersonation fields
5. Audit log written
6. Client reloads app context

### Stop impersonation
1. Click **X Stop impersonating**
2. `POST /platform/impersonate/stop`
3. Session cleared
4. Audit log written
5. Client reloads original identity

---

## Top Bar / Identity UI (MANDATORY)

When impersonating:
- Replace the normal user picker entirely
- Display persistent identity block:

```
Impersonating: Jane Doe (jane@customer.com)
as Alice Admin (alice@workflowops.ai)   [X Stop impersonating]
```

Optional but recommended:
- Global banner: **IMPERSONATING**

Rules:
- No access to normal account switcher while impersonating
- “Stop impersonating” must be visible on every page

---

## Authorization Rules During Impersonation

- **Effective org permissions** = impersonated user’s role
- **Privilege ceiling**:
  - Org routes: impersonated user only
  - Platform routes: hidden while impersonating (recommended)

This ensures platform admins experience the product exactly as the customer.

---

## Sidebar Behavior During Impersonation

Recommended:
- Hide Platform sidebar entirely
- Show only operational + admin routes available to impersonated user
- Provide a single escape hatch: **Stop impersonating**

---

## Audit Logging (REQUIRED)

Log all impersonation events:

- `impersonation.start`
  - actor_user_id
  - target_user_id
  - tenant_id
  - timestamp
- `impersonation.stop`
  - actor_user_id
  - target_user_id
  - tenant_id
  - timestamp

Additionally:
- Log **every write action** during impersonation with:
  - actor_user_id
  - impersonated_user_id

---

## Guardrails (MANDATORY)

1. Only platform admins may impersonate
2. Platform admins may not impersonate other platform admins
3. Impersonation state must be server-enforced
4. Impersonation ends on logout or session expiry
5. Billing payment methods may not be modified while impersonating (recommended)

---

## Explicit Non-Goals

Do NOT implement:
- Nested impersonation
- Time-limited impersonation
- Approval workflows
- Customer-initiated impersonation requests
- UI access to impersonation from org admin screens

---

## Summary (Lock This In)

- New page: `/platform/console`
- Capability: Tenant & user search + impersonation
- Identity UI: Hard replace user picker with impersonation banner
- Safety: Strict guards + full audit trail
- Scope: Minimal, support-focused, non-leaky
