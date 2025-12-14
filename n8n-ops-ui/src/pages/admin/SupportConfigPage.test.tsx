import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SupportConfigPage } from './SupportConfigPage';
import { render } from '@/test/test-utils';

describe('SupportConfigPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should display page heading', async () => {
      render(<SupportConfigPage />);

      await waitFor(() => {
        expect(screen.getByRole('heading', { level: 1, name: /support configuration/i })).toBeInTheDocument();
      });
    });

    it('should display tabs', async () => {
      render(<SupportConfigPage />);

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /n8n integration/i })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: /jsm settings/i })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: /request types/i })).toBeInTheDocument();
      });
    });

    it('should display save button', async () => {
      render(<SupportConfigPage />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /save configuration/i })).toBeInTheDocument();
      });
    });
  });

  describe('n8n Integration Tab', () => {
    it('should display webhook URL field', async () => {
      render(<SupportConfigPage />);

      await waitFor(() => {
        expect(screen.getByLabelText(/webhook url/i)).toBeInTheDocument();
      });
    });

    it('should display test connection button', async () => {
      render(<SupportConfigPage />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /test connection/i })).toBeInTheDocument();
      });
    });

    it('should allow editing webhook URL', async () => {
      render(<SupportConfigPage />);

      await waitFor(() => {
        expect(screen.getByLabelText(/webhook url/i)).toBeInTheDocument();
      });

      const webhookInput = screen.getByLabelText(/webhook url/i);
      await userEvent.clear(webhookInput);
      await userEvent.type(webhookInput, 'https://new-webhook.example.com');

      expect(webhookInput).toHaveValue('https://new-webhook.example.com');
    });
  });

  describe('JSM Settings Tab', () => {
    it('should switch to JSM Settings tab', async () => {
      render(<SupportConfigPage />);

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /jsm settings/i })).toBeInTheDocument();
      });

      const jsmTab = screen.getByRole('tab', { name: /jsm settings/i });
      await userEvent.click(jsmTab);

      await waitFor(() => {
        expect(screen.getByLabelText(/customer portal url/i)).toBeInTheDocument();
      });
    });
  });

  describe('Request Types Tab', () => {
    it('should switch to Request Types tab', async () => {
      render(<SupportConfigPage />);

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /request types/i })).toBeInTheDocument();
      });

      const typesTab = screen.getByRole('tab', { name: /request types/i });
      await userEvent.click(typesTab);

      await waitFor(() => {
        expect(screen.getByLabelText(/bug report request type id/i)).toBeInTheDocument();
      });
    });

    it('should display all request type ID fields', async () => {
      render(<SupportConfigPage />);

      // Wait for tabs to be available first
      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /request types/i })).toBeInTheDocument();
      });

      const typesTab = screen.getByRole('tab', { name: /request types/i });
      await userEvent.click(typesTab);

      await waitFor(() => {
        expect(screen.getByLabelText(/bug report request type id/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/feature request type id/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/help \/ question request type id/i)).toBeInTheDocument();
      });
    });
  });

  describe('Test Connection', () => {
    it('should have test n8n connection button', async () => {
      render(<SupportConfigPage />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /test connection/i })).toBeInTheDocument();
      });
    });
  });

  describe('Save Configuration', () => {
    it('should save configuration when clicking save button', async () => {
      render(<SupportConfigPage />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /save configuration/i })).toBeInTheDocument();
      });

      const saveButton = screen.getByRole('button', { name: /save configuration/i });
      await userEvent.click(saveButton);

      // Should show success message after save
      await waitFor(() => {
        expect(screen.queryByText(/saved/i) || screen.queryByText(/success/i)).toBeInTheDocument();
      }, { timeout: 3000 });
    });
  });
});
