# Pro/Agency Admin Dashboard (Control Plane) — Claude Code Instructions

## Objective
Convert **Admin** into a true **Admin Dashboard** (control plane) for **Pro+** only.
- **Free** users should not see “Admin”. They see **Account** (Members, Billing, Settings).
- **Admin Dashboard** is **insight-first** (health, risk, limits), not a link list and not a sales surface.
- No locked widgets inside Admin. Upsell for Free happens outside Admin (Dashboard card, action gates, Billing).

---

## 1) Navigation & Routing Changes

### 1.1 Sidebar labels by plan
- **Free**: replace `Admin` section with `Account`
- **Pro/Agency**: show `Admin` section and `Admin Dashboard` entry

### 1.2 Routes
- Create/confirm a route for admin dashboard:
  - `GET /admin` → **Admin Dashboard** (Pro/Agency)
- If you currently have `/admin/*` pages, keep them, but make `/admin` the dashboard landing.

### 1.3 Free user access guard
- If Free user hits `/admin` directly:
  - return a dedicated “Upgrade Required” page (not the dashboard)
  - provide CTA “Upgrade to Pro”
  - provide 2–3 bullets (Credential Health, detailed Usage, governance signals)
  - DO NOT show any operational data beyond what Free already sees elsewhere

---

## 2) Admin Dashboard Content (Pro/Agency)

### Layout rule
- Top: **Org Health** tiles
- Middle: **Usage & Limits** pressure indicators
- Bottom: **Governance Signals**
- Footer/side: **Admin Shortcuts** (small, not primary)

Use existing UI components (cards/tiles/badges) and maintain existing styling conventions.

---

## 3) Widgets (V1)

### 3.1 Org Health (Top row)
Create 4 tiles (clickable to relevant detail pages):
1. **Environments**
   - value: `current_count / plan_limit` (or `current_count` if unlimited)
   - status: warn when >= 80% of limit
   - click → `/environments`
2. **Credential Health**
   - value: `Healthy / Warning / Failing` counts (or just failing count + status)
   - click → `/credentials` (and anchor to health section if present)
3. **Recent Failures**
   - value: count of failed executions in last 24h (or 72h if you prefer)
   - click → `/executions?status=failed&range=24h`
4. **Drift**
   - value: `Drift Detected` environment count (or active incidents count)
   - click → `/environments?drift=detected` (or drift incidents page if exists)

### 3.2 Usage & Limits (middle)
Create 3–5 “pressure” cards showing current usage vs limit and trend direction if available.
- **Executions**
- **Workflows**
- **Snapshots**
- **Promotions / Pipelines** (only if you actually meter them)
Rules:
- Use a simple progress indicator (bar or %)
- Status thresholds:
  - OK < 80%
  - Warning 80–95%
  - Critical >= 95%
- Click → `/admin/usage` (detail)

Agency additions:
- If you support client/tenant aggregation, show:
  - “Top 5 orgs by execution usage” OR “Top 5 environments by failures”
  - Click-through to filtered usage view

### 3.3 Governance Signals (bottom)
Show only signals you can back with data. Start minimal.
- **Credentials needing attention** (count)
- **Drift detected environments** (count)
- **Stale configuration** (optional, only if you have definition)

Each signal row should be clickable to the remediation location.

### 3.4 Admin Shortcuts (secondary)
Add small links/buttons (not tiles):
- Members → `/admin/members` (or existing)
- Usage → `/admin/usage`
- Billing → `/billing`
- Settings → `/settings`

---

## 4) Data & API Requirements (minimal)
Prefer reusing existing endpoints. If needed, add a single admin overview endpoint:

### 4.1 New endpoint (if you don’t already have one)
- `GET /api/admin/overview`
- Returns:
  - environment_count, environment_limit
  - credential_health_counts (healthy/warn/fail)
  - failed_executions_last_24h
  - drift_detected_count (and/or active_incidents_count)
  - usage: { executions: {used, limit}, workflows: {used, limit}, snapshots: {used, limit}, promotions: {used, limit} }

### 4.2 Authorization
- Must enforce plan gating server-side:
  - Pro/Agency allowed
  - Free denied

---

## 5) UX Rules (must follow)
- Admin Dashboard contains **no**:
  - Feature Matrix
  - Entitlements editor
  - Pricing tables
  - Locked cards / lock icons
  - Sales copy
- Keep copy operational and short.
- Every widget must answer one of:
  1) Are we healthy?
  2) Are we drifting?
  3) Are we approaching limits?
  4) Are we exposed to risk?

---

## 6) Acceptance Criteria
- Free plan:
  - Sidebar has **Account**, not Admin
  - `/admin` shows upgrade-required page
- Pro/Agency:
  - Sidebar shows Admin with landing `/admin`
  - Admin dashboard shows Org Health, Usage & Limits, Governance Signals, Shortcuts
  - All counts/limits are accurate and consistent with backend enforcement
- No locked nav items in the sidebar for any plan

---

## 7) Implementation Order (recommended)
1. Update sidebar menu config for Free vs Pro/Agency
2. Add/confirm `/admin` route and Pro+ guard
3. Implement Admin Dashboard UI shell + tiles
4. Wire data (reuse existing endpoints or create `/api/admin/overview`)
5. Add usage pressure cards and drill-down links
6. Verify Free cannot access Admin endpoints

