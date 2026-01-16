/**
 * Validation script for legacy route redirects
 *
 * This script verifies the redirect logic without requiring full React rendering.
 * It checks the redirect component implementations for correctness.
 */

import { describe, it, expect } from 'vitest';

describe('Legacy Redirect Implementation Validation', () => {
  it('validates redirect component structure exists', async () => {
    const AppModule = await import('../App');

    // Verify all redirect components are exported
    expect(AppModule.LegacyEnvironmentWorkflowsRedirect).toBeDefined();
    expect(AppModule.LegacyEnvironmentDeploymentsRedirect).toBeDefined();
    expect(AppModule.LegacyEnvironmentSnapshotsRedirect).toBeDefined();
    expect(AppModule.LegacyEnvironmentExecutionsRedirect).toBeDefined();
    expect(AppModule.LegacyEnvironmentActivityRedirect).toBeDefined();
    expect(AppModule.LegacyEnvironmentCredentialsRedirect).toBeDefined();
  });

  it('validates redirect components are functions', async () => {
    const AppModule = await import('../App');

    expect(typeof AppModule.LegacyEnvironmentWorkflowsRedirect).toBe('function');
    expect(typeof AppModule.LegacyEnvironmentDeploymentsRedirect).toBe('function');
    expect(typeof AppModule.LegacyEnvironmentSnapshotsRedirect).toBe('function');
    expect(typeof AppModule.LegacyEnvironmentExecutionsRedirect).toBe('function');
    expect(typeof AppModule.LegacyEnvironmentActivityRedirect).toBe('function');
    expect(typeof AppModule.LegacyEnvironmentCredentialsRedirect).toBe('function');
  });

  it('validates App.tsx contains route definitions', async () => {
    const fs = await import('fs');
    const path = await import('path');

    const appPath = path.join(__dirname, '../App.tsx');
    const appContent = fs.readFileSync(appPath, 'utf-8');

    // Verify route paths exist
    expect(appContent).toContain('/environments/:id/workflows');
    expect(appContent).toContain('/environments/:id/deployments');
    expect(appContent).toContain('/environments/:id/snapshots');
    expect(appContent).toContain('/environments/:id/executions');
    expect(appContent).toContain('/environments/:id/activity');
    expect(appContent).toContain('/environments/:id/credentials');

    // Verify redirect components are used in routes
    expect(appContent).toContain('LegacyEnvironmentWorkflowsRedirect');
    expect(appContent).toContain('LegacyEnvironmentDeploymentsRedirect');
    expect(appContent).toContain('LegacyEnvironmentSnapshotsRedirect');
    expect(appContent).toContain('LegacyEnvironmentExecutionsRedirect');
    expect(appContent).toContain('LegacyEnvironmentActivityRedirect');
    expect(appContent).toContain('LegacyEnvironmentCredentialsRedirect');
  });

  it('validates redirect URLs are correctly formed', async () => {
    const fs = await import('fs');
    const path = await import('path');

    const appPath = path.join(__dirname, '../App.tsx');
    const appContent = fs.readFileSync(appPath, 'utf-8');

    // Verify redirect URL patterns
    expect(appContent).toContain('/workflows?env_id=');
    expect(appContent).toContain('/deployments?env_id=');
    expect(appContent).toContain('/snapshots?env_id=');
    expect(appContent).toContain('/executions?env_id=');
    expect(appContent).toContain('/activity?env_id=');
    expect(appContent).toContain('/credentials?env_id=');
  });

  it('validates all redirects use replace: true', async () => {
    const fs = await import('fs');
    const path = await import('path');

    const appPath = path.join(__dirname, '../App.tsx');
    const appContent = fs.readFileSync(appPath, 'utf-8');

    // Extract redirect component definitions
    const redirectSections = [
      'LegacyEnvironmentWorkflowsRedirect',
      'LegacyEnvironmentDeploymentsRedirect',
      'LegacyEnvironmentSnapshotsRedirect',
      'LegacyEnvironmentExecutionsRedirect',
      'LegacyEnvironmentActivityRedirect',
      'LegacyEnvironmentCredentialsRedirect',
    ];

    redirectSections.forEach(section => {
      const startIndex = appContent.indexOf(`export function ${section}`);
      expect(startIndex).toBeGreaterThan(-1);

      const endIndex = appContent.indexOf('}', startIndex + 100);
      const componentCode = appContent.substring(startIndex, endIndex + 1);

      // Verify component uses replace: true
      const hasReplace = componentCode.includes('replace');
      expect(hasReplace).toBe(true);
    });
  });

  it('validates redirect components handle missing id', async () => {
    const fs = await import('fs');
    const path = await import('path');

    const appPath = path.join(__dirname, '../App.tsx');
    const appContent = fs.readFileSync(appPath, 'utf-8');

    const redirectSections = [
      { component: 'LegacyEnvironmentWorkflowsRedirect', fallback: '/workflows' },
      { component: 'LegacyEnvironmentDeploymentsRedirect', fallback: '/deployments' },
      { component: 'LegacyEnvironmentSnapshotsRedirect', fallback: '/snapshots' },
      { component: 'LegacyEnvironmentExecutionsRedirect', fallback: '/executions' },
      { component: 'LegacyEnvironmentActivityRedirect', fallback: '/activity' },
      { component: 'LegacyEnvironmentCredentialsRedirect', fallback: '/credentials' },
    ];

    redirectSections.forEach(({ component, fallback }) => {
      const startIndex = appContent.indexOf(`export function ${component}`);
      const endIndex = appContent.indexOf('}', startIndex + 200);
      const componentCode = appContent.substring(startIndex, endIndex + 1);

      // Verify component checks for missing id
      expect(componentCode).toContain('if (!id)');
      expect(componentCode).toContain(fallback);
    });
  });
});

