import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { EntitlementsAuditPage } from './EntitlementsAuditPage';

const API_BASE = 'http://localhost:4000/api/v1';

const mockAuditEntries = [
  {
    id: 'audit-1',
    timestamp: '2024-01-15T10:00:00Z',
    actor_email: 'admin@test.com',
    action: 'override_created',
    tenant_name: 'Acme Corp',
    feature_key: 'max_workflows',
    old_value: null,
    new_value: 200,
  },
  {
    id: 'audit-2',
    timestamp: '2024-01-14T15:30:00Z',
    actor_email: 'admin@test.com',
    action: 'override_updated',
    tenant_name: 'Test Org',
    feature_key: 'max_environments',
    old_value: 5,
    new_value: 10,
  },
  {
    id: 'audit-3',
    timestamp: '2024-01-13T09:00:00Z',
    actor_email: 'admin@test.com',
    action: 'override_deleted',
    tenant_name: 'Demo Inc',
    feature_key: 'max_users',
    old_value: 50,
    new_value: null,
  },
];

describe('EntitlementsAuditPage', () => {
  beforeEach(() => {
    server.resetHandlers();

    server.use(
      http.get(`${API_BASE}/admin/entitlements/audit`, () => {
        return HttpResponse.json({
          entries: mockAuditEntries,
          total: 3,
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

      expect(screen.getByRole('heading', { level: 1, name: /entitlements audit log/i })).toBeInTheDocument();
    });

    it('should display the page description', async () => {
      render(<EntitlementsAuditPage />);

      expect(screen.getByText(/track all changes to tenant feature overrides/i)).toBeInTheDocument();
    });

    it('should display Feature Matrix link', async () => {
      render(<EntitlementsAuditPage />);

      expect(screen.getByRole('link', { name: /feature matrix/i })).toBeInTheDocument();
    });

    it('should display Overrides link', async () => {
      render(<EntitlementsAuditPage />);

      expect(screen.getByRole('link', { name: /overrides/i })).toBeInTheDocument();
    });

    it('should display Export button', async () => {
      render(<EntitlementsAuditPage />);

      expect(screen.getByRole('button', { name: /export/i })).toBeInTheDocument();
    });
  });

  describe('Audit Table', () => {
    it('should display table headers', async () => {
      render(<EntitlementsAuditPage />);

      await waitFor(() => {
        expect(screen.getByText('Timestamp')).toBeInTheDocument();
      });
      expect(screen.getByText('Actor')).toBeInTheDocument();
      expect(screen.getByText('Action')).toBeInTheDocument();
      expect(screen.getByText('Tenant')).toBeInTheDocument();
      expect(screen.getByText('Feature')).toBeInTheDocument();
      expect(screen.getByText('Change')).toBeInTheDocument();
    });

    it('should display actor emails', async () => {
      render(<EntitlementsAuditPage />);

      await waitFor(() => {
        expect(screen.getAllByText('admin@test.com').length).toBeGreaterThan(0);
      });
    });

    it('should display action types', async () => {
      render(<EntitlementsAuditPage />);

      await waitFor(() => {
        expect(screen.getByText('override_created')).toBeInTheDocument();
      });
      expect(screen.getByText('override_updated')).toBeInTheDocument();
      expect(screen.getByText('override_deleted')).toBeInTheDocument();
    });

    it('should display tenant names', async () => {
      render(<EntitlementsAuditPage />);

      await waitFor(() => {
        expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      });
      expect(screen.getByText('Test Org')).toBeInTheDocument();
      expect(screen.getByText('Demo Inc')).toBeInTheDocument();
    });

    it('should display feature keys', async () => {
      render(<EntitlementsAuditPage />);

      await waitFor(() => {
        expect(screen.getByText('max_workflows')).toBeInTheDocument();
      });
      expect(screen.getByText('max_environments')).toBeInTheDocument();
      expect(screen.getByText('max_users')).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('should show empty message when no entries exist', async () => {
      server.use(
        http.get(`${API_BASE}/admin/entitlements/audit`, () => {
          return HttpResponse.json({ entries: [], total: 0 });
        })
      );

      render(<EntitlementsAuditPage />);

      await waitFor(() => {
        expect(screen.getByText(/no audit entries found/i)).toBeInTheDocument();
      });
    });
  });

  describe('Loading State', () => {
    it('should show loading state initially', async () => {
      server.use(
        http.get(`${API_BASE}/admin/entitlements/audit`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json({ entries: mockAuditEntries, total: 3 });
        })
      );

      render(<EntitlementsAuditPage />);

      expect(screen.getByText(/loading audit log/i)).toBeInTheDocument();
    });
  });
});
