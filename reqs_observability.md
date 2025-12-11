Replace existing placeholder pages for Observability and alerts.

# Observability & Alerts — Functional Specification  
For n8n-Ops Application (API-only access)

This document defines what the Observability and Alerts subsystems must provide using only:
- n8n API access  
- n8n-ops database (workflows, executions, pipelines, deployments, snapshots, drift)  
- Lightweight internal collectors (environment health checks)

No server/infra metrics are assumed.

---

## 0. Scope & Data Sources

### Available
- **n8n API**
  - Workflows
  - Executions
- **n8n-ops DB**
  - Environments
  - Workflows metadata
  - Executions mirror (if enabled)
  - Pipelines
  - Deployments
  - Snapshots
  - Drift/sync tables
- **Internal collectors**
  - Periodic environment health checks (latency, availability)

### Not Available
- Host OS metrics (CPU, memory, disk)
- Container/VM metrics
- Raw logs from underlying infrastructure

---

# 1. Observability → Overview Page

A read-only dashboard summarizing workflow behavior, environment connectivity, and promotion/sync health.

---

## 1.1 KPI Row (Top Section)

Cards:
- **Total Executions**
- **Success Rate**
- **Avg Duration**
- **Failed Executions**

Behavior:
- Values computed for selected time range (default: 24h)
- Optional trend vs previous period
- Clicking a card filters workflow list

Backend:  
- executions_count  
- successes_count  
- failures_count  
- avg_duration_ms or p95_duration_ms  
- optional deltas

Source:  
- n8n `/executions` API or mirrored `executions` table

---

## 1.2 Workflow Performance (Bottom-Left)

Each workflow displays:
- Executions
- Success count
- Failed count
- Error rate %
- Optional: p95 duration
- Row click → Workflow Detail Page

Modes:
- **Top by Executions**
- **Top by Failures**

Backend:
- Aggregated stats per workflow for selected period

Source:
- n8n executions API or mirrored DB

---

## 1.3 Environment Health Cards (Bottom-Right)

For each environment:
- Latency (avg or p95)
- Uptime % (health-check success rate)
- Status: Healthy / Degraded / Unreachable
- Active workflows count
- Promotion/sync summary:
  - Last deployment time
  - Last snapshot time
  - Drift state: In Sync / Drift / Unknown

Click → Environment Detail view.

Backend:
- environment_health status
- latency metrics
- uptime %
- drift state
- promotion/snapshot metadata

Source:
- **Internal health-check table** (new)
- deployments table
- snapshots table
- drift/sync table
- workflows table

---

## 1.4 Promotion & Sync Panel (Optional, Recommended)

KPIs (last 7 days):
- Promotions: total / success / failed / blocked
- Snapshots: created / restored
- Drift count (# workflows out of sync)

Short list of recent deployments:
- pipeline
- source → target
- status
- timestamp

Backend:
- Aggregated pipeline + deployment records

---

# 2. Alerts Page

Alerts = event catalog + notification channels + mapping rules.

---

## 2.1 Event Catalog (Emitted by the App)

Promotion:
- promotion.started
- promotion.success
- promotion.failure
- promotion.blocked

Sync / Drift:
- sync.failure
- sync.drift_detected

Environment:
- environment.unhealthy
- environment.connection_lost
- environment.recovered

Snapshots:
- snapshot.created
- snapshot.restore_success
- snapshot.restore_failure

Credentials:
- credential.placeholder_created
- credential.missing

System:
- system.error

Event fields:
- type
- tenant_id
- environment_id (optional)
- timestamp
- metadata JSON

Source:
- Emitted directly by n8n-ops backend

---

## 2.2 Notification Channels (Left Side)

Supported types:
- Slack
- Email
- Webhook

UI:
- List channels
- Name, Type, Status
- Add / Edit / Delete
- Type-specific config fields

Backend:
- notification_channels table
- Validate config on save

---

## 2.3 Notification Rules (Right Side)

One row per event type.  
Each row: multi-select of channels.

Semantics:
- 0 channels = disabled
- 1..N channels = notify each

Backend:
- notification_rules table
- Mapping: (tenant, event_type) → [channel_ids]

---

## 2.4 Recent Alert Activity (Optional)

Shows last N emitted events where:
- Event type had ≥1 channel assigned

Columns:
- Time
- Event
- Environment
- Summary

Backend:
- events table (short retention)

---

# 3. Backend Responsibilities

### 3.1 Collect Metrics
- Query n8n API for executions/workflows
- Store health-check results
- Maintain drift/sync status
- Track deployments/snapshots

### 3.2 Compute Aggregates for Overview
- KPI stats
- Workflow-level stats
- Environment connectivity & uptime
- Promotion/sync stats

### 3.3 Emit Events & Notifications
- Generate structured events on state changes
- Look up channels
- Send Slack / Email / Webhook notifications
- Store event in events table

---

# 4. Summary for Implementation

The Overview page displays KPI metrics, workflow performance, and environment health using data derived from n8n APIs, the n8n-ops DB, and internal health checks. The Alerts page provides configurable notification channels and event-to-channel mappings, with the backend emitting structured events for promotions, sync/drift, environment issues, snapshots, credentials, and system errors. No server-level metrics are required; all data is obtainable from API access and your own database.
