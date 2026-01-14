# Feature Verification Checklist

**Feature ID:** feature-1767910795355-mlndzgiyi
**Title:** Run canonical onboarding from scratch
**Date:** 2026-01-08
**Status:** ✅ READY FOR VERIFICATION

---

## Pre-Verification Setup

### ✅ Installation Requirements
- [ ] Node.js and npm installed
- [ ] Navigate to `app-front` directory
- [ ] Run `npm install` (if not already done)
- [ ] Run `npx playwright install` (if browsers not installed)

### ✅ Files Created/Modified

**Created:**
- [x] `app-front/tests/verification/canonical-onboarding-verification.spec.ts` (465 lines)
- [x] `app-front/tests/verification/CANONICAL_ONBOARDING_VERIFICATION.md` (484 lines)
- [x] `app-front/tests/verification/CANONICAL_ONBOARDING_QUICK_START.md` (217 lines)
- [x] `app-front/tests/verification/IMPLEMENTATION_NOTES.md` (390 lines)
- [x] `app-front/tests/verification/run-canonical-verification.bat` (Windows)
- [x] `app-front/tests/verification/run-canonical-verification.sh` (Linux/Mac)
- [x] `FEATURE_1767910795355_SUMMARY.md` (Comprehensive summary)
- [x] `VERIFICATION_CHECKLIST_1767910795355.md` (This file)

**Modified:**
- [x] `app-front/tests/testkit/test-data.ts` (Added canonical test data)
- [x] `app-front/tests/testkit/mock-api.ts` (Enhanced mockCanonicalFlow)

---

## Verification Steps

### Step 1: Verify Test File Structure ✅

```bash
cd app-front
npx playwright test tests/verification/canonical-onboarding-verification.spec.ts --list
```

**Expected Output:**
```
Total: 7 tests in 1 file
```

**Tests should include:**
- [ ] "should complete full canonical onboarding flow from scratch"
- [ ] "should display canonical matrix view correctly after onboarding"
- [ ] "should handle workflow linking for untracked workflows"
- [ ] "should show workflow sync status in matrix view"
- [ ] "should handle inventory phase with multiple environments"
- [ ] "should handle preflight check failures gracefully"
- [ ] "should handle inventory phase errors"

**Status:** ✅ VERIFIED (7 tests detected)

---

### Step 2: Run Tests in UI Mode (Recommended)

```bash
npx playwright test tests/verification/canonical-onboarding-verification.spec.ts --ui
```

**What to verify:**
- [ ] UI mode launches successfully
- [ ] All 7 tests are listed
- [ ] Can step through test execution
- [ ] Can see page screenshots at each step
- [ ] Can inspect DOM elements
- [ ] No JavaScript errors in console

**OR use the script:**

Windows:
```bash
.\tests\verification\run-canonical-verification.bat --ui
```

Linux/Mac:
```bash
./tests/verification/run-canonical-verification.sh --ui
```

---

### Step 3: Run Full Test Suite

```bash
npx playwright test tests/verification/canonical-onboarding-verification.spec.ts
```

**Expected Results:**
- [ ] All 7 tests pass (✓)
- [ ] Total execution time: ~45-60 seconds
- [ ] No TypeScript errors
- [ ] No console errors
- [ ] HTML report generated

**Success Output:**
```
✓ should complete full canonical onboarding flow from scratch
✓ should display canonical matrix view correctly after onboarding
✓ should handle workflow linking for untracked workflows
✓ should show workflow sync status in matrix view
✓ should handle inventory phase with multiple environments
✓ should handle preflight check failures gracefully
✓ should handle inventory phase errors

7 passed (45s)
```

---

### Step 4: Verify Test Coverage

Each test should verify specific aspects:

#### Test 1: Complete Onboarding Flow
- [ ] Navigate to /canonical page
- [ ] Start onboarding wizard
- [ ] Preflight checks run and pass
- [ ] Can select anchor environment (production)
- [ ] Inventory phase starts and completes
- [ ] Progress indicators shown
- [ ] Auto-linking results displayed
- [ ] Untracked workflows listed (if any)
- [ ] Success message shown
- [ ] Redirects to matrix or canonical page

