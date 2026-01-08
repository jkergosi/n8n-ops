# Canonical Onboarding Verification - Implementation Notes

## What Was Built

This verification test suite was created to validate the canonical workflow onboarding feature end-to-end. It ensures that users can successfully onboard their n8n workflows into the canonical system from scratch.

## Files Created

### 1. Test Suite
**`canonical-onboarding-verification.spec.ts`** - Main test file with 7 test scenarios covering:
- Complete onboarding flow from scratch
- Matrix view display and rendering
- Workflow linking functionality
- Status indicators (linked, drift, out-of-date)
- Multiple environment handling
- Error scenarios (preflight failures, inventory errors)

### 2. Documentation
- **`CANONICAL_ONBOARDING_VERIFICATION.md`** - Comprehensive documentation
- **`CANONICAL_ONBOARDING_QUICK_START.md`** - Quick reference guide
- **`IMPLEMENTATION_NOTES.md`** - This file

### 3. Test Runners
- **`run-canonical-verification.bat`** - Windows test runner script
- **`run-canonical-verification.sh`** - Linux/Mac test runner script

### 4. Enhanced Test Infrastructure
- Updated `../testkit/test-data.ts` with canonical onboarding test data
- Enhanced `../testkit/mock-api.ts` with canonical flow mocking

## Design Decisions

### Why Playwright?
- Already used in the project for E2E testing
- Excellent debugging tools (UI mode, traces, screenshots)
- Cross-browser support
- Reliable selector engine

### Why Mock APIs?
- Fast test execution (~45 seconds for all 7 tests)
- No backend dependencies required
- Deterministic results
- Can run on any machine without setup

### Why Separate Verification Folder?
- Clear separation between regular E2E tests and verification tests
- Easy to find and run specifically for feature verification
- Can be deleted after verification if desired (though we recommend keeping for regression testing)

### Test Data Structure
We created comprehensive test data that mirrors actual API responses:

```typescript
canonical: {
  preflightSuccess: {...},      // Successful preflight response
  preflightFailure: {...},      // Failed preflight with errors
  inventoryStarted: {...},      // Inventory job started
  inventoryComplete: {...},     // Inventory completed with summary
  inventoryProgress: {...},     // Mid-progress status
  untrackedWorkflows: [...],    // List of untracked workflows
  matrix: {                     // Full matrix view data
    workflows: [...],
    environments: [...],
    matrix: {...}
  }
}
```

## Technical Implementation Details

### Progressive Test Approach

The tests follow a logical progression:

1. **Happy Path First** - Main onboarding flow test
2. **Individual Features** - Matrix view, linking, status indicators
3. **Complex Scenarios** - Multiple environments
4. **Error Handling** - Preflight and inventory failures

### Flexible Selectors

Tests use multiple selector strategies to be resilient to UI changes:

```typescript
const element = page.locator('[data-testid="element"]').or(
  page.locator('.element-class')
);
```

This makes tests less brittle while still being specific enough to catch real issues.

### Timeout Strategy

- Default: 30 seconds per test
- Waits: Explicit waits for key elements (5-15 seconds)
- Visibility checks: Short timeouts (2-3 seconds) for optional elements

### Mock API Polling Simulation

The inventory progress endpoint is mocked to simulate real polling behavior:

```typescript
let pollCount = 0;
await this.page.route('**/api/v1/canonical/onboard/inventory/job-1/status', async (route) => {
  pollCount++;
  if (pollCount <= 2) {
    // Return in-progress
  } else {
    // Return completed
  }
});
```

This tests the UI's polling logic without actual delays.

## Running the Tests

### Quick Run
```bash
npx playwright test tests/verification/canonical-onboarding-verification.spec.ts
```

### Debug Mode
```bash
npx playwright test tests/verification/canonical-onboarding-verification.spec.ts --ui
```

### Using Scripts
```bash
# Windows
.\tests\verification\run-canonical-verification.bat --ui

# Linux/Mac
./tests/verification/run-canonical-verification.sh --ui
```

## Test Coverage

### Covered Scenarios ✅
- [x] Complete onboarding wizard flow
- [x] Preflight check success and failure
- [x] Anchor environment selection
- [x] Inventory phase execution
- [x] Progress monitoring
- [x] Auto-linking by content hash
- [x] Untracked workflow listing
- [x] Manual workflow linking
- [x] Matrix view rendering
- [x] Status badge display (linked, drift, out-of-date)
- [x] Multiple environment handling
- [x] Error message display
- [x] Retry functionality

