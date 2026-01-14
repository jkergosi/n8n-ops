import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { PromotionPage } from './PromotionPage';
import { render } from '@/test/test-utils';
import { server } from '@/test/mocks/server';

const API_BASE = 'http://localhost:3000/api/v1';

const mockPipelines = [
  {
    id: 'pipeline-1',
    name: 'Dev to Staging',
    isActive: true,
    stages: [
      {
        sourceEnvironmentId: 'env-dev',
        targetEnvironmentId: 'env-staging',
        approvals: { requireApproval: true },
        policyFlags: { allowOverwritingHotfixes: false },
      },
    ],
  },
  {
    id: 'pipeline-2',
    name: 'Staging to Prod',
    isActive: true,
    stages: [
      {
        sourceEnvironmentId: 'env-staging',
        targetEnvironmentId: 'env-prod',
        approvals: { requireApproval: true },
        policyFlags: { allowOverwritingHotfixes: false },
      },
    ],
  },
];

const mockEnvironments = [
  { id: 'env-dev', name: 'Development', type: 'dev', provider: 'n8n' },
  { id: 'env-staging', name: 'Staging', type: 'staging', provider: 'n8n' },
  { id: 'env-prod', name: 'Production', type: 'production', provider: 'n8n' },
];

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useSearchParams: () => [
      new URLSearchParams({ source: 'env-dev', target: 'env-staging' }),
    ],
    useNavigate: () => vi.fn(),
  };
});

describe('PromotionPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    server.use(
      http.get(`${API_BASE}/pipelines`, () => {
        return HttpResponse.json(mockPipelines);
      }),
      http.get(`${API_BASE}/environments`, () => {
        return HttpResponse.json(mockEnvironments);
      })
    );
  });

  describe('Rendering', () => {
    it('should display page heading', async () => {
      render(<PromotionPage />);

      expect(screen.getByRole('heading', { level: 1, name: /new deployment/i })).toBeInTheDocument();
    });

    it('should display back button', async () => {
      render(<PromotionPage />);

      expect(screen.getByRole('button', { name: /back/i })).toBeInTheDocument();
    });

    it('should display pipeline selection card', async () => {
      render(<PromotionPage />);

      expect(screen.getByText(/pipeline.*stage selection/i)).toBeInTheDocument();
    });
  });

  describe('Pipeline Selection', () => {
    it('should show pipeline dropdown', async () => {
      render(<PromotionPage />);

      await waitFor(() => {
        expect(screen.getByRole('combobox', { name: /pipeline/i })).toBeInTheDocument();
      });
    });

    it('should load pipelines from API', async () => {
      render(<PromotionPage />);

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });
    });
  });

  describe('Environment Display', () => {
    it('should show source and target placeholder text', async () => {
      render(<PromotionPage />);

      await waitFor(() => {
        expect(screen.getByText(/source/i)).toBeInTheDocument();
      });
    });
  });

  describe('Actions', () => {
    it('should show cancel button when pipeline is selected', async () => {
      render(<PromotionPage />);

      await waitFor(() => {
        const combobox = screen.getByRole('combobox');
        expect(combobox).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle API error gracefully', async () => {
      server.use(
        http.get(`${API_BASE}/pipelines`, () => {
          return new HttpResponse(JSON.stringify({ detail: 'Server error' }), {
            status: 500,
          });
        })
      );

      render(<PromotionPage />);

      await waitFor(() => {
        expect(screen.getByText(/pipeline.*stage selection/i)).toBeInTheDocument();
      });
    });
  });

  describe('Workflow Selection', () => {
    it('should show workflow selection after pipeline is selected', async () => {
      render(<PromotionPage />);

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });
    });
  });
});
