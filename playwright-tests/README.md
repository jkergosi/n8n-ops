# Playwright Verification Tests

This directory contains **one-time verification tests** that are meant to be run once to verify a feature implementation works end-to-end, then deleted.

## Purpose

Unlike regular E2E tests in `n8n-ops-ui/tests/e2e/`, these tests are **temporary verification tests** used during feature development to:

1. Verify the complete feature works end-to-end in the browser
2. Test UI interactions that backend/unit tests can't cover
3. Validate the user experience flows
4. Confirm acceptance criteria are met

## Running the Tests

### Prerequisites

Make sure both backend and frontend are running:

```bash
# Terminal 1: Start backend
cd n8n-ops-backend
python -m uvicorn app.main:app --reload

# Terminal 2: Start frontend
cd n8n-ops-ui
npm run dev
```

### Run the verification test

```bash
cd n8n-ops-ui
npx playwright test ../playwright-tests/approval-flow.spec.ts --headed
```

Or run in UI mode for debugging:

```bash
cd n8n-ops-ui
npx playwright test ../playwright-tests/approval-flow.spec.ts --ui
```

## Current Tests

### `approval-flow.spec.ts`

Verifies the complete approval workflow implementation for drift incident actions.

**Acceptance Criteria Covered:**

- AC1: Block action execution when approval is required but not granted
- AC2: Request approval for gated action (acknowledge)
- AC3: Approve request and verify audit trail
- AC4: Request approval for extend_ttl with metadata
- AC5: Request approval for reconcile action
- AC6: Reject approval blocks action execution
- AC7: List all pending approvals with full context

**Edge Cases Covered:**

- EC1: Prevent duplicate approval requests
- EC2: Self-approval prevention

**What This Test Verifies:**

1. Users can request approval for gated actions (acknowledge, extend_ttl, reconcile)
2. Approvers can approve or reject approval requests
3. Approved actions execute automatically with proper audit trail
4. Rejected approvals block action execution
5. UI displays approval status correctly
6. Complete audit trail is created for governance compliance
7. Edge cases like duplicate requests and self-approval are handled

**After Verification:**

Once the feature is verified to work correctly:

1. ✅ Mark T009 as complete
2. ✅ Run T010 to execute this test
3. ✅ Run T011 to delete this test and directory

## Notes

- These tests use mock API responses to simulate backend behavior
- Tests are designed to be resilient to UI changes (using multiple selectors)
- Focus is on critical user journeys, not exhaustive coverage
- Regular E2E tests should be added to `n8n-ops-ui/tests/e2e/` for permanent test coverage
