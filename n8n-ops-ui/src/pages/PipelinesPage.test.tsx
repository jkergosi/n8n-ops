import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { PipelinesPage } from './PipelinesPage';

const API_BASE = 'http://localhost:4000/api/v1';

const mockEnvironments = [
  {
    id: 'env-1',
    tenant_id: 'tenant-1',
    n8n_name: 'Development',
    name: 'Development',
    n8n_type: 'development',
    type: 'development',
    is_active: true,
    workflow_count: 5,
  },
  {
    id: 'env-2',
    tenant_id: 'tenant-1',
    n8n_name: 'Production',
    name: 'Production',
    n8n_type: 'production',
    type: 'production',
    is_active: true,
    workflow_count: 12,
  },
];

const mockPipelines = [
  {
    id: 'pipeline-1',
    tenant_id: 'tenant-1',
    name: 'Dev to Prod Pipeline',
    description: 'Promote workflows from development to production',
    isActive: true,
    is_active: true,
    environmentIds: ['env-1', 'env-2'],
    environment_ids: ['env-1', 'env-2'],
    stages: [
      {
        source_environment_id: 'env-1',
        target_environment_id: 'env-2',
        gates: { require_clean_drift: true },
        approvals: { require_approval: true, approver_role: 'admin' },
      },
    ],
    createdAt: '2024-01-01T00:00:00Z',
    created_at: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-15T00:00:00Z',
    updated_at: '2024-01-15T00:00:00Z',
    lastModifiedAt: '2024-01-15T00:00:00Z',
  },
  {
    id: 'pipeline-2',
    tenant_id: 'tenant-1',
    name: 'Inactive Pipeline',
    description: 'A deactivated pipeline',
    isActive: false,
    is_active: false,
    environmentIds: ['env-1', 'env-2'],
    environment_ids: ['env-1', 'env-2'],
    stages: [],
    createdAt: '2024-01-02T00:00:00Z',
    created_at: '2024-01-02T00:00:00Z',
    updatedAt: '2024-01-16T00:00:00Z',
    updated_at: '2024-01-16T00:00:00Z',
    lastModifiedAt: '2024-01-16T00:00:00Z',
  },
];

