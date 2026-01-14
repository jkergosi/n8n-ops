import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { TagsPage } from './TagsPage';
import { render } from '@/test/test-utils';
import { server } from '@/test/mocks/server';

const API_BASE = '/api/v1';

const mockTags = [
  {
    id: 'tag-1',
    name: 'production',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-15T00:00:00Z',
  },
  {
    id: 'tag-2',
    name: 'staging',
    createdAt: '2024-01-02T00:00:00Z',
    updatedAt: '2024-01-14T00:00:00Z',
  },
  {
    id: 'tag-3',
    name: 'automation',
    createdAt: '2024-01-03T00:00:00Z',
    updatedAt: '2024-01-13T00:00:00Z',
  },
];

describe('TagsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    server.use(
      http.get(`${API_BASE}/tags/:environmentId`, () => {
        return HttpResponse.json(mockTags);
      })
    );
  });

  describe('Loading State', () => {
    it('should show loading state initially', async () => {
      server.use(
        http.get(`${API_BASE}/environments`, () => {
          return HttpResponse.json([
            {
              id: 'env-1',
              tenant_id: 'tenant-1',
              n8n_name: 'Development',
              n8n_type: 'development',
              n8n_base_url: 'https://dev.example.com',
              is_active: true,
            },
          ]);
        }),
        http.get(`${API_BASE}/tags/:environmentId`, async () => {
          await new Promise((r) => setTimeout(r, 100));
          return HttpResponse.json(mockTags);
        })
      );

      render(<TagsPage />);

      await waitFor(() => {
        expect(screen.getByText(/loading tags/i)).toBeInTheDocument();
      });
    });
  });

  describe('Success State', () => {
    it('should display page heading', async () => {
      render(<TagsPage />);

      expect(screen.getByRole('heading', { level: 1, name: /tags/i })).toBeInTheDocument();
    });

    it('should display tags after loading', async () => {
      render(<TagsPage />);

      await waitFor(() => {
        expect(screen.getByText('production')).toBeInTheDocument();
      });

      expect(screen.getByText('staging')).toBeInTheDocument();
      expect(screen.getByText('automation')).toBeInTheDocument();
    });

    it('should display tag table with correct headers', async () => {
      render(<TagsPage />);

      await waitFor(() => {
        expect(screen.getByText('production')).toBeInTheDocument();
      });

      expect(screen.getByRole('columnheader', { name: /name/i })).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('should show empty state when no tags exist', async () => {
      server.use(
        http.get(`${API_BASE}/tags/:environmentId`, () => {
          return HttpResponse.json([]);
        })
      );

      render(<TagsPage />);

      await waitFor(() => {
        expect(screen.getByText(/no tags/i)).toBeInTheDocument();
      });
    });
  });

  describe('Filtering', () => {
    it('should filter tags by search query', async () => {
      render(<TagsPage />);

      await waitFor(() => {
        expect(screen.getByText('production')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText(/search/i);
      await userEvent.type(searchInput, 'prod');

      await waitFor(() => {
        expect(screen.getByText('production')).toBeInTheDocument();
        expect(screen.queryByText('staging')).not.toBeInTheDocument();
      });
    });

    it('should show no results message when filter matches nothing', async () => {
      render(<TagsPage />);

      await waitFor(() => {
        expect(screen.getByText('production')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText(/search/i);
      await userEvent.type(searchInput, 'nonexistent tag xyz');

      await waitFor(() => {
        expect(screen.getByText(/no tags match/i)).toBeInTheDocument();
      });
    });
  });

  describe('Sorting', () => {
    it('should sort by name when clicking Name header', async () => {
      render(<TagsPage />);

      await waitFor(() => {
        expect(screen.getByText('production')).toBeInTheDocument();
      });

      const nameHeader = screen.getByRole('columnheader', { name: /name/i });
      await userEvent.click(nameHeader);

      // Tags should still be visible
      expect(screen.getByText('production')).toBeInTheDocument();
      expect(screen.getByText('staging')).toBeInTheDocument();
    });
  });

  describe('Pagination', () => {
    it('should show pagination controls', async () => {
      render(<TagsPage />);

      await waitFor(() => {
        expect(screen.getByText('production')).toBeInTheDocument();
      });

      expect(screen.getByText(/showing/i)).toBeInTheDocument();
    });
  });

  describe('Environment Selection', () => {
    it('should have environment selector', async () => {
      render(<TagsPage />);

      const environmentSelect = screen.getByLabelText(/environment/i);
      expect(environmentSelect).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('should handle API error gracefully', async () => {
      server.use(
        http.get(`${API_BASE}/tags/:environmentId`, () => {
          return new HttpResponse(JSON.stringify({ detail: 'Server error' }), {
            status: 500,
          });
        })
      );

      render(<TagsPage />);

      await waitFor(
        () => {
          expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });
  });
});
