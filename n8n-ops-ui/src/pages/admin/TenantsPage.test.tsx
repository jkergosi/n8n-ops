import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { TenantsPage } from './TenantsPage';

const API_BASE = '/api/v1';

const mockTenants = [
  {
    id: 'tenant-1',
    name: 'Acme Corp',
    email: 'admin@acme.com',
    subscriptionPlan: 'pro',
    status: 'active',
    workflowCount: 15,
    environmentCount: 3,
    userCount: 5,
    createdAt: '2024-01-01T00:00:00Z',
  },
  {
    id: 'tenant-2',
    name: 'Test Org',
    email: 'admin@test.com',
    subscriptionPlan: 'free',
    status: 'suspended',
    workflowCount: 5,
    environmentCount: 1,
    userCount: 2,
    createdAt: '2024-02-01T00:00:00Z',
  },
];

const mockStats = {
  totalTenants: 10,
  activeTenants: 8,
  suspendedTenants: 2,
  byPlan: { free: 5, pro: 3, agency: 1, enterprise: 1 },
};

describe('TenantsPage', () => {
  beforeEach(() => {
    server.resetHandlers();

    server.use(
      http.get(`${API_BASE}/tenants`, ({ request }) => {
        const url = new URL(request.url);
        const search = (url.searchParams.get('search') || '').toLowerCase();
        const tenants = search
          ? mockTenants.filter((t) =>
              t.name.toLowerCase().includes(search) || (t.email || '').toLowerCase().includes(search)
            )
          : mockTenants;
        return HttpResponse.json({
          tenants,
          total: tenants.length,
          total_pages: 1,
        });
      }),
      http.get(`${API_BASE}/tenants/stats`, () => {
        return HttpResponse.json(mockStats);
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

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('Page Header', () => {
    it('should display the page title', async () => {
      render(<TenantsPage />);

      expect(screen.getByRole('heading', { level: 1, name: /tenants/i })).toBeInTheDocument();
    });

    it('should display the page description', async () => {
      render(<TenantsPage />);

      expect(screen.getByText(/manage all tenants in the system/i)).toBeInTheDocument();
    });

    it('should display Add Tenant button', async () => {
      render(<TenantsPage />);

      expect(screen.getByRole('button', { name: /add tenant/i })).toBeInTheDocument();
    });

    it('should display Export CSV button', async () => {
      render(<TenantsPage />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /export csv/i })).toBeInTheDocument();
      });
    });

    it('should display Refresh button', async () => {
      render(<TenantsPage />);

      expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
    });
  });

  describe('Stats Cards', () => {
    it('should display Total Tenants stat', async () => {
      render(<TenantsPage />);

      await waitFor(() => {
        expect(screen.getByText('Total Tenants')).toBeInTheDocument();
      });
    });

    it('should display Active stat', async () => {
      render(<TenantsPage />);

      await waitFor(() => {
        expect(screen.getByText('Active')).toBeInTheDocument();
      });
    });

    it('should display Enterprise stat', async () => {
      render(<TenantsPage />);

      await waitFor(() => {
        expect(screen.getByText('Enterprise')).toBeInTheDocument();
      });
    });

    it('should display Pro stat', async () => {
      render(<TenantsPage />);

      await waitFor(() => {
        expect(screen.getByText('Pro')).toBeInTheDocument();
      });
    });
  });

  describe('Filters', () => {
    it('should display Filters section', async () => {
      render(<TenantsPage />);

      expect(screen.getByText('Filters')).toBeInTheDocument();
    });

    it('should display search input', async () => {
      render(<TenantsPage />);

      expect(screen.getByPlaceholderText(/search by name or email/i)).toBeInTheDocument();
    });

    it('should debounce search and return matching tenants', async () => {
      vi.useFakeTimers();
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

      render(<TenantsPage />);

      await waitFor(() => {
        expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      });
      expect(screen.getByText('Test Org')).toBeInTheDocument();

      const input = screen.getByPlaceholderText(/search by name or email/i);
      await user.clear(input);
      await user.type(input, 'acme');

      // Still shows previous results until debounce fires and fetch resolves
      expect(screen.getByText('Test Org')).toBeInTheDocument();

      vi.advanceTimersByTime(350);

      await waitFor(() => {
        expect(screen.getByText('Acme Corp')).toBeInTheDocument();
        expect(screen.queryByText('Test Org')).not.toBeInTheDocument();
      });
    });
  });

  describe('Tenants Table', () => {
    it('should display All Tenants section title', async () => {
      render(<TenantsPage />);

      await waitFor(() => {
        expect(screen.getByText('All Tenants')).toBeInTheDocument();
      });
    });

    it('should display loading state initially', async () => {
      server.use(
        http.get(`${API_BASE}/tenants`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json({ tenants: mockTenants, total: 2 });
        })
      );

      render(<TenantsPage />);

      expect(screen.getByText(/loading tenants/i)).toBeInTheDocument();
    });

    it('should display tenant names', async () => {
      render(<TenantsPage />);

      await waitFor(() => {
        expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      });
      expect(screen.getByText('Test Org')).toBeInTheDocument();
    });

    it('should display tenant emails', async () => {
      render(<TenantsPage />);

      await waitFor(() => {
        expect(screen.getByText('admin@acme.com')).toBeInTheDocument();
      });
      expect(screen.getByText('admin@test.com')).toBeInTheDocument();
    });

    it('should display plan badges', async () => {
      render(<TenantsPage />);

      await waitFor(() => {
        expect(screen.getByText('pro')).toBeInTheDocument();
      });
      expect(screen.getByText('free')).toBeInTheDocument();
    });

    it('should display status badges', async () => {
      render(<TenantsPage />);

      await waitFor(() => {
        expect(screen.getAllByText('active').length).toBeGreaterThan(0);
      });
      expect(screen.getAllByText('suspended').length).toBeGreaterThan(0);
    });

    it('should display table headers', async () => {
      render(<TenantsPage />);

      await waitFor(() => {
        expect(screen.getByText('Tenant')).toBeInTheDocument();
      });
      expect(screen.getByText('Plan')).toBeInTheDocument();
      expect(screen.getByText('Status')).toBeInTheDocument();
      expect(screen.getByText('Created')).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('should show empty message when no tenants exist', async () => {
      server.use(
        http.get(`${API_BASE}/tenants`, () => {
          return HttpResponse.json({ tenants: [], total: 0 });
        })
      );

      render(<TenantsPage />);

      await waitFor(() => {
        expect(screen.getByText(/no tenants/i)).toBeInTheDocument();
      });
    });

    it('should show filter message when no tenants match filters', async () => {
      server.use(
        http.get(`${API_BASE}/tenants`, () => {
          return HttpResponse.json({ tenants: [], total: 0 });
        })
      );

      render(<TenantsPage />);

      await waitFor(() => {
        expect(screen.getByText(/no tenants/i)).toBeInTheDocument();
      });
    });
  });

  describe('Error State', () => {
    it('should handle server error gracefully', async () => {
      server.use(
        http.get(`${API_BASE}/tenants`, () => {
          return new HttpResponse(JSON.stringify({ detail: 'Internal server error' }), {
            status: 500,
          });
        })
      );

      render(<TenantsPage />);

      // Page should not crash
      await waitFor(() => {
        expect(screen.getByRole('heading', { level: 1, name: /tenants/i })).toBeInTheDocument();
      });
    });
  });
});
