import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { NotificationsPage } from './NotificationsPage';

const API_BASE = '/api/v1';

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

  it('should render Alerts page shell', async () => {
    render(<NotificationsPage />);

    expect(screen.getByRole('heading', { level: 1, name: /alerts/i })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Notification Channels')).toBeInTheDocument();
    });
    expect(screen.getByText('Notification Rules')).toBeInTheDocument();
    expect(screen.getByText(/recent events/i)).toBeInTheDocument();
  });
});
