# N8N Ops Platform - Product Requirements Document

## Document Information

| Field | Value |
|-------|-------|
| Product Name | N8N Ops Platform |
| Version | 1.1 |
| Last Updated | January 16, 2026 |
| Status | Production |

---

## 1. Executive Summary

### 1.1 Product Vision

N8N Ops is a multi-tenant workflow governance and lifecycle management platform that enables enterprises to manage n8n automation workflows across multiple environments (development, staging, production). The platform provides policy-based promotion, drift detection, credential management, and comprehensive observability for workflow automation infrastructure.

### 1.2 Problem Statement

Organizations using n8n for workflow automation face critical challenges:

1. **Environment Sprawl**: Managing workflows across multiple n8n instances is manual and error-prone
2. **No Promotion Controls**: Moving workflows between environments lacks governance, approvals, and audit trails
3. **Configuration Drift**: Changes made directly in production go untracked, creating compliance risks
4. **Credential Management**: Mapping credentials across environments is complex and insecure
5. **Limited Visibility**: No centralized view of workflow health, execution metrics, or deployment history
6. **No Version Control**: Workflow changes aren't tracked in Git, making rollback impossible

### 1.3 Solution Overview

N8N Ops provides:

- **Centralized Management**: Single pane of glass for all n8n environments
- **Governed Promotions**: Pipeline-based workflow promotions with gates and approvals
- **Drift Detection**: Automated monitoring and incident management for configuration drift
- **Git Integration**: Full version control with snapshots and restore capabilities
- **Execution Analytics**: Comprehensive metrics and health monitoring
- **Multi-Tenancy**: Complete data isolation with role-based access control
- **Enterprise Features**: SSO, audit logging, compliance tools, and SLA enforcement

---

## 2. User Personas

### 2.1 DevOps Engineer / Platform Lead

**Demographics**: Technical lead responsible for workflow automation infrastructure

**Goals**:
- Ensure workflow governance across all environments
- Minimize production incidents from uncontrolled changes
- Maintain compliance and audit readiness
- Reduce manual deployment overhead

**Pain Points**:
- Manual workflow copying between environments
- No visibility into what changed and when
- Difficult to enforce approval workflows
- Time-consuming troubleshooting of production issues

**Key Features Used**:
- Environment management and configuration
- Promotion pipeline design
- Drift policies and TTL configuration
- Admin dashboards and audit logs

### 2.2 Workflow Developer

**Demographics**: Developer building and maintaining n8n workflows

**Goals**:
- Deploy workflows safely to production
- Understand what's required for promotion
- Track workflow execution and performance
- Quickly identify and fix issues

**Pain Points**:
- Uncertainty about promotion requirements
- No easy way to compare environments
- Limited execution visibility
- Manual rollback procedures

**Key Features Used**:
- Workflow management and upload
- Promotion execution
- Drift dashboard and diff viewer
- Execution analytics

### 2.3 Security/Compliance Officer

**Demographics**: Responsible for security, compliance, and access control

**Goals**:
- Maintain audit trail of all changes
- Control who can access what
- Ensure drift is detected and remediated
- Verify credential security

**Pain Points**:
- Lack of change tracking
- No centralized access control
- Manual compliance verification
- Credential sprawl across environments

**Key Features Used**:
- Audit logs
- Role-based access control
- Drift incident management
- Credential health monitoring

### 2.4 System Administrator (Multi-tenant)

**Demographics**: Platform administrator managing multiple customer tenants

**Goals**:
- Manage customer subscriptions and billing
- Configure feature access per customer
- Handle support requests efficiently
- Monitor platform-wide health

**Pain Points**:
- Managing multiple isolated environments
- Custom feature requests per customer
- Support ticket management
- Usage tracking and billing

**Key Features Used**:
- Tenant administration
- Feature overrides
- Support console
- Usage analytics

---

## 3. Feature Requirements

### 3.1 Environment Management

#### 3.1.1 Environment Configuration

**Description**: Connect and configure multiple n8n instances as managed environments

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| ENV-001 | Create environment with name, URL, and API key | P0 |
| ENV-002 | Test n8n connection before saving | P0 |
| ENV-003 | Configure GitHub repository for backups | P1 |
| ENV-004 | Test GitHub connection | P1 |
| ENV-005 | Assign environment class (dev/staging/production) | P0 |
| ENV-006 | View environment list with sync status | P0 |
| ENV-007 | Delete environment with confirmation | P1 |
| ENV-008 | View environment limits based on plan | P1 |

