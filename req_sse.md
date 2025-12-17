# SSE real-time updates for Deployments UI (React + Python backend)

## Purpose
Enable real-time UI updates driven by backend deployment activity across:
- Deployments page counters (e.g., running/success/failed, “successfully deployed workflows” count)
- Deployments page table rows (create/update/remove)
- Deployment details page (state, progress, timeline)
- Workflows table (workflow row fields affected by deployments)

This document describes **architecture and best practices** only (no code, no library-specific instructions).

---

## Core principles
1. **Backend is the source of truth**
   - All deployment state lives in the database (or an authoritative state store).
   - The UI never infers “success” or “current status” from local events alone.

2. **Model updates as domain events**
   - Backend emits a stream of small, typed events describing state changes.
   - UI consumes events and applies deterministic patches to local state.

3. **Use SSE for server → client streaming**
   - SSE is well suited for one-way real-time updates (live dashboards, counters, tables).
   - Prefer SSE over WebSockets unless you need true bidirectional interactive real-time features.

4. **Support multi-instance backends**
   - In-process pub/sub is insufficient when multiple API instances exist.
   - Use a shared message fanout (e.g., broker) so any instance can serve clients and still receive the same events.

5. **Snapshot + incremental updates**
   - On connect (and reconnect), server sends a **snapshot** for fast correctness.
   - After snapshot, server streams **incremental events** (deltas/patches).

---

## Recommended event strategy

### Event envelope
All streamed messages should share a stable envelope:
- `event_id`: monotonic identifier (supports ordering and debugging)
- `type`: event name (e.g., `deployment.upsert`)
- `tenant_id`, `env_id`: routing keys
- `ts`: event timestamp
- `payload`: minimal structured data

### Minimal event types
Use a small set of events that map directly to UI updates:

1. **`snapshot`**
   - Sent immediately on connection.
   - Contains the initial state needed for the subscribed scope (page or details).

2. **`deployment.upsert`**
   - Create/update a deployment row for list + details views.
   - Payload includes only fields needed to render and sort the row.

3. **`deployment.progress`** (optional)
   - Progress updates that happen frequently (percentage, phase, step).
   - Keep payload small; avoid high-frequency “chatty” events unless necessary.

4. **`deployment.delete`** (optional)
   - If your UX supports removals (rare).

5. **`workflow.upsert`**
   - Update workflow summary row fields affected by deployments (last deployed status/time/version).

6. **`counts.update`**
   - Authoritative counters that reflect your defined counting rules.

---

## Scopes and subscriptions
Avoid streaming more than each page needs.

### Common scopes
- **Deployments page scope**
  - Snapshot includes counters + the current deployments list + minimal workflow summaries for the workflows table.
  - Stream includes relevant deployment/workflow updates and counter updates.

- **Deployment details scope**
  - Snapshot includes the single deployment + associated timeline/progress context.
  - Stream includes only events relevant to that deployment (plus optional counter updates).

### Routing keys
All events should include routing keys used for:
- tenant isolation
- environment isolation
- optional deployment/workflow targeting

---

## Counting rules (define explicitly)
Counters and derived metrics must be defined unambiguously, e.g.:
- “Success workflows count” could mean:
  - count of workflows whose **latest** deployment in an environment is `success`
  - OR count of successful deployments in a time window
  - OR count of all workflows that have ever successfully deployed

Pick one definition for each counter and make it consistent across:
- page counters
- details page
- exported metrics/APIs

---

## UI state management best practices

### Normalize client state
Maintain a single source of client truth for entities:
- `deploymentById` map + `deploymentListIds` for ordering
- `workflowById` map + `workflowListIds`
- counters object(s)

Avoid duplicating the same deployment/workflow object in multiple places.

### Deterministic reducers
For each event type, apply a deterministic update rule:
- `snapshot`: replace state for that scope (or reconcile and then replace)
- `upsert`: merge entity by ID; adjust list ordering by your sort key
- `counts.update`: replace counters (authoritative)
- `progress`: patch only progress-related fields

### Sorting and jitter control
- Prefer stable ordering (e.g., primary sort key + tie-breaker).
- Only re-order when the relevant sort keys change.
- For high-frequency progress events, avoid re-sorting on every progress tick.

---

## Consistency and correctness

### Ordering
- Use `event_id` (monotonic) to detect out-of-order messages.
- Client should ignore stale updates when it can detect they’re older than current state.

### Reconnect behavior
- Treat reconnect as normal.
- Always send a snapshot on connect to ensure correctness, then resume incremental events.
- Keep event payloads small so snapshot is your main “state sync” mechanism.

### Transaction boundaries
Emit events only for committed state changes.
- Update authoritative state → commit → publish event(s)

---

## Performance and scaling

### Event volume control
- Favor coarse-grained updates for list rows (status, timestamps, summary fields).
- For logs/progress:
  - throttle or batch
  - separate stream/scope if needed

### Fanout
Use a shared broker/fanout mechanism so:
- multiple API instances can serve SSE connections
- all instances receive the same update events

### Payload sizing
- Avoid embedding large blobs in events (e.g., full logs).
- Send references/IDs and let UI fetch large content on demand if required.

---

## Operational considerations
- Ensure your HTTP/proxy stack supports streaming responses without buffering.
- Add keepalive pings to avoid idle connection termination.
- Track metrics:
  - active connections
  - event rate
  - reconnect rate
  - snapshot time and size
- Apply sensible per-tenant connection limits if needed.

---

## Acceptance criteria (validate in production-like conditions)
- Counters update in real time without page refresh.
- Deployment list row updates (status/progress/timestamps) appear within expected latency.
- Details page reflects current status/progress/timeline in real time.
- Workflow table rows update when deployments affect workflow summary fields.
- Works with multiple backend instances.
- On reconnect, UI state is correct after snapshot and continues updating.

