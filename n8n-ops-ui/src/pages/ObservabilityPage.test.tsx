import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { ObservabilityPage } from './ObservabilityPage';
import { render } from '@/test/test-utils';
import { server } from '@/test/mocks/server';

const API_BASE = 'http://localhost:4000/api/v1';

const mockObservabilityData = {
  data: {
    kpiMetrics: {
      totalExecutions: 1000,
      successRate: 95.5,
      avgDurationMs: 5000,
      p95DurationMs: 15000,
      failureCount: 45,
      deltaExecutions: 10,
      deltaSuccessRate: 2.5,
    },
    workflowPerformance: [
      {
        workflowId: 'wf-1',
        workflowName: 'Test Workflow 1',
        executionCount: 500,
        successCount: 480,
        failureCount: 20,
        errorRate: 4.0,
      },
      {
        workflowId: 'wf-2',
        workflowName: 'Test Workflow 2',
        executionCount: 300,
        successCount: 270,
        failureCount: 30,
        errorRate: 10.0,
      },
    ],
    environmentHealth: [
      {
        environmentId: 'env-1',
        environmentName: 'Development',
        environmentType: 'dev',
        status: 'healthy',
        latencyMs: 150,
        uptimePercent: 99.9,
        activeWorkflows: 10,
        totalWorkflows: 12,
        driftState: 'in_sync',
      },
    ],
    promotionSyncStats: {
      promotionsTotal: 10,
      promotionsSuccess: 8,
      promotionsFailed: 2,
      snapshotsCreated: 15,
      driftCount: 1,
      recentDeployments: [
        {
          id: 'deploy-1',
          sourceEnvironmentName: 'Dev',
          targetEnvironmentName: 'Staging',
          status: 'success',
        },
      ],
    },
  },
};

describe('ObservabilityPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    server.use(
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

      render(<ObservabilityPage />);

      expect(screen.getByRole('status') || screen.getByText(/loading/i)).toBeTruthy();
    });
  });

  describe('Success State', () => {
    it('should display page heading', async () => {
      render(<ObservabilityPage />);

      expect(screen.getByRole('heading', { level: 1, name: /observability/i })).toBeInTheDocument();
    });

    it('should display time range selector', async () => {
      render(<ObservabilityPage />);

      expect(screen.getByText(/last 24 hours/i)).toBeInTheDocument();
    });

    it('should display refresh button', async () => {
      render(<ObservabilityPage />);

      expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
    });
  });

  describe('KPI Cards', () => {
    it('should display total executions card', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getByText(/total executions/i)).toBeInTheDocument();
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
        expect(screen.getByText(/avg duration/i)).toBeInTheDocument();
      });
    });

    it('should display failed executions card', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getByText(/failed executions/i)).toBeInTheDocument();
      });
    });
  });

  describe('Workflow Performance Section', () => {
    it('should display workflow performance section', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getByText(/workflow performance/i)).toBeInTheDocument();
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
        expect(screen.getByText(/by executions/i)).toBeInTheDocument();
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
        expect(screen.getByText('Development')).toBeInTheDocument();
      });
    });

    it('should show environment status badges', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getByText(/healthy/i)).toBeInTheDocument();
      });
    });
  });

  describe('Promotion & Sync Stats', () => {
    it('should display promotion section', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getByText(/promotion & sync/i)).toBeInTheDocument();
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

      const timeRangeSelect = screen.getByText(/last 24 hours/i);
      await userEvent.click(timeRangeSelect);

      await waitFor(() => {
        expect(screen.getByText(/last 7 days/i)).toBeInTheDocument();
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

      await waitFor(() => {
        expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
      });
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

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
      });
    });
  });
});
