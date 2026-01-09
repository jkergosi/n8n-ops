# 09 - API Endpoint Inventory

## Summary Statistics

**Evidence:** `n8n-ops-backend/app/api/endpoints/` directory contains 51 files (50 .py, 1 .md)

- **Total Endpoints**: ~344 (estimated from router registrations + new endpoints: 8 alert rules + 6 bulk ops + 3 SSE)
- **Endpoint Modules**: 51 files in `n8n-ops-backend/app/api/endpoints/`
- **API Prefix**: `/api/v1` (from `n8n-ops-backend/app/core/config.py:25`)

---

## Endpoint Categories

### Authentication & Authorization (13 endpoints)

| Method | Path | Auth | Tenant Scope | Entitlements | Audit Logged | Handler |
|--------|------|------|--------------|--------------|--------------|---------|
| POST | `/auth/register` | None | N/A | None | Yes | `auth.py:register` |
| POST | `/auth/login` | None | N/A | None | Yes | `auth.py:login` |
| POST | `/auth/logout` | JWT | User tenant | None | Yes | `auth.py:logout` |
| GET | `/auth/me` | JWT | User tenant | None | No | `auth.py:get_current_user_info` |
| POST | `/auth/refresh` | JWT | User tenant | None | No | `auth.py:refresh_token` |
| POST | `/auth/forgot-password` | None | N/A | None | Yes | `auth.py:forgot_password` |
| POST | `/auth/reset-password` | Token | N/A | None | Yes | `auth.py:reset_password` |
| POST | `/auth/verify-email` | Token | N/A | None | Yes | `auth.py:verify_email` |
| POST | `/auth/resend-verification` | JWT | User tenant | None | No | `auth.py:resend_verification` |
| POST | `/auth/change-password` | JWT | User tenant | None | Yes | `auth.py:change_password` |
| GET | `/auth/sessions` | JWT | User tenant | None | No | `auth.py:list_sessions` |
| DELETE | `/auth/sessions/{id}` | JWT | User tenant | None | Yes | `auth.py:revoke_session` |
| POST | `/onboard` | JWT | User tenant | None | Yes | `tenants.py:onboard_tenant` |

### Environments (17 endpoints)

| Method | Path | Auth | Tenant Scope | Entitlements | Audit Logged | Handler |
|--------|------|------|--------------|--------------|--------------|---------|
| GET | `/environments` | JWT | User tenant | None | No | `environments.py:list_environments` |
| POST | `/environments` | JWT | User tenant | `environment_limits` | Yes | `environments.py:create_environment` |
| GET | `/environments/{id}` | JWT | User tenant | None | No | `environments.py:get_environment` |
| PUT | `/environments/{id}` | JWT | User tenant | None | Yes | `environments.py:update_environment` |
| DELETE | `/environments/{id}` | JWT | User tenant | None | Yes | `environments.py:delete_environment` |
| POST | `/environments/{id}/test-connection` | JWT | User tenant | None | No | `environments.py:test_connection` |
| POST | `/environments/{id}/sync` | JWT | User tenant | None | Yes | `environments.py:sync_environment` |
| POST | `/environments/{id}/sync-workflows` | JWT | User tenant | None | Yes | `environments.py:sync_workflows` |
| POST | `/environments/{id}/sync-credentials` | JWT | User tenant | None | Yes | `environments.py:sync_credentials` |
| POST | `/environments/{id}/sync-executions` | JWT | User tenant | None | Yes | `environments.py:sync_executions` |
| GET | `/environments/{id}/sync-status` | JWT | User tenant | None | No | `environments.py:get_sync_status` |
| POST | `/environments/{id}/github-test` | JWT | User tenant | None | No | `environments.py:test_github` |
| POST | `/environments/{id}/backup` | JWT | User tenant | `snapshots_enabled` | Yes | `environments.py:backup_environment` |
| GET | `/environments/{id}/capabilities` | JWT | User tenant | None | No | `environment_capabilities.py:get_capabilities` |
| GET | `/environments/{id}/health` | JWT | User tenant | None | No | `environments.py:check_health` |
| POST | `/environments/{id}/restore` | JWT | User tenant | `snapshots_enabled` | Yes | `restore.py:restore_environment` |
| GET | `/environments/{id}/drift` | JWT | User tenant | `drift_detection_enabled` | No | `environments.py:check_drift` |

