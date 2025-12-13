import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { SettingsPage } from './SettingsPage';

const API_BASE = 'http://localhost:4000/api/v1';

describe('SettingsPage', () => {
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
      render(<SettingsPage />);

      expect(screen.getByRole('heading', { level: 1, name: /settings/i })).toBeInTheDocument();
    });

    it('should display the page description', async () => {
      render(<SettingsPage />);

      expect(screen.getByText(/configure system-wide settings and integrations/i)).toBeInTheDocument();
    });
  });

  describe('Tabs', () => {
    it('should display General tab', async () => {
      render(<SettingsPage />);

      expect(screen.getByRole('tab', { name: /general/i })).toBeInTheDocument();
    });

    it('should display Database tab', async () => {
      render(<SettingsPage />);

      expect(screen.getByRole('tab', { name: /database/i })).toBeInTheDocument();
    });

    it('should display Auth0 tab', async () => {
      render(<SettingsPage />);

      expect(screen.getByRole('tab', { name: /auth0/i })).toBeInTheDocument();
    });

    it('should display Payments tab', async () => {
      render(<SettingsPage />);

      expect(screen.getByRole('tab', { name: /payments/i })).toBeInTheDocument();
    });

    it('should display Email tab', async () => {
      render(<SettingsPage />);

      expect(screen.getByRole('tab', { name: /email/i })).toBeInTheDocument();
    });
  });

  describe('General Tab (Default)', () => {
    it('should display System Settings section', async () => {
      render(<SettingsPage />);

      await waitFor(() => {
        expect(screen.getByText('System Settings')).toBeInTheDocument();
      });
    });

    it('should display Application Name field', async () => {
      render(<SettingsPage />);

      await waitFor(() => {
        expect(screen.getByLabelText('Application Name')).toBeInTheDocument();
      });
    });

    it('should display Application URL field', async () => {
      render(<SettingsPage />);

      await waitFor(() => {
        expect(screen.getByLabelText('Application URL')).toBeInTheDocument();
      });
    });

    it('should display Support Email field', async () => {
      render(<SettingsPage />);

      await waitFor(() => {
        expect(screen.getByLabelText('Support Email')).toBeInTheDocument();
      });
    });

    it('should display Default Timezone field', async () => {
      render(<SettingsPage />);

      await waitFor(() => {
        expect(screen.getByLabelText('Default Timezone')).toBeInTheDocument();
      });
    });

    it('should display Maintenance Mode toggle', async () => {
      render(<SettingsPage />);

      await waitFor(() => {
        expect(screen.getByText('Maintenance Mode')).toBeInTheDocument();
      });
    });

    it('should display Save Changes button', async () => {
      render(<SettingsPage />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /save changes/i })).toBeInTheDocument();
      });
    });
  });

  describe('Environment Variables Section', () => {
    it('should display Environment Variables section', async () => {
      render(<SettingsPage />);

      await waitFor(() => {
        expect(screen.getByText('Environment Variables')).toBeInTheDocument();
      });
    });

    it('should display NODE_ENV variable', async () => {
      render(<SettingsPage />);

      await waitFor(() => {
        expect(screen.getByText('NODE_ENV')).toBeInTheDocument();
      });
    });

    it('should display API_VERSION variable', async () => {
      render(<SettingsPage />);

      await waitFor(() => {
        expect(screen.getByText('API_VERSION')).toBeInTheDocument();
      });
    });
  });
});
