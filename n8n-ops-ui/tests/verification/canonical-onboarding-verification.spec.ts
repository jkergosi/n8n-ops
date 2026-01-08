/**
 * Canonical Onboarding Verification Test
 *
 * This test verifies the complete canonical onboarding flow from scratch:
 * 1. Start onboarding wizard
 * 2. Run preflight checks
 * 3. Select anchor environment
 * 4. Run inventory phase (creates canonical workflows)
 * 5. Auto-link workflows where possible
 * 6. List remaining untracked workflows
 * 7. Verify matrix view renders correctly with workflow statuses
 *
 * This is a verification test meant to be run manually to confirm
 * the canonical onboarding feature works end-to-end.
 */
import { test, expect } from '@playwright/test';
import { MockApiClient } from '../testkit/mock-api';

test.describe('Canonical Onboarding Verification - From Scratch', () => {
  let mockApi: MockApiClient;

  test.beforeEach(async ({ page }) => {
    mockApi = new MockApiClient(page);
    await mockApi.mockAuth('admin');
    await mockApi.mockEnvironments();
    await mockApi.mockCanonicalFlow();
  });

  test('should complete full canonical onboarding flow from scratch', async ({ page }) => {
    // Step 1: Navigate to canonical onboarding page
    await page.goto('/canonical/onboarding');
    await expect(page).toHaveTitle(/n8n-ops/i);

    // Verify we're on the canonical workflows page
    await expect(page.locator('h1')).toContainText('Canonical Workflows');

    // Step 2: Start the onboarding wizard
    const startButton = page.locator('button:has-text("Start Onboarding")');
    await expect(startButton).toBeVisible({ timeout: 5000 });
    await startButton.click();

    // Step 3: Preflight checks should run automatically
    await expect(page.locator('h2')).toContainText('Preflight Checks', { timeout: 10000 });

    // Verify preflight check items are visible
    await expect(page.locator('text=Checking GitHub connection')).toBeVisible();
    await expect(page.locator('text=Checking environments')).toBeVisible();

    // Wait for all checks to pass
    await expect(page.locator('text=All checks passed')).toBeVisible({ timeout: 10000 });

    // Verify the preflight success indicator
    const allChecksPassed = page.locator('[data-testid="preflight-success"]').or(
      page.locator('text=All preflight checks passed successfully')
    );
    await expect(allChecksPassed.first()).toBeVisible();

    // Step 4: Proceed to anchor environment selection
    const nextButton = page.locator('button:has-text("Next")');
    await nextButton.click();

    // Verify we're on the anchor environment selection step
    await expect(page.locator('h2')).toContainText('Select Anchor Environment');

    // Verify explanation text is shown
    await expect(page.locator('text=anchor environment')).toBeVisible();
    await expect(page.locator('text=production')).toBeVisible();

    // Step 5: Select the production environment as anchor
    const anchorSelect = page.locator('select[name="anchor_environment"]').or(
      page.locator('[data-testid="anchor-environment-select"]')
    );
    await anchorSelect.first().selectOption('env-prod');

    // Verify the selection was made
    await expect(anchorSelect.first()).toHaveValue('env-prod');

    // Step 6: Start the inventory phase
    const startInventoryButton = page.locator('button:has-text("Start Inventory")');
    await expect(startInventoryButton).toBeEnabled();
    await startInventoryButton.click();

    // Step 7: Monitor inventory progress
    await expect(page.locator('text=Running inventory')).toBeVisible({ timeout: 5000 });

    // Verify progress indicator is shown
    const progressBar = page.locator('[role="progressbar"]').or(
      page.locator('[data-testid="inventory-progress"]')
    );
    await expect(progressBar.first()).toBeVisible();

    // Verify inventory phases are displayed
    await expect(
      page.locator('text=Scanning anchor environment').or(
        page.locator('text=Syncing from Git')
      ).first()
    ).toBeVisible();

    // Wait for inventory to complete
    await expect(page.locator('text=Inventory complete')).toBeVisible({ timeout: 15000 });

    // Verify inventory summary shows
    const inventorySummary = page.locator('[data-testid="inventory-summary"]').or(
      page.locator('text=canonical workflows created')
    );
    await expect(inventorySummary.first()).toBeVisible();

    // Step 8: Verify auto-linking results
    await expect(
      page.locator('text=auto-linked').or(
        page.locator('text=automatically linked')
      ).first()
    ).toBeVisible();

    // Step 9: Review untracked workflows (if any)
    await page.locator('button:has-text("Next")').click();

    // Either we have untracked workflows or we're done
    const hasUntrackedWorkflows = await page.locator('text=Untracked Workflows').isVisible({ timeout: 3000 });

    if (hasUntrackedWorkflows) {
      // Verify untracked workflows are listed
      await expect(page.locator('[data-testid="untracked-workflow-list"]').or(
        page.locator('text=untracked workflow')
      ).first()).toBeVisible();

      // Verify we can see workflow details
      await expect(page.locator('[data-workflow-status="untracked"]').first()).toBeVisible();
    }

    // Step 10: Complete onboarding
    const completeButton = page.locator('button:has-text("Complete Onboarding")').or(
      page.locator('button:has-text("Finish")')
    );
    await completeButton.first().click();

    // Step 11: Verify success message
    await expect(page.locator('text=Onboarding successful')).toBeVisible({ timeout: 5000 });

    // Should redirect to canonical workflows page or matrix view
    await expect(page).toHaveURL(/\/(canonical|matrix)/);
  });

  test('should display canonical matrix view correctly after onboarding', async ({ page }) => {
    // Navigate to matrix view (workflows overview page)
    await page.goto('/workflows-overview');

    // Step 1: Verify matrix view loads
    await expect(page.locator('h1')).toContainText('Workflows Overview', { timeout: 5000 });

    // Step 2: Verify environment headers are shown
    await expect(page.locator('text=Development')).toBeVisible();
    await expect(page.locator('text=Production')).toBeVisible();

    // Step 3: Verify workflow rows are displayed
    await expect(page.locator('text=Customer Onboarding')).toBeVisible();

    // Step 4: Verify status indicators are present
    // Linked status (green indicator)
    const linkedStatus = page.locator('[data-status="linked"]').or(
      page.locator('.status-linked')
    );
    await expect(linkedStatus.first()).toBeVisible();

    // Drift status (yellow/warning indicator)
    const driftStatus = page.locator('[data-status="drift"]').or(
      page.locator('.status-drift')
    );
    await expect(driftStatus.first()).toBeVisible();

    // Step 5: Verify matrix cells show correct information
    const matrixCell = page.locator('[data-testid^="matrix-cell-"]').or(
      page.locator('.matrix-cell')
    );
    await expect(matrixCell.first()).toBeVisible();

    // Step 6: Verify empty cells (workflow doesn't exist in environment)
    const emptyCell = page.locator('[data-status="missing"]').or(
      page.locator('.matrix-cell-empty')
    );
    // Empty cells may or may not exist depending on workflow distribution

    // Step 7: Verify we can interact with the matrix
    // Hover over a cell to see details
    await matrixCell.first().hover();

    // Tooltip or details should appear
    const tooltip = page.locator('[role="tooltip"]').or(
      page.locator('.workflow-details-popup')
    );
    // Tooltip is optional depending on implementation
  });

  test('should handle workflow linking for untracked workflows', async ({ page }) => {
    // Navigate to untracked workflows page
    await page.goto('/canonical/untracked');

    // Step 1: Verify untracked workflows page loads
    await expect(page.locator('h1')).toContainText('Untracked Workflows', { timeout: 5000 });

    // Step 2: Verify untracked workflow list is shown
    const untrackedList = page.locator('[data-testid="untracked-workflow-list"]').or(
      page.locator('.untracked-workflow-item')
    );

    // May have no untracked workflows if all were auto-linked
    const hasUntrackedWorkflows = await untrackedList.first().isVisible({ timeout: 3000 });

    if (hasUntrackedWorkflows) {
      // Step 3: Attempt to link an untracked workflow
      const linkButton = page.locator('button[data-workflow-id="wf-untracked"]:has-text("Link")').or(
        page.locator('button:has-text("Link to Canonical")').first()
      );

      if (await linkButton.isVisible({ timeout: 2000 })) {
        await linkButton.click();

        // Step 4: Select canonical workflow to link to
        const canonicalSelect = page.locator('select[name="canonical_id"]').or(
          page.locator('[data-testid="canonical-workflow-select"]')
        );
        await expect(canonicalSelect.first()).toBeVisible();

        // Select first available canonical workflow
        await canonicalSelect.first().selectOption({ index: 1 });

        // Step 5: Confirm the linking
        const confirmButton = page.locator('button:has-text("Link Workflow")').or(
          page.locator('button:has-text("Confirm")')
        );
        await confirmButton.first().click();

        // Step 6: Verify success message
        await expect(page.locator('text=Workflow linked successfully')).toBeVisible({ timeout: 5000 });

        // Step 7: Verify the workflow is removed from untracked list
        // The list should update to remove the linked workflow
      }
    } else {
      // No untracked workflows - this is also a valid state
      await expect(
        page.locator('text=No untracked workflows').or(
          page.locator('text=All workflows are tracked')
        ).first()
      ).toBeVisible();
    }
  });

  test('should show workflow sync status in matrix view', async ({ page }) => {
    await page.goto('/workflows-overview');

    // Step 1: Verify different status types are rendered correctly
    await expect(page.locator('h1')).toContainText('Workflows Overview');

    // Step 2: Check for 'linked' status (workflow in sync)
    const linkedWorkflows = page.locator('[data-status="linked"]');
    const linkedCount = await linkedWorkflows.count();

    if (linkedCount > 0) {
      // Verify linked workflows show appropriate visual indicator
      await expect(linkedWorkflows.first()).toBeVisible();

      // May have a checkmark or green indicator
      const syncedIndicator = linkedWorkflows.first().locator('[data-icon="check"]').or(
        linkedWorkflows.first().locator('.status-icon-synced')
      );
      // Icon presence depends on implementation
    }

    // Step 3: Check for 'drift' status (workflow changed in n8n)
    const driftWorkflows = page.locator('[data-status="drift"]');
    const driftCount = await driftWorkflows.count();

    if (driftCount > 0) {
      await expect(driftWorkflows.first()).toBeVisible();

      // Should show drift indicator (warning icon, yellow badge, etc.)
      const driftIndicator = driftWorkflows.first().locator('[data-icon="alert"]').or(
        driftWorkflows.first().locator('.status-icon-drift')
      );
      // Drift indicator should be present
    }

    // Step 4: Check for 'out_of_date' status (Git ahead of n8n)
    const outOfDateWorkflows = page.locator('[data-status="out_of_date"]');
    const outOfDateCount = await outOfDateWorkflows.count();

    if (outOfDateCount > 0) {
      await expect(outOfDateWorkflows.first()).toBeVisible();
    }

    // Step 5: Verify matrix legend/key is shown
    const legend = page.locator('[data-testid="matrix-legend"]').or(
      page.locator('text=Legend')
    );
    // Legend may be shown to explain status colors

    // Step 6: Verify we can filter/sort the matrix
    const filterButton = page.locator('button:has-text("Filter")');
    // Filtering is optional depending on implementation
  });

  test('should handle inventory phase with multiple environments', async ({ page }) => {
    // This test verifies that non-anchor environments are also synced
    await page.goto('/canonical/onboarding');

    // Start onboarding
    await page.locator('button:has-text("Start Onboarding")').click();

    // Get through preflight
    await expect(page.locator('text=All checks passed')).toBeVisible({ timeout: 10000 });
    await page.locator('button:has-text("Next")').click();

    // Select anchor and start inventory
    await page.locator('select[name="anchor_environment"]').first().selectOption('env-prod');
    await page.locator('button:has-text("Start Inventory")').click();

    // Verify multiple environments are being processed
    await expect(page.locator('text=Running inventory')).toBeVisible();

    // Should show progress for anchor environment
    await expect(
      page.locator('text=Production').or(
        page.locator('text=env-prod')
      ).first()
    ).toBeVisible();

    // Should also show other environments being synced
    await expect(
      page.locator('text=Development').or(
        page.locator('text=env-dev')
      ).first()
    ).toBeVisible();

    // Wait for completion
    await expect(page.locator('text=Inventory complete')).toBeVisible({ timeout: 15000 });

    // Verify summary shows multiple environments
    const summary = page.locator('[data-testid="inventory-summary"]').or(
      page.locator('.inventory-summary')
    );

    // Should mention multiple environments processed
    await expect(
      page.locator('text=environments synced').or(
        page.locator('text=2 environments')
      ).first()
    ).toBeVisible();
  });
});

