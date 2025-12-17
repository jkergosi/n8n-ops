import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { CredentialPicker } from './CredentialPicker';

const API_BASE = 'http://localhost:3000/api/v1';

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

    it('should render combobox when environment is provided', async () => {
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

    it('should render with placeholder text', async () => {
      const onChange = vi.fn();
      render(
        <CredentialPicker
          environmentId="env-1"
          value=""
          onChange={onChange}
          placeholder="Select credential..."
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Select credential...')).toBeInTheDocument();
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

    it('should be disabled when no environmentId', async () => {
      const onChange = vi.fn();
      render(
        <CredentialPicker
          environmentId=""
          value=""
          onChange={onChange}
        />
      );

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      const combobox = screen.getByRole('combobox');
      expect(combobox).toBeDisabled();
    });
  });

  describe('Selected Value Display', () => {
    it('should display selected credential name when value is set', async () => {
      const onChange = vi.fn();
      render(
        <CredentialPicker
          environmentId="env-1"
          value="n8n-cred-1"
          onChange={onChange}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Dev Slack')).toBeInTheDocument();
      });
    });

    it('should display credential type in parentheses', async () => {
      const onChange = vi.fn();
      render(
        <CredentialPicker
          environmentId="env-1"
          value="n8n-cred-1"
          onChange={onChange}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('(slackApi)')).toBeInTheDocument();
      });
    });
  });
});
