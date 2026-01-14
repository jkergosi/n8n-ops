/**
 * E2E tests for Environment Setup Wizard Mode.
 *
 * Tests:
 * - First-time user flow (wizard mode by default)
 * - Returning user flow (full form by default)
 * - Mode toggle functionality
 * - localStorage persistence
 * - Wizard step navigation
 *
 * Run Mode: Manual / Local verification
 * Note: These tests are kept in the repository for local verification.
 * If CI does not run Playwright tests, run locally with: npx playwright test environment-setup-wizard.spec.ts
 */
import { test, expect } from '@playwright/test';
import { MockApiClient } from '../testkit/mock-api';

test.describe('Environment Setup Wizard Mode', () => {
  let mockApi: MockApiClient;

  test.beforeEach(async ({ page }) => {
    mockApi = new MockApiClient(page);
    await mockApi.mockAuth('admin');
    await mockApi.mockEnvironments();

    // Mock environment types
    await page.route('**/api/v1/environment-types', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: '1', key: 'dev', label: 'Development' },
          { id: '2', key: 'staging', label: 'Staging' },
          { id: '3', key: 'prod', label: 'Production' },
        ]),
      });
    });

    // Mock environment creation
    await page.route('**/api/v1/environments', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'env-new',
            name: 'Test Environment',
            type: 'dev',
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([]),
        });
      }
    });

    // Mock sync endpoint
    await page.route('**/api/v1/environments/*/sync', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          results: { workflows: { synced: 5 } },
        }),
      });
    });
  });

  test.describe('First-Time User Flow', () => {
    test('first visit (no localStorage) shows wizard mode', async ({ page }) => {
      // Clear localStorage to simulate first-time user
      await page.addInitScript(() => {
        localStorage.clear();
      });

      await page.goto('/environments/new');

      // Should see wizard step indicator
      const stepIndicator = page.locator('.flex.items-center.justify-center.gap-2.mb-6');
      await expect(stepIndicator).toBeVisible();

      // Should see step 1 highlighted
      const step1 = page.locator('text=1').first();
      await expect(step1).toBeVisible();

      // Should see "Next: GitHub Setup" button (wizard mode specific)
      const nextButton = page.locator('button:has-text("Next: GitHub Setup")');
      await expect(nextButton).toBeVisible();

      // Should NOT see the AdvancedOptionsPanel (that's for full form mode)
      const advancedPanel = page.locator('button:has-text("GitHub Integration")').filter({ hasText: 'Optional' });
      await expect(advancedPanel).not.toBeVisible();
    });

    test('wizard mode shows step-by-step navigation', async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.clear();
      });

      await page.goto('/environments/new');

      // Fill in required fields for step 1
      await page.fill('input#name', 'Test Environment');
      await page.fill('input#n8nUrl', 'https://n8n.example.com');
      await page.fill('input#n8nApiKey', 'test-api-key');

      // Click Next button
      const nextButton = page.locator('button:has-text("Next: GitHub Setup")');
      await nextButton.click();

      // Should now be on step 2 (GitHub)
      const githubHeader = page.locator('h3:has-text("GitHub Integration")');
      await expect(githubHeader).toBeVisible();

      // Should see Back button
      const backButton = page.locator('button:has-text("Back")');
      await expect(backButton).toBeVisible();

      // Should see Create Environment button
      const createButton = page.locator('button:has-text("Create Environment")');
      await expect(createButton).toBeVisible();
    });

    test('wizard step 1 validates required fields before proceeding', async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.clear();
      });

      await page.goto('/environments/new');

      // Try to click Next without filling fields
      const nextButton = page.locator('button:has-text("Next: GitHub Setup")');

      // Button should be disabled when required fields are empty
      await expect(nextButton).toBeDisabled();

      // Fill only name
      await page.fill('input#name', 'Test Environment');
      await expect(nextButton).toBeDisabled();

      // Fill URL
      await page.fill('input#n8nUrl', 'https://n8n.example.com');
      await expect(nextButton).toBeDisabled();

      // Fill API key - now button should be enabled
      await page.fill('input#n8nApiKey', 'test-api-key');
      await expect(nextButton).toBeEnabled();
    });
  });

  test.describe('Returning User Flow', () => {
    test('after completing setup, wizard_env_setup_seen is set', async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.clear();
      });

      await page.goto('/environments/new');

      // Fill all required fields
      await page.fill('input#name', 'Test Environment');
      await page.fill('input#n8nUrl', 'https://n8n.example.com');
      await page.fill('input#n8nApiKey', 'test-api-key');

      // Go to step 2
      await page.locator('button:has-text("Next: GitHub Setup")').click();

      // Submit the form
      await page.locator('button:has-text("Create Environment")').click();

      // Check localStorage was set
      const seenValue = await page.evaluate(() => localStorage.getItem('wizard_env_setup_seen'));
      expect(seenValue).toBe('true');
    });

    test('subsequent visits show full form by default', async ({ page }) => {
      // Simulate returning user
      await page.addInitScript(() => {
        localStorage.setItem('wizard_env_setup_seen', 'true');
      });

      await page.goto('/environments/new');

      // Should NOT see wizard step indicator
      const stepIndicator = page.locator('.flex.items-center.justify-center.gap-2.mb-6');
      await expect(stepIndicator).not.toBeVisible();

      // Should see AdvancedOptionsPanel for GitHub
      const advancedPanel = page.locator('button:has-text("GitHub Integration")');
      await expect(advancedPanel).toBeVisible();

      // Should NOT see "Next: GitHub Setup" button
      const nextButton = page.locator('button:has-text("Next: GitHub Setup")');
      await expect(nextButton).not.toBeVisible();

      // Should see direct "Create Environment" button
      const createButton = page.locator('button:has-text("Create Environment")');
      await expect(createButton).toBeVisible();
    });
  });

  test.describe('Mode Toggle Functionality', () => {
    test('toggle link switches between wizard and full form modes', async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.clear();
      });

      await page.goto('/environments/new');

      // Initially in wizard mode - should see toggle to full form
      const toggleToFull = page.locator('button:has-text("Switch to full form")');
      await expect(toggleToFull).toBeVisible();

      // Click to switch to full form
      await toggleToFull.click();

      // Should now see toggle to guided setup
      const toggleToWizard = page.locator('button:has-text("Switch to guided setup")');
      await expect(toggleToWizard).toBeVisible();

      // Should see AdvancedOptionsPanel (full form mode)
      const advancedPanel = page.locator('button:has-text("GitHub Integration")');
      await expect(advancedPanel).toBeVisible();

      // Click to switch back to wizard
      await toggleToWizard.click();

      // Should be back in wizard mode
      await expect(toggleToFull).toBeVisible();
      const nextButton = page.locator('button:has-text("Next: GitHub Setup")');
      await expect(nextButton).toBeVisible();
    });

    test('toggle link changes mode and updates localStorage', async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.clear();
      });

      await page.goto('/environments/new');

      // Initially wizard mode is enabled (first-time user)
      let modeEnabled = await page.evaluate(() => localStorage.getItem('wizard_mode_enabled'));
      expect(modeEnabled).toBeNull(); // Not explicitly set yet

      // Toggle to full form
      const toggleToFull = page.locator('button:has-text("Switch to full form")');
      await toggleToFull.click();

      // localStorage should now have explicit preference
      modeEnabled = await page.evaluate(() => localStorage.getItem('wizard_mode_enabled'));
      expect(modeEnabled).toBe('false');

      // Toggle back to wizard
      const toggleToWizard = page.locator('button:has-text("Switch to guided setup")');
      await toggleToWizard.click();

      modeEnabled = await page.evaluate(() => localStorage.getItem('wizard_mode_enabled'));
      expect(modeEnabled).toBe('true');
    });

    test('mode persists across page refreshes', async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.clear();
      });

      await page.goto('/environments/new');

      // Toggle to full form
      await page.locator('button:has-text("Switch to full form")').click();

      // Verify we're in full form mode
      await expect(page.locator('button:has-text("GitHub Integration")')).toBeVisible();

      // Refresh the page
      await page.reload();

      // Should still be in full form mode
      await expect(page.locator('button:has-text("GitHub Integration")')).toBeVisible();
      await expect(page.locator('button:has-text("Switch to guided setup")')).toBeVisible();
    });
  });

  test.describe('Wizard Step Navigation', () => {
    test('Back button on step 2 returns to step 1', async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.clear();
      });

      await page.goto('/environments/new');

      // Fill required fields and go to step 2
      await page.fill('input#name', 'Test Environment');
      await page.fill('input#n8nUrl', 'https://n8n.example.com');
      await page.fill('input#n8nApiKey', 'test-api-key');
      await page.locator('button:has-text("Next: GitHub Setup")').click();

      // Verify on step 2
      await expect(page.locator('h3:has-text("GitHub Integration")')).toBeVisible();

      // Click Back
      await page.locator('button:has-text("Back")').click();

      // Should be back on step 1
      await expect(page.locator('button:has-text("Next: GitHub Setup")')).toBeVisible();

      // Form data should be preserved
      await expect(page.locator('input#name')).toHaveValue('Test Environment');
      await expect(page.locator('input#n8nUrl')).toHaveValue('https://n8n.example.com');
    });

    test('switching to wizard mode resets to step 1', async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.clear();
      });

      await page.goto('/environments/new');

      // Fill required fields and go to step 2
      await page.fill('input#name', 'Test Environment');
      await page.fill('input#n8nUrl', 'https://n8n.example.com');
      await page.fill('input#n8nApiKey', 'test-api-key');
      await page.locator('button:has-text("Next: GitHub Setup")').click();

      // Verify on step 2
      await expect(page.locator('h3:has-text("GitHub Integration")')).toBeVisible();

      // Switch to full form mode
      await page.locator('button:has-text("Switch to full form")').click();

      // Switch back to wizard mode
      await page.locator('button:has-text("Switch to guided setup")').click();

      // Should be back on step 1
      await expect(page.locator('button:has-text("Next: GitHub Setup")')).toBeVisible();
    });
  });

  test.describe('Edit Mode Behavior', () => {
    test('edit mode always shows full form (no wizard)', async ({ page }) => {
      // Mock getting an existing environment
      await page.route('**/api/v1/environments/env-existing', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'env-existing',
            name: 'Existing Environment',
            type: 'dev',
            baseUrl: 'https://n8n.example.com',
            apiKey: 'existing-api-key',
            gitRepoUrl: '',
            gitBranch: 'main',
            gitPat: '',
          }),
        });
      });

      // Clear localStorage - would normally trigger wizard mode
      await page.addInitScript(() => {
        localStorage.clear();
      });

      await page.goto('/environments/env-existing/edit');

      // Should NOT see wizard elements (wizard is disabled in edit mode)
      const nextButton = page.locator('button:has-text("Next: GitHub Setup")');
      await expect(nextButton).not.toBeVisible();

      // Should see full form with AdvancedOptionsPanel
      const advancedPanel = page.locator('button:has-text("GitHub Integration")');
      await expect(advancedPanel).toBeVisible();

      // Should see Save Changes button
      const saveButton = page.locator('button:has-text("Save Changes")');
      await expect(saveButton).toBeVisible();
    });
  });

  test.describe('Accessibility', () => {
    test('wizard mode toggle is keyboard accessible', async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.clear();
      });

      await page.goto('/environments/new');

      // Find the toggle link and focus it
      const toggleLink = page.locator('button:has-text("Switch to full form")');
      await toggleLink.focus();

      // Press Enter to activate
      await page.keyboard.press('Enter');

      // Should have switched modes
      await expect(page.locator('button:has-text("Switch to guided setup")')).toBeVisible();
    });

    test('wizard step buttons are focusable', async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.clear();
      });

      await page.goto('/environments/new');

      // Fill required fields
      await page.fill('input#name', 'Test Environment');
      await page.fill('input#n8nUrl', 'https://n8n.example.com');
      await page.fill('input#n8nApiKey', 'test-api-key');

      // Next button should be focusable
      const nextButton = page.locator('button:has-text("Next: GitHub Setup")');
      await nextButton.focus();

      // Verify it's focused
      await expect(nextButton).toBeFocused();

      // Press Enter to advance
      await page.keyboard.press('Enter');

      // Should be on step 2
      await expect(page.locator('h3:has-text("GitHub Integration")')).toBeVisible();
    });
  });
});