### Workflows (17 endpoints)

| Method | Path | Auth | Tenant Scope | Entitlements | Audit Logged | Handler |
|--------|------|------|--------------|--------------|--------------|---------|
| GET | `/workflows` | JWT | User tenant | None | No | `workflows.py:list_workflows` |
| POST | `/workflows` | JWT | User tenant | None | Yes | `workflows.py:create_workflow` |
| GET | `/workflows/{id}` | JWT | User tenant | None | No | `workflows.py:get_workflow` |
| PUT | `/workflows/{id}` | JWT | User tenant | None | Yes | `workflows.py:update_workflow` |
| DELETE | `/workflows/{id}` | JWT | User tenant | None | Yes | `workflows.py:delete_workflow` |
| POST | `/workflows/{id}/activate` | JWT | User tenant | Policy guard | Yes | `workflows.py:activate_workflow` |
| POST | `/workflows/{id}/deactivate` | JWT | User tenant | Policy guard | Yes | `workflows.py:deactivate_workflow` |
| POST | `/workflows/upload` | JWT | User tenant | None | Yes | `workflows.py:upload_workflows` |
| POST | `/workflows/{id}/backup` | JWT | User tenant | `snapshots_enabled` | Yes | `workflows.py:backup_workflow` |
| POST | `/workflows/{id}/restore` | JWT | User tenant | `snapshots_enabled` | Yes | `restore.py:restore_workflow` |
| GET | `/workflows/{id}/history` | JWT | User tenant | None | No | `workflows.py:get_workflow_history` |
| GET | `/workflows/{id}/analysis` | JWT | User tenant | None | No | `workflows.py:analyze_workflow` |
| POST | `/workflows/{id}/archive` | JWT | User tenant | None | Yes | `workflows.py:archive_workflow` |
| POST | `/workflows/{id}/unarchive` | JWT | User tenant | None | Yes | `workflows.py:unarchive_workflow` |
| GET | `/workflows/{id}/dependencies` | JWT | User tenant | None | No | `workflows.py:get_dependencies` |
| GET | `/workflows/matrix` | JWT | User tenant | `canonical_workflows_enabled` | No | `workflow_matrix.py:get_matrix` |
| POST | `/workflows/{id}/policy-check` | JWT | User tenant | None | No | `workflow_policy.py:check_policy` |

### Canonical Workflows (13 endpoints)

| Method | Path | Auth | Tenant Scope | Entitlements | Audit Logged | Handler |
|--------|------|------|--------------|--------------|--------------|---------|
| GET | `/canonical/workflows` | JWT | User tenant | `canonical_workflows_enabled` | No | `canonical_workflows.py:list_canonical` |
| GET | `/canonical/workflows/{id}` | JWT | User tenant | `canonical_workflows_enabled` | No | `canonical_workflows.py:get_canonical` |
| POST | `/canonical/sync-repo` | JWT | User tenant | `canonical_workflows_enabled` | Yes | `canonical_workflows.py:sync_repo` |
| POST | `/canonical/sync-environment/{id}` | JWT | User tenant | `canonical_workflows_enabled` | Yes | `canonical_workflows.py:sync_environment` |
| POST | `/canonical/reconcile` | JWT | User tenant | `canonical_workflows_enabled` | Yes | `canonical_workflows.py:reconcile` |
| GET | `/canonical/untracked` | JWT | User tenant | `canonical_workflows_enabled` | No | `untracked_workflows.py:list_untracked` |
| POST | `/canonical/link` | JWT | User tenant | `canonical_workflows_enabled` | Yes | `untracked_workflows.py:link_workflow` |
| GET | `/canonical/onboard/preflight` | JWT | User tenant | `canonical_workflows_enabled` | No | `canonical_workflows.py:preflight_check` |
| POST | `/canonical/onboard/inventory` | JWT | User tenant | `canonical_workflows_enabled` | Yes | `canonical_workflows.py:start_inventory` |
| GET | `/canonical/onboard/completion` | JWT | User tenant | `canonical_workflows_enabled` | No | `canonical_workflows.py:check_completion` |
| POST | `/canonical/onboard/create-pr` | JWT | User tenant | `canonical_workflows_enabled` | Yes | `canonical_workflows.py:create_migration_pr` |
| GET | `/canonical/matrix` | JWT | User tenant | `canonical_workflows_enabled` | No | `workflow_matrix.py:get_canonical_matrix` |
| POST | `/canonical/bulk-link` | JWT | User tenant | `canonical_workflows_enabled` | Yes | `untracked_workflows.py:bulk_link` |

