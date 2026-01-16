# ADR-007 — Environment State Scenarios Closure

**Status:** Accepted  
**Date:** 2026-01-16  
**Owner:** Workflow Ops  
**Scope:** Environment state modeling, drift handling, and user action semantics

---

## Context

Workflow Ops defines a finite set of **environment state scenarios** describing how Git state, n8n runtime state, drift detection, and user actions interact across DEV, STAGING, and PROD environments.

During MVP hardening, repeated gap analyses confirmed that:
- All scenarios were detectable and labeled
- Remaining discrepancies were due to **terminology alignment** and **action-scope ambiguity**, not missing logic

This ADR records the **final decisions** that close the Environment State Scenarios workstream.

---

## Decision 1 — Git Failure Granularity

### Decision
**Adopt a single consolidated state: `GIT_UNAVAILABLE`.**

### Rationale
- All Git access failures (401 / 403 / 404 / network) require the **same user remediation**:
  - Verify repository URL
  - Update credentials (PAT)
- Distinguishing `MISSING_REPO` adds state complexity without improving user outcomes
- Existing code and comments already treat this consolidation as intentional

### Outcome
- `MISSING_REPO` is retired from terminology
- Scenario #6 is defined as:

| Scenario | Effective State | Handling |
|--------|-----------------|----------|
| Git missing (previously managed) | `GIT_UNAVAILABLE` | User checks repo URL and credentials |

---

## Decision 2 — Action Scope Definition

### Decision
**Management and ignore actions are workflow-level, not environment-level.**

### Rationale
- Governance decisions apply to individual workflows, not entire environments
- Environment-level controls should focus on configuration and policy
- Avoids UI clutter and ambiguous bulk actions

### Action Scope Matrix

| Action | Scope | Implementation |
|------|------|----------------|
| Manage (track) | Workflow-level | Unmapped Workflows page |
| Ignore | Workflow-level | Leave unmapped (no-op) |
| Configure Git | Environment-level | Edit Environment dialog |

### Outcome
- No environment-level “Manage Unmanaged” button
- No environment-level “Ignore” button
- Checklist actions are either explicit or intentionally implicit

---

## Validation Criteria (All Met)

| Criterion | Status |
|---------|--------|
| All 10 scenarios detectable | ✅ |
| All states labeled correctly | ✅ |
| Actions implemented or documented as implicit | ✅ |
| Drift & incidents LINKED-only | ✅ |
| Terminology aligned with implementation | ✅ |

---

## Non-Goals (Explicit)

- No additional drift states
- No sync reintroduction
- No schema or enum expansion
- No environment-level ignore semantics

---

## Consequences

### Positive
- Stable, minimal state machine
- Clear separation of concerns
- Reduced future regression risk
- MVP scope firmly locked

### Trade-offs
- Less granular Git failure messaging
- Some actions require users to navigate to workflow-specific pages

These trade-offs are acceptable for MVP and can be revisited post-launch if needed.

---

## Status

**Environment State Scenarios workstream is CLOSED.**

Any future changes require a new ADR.
