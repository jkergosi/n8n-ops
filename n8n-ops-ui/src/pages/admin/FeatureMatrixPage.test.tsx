import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { FeatureMatrixPage } from './FeatureMatrixPage';

const API_BASE = 'http://localhost:4000/api/v1';

describe('FeatureMatrixPage', () => {
  beforeEach(() => {
    server.resetHandlers();

    server.use(
      http.get(`${API_BASE}/admin/entitlements/features/matrix`, () => {
        return HttpResponse.json({
          features: [
            { key: 'max_environments', name: 'Environments', free: 1, pro: 3, agency: 10, enterprise: -1 },
            { key: 'max_workflows', name: 'Workflows', free: 10, pro: 100, agency: 500, enterprise: -1 },
            { key: 'max_users', name: 'Users', free: 2, pro: 10, agency: 50, enterprise: -1 },
          ],
          plans: [
            { id: 'free', name: 'Free', description: 'Get started for free' },
            { id: 'pro', name: 'Pro', description: 'For growing teams' },
            { id: 'agency', name: 'Agency', description: 'For agencies' },
            { id: 'enterprise', name: 'Enterprise', description: 'For large organizations' },
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
      render(<FeatureMatrixPage />);

      expect(screen.getByRole('heading', { level: 1, name: /feature matrix/i })).toBeInTheDocument();
    });

    it('should display the page description', async () => {
      render(<FeatureMatrixPage />);

      expect(screen.getByText(/manage feature limits and entitlements by plan/i)).toBeInTheDocument();
    });

    it('should display Tenant Overrides link', async () => {
      render(<FeatureMatrixPage />);

      expect(screen.getByRole('link', { name: /tenant overrides/i })).toBeInTheDocument();
    });

    it('should display Audit Log link', async () => {
      render(<FeatureMatrixPage />);

      expect(screen.getByRole('link', { name: /audit log/i })).toBeInTheDocument();
    });
  });

  describe('Feature Matrix Table', () => {
    it('should display table headers for all plans', async () => {
      render(<FeatureMatrixPage />);

      await waitFor(() => {
        expect(screen.getByText('Feature')).toBeInTheDocument();
      });
      expect(screen.getByText('Free')).toBeInTheDocument();
      expect(screen.getByText('Pro')).toBeInTheDocument();
      expect(screen.getByText('Agency')).toBeInTheDocument();
      expect(screen.getByText('Enterprise')).toBeInTheDocument();
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
          return HttpResponse.json({ features: [], plans: [] });
        })
      );

      render(<FeatureMatrixPage />);

      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });
  });
});
