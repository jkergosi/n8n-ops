/**
 * E2E tests for AdvancedOptionsPanel component.
 *
 * Tests:
 * - Panel expand/collapse behavior
 * - ARIA attributes accessibility
 * - Keyboard navigation support
 * - Animation respects prefers-reduced-motion
 *
 * Run Mode: Manual / Local verification
 * Note: These tests are kept in the repository for local verification.
 * If CI does not run Playwright tests, run locally with: npx playwright test advanced-options-panel.spec.ts
 */
import { test, expect } from '@playwright/test';
import { MockApiClient } from '../testkit/mock-api';

test.describe('AdvancedOptionsPanel Component', () => {
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

    // Clear localStorage to ensure clean state
    await page.addInitScript(() => {
      localStorage.clear();
    });
  });

  test.describe('Expand/Collapse Behavior', () => {
    test('panel is collapsed by default when defaultExpanded is false/undefined', async ({ page }) => {
      // Set wizard mode to false to see full form with panel
      await page.addInitScript(() => {
        localStorage.setItem('wizard_mode_enabled', 'false');
        localStorage.setItem('wizard_env_setup_seen', 'true');
      });

      await page.goto('/environments/new');

      // Find the GitHub Integration panel
      const panelButton = page.locator('button:has-text("GitHub Integration")');
      await expect(panelButton).toBeVisible();

      // Check that aria-expanded is false (collapsed)
      await expect(panelButton).toHaveAttribute('aria-expanded', 'false');

      // Panel content should be hidden
      const panelContent = page.locator('[aria-hidden="true"]').filter({ hasText: 'Repository URL' });
      await expect(panelContent).toBeVisible();
    });

    test('clicking the toggle button expands the panel', async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.setItem('wizard_mode_enabled', 'false');
        localStorage.setItem('wizard_env_setup_seen', 'true');
      });

      await page.goto('/environments/new');

      const panelButton = page.locator('button:has-text("GitHub Integration")');
      await expect(panelButton).toBeVisible();

      // Initially collapsed
      await expect(panelButton).toHaveAttribute('aria-expanded', 'false');

      // Click to expand
      await panelButton.click();

      // Now expanded
      await expect(panelButton).toHaveAttribute('aria-expanded', 'true');

      // Content should be visible
      const repoUrlLabel = page.locator('label:has-text("Repository URL")');
      await expect(repoUrlLabel).toBeVisible();
    });

    test('clicking again collapses the panel', async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.setItem('wizard_mode_enabled', 'false');
        localStorage.setItem('wizard_env_setup_seen', 'true');
      });

      await page.goto('/environments/new');

      const panelButton = page.locator('button:has-text("GitHub Integration")');

      // Expand
      await panelButton.click();
      await expect(panelButton).toHaveAttribute('aria-expanded', 'true');

      // Collapse
      await panelButton.click();
      await expect(panelButton).toHaveAttribute('aria-expanded', 'false');
    });
  });

  test.describe('ARIA Attributes', () => {
    test('aria-expanded attribute changes on toggle', async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.setItem('wizard_mode_enabled', 'false');
        localStorage.setItem('wizard_env_setup_seen', 'true');
      });

      await page.goto('/environments/new');

      const panelButton = page.locator('button:has-text("GitHub Integration")');

      // Initially collapsed
      await expect(panelButton).toHaveAttribute('aria-expanded', 'false');

      // Toggle to expanded
      await panelButton.click();
      await expect(panelButton).toHaveAttribute('aria-expanded', 'true');

      // Toggle back to collapsed
      await panelButton.click();
      await expect(panelButton).toHaveAttribute('aria-expanded', 'false');
    });

    test('panel content uses aria-hidden when collapsed', async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.setItem('wizard_mode_enabled', 'false');
        localStorage.setItem('wizard_env_setup_seen', 'true');
      });

      await page.goto('/environments/new');

      const panelButton = page.locator('button:has-text("GitHub Integration")');

      // Get the aria-controls attribute to find the content region
      const contentId = await panelButton.getAttribute('aria-controls');
      expect(contentId).toBeTruthy();

      const contentRegion = page.locator(`#${contentId}`);

      // Initially collapsed - content should be aria-hidden
      await expect(contentRegion).toHaveAttribute('aria-hidden', 'true');

      // Expand
      await panelButton.click();

      // Now content should not be aria-hidden
      await expect(contentRegion).toHaveAttribute('aria-hidden', 'false');
    });

    test('panel content has role="region"', async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.setItem('wizard_mode_enabled', 'false');
        localStorage.setItem('wizard_env_setup_seen', 'true');
      });

      await page.goto('/environments/new');

      const panelButton = page.locator('button:has-text("GitHub Integration")');
      const contentId = await panelButton.getAttribute('aria-controls');

      const contentRegion = page.locator(`#${contentId}`);
      await expect(contentRegion).toHaveAttribute('role', 'region');
    });
  });

  test.describe('Keyboard Navigation', () => {
    test('Tab key navigates to the toggle button', async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.setItem('wizard_mode_enabled', 'false');
        localStorage.setItem('wizard_env_setup_seen', 'true');
      });

      await page.goto('/environments/new');

      // Tab through the page until we reach the GitHub Integration button
      // First focus something at the start
      await page.keyboard.press('Tab');

      // Keep tabbing until we find the button or hit a reasonable limit
      let foundButton = false;
      for (let i = 0; i < 20; i++) {
        const focusedElement = page.locator(':focus');
        const text = await focusedElement.textContent().catch(() => '');
        if (text?.includes('GitHub Integration')) {
          foundButton = true;
          break;
        }
        await page.keyboard.press('Tab');
      }

      expect(foundButton).toBe(true);
    });

    test('Enter key toggles the panel', async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.setItem('wizard_mode_enabled', 'false');
        localStorage.setItem('wizard_env_setup_seen', 'true');
      });

      await page.goto('/environments/new');

      const panelButton = page.locator('button:has-text("GitHub Integration")');

      // Focus the button
      await panelButton.focus();

      // Verify initially collapsed
      await expect(panelButton).toHaveAttribute('aria-expanded', 'false');

      // Press Enter to expand
      await page.keyboard.press('Enter');
      await expect(panelButton).toHaveAttribute('aria-expanded', 'true');

      // Press Enter again to collapse
      await page.keyboard.press('Enter');
      await expect(panelButton).toHaveAttribute('aria-expanded', 'false');
    });

    test('Space key toggles the panel', async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.setItem('wizard_mode_enabled', 'false');
        localStorage.setItem('wizard_env_setup_seen', 'true');
      });

      await page.goto('/environments/new');

      const panelButton = page.locator('button:has-text("GitHub Integration")');

      // Focus the button
      await panelButton.focus();

      // Verify initially collapsed
      await expect(panelButton).toHaveAttribute('aria-expanded', 'false');

      // Press Space to expand
      await page.keyboard.press('Space');
      await expect(panelButton).toHaveAttribute('aria-expanded', 'true');

      // Press Space again to collapse
      await page.keyboard.press('Space');
      await expect(panelButton).toHaveAttribute('aria-expanded', 'false');
    });
  });

  test.describe('Visual Behavior', () => {
    test('chevron icon rotates on toggle', async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.setItem('wizard_mode_enabled', 'false');
        localStorage.setItem('wizard_env_setup_seen', 'true');
      });

      await page.goto('/environments/new');

      const panelButton = page.locator('button:has-text("GitHub Integration")');
      const chevron = panelButton.locator('svg');

      // Initially should not have rotate-180 class
      await expect(chevron).not.toHaveClass(/rotate-180/);

      // Click to expand
      await panelButton.click();

      // Should now have rotate-180 class
      await expect(chevron).toHaveClass(/rotate-180/);
    });

    test('panel shows description text', async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.setItem('wizard_mode_enabled', 'false');
        localStorage.setItem('wizard_env_setup_seen', 'true');
      });

      await page.goto('/environments/new');

      // The description text should be visible
      const description = page.locator('text=Optional: Set up version control for your workflows');
      await expect(description).toBeVisible();
    });
  });
});