**Acceptance Criteria**:
- Connection test validates API key and n8n version
- Environment class determines available actions
- Deletion removes all associated workflows and credentials
- Plan limits are enforced (Free: 2, Pro: 10, Enterprise: unlimited)

#### 3.1.2 Environment Synchronization

**Description**: Sync workflow data from n8n instances

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| ENV-009 | Full sync: workflows, credentials, tags, users | P0 |
| ENV-010 | Selective sync: workflows only | P1 |
| ENV-011 | Selective sync: credentials only | P1 |
| ENV-012 | Selective sync: executions only | P1 |
| ENV-013 | Background job with progress tracking | P0 |
| ENV-014 | Live log streaming during sync | P1 |

**Acceptance Criteria**:
- Sync completes within reasonable time for large instances
- Progress updates are shown in real-time
- Errors are logged and reported clearly
- Partial failures don't corrupt existing data

#### 3.1.3 Environment Capabilities

**Description**: Policy-based action guards per environment class

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| ENV-015 | Define action policies per environment class | P0 |
| ENV-016 | Restrict direct edits in production | P0 |
| ENV-017 | Require approvals for certain actions | P1 |
| ENV-018 | Display capability warnings in UI | P0 |

**Environment Class Policies**:
| Action | Development | Staging | Production |
|--------|-------------|---------|------------|
| Direct Edit | Allowed | Warning | Blocked |
| Activate/Deactivate | Allowed | Allowed | Requires Approval |
| Delete | Allowed | Warning | Requires Approval |
| Upload | Allowed | Allowed | Blocked |

### 3.2 Workflow Management

#### 3.2.1 Workflow Catalog

**Description**: Browse and manage workflows across environments

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| WF-001 | List all workflows with search | P0 |
| WF-002 | Filter by environment, tags, status | P0 |
| WF-003 | View workflow details (nodes, connections) | P0 |
| WF-004 | Interactive workflow graph visualization | P1 |
| WF-005 | Workflow complexity analysis | P2 |
| WF-006 | Bulk selection and actions | P1 |

**Acceptance Criteria**:
- Search supports workflow name and node types
- Graph shows all nodes and connections
- Analysis identifies credentials, HTTP calls, triggers

#### 3.2.2 Workflow Operations

**Description**: Perform actions on workflows

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| WF-007 | Upload workflows (JSON/ZIP) | P0 |
| WF-008 | Activate/deactivate workflows | P0 |
| WF-009 | Delete workflows (soft delete) | P0 |
| WF-010 | Hard delete with confirmation | P1 |
| WF-011 | Download workflows as ZIP | P1 |
| WF-012 | Tag management | P1 |

**Acceptance Criteria**:
- Upload validates workflow JSON structure
- Activation respects environment policies
- Soft delete allows recovery
- Hard delete is irreversible with audit log

#### 3.2.3 GitHub Integration

**Description**: Version control workflows in Git

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| WF-013 | Backup workflows to GitHub | P1 |
| WF-014 | Restore workflows from GitHub | P1 |
| WF-015 | View Git drift status | P1 |
| WF-016 | Automatic backup on promotion | P1 |

**Acceptance Criteria**:
- Backup creates commit with workflow metadata
- Restore preserves workflow structure
- Drift detection compares local vs Git
- Git operations are atomic

### 3.3 Promotion Pipeline System

#### 3.3.1 Pipeline Definition

**Description**: Define promotion paths between environments

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| PIPE-001 | Create pipeline with name and description | P0 |
| PIPE-002 | Define ordered stages (source → target) | P0 |
| PIPE-003 | Configure gates per stage | P1 |
| PIPE-004 | Configure approval requirements | P1 |
| PIPE-005 | Set scheduled promotion windows | P2 |
| PIPE-006 | Visual pipeline editor | P1 |

**Gate Types**:
- Drift check required
- Credential availability check
- Manual approval
- Scheduled window
- Custom validation

#### 3.3.2 Promotion Execution

