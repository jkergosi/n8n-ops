# Canonical Onboarding Verification - Quick Start

This is a quick guide to run the canonical onboarding verification test.

## Quick Run (1 minute)

```bash
# Navigate to UI project
cd n8n-ops-ui

# Install dependencies (if not already done)
npm install

# Install Playwright browsers (if not already done)
npx playwright install

# Run the verification test
npx playwright test tests/verification/canonical-onboarding-verification.spec.ts
```

## What This Test Verifies

✅ Complete canonical onboarding flow from scratch
✅ Anchor environment selection (typically production)
✅ Inventory phase (creates canonical workflows)
✅ Auto-linking workflows based on content hash
✅ Listing untracked workflows
✅ Matrix view rendering with correct statuses
✅ Error handling for preflight and inventory failures

## Visual Mode (Recommended for First Run)

See what's happening step-by-step:

```bash
npx playwright test tests/verification/canonical-onboarding-verification.spec.ts --ui
```

This opens an interactive UI where you can:
- Watch each test step execute
- Pause/resume execution
- Inspect elements
- See network requests
- View console logs

## Expected Output

When all tests pass, you'll see:

```
✓ should complete full canonical onboarding flow from scratch
✓ should display canonical matrix view correctly after onboarding
✓ should handle workflow linking for untracked workflows
✓ should show workflow sync status in matrix view
✓ should handle inventory phase with multiple environments
✓ should handle preflight check failures gracefully
✓ should handle inventory phase errors

7 passed (30s)
```

## Test Flow Visualization

```
Start
  ↓
Navigate to /canonical
  ↓
Click "Start Onboarding"
  ↓
Preflight Checks
  ✓ GitHub connected
  ✓ Environments configured
  ✓ No active onboarding
  ↓
Select Anchor Environment
  → Production (recommended)
  ↓
Start Inventory
  ├─ Sync anchor from Git
  ├─ Create canonical workflows
  ├─ Sync other environments from n8n
  ├─ Auto-link by content hash
  └─ List untracked workflows
  ↓
Review & Link Untracked
  → Manual linking if needed
  ↓
Complete Onboarding
  ↓
Verify Matrix View
  ├─ Linked (green)
  ├─ Drift (yellow)
  └─ Out of Date (blue)
  ↓
Done ✓
```

## Quick Troubleshooting

### Tests fail with timeout
```bash
# Run with longer timeout
npx playwright test tests/verification/canonical-onboarding-verification.spec.ts --timeout=120000
```

### Want to see browser
```bash
# Run in headed mode
npx playwright test tests/verification/canonical-onboarding-verification.spec.ts --headed
```

### Need detailed logs
```bash
# Run with list reporter
npx playwright test tests/verification/canonical-onboarding-verification.spec.ts --reporter=list
```

### See what went wrong
```bash
# View HTML report
npx playwright show-report
```

## Run Individual Tests

```bash
# Just the main onboarding flow
npx playwright test -g "complete full canonical"

# Just the matrix view
npx playwright test -g "matrix view"

# Just error handling
npx playwright test -g "Error Scenarios"
```

## No Backend Required

These tests use **mock APIs**, so you don't need:
- ❌ Backend server running
- ❌ Database connection
- ❌ GitHub repository access
- ❌ n8n instances

The tests verify the **frontend behavior** with simulated API responses.

## For Full E2E Testing

If you want to test against a real backend:

1. Start the backend server:
   ```bash
   cd ../n8n-ops-backend
   python -m app.main
   ```

2. Start the frontend dev server:
   ```bash
   npm run dev
   ```

3. Remove mock routes in the test (comment out `mockCanonicalFlow()`)

4. Run tests against live servers

## What Success Looks Like

When verification is successful:

1. ✅ All 7 tests pass
2. ✅ No console errors
3. ✅ Screenshots show correct UI states
4. ✅ Network requests intercepted correctly
5. ✅ Matrix view displays workflows

## Next Steps

After successful verification:

1. Check out the detailed documentation: `CANONICAL_ONBOARDING_VERIFICATION.md`
2. Run the full E2E test suite: `npm test`
3. Test the feature manually in the UI
4. Review the backend E2E tests in `n8n-ops-backend/tests/e2e/`

## Questions?

- 📖 Full documentation: `CANONICAL_ONBOARDING_VERIFICATION.md`
- 🔍 Test code: `canonical-onboarding-verification.spec.ts`
- 📊 Test data: `../testkit/test-data.ts`
- 🔌 Mock API: `../testkit/mock-api.ts`
