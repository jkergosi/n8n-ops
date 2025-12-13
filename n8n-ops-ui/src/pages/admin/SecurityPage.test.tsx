import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { SecurityPage } from './SecurityPage';

const API_BASE = 'http://localhost:4000/api/v1';

describe('SecurityPage', () => {
  beforeEach(() => {
    server.resetHandlers();

    server.use(
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
    it('should display Security Score card', async () => {
      render(<SecurityPage />);

      await waitFor(() => {
        expect(screen.getByText('Security Score')).toBeInTheDocument();
      });
    });

    it('should display Active API Keys card', async () => {
      render(<SecurityPage />);

      await waitFor(() => {
        expect(screen.getByText('Active API Keys')).toBeInTheDocument();
      });
    });

    it('should display Security Events card', async () => {
      render(<SecurityPage />);

      await waitFor(() => {
        expect(screen.getByText('Security Events')).toBeInTheDocument();
      });
    });

    it('should display MFA Status card', async () => {
      render(<SecurityPage />);

      await waitFor(() => {
        expect(screen.getByText('MFA Status')).toBeInTheDocument();
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
      expect(screen.getByText('Monitoring Service')).toBeInTheDocument();
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

  describe('Security Settings Section', () => {
    it('should display Security Settings section title', async () => {
      render(<SecurityPage />);

      await waitFor(() => {
        expect(screen.getByText('Security Settings')).toBeInTheDocument();
      });
    });

    it('should display MFA setting', async () => {
      render(<SecurityPage />);

      await waitFor(() => {
        expect(screen.getByText('Multi-Factor Authentication')).toBeInTheDocument();
      });
    });

    it('should display Session Timeout setting', async () => {
      render(<SecurityPage />);

      await waitFor(() => {
        expect(screen.getByText('Session Timeout')).toBeInTheDocument();
      });
    });

    it('should display Rate Limiting setting', async () => {
      render(<SecurityPage />);

      await waitFor(() => {
        expect(screen.getByText('Rate Limiting')).toBeInTheDocument();
      });
    });

    it('should display IP Whitelist section', async () => {
      render(<SecurityPage />);

      await waitFor(() => {
        expect(screen.getByText('IP Whitelist')).toBeInTheDocument();
      });
    });

    it('should display Password Policy section', async () => {
      render(<SecurityPage />);

      await waitFor(() => {
        expect(screen.getByText('Password Policy')).toBeInTheDocument();
      });
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
        expect(screen.getByText('Failed login attempt')).toBeInTheDocument();
      });
      expect(screen.getByText('API key rotated')).toBeInTheDocument();
    });
  });
});