### Pipelines (7 endpoints)

| Method | Path | Auth | Tenant Scope | Entitlements | Audit Logged | Handler |
|--------|------|------|--------------|--------------|--------------|---------|
| GET | `/pipelines` | JWT | User tenant | `promotions_enabled` | No | `pipelines.py:list_pipelines` |
| POST | `/pipelines` | JWT | User tenant | `workflow_ci_cd` + Admin (`require_tenant_admin`) | Yes | `pipelines.py:create_pipeline` (line 124) |
| GET | `/pipelines/{id}` | JWT | User tenant | `promotions_enabled` | No | `pipelines.py:get_pipeline` |
| PATCH | `/pipelines/{id}` | JWT | User tenant | `workflow_ci_cd` + Admin (`require_tenant_admin`) | Yes | `pipelines.py:update_pipeline` (line 224) |
| DELETE | `/pipelines/{id}` | JWT | User tenant | `workflow_ci_cd` + Admin (`require_tenant_admin`) | Yes | `pipelines.py:delete_pipeline` (line 334) |
| POST | `/pipelines/{id}/activate` | JWT | User tenant | `promotions_enabled` | Yes | `pipelines.py:activate_pipeline` |
| POST | `/pipelines/{id}/deactivate` | JWT | User tenant | `promotions_enabled` | Yes | `pipelines.py:deactivate_pipeline` |

### Promotions (12 endpoints)

| Method | Path | Auth | Tenant Scope | Entitlements | Audit Logged | Handler |
|--------|------|------|--------------|--------------|--------------|---------|
| GET | `/promotions` | JWT | User tenant | `promotions_enabled` | No | `promotions.py:list_promotions` |
| POST | `/promotions` | JWT | User tenant | `promotions_enabled` | Yes | `promotions.py:create_promotion` |
| GET | `/promotions/{id}` | JWT | User tenant | `promotions_enabled` | No | `promotions.py:get_promotion` |
| POST | `/promotions/validate` | JWT | User tenant | `promotions_enabled` | No | `promotions.py:validate_promotion` |
| POST | `/promotions/compare` | JWT | User tenant | `promotions_enabled` | No | `promotions.py:compare_environments` |
| POST | `/promotions/{id}/execute` | JWT | User tenant | `promotions_enabled` + Admin + Gates | Yes | `promotions.py:execute_promotion` |
| POST | `/promotions/{id}/approve` | JWT | User tenant | `promotions_enabled` | Yes | `promotions.py:approve_promotion` |
| POST | `/promotions/{id}/reject` | JWT | User tenant | `promotions_enabled` | Yes | `promotions.py:reject_promotion` |
| POST | `/promotions/{id}/cancel` | JWT | User tenant | `promotions_enabled` | Yes | `promotions.py:cancel_promotion` |
| GET | `/promotions/{id}/diff` | JWT | User tenant | `promotions_enabled` | No | `promotions.py:get_promotion_diff` |
| GET | `/promotions/drift-check/{env_id}` | JWT | User tenant | `drift_detection_enabled` | No | `promotions.py:check_drift_policy_blocking` |
| POST | `/promotions/{id}/rollback` | JWT | User tenant | `promotions_enabled` | Yes | `promotions.py:rollback_promotion` |

### Deployments (5 endpoints)

