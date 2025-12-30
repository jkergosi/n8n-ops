# Environment Details Page — Control Plane

## Purpose
The Environment Details page is the **primary operational surface** for a single environment.

Its goals are to:
- Provide full visibility into the environment
- Centralize all environment-specific actions
- Enforce safety, confirmation, and context
- Prevent accidental destructive operations

This page is intentionally scoped to ONE environment.

---

## Primary User Intent
1. Understand the current state of an environment
2. Inspect drift, history, and configuration
3. Perform operational actions safely
4. Diagnose issues

---

## Page Entry
Reached by:
- Clicking an environment row or name from the Environments page

This navigation is intentional and required.

---

## Page Structure

### 1. Environment Header (Always Visible)

Includes:
- Environment name
- Environment type badge (dev / staging / prod)
- Status badge (Connected / Degraded / Offline)
- Persistent **Production Warning Banner** when applicable

Example:
> ⚠ You are operating on **Production**

---

### 2. Environment Summary Panel

Display:
- Instance URL (clickable)
- Provider (e.g., n8n)
- Source of truth: Git / Manual / External
- Workflow count
- Last sync time
- Last backup time

This section is informational only.

---

## 3. Primary Action Bar

This is the ONLY place where high-impact actions live.

### Allowed Actions
- Sync
- Backup (Create Snapshot)
- Restore (From Snapshot)
- Download
- Delete Environment

---

### Action Safety Rules

#### Sync
- Confirmation required for staging and prod
- Optional diff preview
- Explicit target/source displayed

#### Backup
- Non-destructive
- Always allowed
- Snapshot must be named or auto-labeled

#### Restore
- Always gated
- Requires:
  - Snapshot selection
  - Diff preview
  - Typed confirmation for production
- Explicit warning: “This will overwrite current state”

#### Download
- Non-destructive
- Includes scope selection (workflows only, credentials excluded, etc.)

#### Delete
- Disabled for production by default
- Requires:
  - Admin role
  - Typed environment name
  - Final confirmation modal

---

## 4. Tabs / Sections

### Overview (Default)
- Health summary
- Drift summary
- Recent activity (syncs, restores)
- Alerts or warnings

---

### Workflows
- List of workflows in this environment
- Enabled / disabled state
- Last updated
- Drift indicators per workflow

---

### Snapshots / Backups
- Chronological list of snapshots
- Metadata:
  - Created by
  - Timestamp
  - Trigger (manual / scheduled)
- Restore and download actions scoped to snapshot

---

### Sync History
- Audit log of:
  - Syncs
  - Restores
  - Failures
- Who initiated
- Outcome

---

### Credentials (Optional but Recommended)
- Credential health summary
- Missing / mismatched credentials
- Links to credential management

---

### Settings
- Environment metadata
- Instance connection details
- Feature flags
- Disable / archive environment

---

## Production-Specific Rules

When environment type = production:
- Persistent warning banner
- Restore requires typed confirmation
- Delete hidden or disabled
- Sync defaults to “preview first”

---

## UX & Safety Principles

- Context before action
- Diff before overwrite
- Typed confirmation for irreversible changes
- No destructive actions without scoping
- No global actions leaking into this page

---

## Summary Principles

- One environment, full context
- Power with guardrails
- Intentional friction over accidental speed
- Clear separation from overview page