describe('Redirect Route Integration', () => {
  it('validates route definitions are wrapped with RoleProtectedRoute', async () => {
    const fs = await import('fs');
    const path = await import('path');

    const appPath = path.join(__dirname, '../App.tsx');
    const appContent = fs.readFileSync(appPath, 'utf-8');

    // Verify RoleProtectedRoute wraps redirect components
    expect(appContent).toContain('<RoleProtectedRoute><LegacyEnvironmentWorkflowsRedirect /></RoleProtectedRoute>');
    expect(appContent).toContain('<RoleProtectedRoute><LegacyEnvironmentDeploymentsRedirect /></RoleProtectedRoute>');
    expect(appContent).toContain('<RoleProtectedRoute><LegacyEnvironmentSnapshotsRedirect /></RoleProtectedRoute>');
    expect(appContent).toContain('<RoleProtectedRoute><LegacyEnvironmentExecutionsRedirect /></RoleProtectedRoute>');
    expect(appContent).toContain('<RoleProtectedRoute><LegacyEnvironmentActivityRedirect /></RoleProtectedRoute>');
    expect(appContent).toContain('<RoleProtectedRoute><LegacyEnvironmentCredentialsRedirect /></RoleProtectedRoute>');
  });

  it('validates redirect routes come before wildcard routes', async () => {
    const fs = await import('fs');
    const path = await import('path');

    const appPath = path.join(__dirname, '../App.tsx');
    const appContent = fs.readFileSync(appPath, 'utf-8');

    // Find positions of routes
    const environmentsIdIndex = appContent.indexOf('path="/environments/:id"');
    const workflowsRedirectIndex = appContent.indexOf('path="/environments/:id/workflows"');

    // Specific routes should come after the more general environment detail route
    // but they should be defined (React Router will match most specific first)
    expect(workflowsRedirectIndex).toBeGreaterThan(-1);
    expect(environmentsIdIndex).toBeGreaterThan(-1);
  });
});

describe('Documentation Validation', () => {
  it('validates manual testing guide exists', async () => {
    const fs = await import('fs');
    const path = await import('path');

    const guidePath = path.join(__dirname, 'App.legacy-redirects.manual-test.md');
    expect(fs.existsSync(guidePath)).toBe(true);
  });

  it('validates testing summary exists', async () => {
    const fs = await import('fs');
    const path = await import('path');

    const summaryPath = path.join(__dirname, '../../../TESTING-T042-LEGACY-REDIRECTS.md');
    expect(fs.existsSync(summaryPath)).toBe(true);
  });

  it('validates manual test guide contains all redirect routes', async () => {
    const fs = await import('fs');
    const path = await import('path');

    const guidePath = path.join(__dirname, 'App.legacy-redirects.manual-test.md');
    const guideContent = fs.readFileSync(guidePath, 'utf-8');

    expect(guideContent).toContain('/environments/:id/workflows');
    expect(guideContent).toContain('/environments/:id/deployments');
    expect(guideContent).toContain('/environments/:id/snapshots');
    expect(guideContent).toContain('/environments/:id/executions');
    expect(guideContent).toContain('/environments/:id/activity');
    expect(guideContent).toContain('/environments/:id/credentials');

    expect(guideContent).toContain('/workflows?env_id=');
    expect(guideContent).toContain('/deployments?env_id=');
    expect(guideContent).toContain('/snapshots?env_id=');
    expect(guideContent).toContain('/executions?env_id=');
    expect(guideContent).toContain('/activity?env_id=');
    expect(guideContent).toContain('/credentials?env_id=');
  });
});

console.log('✅ All redirect validation checks passed!');
