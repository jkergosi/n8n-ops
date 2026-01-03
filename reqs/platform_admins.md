# WorkflowOps — Platform Admin Management Spec (MVP)

## Purpose
Define the UI, data model, routing, and safeguards for managing **Platform Admins** (global super users) in WorkflowOps.

This document is authoritative. Implement exactly as specified.

---

## Naming Decision

**Use the term: Platform Admin**

Rationale:
- Clearly scoped above organizations
- Avoids ambiguity of “super user”
- Distinct from org-scoped admins
- Industry-aligned (GitHub Site Admin, Stripe Platform Admin)

Never use:
- Super user
- System admin
- Generic “admin” without scope

---

## Navigation Placement

Left sidebar → **Platform** section (conditional):

Platform  
- Overview  
- Tenants  
- **Platform Admins**  
- Tenant Overrides  
- Support Requests  
- Settings  

Visibility rule:
- Entire Platform section is visible **only if** `user.is_platform_admin === true`

---

## Route Definitions

Frontend route:
```
/platform/admins
```

API routes:
```
GET    /platform/admins
POST   /platform/admins
DELETE /platform/admins/:userId
```

---

## Data Model

### Table: `platform_admins`

```sql
platform_admins (
  user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  granted_by UUID REFERENCES users(id),
  granted_at TIMESTAMP WITH TIME ZONE DEFAULT now()
)
```

Rules:
- Presence in this table = platform admin
- Do not reuse org role tables
- Backend may expose `user.is_platform_admin` as a computed boolean

---

## Page: Platform Admins (`/platform/admins`)

### Purpose
Manage users with **global, cross-tenant authority**.

This page:
- Is not org-scoped
- Is not visible to org admins
- Is high-risk and must be explicit and auditable

---

## UI Layout

### Header
```
Platform Admins
Users with full, cross-tenant administrative access to WorkflowOps.
This access applies globally across all organizations.
```

Warning callout:
> Platform Admins can view and modify any tenant. Grant sparingly.

---

### Platform Admins Table

Columns:
- Name
- Email
- Granted At
- Granted By
- Actions

Actions:
- Remove access

Rules:
- A platform admin cannot remove themselves if they are the **last** platform admin
- Enforce server-side

---

### Add Platform Admin

UI:
- Button: **Add Platform Admin**
- Opens modal or inline panel

Fields:
- User selector (email search; user must already exist)
- Confirmation checkbox:
  - “I understand this grants global platform access.”

Submit behavior:
- Insert row into `platform_admins`
- Write audit log entry
- Refresh table

---

## Permissions & Guards (MANDATORY)

All `/platform/admins*` routes must enforce:

```
requireAuth
requirePlatformAdmin
```

No exceptions.
No org-admin access.

---

## Audit Logging (REQUIRED)

Log every mutation:
- Actor user ID
- Target user ID
- Action (`platform_admin.grant` / `platform_admin.revoke`)
- Timestamp

Reuse existing audit system if present.
If not, stub but do not skip.

---

## Sidebar Behavior

- Show **Platform Admins** menu item only if `user.is_platform_admin === true`
- Do not show disabled or locked items
- Do not leak platform features to non-platform users

---

## Copy Rules (to avoid confusion)

Always say:
- Platform Admin
- Global access across all organizations

Never say:
- Super user
- System admin
- Admin (without scope)

---

## Invariants (Must Be Enforced)

1. At least one platform admin must always exist
2. Platform admins cannot demote themselves if they are the last one
3. Org admins cannot view or manage platform admins
4. Platform admin access is never plan-gated

---

## Explicit Non-Goals

Do NOT implement:
- Approval workflows
- Role tiers within platform admins
- Temporary or expiring access
- Requests for platform access from org admins
- Visibility from org admin screens

---

## Summary (Lock This In)

- Name: Platform Admin
- Route: /platform/admins
- Storage: platform_admins table
- Access: platform_admin only
- UI: minimal, explicit, auditable
