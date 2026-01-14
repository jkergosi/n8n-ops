import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { PerformancePage } from './PerformancePage';

const API_BASE = 'http://localhost:4000/api/v1';

describe('PerformancePage', () => {
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
      render(<PerformancePage />);

      expect(screen.getByRole('heading', { level: 1, name: /performance/i })).toBeInTheDocument();
    });

    it('should display the page description', async () => {
      render(<PerformancePage />);

      expect(screen.getByText(/monitor system health and api performance/i)).toBeInTheDocument();
    });
  });

  describe('System Health Cards', () => {
    it('should display CPU Usage card', async () => {
      render(<PerformancePage />);

      await waitFor(() => {
        expect(screen.getByText('CPU Usage')).toBeInTheDocument();
      });
    });

    it('should display Memory Usage card', async () => {
      render(<PerformancePage />);

      await waitFor(() => {
        expect(screen.getByText('Memory Usage')).toBeInTheDocument();
      });
    });

    it('should display API Latency card', async () => {
      render(<PerformancePage />);

      await waitFor(() => {
        expect(screen.getByText('API Latency (avg)')).toBeInTheDocument();
      });
    });

    it('should display Active Connections card', async () => {
      render(<PerformancePage />);

      await waitFor(() => {
        expect(screen.getByText('Active Connections')).toBeInTheDocument();
      });
    });
  });

  describe('API Endpoint Performance', () => {
    it('should display API Endpoint Performance section', async () => {
      render(<PerformancePage />);

      await waitFor(() => {
        expect(screen.getByText('API Endpoint Performance')).toBeInTheDocument();
      });
    });

    it('should display endpoint performance description', async () => {
      render(<PerformancePage />);

      await waitFor(() => {
        expect(screen.getByText(/response times and error rates by endpoint/i)).toBeInTheDocument();
      });
    });

    it('should display endpoint table headers', async () => {
      render(<PerformancePage />);

      await waitFor(() => {
        expect(screen.getByText('Endpoint')).toBeInTheDocument();
      });
      expect(screen.getByText('Method')).toBeInTheDocument();
      expect(screen.getByText('Avg Latency')).toBeInTheDocument();
      expect(screen.getByText('P95 Latency')).toBeInTheDocument();
      expect(screen.getByText('Req/min')).toBeInTheDocument();
      expect(screen.getByText('Error Rate')).toBeInTheDocument();
    });

    it('should display endpoint paths', async () => {
      render(<PerformancePage />);

      await waitFor(() => {
        expect(screen.getByText('/api/v1/workflows')).toBeInTheDocument();
      });
      expect(screen.getByText('/api/v1/environments/sync')).toBeInTheDocument();
      expect(screen.getByText('/api/v1/executions')).toBeInTheDocument();
    });

    it('should display HTTP method badges', async () => {
      render(<PerformancePage />);

      await waitFor(() => {
        expect(screen.getAllByText('GET').length).toBeGreaterThan(0);
      });
      expect(screen.getAllByText('POST').length).toBeGreaterThan(0);
    });
  });

  describe('Recent Alerts', () => {
    it('should display Recent Alerts section', async () => {
      render(<PerformancePage />);

      await waitFor(() => {
        expect(screen.getByText('Recent Alerts')).toBeInTheDocument();
      });
    });

    it('should display alerts description', async () => {
      render(<PerformancePage />);

      await waitFor(() => {
        expect(screen.getByText(/system notifications and events/i)).toBeInTheDocument();
      });
    });

    it('should display alert messages', async () => {
      render(<PerformancePage />);

      await waitFor(() => {
        expect(screen.getByText(/high memory usage detected/i)).toBeInTheDocument();
      });
    });
  });

  describe('Infrastructure Overview', () => {
    it('should display Infrastructure Overview section', async () => {
      render(<PerformancePage />);

      await waitFor(() => {
        expect(screen.getByText('Infrastructure Overview')).toBeInTheDocument();
      });
    });

    it('should display resource utilization description', async () => {
      render(<PerformancePage />);

      await waitFor(() => {
        expect(screen.getByText(/current system resource utilization/i)).toBeInTheDocument();
      });
    });

    it('should display Database Connections', async () => {
      render(<PerformancePage />);

      await waitFor(() => {
        expect(screen.getByText('Database Connections')).toBeInTheDocument();
      });
    });

    it('should display Redis Cache Usage', async () => {
      render(<PerformancePage />);

      await waitFor(() => {
        expect(screen.getByText('Redis Cache Usage')).toBeInTheDocument();
      });
    });

    it('should display File Storage', async () => {
      render(<PerformancePage />);

      await waitFor(() => {
        expect(screen.getByText('File Storage')).toBeInTheDocument();
      });
    });
  });
});
