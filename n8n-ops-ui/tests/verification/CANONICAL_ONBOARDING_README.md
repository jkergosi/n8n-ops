# Canonical Onboarding Verification Tests

## Quick Start

Run the canonical onboarding verification test:

```bash
# Simple run
npx playwright test tests/verification/canonical-onboarding-verification.spec.ts

# Visual mode (recommended)
npx playwright test tests/verification/canonical-onboarding-verification.spec.ts --ui

# Using the script (Windows)
.\tests\verification\run-canonical-verification.bat --ui

# Using the script (Linux/Mac)
./tests/verification/run-canonical-verification.sh --ui
```

## What This Tests

This verification suite validates the complete canonical workflow onboarding flow:

1. ✅ **Preflight Checks** - System readiness validation
2. ✅ **Anchor Environment Selection** - Choose production as source of truth
3. ✅ **Inventory Phase** - Scan and sync all environments
4. ✅ **Auto-linking** - Match workflows by content hash
5. ✅ **Untracked Workflows** - List and manually link remaining workflows
6. ✅ **Matrix View** - Display workflow status across environments
7. ✅ **Error Handling** - Graceful failure scenarios

## Test Scenarios (7 total)

| # | Test Name | Duration | Purpose |
|---|-----------|----------|---------|
| 1 | Complete onboarding flow | ~15s | Full wizard journey |
| 2 | Matrix view display | ~5s | Grid rendering |
| 3 | Workflow linking | ~4s | Manual linking |
| 4 | Status indicators | ~3s | Badge display |
| 5 | Multiple environments | ~12s | Multi-env sync |
| 6 | Preflight failures | ~2s | Error handling |
| 7 | Inventory errors | ~2s | Recovery testing |

**Total: ~45 seconds**

## Expected Output

```
Running 7 tests using 1 worker

✓ [chromium] › canonical-onboarding-verification.spec.ts:29:3 › should complete full canonical onboarding flow from scratch (15s)
✓ [chromium] › canonical-onboarding-verification.spec.ts:144:3 › should display canonical matrix view correctly (5s)
✓ [chromium] › canonical-onboarding-verification.spec.ts:194:3 › should handle workflow linking (4s)
✓ [chromium] › canonical-onboarding-verification.spec.ts:249:3 › should show workflow sync status (3s)
✓ [chromium] › canonical-onboarding-verification.spec.ts:303:3 › should handle multiple environments (12s)
✓ [chromium] › canonical-onboarding-verification.spec.ts:361:3 › should handle preflight failures (2s)
✓ [chromium] › canonical-onboarding-verification.spec.ts:395:3 › should handle inventory errors (2s)

7 passed (43s)
```

## File Structure

```
tests/verification/
├── canonical-onboarding-verification.spec.ts    # Main test suite
├── CANONICAL_ONBOARDING_VERIFICATION.md         # Comprehensive guide
├── CANONICAL_ONBOARDING_QUICK_START.md          # Quick reference
├── CANONICAL_ONBOARDING_README.md               # This file
├── IMPLEMENTATION_NOTES.md                      # Technical details
├── run-canonical-verification.bat               # Windows runner
└── run-canonical-verification.sh                # Linux/Mac runner
```

## Documentation

- **Quick Start:** [`CANONICAL_ONBOARDING_QUICK_START.md`](./CANONICAL_ONBOARDING_QUICK_START.md)
- **Full Documentation:** [`CANONICAL_ONBOARDING_VERIFICATION.md`](./CANONICAL_ONBOARDING_VERIFICATION.md)
- **Implementation Notes:** [`IMPLEMENTATION_NOTES.md`](./IMPLEMENTATION_NOTES.md)
- **Feature Summary:** `../../FEATURE_1767910795355_SUMMARY.md`
- **Verification Checklist:** `../../VERIFICATION_CHECKLIST_1767910795355.md`

## Requirements

- Node.js (v18+)
- npm
- Playwright browsers (`npx playwright install`)

## No Backend Required

These tests use **mock APIs**, so you don't need:
- ❌ Backend server running
- ❌ Database connection
- ❌ GitHub access
- ❌ n8n instances

Perfect for:
- ✅ Quick verification
- ✅ Offline development
- ✅ CI/CD pipelines
- ✅ Frontend-only changes

## Debugging

### UI Mode (Best for debugging)
```bash
npx playwright test tests/verification/canonical-onboarding-verification.spec.ts --ui
```

### Headed Mode (See browser)
```bash
npx playwright test tests/verification/canonical-onboarding-verification.spec.ts --headed
```

### Verbose Output
```bash
npx playwright test tests/verification/canonical-onboarding-verification.spec.ts --reporter=list
```

### View HTML Report
```bash
npx playwright test tests/verification/canonical-onboarding-verification.spec.ts --reporter=html
npx playwright show-report
```

## Troubleshooting

### Tests timeout
```bash
npx playwright test tests/verification/canonical-onboarding-verification.spec.ts --timeout=120000
```

### Playwright not found
```bash
npx playwright install
```

### "Cannot find module" errors
```bash
npm install
```

### Tests fail unexpectedly
1. Run in UI mode: `--ui`
2. Check screenshots in `test-results/`
3. View trace: `npx playwright show-trace test-results/trace.zip`
4. Review [troubleshooting guide](./CANONICAL_ONBOARDING_VERIFICATION.md#troubleshooting)

## Integration with CI/CD

Add to your CI pipeline:

```yaml
# GitHub Actions example
- name: Run Canonical Onboarding Verification
  run: |
    cd n8n-ops-ui
    npx playwright test tests/verification/canonical-onboarding-verification.spec.ts
```

## Test Architecture

```
Test Suite
    ↓
MockApiClient.mockCanonicalFlow()
    ↓
Intercept API Routes
    ↓
Return TestData.canonical.*
    ↓
UI Updates
    ↓
Assertions ✓
```

## Key Test Data

From `../testkit/test-data.ts`:

```typescript
TestData.canonical = {
  preflightSuccess: { ready: true, errors: [], warnings: [] },
  inventoryComplete: {
    summary: {
      canonical_workflows_created: 15,
      environments_synced: 2,
      auto_linked: 12,
      untracked: 3
    }
  },
  matrix: { workflows, environments, matrix }
}
```

## Verification Checklist

After running tests, verify:

- [ ] All 7 tests pass ✓
- [ ] No console errors
- [ ] Screenshots look correct
- [ ] Test execution time reasonable (~45s)
- [ ] HTML report shows all scenarios

## Related Features

- **Canonical Workflows:** Core feature for workflow version control
- **Environment Sync:** Syncs workflows from n8n instances
- **Git Integration:** Stores workflows in Git repository
- **Matrix View:** Visualizes workflow status across environments

## Support

For issues or questions:
1. Check [Quick Start Guide](./CANONICAL_ONBOARDING_QUICK_START.md)
2. Review [Full Documentation](./CANONICAL_ONBOARDING_VERIFICATION.md)
3. Read [Implementation Notes](./IMPLEMENTATION_NOTES.md)
4. Check [Feature Summary](../../FEATURE_1767910795355_SUMMARY.md)

## Status

**Feature:** ✅ COMPLETE
**Tests:** ✅ READY
**Documentation:** ✅ COMPLETE
**Scripts:** ✅ WORKING

---

**Last Updated:** 2026-01-08
**Feature ID:** feature-1767910795355-mlndzgiyi
**Test Suite Version:** 1.0