**Description**: Execute workflow promotions through pipelines

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| PROMO-001 | Initiate promotion with workflow selection | P0 |
| PROMO-002 | Pre-flight validation (drift, credentials) | P0 |
| PROMO-003 | Display diff between environments | P0 |
| PROMO-004 | Submit for approval if required | P1 |
| PROMO-005 | Execute promotion atomically | P0 |
| PROMO-006 | Create pre-promotion snapshot | P0 |
| PROMO-007 | Rollback on failure | P1 |

**Promotion States**:
```
PENDING → PENDING_APPROVAL → APPROVED → RUNNING → COMPLETED
                                    ↘ FAILED
                          ↘ REJECTED
            ↘ CANCELLED
```

**Diff Status Types**:
| Status | Description |
|--------|-------------|
| ADDED | Workflow only in source |
| MODIFIED | Exists in both, source is newer |
| DELETED | Workflow only in target |
| UNCHANGED | Identical content |
| TARGET_HOTFIX | Target has newer version (conflict) |

**Risk Levels**:
| Level | Trigger |
|-------|---------|
| LOW | Rename only |
| MEDIUM | Error handling, settings changes |
| HIGH | Credentials, expressions, triggers, HTTP, code, routing |

#### 3.3.3 Deployment Tracking

**Description**: Track deployment history and status

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| DEP-001 | List all deployments with filters | P0 |
| DEP-002 | View deployment details | P0 |
| DEP-003 | View per-workflow deployment results | P1 |
| DEP-004 | Schedule future deployments | P2 |
| DEP-005 | Cancel pending deployments | P1 |

### 3.4 Drift Detection & Incident Management

#### 3.4.1 Drift Detection

**Description**: Identify configuration drift between environments

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| DRIFT-001 | Scheduled drift detection | P1 |
| DRIFT-002 | On-demand drift check | P0 |
| DRIFT-003 | Compare workflow JSON with detailed diff | P0 |
| DRIFT-004 | Detect untracked changes in production | P1 |
| DRIFT-005 | Skip drift detection for DEV environments | P1 |

**Acceptance Criteria**:
- Drift detection runs on configurable schedule
- Diff shows exact changes (nodes, credentials, settings)
- Changes are categorized by risk level

#### 3.4.2 Incident Management

**Description**: Manage drift incidents through lifecycle

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| INC-001 | Create incident when drift detected | P0 |
| INC-002 | Incident severity levels (critical/high/medium/low) | P1 |
| INC-003 | Acknowledge incidents | P0 |
| INC-004 | Resolve incidents with notes | P0 |
| INC-005 | Incident dashboard with filters | P1 |
| INC-006 | Incident notifications | P2 |

**Incident States**:
```
OPEN → ACKNOWLEDGED → RESOLVED
```

#### 3.4.3 Drift Policies

**Description**: Configure drift governance policies

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| POL-001 | Set TTL per severity level | P2 |
| POL-002 | Configure SLA enforcement | P2 |
| POL-003 | Auto-resolve settings | P2 |
| POL-004 | Notification thresholds | P2 |
| POL-005 | Block deployments on drift | P2 |
| POL-006 | Data retention policies | P2 |

**Default TTL Configuration**:
| Severity | Default TTL |
|----------|-------------|
| Critical | 24 hours |
| High | 48 hours |
| Medium | 72 hours |
| Low | 168 hours (1 week) |

### 3.5 Canonical Workflow System

> **Terminology Note**: User-facing: "Source-Managed Workflow" = Internal: "Canonical Workflow". User-facing: "Unmanaged Workflow" = Internal: "Unmapped Workflow".

#### 3.5.1 Canonical Workflow Management

**Description**: Git-backed source of truth for workflows

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| CAN-001 | Track canonical workflow definitions | P1 |
| CAN-002 | Map workflows to environments | P1 |
| CAN-003 | Sync Git repository to canonical state | P1 |
| CAN-004 | Sync environment to canonical state | P1 |
| CAN-005 | Reconcile Git and environment state | P1 |

#### 3.5.2 Unmanaged Workflow Detection

**Description**: Identify workflows not in canonical system

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| CAN-006 | Detect unmanaged workflows | P1 |
| CAN-007 | List unmanaged workflows by environment | P1 |
| CAN-008 | Onboard unmanaged workflows | P1 |
| CAN-009 | Bulk onboarding with smart matching | P1 |
| CAN-010 | Preflight validation before onboarding | P1 |