### Not Covered (Out of Scope) ❌
- [ ] Actual GitHub API integration
- [ ] Real n8n instance connectivity
- [ ] Database transactions
- [ ] Performance/load testing
- [ ] Accessibility testing
- [ ] Mobile responsive testing

## Maintenance Guide

### Updating Tests When UI Changes

If UI components change, update selectors:

```typescript
// Before
const button = page.locator('button:has-text("Start Onboarding")');

// After (if button text changes)
const button = page.locator('button:has-text("Begin Setup")');
```

### Updating Tests When API Changes

If API responses change, update test data:

```typescript
// In test-data.ts
canonical: {
  inventoryComplete: {
    // Update structure to match new API response
    job_id: 'job-1',
    status: 'COMPLETED',
    new_field: 'new_value'  // Add new fields
  }
}
```

### Adding New Test Scenarios

1. Add test data to `test-data.ts`
2. Add mock route to `mock-api.ts` if needed
3. Write test in `canonical-onboarding-verification.spec.ts`
4. Update documentation

Example:
```typescript
test('should handle concurrent onboarding attempts', async ({ page }) => {
  // Mock API to return "onboarding already in progress" error
  await page.route('**/api/v1/canonical/onboard/inventory', async (route) => {
    await route.fulfill({
      status: 409,
      contentType: 'application/json',
      body: JSON.stringify({ error: 'Onboarding already in progress' })
    });
  });

  // Test implementation...
});
```

## Debugging Tips

### Test Fails Intermittently

**Cause:** Timing issues, animations, network delays

**Solution:**
```typescript
// Add explicit waits
await expect(element).toBeVisible({ timeout: 10000 });

// Wait for network idle
await page.waitForLoadState('networkidle');
```

### Element Not Found

**Cause:** Selector changed or element doesn't exist

**Solution:**
1. Run in UI mode: `--ui`
2. Inspect the actual page
3. Update selector or add fallback:
```typescript
const element = page.locator('[data-testid="element"]').or(
  page.locator('.fallback-selector')
);
```

### Mock Not Intercepting

**Cause:** Route pattern doesn't match or mock not set up

**Solution:**
1. Check route pattern matches actual request
2. Ensure `mockCanonicalFlow()` is called in `beforeEach`
3. Use `page.on('request', ...)` to debug:
```typescript
page.on('request', request => {
  console.log('Request:', request.url());
});
```

### Tests Pass Locally, Fail in CI

**Cause:** Environment differences, timing

**Solution:**
1. Check Playwright config for CI settings
2. Increase timeouts in CI environment
3. Ensure all dependencies are installed in CI

## Future Improvements

### Short Term
1. Add more error scenarios (network failures, timeout)
2. Test pagination if workflow list grows large
3. Add tests for filters/search in matrix view

### Medium Term
1. Visual regression testing (Percy, Chromatic)
2. Accessibility testing (axe-core)
3. Performance benchmarks

### Long Term
1. Integrate with CI/CD pipeline
2. Add mutation testing to verify test quality
3. Create synthetic user flows for monitoring

## Questions & Answers

### Q: Why not use the existing E2E test?
**A:** The existing E2E test in `tests/e2e/canonical-onboarding.spec.ts` is more basic. This verification test is more comprehensive and provides better documentation.

### Q: Should we delete this after verification?
**A:** No, these tests serve as excellent regression tests. Keep them and run regularly.

### Q: Can we run against real backend?
**A:** Yes, by commenting out `mockCanonicalFlow()` and ensuring backend is running at the base URL.

### Q: How do we add this to CI?
**A:** Add to CI config:
```yaml
- name: Run Canonical Onboarding Verification
  run: npx playwright test tests/verification/canonical-onboarding-verification.spec.ts
```

### Q: What if preflight always fails?
**A:** Check that `test-data.ts` has `preflightSuccess` configured correctly. The mock should return success by default.

## Related Documentation

- **Feature Spec:** `mvp_readiness_pack/04_canonical_workflows.md`
- **Backend E2E Tests:** `n8n-ops-backend/tests/e2e/test_canonical_e2e.py`
- **Onboarding Service:** `n8n-ops-backend/app/services/canonical_onboarding_service.py`
- **UI Component:** `n8n-ops-ui/src/pages/CanonicalOnboardingPage.tsx`

## Contact

For questions or issues with these tests:
1. Review the comprehensive documentation: `CANONICAL_ONBOARDING_VERIFICATION.md`
2. Check the quick start guide: `CANONICAL_ONBOARDING_QUICK_START.md`
3. Consult the feature summary: `FEATURE_1767910795355_SUMMARY.md`

---

**Created:** 2026-01-08
**Author:** Development Team
**Version:** 1.0
**Status:** Active
