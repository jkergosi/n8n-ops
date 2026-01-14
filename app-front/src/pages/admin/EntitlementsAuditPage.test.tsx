import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { EntitlementsAuditPage } from './EntitlementsAuditPage';

const API_BASE = '/api/v1';

const mockConfigAudits = [
  {
    id: 'audit-1',
    entity_type: 'tenant_override',
    feature_key: 'max_workflows',
    action: 'create',
    old_value: null,
    new_value: { value: 200 },
    changed_by_email: 'admin@test.com',
    changed_at: '2024-01-15T10:00:00Z',
    reason: 'Enterprise upgrade',
  },
  {
    id: 'audit-2',
    entity_type: 'plan_feature',
    feature_key: 'max_environments',
    action: 'update',
    old_value: { value: 5 },
    new_value: { value: 10 },
    changed_by_email: 'admin@test.com',
    changed_at: '2024-01-14T15:30:00Z',
    reason: 'Plan update',
  },
];

const mockAccessLogs = [
  {
    id: 'log-1',
    featureKey: 'max_workflows',
    accessType: 'limit_check',
    result: 'allowed',
    limitValue: 100,
    currentValue: 50,
    userEmail: 'user@test.com',
    endpoint: '/api/v1/workflows',
    accessedAt: '2024-01-15T10:00:00Z',
  },
];

const mockTenants = [
  { id: 'tenant-1', name: 'Acme Corp', email: 'admin@acme.com', subscriptionPlan: 'pro', status: 'active' },
  { id: 'tenant-2', name: 'Test Org', email: 'admin@test.com', subscriptionPlan: 'free', status: 'active' },
];

const mockFeatures = [
  { id: 'feat-1', key: 'max_workflows', displayName: 'Max Workflows', description: 'Maximum workflows allowed' },
  { id: 'feat-2', key: 'max_environments', displayName: 'Max Environments', description: 'Maximum environments allowed' },
];

describe('EntitlementsAuditPage', () => {
  beforeEach(() => {
    server.resetHandlers();

    server.use(
      http.get(`${API_BASE}/tenants/entitlements/audits`, () => {
        return HttpResponse.json({
          audits: mockConfigAudits,
          total: 2,
          page: 1,
          page_size: 20,
        });
      }),
      http.get(`${API_BASE}/tenants/entitlements/access-logs`, () => {
        return HttpResponse.json({
          logs: mockAccessLogs,
          total: 1,
          page: 1,
          page_size: 20,
        });
      }),
      http.get(`${API_BASE}/tenants`, () => {
        return HttpResponse.json({
          tenants: mockTenants,
          total: 2,
        });
      }),
      http.get(`${API_BASE}/admin/entitlements/features`, () => {
        return HttpResponse.json({
          features: mockFeatures,
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
      render(<EntitlementsAuditPage />);

      expect(screen.getByRole('heading', { level: 1, name: /entitlements audit/i })).toBeInTheDocument();
    });

    it('should display the page description', async () => {
      render(<EntitlementsAuditPage />);

      expect(screen.getByText(/view configuration changes and access logs for feature entitlements/i)).toBeInTheDocument();
    });

    it('should display Refresh button', async () => {
      render(<EntitlementsAuditPage />);

      expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
    });
  });

  describe('Filters', () => {
    it('should display Filters card', async () => {
      render(<EntitlementsAuditPage />);

      expect(screen.getByText('Filters')).toBeInTheDocument();
    });

    it('should display tenant filter', async () => {
      render(<EntitlementsAuditPage />);

      expect(screen.getByText('All Tenants')).toBeInTheDocument();
    });

    it('should display feature filter', async () => {
      render(<EntitlementsAuditPage />);

      expect(screen.getByText('All Features')).toBeInTheDocument();
    });

    it('should display Clear Filters button', async () => {
      render(<EntitlementsAuditPage />);

      expect(screen.getByRole('button', { name: /clear filters/i })).toBeInTheDocument();
    });
  });

  describe('Tabs', () => {
    it('should display Config Changes tab', async () => {
      render(<EntitlementsAuditPage />);

      expect(screen.getByRole('tab', { name: /config changes/i })).toBeInTheDocument();
    });

    it('should display Access Logs tab', async () => {
      render(<EntitlementsAuditPage />);

      expect(screen.getByRole('tab', { name: /access logs/i })).toBeInTheDocument();
    });
  });

  describe('Config Changes Table', () => {
    it('should display table headers', async () => {
      render(<EntitlementsAuditPage />);

      await waitFor(() => {
        expect(screen.getByText('Date')).toBeInTheDocument();
      });
      expect(screen.getByText('Entity Type')).toBeInTheDocument();
      expect(screen.getByText('Feature')).toBeInTheDocument();
      expect(screen.getByText('Action')).toBeInTheDocument();
      expect(screen.getByText('Value Change')).toBeInTheDocument();
      expect(screen.getByText('Changed By')).toBeInTheDocument();
      expect(screen.getByText('Reason')).toBeInTheDocument();
    });

    it('should display feature keys', async () => {
      render(<EntitlementsAuditPage />);

      await waitFor(() => {
        expect(screen.getByText('max_workflows')).toBeInTheDocument();
      });
      expect(screen.getByText('max_environments')).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('should show empty message when no config changes exist', async () => {
      server.use(
        http.get(`${API_BASE}/tenants/entitlements/audits`, () => {
          return HttpResponse.json({ audits: [], total: 0, page: 1, page_size: 20 });
        })
      );

      render(<EntitlementsAuditPage />);

      await waitFor(() => {
        expect(screen.getByText(/no configuration changes found/i)).toBeInTheDocument();
      });
    });
  });

  describe('Loading State', () => {
    it('should show loading state initially', async () => {
      server.use(
        http.get(`${API_BASE}/tenants/entitlements/audits`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json({ audits: mockConfigAudits, total: 2, page: 1, page_size: 20 });
        })
      );

      render(<EntitlementsAuditPage />);

      expect(screen.getByText(/loading audit logs/i)).toBeInTheDocument();
    });
  });
});
