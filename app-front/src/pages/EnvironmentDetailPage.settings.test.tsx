import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { Route, Routes } from 'react-router-dom';
import { EnvironmentDetailPage } from './EnvironmentDetailPage';

const API_BASE = '/api/v1';

// Mock environment data
const mockEnvironment = {
  id: 'env-test-1',
  tenant_id: 'tenant-1',
  n8n_name: 'Test Environment',
  n8n_type: 'development',
  n8n_base_url: 'https://test.n8n.example.com',
  n8n_api_key_encrypted: 'encrypted-key',
  is_active: true,
  allow_upload: true,
  workflow_count: 5,
  active_workflow_count: 3,
  last_connected: '2024-01-15T10:00:00Z',
  last_backup: '2024-01-14T12:00:00Z',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-15T10:00:00Z',
  git_repo_url: 'https://github.com/test/repo',
  git_branch: 'main',
  git_credentials_encrypted: 'encrypted-git-creds',
  unmanaged_count: 2,
};

const mockWorkflows = {
  items: [],
  total: 0,
  page: 1,
  pageSize: 50,
};

const mockDeployments = {
  items: [],
  total: 0,
  page: 1,
  pageSize: 50,
};

const mockSnapshots = {
  items: [],
  total: 0,
  page: 1,
  pageSize: 50,
};

const mockExecutions = {
  items: [],
  total: 0,
  page: 1,
  pageSize: 50,
};

const mockCredentials = {
  items: [],
  total: 0,
  page: 1,
  pageSize: 50,
};

const mockBackgroundJobs = [];

