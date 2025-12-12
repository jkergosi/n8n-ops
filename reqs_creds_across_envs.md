# Credential-Safe Workflow Promotion Across Environments  
## Provider-Aware Specification (n8n now; Make/Zapier later)

---

## 1) Purpose
Enable safe workflow promotion across environments without handling secrets. WorkflowOps:
- Promotes workflow definitions only.
- Enforces credential correctness per environment and provider.
- Blocks promotions that would fail from missing/mismatched credentials.
- Gives clear pre-deployment validation and feedback.

Never:
- Store or replicate secrets.
- Decrypt/display credential contents.
- Act as a secrets manager.

Allowed (transient only): Secret fields may pass through UI → backend → provider during credential create/edit; they are not stored locally.

---

## 2) Non-Goals
- Secret storage or vaulting.
- Cross-environment credential cloning.
- Secret rotation or lifecycle management.
- Provider encryption internals.

---

## 3) Core Concepts (provider-aware)
### 3.1 Logical Credentials (alias layer)
- Stable, provider-agnostic identifiers for required integrations (no secrets).
- Examples: `stripe_primary`, `sendgrid_main`, `db_main`.
- Referenced by workflows (directly or via metadata).
- Mapped to platform-specific credentials per environment and provider.

### 3.2 Physical Credentials (provider-owned)
- Native credentials in each provider (n8n records, Make connections, Zapier app auth).
- Environment-specific and encrypted by provider.
- WorkflowOps sees only metadata (id/name/type/existence/compatibility), never secrets.

---

## 4) Responsibilities
WorkflowOps owns:
- Logical credential definitions (tenant-scoped, provider-agnostic).
- Env+provider mappings (logical → physical).
- Workflow dependency discovery (provider adapter parses workflow definitions).
- Promotion validation/gating.
- Workflow definition rewriting to swap logical → physical references (adapter-specific).
- Operator visibility and auditability (no secrets).

WorkflowOps does NOT own:
- Secret values, encryption keys, or provider credential lifecycle.

---

## 5) Provider compatibility model
Assumptions per provider:
- Can list credentials/connections (metadata only).
- Can deploy/update workflows.
- Has stable credential references in workflow definitions.

Examples:
- n8n: `credentials.<type>.id`.
- Make/Zapier: connection/app-auth references; normalized via adapter.

Adapters handle provider-specific parse/transform of credential references.

---

## 6) UX Model
### 6.1 Environment → Credential Health
Per environment (and provider):
- Logical credential
- Expected type/integration
- Mapping status (valid/missing/incompatible)
- Impacted workflows
No secrets shown.

### 6.2 Workflow → Dependencies
Per workflow:
- Logical credentials used; required vs optional.
- Readiness per environment/provider (Dev/Staging/Prod).
Read-only, auto-derived.

### 6.3 Promotion Gate
On promotion (e.g., Dev → Staging, provider-scoped):
- Preflight validation:
  - All required logical creds mapped in target env/provider.
  - Types/integrations compatible.
  - Environment boundaries respected.
- If fails: block; show actionable errors; direct user to fix target env mapping.

---

## 7) Promotion behavior (critical path)
On successful promotion (per provider):
1) Retrieve workflow definition from source env/provider.  
2) Resolve logical credential references using target env/provider mappings.  
3) Rewrite definition with target physical credential references (adapter-specific).  
4) Deploy to target env via provider adapter.  
5) Secrets are never copied or touched—only references change.

---

## 8) Data model (high level, provider-aware)
- Logical credentials (tenant-scoped, provider-agnostic): `id`, `name`, `description`, `required_type`.
- Credential mappings (env + provider scoped): `logical_credential_id`, `environment_id`, `provider`, `physical_credential_id`, `physical_name`, `physical_type`, `status`.
- Workflow dependency index (per workflow, per provider): `workflow_id`, `provider`, `logical_credential_ids[]`.
- Audit/logs store `provider` for all mapping and promotion actions.

---

## 9) API/Service requirements
- List logical credentials (tenant).
- Manage mappings (logical → physical) per environment and provider.
- Discover workflow dependencies (adapter parses workflow JSON).
- Validate promotion (per provider) with clear errors on missing/incompatible mappings.
- Rewrite workflow definitions with mapped credential references before deploy (adapter-specific).
- Audit every mapping change and promotion validation/deploy with `provider`, actor, env, logical credential, outcome.

---

## 10) UI requirements
- Provider-aware views; hide provider selector if only one provider is active.
- Environment Credential Health: filter by provider; show mapping status.
- Workflow Dependencies: show logical creds and readiness by environment/provider.
- Promotion dialog: show preflight results; block on missing/incompatible mappings with actionable messages.
- No secret values shown—only names/ids/types/status.
- Provider badge/column when multiple providers exist.

---

## 11) Non-Functional
- Backward compatible: single-provider (n8n) flows unchanged; default provider assumed when not specified.
- No secrets exposure; only metadata handled; secret fields may transit on create/edit to provider, never stored locally.
- Performance: index mappings on (environment, provider, logical_credential); cache dependency lookups where safe.
- Auditability: all actions log provider, actor, env, logical credential, outcome.

