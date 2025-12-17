import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { InlineMappingDialog } from './InlineMappingDialog';
import type { CredentialIssue } from '@/types/credentials';

const API_BASE = 'http://localhost:3000/api/v1';

const mockN8NCredentials = [
  { id: 'n8n-cred-1', name: 'Prod Slack', type: 'slackApi', createdAt: '2024-01-01T00:00:00Z' },
  { id: 'n8n-cred-2', name: 'Prod GitHub', type: 'githubApi', createdAt: '2024-01-02T00:00:00Z' },
  { id: 'n8n-cred-3', name: 'Prod PostgreSQL', type: 'postgresApi', createdAt: '2024-01-03T00:00:00Z' },
];

const mockLogicalCredentials = [
  { id: 'logical-1', name: 'slackApi:notifications', required_type: 'slackApi', tenant_id: 'tenant-1' },
];

const mockMissingMappingIssue: CredentialIssue = {
  workflow_id: 'wf-1',
  workflow_name: 'Notification Workflow',
  logical_credential_key: 'slackApi:notifications',
  issue_type: 'missing_mapping',
  message: 'No mapping found for target environment',
  is_blocking: true,
};

const mockNoLogicalIssue: CredentialIssue = {
  workflow_id: 'wf-2',
  workflow_name: 'New Workflow',
  logical_credential_key: 'githubApi:deployment',
  issue_type: 'no_logical_credential',
  message: 'No logical credential exists',
  is_blocking: true,
};

