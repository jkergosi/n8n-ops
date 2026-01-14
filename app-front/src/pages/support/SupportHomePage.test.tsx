import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SupportHomePage } from './SupportHomePage';
import { render } from '@/test/test-utils';

// Mock window.open
const mockOpen = vi.fn();
Object.defineProperty(window, 'open', {
  value: mockOpen,
  writable: true,
});

describe('SupportHomePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should display page heading', async () => {
      render(<SupportHomePage />);

      expect(screen.getByRole('heading', { level: 1, name: /support/i })).toBeInTheDocument();
    });

    it('should display page description', async () => {
      render(<SupportHomePage />);

      expect(screen.getByText(/get help, report issues, or request new features/i)).toBeInTheDocument();
    });

    it('should display Report a Bug card', async () => {
      render(<SupportHomePage />);

      expect(screen.getByText('Report a Bug')).toBeInTheDocument();
      expect(screen.getByText(/something not working as expected/i)).toBeInTheDocument();
    });

    it('should display Request a Feature card', async () => {
      render(<SupportHomePage />);

      expect(screen.getByText('Request a Feature')).toBeInTheDocument();
      expect(screen.getByText(/have an idea for improvement/i)).toBeInTheDocument();
    });

    it('should display Get Help card', async () => {
      render(<SupportHomePage />);

      expect(screen.getByText('Get Help')).toBeInTheDocument();
      expect(screen.getByText(/need assistance or guidance/i)).toBeInTheDocument();
    });

    it('should display View my support requests button', async () => {
      render(<SupportHomePage />);

      expect(screen.getByRole('button', { name: /view my support requests/i })).toBeInTheDocument();
    });
  });

  describe('Navigation', () => {
    it('should have link to bug report page', async () => {
      render(<SupportHomePage />);

      const bugCard = screen.getByText('Report a Bug').closest('a');
      expect(bugCard).toHaveAttribute('href', '/support/bug/new');
    });

    it('should have link to feature request page', async () => {
      render(<SupportHomePage />);

      const featureCard = screen.getByText('Request a Feature').closest('a');
      expect(featureCard).toHaveAttribute('href', '/support/feature/new');
    });

    it('should have link to get help page', async () => {
      render(<SupportHomePage />);

      const helpCard = screen.getByText('Get Help').closest('a');
      expect(helpCard).toHaveAttribute('href', '/support/help/new');
    });
  });

  describe('External Links', () => {
    it('should open support portal when clicking View my support requests', async () => {
      render(<SupportHomePage />);

      const button = screen.getByRole('button', { name: /view my support requests/i });
      await userEvent.click(button);

      await waitFor(() => {
        expect(mockOpen).toHaveBeenCalledWith(expect.any(String), '_blank');
      });
    });
  });
});
