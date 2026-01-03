# Move `/admin/settings` → Platform Settings + Build Tenant Admin Settings — Claude Code Instructions

## Objective
Fix the current mismatch where `/admin/settings` exposes **platform-wide** configuration.
- Move the current **SettingsPage** (system-wide config) to **Platform Settings**.
- Build a new **Tenant Admin Settings** page for Free/Pro/Agency at `/admin/settings` (tenant-scoped only).
- Do **not** create `/admin/security`.

---

## Target End State

### Platform
- **Route:** `/platform/settings`
- **Access:** platform admins only
- **Page:** Platform Settings (existing SettingsPage content)

### Tenant (Free/Pro/Agency)
- **Route:** `/admin/settings`
- **Access:** tenant admins (org admins)
- **Page:** Tenant Settings (new page; tenant-scoped configuration only)

---

## 1) Inventory Current `/admin/settings` Content (do first)
1. Locate the current component used by `/admin/settings` (Cursor indicated `SettingsPage`).
2. Enumerate each section currently rendered (likely includes: app name/url, maintenance mode, DB config, Auth0 config, Stripe config, email config, provider plans mgmt, environment types, plus any tenant items like provider subscription / display name).
3. Classify each section as:
   - **PLATFORM** (system-wide) → move to `/platform/settings`
   - **TENANT** (org-scoped) → move into the new tenant settings page (only if truly tenant-scoped)

**Rule:** If it affects all tenants or requires secrets/keys used by the whole platform, it is PLATFORM.

---

## 2) Routing Changes (UI)

### 2.1 Add Platform Settings route
- Add route: `/platform/settings`
- Render: existing `SettingsPage` (or rename to `PlatformSettingsPage`)
- Gate: platform-admin only (same guard used for other `/platform/*` admin pages)

### 2.2 Replace `/admin/settings`
- Update route: `/admin/settings` to render a new page `TenantSettingsPage`
- Gate: tenant admin only (org admin role)
- Ensure platform admins can still access it if they are also tenant admins (optional; depends on your role model)

### 2.3 Backward compatibility (recommended)
- If any existing links or bookmarks point to `/admin/settings` expecting platform config, they should now land on tenant settings.
- Add a link to Platform Settings inside Platform Dashboard “Shortcuts” for platform admins.

---

## 3) Sidebar Menu Changes

### 3.1 Tenant sidebar (Free/Pro/Agency)
Under the tenant “Account” (or “Admin”) section:
- Keep: **Settings** → `/admin/settings` (Tenant Settings)

### 3.2 Platform sidebar
Under Platform section:
- Add: **Settings** → `/platform/settings`

---

## 4) Platform Settings Page (moved, minimal changes)

### 4.1 Component naming (recommended)
- Rename `SettingsPage` → `PlatformSettingsPage` for clarity (optional but strongly recommended).
- Update imports/exports accordingly.

### 4.2 Platform Settings contents (keep here)
Keep these sections on platform settings (do not show to tenants):
- App name / base URL / environment flags
- Maintenance mode toggles
- Database configuration / connection settings
- Auth provider configuration (Auth0/SSO)
- Stripe/Payments configuration
- Email provider configuration
- Provider Plans / plan catalog management
- Environment Types catalog / global taxonomy
- Any other system-wide defaults

### 4.3 Tenant-only items currently on SettingsPage
If SettingsPage currently includes tenant-scoped items (e.g., provider display name, provider subscriptions):
- Remove them from Platform Settings UI unless they are truly platform-wide defaults.
- Tenant-scoped items belong in Tenant Settings (Section 5).

---

## 5) Build Tenant Admin Settings (`/admin/settings`)

### 5.1 Goals for Tenant Settings (v1)
This is the settings page for org admins (Free/Pro/Agency). Keep it small and clearly tenant-scoped.

### 5.2 Sections to implement (v1)

#### A) Organization
- Org name
- Timezone (if supported)
- Optional: org slug (read-only), created date (read-only)

#### B) API Keys (tenant-scoped)
- List existing tenant API keys
- Create new key
- Revoke key
- Display: created_at, last_used_at (if tracked), created_by

Reuse existing API calls if already implemented (Cursor mentioned `getTenantApiKeys()`).

#### C) Audit Logs (tenant-scoped)
- Recent audit events for this tenant (last N, paginated)
- Filters: actor, action, date range (minimal)
- If there is already an “Activity” page, it’s OK to link out, but tenant settings can embed a small “Recent audit events” table.

Reuse existing tenant audit endpoint if available.

#### D) Notifications (optional, only if already exists)
- Email notifications for failures/drift (tenant-level preferences)

If notifications don’t exist today, omit this section (do not add empty toggles).

### 5.3 What Tenant Settings must NOT contain
- Maintenance mode
- Auth0 config
- Stripe secret keys / webhooks
- Email SMTP/provider keys
- Provider plan catalog management
- Environment type catalog
- Any platform-wide defaults

---

## 6) Backend/API Changes (minimal)

### 6.1 Platform settings endpoints
No change required if the existing SettingsPage already reads/writes platform config via existing endpoints.
Just ensure endpoints are platform-admin guarded.

### 6.2 Tenant settings endpoints
Ensure these endpoints exist (or create them):
- `GET /api/tenant/settings` (org name/timezone)
- `PATCH /api/tenant/settings` (update org name/timezone)
- `GET /api/tenant/api-keys`
- `POST /api/tenant/api-keys`
- `DELETE /api/tenant/api-keys/:id`
- `GET /api/tenant/audit-logs` (paginated)

**Authorization:** tenant admin required.

---

## 7) Implementation Checklist (recommended order)
1. Add `/platform/settings` route pointing to existing SettingsPage (platform-admin gated)
2. Create `TenantSettingsPage` and route `/admin/settings` to it (tenant-admin gated)
3. Move/remove tenant-scoped items out of Platform Settings UI
4. Implement Organization section in Tenant Settings (read/write)
5. Implement Tenant API Keys section (reuse existing code)
6. Implement Tenant Audit Logs section (embed or link)
7. Update sidebar menus (tenant + platform)
8. Add shortcuts on Platform Dashboard to Platform Settings
9. Verify permissions:
   - tenant admin cannot access `/platform/settings`
   - platform admin cannot accidentally expose secrets to tenants via `/admin/settings`

---

## 8) Acceptance Criteria
- `/platform/settings` exists and contains all system-wide configuration previously shown at `/admin/settings`
- `/admin/settings` exists and shows only tenant-scoped settings (Org + API keys + audit)
- No tenant can view or mutate platform config
- Sidebar shows Settings under both tenant Account/Admin and Platform, routed appropriately
- No `/admin/security` route created