| Method | Path | Auth | Tenant Scope | Entitlements | Audit Logged | Handler |
|--------|------|------|--------------|--------------|--------------|---------|
| GET | `/deployments` | JWT | User tenant | None | No | `deployments.py:list_deployments` |
| POST | `/deployments` | JWT | User tenant | `promotions_enabled` | Yes | `deployments.py:create_deployment` |
| GET | `/deployments/{id}` | JWT | User tenant | None | No | `deployments.py:get_deployment` |
| POST | `/deployments/{id}/cancel` | JWT | User tenant | None | Yes | `deployments.py:cancel_deployment` |
| DELETE | `/deployments/{id}` | JWT | User tenant | None | Yes | `deployments.py:delete_deployment` |

### Drift & Incidents (12 endpoints)

| Method | Path | Auth | Tenant Scope | Entitlements | Audit Logged | Handler |
|--------|------|------|--------------|--------------|--------------|---------|
| GET | `/incidents` | JWT | User tenant | `drift_detection_enabled` | No | `incidents.py:list_incidents` |
| GET | `/incidents/{id}` | JWT | User tenant | `drift_detection_enabled` | No | `incidents.py:get_incident` |
| POST | `/incidents/check-drift` | JWT | User tenant | `drift_detection_enabled` | Yes | `incidents.py:check_drift` |
| POST | `/incidents/{id}/acknowledge` | JWT | User tenant | `drift_detection_enabled` | Yes | `incidents.py:acknowledge_incident` |
| POST | `/incidents/{id}/stabilize` | JWT | User tenant | `drift_detection_enabled` | Yes | `incidents.py:stabilize_incident` |
| POST | `/incidents/{id}/reconcile` | JWT | User tenant | `drift_detection_enabled` | Yes | `incidents.py:reconcile_incident` |
| POST | `/incidents/{id}/close` | JWT | User tenant | `drift_detection_enabled` | Yes | `incidents.py:close_incident` |
| POST | `/incidents/{id}/extend-ttl` | JWT | User tenant | `drift_ttl_sla` | Yes | `incidents.py:extend_ttl` |
| PUT | `/incidents/{id}` | JWT | User tenant | `drift_detection_enabled` | Yes | `incidents.py:update_incident` |
| DELETE | `/incidents/{id}` | JWT | User tenant | `drift_detection_enabled` | Yes | `incidents.py:delete_incident` |
| GET | `/drift-policies` | JWT | User tenant | `drift_ttl_sla` | No | `drift_policies.py:get_policies` |
| POST | `/drift-policies` | JWT | User tenant | `drift_ttl_sla` | Yes | `drift_policies.py:create_or_update_policy` |

### Platform Admin (10 endpoints)

| Method | Path | Auth | Tenant Scope | Entitlements | Audit Logged | Handler |
|--------|------|------|--------------|--------------|--------------|---------|
| GET | `/platform/admins` | Platform Admin | Cross-tenant | None | No | `platform_admins.py:list_admins` |
| POST | `/platform/admins` | Platform Admin | Cross-tenant | None | Yes | `platform_admins.py:add_admin` |
| DELETE | `/platform/admins/{user_id}` | Platform Admin | Cross-tenant | None | Yes | `platform_admins.py:remove_admin` |
| POST | `/platform/impersonate` | Platform Admin | Cross-tenant | None | Yes | `platform_impersonation.py:start_impersonation` |
| POST | `/platform/end-impersonation` | Platform Admin | Cross-tenant | None | Yes | `platform_impersonation.py:end_impersonation` |
| GET | `/platform/impersonation/sessions` | Platform Admin | Cross-tenant | None | No | `platform_impersonation.py:list_sessions` |
| GET | `/platform/console/search` | Platform Admin | Cross-tenant | None | No | `platform_console.py:search_tenants` |
| GET | `/platform/console/tenants/{id}` | Platform Admin | Cross-tenant | None | No | `platform_console.py:get_tenant` |
| GET | `/platform/console/tenants/{id}/users` | Platform Admin | Cross-tenant | None | No | `platform_console.py:list_tenant_users` |
| GET | `/platform` | Platform Admin | Cross-tenant | None | No | `platform_overview.py:get_platform_overview` |

**Note**: Platform admin endpoints exempt from tenant isolation by design. Protected by `require_platform_admin()` guard.

