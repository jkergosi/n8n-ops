# Claude Code Instructions — Test Infrastructure for N8N Ops (Frontend + Backend)

This document instructs Claude Code to add a complete, production-grade testing setup for the N8N Ops project.  
Scope includes **frontend (React)** and **backend (Python/FastAPI)** unit and integration tests.

---

## Global Rules

- Do **not** change runtime behavior.
- Only add:
  - test files
  - test configuration
  - fixtures
  - minimal dependency-injection seams if required for testability
- No real network calls in tests.
- Tests must be deterministic (no wall-clock time, randomness, shared state).
- Keep frontend and backend changes in **separate commits**.

---

# Part 1 — Frontend (React)

## 1. Detect Current Stack
- Determine:
  - Vite vs CRA
  - TypeScript vs JavaScript
- If Vite → use **Vitest**
- If Jest already exists → keep Jest (do not migrate)

---

## 2. Install Test Tooling

Add dev dependencies:

- Test runner: **Vitest** (preferred) or **Jest**
- **@testing-library/react**
- **@testing-library/jest-dom**
- **@testing-library/user-event**
- **MSW (Mock Service Worker)**
- DOM environment:
  - `jsdom` or `happy-dom` (align with runner)

---

## 3. Configure Test Setup

Create a single test setup file that:
- Registers `jest-dom` matchers
- Starts MSW before tests
- Resets MSW handlers after each test
- Stops MSW after all tests
- Fails tests on **unhandled network requests**
- Adds only required browser polyfills

Wire this setup file into the test runner config.

---

## 4. Standardize Test Conventions

### File naming
- `*.test.ts` / `*.test.tsx`
- Co-locate with source files OR use `src/__tests__` (choose one and be consistent)

### Test utilities
Create a `test-utils` module that exports:
- `renderWithProviders()`
  - Wraps components in:
    - Router
    - Auth context
    - Feature flags
    - Query/client providers
- Default fixtures:
  - Admin user
  - Tenant
  - Enabled feature flags
- Allow overrides per test

---

## 5. Network Mocking (MSW)

- Identify how API calls are made (fetch / axios / API client).
- Create MSW handlers for:
  - Success responses
  - Error responses (401/403/500)
- No tests may hit real URLs.
- Unhandled requests must fail the test.

---

## 6. Initial Test Coverage (Minimum Required)

Add the following tests:

### 6.1 Pure unit test
- Target a utility or service module (parsing, mapping, formatting).
- No React rendering.

### 6.2 Component / page tests (2–3 files)
Each must cover:
- Loading state
- Empty state
- Success state
- Error state

At least one test must cover:
- Permission-gated behavior (admin vs non-admin)
- A full action flow:
  - User interaction
  - API call
  - Toast/notification
  - UI update

### Requirements
- Use `getByRole`, `getByLabelText`, `findByRole`
- Avoid `data-testid` unless unavoidable
- Assert user-visible behavior only

---

## 7. Scripts

Add package scripts:
- `test`
- `test:watch`
- `test:coverage`

Ensure tests:
- Run headlessly
- Exit non-zero on failure
- Do not require backend running

---

## 8. Frontend Acceptance Criteria

- Clean checkout → `npm/yarn/pnpm test` passes
- No real network calls
- MSW enforced
- At least:
  - 1 pure unit test
  - 2–3 component/page tests
  - Permission logic covered

---

# Part 2 — Backend (Python / FastAPI)

## 1. Detect Backend Architecture

Identify:
- Framework (assume FastAPI unless proven otherwise)
- Sync vs async endpoints
- ORM (e.g., SQLAlchemy)
- DB (Postgres assumed)
- External n8n API client module

---

## 2. Install Test Tooling

Add dev dependencies:
- `pytest`
- `pytest-cov`
- `pytest-mock`
- `httpx` (for async API tests)

Add pytest configuration (`pytest.ini` or `pyproject.toml`):
- Test discovery rules
- Markers:
  - `unit`
  - `integration`
  - `api`
- Reasonable warning strictness

---

## 3. Fixture Architecture (Critical)

Create **small, composable fixtures**:

- `app`
  - Returns FastAPI app instance
- `client`
  - `TestClient` or `httpx.AsyncClient`
- `db_session`
  - Isolated test DB session
- `admin_user`
- `tenant`
- `auth_headers`

Rules:
- No “god fixtures”
- No shared mutable state
- Roll back DB changes per test or recreate schema

---

## 4. Dependency Injection Overrides

For tests:
- Override FastAPI dependencies for:
  - DB session
  - Current user
  - Tenant resolution
  - External n8n client

Never call the real n8n API.

---

## 5. External API Isolation

- Ensure all n8n interactions go through a **client interface/module**
- Unit tests:
  - Mock this client
- Integration/API tests:
  - Still mocked unless explicitly marked otherwise

---

## 6. Required Test Coverage

### 6.1 Unit tests
- Service functions
- State transitions (pipelines, promotions, snapshots)
- Error mapping and validation logic

### 6.2 Integration tests
- DB + repository + service wiring
- Verify side-effects (records created, updated, rolled back)

### 6.3 API tests
- Status codes
- Auth / RBAC enforcement
- Request/response schemas
- Error shapes
- Idempotency where applicable

---

## 7. Time Control

- All time-based logic must be deterministic
- Use:
  - `freezegun` OR
  - injected clock dependency
- No reliance on `datetime.now()` in tests

---

## 8. Coverage and CI

- Enable coverage via `pytest-cov`
- Enforce coverage thresholds on **changed files**, not global %
- CI must:
  - Run unit + API tests on every PR
  - Allow integration tests with service containers if needed

---

## 9. Backend Acceptance Criteria

- `pytest` passes in clean environment
- No real external
