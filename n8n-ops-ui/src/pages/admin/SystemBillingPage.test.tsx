import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { SystemBillingPage } from './SystemBillingPage';

const API_BASE = 'http://localhost:4000/api/v1';

describe('SystemBillingPage', () => {
  beforeEach(() => {
    server.resetHandlers();

    server.use(
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
      http.get(`${API_BASE}/admin/billing/plan-distribution`, () => {
        return HttpResponse.json([
          { plan: 'free', count: 50 },
          { plan: 'pro', count: 30 },
          { plan: 'agency', count: 15 },
          { plan: 'enterprise', count: 5 },
        ]);
      }),
      http.get(`${API_BASE}/admin/billing/charges`, () => {
        return HttpResponse.json([
          { id: 'ch_1', tenantName: 'Acme Corp', amount: 99, status: 'succeeded', createdAt: '2024-01-15T10:00:00Z' },
        ]);
      }),
      http.get(`${API_BASE}/admin/billing/failed`, () => {
        return HttpResponse.json([]);
      }),
      http.get(`${API_BASE}/admin/billing/dunning`, () => {
        return HttpResponse.json([]);
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
      render(<SystemBillingPage />);

      expect(screen.getByRole('heading', { level: 1, name: /billing overview/i })).toBeInTheDocument();
    });

    it('should display the page description', async () => {
      render(<SystemBillingPage />);

      expect(screen.getByText(/monitor revenue metrics and subscription health/i)).toBeInTheDocument();
    });

    it('should display Refresh button', async () => {
      render(<SystemBillingPage />);

      expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
    });

    it('should display Export button', async () => {
      render(<SystemBillingPage />);

      expect(screen.getByRole('button', { name: /export/i })).toBeInTheDocument();
    });
  });

  describe('Revenue Metrics Cards', () => {
    it('should display MRR card', async () => {
      render(<SystemBillingPage />);

      await waitFor(() => {
        expect(screen.getByText('Monthly Recurring Revenue')).toBeInTheDocument();
      });
    });

    it('should display ARR card', async () => {
      render(<SystemBillingPage />);

      await waitFor(() => {
        expect(screen.getByText('Annual Recurring Revenue')).toBeInTheDocument();
      });
    });

    it('should display Active Subscriptions card', async () => {
      render(<SystemBillingPage />);

      await waitFor(() => {
        expect(screen.getByText('Active Subscriptions')).toBeInTheDocument();
      });
    });

    it('should display Churn Rate card', async () => {
      render(<SystemBillingPage />);

      await waitFor(() => {
        expect(screen.getByText('Churn Rate')).toBeInTheDocument();
      });
    });
  });

  describe('Subscription Distribution', () => {
    it('should display Subscription Distribution section', async () => {
      render(<SystemBillingPage />);

      await waitFor(() => {
        expect(screen.getByText('Subscription Distribution')).toBeInTheDocument();
      });
    });

    it('should display distribution by subscription plan', async () => {
      render(<SystemBillingPage />);

      await waitFor(() => {
        expect(screen.getByText(/breakdown by subscription plan/i)).toBeInTheDocument();
      });
    });
  });

  describe('Recent Charges', () => {
    it('should display Recent Charges section', async () => {
      render(<SystemBillingPage />);

      await waitFor(() => {
        expect(screen.getByText('Recent Charges')).toBeInTheDocument();
      });
    });
  });

  describe('Failed Payments & Dunning', () => {
    it('should display Failed Payments section', async () => {
      render(<SystemBillingPage />);

      await waitFor(() => {
        expect(screen.getByText('Failed Payments')).toBeInTheDocument();
      });
    });

    it('should display Dunning Management section', async () => {
      render(<SystemBillingPage />);

      await waitFor(() => {
        expect(screen.getByText('Dunning Management')).toBeInTheDocument();
      });
    });
  });

  describe('Loading State', () => {
    it('should show loading state initially', async () => {
      server.use(
        http.get(`${API_BASE}/admin/billing/metrics`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json({});
        })
      );

      render(<SystemBillingPage />);

      expect(screen.getByText(/loading billing data/i)).toBeInTheDocument();
    });
  });
});