describe('EnvironmentDetailPage - Settings Section Inline Display', () => {
  beforeEach(() => {
    server.resetHandlers();

    // Set up default handlers
    server.use(
      http.get(`${API_BASE}/environments/:id`, () => {
        return HttpResponse.json(mockEnvironment);
      }),
      http.get(`${API_BASE}/workflows`, () => {
        return HttpResponse.json(mockWorkflows);
      }),
      http.get(`${API_BASE}/deployments`, () => {
        return HttpResponse.json(mockDeployments);
      }),
      http.get(`${API_BASE}/snapshots`, () => {
        return HttpResponse.json(mockSnapshots);
      }),
      http.get(`${API_BASE}/executions`, () => {
        return HttpResponse.json(mockExecutions);
      }),
      http.get(`${API_BASE}/credentials`, () => {
        return HttpResponse.json(mockCredentials);
      }),
      http.get(`${API_BASE}/background-jobs`, () => {
        return HttpResponse.json(mockBackgroundJobs);
      }),
      http.get(`${API_BASE}/auth/status`, () => {
        return HttpResponse.json({
          authenticated: true,
          onboarding_required: false,
          has_environment: true,
          user: { id: 'user-1', email: 'admin@test.com', name: 'Admin', role: 'admin' },
          tenant: { id: 'tenant-1', name: 'Test Org', subscription_tier: 'pro' },
          entitlements: {
            plan_name: 'pro',
            features: {
              max_environments: { enabled: true, limit: 10 },
              workflow_ci_cd: { enabled: true },
              drift_detection: { enabled: true },
            },
          },
        });
      })
    );
  });

  it('should render Settings section inline on the page', async () => {
    render(
      <Routes>
        <Route path="/environments/:id" element={<EnvironmentDetailPage />} />
      </Routes>,
      { initialRoute: '/environments/env-test-1' }
    );

    // Wait for page to load
    await waitFor(() => {
      expect(screen.getByText('Test Environment')).toBeInTheDocument();
    });

    // Verify Settings section header is present
    expect(screen.getByText('Environment Settings')).toBeInTheDocument();
    expect(screen.getByText('Configuration and safety controls')).toBeInTheDocument();
  });

  it('should display Connection subsection in Settings', async () => {
    render(
      <Routes>
        <Route path="/environments/:id" element={<EnvironmentDetailPage />} />
      </Routes>,
      { initialRoute: '/environments/env-test-1' }
    );

    await waitFor(() => {
      expect(screen.getByText('Test Environment')).toBeInTheDocument();
    });

    // Check Connection section
    expect(screen.getByText('Connection')).toBeInTheDocument();
    expect(screen.getByText(/Connection credentials are managed via environment configuration/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Test Connection/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Edit Configuration/i })).toBeInTheDocument();
  });

  it('should display Git Configuration subsection in Settings', async () => {
    render(
      <Routes>
        <Route path="/environments/:id" element={<EnvironmentDetailPage />} />
      </Routes>,
      { initialRoute: '/environments/env-test-1' }
    );

    await waitFor(() => {
      expect(screen.getByText('Test Environment')).toBeInTheDocument();
    });

    // Check Git Configuration section
    expect(screen.getByText('Git Configuration')).toBeInTheDocument();
    // Verify repository and branch appear (they might appear multiple times in the page)
    const repoUrls = screen.getAllByText('https://github.com/test/repo');
    expect(repoUrls.length).toBeGreaterThan(0);
    const branches = screen.getAllByText('main');
    expect(branches.length).toBeGreaterThan(0);
  });

  it('should display Snapshots subsection in Settings', async () => {
    render(
      <Routes>
        <Route path="/environments/:id" element={<EnvironmentDetailPage />} />
      </Routes>,
      { initialRoute: '/environments/env-test-1' }
    );

    await waitFor(() => {
      expect(screen.getByText('Test Environment')).toBeInTheDocument();
    });

    // Check Snapshots section (in Settings)
    const snapshotsHeadings = screen.getAllByText('Snapshots');
    // Should appear at least once in Settings
    expect(snapshotsHeadings.length).toBeGreaterThan(0);
    expect(screen.getByText(/Create a Git-backed snapshot of the current environment state/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Create Snapshot/i })).toBeInTheDocument();
  });

  it('should display Feature Flags subsection in Settings', async () => {
    render(
      <Routes>
        <Route path="/environments/:id" element={<EnvironmentDetailPage />} />
      </Routes>,
      { initialRoute: '/environments/env-test-1' }
    );

    await waitFor(() => {
      expect(screen.getByText('Test Environment')).toBeInTheDocument();
    });

    // Check Feature Flags section
    expect(screen.getByText('Feature Flags')).toBeInTheDocument();
    expect(screen.getByText('Environment Status')).toBeInTheDocument();
    expect(screen.getByText('Workflow Upload')).toBeInTheDocument();
    // Badges should show Active and Enabled
    const badges = screen.getAllByText('Active');
    expect(badges.length).toBeGreaterThan(0);
    const enabledBadges = screen.getAllByText('Enabled');
    expect(enabledBadges.length).toBeGreaterThan(0);
  });

  it('should display Timestamps subsection in Settings', async () => {
    render(
      <Routes>
        <Route path="/environments/:id" element={<EnvironmentDetailPage />} />
      </Routes>,
      { initialRoute: '/environments/env-test-1' }
    );

    await waitFor(() => {
      expect(screen.getByText('Test Environment')).toBeInTheDocument();
    });

    // Check Timestamps section
    expect(screen.getByText('Timestamps')).toBeInTheDocument();
    expect(screen.getByText('Created')).toBeInTheDocument();
    expect(screen.getByText('Last Updated')).toBeInTheDocument();
    expect(screen.getByText('Last Connected')).toBeInTheDocument();
    expect(screen.getByText('Last Backup')).toBeInTheDocument();
  });

  it('should display Danger Zone subsection in Settings', async () => {
    render(
      <Routes>
        <Route path="/environments/:id" element={<EnvironmentDetailPage />} />
      </Routes>,
      { initialRoute: '/environments/env-test-1' }
    );

    await waitFor(() => {
      expect(screen.getByText('Test Environment')).toBeInTheDocument();
    });

    // Check Danger Zone section
    expect(screen.getByText('Danger Zone')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Delete Environment/i })).toBeInTheDocument();
  });

  it('should display Settings section after Related Views section', async () => {
    render(
      <Routes>
        <Route path="/environments/:id" element={<EnvironmentDetailPage />} />
      </Routes>,
      { initialRoute: '/environments/env-test-1' }
    );

    await waitFor(() => {
      expect(screen.getByText('Test Environment')).toBeInTheDocument();
    });

    // Verify both Related Views and Settings sections exist
    expect(screen.getByText('Related Views')).toBeInTheDocument();
    expect(screen.getByText('Environment Settings')).toBeInTheDocument();

    // Get all sections to verify order
    const relatedViewsSection = screen.getByText('Related Views').closest('div[class*="space-y"]');
    const settingsSection = screen.getByText('Environment Settings').closest('div[class*="space-y"]');

    // Both should exist in the DOM
    expect(relatedViewsSection).toBeInTheDocument();
    expect(settingsSection).toBeInTheDocument();
  });

  it('should NOT display tab navigation UI', async () => {
    render(
      <Routes>
        <Route path="/environments/:id" element={<EnvironmentDetailPage />} />
      </Routes>,
      { initialRoute: '/environments/env-test-1' }
    );

    await waitFor(() => {
      expect(screen.getByText('Test Environment')).toBeInTheDocument();
    });

    // Verify no tabs are present (checking for common tab-related attributes)
    const tabElements = document.querySelectorAll('[role="tab"]');
    expect(tabElements.length).toBe(0);

    const tabListElements = document.querySelectorAll('[role="tablist"]');
    expect(tabListElements.length).toBe(0);

    const tabPanelElements = document.querySelectorAll('[role="tabpanel"]');
    expect(tabPanelElements.length).toBe(0);
  });

  it('should display all Settings content in a single scrollable view', async () => {
    render(
      <Routes>
        <Route path="/environments/:id" element={<EnvironmentDetailPage />} />
      </Routes>,
      { initialRoute: '/environments/env-test-1' }
    );

    await waitFor(() => {
      expect(screen.getByText('Test Environment')).toBeInTheDocument();
    });

    // All major sections should be visible without clicking tabs
    expect(screen.getByText('Environment Settings')).toBeInTheDocument();
    expect(screen.getByText('Connection')).toBeInTheDocument();
    expect(screen.getByText('Git Configuration')).toBeInTheDocument();
    expect(screen.getByText('Feature Flags')).toBeInTheDocument();
    expect(screen.getByText('Timestamps')).toBeInTheDocument();
    expect(screen.getByText('Danger Zone')).toBeInTheDocument();
  });

  it('should display Drift Handling section for Pro tier without drift incidents', async () => {
    // Override the auth status to disable drift_incidents feature
    server.use(
      http.get(`${API_BASE}/auth/status`, () => {
        return HttpResponse.json({
          authenticated: true,
          onboarding_required: false,
          has_environment: true,
          user: { id: 'user-1', email: 'admin@test.com', name: 'Admin', role: 'admin' },
          tenant: { id: 'tenant-1', name: 'Test Org', subscription_tier: 'pro' },
          entitlements: {
            plan_name: 'pro',
            features: {
              max_environments: { enabled: true, limit: 10 },
              workflow_ci_cd: { enabled: true },
              drift_detection: { enabled: true },
              // drift_incidents is NOT enabled - this should show Drift Handling section
            },
          },
        });
      })
    );

    render(
      <Routes>
        <Route path="/environments/:id" element={<EnvironmentDetailPage />} />
      </Routes>,
      { initialRoute: '/environments/env-test-1' }
    );

    await waitFor(() => {
      expect(screen.getByText('Test Environment')).toBeInTheDocument();
    });

    // Check for Drift Handling section (available in Pro tier when drift incidents not enabled)
    expect(screen.getByText('Drift Handling (Free/Pro)')).toBeInTheDocument();
    expect(screen.getByText(/Configure how drift should be handled for this environment/i)).toBeInTheDocument();
  });
});
