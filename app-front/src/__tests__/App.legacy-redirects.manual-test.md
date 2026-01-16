# Manual Testing Guide: Legacy Route Redirects

## Overview
This guide provides step-by-step instructions to manually test that legacy environment routes correctly redirect to the new filtered routes with `env_id` parameter preserved.

## Prerequisites
- Application running locally at `http://localhost:3000`
- At least one test environment created (note its UUID)
- Browser DevTools open to monitor network and navigation

## Test Cases

### Test 1: Workflows Redirect
**Objective:** Verify `/environments/:id/workflows` redirects to `/workflows?env_id=:id`

**Steps:**
1. Get a valid environment ID from `/environments` page
2. Navigate to: `http://localhost:3000/environments/{ENV_ID}/workflows`
3. **Expected:** Browser redirects to `/workflows?env_id={ENV_ID}`
4. **Expected:** Environment dropdown shows the selected environment
5. **Expected:** Workflows table displays only workflows for that environment

**Example:**
```
Input:  http://localhost:3000/environments/550e8400-e29b-41d4-a716-446655440000/workflows
Output: http://localhost:3000/workflows?env_id=550e8400-e29b-41d4-a716-446655440000
```

### Test 2: Deployments Redirect
**Objective:** Verify `/environments/:id/deployments` redirects to `/deployments?env_id=:id`

**Steps:**
1. Get a valid environment ID from `/environments` page
2. Navigate to: `http://localhost:3000/environments/{ENV_ID}/deployments`
3. **Expected:** Browser redirects to `/deployments?env_id={ENV_ID}`
4. **Expected:** Environment dropdown shows the selected environment
5. **Expected:** Deployments list shows only deployments for that environment

**Example:**
```
Input:  http://localhost:3000/environments/550e8400-e29b-41d4-a716-446655440000/deployments
Output: http://localhost:3000/deployments?env_id=550e8400-e29b-41d4-a716-446655440000
```

### Test 3: Snapshots Redirect
**Objective:** Verify `/environments/:id/snapshots` redirects to `/snapshots?env_id=:id`

**Steps:**
1. Get a valid environment ID from `/environments` page
2. Navigate to: `http://localhost:3000/environments/{ENV_ID}/snapshots`
3. **Expected:** Browser redirects to `/snapshots?env_id={ENV_ID}`
4. **Expected:** Environment dropdown shows the selected environment
5. **Expected:** Snapshots table displays only snapshots for that environment

**Example:**
```
Input:  http://localhost:3000/environments/550e8400-e29b-41d4-a716-446655440000/snapshots
Output: http://localhost:3000/snapshots?env_id=550e8400-e29b-41d4-a716-446655440000
```

### Test 4: Executions Redirect
**Objective:** Verify `/environments/:id/executions` redirects to `/executions?env_id=:id`

**Steps:**
1. Get a valid environment ID from `/environments` page
2. Navigate to: `http://localhost:3000/environments/{ENV_ID}/executions`
3. **Expected:** Browser redirects to `/executions?env_id={ENV_ID}`
4. **Expected:** Environment dropdown shows the selected environment
5. **Expected:** Executions table shows only executions for that environment

**Example:**
```
Input:  http://localhost:3000/environments/550e8400-e29b-41d4-a716-446655440000/executions
Output: http://localhost:3000/executions?env_id=550e8400-e29b-41d4-a716-446655440000
```

### Test 5: Activity Redirect
**Objective:** Verify `/environments/:id/activity` redirects to `/activity?env_id=:id`

**Steps:**
1. Get a valid environment ID from `/environments` page
2. Navigate to: `http://localhost:3000/environments/{ENV_ID}/activity`
3. **Expected:** Browser redirects to `/activity?env_id={ENV_ID}`
4. **Expected:** Environment dropdown shows the selected environment
5. **Expected:** Activity feed displays only activity for that environment

**Example:**
```
Input:  http://localhost:3000/environments/550e8400-e29b-41d4-a716-446655440000/activity
Output: http://localhost:3000/activity?env_id=550e8400-e29b-41d4-a716-446655440000
```