### Alert Rules & Notifications (8 endpoints)

| Method | Path | Auth | Tenant Scope | Entitlements | Audit Logged | Handler |
|--------|------|------|--------------|--------------|--------------|---------|
| GET | `/notifications/alert-rules` | JWT | User tenant | `alerts_enabled` | No | `alert_rules.py:list_alert_rules` |
| POST | `/notifications/alert-rules` | JWT | User tenant | `alerts_enabled` | Yes | `alert_rules.py:create_alert_rule` |
| GET | `/notifications/alert-rules/{id}` | JWT | User tenant | `alerts_enabled` | No | `alert_rules.py:get_alert_rule` |
| PUT | `/notifications/alert-rules/{id}` | JWT | User tenant | `alerts_enabled` | Yes | `alert_rules.py:update_alert_rule` |
| DELETE | `/notifications/alert-rules/{id}` | JWT | User tenant | `alerts_enabled` | Yes | `alert_rules.py:delete_alert_rule` |
| POST | `/notifications/alert-rules/{id}/test` | JWT | User tenant | `alerts_enabled` | No | `alert_rules.py:test_alert_rule` |
| GET | `/notifications/alert-rules/{id}/history` | JWT | User tenant | `alerts_enabled` | No | `alert_rules.py:get_alert_rule_history` |
| GET | `/notifications/channels` | JWT | User tenant | None | No | `notifications.py:list_notification_channels` |

**Evidence:** `app/services/alert_rules_service.py`, migration `alembic/versions/20260108_add_alert_rules.py`

**Features:**
- Configurable alert conditions (execution failure rate, workflow success rate, drift threshold)
- JSONB conditions for flexible rule configuration
- Periodic evaluation via background scheduler
- Multi-channel notifications (email, Slack, webhook)
- Evaluation history with 30-day retention

### Bulk Operations (6 endpoints)

| Method | Path | Auth | Tenant Scope | Entitlements | Audit Logged | Handler |
|--------|------|------|--------------|--------------|--------------|---------|
| POST | `/executions/bulk-retry` | JWT | User tenant | `workflow_ci_cd` | Yes | `executions.py:bulk_retry_executions` |
| POST | `/executions/bulk-delete` | JWT | User tenant | `workflow_ci_cd` | Yes | `executions.py:bulk_delete_executions` |
| POST | `/executions/bulk-export` | JWT | User tenant | `workflow_ci_cd` | No | `executions.py:bulk_export_executions` |
| POST | `/credentials/bulk-health-check` | JWT | User tenant | `health_checks_enabled` | No | `credentials.py:bulk_health_check` |
| POST | `/workflows/bulk-activate` | JWT | User tenant | `workflow_ci_cd` | Yes | `workflows.py:bulk_activate_workflows` |
| POST | `/workflows/bulk-deactivate` | JWT | User tenant | `workflow_ci_cd` | Yes | `workflows.py:bulk_deactivate_workflows` |

**Evidence:** Bulk operations implemented for execution management, credential health checks, and workflow activation

**Features:**
- Batch processing with configurable batch sizes
- Async job tracking for long-running operations
- Progress reporting via background jobs SSE
- Transaction safety with rollback on failure
- Limit checks to prevent resource exhaustion

### SSE & Live Streaming (3 endpoints)

| Method | Path | Auth | Tenant Scope | Entitlements | Audit Logged | Handler |
|--------|------|------|--------------|--------------|--------------|---------|
| GET | `/sse/deployments` | JWT | User tenant | `workflow_ci_cd` | No | `sse.py:sse_deployments_stream` |
| GET | `/sse/deployments/{id}` | JWT | User tenant | `workflow_ci_cd` | No | `sse.py:sse_deployments_stream` |
| GET | `/sse/background-jobs` | JWT | User tenant | None | No | `sse.py:sse_background_jobs_stream` |
| GET | `/sse/executions/{id}/logs` | JWT | User tenant | `workflow_ci_cd` | No | `sse.py:sse_execution_logs_stream` |

**Evidence:** `app/api/endpoints/sse.py`, frontend: `lib/use-deployments-sse.ts`, `lib/use-background-jobs-sse.ts`

