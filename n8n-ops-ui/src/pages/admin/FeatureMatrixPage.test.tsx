import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { FeatureMatrixPage } from './FeatureMatrixPage';

const API_BASE = 'http://localhost:4000/api/v1';

const mockFeatureMatrix = {
  features: [
    {
      feature_id: 'feat-1',
      feature_key: 'max_environments',
      feature_display_name: 'Environments',
      feature_type: 'limit',
      description: 'Maximum environments allowed',
      status: 'active',
      plan_values: { Free: 1, Pro: 3, Agency: 10, Enterprise: -1 },
    },
    {
      feature_id: 'feat-2',
      feature_key: 'max_workflows',
      feature_display_name: 'Workflows',
      feature_type: 'limit',
      description: 'Maximum workflows allowed',
      status: 'active',
      plan_values: { Free: 10, Pro: 100, Agency: 500, Enterprise: -1 },
    },
    {
      feature_id: 'feat-3',
      feature_key: 'max_users',
      feature_display_name: 'Users',
      feature_type: 'limit',
      description: 'Maximum users allowed',
      status: 'active',
      plan_values: { Free: 2, Pro: 10, Agency: 50, Enterprise: -1 },
    },
  ],
  plans: [
    { id: 'free', name: 'Free', display_name: 'Free', description: 'Get started for free', sort_order: 1, is_active: true },
    { id: 'pro', name: 'Pro', display_name: 'Pro', description: 'For growing teams', sort_order: 2, is_active: true },
    { id: 'agency', name: 'Agency', display_name: 'Agency', description: 'For agencies', sort_order: 3, is_active: true },
    { id: 'enterprise', name: 'Enterprise', display_name: 'Enterprise', description: 'For large organizations', sort_order: 4, is_active: true },
  ],
  total_features: 3,
};

describe('FeatureMatrixPage', () => {
  beforeEach(() => {
    server.resetHandlers();

    server.use(
      http.get(`${API_BASE}/admin/entitlements/features/matrix`, () => {
        return HttpResponse.json(mockFeatureMatrix);
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
      render(<FeatureMatrixPage />);

      expect(screen.getByRole('heading', { level: 1, name: /feature matrix/i })).toBeInTheDocument();
    });

    it('should display the page description after loading', async () => {
      render(<FeatureMatrixPage />);

      await waitFor(() => {
        expect(screen.getByText(/manage feature entitlements across all plans/i)).toBeInTheDocument();
      });
    });

    it('should display Refresh button', async () => {
      render(<FeatureMatrixPage />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
      });
    });

    it('should display Clear Cache button', async () => {
      render(<FeatureMatrixPage />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /clear cache/i })).toBeInTheDocument();
      });
    });
  });

  describe('Feature Matrix Table', () => {
    it('should display table headers for all plans', async () => {
      render(<FeatureMatrixPage />);

      await waitFor(() => {
        expect(screen.getByText('Feature')).toBeInTheDocument();
      });
      expect(screen.getByText('Type')).toBeInTheDocument();
    });

    it('should display feature names', async () => {
      render(<FeatureMatrixPage />);

      await waitFor(() => {
        expect(screen.getByText('Environments')).toBeInTheDocument();
      });
      expect(screen.getByText('Workflows')).toBeInTheDocument();
      expect(screen.getByText('Users')).toBeInTheDocument();
    });
  });

  describe('Loading State', () => {
    it('should show loading state initially', async () => {
      server.use(
        http.get(`${API_BASE}/admin/entitlements/features/matrix`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json(mockFeatureMatrix);
        })
      );

      render(<FeatureMatrixPage />);

      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });
  });
});