**Workflow Mapping Statuses**:
| Status | Description |
|--------|-------------|
| LINKED | Has canonical_id, tracked in system |
| UNMAPPED | No canonical_id, needs onboarding |
| MISSING | Was linked/unmapped, now gone from n8n |
| IGNORED | Explicitly ignored by user |
| DELETED | Soft-deleted |

#### 3.5.3 Workflow Matrix

**Description**: Cross-environment workflow status view

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| CAN-011 | Matrix view of workflows across environments | P1 |
| CAN-012 | Show sync status per environment | P1 |
| CAN-013 | Identify missing deployments | P1 |
| CAN-014 | Display drift status (hash comparison) | P1 |

### 3.6 Snapshots & Restore

#### 3.6.1 Snapshot Management

**Description**: Version control for environment state

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| SNAP-001 | Create manual snapshots | P1 |
| SNAP-002 | Auto-snapshot before promotions | P0 |
| SNAP-003 | List snapshots by environment | P0 |
| SNAP-004 | View snapshot metadata | P1 |
| SNAP-005 | Git-backed snapshot storage | P1 |

#### 3.6.2 Restore Operations

**Description**: Restore workflows from snapshots

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| SNAP-006 | Restore single workflow | P1 |
| SNAP-007 | Restore multiple workflows | P1 |
| SNAP-008 | Full environment restore | P2 |
| SNAP-009 | Preview restore diff | P1 |
| SNAP-010 | Rollback state tracking | P1 |

### 3.7 Execution Analytics

#### 3.7.1 Execution Monitoring

**Description**: Track workflow execution history

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| EXEC-001 | List executions with filters | P0 |
| EXEC-002 | Filter by workflow, environment, status | P0 |
| EXEC-003 | View execution details | P1 |
| EXEC-004 | View execution error messages | P1 |

#### 3.7.2 Analytics Dashboard

**Description**: Execution metrics and trends

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| EXEC-005 | Total executions count | P1 |
| EXEC-006 | Success rate calculation | P1 |
| EXEC-007 | Average execution duration | P1 |
| EXEC-008 | Execution trends over time | P2 |
| EXEC-009 | Top failing workflows | P2 |
| EXEC-010 | Performance benchmarking | P2 |

### 3.8 Credentials Management

#### 3.8.1 Credential Viewing

**Description**: View credential metadata (not secrets)

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| CRED-001 | List credentials by environment | P0 |
| CRED-002 | View credential type and usage | P1 |
| CRED-003 | Identify workflows using credential | P1 |

#### 3.8.2 Credential Health

**Description**: Monitor credential status

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| CRED-004 | Track credential health status | P1 |
| CRED-005 | Automatic health validation | P2 |
| CRED-006 | Health alerts and notifications | P2 |
| CRED-007 | Cross-environment credential matrix | P2 |

#### 3.8.3 Credential Remapping

**Description**: Map credentials during promotion

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| CRED-008 | Credential mapping UI | P2 |
| CRED-009 | Auto-detect credential dependencies | P1 |
| CRED-010 | Validate credential availability | P1 |

### 3.9 Bulk Operations

**Description**: Batch operations on multiple resources

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| BULK-001 | Bulk sync multiple environments | P1 |
| BULK-002 | Bulk backup to Git | P1 |
| BULK-003 | Bulk restore from snapshots | P2 |
| BULK-004 | Progress tracking per operation | P1 |
| BULK-005 | Partial failure handling | P1 |

### 3.9.1 Environment States

**Description**: Environment-level drift and sync status tracking

**Environment States (DriftStatus)**:
| Status | Condition | Description |
|--------|-----------|-------------|
| NEW | No baseline exists | Drift detection skipped, awaiting onboarding |
| IN_SYNC | Baseline exists, runtime matches | All workflows match approved versions |
| DRIFT_DETECTED | Baseline exists, runtime differs | One or more workflows differ from approved |
| GIT_UNAVAILABLE | Git repo inaccessible | Repository deleted, forbidden, or unreachable |
| ERROR | Exception during detection | Check failed; see error details |
| UNKNOWN | Never checked | Initial state before first detection |

