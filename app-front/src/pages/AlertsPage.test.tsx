import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { AlertsPage } from './AlertsPage';
import { render } from '@/test/test-utils';
import { server } from '@/test/mocks/server';

const API_BASE = 'http://localhost:4000/api/v1';

const mockChannels = {
  data: [
    {
      id: 'channel-1',
      name: 'Slack Alerts',
      type: 'slack',
      isEnabled: true,
      configJson: { webhook_url: 'https://hooks.slack.com/...' },
    },
    {
      id: 'channel-2',
      name: 'Email Notifications',
      type: 'email',
      isEnabled: false,
      configJson: { smtp_host: 'smtp.example.com' },
    },
  ],
};

const mockRules = {
  data: [
    {
      id: 'rule-1',
      eventType: 'workflow.execution.failed',
      channelIds: ['channel-1'],
      isEnabled: true,
    },
  ],
};

const mockEvents = {
  data: [
    {
      id: 'event-1',
      eventType: 'workflow.execution.failed',
      timestamp: new Date().toISOString(),
      notificationStatus: 'sent',
      channelsNotified: ['channel-1'],
    },
  ],
};

const mockCatalog = {
  data: [
    {
      eventType: 'workflow.execution.failed',
      displayName: 'Workflow Execution Failed',
      description: 'Triggered when a workflow execution fails',
      category: 'workflow',
    },
    {
      eventType: 'workflow.execution.success',
      displayName: 'Workflow Execution Success',
      description: 'Triggered when a workflow execution completes successfully',
      category: 'workflow',
    },
  ],
};

describe('AlertsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    server.use(
      http.get(`${API_BASE}/notifications/channels`, () => {
        return HttpResponse.json(mockChannels);
      }),
      http.get(`${API_BASE}/notifications/rules`, () => {
        return HttpResponse.json(mockRules);
      }),
      http.get(`${API_BASE}/notifications/events`, () => {
        return HttpResponse.json(mockEvents);
      }),
      http.get(`${API_BASE}/notifications/catalog`, () => {
        return HttpResponse.json(mockCatalog);
      }),
      http.get(`${API_BASE}/notifications/event-catalog`, () => {
        return HttpResponse.json(mockCatalog);
      })
    );
  });

  describe('Rendering', () => {
    it('should display page heading', async () => {
      render(<AlertsPage />);

      expect(screen.getByRole('heading', { level: 1, name: /alerts/i })).toBeInTheDocument();
    });

    it('should display notification channels section', async () => {
      render(<AlertsPage />);

      expect(screen.getByRole('heading', { name: /notification channels/i })).toBeInTheDocument();
    });

    it('should display notification rules section', async () => {
      render(<AlertsPage />);

      expect(screen.getByText(/notification rules/i)).toBeInTheDocument();
    });

    it('should display recent activity section', async () => {
      render(<AlertsPage />);

      expect(screen.getByText(/recent activity/i)).toBeInTheDocument();
    });

    it('should have refresh button', async () => {
      render(<AlertsPage />);

      expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
    });
  });

  describe('Notification Channels', () => {
    it('should display add channel button', async () => {
      render(<AlertsPage />);

      expect(screen.getByRole('button', { name: /add channel/i })).toBeInTheDocument();
    });

    it('should show channels section with loading or content', async () => {
      render(<AlertsPage />);

      // Page should either show channels or empty state
      await waitFor(() => {
        const hasChannels = screen.queryByText('Slack Alerts') !== null;
        const hasEmptyState = screen.queryByText(/no notification channels/i) !== null;
        expect(hasChannels || hasEmptyState).toBe(true);
      });
    });
  });

  describe('Notification Rules', () => {
    it('should display add rule button', async () => {
      render(<AlertsPage />);

      expect(screen.getByRole('button', { name: /add rule/i })).toBeInTheDocument();
    });

    it('should show rules section with loading or content', async () => {
      render(<AlertsPage />);

      // Page should either show rules or empty state
      await waitFor(() => {
        const hasRules = screen.queryByText(/workflow.*failed/i) !== null;
        const hasEmptyState = screen.queryByText(/no notification rules/i) !== null;
        expect(hasRules || hasEmptyState).toBe(true);
      });
    });
  });

  describe('Create Channel Dialog', () => {
    it('should open create channel dialog when clicking add channel', async () => {
      render(<AlertsPage />);

      const addButton = screen.getByRole('button', { name: /add channel/i });
      await userEvent.click(addButton);

      await waitFor(() => {
        expect(screen.getByText(/add notification channel/i)).toBeInTheDocument();
      });
    });

    it('should show channel type tabs in dialog', async () => {
      render(<AlertsPage />);

      const addButton = screen.getByRole('button', { name: /add channel/i });
      await userEvent.click(addButton);

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /slack/i })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: /email/i })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: /webhook/i })).toBeInTheDocument();
      });
    });
  });

  describe('Empty States', () => {
    it('should show empty state for channels when none exist', async () => {
      server.use(
        http.get(`${API_BASE}/notifications/channels`, () => {
          return HttpResponse.json({ data: [] });
        })
      );

      render(<AlertsPage />);

      await waitFor(() => {
        expect(screen.getByText(/no notification channels configured/i)).toBeInTheDocument();
      });
    });

    it('should show empty state for rules when none exist', async () => {
      server.use(
        http.get(`${API_BASE}/notifications/rules`, () => {
          return HttpResponse.json({ data: [] });
        })
      );

      render(<AlertsPage />);

      await waitFor(() => {
        expect(screen.getByText(/no notification rules configured/i)).toBeInTheDocument();
      });
    });

    it('should show empty state for events when none exist', async () => {
      server.use(
        http.get(`${API_BASE}/notifications/events`, () => {
          return HttpResponse.json({ data: [] });
        })
      );

      render(<AlertsPage />);

      await waitFor(() => {
        expect(screen.getByText(/no recent events/i)).toBeInTheDocument();
      });
    });
  });

  describe('Actions', () => {
    it('should have action buttons', async () => {
      render(<AlertsPage />);

      // Page should have action buttons (add, refresh, etc.)
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(2);
    });
  });
});
