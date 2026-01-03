# Platform Menu Simplification — Claude Code Instructions

## Objective
Simplify the **Platform** menu to a flat, non-redundant set of entries (no subsections), and merge/remove redundant pages.

### Final Platform menu (flat)
1. Platform Dashboard
2. Tenants
3. Support Console
4. Tenant Overrides
5. Entitlements Audit
6. Platform Admins

### Remove from Platform menu
- Support Requests
- Support Config
- Settings

---

## 1) Sidebar / Navigation Changes

### 1.1 Update the Platform menu items
- In the sidebar config for the **Platform** section:
  - Keep only the 6 items listed above
  - Remove the 3 items listed above

### 1.2 Routes (ensure these exist and remain stable)
- Platform Dashboard → `/platform` (or the existing dashboard route)
- Tenants → `/platform/tenants`
- Support Console → `/platform/support` (or existing)
- Tenant Overrides → `/platform/overrides`
- Entitlements Audit → `/platform/entitlements-audit`
- Platform Admins → `/platform/admins`

**Do not introduce nested menu/subsections.** Only change which items appear.

---

## 2) Page Merges (move functionality, not just links)

### 2.1 Support Requests → move into Support Console
- Remove “Support Requests” as a standalone nav item.
- In Support Console, add a tab or internal navigation (within the page) for:
  - Requests list
  - Request detail view
  - Request status updates / actions

**Acceptance:** anything previously done on Support Requests is reachable from Support Console.

### 2.2 Support Config → move into Support Console
- Remove “Support Config” as a standalone nav item.
- In Support Console, add a tab/section for Support settings:
  - Templates
  - Defaults/queues (whatever currently exists)
  - Any support-related config

**Acceptance:** support configuration is reachable from Support Console.

### 2.3 Settings → move into Platform Dashboard (as secondary shortcuts)
- Remove “Settings” as a standalone nav item.
- Add a small “Shortcuts” area on Platform Dashboard containing links to:
  - Platform Admins
  - Tenant Overrides
  - Entitlements Audit
  - Support Console
  - Tenants

If there were platform-level system settings previously on Settings:
- Either:
  - Move them into the most relevant existing page (preferred), OR
  - Keep the Settings route accessible via a deep link (not in menu) until fully migrated

**Do not create new menu structure.**

---

## 3) Redirects / Backward Compatibility (recommended)
To avoid breaking existing bookmarks:
- Keep the old routes for removed menu items and redirect them:
  - `/platform/support-requests` → `/platform/support?tab=requests`
  - `/platform/support-config` → `/platform/support?tab=config`
  - `/platform/settings` → `/platform` (or `/platform/admins` if settings were mostly access-related)

---

## 4) Permissions
No change in permissions implied by this refactor.
- Ensure platform-admin gating still applies to all `/platform/*` routes.

---

## 5) Acceptance Criteria
- Platform sidebar shows exactly:
  - Platform Dashboard, Tenants, Support Console, Tenant Overrides, Entitlements Audit, Platform Admins
- Support Console contains both:
  - Support Requests functionality
  - Support Config functionality
- No new menu nesting introduced
- Old routes (if they exist) redirect to the new locations
