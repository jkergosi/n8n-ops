import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { SecurityPage } from './SecurityPage';

const API_BASE = '/api/v1';

describe('SecurityPage', () => {
  beforeEach(() => {
    server.resetHandlers();

    server.use(
      http.get(`${API_BASE}/security/api-keys`, () => {
        return HttpResponse.json([
          {
            id: 'key-1',
            name: 'Production API Key',
            key_prefix: 'n8n_prod_****',
            scopes: ['read', 'write'],
            created_at: '2024-01-01T00:00:00Z',
            last_used_at: null,
            revoked_at: null,
            is_active: true,
          },
          {
            id: 'key-2',
            name: 'CI/CD Integration',
            key_prefix: 'n8n_ci_****',
            scopes: ['read'],
            created_at: '2024-01-02T00:00:00Z',
            last_used_at: '2024-02-01T00:00:00Z',
            revoked_at: null,
            is_active: true,
          },
        ]);
      }),
      http.get(`${API_BASE}/admin/audit-logs`, () => {
        return HttpResponse.json({
          logs: [
            {
              id: 'log-1',
              timestamp: '2024-02-01T00:00:00Z',
              action_type: 'api_key_created',
              action: 'Created API key',
              ip_address: '127.0.0.1',
            },
          ],
          total: 1,
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
      render(<SecurityPage />);

      expect(screen.getByRole('heading', { level: 1, name: /security/i })).toBeInTheDocument();
    });

    it('should display the page description', async () => {
      render(<SecurityPage />);

      expect(screen.getByText(/manage api keys, access controls, and security settings/i)).toBeInTheDocument();
    });
  });

  describe('Security Overview Cards', () => {
    it('should display Active API Keys card', async () => {
      render(<SecurityPage />);

      await waitFor(() => {
        expect(screen.getByText('Active API Keys')).toBeInTheDocument();
      });
    });

    it('should display Recent Events card', async () => {
      render(<SecurityPage />);

      await waitFor(() => {
        expect(screen.getByText('Recent Events')).toBeInTheDocument();
      });
    });
  });

  describe('API Keys Section', () => {
    it('should display API Keys section title', async () => {
      render(<SecurityPage />);

      await waitFor(() => {
        expect(screen.getByText('API Keys')).toBeInTheDocument();
      });
    });

    it('should display Create Key button', async () => {
      render(<SecurityPage />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /create key/i })).toBeInTheDocument();
      });
    });

    it('should display API key names', async () => {
      render(<SecurityPage />);

      await waitFor(() => {
        expect(screen.getByText('Production API Key')).toBeInTheDocument();
      });
      expect(screen.getByText('CI/CD Integration')).toBeInTheDocument();
    });

    it('should display API key prefixes', async () => {
      render(<SecurityPage />);

      await waitFor(() => {
        expect(screen.getByText('n8n_prod_****')).toBeInTheDocument();
      });
    });

    it('should display scope badges', async () => {
      render(<SecurityPage />);

      await waitFor(() => {
        expect(screen.getAllByText('read').length).toBeGreaterThan(0);
      });
      expect(screen.getAllByText('write').length).toBeGreaterThan(0);
    });
  });

  describe('Security Events Table', () => {
    it('should display Recent Security Events section', async () => {
      render(<SecurityPage />);

      await waitFor(() => {
        expect(screen.getByText('Recent Security Events')).toBeInTheDocument();
      });
    });

    it('should display table headers', async () => {
      render(<SecurityPage />);

      await waitFor(() => {
        expect(screen.getByText('Event')).toBeInTheDocument();
      });
      expect(screen.getByText('Details')).toBeInTheDocument();
      expect(screen.getByText('IP Address')).toBeInTheDocument();
    });

    it('should display security event descriptions', async () => {
      render(<SecurityPage />);

      await waitFor(() => {
        expect(screen.getByText('api_key_created')).toBeInTheDocument();
      });
    });
  });
});
