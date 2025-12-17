import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { CredentialDiscovery } from './CredentialDiscovery';

const API_BASE = 'http://localhost:4000/api/v1';

const mockEnvironments = [
  { id: 'env-1', name: 'Development', type: 'development', n8n_name: 'Development', n8n_type: 'development' },
  { id: 'env-2', name: 'Production', type: 'production', n8n_name: 'Production', n8n_type: 'production' },
];

const mockDiscoveredCredentials = [
  { type: 'slackApi', name: 'prod-slack', logical_key: 'slackApi:prod-slack', workflow_count: 3, workflows: [{ id: 'wf-1', name: 'Workflow 1' }], existing_logical_id: 'logical-1', mapping_status: 'mapped' },
  { type: 'githubApi', name: 'gh-token', logical_key: 'githubApi:gh-token', workflow_count: 2, workflows: [{ id: 'wf-2', name: 'Workflow 2' }], existing_logical_id: null, mapping_status: 'unmapped' },
];

describe('CredentialDiscovery', () => {
  beforeEach(() => {
    server.resetHandlers();

    server.use(
      http.get(`${API_BASE}/environments`, () => {
        return HttpResponse.json(mockEnvironments);
      }),
      http.post(`${API_BASE}/admin/credentials/discover/:environmentId`, () => {
        return HttpResponse.json(mockDiscoveredCredentials);
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
      }),
      http.post(`${API_BASE}/admin/credentials/logical`, async ({ request }) => {
        const body = await request.json();
        return HttpResponse.json({
          id: `logical-${Date.now()}`,
          ...body,
          created_at: new Date().toISOString(),
        }, { status: 201 });
      })
    );
  });

  describe('Rendering', () => {
    it('should display the credential discovery title', async () => {
      render(<CredentialDiscovery />);

      expect(screen.getByText('Credential Discovery')).toBeInTheDocument();
    });

    it('should display environment selector', async () => {
      render(<CredentialDiscovery />);

      await waitFor(() => {
        expect(screen.getByText(/environment to scan/i)).toBeInTheDocument();
      });
    });

    it('should display Scan Workflows button', async () => {
      render(<CredentialDiscovery />);

      expect(screen.getByRole('button', { name: /scan workflows/i })).toBeInTheDocument();
    });

    it('should show initial empty state', async () => {
      render(<CredentialDiscovery />);

      await waitFor(() => {
        expect(screen.getByText(/click.*scan workflows.*to discover/i)).toBeInTheDocument();
      });
    });
  });

  describe('Discovery Flow', () => {
    it('should show discovered credentials after scanning', async () => {
      const user = userEvent.setup();
      render(<CredentialDiscovery />);

      // Select environment
      const envSelect = screen.getByRole('combobox');
      await user.click(envSelect);

      await waitFor(() => {
        expect(screen.getByText(/development/i)).toBeInTheDocument();
      });

      await user.click(screen.getByText(/development/i));

      // Click scan button
      const scanButton = screen.getByRole('button', { name: /scan workflows/i });
      await user.click(scanButton);

      // Should show discovered credentials
      await waitFor(() => {
        expect(screen.getByText('prod-slack')).toBeInTheDocument();
        expect(screen.getByText('gh-token')).toBeInTheDocument();
      });
    });

    it('should show workflow count for discovered credentials', async () => {
      const user = userEvent.setup();
      render(<CredentialDiscovery />);

      // Select environment and scan
      const envSelect = screen.getByRole('combobox');
      await user.click(envSelect);
      await user.click(await screen.findByText(/development/i));

      const scanButton = screen.getByRole('button', { name: /scan workflows/i });
      await user.click(scanButton);

      await waitFor(() => {
        // Should show "3 workflows" for first credential
        expect(screen.getByText(/3 workflow/i)).toBeInTheDocument();
      });
    });

    it('should show Create button for credentials without logical definition', async () => {
      const user = userEvent.setup();
      render(<CredentialDiscovery />);

      // Select environment and scan
      const envSelect = screen.getByRole('combobox');
      await user.click(envSelect);
      await user.click(await screen.findByText(/development/i));

      const scanButton = screen.getByRole('button', { name: /scan workflows/i });
      await user.click(scanButton);

      await waitFor(() => {
        // Should show Create button for unmapped credential
        const createButtons = screen.getAllByRole('button', { name: /create/i });
        expect(createButtons.length).toBeGreaterThan(0);
      });
    });

    it('should show status badges for credentials', async () => {
      const user = userEvent.setup();
      render(<CredentialDiscovery />);

      // Select environment and scan
      const envSelect = screen.getByRole('combobox');
      await user.click(envSelect);
      await user.click(await screen.findByText(/development/i));

      const scanButton = screen.getByRole('button', { name: /scan workflows/i });
      await user.click(scanButton);

      await waitFor(() => {
        expect(screen.getByText('Mapped')).toBeInTheDocument();
      });
    });
  });

  describe('Button States', () => {
    it('should disable Scan button when no environment selected', async () => {
      render(<CredentialDiscovery />);

      const scanButton = screen.getByRole('button', { name: /scan workflows/i });
      expect(scanButton).toBeDisabled();
    });
  });
});
