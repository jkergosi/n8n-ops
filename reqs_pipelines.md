# Pipeline UI Requirements (v1)

## 1. Scope

This document describes the requirements for building the **Pipeline UI**, which allows tenants to define how workflows are promoted between environments.

Out of scope:
- Executing promotions
- Viewing execution logs
- Workflow editing

This UI only defines **rules and structure** used by the promotion engine.

---

## 2. Pipelines List Screen

### 2.1 Purpose
Allow users to view, create, and manage promotion pipelines for a tenant.

### 2.2 UI Elements
- List or table of pipelines with:
  - Pipeline Name
  - Environment Path (e.g., `Dev → Staging → Prod`)
  - Status (Active / Inactive)
  - Last Modified (user + timestamp)
- Primary action: **Create Pipeline**
- Per-row actions:
  - Edit
  - Duplicate
  - Activate / Deactivate

### 2.3 Behavior
- Clicking a pipeline opens the Pipeline Editor.
- Deactivated pipelines cannot be used for promotions.
- Deleting pipelines is not required for MVP (soft-disable is sufficient).

---

## 3. Pipeline Editor Screen

### 3.1 Purpose
Create or edit a pipeline and define rules per environment transition.

### 3.2 Layout
Top-to-bottom:
1. Pipeline Header
2. Environment Sequence Editor
3. Stage Configuration Cards
4. Save / Cancel

---

## 4. Pipeline Header

### Fields
- Pipeline Name (required)
- Description (optional)
- Status toggle (Active / Inactive)

### Validation
- Name is required.
- Inactive pipelines cannot be selected during promotion.

---

## 5. Environment Sequence Editor

Defines the ordered list of environments for the pipeline.

### UI
- Horizontal sequence or vertical list:
  - Example: `Dev → Staging → Prod`
- Controls:
  - Add environment (dropdown of tenant environments)
  - Remove environment
  - Reorder (drag/drop or up/down arrows)

### Rules
- Minimum of 2 environments required.
- No duplicate environments allowed.
- Each adjacent pair forms a **stage**:
  - `Dev → Staging`
  - `Staging → Prod`

Modifying the sequence dynamically updates the stages below.

---

## 6. Stage Configuration

For each adjacent environment pair, render a **Stage Card**.

### Stage Header
- Title: `<Source> → <Target>`
- Expand / collapse control

---

## 7. Stage Sections

Each stage includes the following configurable sections.

---

### 7.1 Basic Info (Read-Only)
- Source Environment
- Target Environment

---

### 7.2 Gates

Used to block or allow promotion execution.

#### Fields
- Require clean drift before promotion (checkbox)
- Run pre-flight validation (checkbox)
  - Credentials exist in target
  - Nodes supported in target
  - Webhooks available
- Target environment must be Healthy (checkbox)
- Max allowed workflow risk level (dropdown: Low / Medium / High)

#### Behavior
- If pre-flight validation is disabled, sub-options are disabled.
- Risk threshold is stored only; enforcement occurs during promotion.

---

### 7.3 Approvals

Controls whether human approval is required to promote.

#### Fields
- Require approval (toggle)
- If enabled:
  - Approver role/group (dropdown)
  - Required approvals (1 of N / All)

#### Behavior
- When enabled, promotion becomes “Request approval.”
- Rejection requires comment (handled in promotion flow).

---

### 7.4 Schedule Restrictions (Optional / MVP-lite)

Restricts when promotions may occur.

#### Fields
- Restrict promotion times (toggle)
- Allowed days (multi-select)
- Start time / End time (HH:MM)

#### Behavior
- Outside allowed window → promotion blocked or deferred.
- No auto-queueing required for MVP.

---

### 7.5 Policy Flags

Control strictness of promotion behavior.

#### Fields
- Allow placeholder credentials in target
- Allow overwriting target hotfixes
- Allow force promotion on conflicts (can be ignored for MVP enforcement)

#### Defaults
- Stages targeting Prod should default to stricter settings:
  - Placeholders OFF
  - Hotfix overwrite OFF

---

## 8. Save & Validation

### Validation Rules
- At least 2 environments in pipeline.
- No duplicate environments.
- Approval fields required when approval toggle is enabled.
- Schedule fields valid if schedule restriction enabled.

### Actions
- Save
- Cancel

On save, persist:
- Pipeline metadata
- Ordered environment IDs
- Per-stage configuration:
  - Gates
  - Approvals
  - Schedule
  - Policy flags

---

## 9. Promotion UI Integration (Read-Only from this UI)

When promotion is initiated:
- User selects a pipeline.
- System determines the active stage based on source environment.
- Promotion engine consumes:
  - Gate settings
  - Approval requirements
  - Schedule limits
  - Policy flags

Pipeline UI does **not** implement promotion logic.

---

## 10. MVP Requirements Summary

### Required for v1
- Pipelines list view
- Create/edit pipeline
- Environment sequencing
- Stage configuration:
  - Gates
  - Approvals
  - Policy flags
- Persist and expose configuration to promotion flow

### Deferred
- Advanced schedule behaviors
- Conditional gates by tags or workflow attributes
- Force-promotion overrides
- Cross-pipeline analytics
