import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { MappingHealthCheck } from './MappingHealthCheck';

const API_BASE = 'http://localhost:4000/api/v1';

const mockEnvironments = [
  { id: 'env-1', name: 'Development', type: 'development', n8n_name: 'Development', n8n_type: 'development' },
  { id: 'env-2', name: 'Production', type: 'production', n8n_name: 'Production', n8n_type: 'production' },
];

const mockValidationReport = {
  total: 5,
  valid: 3,
  invalid: 1,
  stale: 1,
  issues: [
    { mapping_id: 'mapping-4', logical_name: 'awsApi:s3-bucket', environment_id: 'env-2', environment_name: 'Production', issue: 'credential_not_found', message: 'Physical credential not found in N8N' },
    { mapping_id: 'mapping-5', logical_name: 'postgresApi:main-db', environment_id: 'env-1', environment_name: 'Development', issue: 'name_changed', message: "Credential name changed from 'Main DB' to 'Primary DB'" },
  ],
};

describe('MappingHealthCheck', () => {
  beforeEach(() => {
    server.resetHandlers();

    server.use(
      http.get(`${API_BASE}/environments`, () => {
        return HttpResponse.json(mockEnvironments);
      }),
      http.post(`${API_BASE}/admin/credentials/mappings/validate`, () => {
        return HttpResponse.json(mockValidationReport);
      }),
      http.get(`${API_BASE}/auth/status`, () => {
        return HttpResponse.json({
          authenticated: true,
          onboarding_required: false,
          has_environment: true,
          user: { id: 'user-1', email: 'admin@test.com', name: 'Admin', role: 'admin' },
          tenant: { id: 'tenant-1', name: 'Test Org', subscription_tier: 'pro' },
          entitlements: { plan_name: 'pro', features: {} },
        });
      })
    );
  });

  describe('Rendering', () => {
    it('should display the health check title', async () => {
      render(<MappingHealthCheck />);

      expect(screen.getByText('Mapping Health Check')).toBeInTheDocument();
    });

    it('should display environment filter', async () => {
      render(<MappingHealthCheck />);

      await waitFor(() => {
        expect(screen.getByText(/environment filter/i)).toBeInTheDocument();
      });
    });

    it('should display Validate Mappings button', async () => {
      render(<MappingHealthCheck />);

      expect(screen.getByRole('button', { name: /validate mappings/i })).toBeInTheDocument();
    });

    it('should show initial state with instructions', async () => {
      render(<MappingHealthCheck />);

      await waitFor(() => {
        expect(screen.getByText(/click.*validate mappings.*to check/i)).toBeInTheDocument();
      });
    });
  });

  describe('Validation Flow', () => {
    it('should show validation results after clicking validate', async () => {
      const user = userEvent.setup();
      render(<MappingHealthCheck />);

      const validateButton = screen.getByRole('button', { name: /validate mappings/i });
      await user.click(validateButton);

      await waitFor(() => {
        expect(screen.getByText('Total Mappings')).toBeInTheDocument();
        expect(screen.getByText('5')).toBeInTheDocument();
      });
    });

    it('should show summary cards with counts', async () => {
      const user = userEvent.setup();
      render(<MappingHealthCheck />);

      const validateButton = screen.getByRole('button', { name: /validate mappings/i });
      await user.click(validateButton);

      await waitFor(() => {
        expect(screen.getByText('Valid')).toBeInTheDocument();
        expect(screen.getByText('Invalid')).toBeInTheDocument();
        expect(screen.getByText('Stale')).toBeInTheDocument();
      });
    });

    it('should show issues table when there are issues', async () => {
      const user = userEvent.setup();
      render(<MappingHealthCheck />);

      const validateButton = screen.getByRole('button', { name: /validate mappings/i });
      await user.click(validateButton);

      await waitFor(() => {
        expect(screen.getByText('Issues Found')).toBeInTheDocument();
        expect(screen.getByText('awsApi:s3-bucket')).toBeInTheDocument();
        expect(screen.getByText('postgresApi:main-db')).toBeInTheDocument();
      });
    });

    it('should show issue type badges', async () => {
      const user = userEvent.setup();
      render(<MappingHealthCheck />);

      const validateButton = screen.getByRole('button', { name: /validate mappings/i });
      await user.click(validateButton);

      await waitFor(() => {
        expect(screen.getByText('Not Found')).toBeInTheDocument();
        expect(screen.getByText('Name Changed')).toBeInTheDocument();
      });
    });

    it('should show Fix button for each issue', async () => {
      const user = userEvent.setup();
      render(<MappingHealthCheck />);

      const validateButton = screen.getByRole('button', { name: /validate mappings/i });
      await user.click(validateButton);

      await waitFor(() => {
        const fixButtons = screen.getAllByRole('button', { name: /fix/i });
        expect(fixButtons.length).toBe(2);
      });
    });
  });

  describe('All Healthy State', () => {
    it('should show success message when all mappings are valid', async () => {
      server.use(
        http.post(`${API_BASE}/admin/credentials/mappings/validate`, () => {
          return HttpResponse.json({
            total: 5,
            valid: 5,
            invalid: 0,
            stale: 0,
            issues: [],
          });
        })
      );

      const user = userEvent.setup();
      render(<MappingHealthCheck />);

      const validateButton = screen.getByRole('button', { name: /validate mappings/i });
      await user.click(validateButton);

      await waitFor(() => {
        expect(screen.getByText(/all mappings are healthy/i)).toBeInTheDocument();
      });
    });
  });

  describe('Callbacks', () => {
    it('should call onFixMapping when Fix button is clicked', async () => {
      const onFixMapping = vi.fn();
      const user = userEvent.setup();

      render(<MappingHealthCheck onFixMapping={onFixMapping} />);

      const validateButton = screen.getByRole('button', { name: /validate mappings/i });
      await user.click(validateButton);

      await waitFor(() => {
        expect(screen.getAllByRole('button', { name: /fix/i }).length).toBeGreaterThan(0);
      });

      const fixButtons = screen.getAllByRole('button', { name: /fix/i });
      await user.click(fixButtons[0]);

      expect(onFixMapping).toHaveBeenCalledWith('mapping-4');
    });
  });
});

import { vi } from 'vitest';