**UI Labels by Environment Class**:
| DriftStatus | DEV Label | STAGING/PROD Label |
|-------------|-----------|-------------------|
| NEW | "No baseline" | "Not onboarded" |
| IN_SYNC | "Matches baseline" | "Matches approved" |
| DRIFT_DETECTED | "Different from baseline" | "Drift detected" |
| GIT_UNAVAILABLE | "Git unavailable" | "Git unavailable" |

**Action Gating**:
| Action | Condition | Rationale |
|--------|-----------|-----------|
| Revert | Onboarded AND Git accessible | Cannot revert without baseline |
| Keep Hotfix | Onboarded AND Git accessible | Cannot mark hotfix without baseline |
| Save as Approved | Git accessible | Creates or updates baseline |
| Promote | Source onboarded AND Git accessible | Must have baseline to promote |

### 3.9.2 Retention Policies

**Description**: Data lifecycle management with configurable retention periods

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| RET-001 | Execution data retention by plan tier | P1 |
| RET-002 | Activity/audit log retention by plan tier | P1 |
| RET-003 | Snapshot retention by plan tier | P1 |
| RET-004 | Deployment history retention by plan tier | P1 |
| RET-005 | Drift data retention by plan tier | P1 |
| RET-006 | Background job enforcement scheduler | P1 |

**Default Retention by Plan**:
| Data Type | Free | Pro | Agency | Enterprise |
|-----------|------|-----|--------|------------|
| Executions | 7 days | 30 days | 90 days | 365 days |
| Audit Logs | 7 days | 90 days | 180 days | Unlimited |
| Snapshots | 7 days | 30 days | 90 days | 365 days |
| Deployments | 7 days | 30 days | 90 days | 365 days |

### 3.9.3 Git-Based Promotions

**Description**: Target-ownership snapshot system for workflow promotion

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| GITPROMO-001 | Create pre-promotion snapshot on target | P0 |
| GITPROMO-002 | Git-backed promotion audit trail | P1 |
| GITPROMO-003 | PROD hotfix "keep" behavior | P1 |
| GITPROMO-004 | Rollback to pre-promotion state | P1 |
| GITPROMO-005 | Upload restriction on STAGING/PROD | P1 |

**PROD Hotfix Handling**:
- Hotfixes made directly in PROD can be "kept" (approved)
- Kept hotfixes update the Git baseline to match PROD state
- Prevents drift alerts for intentional production fixes

### 3.10 Team & Access Management

#### 3.10.1 Team Management

**Description**: Manage team members and roles

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| TEAM-001 | Invite team members by email | P0 |
| TEAM-002 | Assign roles (admin/developer/viewer) | P0 |
| TEAM-003 | Remove team members | P0 |
| TEAM-004 | View team member list | P0 |
| TEAM-005 | Team member limits per plan | P1 |

#### 3.10.2 Role-Based Access Control

**Description**: Permission system based on roles

**Role Permissions**:
| Permission | Viewer | Developer | Admin |
|------------|--------|-----------|-------|
| View workflows | Yes | Yes | Yes |
| Upload workflows | No | Yes | Yes |
| Execute promotions | No | Yes | Yes |
| Configure pipelines | No | No | Yes |
| Manage team | No | No | Yes |
| Access billing | No | No | Yes |
| View audit logs | No | No | Yes |
| Configure drift policies | No | No | Yes |

### 3.11 Billing & Subscriptions

#### 3.11.1 Subscription Management

**Description**: Stripe-based billing integration

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| BILL-001 | View current subscription | P0 |
| BILL-002 | Upgrade/downgrade plan | P0 |
| BILL-003 | Update payment method | P0 |
| BILL-004 | View billing history | P1 |
| BILL-005 | Cancel subscription | P0 |

#### 3.11.2 Plan Tiers