#### Test 2: Matrix View Display
- [ ] Matrix view loads at /canonical/matrix
- [ ] Environment headers shown (Development, Production)
- [ ] Workflow rows displayed
- [ ] Status indicators visible (linked, drift, out-of-date)
- [ ] Matrix cells render correctly
- [ ] Empty cells handled properly

#### Test 3: Workflow Linking
- [ ] Untracked workflows page loads
- [ ] Untracked workflows listed
- [ ] Link button available
- [ ] Can select canonical workflow to link to
- [ ] Linking action succeeds
- [ ] Success message shown
- [ ] Workflow removed from untracked list

#### Test 4: Status Indicators
- [ ] Different status types render correctly
- [ ] Linked status (green/synced)
- [ ] Drift status (yellow/modified)
- [ ] Out-of-date status (blue/behind)
- [ ] Visual indicators are distinct

#### Test 5: Multiple Environments
- [ ] Both anchor and non-anchor environments processed
- [ ] Progress shows all environments
- [ ] Summary shows environment count
- [ ] All environments appear in matrix

#### Test 6: Preflight Failures
- [ ] Error messages displayed
- [ ] Warnings shown
- [ ] Cannot proceed with errors
- [ ] Clear indication of issues

#### Test 7: Inventory Errors
- [ ] Error message shown on inventory failure
- [ ] Retry option available
- [ ] Application doesn't crash

---

### Step 5: Verify Documentation

Check that documentation is comprehensive and accurate:

- [ ] `CANONICAL_ONBOARDING_VERIFICATION.md` explains all tests
- [ ] `CANONICAL_ONBOARDING_QUICK_START.md` provides quick instructions
- [ ] `IMPLEMENTATION_NOTES.md` documents technical details
- [ ] `FEATURE_1767910795355_SUMMARY.md` provides complete overview
- [ ] All documentation is clear and well-formatted

---

### Step 6: Verify Scripts Work

#### Windows:
```bash
.\tests\verification\run-canonical-verification.bat
```
- [ ] Script runs without errors
- [ ] Checks for Playwright installation
- [ ] Runs all tests
- [ ] Shows success/failure message
- [ ] Exit code correct (0 = success, 1 = failure)

#### Linux/Mac:
```bash
chmod +x ./tests/verification/run-canonical-verification.sh
./tests/verification/run-canonical-verification.sh
```
- [ ] Script is executable
- [ ] Runs without errors
- [ ] Shows success/failure message
- [ ] Exit code correct

---

### Step 7: Code Quality Checks

```bash
# Check for linting errors (if lint script exists)
npm run lint tests/verification/canonical-onboarding-verification.spec.ts

# Check TypeScript compilation
npx tsc --noEmit tests/verification/canonical-onboarding-verification.spec.ts
```

**Verify:**
- [ ] No linting errors
- [ ] No TypeScript errors
- [ ] Imports resolve correctly
- [ ] Test data references are correct

---

## Test Scenarios Verification Matrix

| Scenario | Test Coverage | Mock Data | Expected Result | Status |
|----------|---------------|-----------|-----------------|--------|
| Start Onboarding | ✅ Test 1 | preflightSuccess | Wizard opens | ⬜ |
| Preflight Pass | ✅ Test 1 | preflightSuccess | All checks pass | ⬜ |
| Preflight Fail | ✅ Test 6 | preflightFailure | Errors shown | ⬜ |
| Anchor Selection | ✅ Test 1, 5 | N/A | Can select env | ⬜ |
| Inventory Start | ✅ Test 1, 5 | inventoryStarted | Job starts | ⬜ |
| Inventory Progress | ✅ Test 1, 5 | inventoryProgress | Progress shown | ⬜ |
| Inventory Complete | ✅ Test 1, 5 | inventoryComplete | Summary shown | ⬜ |
| Inventory Error | ✅ Test 7 | Error response | Error handled | ⬜ |
| Auto-linking | ✅ Test 1 | inventoryComplete | Count shown | ⬜ |
| Untracked List | ✅ Test 3 | untrackedWorkflows | Workflows listed | ⬜ |
| Manual Link | ✅ Test 3 | N/A | Link succeeds | ⬜ |
| Matrix Display | ✅ Test 2, 4 | matrix | Grid renders | ⬜ |
| Status: Linked | ✅ Test 4 | matrix | Green indicator | ⬜ |
| Status: Drift | ✅ Test 4 | matrix | Yellow indicator | ⬜ |
| Status: Out-of-date | ✅ Test 4 | matrix | Blue indicator | ⬜ |
| Multi-env | ✅ Test 5 | N/A | All envs synced | ⬜ |

