import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { UsagePage } from './UsagePage';

const API_BASE = 'http://localhost:4000/api/v1';

describe('UsagePage', () => {
  beforeEach(() => {
    server.resetHandlers();

    server.use(
      http.get(`${API_BASE}/admin/usage`, () => {
        return HttpResponse.json({
          stats: {
            total_tenants: 100,
            total_workflows: 500,
            total_environments: 150,
            total_users: 300,
            total_executions_today: 5000,
            total_executions_month: 150000,
            tenants_at_limit: 5,
            tenants_over_limit: 2,
            tenants_near_limit: 10,
          },
          usage_by_plan: { free: 50, pro: 30, agency: 15, enterprise: 5 },
          recent_growth: {
            tenants_7d: 5,
            tenants_30d: 15,
            workflows_7d: 25,
            workflows_30d: 75,
            executions_7d: 35000,
            executions_30d: 150000,
          },
        });
      }),
      http.get(`${API_BASE}/admin/usage/top-tenants`, () => {
        return HttpResponse.json({
          tenants: [
            { rank: 1, tenant_id: 'tenant-1', tenant_name: 'Acme Corp', plan: 'enterprise', value: 100, limit: 500, percentage: 20 },
            { rank: 2, tenant_id: 'tenant-2', tenant_name: 'Test Org', plan: 'pro', value: 50, limit: 100, percentage: 50 },
          ],
        });
      }),
      http.get(`${API_BASE}/admin/usage/at-limit`, () => {
        return HttpResponse.json({
          tenants: [],
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
      render(<UsagePage />);

      expect(screen.getByRole('heading', { level: 1, name: /usage & limits/i })).toBeInTheDocument();
    });

    it('should display the page description', async () => {
      render(<UsagePage />);

      expect(screen.getByText(/monitor platform usage and identify upsell opportunities/i)).toBeInTheDocument();
    });

    it('should display Refresh button', async () => {
      render(<UsagePage />);

      expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
    });

    it('should display Export Summary button', async () => {
      render(<UsagePage />);

      expect(screen.getByRole('button', { name: /export summary/i })).toBeInTheDocument();
    });
  });

  describe('Global Stats', () => {
    it('should display Total Tenants', async () => {
      render(<UsagePage />);

      await waitFor(() => {
        expect(screen.getByText('Total Tenants')).toBeInTheDocument();
      });
    });

    it('should display Total Workflows', async () => {
      render(<UsagePage />);

      await waitFor(() => {
        expect(screen.getByText('Total Workflows')).toBeInTheDocument();
      });
    });

    it('should display Executions Today', async () => {
      render(<UsagePage />);

      await waitFor(() => {
        expect(screen.getByText('Executions Today')).toBeInTheDocument();
      });
    });

    it('should display Total Users', async () => {
      render(<UsagePage />);

      await waitFor(() => {
        expect(screen.getByText('Total Users')).toBeInTheDocument();
      });
    });
  });

  describe('Usage by Plan', () => {
    it('should display Usage by Plan section', async () => {
      render(<UsagePage />);

      await waitFor(() => {
        expect(screen.getByText('Usage by Plan')).toBeInTheDocument();
      });
    });

    it('should display plan distribution description', async () => {
      render(<UsagePage />);

      await waitFor(() => {
        expect(screen.getByText(/distribution of tenants across subscription plans/i)).toBeInTheDocument();
      });
    });
  });

  describe('Top Tenants', () => {
    it('should display Top Tenants section', async () => {
      render(<UsagePage />);

      await waitFor(() => {
        expect(screen.getByText('Top Tenants')).toBeInTheDocument();
      });
    });

    it('should display Ranked by usage metrics description', async () => {
      render(<UsagePage />);

      await waitFor(() => {
        expect(screen.getByText('Ranked by usage metrics')).toBeInTheDocument();
      });
    });
  });

  describe('Tenants Near Limits', () => {
    it('should display Tenants Near Limits section', async () => {
      render(<UsagePage />);

      await waitFor(() => {
        expect(screen.getByText('Tenants Near Limits')).toBeInTheDocument();
      });
    });
  });

  describe('Recent Growth', () => {
    it('should display Recent Growth section', async () => {
      render(<UsagePage />);

      await waitFor(() => {
        expect(screen.getByText('Recent Growth')).toBeInTheDocument();
      });
    });
  });

  describe('Loading State', () => {
    it('should show loading state initially', async () => {
      server.use(
        http.get(`${API_BASE}/admin/usage`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json({ stats: {}, usage_by_plan: {}, recent_growth: {} });
        })
      );

      render(<UsagePage />);

      expect(screen.getByText(/loading usage data/i)).toBeInTheDocument();
    });
  });
});
