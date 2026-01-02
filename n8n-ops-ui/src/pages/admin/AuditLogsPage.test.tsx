import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { AuditLogsPage } from './AuditLogsPage';

const API_BASE = '/api/v1';

const mockLogs = [
  {
    id: 'log-1',
    timestamp: '2024-01-15T10:00:00Z',
    actorEmail: 'admin@test.com',
    actorId: 'user-1',
    tenantId: 'tenant-1',
    actionType: 'tenant_created',
    resourceType: 'tenant',
    resourceId: 'tenant-1',
    ipAddress: '192.168.1.1',
    oldValue: null,
    newValue: { name: 'Test Tenant' },
  },
  {
    id: 'log-2',
    timestamp: '2024-01-15T09:00:00Z',
    actorEmail: 'admin@test.com',
    actorId: 'user-1',
    tenantId: 'tenant-1',
    actionType: 'feature_override_created',
    resourceType: 'feature',
    resourceId: 'feature-1',
    ipAddress: '192.168.1.1',
    oldValue: null,
    newValue: { feature: 'max_workflows', value: 200 },
  },
];

describe('AuditLogsPage', () => {
  beforeEach(() => {
    server.resetHandlers();

    server.use(
      http.get(`${API_BASE}/admin/audit-logs`, () => {
        return HttpResponse.json({
          logs: mockLogs,
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
      render(<AuditLogsPage />);

      expect(screen.getByRole('heading', { level: 1, name: /audit logs/i })).toBeInTheDocument();
    });

    it('should display the page description', async () => {
      render(<AuditLogsPage />);

      expect(screen.getByText(/track all system activity and admin actions/i)).toBeInTheDocument();
    });

    it('should display Refresh button', async () => {
      render(<AuditLogsPage />);

      expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
    });

    it('should display Export Logs button', async () => {
      render(<AuditLogsPage />);

      expect(screen.getByRole('button', { name: /export logs/i })).toBeInTheDocument();
    });
  });

  describe('Stats Cards', () => {
    it('should display Total Events stat', async () => {
      render(<AuditLogsPage />);

      await waitFor(() => {
        expect(screen.getByText('Total Events')).toBeInTheDocument();
      });
    });

    it('should display Tenant Events stat', async () => {
      render(<AuditLogsPage />);

      await waitFor(() => {
        expect(screen.getByText('Tenant Events')).toBeInTheDocument();
      });
    });

    it('should display Feature Events stat', async () => {
      render(<AuditLogsPage />);

      await waitFor(() => {
        expect(screen.getByText('Feature Events')).toBeInTheDocument();
      });
    });

    it('should display System Events stat', async () => {
      render(<AuditLogsPage />);

      await waitFor(() => {
        expect(screen.getByText('System Events')).toBeInTheDocument();
      });
    });
  });

  describe('Filters', () => {
    it('should display Filters section', async () => {
      render(<AuditLogsPage />);

      expect(screen.getByText('Filters')).toBeInTheDocument();
    });

    it('should display search input', async () => {
      render(<AuditLogsPage />);

      expect(screen.getByPlaceholderText(/search by actor, tenant, or details/i)).toBeInTheDocument();
    });

    it('should display quick filter buttons', async () => {
      render(<AuditLogsPage />);

      expect(screen.getByRole('button', { name: /all/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /tenant/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /users/i })).toBeInTheDocument();
    });
  });

  describe('Logs Table', () => {
    it('should display Activity Log section', async () => {
      render(<AuditLogsPage />);

      await waitFor(() => {
        expect(screen.getByText('Activity Log')).toBeInTheDocument();
      });
    });

    it('should display loading state initially', async () => {
      server.use(
        http.get(`${API_BASE}/admin/audit-logs`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json({ logs: mockLogs, total: 2 });
        })
      );

      render(<AuditLogsPage />);

      expect(screen.getByText(/loading audit logs/i)).toBeInTheDocument();
    });

    it('should display table headers', async () => {
      render(<AuditLogsPage />);

      await waitFor(() => {
        expect(screen.getByText('Timestamp')).toBeInTheDocument();
      });
      expect(screen.getByText('Actor')).toBeInTheDocument();
      expect(screen.getByText('Action')).toBeInTheDocument();
      expect(screen.getByText('Details')).toBeInTheDocument();
      expect(screen.getByText('IP Address')).toBeInTheDocument();
    });

    it('should display actor emails', async () => {
      render(<AuditLogsPage />);

      await waitFor(() => {
        expect(screen.getAllByText('admin@test.com').length).toBeGreaterThan(0);
      });
    });
  });

  describe('Empty State', () => {
    it('should show empty message when no logs exist', async () => {
      server.use(
        http.get(`${API_BASE}/admin/audit-logs`, () => {
          return HttpResponse.json({ logs: [], total: 0 });
        })
      );

      render(<AuditLogsPage />);

      await waitFor(() => {
        expect(screen.getByText(/no audit logs found/i)).toBeInTheDocument();
      });
    });
  });
});
