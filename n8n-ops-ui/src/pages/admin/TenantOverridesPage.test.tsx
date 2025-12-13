import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { TenantOverridesPage } from './TenantOverridesPage';

const API_BASE = 'http://localhost:4000/api/v1';

const mockOverrides = [
  {
    id: 'override-1',
    tenant_id: 'tenant-1',
    tenant_name: 'Acme Corp',
    feature_key: 'max_workflows',
    override_value: 200,
    reason: 'Enterprise upgrade pending',
    created_at: '2024-01-01T00:00:00Z',
    created_by: 'admin@test.com',
  },
  {
    id: 'override-2',
    tenant_id: 'tenant-2',
    tenant_name: 'Test Org',
    feature_key: 'max_environments',
    override_value: 10,
    reason: 'Trial extension',
    created_at: '2024-01-15T00:00:00Z',
    created_by: 'admin@test.com',
  },
];

describe('TenantOverridesPage', () => {
  beforeEach(() => {
    server.resetHandlers();

    server.use(
      http.get(`${API_BASE}/admin/entitlements/overrides`, () => {
        return HttpResponse.json({
          overrides: mockOverrides,
          total: 2,
        });
      }),
      http.get(`${API_BASE}/auth/status`, () => {
        return HttpResponse.json({
          authenticated: true,
          onboarding_required: false,
          has_environment: true,
          user: { id: 'user-1', email: 'admin@test.com', name: 'Admin User', role: 'admin' },
          tenant: { id: 'tenant-1', name: 'Test Org', subscription_tier: 'pro' },
          entitlements: { plan_name: 'pro', features: {} },
        });
      })
    );
  });

  describe('Page Header', () => {
    it('should display the page title', async () => {
      render(<TenantOverridesPage />);

      expect(screen.getByRole('heading', { level: 1, name: /tenant overrides/i })).toBeInTheDocument();
    });

    it('should display the page description', async () => {
      render(<TenantOverridesPage />);

      expect(screen.getByText(/manage per-tenant feature limit overrides/i)).toBeInTheDocument();
    });

    it('should display Feature Matrix link', async () => {
      render(<TenantOverridesPage />);

      expect(screen.getByRole('link', { name: /feature matrix/i })).toBeInTheDocument();
    });

    it('should display Add Override button', async () => {
      render(<TenantOverridesPage />);

      expect(screen.getByRole('button', { name: /add override/i })).toBeInTheDocument();
    });
  });

  describe('Overrides Table', () => {
    it('should display table headers', async () => {
      render(<TenantOverridesPage />);

      await waitFor(() => {
        expect(screen.getByText('Tenant')).toBeInTheDocument();
      });
      expect(screen.getByText('Feature')).toBeInTheDocument();
      expect(screen.getByText('Override Value')).toBeInTheDocument();
      expect(screen.getByText('Reason')).toBeInTheDocument();
    });

    it('should display tenant names', async () => {
      render(<TenantOverridesPage />);

      await waitFor(() => {
        expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      });
      expect(screen.getByText('Test Org')).toBeInTheDocument();
    });

    it('should display feature keys', async () => {
      render(<TenantOverridesPage />);

      await waitFor(() => {
        expect(screen.getByText('max_workflows')).toBeInTheDocument();
      });
      expect(screen.getByText('max_environments')).toBeInTheDocument();
    });

    it('should display override reasons', async () => {
      render(<TenantOverridesPage />);

      await waitFor(() => {
        expect(screen.getByText('Enterprise upgrade pending')).toBeInTheDocument();
      });
      expect(screen.getByText('Trial extension')).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('should show empty message when no overrides exist', async () => {
      server.use(
        http.get(`${API_BASE}/admin/entitlements/overrides`, () => {
          return HttpResponse.json({ overrides: [], total: 0 });
        })
      );

      render(<TenantOverridesPage />);

      await waitFor(() => {
        expect(screen.getByText(/no overrides found/i)).toBeInTheDocument();
      });
    });
  });

  describe('Loading State', () => {
    it('should show loading state initially', async () => {
      server.use(
        http.get(`${API_BASE}/admin/entitlements/overrides`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json({ overrides: mockOverrides, total: 2 });
        })
      );

      render(<TenantOverridesPage />);

      expect(screen.getByText(/loading overrides/i)).toBeInTheDocument();
    });
  });
});