**Features:**
- Real-time deployment status updates
- Live execution log streaming with backpressure handling
- Pub/sub pattern for multi-instance support
- Automatic reconnect with exponential backoff (1s → 30s, max 10 attempts)
- `lastEventId` support for missed event recovery

---

## Endpoint Protection Patterns

### 1. Authentication
- All endpoints except `/auth/register`, `/auth/login`, `/health` require JWT
- JWT extracted via `Depends(get_current_user)` or `Depends(get_current_user_optional)`

### 2. Tenant Isolation
- tenant_id ALWAYS extracted from user context: `user_info["tenant"]["id"]`
- NEVER from path/query params

### 3. RBAC (Role-Based Access)
- Backend-enforced for sensitive tenant actions:
  - Promotions: `POST /promotions/{id}/execute` requires tenant admin + feature
  - Pipelines: create/update/delete requires tenant admin + feature
  - Billing: subscription/checkout/portal/cancel/reactivate/invoices/payment-history require tenant admin
  - Impersonation: admin-only (platform- or tenant-level guards)
- Pattern: dependency guard (`require_tenant_admin()` or `require_platform_admin()`) plus entitlement gate

### 4. Entitlement Gates
- Decorator: `Depends(require_entitlement("feature_name"))`
- Examples: `snapshots_enabled`, `promotions_enabled`, `drift_detection_enabled`

### 5. Environment Policy Guards
- Action guards based on environment_class: dev/staging/production
- Examples: Block direct edit in production, require approval for delete

### 6. Audit Logging
- Write actions (POST, PUT, PATCH, DELETE) logged automatically via middleware
- Manual logging for sensitive operations: `create_audit_log(...)`

---

## High-Risk Endpoints

### Mutation Endpoints (Require Extra Scrutiny)

1. **POST `/environments`** - Creates new environment, checks limit
2. **DELETE `/environments/{id}`** - Deletes environment and all workflows
3. **POST `/promotions/{id}/execute`** - Executes promotion, creates snapshots
4. **POST `/billing/stripe-webhook`** - Processes payments, downgrades
5. **POST `/platform/impersonate`** - Starts impersonation session
6. **DELETE `/workflows/{id}`** - Deletes workflow (hard delete)
7. **POST `/canonical/reconcile`** - Reconciles drift (may overwrite)

### Performance-Sensitive Endpoints

1. **GET `/workflows`** - Lists workflows (pagination required for 1000+)
2. **GET `/workflows/matrix`** - Matrix view (performance risk with 1000+ workflows)
3. **GET `/executions`** - Lists executions (pagination required for 10k+)
4. **GET `/observability/overview`** - Complex aggregations (2s target)
5. **POST `/environments/{id}/sync`** - Syncs workflows (may take minutes)

---

## Gaps & Recommendations

### Missing Endpoints

1. **Workflow Version History**: No endpoint to list workflow versions (n8n maintains version history internally)
2. **Audit Log Export**: No dedicated endpoint to export audit logs as CSV/JSON (can query via database)
3. **Health Check Per Service**: Only overall `/health`, no per-service health breakdown

### Recently Added (2026-01-08)

1. ✅ **Bulk Workflow Operations**: Implemented `/workflows/bulk-activate`, `/workflows/bulk-deactivate`
2. ✅ **Bulk Execution Operations**: Implemented `/executions/bulk-retry`, `/executions/bulk-delete`, `/executions/bulk-export`
3. ✅ **Alert Rules Management**: 8 endpoints for configurable alert rules
4. ✅ **Live Execution Logs**: SSE streaming endpoint `/sse/executions/{id}/logs`

### Recommendations

1. **Add API Rate Limiting**: No rate limiting observed in code (consider for production)
2. **Add Request ID Tracking**: No request ID header for distributed tracing
3. **Add Webhook Management**: No endpoints to manage outbound webhooks (notification channels exist)
4. **Add API Documentation**: Generate OpenAPI spec from FastAPI (FastAPI auto-generates at `/docs`)
5. **Add Workflow Version History API**: Expose n8n's internal version history

