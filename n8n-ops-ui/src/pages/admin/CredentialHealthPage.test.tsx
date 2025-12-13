import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { CredentialHealthPage } from './CredentialHealthPage';

const API_BASE = 'http://localhost:4000/api/v1';

describe('CredentialHealthPage', () => {
  beforeEach(() => {
    server.resetHandlers();

    server.use(
      http.get(`${API_BASE}/admin/credentials/health`, () => {
        return HttpResponse.json({
          summary: {
            total: 50,
            healthy: 45,
            warning: 3,
            error: 2,
          },
          credentials: [
            { id: 'cred-1', name: 'Slack API', type: 'slackApi', status: 'healthy', tenant: 'Acme Corp', lastChecked: new Date().toISOString() },
            { id: 'cred-2', name: 'GitHub Token', type: 'githubApi', status: 'warning', tenant: 'Test Org', lastChecked: new Date().toISOString() },
            { id: 'cred-3', name: 'OpenAI Key', type: 'openAiApi', status: 'error', tenant: 'Demo Inc', lastChecked: new Date().toISOString() },
          ],
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
      render(<CredentialHealthPage />);

      expect(screen.getByRole('heading', { level: 1, name: /credential health/i })).toBeInTheDocument();
    });

    it('should display the page description', async () => {
      render(<CredentialHealthPage />);

      expect(screen.getByText(/monitor credential status across all tenants/i)).toBeInTheDocument();
    });

    it('should display Refresh button', async () => {
      render(<CredentialHealthPage />);

      expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
    });
  });

  describe('Summary Cards', () => {
    it('should display Total Credentials card', async () => {
      render(<CredentialHealthPage />);

      await waitFor(() => {
        expect(screen.getByText('Total Credentials')).toBeInTheDocument();
      });
    });

    it('should display Healthy card', async () => {
      render(<CredentialHealthPage />);

      await waitFor(() => {
        expect(screen.getByText('Healthy')).toBeInTheDocument();
      });
    });

    it('should display Warning card', async () => {
      render(<CredentialHealthPage />);

      await waitFor(() => {
        expect(screen.getByText('Warning')).toBeInTheDocument();
      });
    });

    it('should display Error card', async () => {
      render(<CredentialHealthPage />);

      await waitFor(() => {
        expect(screen.getByText('Error')).toBeInTheDocument();
      });
    });
  });

  describe('Credentials Table', () => {
    it('should display table headers', async () => {
      render(<CredentialHealthPage />);

      await waitFor(() => {
        expect(screen.getByText('Credential')).toBeInTheDocument();
      });
      expect(screen.getByText('Type')).toBeInTheDocument();
      expect(screen.getByText('Status')).toBeInTheDocument();
    });

    it('should display credential names', async () => {
      render(<CredentialHealthPage />);

      await waitFor(() => {
        expect(screen.getByText('Slack API')).toBeInTheDocument();
      });
      expect(screen.getByText('GitHub Token')).toBeInTheDocument();
      expect(screen.getByText('OpenAI Key')).toBeInTheDocument();
    });

    it('should display status badges', async () => {
      render(<CredentialHealthPage />);

      await waitFor(() => {
        expect(screen.getByText('healthy')).toBeInTheDocument();
      });
      expect(screen.getByText('warning')).toBeInTheDocument();
      expect(screen.getByText('error')).toBeInTheDocument();
    });
  });

  describe('Loading State', () => {
    it('should show loading state initially', async () => {
      server.use(
        http.get(`${API_BASE}/admin/credentials/health`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json({ summary: {}, credentials: [] });
        })
      );

      render(<CredentialHealthPage />);

      expect(screen.getByText(/loading credential health/i)).toBeInTheDocument();
    });
  });
});