describe('PipelinesPage', () => {
  beforeEach(() => {
    server.resetHandlers();

    server.use(
      http.get(`${API_BASE}/pipelines`, () => {
        return HttpResponse.json(mockPipelines);
      }),
      http.get(`${API_BASE}/environments`, () => {
        return HttpResponse.json(mockEnvironments);
      }),
      http.get(`${API_BASE}/auth/status`, () => {
        return HttpResponse.json({
          authenticated: true,
          onboarding_required: false,
          has_environment: true,
          user: { id: 'user-1', email: 'admin@test.com', name: 'Admin', role: 'admin' },
          tenant: { id: 'tenant-1', name: 'Test Org', subscription_tier: 'pro' },
          entitlements: {
            plan_name: 'pro',
            features: {
              max_environments: { enabled: true, limit: 10 },
              environment_promotion: { enabled: true },
            },
          },
        });
      })
    );
  });

  describe('Loading State', () => {
    it('should show loading message while fetching pipelines', async () => {
      server.use(
        http.get(`${API_BASE}/pipelines`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json(mockPipelines);
        })
      );

      render(<PipelinesPage />);

      expect(screen.getByText(/loading pipelines/i)).toBeInTheDocument();
    });
  });

  describe('Success State', () => {
    it('should display page heading', async () => {
      render(<PipelinesPage />);

      expect(screen.getByRole('heading', { level: 1, name: /pipelines/i })).toBeInTheDocument();
    });

    it('should display page description', async () => {
      render(<PipelinesPage />);

      expect(screen.getByText(/define promotion rules and workflows between environments/i)).toBeInTheDocument();
    });

    it('should display Create Pipeline button', async () => {
      render(<PipelinesPage />);

      expect(screen.getByRole('button', { name: /create pipeline/i })).toBeInTheDocument();
    });

    it('should display pipelines in the table', async () => {
      render(<PipelinesPage />);

      await waitFor(() => {
        expect(screen.getByText('Dev to Prod Pipeline')).toBeInTheDocument();
      });

      expect(screen.getByText('Inactive Pipeline')).toBeInTheDocument();
    });

    it('should display pipeline descriptions', async () => {
      render(<PipelinesPage />);

      await waitFor(() => {
        expect(screen.getByText(/promote workflows from development to production/i)).toBeInTheDocument();
      });
    });

    it('should display environment path for pipelines', async () => {
      render(<PipelinesPage />);

      await waitFor(() => {
        expect(screen.getByText('Dev to Prod Pipeline')).toBeInTheDocument();
      });

      // Should show "Development → Production"
      expect(screen.getAllByText(/development/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(/production/i).length).toBeGreaterThanOrEqual(1);
    });

    it('should display pipeline status badges', async () => {
      render(<PipelinesPage />);

      await waitFor(() => {
        expect(screen.getByText('Dev to Prod Pipeline')).toBeInTheDocument();
      });

      // Should have Active and Inactive badges
      const activeBadges = screen.getAllByText('Active');
      expect(activeBadges.length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('Inactive')).toBeInTheDocument();
    });

    it('should display Promotion Pipelines card title', async () => {
      render(<PipelinesPage />);

      await waitFor(() => {
        expect(screen.getByText('Promotion Pipelines')).toBeInTheDocument();
      });
    });
  });

  describe('Empty State', () => {
    it('should show empty state when no pipelines exist', async () => {
      server.use(
        http.get(`${API_BASE}/pipelines`, () => {
          return HttpResponse.json([]);
        })
      );

      render(<PipelinesPage />);

      await waitFor(() => {
        expect(screen.getByText(/no pipelines found/i)).toBeInTheDocument();
      });
    });

    it('should show Create Your First Pipeline button in empty state', async () => {
      server.use(
        http.get(`${API_BASE}/pipelines`, () => {
          return HttpResponse.json([]);
        })
      );

      render(<PipelinesPage />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /create your first pipeline/i })).toBeInTheDocument();
      });
    });
  });

  describe('User Interactions - Edit Pipeline', () => {
    it('should have Edit button for each pipeline', async () => {
      render(<PipelinesPage />);

      await waitFor(() => {
        expect(screen.getByText('Dev to Prod Pipeline')).toBeInTheDocument();
      });

      const editButtons = screen.getAllByRole('button', { name: /edit/i });
      expect(editButtons.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe('User Interactions - Duplicate Pipeline', () => {
    it('should have Duplicate button for each pipeline', async () => {
      render(<PipelinesPage />);

      await waitFor(() => {
        expect(screen.getByText('Dev to Prod Pipeline')).toBeInTheDocument();
      });

      const duplicateButtons = screen.getAllByRole('button', { name: /duplicate/i });
      expect(duplicateButtons.length).toBeGreaterThanOrEqual(2);
    });

    it('should duplicate pipeline when clicking Duplicate button', async () => {
      const user = userEvent.setup();
      let createCalled = false;

      server.use(
        http.post(`${API_BASE}/pipelines`, async () => {
          createCalled = true;
          return HttpResponse.json({
            id: 'pipeline-new',
            name: 'Dev to Prod Pipeline (Copy)',
            tenant_id: 'tenant-1',
            isActive: false,
            environmentIds: ['env-1', 'env-2'],
            stages: [],
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          }, { status: 201 });
        })
      );

      render(<PipelinesPage />);

      await waitFor(() => {
        expect(screen.getByText('Dev to Prod Pipeline')).toBeInTheDocument();
      });

      const duplicateButtons = screen.getAllByRole('button', { name: /duplicate/i });
      await user.click(duplicateButtons[0]);

      await waitFor(() => {
        expect(createCalled).toBe(true);
      });
    });
  });

  describe('User Interactions - Toggle Active State', () => {
    it('should have Activate/Deactivate button for each pipeline', async () => {
      render(<PipelinesPage />);

      await waitFor(() => {
        expect(screen.getByText('Dev to Prod Pipeline')).toBeInTheDocument();
      });

      // First pipeline is active, so should have Deactivate button
      expect(screen.getByText('Deactivate')).toBeInTheDocument();
      // Second pipeline is inactive, so should have Activate button
      expect(screen.getByText('Activate')).toBeInTheDocument();
    });

    it('should toggle pipeline active state when clicking toggle button', async () => {
      const user = userEvent.setup();
      let updateCalled = false;

      server.use(
        http.patch(`${API_BASE}/pipelines/:id`, async () => {
          updateCalled = true;
          return HttpResponse.json({
            ...mockPipelines[0],
            isActive: false,
          });
        })
      );

      render(<PipelinesPage />);

      await waitFor(() => {
        expect(screen.getByText('Dev to Prod Pipeline')).toBeInTheDocument();
      });

      const deactivateButton = screen.getByRole('button', { name: /deactivate/i });
      await user.click(deactivateButton);

      await waitFor(() => {
        expect(updateCalled).toBe(true);
      });
    });
  });

  describe('User Interactions - Delete Pipeline', () => {
    it('should have Delete button for each pipeline', async () => {
      render(<PipelinesPage />);

      await waitFor(() => {
        expect(screen.getByText('Dev to Prod Pipeline')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
      expect(deleteButtons.length).toBeGreaterThanOrEqual(2);
    });

    it('should open delete confirmation dialog', async () => {
      const user = userEvent.setup();
      render(<PipelinesPage />);

      await waitFor(() => {
        expect(screen.getByText('Dev to Prod Pipeline')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
      await user.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const dialog = screen.getByRole('dialog');
      expect(within(dialog).getByText(/delete pipeline/i)).toBeInTheDocument();
      expect(within(dialog).getByText(/cannot be undone/i)).toBeInTheDocument();
    });

    it('should delete pipeline when confirmed', async () => {
      const user = userEvent.setup();
      let deleteCalled = false;

      server.use(
        http.delete(`${API_BASE}/pipelines/:id`, () => {
          deleteCalled = true;
          return new HttpResponse(null, { status: 204 });
        })
      );

      render(<PipelinesPage />);

      await waitFor(() => {
        expect(screen.getByText('Dev to Prod Pipeline')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
      await user.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const confirmButton = screen.getByRole('button', { name: /yes, delete/i });
      await user.click(confirmButton);

      await waitFor(() => {
        expect(deleteCalled).toBe(true);
      });
    });

    it('should cancel deletion when clicking Cancel', async () => {
      const user = userEvent.setup();
      render(<PipelinesPage />);

      await waitFor(() => {
        expect(screen.getByText('Dev to Prod Pipeline')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
      await user.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });

      // Pipeline should still be in the list
      expect(screen.getByText('Dev to Prod Pipeline')).toBeInTheDocument();
    });
  });

  describe('Table Structure', () => {
    it('should display table with correct column headers', async () => {
      render(<PipelinesPage />);

      await waitFor(() => {
        expect(screen.getByText('Dev to Prod Pipeline')).toBeInTheDocument();
      });

      const table = screen.getByRole('table');
      expect(within(table).getByText('Pipeline Name')).toBeInTheDocument();
      expect(within(table).getByText('Environment Path')).toBeInTheDocument();
      expect(within(table).getByText('Status')).toBeInTheDocument();
      expect(within(table).getByText('Last Modified')).toBeInTheDocument();
      expect(within(table).getByText('Actions')).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('should handle server error gracefully', async () => {
      server.use(
        http.get(`${API_BASE}/pipelines`, () => {
          return new HttpResponse(JSON.stringify({ detail: 'Internal server error' }), {
            status: 500,
          });
        })
      );

      render(<PipelinesPage />);

      // Page should not crash
      await waitFor(() => {
        expect(screen.getByRole('heading', { level: 1, name: /pipelines/i })).toBeInTheDocument();
      });
    });
  });
});