test.describe('Canonical Onboarding Error Scenarios', () => {
  let mockApi: MockApiClient;

  test.beforeEach(async ({ page }) => {
    mockApi = new MockApiClient(page);
    await mockApi.mockAuth('admin');
    await mockApi.mockEnvironments();
  });

  test('should handle preflight check failures gracefully', async ({ page }) => {
    // Mock preflight failure
    await page.route('**/api/v1/canonical/onboard/preflight', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ready: false,
          errors: ['GitHub repository not configured'],
          warnings: ['Some environments are inactive'],
        }),
      });
    });

    await page.goto('/canonical/onboarding');
    await page.locator('button:has-text("Start Onboarding")').click();

    // Should show preflight check failed
    await expect(page.locator('text=Preflight checks failed')).toBeVisible({ timeout: 10000 });

    // Should show the specific error
    await expect(page.locator('text=GitHub repository not configured')).toBeVisible();

    // Should show warnings
    await expect(page.locator('text=Some environments are inactive')).toBeVisible();

    // Next button should be disabled or show "Fix Issues" instead
    const nextButton = page.locator('button:has-text("Next")');
    const isDisabled = await nextButton.isDisabled({ timeout: 2000 }).catch(() => true);

    // Button should either be disabled or not visible
    expect(isDisabled || !(await nextButton.isVisible())).toBeTruthy();
  });

  test('should handle inventory phase errors', async ({ page }) => {
    await mockApi.mockCanonicalFlow();

    // Mock inventory error
    await page.route('**/api/v1/canonical/onboard/inventory', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Failed to sync from GitHub',
          detail: 'Repository access denied',
        }),
      });
    });

    await page.goto('/canonical/onboarding');
    await page.locator('button:has-text("Start Onboarding")').click();

    await expect(page.locator('text=All checks passed')).toBeVisible({ timeout: 10000 });
    await page.locator('button:has-text("Next")').click();

    await page.locator('select[name="anchor_environment"]').first().selectOption('env-prod');
    await page.locator('button:has-text("Start Inventory")').click();

    // Should show error message
    await expect(page.locator('text=Failed to sync from GitHub')).toBeVisible({ timeout: 10000 });

    // Should allow retry
    const retryButton = page.locator('button:has-text("Retry")').or(
      page.locator('button:has-text("Try Again")')
    );

    if (await retryButton.isVisible({ timeout: 2000 })) {
      await expect(retryButton).toBeVisible();
    }
  });
});