| Feature | Free | Pro | Agency | Enterprise |
|---------|------|-----|--------|------------|
| **Price** | $0 | $299/mo | Custom | Custom |
| **Environments** | 2 | 10 | Unlimited | Unlimited |
| **Team Members** | 3 | 10 | Unlimited | Unlimited |
| **Workflows** | Unlimited | Unlimited | Unlimited | Unlimited |
| GitHub Backup/Restore | No | Yes | Yes | Yes |
| Environment Promotion | No | Yes | Yes | Yes |
| Scheduled Backups | No | Yes | Yes | Yes |
| Workflow Diff | No | Yes | Yes | Yes |
| Full Drift Diff | No | No | Yes | Yes |
| Drift TTL/SLA | No | No | Yes | Yes |
| Drift Policies | No | No | No | Yes |
| Execution Metrics | No | Yes | Yes | Yes |
| Alerting | No | Yes | Yes | Yes |
| Role-Based Access | No | Yes | Yes | Yes |
| **Data Retention** | | | | |
| - Executions | 7 days | 30 days | 90 days | 365 days |
| - Audit Logs | 7 days | 90 days | 180 days | Unlimited |
| - Snapshots | 7 days | 30 days | 90 days | 365 days |
| - Deployments | 7 days | 30 days | 90 days | 365 days |
| Credential Remapping | No | No | No | Yes |
| SSO/SCIM | No | No | No | Yes |
| **Support** | Community | Email | Priority | Dedicated |

### 3.12 Admin Portal

**Description**: Tenant-level system administration features (21 pages)

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| ADMIN-001 | Admin dashboard overview | P0 |
| ADMIN-002 | Audit logs viewer | P1 |
| ADMIN-003 | Credential health monitoring | P1 |
| ADMIN-004 | Drift policies configuration | P1 |
| ADMIN-005 | Entitlements audit | P1 |
| ADMIN-006 | Feature matrix configuration | P1 |
| ADMIN-007 | Notifications management | P1 |
| ADMIN-008 | Performance metrics | P2 |
| ADMIN-009 | Plans management | P1 |
| ADMIN-010 | Retention settings | P1 |
| ADMIN-011 | Security settings | P1 |
| ADMIN-012 | Support configuration | P2 |
| ADMIN-013 | Support requests management | P1 |
| ADMIN-014 | System billing overview | P1 |
| ADMIN-015 | Tenant detail view | P1 |
| ADMIN-016 | Tenant overrides configuration | P2 |
| ADMIN-017 | Tenant providers configuration | P2 |
| ADMIN-018 | Tenant settings | P1 |
| ADMIN-019 | Tenants list | P0 |
| ADMIN-020 | Usage statistics | P1 |
| ADMIN-021 | General settings | P1 |

### 3.12.1 Platform Console

**Description**: Cross-tenant platform administration (4 pages)

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| PLAT-001 | Platform dashboard with system-wide metrics | P1 |
| PLAT-002 | Platform admins management | P1 |
| PLAT-003 | Tenant user/role management | P1 |
| PLAT-004 | Support console for cross-tenant support | P1 |
| PLAT-005 | Tenant impersonation for debugging | P2 |
| PLAT-006 | Impersonation audit logging | P1 |

### 3.13 Support System

**Description**: User support ticket management

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| SUPP-001 | Submit bug reports | P1 |
| SUPP-002 | Request features | P1 |
| SUPP-003 | Get help with issues | P1 |
| SUPP-004 | Attach files to tickets | P2 |
| SUPP-005 | Track ticket status | P1 |
| SUPP-006 | Admin support console | P1 |

### 3.14 Real-Time Updates

**Description**: Server-Sent Events for live updates

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| SSE-001 | Background job progress streaming | P0 |
| SSE-002 | Live log output during operations | P1 |
| SSE-003 | Deployment status updates | P1 |
| SSE-004 | Auto-reconnect on disconnect | P1 |

### 3.15 Health Monitoring

**Description**: System health and connectivity monitoring

**Requirements**:
| ID | Requirement | Priority |
|----|-------------|----------|
| HEALTH-001 | Backend health check endpoint | P0 |
| HEALTH-002 | Environment heartbeat tracking | P1 |
| HEALTH-003 | Connection status indicator | P1 |
| HEALTH-004 | Graceful degradation page | P1 |
| HEALTH-005 | Automatic health polling | P1 |

---

## 4. Technical Architecture

### 4.1 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend: React + TanStack Query + Zustand + shadcn/ui         │
│  app-front/ (Vite, TypeScript)                                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST API + SSE
┌──────────────────────────▼──────────────────────────────────────┐
│  Backend: FastAPI + Pydantic + httpx                            │
│  app-back/ (Python 3.11+, async)                         │
└──────┬─────────────────────┬─────────────────────┬──────────────┘
       │                     │                     │