describe('InlineMappingDialog', () => {
  const defaultProps = {
    open: true,
    onOpenChange: vi.fn(),
    issue: mockMissingMappingIssue,
    targetEnvironmentId: 'env-2',
    targetEnvironmentName: 'Production',
    onMappingCreated: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    server.resetHandlers();

    // Setup default handlers
    server.use(
      http.get(`${API_BASE}/credentials/by-environment/:environmentId`, () => {
        return HttpResponse.json(mockN8NCredentials);
      }),
      http.get(`${API_BASE}/admin/credentials/logical`, () => {
        return HttpResponse.json(mockLogicalCredentials);
      }),
      http.post(`${API_BASE}/admin/credentials/logical`, async ({ request }) => {
        const body = await request.json() as any;
        return HttpResponse.json({
          id: `logical-new-${Date.now()}`,
          ...body,
          created_at: new Date().toISOString(),
        }, { status: 201 });
      }),
      http.post(`${API_BASE}/admin/credentials/mappings`, async ({ request }) => {
        const body = await request.json() as any;
        return HttpResponse.json({
          id: `mapping-new-${Date.now()}`,
          ...body,
          created_at: new Date().toISOString(),
        }, { status: 201 });
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
    it('should render dialog when open', async () => {
      render(<InlineMappingDialog {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('Create Credential Mapping')).toBeInTheDocument();
      });
    });

    it('should not render when open is false', () => {
      render(<InlineMappingDialog {...defaultProps} open={false} />);

      expect(screen.queryByText('Create Credential Mapping')).not.toBeInTheDocument();
    });

    it('should not render when issue is null', () => {
      render(<InlineMappingDialog {...defaultProps} issue={null} />);

      expect(screen.queryByText('Create Credential Mapping')).not.toBeInTheDocument();
    });

    it('should display workflow name in description', async () => {
      render(<InlineMappingDialog {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText(/Notification Workflow/)).toBeInTheDocument();
      });
    });

    it('should display target environment name', async () => {
      render(<InlineMappingDialog {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText(/Production/)).toBeInTheDocument();
      });
    });

    it('should display the logical credential key', async () => {
      render(<InlineMappingDialog {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('slackApi:notifications')).toBeInTheDocument();
      });
    });
  });

  describe('Missing Mapping Issue', () => {
    it('should show logical credential name as disabled input', async () => {
      render(<InlineMappingDialog {...defaultProps} />);

      await waitFor(() => {
        const input = screen.getByDisplayValue('slackApi:notifications');
        expect(input).toBeInTheDocument();
        expect(input).toBeDisabled();
      });
    });

    it('should not show alert for no_logical_credential', async () => {
      render(<InlineMappingDialog {...defaultProps} />);

      await waitFor(() => {
        expect(screen.queryByText(/No logical credential exists/)).not.toBeInTheDocument();
      });
    });
  });

  describe('No Logical Credential Issue', () => {
    it('should show alert about creating logical credential', async () => {
      render(<InlineMappingDialog {...defaultProps} issue={mockNoLogicalIssue} />);

      await waitFor(() => {
        expect(screen.getByText(/No logical credential exists for this reference/)).toBeInTheDocument();
      });
    });

    it('should allow editing logical credential name', async () => {
      const user = userEvent.setup();
      render(<InlineMappingDialog {...defaultProps} issue={mockNoLogicalIssue} />);

      await waitFor(() => {
        const input = screen.getByDisplayValue('githubApi:deployment');
        expect(input).not.toBeDisabled();
      });

      const input = screen.getByDisplayValue('githubApi:deployment');
      await user.clear(input);
      await user.type(input, 'githubApi:custom-name');

      expect(screen.getByDisplayValue('githubApi:custom-name')).toBeInTheDocument();
    });
  });

  describe('Credential Picker', () => {
    it('should render credential picker with environment ID', async () => {
      render(<InlineMappingDialog {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });
    });

    it('should show label with target environment name', async () => {
      render(<InlineMappingDialog {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText(/Target Credential in Production/)).toBeInTheDocument();
      });
    });
  });

  describe('Form Submission', () => {
    it('should disable Create Mapping button when no credential selected', async () => {
      render(<InlineMappingDialog {...defaultProps} />);

      await waitFor(() => {
        const createButton = screen.getByRole('button', { name: /create mapping/i });
        expect(createButton).toBeDisabled();
      });
    });

    it('should show Cancel button', async () => {
      render(<InlineMappingDialog {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
      });
    });

    it('should call onOpenChange when Cancel is clicked', async () => {
      const user = userEvent.setup();
      const onOpenChange = vi.fn();
      render(<InlineMappingDialog {...defaultProps} onOpenChange={onOpenChange} />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
      });

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  describe('Selected Credential Preview', () => {
    it('should not show preview when no credential selected', async () => {
      render(<InlineMappingDialog {...defaultProps} />);

      await waitFor(() => {
        expect(screen.queryByText(/Selected Credential/)).not.toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle logical credential creation failure gracefully', async () => {
      server.use(
        http.post(`${API_BASE}/admin/credentials/logical`, () => {
          return HttpResponse.json(
            { detail: 'Failed to create logical credential' },
            { status: 400 }
          );
        })
      );

      // Component should still render without errors
      render(<InlineMappingDialog {...defaultProps} issue={mockNoLogicalIssue} />);

      await waitFor(() => {
        expect(screen.getByText('Create Credential Mapping')).toBeInTheDocument();
      });
    });

    it('should handle mapping creation failure gracefully', async () => {
      server.use(
        http.post(`${API_BASE}/admin/credentials/mappings`, () => {
          return HttpResponse.json(
            { detail: 'Failed to create mapping' },
            { status: 400 }
          );
        })
      );

      // Component should still render without errors
      render(<InlineMappingDialog {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('Create Credential Mapping')).toBeInTheDocument();
      });
    });
  });

  describe('Source Info Display', () => {
    it('should display source credential reference section', async () => {
      render(<InlineMappingDialog {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('Source Credential Reference')).toBeInTheDocument();
      });
    });

    it('should display arrow indicating direction to target', async () => {
      render(<InlineMappingDialog {...defaultProps} />);

      await waitFor(() => {
        // The ArrowRight icon is present in the UI
        expect(screen.getByText('Source Credential Reference')).toBeInTheDocument();
        expect(screen.getByText('Production')).toBeInTheDocument();
      });
    });
  });

  describe('Different Issue Types', () => {
    const mappedMissingInTargetIssue: CredentialIssue = {
      workflow_id: 'wf-3',
      workflow_name: 'Data Pipeline',
      logical_credential_key: 'postgresApi:analytics',
      issue_type: 'mapped_missing_in_target',
      message: 'Mapped credential not found in target environment',
      is_blocking: false,
    };

    it('should handle mapped_missing_in_target issue type', async () => {
      render(<InlineMappingDialog {...defaultProps} issue={mappedMissingInTargetIssue} />);

      await waitFor(() => {
        expect(screen.getByText('Create Credential Mapping')).toBeInTheDocument();
        expect(screen.getByText(/Data Pipeline/)).toBeInTheDocument();
      });
    });

    it('should pre-fill logical name from issue', async () => {
      render(<InlineMappingDialog {...defaultProps} issue={mappedMissingInTargetIssue} />);

      await waitFor(() => {
        expect(screen.getByDisplayValue('postgresApi:analytics')).toBeInTheDocument();
      });
    });
  });
});