---

## 12) Success Criteria
- Promotions fail fast when target env/provider mappings are missing or incompatible.
- No secrets are stored or transferred.
- Operators see exactly what to fix (which logical credential, which environment/provider).
- Works for n8n now; adapters enable other providers without changing the UX.
# Credential-Safe Workflow Promotion Across Environments  
## Provider-Aware Specification (n8n now; Make/Zapier later)

---

## 1) Purpose
Enable safe workflow promotion across environments without handling secrets. WorkflowOps:
- Promotes workflow definitions only.
- Enforces credential correctness per environment and provider.
- Blocks promotions that would fail from missing/mismatched credentials.
- Gives clear pre-deployment validation and feedback.

Never:
- Store/transfer secrets.
- Decrypt/display credential contents.
- Act as a secrets manager.

---

## 2) Non-Goals (out of scope)
- Secret storage or vaulting.
- Credential creation/editing/cloning across environments.
- Secret rotation or lifecycle management.
- Provider encryption internals.

---

## 3) Core Concepts (provider-aware)
### 3.1 Logical Credentials (alias layer)
- Stable, provider-agnostic identifiers for required integrations (no secrets).
- Examples: `stripe_primary`, `sendgrid_main`, `db_main`.
- Referenced by workflows (directly or via metadata).
- Mapped to platform-specific credentials per environment and provider.

### 3.2 Physical Credentials (provider-owned)
- Native credentials in each provider (n8n records, Make connections, Zapier app auth).
- Environment-specific and encrypted by provider.
- WorkflowOps sees only metadata (id/name/type/existence/compatibility), never secrets.

---

## 4) Responsibilities
WorkflowOps owns:
- Logical credential definitions (tenant-scoped, provider-agnostic).
- Env+provider mappings (logical → physical).
- Workflow dependency discovery (provider adapter parses workflow definitions).
- Promotion validation/gating.
- Workflow definition rewriting to swap logical → physical references (adapter-specific).
- Operator visibility and auditability (no secrets).

WorkflowOps does NOT own:
- Secret values, encryption keys, or provider credential lifecycle.

---

## 5) Provider compatibility model
Assumptions per provider:
- Can list credentials/connections (metadata only).
- Can deploy/update workflows.
- Has stable credential references in workflow definitions.

Examples:
- n8n: `credentials.<type>.id`.
- Make/Zapier: connection/app-auth references; normalized via adapter.

Adapters handle provider-specific parse/transform of credential references.

---

## 6) UX Model
### 6.1 Environment → Credential Health
Per environment (and provider):
- Logical credential
- Expected type/integration
- Mapping status (valid/missing/incompatible)
- Impacted workflows
No secrets shown.

### 6.2 Workflow → Dependencies
Per workflow:
- Logical credentials used; required vs optional.
- Readiness per environment/provider (Dev/Staging/Prod).
Read-only, auto-derived.

### 6.3 Promotion Gate
On promotion (e.g., Dev → Staging, provider-scoped):
- Preflight validation:
  - All required logical creds mapped in target env/provider.
  - Types/integrations compatible.
  - Environment boundaries respected.
- If fails: block; show actionable errors; direct user to fix target env mapping.

---

## 7) Promotion behavior (critical path)
On successful promotion (per provider):
1) Retrieve workflow definition from source env/provider.  
2) Resolve logical credential references using target env/provider mappings.  
3) Rewrite definition with target physical credential references (adapter-specific).  
4) Deploy to target env via provider adapter.  
5) Secrets are never copied or touched—only references change.

---

## 8) Data model (high level, provider-aware)
- Logical credentials (tenant-scoped, provider-agnostic): `id`, `name`, `description`, `required_type`.
- Credential mappings (env + provider scoped): `logical_credential_id`, `environment_id`, `provider`, `physical_credential_id`, `physical_name`, `physical_type`, `status`.
- Workflow dependency index (per workflow, per provider): `workflow_id`, `provider`, `logical_credential_ids[]`.
- Audit/logs store `provider` for all mapping and promotion actions.

---

## 9) API/Service requirements
- List logical credentials (tenant).
- Manage mappings (logical → physical) per environment and provider.
- Discover workflow dependencies (adapter parses workflow JSON).
- Validate promotion (per provider) with clear errors on missing/incompatible mappings.
- Rewrite workflow definitions with mapped credential references before deploy (adapter-specific).
- Audit every mapping change and promotion validation/deploy with `provider`, actor, env, logical credential, outcome.

---

## 10) UI requirements
- Provider-aware views; hide provider selector if only one provider is active.
- Environment Credential Health: filter by provider; show mapping status.
- Workflow Dependencies: show logical creds and readiness by environment/provider.
- Promotion dialog: show preflight results; block on missing/incompatible mappings with actionable messages.
- No secret values shown—only names/ids/types/status.
- Provider badge/column when multiple providers exist.

