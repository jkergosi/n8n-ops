# WorkflowOps Menu Gating & Upsell Strategy
## Cursor Implementation Instructions

### Goal
Implement **clean, role-appropriate navigation** for Free, Pro, and Agency plans.
- Navigation only shows what the user can actually use.
- Upsell happens **contextually**, not in the menu.
- No locked menu items, no lock icons, no nagging.

---

## 1. Menu Structure by Plan

### 1.1 Free Plan

#### CORE
- Dashboard
- Environments (limit: 1)
- Workflows (basic)
- Executions (limited retention)
- Activity (basic audit)

#### IDENTITY & SECRETS
- Credentials (basic CRUD, limited count)

#### ACCOUNT (rename from Admin for Free)
- Members (basic invite/remove)
- Billing (view-only + upgrade CTA)
- Settings (org name, profile, API keys)

**DO NOT SHOW (Free):**
- Feature Matrix
- Entitlements
- Credential Health (advanced)
- Usage (detailed)
- Plans (self-service plan mgmt)
- Platform/Admin-only pages

---

### 1.2 Pro Plan

#### CORE
- Dashboard
- Environments
- Workflows
- Executions
- Activity

#### IDENTITY & SECRETS
- Credentials
- Credential Health (full)

#### ADMIN
- Members
- Usage (detailed)
- Billing
- Settings

**DO NOT SHOW (Pro):**
- Entitlements (platform / enterprise only)
- Feature Matrix (billing/marketing only)

---

### 1.3 Agency Plan

Same as Pro, plus:

#### ADMIN (Agency additions)
- Usage (per-client / higher limits)
- Advanced environment counts
- Higher caps surfaced in UI copy

**Still NOT shown:**
- Entitlements (unless Enterprise)
- Feature Matrix in nav

---

## 2. Navigation Rules (Critical)

1. Never show menu items the user cannot fully enter.
2. Do not use lock icons or disabled nav items.
3. Navigation reflects *current capability*, not potential upgrades.
4. All gating is enforced server-side regardless of UI.

---

## 3. Upsell Placement (Where It *Should* Happen)

### 3.1 Dashboard (Free)

Add a non-intrusive card or section:
- Title: "Unlock Advanced Controls"
- Bullets:
  - Credential Health monitoring
  - Environment drift detection
  - Extended execution history
- CTA: "Upgrade to Pro"

Only show this card on Free.

---

### 3.2 Contextual Action Gating (Primary Upsell)

When a Free user attempts a Pro/Agency-only action:

**Modal Pattern**
- Title: "Upgrade Required"
- Copy: "This feature is available on Pro plans."
- 2–3 concrete benefits (no marketing fluff)
- CTA: Upgrade
- Secondary: Cancel

Examples:
- Viewing Credential Health details
- Accessing detailed Usage analytics
- Creating drift incidents

---

### 3.3 Inline Teasers (Allowed)

Within accessible pages (e.g., Credentials page):

- Show a greyed section:
  - Header: "Credential Health (Pro)"
  - One-line description
  - CTA button

Do NOT link from sidebar.

---

### 3.4 Billing Page (Single Comparison Surface)

Billing page should contain:
- Current plan
- Upgrade options
- Feature comparison (Feature Matrix lives here ONLY)
- No separate Feature Matrix menu item

---

## 4. Pages to Remove or Restrict

### Remove from Free & Pro Navigation
- Feature Matrix
- Entitlements

### Restrict Entitlements
- Platform Admin only
- Or Enterprise-only, read-only if ever exposed

---

## 5. Implementation Notes for Cursor

- Menu rendering must be **plan-aware** and **role-aware**
- Prefer a single menu config with plan-based filters
- Do not duplicate menu definitions per plan unless unavoidable
- Backend authorization must reject gated endpoints even if UI fails

---

## 6. Acceptance Criteria

- Free users never see inaccessible menu items
- Pro/Agency users see expanded menus immediately after upgrade
- Upsell only appears at:
  - Dashboard (Free)
  - Blocked actions
  - Billing page
- No lock icons in sidebar

---

## 7. Non-Goals

- No gamification
- No persistent nags
- No sales copy in navigation