┌──────▼──────┐    ┌─────────▼─────────┐   ┌──────▼──────┐
│  Supabase   │    │  N8N Instances    │   │   GitHub    │
│  PostgreSQL │    │  REST API         │   │   Repos     │
└─────────────┘    └───────────────────┘   └─────────────┘
       │
┌──────▼──────┐
│   Stripe    │
│  Payments   │
└─────────────┘
```

### 4.2 Technology Stack

**Frontend**:
- React 18 with TypeScript
- TanStack Query (server state)
- Zustand (client state)
- shadcn/ui + Tailwind CSS
- React Flow (graph visualization)
- Vite (build tool)

**Backend**:
- FastAPI (Python 3.11+)
- Pydantic (validation)
- httpx (async HTTP)
- PyGithub (Git integration)

**Database**:
- Supabase (PostgreSQL)
- Row-level security
- JSONB for flexible data

**External Services**:
- Stripe (payments)
- Auth0 (authentication)
- GitHub (version control)

### 4.2.1 Background Job Schedulers

The backend runs 8 background schedulers for automated operations:

| Scheduler | Purpose | Default Interval |
|-----------|---------|-----------------|
| Deployment Scheduler | Execute scheduled deployments | On-demand |
| Drift Detection Scheduler | Periodic drift checks | Configurable per tenant |
| Canonical Sync Scheduler | Sync canonical workflows with Git | Hourly |
| Health Check Scheduler | Monitor environment health | 5 minutes |
| Rollup Scheduler | Pre-compute observability rollups | 15 minutes |
| Retention Enforcement | Enforce data retention policies | Daily |
| Downgrade Enforcement | Enforce grace period expiry | Hourly |
| Alert Rules Evaluation | Evaluate alert rules and trigger notifications | Configurable |

All schedulers start on application startup and gracefully stop on shutdown.

### 4.3 Multi-Tenancy

- Complete data isolation per tenant
- All queries filtered by `tenant_id`
- Row-level security in database
- Per-tenant feature configuration
- Isolated background job queues

### 4.4 Security

- JWT-based authentication
- Role-based access control
- API key encryption at rest
- Audit logging for all actions
- No credential secret exposure

---

## 5. Non-Functional Requirements

### 5.1 Performance

| Metric | Target |
|--------|--------|
| API Response Time (p95) | < 500ms |
| Page Load Time | < 2s |
| Sync Operation (100 workflows) | < 30s |
| Search Response Time | < 200ms |

### 5.2 Scalability

| Metric | Target |
|--------|--------|
| Concurrent Users | 1,000+ |
| Workflows per Tenant | 10,000+ |
| Environments per Tenant | 100+ |
| API Requests per Second | 1,000+ |

### 5.3 Availability

| Metric | Target |
|--------|--------|
| Uptime SLA | 99.9% |
| Planned Maintenance Window | 4 hours/month |
| Recovery Time Objective (RTO) | 1 hour |
| Recovery Point Objective (RPO) | 1 hour |

### 5.4 Security

- SOC 2 Type II compliance
- GDPR compliance
- Data encryption at rest and in transit
- Regular security audits
- Penetration testing annually

---

## 6. Success Metrics

### 6.1 Product Metrics

| Metric | Target |
|--------|--------|
| Monthly Active Users (MAU) | Track growth |
| Promotions Executed | 1,000+/month |
| Drift Incidents Detected | Track trend |
| Mean Time to Resolve Drift | < 24 hours |
| Snapshot Restore Success Rate | > 99% |

### 6.2 Business Metrics

| Metric | Target |
|--------|--------|
| Free to Paid Conversion | > 5% |
| Monthly Recurring Revenue (MRR) | Track growth |
| Customer Churn Rate | < 5% |
| Net Promoter Score (NPS) | > 40 |

---

## 7. Roadmap

### Phase 1: Foundation (Complete)
- Environment management and configuration
- Workflow synchronization from n8n instances
- Basic promotion pipelines
- GitHub backup/restore
- Multi-tenancy with complete data isolation
- Role-based access control

### Phase 2: Governance (Complete)
- Drift detection and incident management
- Approval workflows for promotions
- Comprehensive audit logging
- Git-backed snapshots and restore
- Credential health monitoring

### Phase 3: Enterprise (Complete)
- Drift policies with TTL/SLA enforcement
- Canonical workflow system with Git integration
- Bulk operations (sync, backup, restore)
- Execution analytics and observability
- Advanced admin portal (21 pages)
- Platform admin console
- Support ticket system

### Phase 4: Operations (Complete)
- Git-based promotion system
- PROD hotfix keep behavior
- Environment state management
- Data retention policies
- Background job schedulers (8 schedulers)
- Real-time SSE streaming
- Health monitoring and recovery

### Phase 5: Scale (Planned)
- Secret vault integration (HashiCorp Vault, AWS Secrets Manager)
- SSO/SCIM enterprise authentication
- Advanced compliance tools and reporting
- Custom provider integrations (beyond n8n)
- White-label deployment options
- Multi-region support

---

## 8. Appendix

### 8.1 Glossary

| Term | Definition |
|------|------------|
| **Environment** | A connected n8n instance (dev, staging, production) |
| **Environment Class** | Category determining policies (DEVELOPMENT, STAGING, PRODUCTION) |
| **Workflow** | An n8n automation workflow |
| **Source-Managed Workflow** | User-facing term for canonical (Git-tracked) workflow |
| **Unmanaged Workflow** | User-facing term for unmapped (not Git-tracked) workflow |
| **Promotion** | Moving a workflow from one environment to another |
| **Pipeline** | A defined path for promotions (e.g., dev → staging → prod) |
| **Drift** | Differences between expected and actual workflow configuration |
| **Snapshot** | A point-in-time backup of environment state |
| **Canonical Workflow** | Internal term for Git-backed source of truth workflow |
| **Content Hash** | SHA256 hash of normalized workflow JSON for comparison |
| **Gate** | A validation step required before promotion |
| **Tenant** | An isolated customer organization |
| **Hotfix** | Direct production change outside normal promotion flow |
| **Baseline** | The approved state of an environment (stored in Git) |
| **Onboarding** | Process of linking existing workflows to canonical system |
| **ADR** | Architecture Decision Record documenting design decisions |

### 8.2 Codebase Statistics

**Backend (`app-back/`)**:
| Component | Count |
|-----------|-------|
| API Endpoint Modules | 51 |
| Service Modules | 63 |
| Schema Files | 28 |
| Test Files | 78 |
| Alembic Migrations | 79 |

**Frontend (`app-front/`)**:
| Component | Count |
|-----------|-------|
| Core Pages | 41 |
| Admin Pages | 21 |
| Support Pages | 4 |
| Platform Pages | 4 |
| **Total Pages** | **70** |

**Documentation**:
| Type | Count |
|------|-------|
| Architecture Decision Records (ADRs) | 10 |
| MVP Readiness Pack Documents | 14 |

### 8.3 API Endpoints Summary

| Category | Endpoint Modules |
|----------|-----------|
| Auth & Security | auth, security |
| Environments | environments, environment_capabilities |
| Workflows | workflows, workflow_matrix, workflow_policy |
| Canonical System | canonical_workflows, git_promotions |
| Pipelines & Promotions | pipelines, promotions, deployments |
| Drift & Incidents | incidents, drift_policies, drift_reports, drift_approvals |
| Snapshots & Restore | snapshots, restore |
| Observability | observability, executions |
| Bulk Operations | bulk_operations |
| Credentials & Tags | credentials, tags |
| Teams & Billing | teams, billing, downgrades |
| Admin | admin_* (11 modules) |
| Platform | platform_* (4 modules) |
| Real-time | sse, notifications, background_jobs |
| Support | support |
| **Total Modules** | **51** |

### 8.4 Database Tables Summary

| Category | Tables |
|----------|--------|
| Core (tenants, users, environments) | 6 |
| Workflows & Executions | 6 |
| Canonical System | 3 |
| Promotion & Deployment | 5 |
| Drift Management | 8 |
| Entitlements & Billing | 6 |
| Plans & Features | 4 |
| Admin & Audit | 6 |
| Support | 3 |
| Background Jobs | 2 |
| Security | 3 |
| **Total** | **52+** |

---

*Document maintained by the N8N Ops Platform Team*