---

## 11) Non-Functional
- Backward compatible: single-provider (n8n) flows unchanged; default provider assumed when not specified.
- No secrets exposure; only metadata handled.
- Performance: index mappings on (environment, provider, logical_credential); cache dependency lookups where safe.
- Auditability: all actions log provider, actor, env, logical credential, outcome.

---

## 12) Success Criteria
- Promotions fail fast when target env/provider mappings are missing or incompatible.
- No secrets are stored or transferred.
- Operators see exactly what to fix (which logical credential, which environment/provider).
- Works for n8n now; adapters enable other providers without changing the UX. 
# creds_across_envs.md

# Credential-Safe Workflow Promotion Across Environments  
## Platform-Generic Specification (n8n, Make, Zapier Compatible)

---

## 1. Purpose

The purpose of this specification is to define a **platform-agnostic mechanism** for promoting workflows across environments **without exposing, copying, or managing secrets**.

The system (referred to here as **WorkflowOps**) must:

- Promote **workflow definitions only**
- Enforce **credential correctness per environment**
- Prevent runtime failures caused by missing or mismatched credentials
- Provide clear, pre-deployment validation and operator feedback

WorkflowOps must **never**:

- Store secret values
- Transfer credentials between environments
- Decrypt or display credential contents
- Act as a secrets manager

This specification applies generically to workflow platforms such as **n8n, Make, Zapier**, and similar tools, while remaining fully compatible with n8n’s current API and security constraints.

---

## 2. Non-Goals (Explicit)

The following are intentionally out of scope:

- Secret storage or vaulting
- Credential creation or editing
- Cross-environment credential cloning
- Secret rotation or lifecycle management
- Platform-specific encryption internals

If a capability requires plaintext secrets, it does not belong in WorkflowOps.

---

## 3. Core Concepts

### 3.1 Logical Credentials (Alias Layer)

A **logical credential** is a stable, environment-agnostic identifier representing a required integration or secret dependency.

Examples:
- `stripe_primary`
- `sendgrid_main`
- `db_main`

Logical credentials:

- Contain **no secret values**
- Are referenced by workflows (directly or via metadata)
- Are mapped to platform-specific credentials **per environment**

This mirrors established DevOps patterns:
- GitHub Actions environment secrets
- Terraform variables per workspace
- Kubernetes Secrets per namespace

---

### 3.2 Physical Credentials (Platform-Owned)

Physical credentials:

- Exist natively inside each workflow platform
- Are encrypted and managed by that platform
- Are environment-specific by design

Examples:
- n8n credential records
- Make connections
- Zapier app connections

WorkflowOps interacts with physical credentials **only via metadata**:
- ID or reference
- Name
- Type / integration
- Existence and compatibility

Secrets are never accessed or transferred.

---

## 4. System Responsibilities

### 4.1 What WorkflowOps Owns

- Logical credential definitions
- Environment-specific credential mappings
- Dependency discovery from workflows
- Promotion validation and gating
- Workflow definition rewriting (credential references only)
- Operator visibility and auditability

---

### 4.2 What WorkflowOps Does Not Own

- Secret values
- Encryption keys
- Credential encryption or decryption
- Credential lifecycle inside the workflow platform

---

## 5. Platform Compatibility Model

WorkflowOps assumes each supported platform provides:

- A way to **list credentials or connections** (metadata only)
- A way to **deploy workflows** programmatically
- Stable credential references within workflow definitions

### Example Mapping by Platform

| Platform | Physical Credential | Reference in Workflow |
|--------|---------------------|-----------------------|
| n8n | Credential record | `credentials.<type>.id` |
| Make | Connection | Connection UUID |
| Zapier | App connection | App auth reference |

WorkflowOps normalizes these differences internally via platform adapters.

---

## 6. User Experience Model

### 6.1 Environment → Credential Health

Each environment exposes a **Credential Health** view.

**Purpose**  
Determine whether workflows can be safely deployed into the environment.

**Displayed per environment**:
- Logical credential name
- Expected credential type or integration
- Mapping status (valid / missing / incompatible)
- Impacted workflows

No secret data is displayed.

---

### 6.2 Workflow → Dependencies

Each workflow exposes a **Dependencies** view.

**Purpose**  
Show what the workflow requires to run correctly across environments.

**Displayed**:
- Logical credentials used
- Required vs optional
- Readiness per environment (e.g., Dev / Staging / Prod)

This view is read-only and automatically derived.

---

### 6.3 Deployment / Promotion Gate

During promotion (e.g., Dev → Staging):

WorkflowOps performs a **preflight validation**:

- All required logical credentials are mapped
- Credential types or integrations are compatible
- Environment boundaries are respected

If validation fails:
- Promotion is blocked
- A clear, actionable error is shown
- The user is directed to fix the **environment**, not the workflow

---

## 7. Promotion Behavior (Critical)

When promotion succeeds:

1. The workflow definition is retrieved from the source environment
2. Logical credential references are resolved:
