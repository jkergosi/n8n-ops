import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor, userEvent } from '@/test/test-utils';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { TenantDetailPage } from './TenantDetailPage';
import { Routes, Route } from 'react-router-dom';

const API_BASE = '/api/v1';

const mockTenant = {
  id: 'tenant-1',
  name: 'Acme Corp',
  email: 'admin@acme.com',
  subscriptionPlan: 'pro',
  status: 'active',
  workflowCount: 15,
  environmentCount: 3,
  userCount: 5,
  createdAt: '2024-01-01T00:00:00Z',
  primaryContactName: 'John Doe',
  primaryContactEmail: 'john@acme.com',
  stripeCustomerId: 'cus_123',
  usage: {
    workflows: { current: 15, limit: 100, percentage: 15 },
    environments: { current: 3, limit: 5, percentage: 60 },
    users: { current: 5, limit: 10, percentage: 50 },
  },
};

const mockNotes = [
  { id: 'note-1', content: 'Customer requested demo', createdAt: '2024-01-15T10:00:00Z', createdBy: 'admin@test.com' },
];

const mockOverrides = [
  { id: 'override-1', featureKey: 'max_workflows', overrideValue: 200, reason: 'Trial extension' },
];

describe('TenantDetailPage', () => {
  beforeEach(() => {
    server.resetHandlers();

    server.use(
      http.get(`${API_BASE}/tenants/:id`, () => {
        return HttpResponse.json(mockTenant);
      }),
      http.get(`${API_BASE}/tenants/:id/notes`, () => {
        return HttpResponse.json({ notes: mockNotes });
      }),
      http.get(`${API_BASE}/tenants/:id/overrides`, () => {
        return HttpResponse.json({ overrides: mockOverrides });
      }),
      http.get(`${API_BASE}/tenants/:id/entitlements/overrides`, () => {
        return HttpResponse.json({ overrides: mockOverrides });
      }),
      http.get(`${API_BASE}/tenants/:id/users`, () => {
        return HttpResponse.json({ users: [] });
      }),
      http.get(`${API_BASE}/tenants/:id/activity`, () => {
        return HttpResponse.json({ activity: [] });
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
    it('should display Back to Tenants link', async () => {
      render(
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetailPage />} />
        </Routes>,
        { initialRoute: '/admin/tenants/tenant-1' }
      );

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /back to tenants/i })).toBeInTheDocument();
      });
    });

    it('should display tenant name', async () => {
      render(
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetailPage />} />
        </Routes>,
        { initialRoute: '/admin/tenants/tenant-1' }
      );

      await waitFor(() => {
        expect(screen.getAllByText('Acme Corp').length).toBeGreaterThan(0);
      });
    });

    it('should display status badge', async () => {
      render(
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetailPage />} />
        </Routes>,
        { initialRoute: '/admin/tenants/tenant-1' }
      );

      await waitFor(() => {
        expect(screen.getByText('active')).toBeInTheDocument();
      });
    });

    it('should display plan badge', async () => {
      render(
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetailPage />} />
        </Routes>,
        { initialRoute: '/admin/tenants/tenant-1' }
      );

      await waitFor(() => {
        expect(screen.getByText('pro')).toBeInTheDocument();
      });
    });

    it('should display Edit button', async () => {
      render(
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetailPage />} />
        </Routes>,
        { initialRoute: '/admin/tenants/tenant-1' }
      );

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /edit/i })).toBeInTheDocument();
      });
    });
  });

  describe('Tabs', () => {
    it('should display Overview tab', async () => {
      render(
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetailPage />} />
        </Routes>,
        { initialRoute: '/admin/tenants/tenant-1' }
      );

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /overview/i })).toBeInTheDocument();
      });
    });

    it('should display Users tab', async () => {
      render(
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetailPage />} />
        </Routes>,
        { initialRoute: '/admin/tenants/tenant-1' }
      );

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /users/i })).toBeInTheDocument();
      });
    });

    it('should display Usage tab', async () => {
      render(
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetailPage />} />
        </Routes>,
        { initialRoute: '/admin/tenants/tenant-1' }
      );

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /usage/i })).toBeInTheDocument();
      });
    });

    it('should display Billing tab', async () => {
      render(
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetailPage />} />
        </Routes>,
        { initialRoute: '/admin/tenants/tenant-1' }
      );

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /billing/i })).toBeInTheDocument();
      });
    });

    it('should display Activity tab', async () => {
      render(
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetailPage />} />
        </Routes>,
        { initialRoute: '/admin/tenants/tenant-1' }
      );

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /notes/i })).toBeInTheDocument();
      });
    });
  });

  describe('Overview Tab', () => {
    it('should display Tenant Information section', async () => {
      render(
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetailPage />} />
        </Routes>,
        { initialRoute: '/admin/tenants/tenant-1' }
      );

      await waitFor(() => {
        expect(screen.getByText('Tenant Information')).toBeInTheDocument();
      });
    });

    it('should display tenant email', async () => {
      render(
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetailPage />} />
        </Routes>,
        { initialRoute: '/admin/tenants/tenant-1' }
      );

      await waitFor(() => {
        expect(screen.getAllByText('admin@acme.com').length).toBeGreaterThan(0);
      });
    });

    it('should display Quick Stats section', async () => {
      render(
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetailPage />} />
        </Routes>,
        { initialRoute: '/admin/tenants/tenant-1' }
      );

      await waitFor(() => {
        expect(screen.getByText('Quick Stats')).toBeInTheDocument();
      });
    });

    it('should display Notes section', async () => {
      render(
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetailPage />} />
        </Routes>,
        { initialRoute: '/admin/tenants/tenant-1' }
      );

      await waitFor(() => {
        expect(screen.getByText('Notes')).toBeInTheDocument();
      });
    });

    it('should display Feature Overrides section', async () => {
      render(
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetailPage />} />
        </Routes>,
        { initialRoute: '/admin/tenants/tenant-1' }
      );

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /plan & features/i })).toBeInTheDocument();
      });

      await userEvent.click(screen.getByRole('tab', { name: /plan & features/i }));

      await waitFor(() => {
        expect(screen.getAllByText('Feature Overrides').length).toBeGreaterThan(0);
      });
    });
  });

  describe('Loading State', () => {
    it('should show loading state initially', async () => {
      server.use(
        http.get(`${API_BASE}/tenants/:id`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json(mockTenant);
        })
      );

      render(
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetailPage />} />
        </Routes>,
        { initialRoute: '/admin/tenants/tenant-1' }
      );

      expect(screen.getByText(/loading tenant/i)).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('should handle server error gracefully', async () => {
      server.use(
        http.get(`${API_BASE}/tenants/:id`, () => {
          return new HttpResponse(JSON.stringify({ detail: 'Tenant not found' }), {
            status: 404,
          });
        })
      );

      render(
        <Routes>
          <Route path="/admin/tenants/:tenantId" element={<TenantDetailPage />} />
        </Routes>,
        { initialRoute: '/admin/tenants/tenant-1' }
      );

      await waitFor(() => {
        expect(screen.getByText(/tenant not found/i)).toBeInTheDocument();
      });
    });
  });
});
