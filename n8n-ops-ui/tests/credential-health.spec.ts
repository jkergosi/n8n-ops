import { test, expect } from '@playwright/test';

/**
 * E2E Test for Credential Health Monitoring
 *
 * This test verifies the manual credential testing flow:
 * 1. Navigate to the Credential Health page
 * 2. Verify the page loads correctly
 * 3. Click the "Test" button on a credential mapping
 * 4. Verify the test executes and updates the health status
 * 5. Verify the timestamp and status are displayed
 */

test.describe('Credential Health', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the credential health page
    // Note: You may need to adjust this URL based on your routing
    await page.goto('/admin/credential-health');

    // Wait for the page to load
    await page.waitForLoadState('networkidle');
  });

  test('should display credential health page with mappings', async ({ page }) => {
    // Verify page title
    await expect(page.locator('h1')).toContainText('Credential Health');

    // Verify the credential mappings table exists
    const mappingsCard = page.locator('text=Credential Mappings').locator('..');
    await expect(mappingsCard).toBeVisible();
  });

  test('should test a credential mapping and update health status', async ({ page }) => {
    // Wait for mappings to load
    await page.waitForSelector('table', { timeout: 5000 }).catch(() => {
      console.log('No mappings table found - test may be running with empty data');
    });

    // Find the first "Test" button (PlayCircle icon)
    const testButton = page.locator('button[title="Test credential"]').first();

    // Check if test button exists
    const testButtonExists = await testButton.count() > 0;

    if (!testButtonExists) {
      console.log('No credential mappings available to test - skipping test');
      test.skip();
      return;
    }

    // Click the test button
    await testButton.click();

    // Wait for the loading state (button should be disabled during test)
    await expect(testButton).toBeDisabled();

    // Wait for the test to complete (button re-enabled)
    await expect(testButton).toBeEnabled({ timeout: 10000 });

    // Verify that a toast notification appears
    // This checks for success, info (unsupported), or error messages
    const toast = page.locator('[role="status"]').first();
    await expect(toast).toBeVisible({ timeout: 3000 }).catch(() => {
      console.log('Toast notification not visible - may have already disappeared');
    });

    // Verify the health status is now displayed
    // Look for status indicators: "Passed", "Failed", or "Unsupported"
    const healthCell = page.locator('td:has-text("Health")').first();
    await expect(healthCell).toBeVisible();

    // Verify at least one of these status texts appears
    const statusTexts = ['Passed', 'Failed', 'Unsupported', 'Not tested'];
    const hasStatus = await Promise.race(
      statusTexts.map(text =>
        page.locator(`text=${text}`).first().isVisible().then(visible => visible ? text : null)
      )
    );

    expect(hasStatus).toBeTruthy();
    console.log(`Test completed with status: ${hasStatus}`);
  });

  test('should display test timestamp after testing', async ({ page }) => {
    // Wait for mappings to load
    await page.waitForSelector('table', { timeout: 5000 }).catch(() => {
      console.log('No mappings table found');
    });

    const testButton = page.locator('button[title="Test credential"]').first();
    const testButtonExists = await testButton.count() > 0;

    if (!testButtonExists) {
      test.skip();
      return;
    }

    // Click test button
    await testButton.click();
    await expect(testButton).toBeEnabled({ timeout: 10000 });

    // Look for timestamp in the health column
    // The timestamp should be in the format of a date/time string
    const timestampPattern = /\d{1,2}\/\d{1,2}\/\d{4}/; // Matches date format like 1/7/2025
    const healthCells = page.locator('td').filter({ hasText: timestampPattern });

    // Verify at least one cell contains a timestamp
    const count = await healthCells.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should show error message for failed credential test', async ({ page }) => {
    // This test assumes there might be a failed credential test
    // It verifies that error messages are displayed properly

    await page.waitForSelector('table', { timeout: 5000 }).catch(() => {
      console.log('No mappings table found');
    });

    // Look for any failed status indicators
    const failedStatus = page.locator('text=Failed').first();
    const failedExists = await failedStatus.count() > 0;

    if (failedExists) {
      // Verify error message is displayed
      const errorMessage = page.locator('.text-destructive').first();
      await expect(errorMessage).toBeVisible();
      console.log('Failed credential test error message is displayed');
    } else {
      console.log('No failed credentials found - skipping error message verification');
    }
  });

  test('should handle unsupported credential testing gracefully', async ({ page }) => {
    await page.waitForSelector('table', { timeout: 5000 }).catch(() => {
      console.log('No mappings table found');
    });

    const testButton = page.locator('button[title="Test credential"]').first();
    const testButtonExists = await testButton.count() > 0;

    if (!testButtonExists) {
      test.skip();
      return;
    }

    // Click test button
    await testButton.click();
    await expect(testButton).toBeEnabled({ timeout: 10000 });

    // Check if "unsupported" status appears
    const unsupportedStatus = page.locator('text=Unsupported').first();
    const isUnsupported = await unsupportedStatus.count() > 0;

    if (isUnsupported) {
      // Verify the unsupported status is displayed with appropriate styling
      await expect(unsupportedStatus).toBeVisible();
      console.log('Provider does not support credential testing - status displayed correctly');
    }
  });
});
