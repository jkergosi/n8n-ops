# WorkflowOps — RBAC & Routing Specification (MVP)

## Purpose
Implement a minimal, non–scope-creeping RBAC and routing model for WorkflowOps.

This spec defines:
- Roles
- Route access
- Sidebar visibility
- Plan gating
- Admin vs Platform separation

This document is authoritative. Do not infer or extend beyond what is written.

---

## Roles (LOCKED FOR MVP)

### Org-scoped roles
- **admin**
  - Full authority for the organization
  - Manages members, billing, plans, settings, credentials
- **developer**
  - Builds and operates workflows and environments
  - No org settings, billing, or secrets
- **viewer**
  - Read-only access to allowed pages
  - No mutations, no secrets

### Platform-scoped role
- **platform_admin**
  - Global, cross-tenant access
  - Never assignable by org admins
  - Platform routes are invisible unless this role is present

There is **no Owner role**.  
**admin == owner** for MVP.

---

## Plans (Feature Gating Only)

Plans gate features, not authority.

- `free`
- `pro`
- `agency`
- `agency_plus`

Notation:
- **Free+** → all plans
- **Pro+** → pro / agency / agency_plus
- **Agency+** → agency / agency_plus

---

## Top-Level Navigation

Dashboard  
Environments  
Workflows  
Executions  
Activity  
Observability  
Identity & Secrets  
Admin  
Platform (platform_admin only)

---

## Route Access Matrix

### Core Operations

| Route | Sidebar | Roles | Plans |
|------|--------|-------|-------|
| / | Yes | viewer+ | Free+ |
| /dashboard | Alias | viewer+ | Free+ |
| /environments | Yes | viewer+ | Free+ |
| /environments/:envId | No | viewer+ | Free+ |
| /workflows | Yes | viewer+ | Free+ |
| /workflows/:workflowId | No | viewer+ | Free+ |
| /executions | Yes | viewer+ | Free+ |
| /executions/:executionId | No | viewer+ | Free+ |
| /activity | Yes | viewer+ | Free+ |

Action rules:
- Workflow mutations: developer+
- Environment creation: developer+
- Secrets/credentials: admin only

---

### Observability

| Route | Sidebar | Roles | Plans |
|------|--------|-------|-------|
| /observability | Yes | viewer+ | Pro+ |

---

### Identity & Secrets

| Route | Sidebar | Roles | Plans |
|------|--------|-------|-------|
| /credentials | Yes | admin only | Free+ |
| /credentials/:id | No | admin only | Free+ |
| /n8n-users | Yes | admin only | Pro+ |

---

### Org Admin

| Route | Sidebar | Roles | Plans |
|------|--------|-------|-------|
| /admin | Yes | admin only | Free+ |
| /admin/members | Yes | admin only | Free+ |
| /admin/plans | Yes | admin only | Free+ |
| /admin/usage | Yes | admin only | Free+ |
| /admin/billing | Yes | admin only | Free+ |
| /admin/feature-matrix | Yes | admin only | Free+ |
| /admin/entitlements | Yes | admin only | Free+ |
| /admin/credential-health | Yes | admin only | Free+ |
| /admin/settings | Yes | admin only | Free+ |

Invariant:
- At least one admin must always exist.

---

### Platform (Hidden)

| Route | Sidebar | Roles | Plans |
|------|--------|-------|-------|
| /platform | Conditional | platform_admin | Free+ |
| /platform/tenants | Conditional | platform_admin | Free+ |
| /platform/tenant-overrides | Conditional | platform_admin | Free+ |
| /platform/entitlements-audit | Conditional | platform_admin | Free+ |
| /platform/support/requests | Conditional | platform_admin | Free+ |
| /platform/support/config | Conditional | platform_admin | Free+ |
| /platform/settings | Conditional | platform_admin | Free+ |

---

## Enforcement Rules

- All routes require server-side guards.
- UI hiding is not sufficient.
- Platform routes must audit all actions.

---

## Non-Goals

- No Owner role
- No extra admin variants
- No custom roles
- No cross-tenant access outside platform