### Test 6: Credentials Redirect
**Objective:** Verify `/environments/:id/credentials` redirects to `/credentials?env_id=:id`

**Steps:**
1. Get a valid environment ID from `/environments` page
2. Navigate to: `http://localhost:3000/environments/{ENV_ID}/credentials`
3. **Expected:** Browser redirects to `/credentials?env_id={ENV_ID}`
4. **Expected:** Environment dropdown shows the selected environment
5. **Expected:** Credentials table displays only credentials for that environment

**Example:**
```
Input:  http://localhost:3000/environments/550e8400-e29b-41d4-a716-446655440000/credentials
Output: http://localhost:3000/credentials?env_id=550e8400-e29b-41d4-a716-446655440000
```

## Edge Cases to Test

### Edge Case 1: Missing Environment ID
**Objective:** Verify redirect handles missing ID gracefully

**Steps:**
1. Navigate to: `http://localhost:3000/environments//workflows` (note the double slash)
2. **Expected:** Browser redirects to `/workflows` (no env_id parameter)
3. **Expected:** Environment dropdown shows "All Environments"
4. **Expected:** All workflows displayed

**Repeat for:** `/environments//deployments`, `/environments//snapshots`, `/environments//executions`, `/environments//activity`, `/environments//credentials`

### Edge Case 2: Invalid Environment ID
**Objective:** Verify redirect preserves ID even if invalid, allowing target page to handle validation

**Steps:**
1. Navigate to: `http://localhost:3000/environments/invalid-id-12345/workflows`
2. **Expected:** Browser redirects to `/workflows?env_id=invalid-id-12345`
3. **Expected:** Target page handles invalid ID (shows error or falls back to "All Environments")

### Edge Case 3: Special Characters in Environment ID
**Objective:** Verify URL encoding is handled correctly

**Steps:**
1. If you have an environment with special characters in ID, use that
2. Or test with: `http://localhost:3000/environments/test-env-with-dashes_and_underscores/workflows`
3. **Expected:** Browser redirects correctly with env_id parameter preserved
4. **Expected:** No URL encoding issues

### Edge Case 4: Browser Back Button
**Objective:** Verify browser history works correctly after redirect

**Steps:**
1. Navigate to `/environments` page
2. Click on an environment to go to `/environments/{ENV_ID}`
3. Manually navigate to `/environments/{ENV_ID}/workflows`
4. Observe redirect to `/workflows?env_id={ENV_ID}`
5. Click browser back button
6. **Expected:** Returns to `/environments/{ENV_ID}` (not back to the legacy route)

## Validation Checklist

For each redirect, verify:
- [ ] URL changes from `/environments/:id/{section}` to `/{section}?env_id=:id`
- [ ] Page renders without errors
- [ ] Environment dropdown is pre-selected to the correct environment
- [ ] Data displayed is filtered to that environment
- [ ] No console errors in DevTools
- [ ] Network requests include the env_id parameter
- [ ] Browser history works correctly (no redirect loops)

## Testing with Bookmarks/Saved Links

**Objective:** Verify users with saved bookmarks to old routes are seamlessly redirected

**Steps:**
1. Create bookmarks for old routes:
   - `http://localhost:3000/environments/{ENV_ID}/workflows`
   - `http://localhost:3000/environments/{ENV_ID}/deployments`
   - etc.
2. Navigate using each bookmark
3. **Expected:** Each bookmark redirects to new route with env_id preserved
4. **Expected:** No user-facing errors or confusion

## Success Criteria

✅ All 6 redirect routes work correctly
✅ env_id parameter is preserved in all cases
✅ Edge cases are handled gracefully
✅ No console errors during redirects
✅ Browser history works as expected
✅ Environment filter dropdown syncs with URL parameter
✅ Data is correctly filtered on target pages

## Notes
- These redirects use `replace: true` to prevent adding legacy routes to browser history
- The redirect components are exported from `App.tsx` for unit testing
- Each redirect component checks for missing ID and falls back to base route without env_id