---

## Mock API Verification

Verify that mock API routes are correctly set up:

### Endpoints Mocked:
- [ ] `GET /api/v1/canonical/onboard/preflight`
- [ ] `POST /api/v1/canonical/onboard/inventory`
- [ ] `GET /api/v1/canonical/onboard/inventory/{job_id}/status`
- [ ] `GET /api/v1/canonical/untracked`
- [ ] `POST /api/v1/canonical/link`
- [ ] `GET /api/v1/workflows/matrix`

### Test Data Available:
- [ ] `TestData.canonical.preflightSuccess`
- [ ] `TestData.canonical.preflightFailure`
- [ ] `TestData.canonical.inventoryStarted`
- [ ] `TestData.canonical.inventoryComplete`
- [ ] `TestData.canonical.inventoryProgress`
- [ ] `TestData.canonical.untrackedWorkflows`
- [ ] `TestData.canonical.matrix`

---

## Final Verification

### All Tests Pass ✅
- [ ] Run full test suite: `npx playwright test tests/verification/canonical-onboarding-verification.spec.ts`
- [ ] All 7 tests show ✓ (passed)
- [ ] No errors or warnings
- [ ] Execution time reasonable (~45-60 seconds)

### Documentation Complete ✅
- [ ] All documentation files created
- [ ] Documentation is clear and accurate
- [ ] Examples and commands work
- [ ] Troubleshooting section helpful

### Scripts Work ✅
- [ ] Windows batch script works
- [ ] Linux/Mac shell script works
- [ ] Scripts handle errors gracefully
- [ ] Scripts provide clear output

### Code Quality ✅
- [ ] No TypeScript errors
- [ ] No linting errors
- [ ] Follows project conventions
- [ ] Test data structure correct

### Integration ✅
- [ ] Uses existing MockApiClient
- [ ] Extends existing test data
- [ ] Follows existing test patterns
- [ ] Compatible with CI/CD

---

## Common Issues and Solutions

### Issue: Tests timeout
**Solution:**
```bash
npx playwright test tests/verification/canonical-onboarding-verification.spec.ts --timeout=120000
```

### Issue: "Cannot find module"
**Solution:**
```bash
npm install
```

### Issue: Playwright not installed
**Solution:**
```bash
npx playwright install
```

### Issue: Tests fail with selector errors
**Solution:**
- Run in UI mode: `--ui`
- Inspect actual page structure
- Check if UI components changed

### Issue: Mock routes not intercepting
**Solution:**
- Verify `mockCanonicalFlow()` called in `beforeEach`
- Check route patterns match actual URLs
- Use `page.on('request', ...)` to debug

---

## Sign-Off Checklist

Before marking feature as complete:

- [ ] All 7 tests pass consistently
- [ ] Tested on Windows ✅
- [ ] Tested on Linux/Mac (if available)
- [ ] Documentation reviewed and accurate
- [ ] Scripts tested and working
- [ ] No TypeScript or linting errors
- [ ] Test coverage is comprehensive
- [ ] Mock data matches real API responses
- [ ] Feature summary document created
- [ ] Verification checklist completed (this document)

---

## Final Status

**Implementation Status:** ✅ COMPLETE

**Verification Status:** ⬜ PENDING (Run tests to complete)

**Ready for:**
- ✅ Local testing
- ✅ Code review
- ✅ Integration into CI/CD
- ✅ Production deployment (after full E2E with backend)

---

## Quick Verification Command

To verify everything at once:

```bash
cd app-front
npx playwright test tests/verification/canonical-onboarding-verification.spec.ts --reporter=html
```

Then open the HTML report:
```bash
npx playwright show-report
```

---

## Next Steps

1. ✅ Implementation complete
2. ⬜ Run verification tests
3. ⬜ Review HTML test report
4. ⬜ Mark all checkboxes in this document
5. ⬜ Code review by team
6. ⬜ Merge to main branch
7. ⬜ Add to CI/CD pipeline
8. ⬜ Document in team wiki/knowledge base

---

**Verification Completed By:** _________________

**Date:** _________________

**Notes:** _________________
