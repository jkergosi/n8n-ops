import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { NotificationsPage } from './NotificationsPage';

const API_BASE = 'http://localhost:4000/api/v1';

describe('NotificationsPage', () => {
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
      render(<NotificationsPage />);

      expect(screen.getByRole('heading', { level: 1, name: /notifications/i })).toBeInTheDocument();
    });

    it('should display the page description', async () => {
      render(<NotificationsPage />);

      expect(screen.getByText(/configure system alerts and notification channels/i)).toBeInTheDocument();
    });
  });

  describe('Notification Channels Section', () => {
    it('should display Notification Channels section', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText('Notification Channels')).toBeInTheDocument();
      });
    });

    it('should display Add Channel button', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /add channel/i })).toBeInTheDocument();
      });
    });

    it('should display Admin Email channel', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText('Admin Email')).toBeInTheDocument();
      });
    });

    it('should display Ops Slack Channel', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText('Ops Slack Channel')).toBeInTheDocument();
      });
    });

    it('should display PagerDuty Webhook channel', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText('PagerDuty Webhook')).toBeInTheDocument();
      });
    });

    it('should display channel type badges', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText('email')).toBeInTheDocument();
      });
      expect(screen.getByText('slack')).toBeInTheDocument();
      expect(screen.getByText('webhook')).toBeInTheDocument();
    });
  });

  describe('Notification Rules Section', () => {
    it('should display Notification Rules section', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText('Notification Rules')).toBeInTheDocument();
      });
    });

    it('should display Add Rule button', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /add rule/i })).toBeInTheDocument();
      });
    });

    it('should display Critical System Alerts rule', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText('Critical System Alerts')).toBeInTheDocument();
      });
    });

    it('should display New Tenant Registration rule', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText('New Tenant Registration')).toBeInTheDocument();
      });
    });

    it('should display High Error Rate Alert rule', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText('High Error Rate Alert')).toBeInTheDocument();
      });
    });
  });

  describe('Recent Notifications Section', () => {
    it('should display Recent Notifications section', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText('Recent Notifications')).toBeInTheDocument();
      });
    });

    it('should display recent notification description', async () => {
      render(<NotificationsPage />);

      await waitFor(() => {
        expect(screen.getByText(/log of recently sent and pending notifications/i)).toBeInTheDocument();
      });
    });
  });
});
