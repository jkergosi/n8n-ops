# ADR-009 — Canonical Identity via Content Hash

**Status:** Accepted  
**Date:** 2026-01-16  
**Owner:** Workflow Ops  
**Scope:** Workflow identity, mapping, drift detection

---

## Context

Workflow Ops must determine whether:
- A workflow in n8n
- A workflow in Git
- A workflow in another environment

represent the *same logical workflow*.

Names, IDs, and timestamps are unreliable across environments and imports.
A stable identity mechanism is required.

---

## Decision

Workflow Ops uses a **content-based hash** as the canonical identity signal
for workflow equivalence.

The content hash is derived from:
- Normalized workflow definition
- Excluding environment-specific or volatile fields

---

## Usage

Content hashes are used to:
- Establish initial workflow mapping
- Detect drift between Git and runtime
- Validate promotions and reverts
- Identify workflow equivalence across environments

Names and runtime IDs are treated as **secondary metadata only**.

---

## Rationale

- Names can change
- Runtime IDs are environment-specific
- Content defines behavior and intent

Hash-based identity ensures correctness across:
- DEV → STAGING → PROD
- Import/export
- Backup/restore

---

## Constraints

- Hash computation must be deterministic
- Normalization rules must be stable
- Hash changes always imply semantic change

---

## Non-Goals

- Hash is not a version number
- Hash does not encode environment or metadata
- Hash is not user-facing

---

## Consequences

### Positive
- Reliable cross-environment mapping
- Drift detection is deterministic
- Promotions are safe and predictable

### Trade-offs
- Requires careful normalization
- Minor workflow changes always register as change

---

## Status

This decision is **binding**.
Any alternative identity mechanism requires a new ADR.
