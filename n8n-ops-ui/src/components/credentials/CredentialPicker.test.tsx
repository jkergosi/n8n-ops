import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { CredentialPicker } from './CredentialPicker';

const API_BASE = 'http://localhost:4000/api/v1';

const mockN8NCredentials = [
  { id: 'n8n-cred-1', name: 'Dev Slack', type: 'slackApi', createdAt: '2024-01-01T00:00:00Z' },
  { id: 'n8n-cred-2', name: 'Dev GitHub', type: 'githubApi', createdAt: '2024-01-02T00:00:00Z' },
  { id: 'n8n-cred-3', name: 'Dev PostgreSQL', type: 'postgresApi', createdAt: '2024-01-03T00:00:00Z' },
];

describe('CredentialPicker', () => {
  beforeEach(() => {
    server.resetHandlers();

    server.use(
      http.get(`${API_BASE}/credentials/by-environment/:environmentId`, () => {
        return HttpResponse.json(mockN8NCredentials);
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
    it('should show "Select environment first" when no environmentId', async () => {
      const onChange = vi.fn();
      render(
        <CredentialPicker
          environmentId=""
          value=""
          onChange={onChange}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/select environment first/i)).toBeInTheDocument();
      });
    });

    it('should show loading state while fetching credentials', async () => {
      server.use(
        http.get(`${API_BASE}/credentials/by-environment/:environmentId`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json(mockN8NCredentials);
        })
      );

      const onChange = vi.fn();
      render(
        <CredentialPicker
          environmentId="env-1"
          value=""
          onChange={onChange}
        />
      );

      expect(screen.getByText(/loading credentials/i)).toBeInTheDocument();
    });

    it('should render placeholder when no value selected', async () => {
      const onChange = vi.fn();
      render(
        <CredentialPicker
          environmentId="env-1"
          value=""
          onChange={onChange}
          placeholder="Choose a credential"
        />
      );

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });
    });
  });

  describe('Credential Selection', () => {
    it('should display credentials in dropdown', async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();

      render(
        <CredentialPicker
          environmentId="env-1"
          value=""
          onChange={onChange}
        />
      );

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      const combobox = screen.getByRole('combobox');
      await user.click(combobox);

      await waitFor(() => {
        expect(screen.getByText('Dev Slack')).toBeInTheDocument();
        expect(screen.getByText('Dev GitHub')).toBeInTheDocument();
        expect(screen.getByText('Dev PostgreSQL')).toBeInTheDocument();
      });
    });

    it('should call onChange when credential is selected', async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();

      render(
        <CredentialPicker
          environmentId="env-1"
          value=""
          onChange={onChange}
        />
      );

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      const combobox = screen.getByRole('combobox');
      await user.click(combobox);

      await waitFor(() => {
        expect(screen.getByText('Dev Slack')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Dev Slack'));

      await waitFor(() => {
        expect(onChange).toHaveBeenCalledWith('n8n-cred-1', expect.objectContaining({
          id: 'n8n-cred-1',
          name: 'Dev Slack',
          type: 'slackApi',
        }));
      });
    });
  });

  describe('Filtering', () => {
    it('should filter credentials by type when filterType is provided', async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();

      render(
        <CredentialPicker
          environmentId="env-1"
          filterType="slackApi"
          value=""
          onChange={onChange}
        />
      );

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      const combobox = screen.getByRole('combobox');
      await user.click(combobox);

      await waitFor(() => {
        expect(screen.getByText('Dev Slack')).toBeInTheDocument();
      });

      // GitHub and PostgreSQL should not be visible due to filter
      expect(screen.queryByText('Dev GitHub')).not.toBeInTheDocument();
      expect(screen.queryByText('Dev PostgreSQL')).not.toBeInTheDocument();
    });

    it('should show search input in dropdown', async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();

      render(
        <CredentialPicker
          environmentId="env-1"
          value=""
          onChange={onChange}
        />
      );

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      const combobox = screen.getByRole('combobox');
      await user.click(combobox);

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search credentials/i)).toBeInTheDocument();
      });
    });
  });

  describe('Empty State', () => {
    it('should show empty message when no credentials in environment', async () => {
      server.use(
        http.get(`${API_BASE}/credentials/by-environment/:environmentId`, () => {
          return HttpResponse.json([]);
        })
      );

      const user = userEvent.setup();
      const onChange = vi.fn();

      render(
        <CredentialPicker
          environmentId="env-1"
          value=""
          onChange={onChange}
        />
      );

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      const combobox = screen.getByRole('combobox');
      await user.click(combobox);

      await waitFor(() => {
        expect(screen.getByText(/no credentials found/i)).toBeInTheDocument();
      });
    });
  });

  describe('Disabled State', () => {
    it('should be disabled when disabled prop is true', async () => {
      const onChange = vi.fn();

      render(
        <CredentialPicker
          environmentId="env-1"
          value=""
          onChange={onChange}
          disabled={true}
        />
      );

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      const combobox = screen.getByRole('combobox');
      expect(combobox).toBeDisabled();
    });
  });
});

import { vi } from 'vitest';
