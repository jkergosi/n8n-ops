# Environments Page — Overview & Navigation

## Purpose
The Environments page is an **overview and comparison surface**, not an operational control plane.

Its goals are to:
- Show all connected environments at a glance
- Surface health, drift, and risk signals
- Enable fast navigation into a specific environment
- Provide a *very small* set of safe, high-frequency actions

Destructive or state-altering actions do NOT belong here.

---

## Primary User Intent
1. Compare environments (dev / staging / production)
2. Detect drift or unhealthy states
3. Navigate to an environment for deeper inspection or action

---

## Non-Goals
- Performing restores or deletes
- Managing backups or snapshots
- Executing high-risk operations
- Fine-grained configuration changes

Those belong on the Environment Details page.

---

## Page Structure

### Header
- Title: **Environments**
- Subtitle: “Manage and monitor connected workflow environments”
- Primary CTA: **Add Environment**
- Optional: environment limit indicator (e.g., `3 / 3 environments`)

---

## Environments Table

### Column Order (Recommended)
1. Environment
2. Status
3. Drift
4. Workflows
5. Last Sync
6. Actions

---

### Column Definitions

#### Environment
- Name (clickable)
- Environment type badge: `dev`, `staging`, `production`
- Visual criticality:
  - dev → neutral
  - staging → amber
  - production → red

Clicking the row or name navigates to **Environment Details**.

---

#### Status
Explicit health indicator:
- Connected
- Degraded
- Offline

Show:
- Status badge
- Secondary text: `Last heartbeat: X min ago`

Avoid raw timestamps alone.

---

#### Drift
Indicates divergence from source of truth or peer environments.

Examples:
- `+5 vs staging`
- `–3 vs dev`
- `In sync`

This is a signal column, not an action.

---

#### Workflows
- Total workflow count
- Clickable to open Environment Details → Workflows tab
- Optional secondary text for enabled/disabled ratio

---

#### Last Sync
- Relative time (`2m ago`, `1h ago`)
- Tooltip with exact timestamp

---

#### Actions (Strictly Limited)

Allowed inline actions:
- **View** (or implicit via row click)
- **Sync** (confirmation required)

Optional:
- **⋯ Ellipsis Menu** for low-risk metadata actions

Disallowed on this page:
- Backup
- Restore
- Download
- Delete

---

## Ellipsis Menu Rules

The ellipsis menu is OPTIONAL and MUST remain minimal.

Allowed items:
- Edit environment metadata
- Reconnect / refresh credentials
- Disable environment (non-destructive)

Disallowed:
- Restore
- Delete
- Snapshot management

If an action can destroy state, it does not belong in this menu.

---

## Production Safety Rules

- Production rows must be visually distinct
- No destructive actions exposed inline
- Sync requires confirmation and optional diff preview
- No delete option visible for production environments

---

## Accessibility & UX Notes

- Entire row (except actions) should be clickable
- Actions column should be sticky on horizontal scroll
- Status and drift must be scannable without tooltips
- No hidden destructive actions

---

## Summary Principles

- This page is for **seeing**, not **doing**
- Optimize for comparison, clarity, and safety
- Push complexity downward into scoped detail views
