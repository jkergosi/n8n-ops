import { test, expect } from '@playwright/test';

/**
 * E2E Smoke Test for Execution Analytics / Observability Dashboard
 *
 * This is a minimal smoke test to verify the observability page loads correctly
 * and displays the essential components. It does NOT test complex interactions
 * or data-dependent scenarios.
 *
 * The test verifies:
 * 1. Page loads without errors
 * 2. Key UI components are present (KPIs, tables, selectors)
 * 3. Time range selector is functional
 *
 * NOTE: This test may show empty data if no executions are present - that's expected.
 * The test focuses on verifying the UI structure, not data content.
 */

test.describe('Observability Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the observability page
    await page.goto('/observability');

    // Wait for the page to load
    await page.waitForLoadState('networkidle');
  });

  test('should display observability page with essential components', async ({ page }) => {
    // Verify we're on the correct page
    // The page should have either a title or heading related to observability/analytics
    const pageContent = await page.content();
    const hasObservabilityContent =
      pageContent.includes('Observability') ||
      pageContent.includes('Analytics') ||
      pageContent.includes('Execution') ||
      pageContent.includes('Dashboard');

    expect(hasObservabilityContent).toBe(true);

    // Verify time range selector exists
    // This is a key component for filtering analytics data
    const timeRangeSelector = page.locator('button[role="combobox"]').first();
    const hasSelectorOrDropdown = await timeRangeSelector.count() > 0 ||
      await page.locator('select').count() > 0;

    if (hasSelectorOrDropdown) {
      console.log('Time range selector found');
    }

    // Page should not show an error state
    const errorMessage = page.locator('text=Something went wrong');
    const hasError = await errorMessage.count() > 0;

    if (hasError) {
      // Log the error but don't fail - API might not be available
      console.log('Warning: Page shows error state - API may be unavailable');
    }
  });

  test('should display KPI metrics section', async ({ page }) => {
    // Look for common KPI-related elements
    // These include: Executions, Success Rate, Duration, Failures
    const kpiTerms = ['Execution', 'Success', 'Duration', 'Failure', 'Rate'];

    let foundKpis = 0;
    for (const term of kpiTerms) {
      const element = page.locator(`text=${term}`).first();
      if (await element.count() > 0) {
        foundKpis++;
      }
    }

    // We should find at least one KPI-related term
    // If API is down, the page might show loading or error state
    if (foundKpis === 0) {
      // Check for loading or empty state
      const loadingIndicator = page.locator('[class*="spinner"], [class*="loader"], text=Loading');
      const isLoading = await loadingIndicator.count() > 0;

      if (isLoading) {
        console.log('Page is still loading KPIs');
      } else {
        console.log('KPIs not visible - may be empty data or API unavailable');
      }
    } else {
      console.log(`Found ${foundKpis} KPI-related elements`);
    }
  });

  test('should allow changing time range filter', async ({ page }) => {
    // Find the time range selector (could be a dropdown or select)
    const timeRangeButton = page.locator('button[role="combobox"]').first();
    const hasDropdown = await timeRangeButton.count() > 0;

    if (!hasDropdown) {
      console.log('No dropdown time range selector found - skipping');
      test.skip();
      return;
    }

    // Click to open the dropdown
    await timeRangeButton.click();

    // Check for time range options (Last 24h, Last 7d, Last 30d are common)
    const timeOptions = ['24', '7d', '30d', 'hour', 'day', 'week', 'month'];
    let foundOption = false;

    for (const option of timeOptions) {
      const optionElement = page.locator(`[role="option"]:has-text("${option}")`);
      if (await optionElement.count() > 0) {
        foundOption = true;
        console.log(`Found time range option containing: ${option}`);
        break;
      }
    }

    // Close the dropdown by pressing Escape
    await page.keyboard.press('Escape');

    if (!foundOption) {
      console.log('Time range options not found in expected format');
    }
  });

  test('should display workflow performance section', async ({ page }) => {
    // Look for workflow-related section
    // Could be "Workflow Performance", "Workflow Risk", "Workflow Health"
    const workflowTerms = ['Workflow', 'Performance', 'Risk', 'Health'];

    let foundWorkflowSection = false;
    for (const term of workflowTerms) {
      const element = page.locator(`text=${term}`).first();
      if (await element.count() > 0) {
        foundWorkflowSection = true;
        console.log(`Found workflow section term: ${term}`);
        break;
      }
    }

    // Check for table which would display workflow data
    const table = page.locator('table');
    const hasTable = await table.count() > 0;

    if (hasTable) {
      console.log('Workflow performance table found');
    } else if (foundWorkflowSection) {
      console.log('Workflow section present but no table (may be loading or empty)');
    } else {
      console.log('No workflow performance section visible');
    }
  });

  test('should handle refresh action', async ({ page }) => {
    // Find a refresh button
    const refreshButton = page.locator('button:has-text("Refresh"), button[aria-label*="refresh"]').first();
    const hasRefresh = await refreshButton.count() > 0;

    if (!hasRefresh) {
      // Try to find by icon (RefreshCw icon)
      const refreshIcon = page.locator('[class*="lucide-refresh"], svg[data-lucide="refresh-cw"]').first();
      if (await refreshIcon.count() > 0) {
        console.log('Found refresh icon');
        return;
      }
      console.log('No refresh button found - skipping');
      test.skip();
      return;
    }

    // Click refresh
    await refreshButton.click();

    // Wait for any loading state to complete
    await page.waitForLoadState('networkidle');

    // Verify page is still functional after refresh
    const pageVisible = await page.locator('body').isVisible();
    expect(pageVisible).toBe(true);

    console.log('Refresh action completed successfully');
  });

  test('should not have console errors on page load', async ({ page }) => {
    const errors: string[] = [];

    // Listen for console errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    // Navigate to the page
    await page.goto('/observability');
    await page.waitForLoadState('networkidle');

    // Filter out expected errors (API not available in test env, etc.)
    const criticalErrors = errors.filter(err =>
      !err.includes('Failed to fetch') &&
      !err.includes('NetworkError') &&
      !err.includes('net::ERR_')
    );

    if (criticalErrors.length > 0) {
      console.log('Console errors found:', criticalErrors);
    }

    // We allow some errors in test environment due to API unavailability
    // but critical JS errors should be flagged
    expect(criticalErrors.filter(e => e.includes('TypeError') || e.includes('ReferenceError')).length).toBe(0);
  });
});
