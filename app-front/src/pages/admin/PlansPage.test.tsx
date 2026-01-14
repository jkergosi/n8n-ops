import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { PlansPage } from './PlansPage';

const API_BASE = '/api/v1';

describe('PlansPage', () => {
  beforeEach(() => {
    server.resetHandlers();

    server.use(
      http.get(`${API_BASE}/admin/billing/plan-distribution`, () => {
        return HttpResponse.json([
          { plan: 'free', count: 50 },
          { plan: 'pro', count: 30 },
          { plan: 'agency', count: 15 },
          { plan: 'enterprise', count: 5 },
        ]);
      }),
      http.get(`${API_BASE}/admin/billing/metrics`, () => {
        return HttpResponse.json({
          mrr: 15000,
          arr: 180000,
          totalSubscriptions: 100,
          activeSubscriptions: 90,
          trialSubscriptions: 10,
          churnRate: 2.5,
          avgRevenuePerUser: 150,
          mrrGrowth: 5.2,
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
      render(<PlansPage />);

      expect(screen.getByRole('heading', { level: 1, name: /plans management/i })).toBeInTheDocument();
    });

    it('should display the page description', async () => {
      render(<PlansPage />);

      expect(screen.getByText(/configure subscription plans and features/i)).toBeInTheDocument();
    });

    it('should display Feature Matrix link button', async () => {
      render(<PlansPage />);

      expect(screen.getByRole('link', { name: /feature matrix/i })).toBeInTheDocument();
    });
  });

  describe('Revenue Stats', () => {
    it('should display Monthly Revenue card', async () => {
      render(<PlansPage />);

      await waitFor(() => {
        expect(screen.getByText('Monthly Revenue')).toBeInTheDocument();
      });
    });

    it('should display Annual Revenue card', async () => {
      render(<PlansPage />);

      await waitFor(() => {
        expect(screen.getByText('Annual Revenue')).toBeInTheDocument();
      });
    });

    it('should display Total Subscribers card', async () => {
      render(<PlansPage />);

      await waitFor(() => {
        expect(screen.getByText('Total Subscribers')).toBeInTheDocument();
      });
    });

    it('should display Enterprise Tenants card', async () => {
      render(<PlansPage />);

      await waitFor(() => {
        expect(screen.getByText('Enterprise Tenants')).toBeInTheDocument();
      });
    });
  });

  describe('Tabs', () => {
    it('should display Plan Overview tab', async () => {
      render(<PlansPage />);

      expect(screen.getByRole('tab', { name: /plan overview/i })).toBeInTheDocument();
    });

    it('should display Feature Comparison tab', async () => {
      render(<PlansPage />);

      expect(screen.getByRole('tab', { name: /feature comparison/i })).toBeInTheDocument();
    });

    it('should display Pricing tab', async () => {
      render(<PlansPage />);

      expect(screen.getByRole('tab', { name: /pricing/i })).toBeInTheDocument();
    });
  });

  describe('Plan Cards', () => {
    it('should display Free plan', async () => {
      render(<PlansPage />);

      await waitFor(() => {
        expect(screen.getByText('Free')).toBeInTheDocument();
      });
    });

    it('should display Pro plan', async () => {
      render(<PlansPage />);

      await waitFor(() => {
        expect(screen.getByText('Pro')).toBeInTheDocument();
      });
    });

    it('should display Agency plan', async () => {
      render(<PlansPage />);

      await waitFor(() => {
        expect(screen.getByText('Agency')).toBeInTheDocument();
      });
    });

    it('should display Enterprise plan', async () => {
      render(<PlansPage />);

      await waitFor(() => {
        expect(screen.getByText('Enterprise')).toBeInTheDocument();
      });
    });

    it('should display plan descriptions', async () => {
      render(<PlansPage />);

      await waitFor(() => {
        expect(screen.getByText('Get started for free')).toBeInTheDocument();
      });
      expect(screen.getByText('For growing teams')).toBeInTheDocument();
    });
  });
});
