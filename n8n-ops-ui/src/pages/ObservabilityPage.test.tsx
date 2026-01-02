import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { ObservabilityPage } from './ObservabilityPage';
import { render } from '@/test/test-utils';
import { server } from '@/test/mocks/server';

const API_BASE = '/api/v1';

// NOTE: apiClient.getObservabilityOverview() expects *snake_case* from the backend and transforms to camelCase.
const mockObservabilityData = {
  system_status: {
    status: 'healthy',
    insights: [],
    failure_delta_percent: 2.5,
    failing_workflows_count: 1,
    sparkline: [],
  },
  kpi_metrics: {
    total_executions: 1000,
    success_rate: 95.5,
    avg_duration_ms: 5000,
    p95_duration_ms: 15000,
    failure_count: 45,
    delta_executions: 10,
    delta_success_rate: 2.5,
    sparkline_executions: [],
    sparkline_success_rate: [],
  },
  error_intelligence: {
    top_errors: [],
    anomaly_alerts: [],
  },
  workflow_performance: [
    {
      workflow_id: 'wf-1',
      workflow_name: 'Test Workflow 1',
      execution_count: 500,
      success_count: 480,
      failure_count: 20,
      error_rate: 4.0,
      avg_duration_ms: 4000,
      p95_duration_ms: 12000,
      sparkline_error_rate: [],
    },
    {
      workflow_id: 'wf-2',
      workflow_name: 'Test Workflow 2',
      execution_count: 300,
      success_count: 270,
      failure_count: 30,
      error_rate: 10.0,
      avg_duration_ms: 6000,
      p95_duration_ms: 16000,
      sparkline_error_rate: [],
    },
  ],
  environment_health: [
    {
      environment_id: 'env-1',
      environment_name: 'Development',
      environment_type: 'development',
      status: 'healthy',
      latency_ms: 150,
      uptime_percent: 99.9,
      active_workflows: 10,
      total_workflows: 12,
      drift_state: 'in_sync',
    },
  ],
  promotion_sync_stats: {
    promotions_total: 10,
    promotions_success: 8,
    promotions_failed: 2,
    snapshots_created: 15,
    drift_count: 1,
    recent_deployments: [
      {
        id: 'deploy-1',
        source_environment_name: 'Dev',
        target_environment_name: 'Staging',
        status: 'success',
      },
    ],
  },
};

describe('ObservabilityPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    server.use(
      http.get(`${API_BASE}/environments`, () => {
        return HttpResponse.json([
          {
            id: 'env-1',
            tenant_id: 'tenant-1',
            n8n_name: 'Development',
            n8n_type: 'development',
            n8n_base_url: 'https://dev.example.com',
            is_active: true,
          },
        ]);
      }),
      http.get(`${API_BASE}/observability/overview`, () => {
        return HttpResponse.json(mockObservabilityData);
      })
    );
  });

  describe('Loading State', () => {
    it('should show loading state initially', async () => {
      server.use(
        http.get(`${API_BASE}/observability/overview`, async () => {
          await new Promise((r) => setTimeout(r, 100));
          return HttpResponse.json(mockObservabilityData);
        })
      );

      const { container } = render(<ObservabilityPage />);

      // Spinner-only loading UI (no accessible "status" text yet)
      expect(container.querySelector('svg.animate-spin')).toBeTruthy();
    });
  });

  describe('Success State', () => {
    it('should display page heading', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getByRole('heading', { level: 1, name: /observability/i })).toBeInTheDocument();
      });
    });

    it('should display time range selector', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getAllByText(/last 24 hours/i).length).toBeGreaterThan(0);
      });
    });

    it('should display refresh button', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
      });
    });
  });

  describe('KPI Cards', () => {
    it('should display total executions card', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getByText(/executions/i)).toBeInTheDocument();
      });
    });

    it('should display success rate card', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getByText(/success rate/i)).toBeInTheDocument();
      });
    });

    it('should display average duration card', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getByText(/duration/i)).toBeInTheDocument();
      });
    });

    it('should display failed executions card', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getByText(/failures/i)).toBeInTheDocument();
      });
    });
  });

  describe('Workflow Performance Section', () => {
    it('should display workflow performance section', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getByText(/workflow risk table/i)).toBeInTheDocument();
      });
    });

    it('should display workflow data after loading', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getByText('Test Workflow 1')).toBeInTheDocument();
      });

      expect(screen.getByText('Test Workflow 2')).toBeInTheDocument();
    });

    it('should have sort selector', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getAllByText(/by risk/i).length).toBeGreaterThan(0);
      });
    });
  });

  describe('Environment Health Section', () => {
    it('should display environment health section', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getByText(/environment health/i)).toBeInTheDocument();
      });
    });

    it('should display environment health data', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getAllByText('Development').length).toBeGreaterThan(0);
      });
    });

    it('should show environment status badges', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getAllByText(/healthy/i).length).toBeGreaterThan(0);
      });
    });
  });

  describe('Promotion & Sync Stats', () => {
    it('should display promotion section', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getByText(/promotions & deployments/i)).toBeInTheDocument();
      });
    });

    it('should show recent deployments', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getByText(/recent deployments/i)).toBeInTheDocument();
      });
    });
  });

  describe('Time Range Selection', () => {
    it('should change time range when selected', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getByText(/active filters/i)).toBeInTheDocument();
      });

      const refreshButton = await screen.findByRole('button', { name: /refresh/i });
      const controls = refreshButton.parentElement;
      expect(controls).toBeTruthy();

      // Radix SelectTrigger renders as a combobox-like control; scope to the top-right controls row.
      const combos = (controls as HTMLElement).querySelectorAll('[role="combobox"]');
      expect(combos.length).toBeGreaterThan(0);
      const timeRangeSelect = combos[combos.length - 1] as HTMLElement;
      await userEvent.click(timeRangeSelect);

      const option = await screen.findByRole('option', { name: /last 7 days/i });
      await userEvent.click(option);

      await waitFor(() => {
        expect(screen.getAllByText(/last 7 days/i).length).toBeGreaterThan(0);
      });
    });
  });

  describe('Error State', () => {
    it('should handle API error gracefully', async () => {
      server.use(
        http.get(`${API_BASE}/observability/overview`, () => {
          return new HttpResponse(JSON.stringify({ detail: 'Server error' }), {
            status: 500,
          });
        })
      );

      render(<ObservabilityPage />);

      await waitFor(
        () => {
          expect(screen.getByText(/failed to load observability data/i)).toBeInTheDocument();
        },
        { timeout: 4000 }
      );
    });

    it('should have retry button on error', async () => {
      server.use(
        http.get(`${API_BASE}/observability/overview`, () => {
          return new HttpResponse(JSON.stringify({ detail: 'Server error' }), {
            status: 500,
          });
        })
      );

      render(<ObservabilityPage />);

      await waitFor(
        () => {
          expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
        },
        { timeout: 4000 }
      );
    });
  });
});
