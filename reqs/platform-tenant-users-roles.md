# Platform → Tenant → Users & Roles (Full Implementation) — Claude Code Instructions

## Objective
Implement **Platform → Tenants → {tenant} → Users & Roles** as a **platform operations** surface:
- **Visibility + intervention** for platform admins
- **Not** a duplicate of tenant “Members” management UX
- **Read-mostly** with a small set of high-leverage platform actions
- All actions must be **audited**

---

## 0) Non-Negotiable Principles
1. This page is **platform-side**. It is not “invite members” UX.
2. Only **platform admins** can access it.
3. Any “intervention” action requires:
   - confirm modal
   - server-side authorization
   - audit log entry (actor, target, tenant, before/after)
4. No new sidebar subsections; page lives under existing Platform → Tenants detail navigation.

---

## 1) Route + Access Control

### 1.1 Route
Implement (or confirm) a route like:
- UI route: `/platform/tenants/:tenantId/users` (or whatever your tenant detail tabs use)
- Page component: `PlatformTenantUsersRolesPage`

### 1.2 Guard
- Enforce platform-admin only at:
  - frontend route guard
  - backend endpoints (must reject non-platform-admin)

---

## 2) Page Layout (Simple)

### 2.1 Header
- Tenant name
- Tenant ID
- Plan tier (Free/Pro/Agency/Enterprise)
- Tenant status (Active/Suspended if applicable)
- Secondary: link back to tenant overview

### 2.2 Main content: Users table
Single table with:
- Search (name/email)
- Filters: Role, Status
- Sorting: Name, Role, Status, Joined, Last Activity

Empty state:
- “No users found for this tenant.”

---

## 3) Data Model (What to Show)

### 3.1 Table columns
1. **User**
   - name (fallback to email prefix)
   - email
2. **Role (tenant-scoped)**
   - Admin / Member / Read-only (only if supported)
3. **Status**
   - Active / Invited / Suspended (tenant-scoped)
4. **Joined**
   - joined_at (fix “Invalid Date” on existing members table by ensuring ISO parsing + null handling)
5. **Last Activity**
   - last_login_at or last_activity_at (pick one available)
6. **Auth Source**
   - Password / SSO / Invite (if available; otherwise omit)
7. **Actions**
   - Impersonate
   - Suspend/Unsuspend
   - Change Role
   - Remove from Tenant

**Do NOT add “Invite Member” CTA here.** Tenant owners manage invitations on their Members page.

---

## 4) Backend Endpoints (Minimal + Efficient)

### 4.1 Read endpoint (required)
Implement:
- `GET /api/platform/tenants/:tenantId/users`

Return an array with:
- user_id
- name
- email
- role_in_tenant
- status_in_tenant (active/invited/suspended)
- joined_at
- last_activity_at (or last_login_at)
- auth_source (optional)

Performance:
- avoid N+1
- include pagination (`page`, `pageSize`) if tenants can be large

### 4.2 Action endpoints (required)
Implement the following platform-admin-only endpoints:

#### A) Impersonate user
- `POST /api/platform/tenants/:tenantId/users/:userId/impersonate`
Returns:
- impersonation session info (whatever your app uses)

#### B) Suspend / Unsuspend user (tenant-scoped)
- `POST /api/platform/tenants/:tenantId/users/:userId/suspend`
- `POST /api/platform/tenants/:tenantId/users/:userId/unsuspend`

#### C) Force role change (tenant-scoped override)
- `PATCH /api/platform/tenants/:tenantId/users/:userId/role`
Body:
```json
{ "role": "admin" | "member" | "readonly" }
```

#### D) Remove user from tenant
- `DELETE /api/platform/tenants/:tenantId/users/:userId`

### 4.3 Audit logging (mandatory)
Every action endpoint must emit an audit entry containing:
- actor_user_id (platform admin)
- tenant_id
- target_user_id
- action_type (impersonate|suspend|unsuspend|role_change|remove)
- before_state + after_state (json)
- timestamp

Reuse your existing `audit_logs` table and patterns.

---

## 5) UI Actions + Confirmation

### 5.1 Impersonate
- Button label: “Impersonate”
- Confirm modal text:
  - “You are about to impersonate {user}. This action will be recorded.”
- On success:
  - activate impersonation banner globally (your existing UI)
  - navigate to tenant context if required

### 5.2 Suspend / Unsuspend
- Button toggles based on current status
- Confirm modal includes impact:
  - “Suspending will block this user from accessing this tenant.”
- Update row state only after success

### 5.3 Change Role
- Inline dropdown or modal selector
- Confirm modal:
  - “Change role for {user} from {from} to {to}?”
- Disallow changing your own role if it would lock you out (safety)

### 5.4 Remove from Tenant
- Destructive action
- Confirm modal with strong warning
- After success: remove row from table

---

## 6) UX Rules
- No upsell content on platform pages.
- No duplicate invites/members onboarding here.
- Keep it operational and terse.
- If a data point isn’t available (auth_source/last_activity), **omit the column** instead of showing fake defaults.

---

## 7) Permissions / Safety Edge Cases
- If a tenant has exactly 1 admin and you remove/suspend them:
  - allow it (platform admins can), but show an extra warning
- Warn if removing yourself from a tenant (optional)

---

## 8) Acceptance Criteria
- Platform admin can open the page and see tenant users with roles/statuses.
- Search + basic filters work.
- Actions work end-to-end and are audited:
  - impersonate
  - suspend/unsuspend
  - role change
  - remove from tenant
- Non-platform admin cannot access the page or endpoints.
- No “Invite Member” is present on this platform page.
