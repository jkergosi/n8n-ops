# Implementation Plan — Credential-Safe Promotion (Provider-Aware)

Scope: Implement `reqs_creds_across_envs.md` in the existing architecture (n8n now; provider-ready).

## Phase 1 — Data Model & Backend Foundations
- Add schema:
  - `logical_credentials` (tenant-scoped): id, tenant_id, name, description, required_type, created_at.
  - `credential_mappings` (env+provider-scoped): id, logical_credential_id, environment_id, provider, physical_credential_id, physical_name, physical_type, status, created_at, updated_at.
  - `workflow_credential_dependencies` (per workflow, per provider): id, workflow_id, provider, logical_credential_ids (array/json), updated_at.
  - Indexes: (tenant_id, name) on logical_credentials; (environment_id, provider, logical_credential_id) on credential_mappings; (workflow_id, provider) on dependencies.
- Migrations for Postgres/Supabase.
- Backend services/APIs:
  - CRUD logical credentials (tenant-scoped).
  - CRUD mappings per environment+provider.
  - Dependency discovery: adapter parses workflow JSON → stores logical_credential_ids.
  - Promotion preflight (admin/promotion service):
    - Input: tenant_id, source_env, target_env, provider, workflow_ids (or selection).
    - Validate mappings exist and types compatible; return actionable errors.
  - Promotion rewrite:
    - Adapter replaces logical references with target physical credentials before deploy.
  - Audit logging: include provider, logical_credential_id, mapping_id, workflow_ids.
- Provider adapters:
  - n8n adapter: parse credential references (credentials.<type>.id), map logical→physical, rewrite payload.
  - Interface ready for other providers.

## Phase 2 — Frontend (Admin)
- UI additions:
  - Environment Credential Health (per env/provider): table of logical creds, expected type, mapping status, impacted workflows.
  - Workflow Dependencies: show logical creds used, required/optional, readiness per env/provider.
  - Promotion dialog: preflight results; block on missing/incompatible mappings; show provider badge.
- API client methods to support new endpoints.
- Provider-aware filtering; hide provider selector if only one provider active.
- No secret display; only metadata/status.

## Phase 3 — Integration & QA
- Wire promotion flow to call preflight + rewrite before deploy.
- Ensure credential create/edit remains provider-pass-through only; no local secret storage.
- Tests:
  - Unit: mapping resolution, rewrite, preflight validation.
  - Integration: promotion succeeds with valid mappings; blocks without.
  - UI: Credential Health, Dependencies, Promotion preflight states.
- Observability/Audit: verify audit entries include provider and mapping context.

