import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { N8NUsersPage } from './N8NUsersPage';
import { render } from '@/test/test-utils';
import { server } from '@/test/mocks/server';

const API_BASE = 'http://localhost:4000/api/v1';

// API returns array directly, api-client wraps it with { data: ... }
const mockN8NUsers = [
  {
    id: 'n8n-user-1',
    email: 'admin@example.com',
    first_name: 'Admin',
    last_name: 'User',
    role: 'owner',
    is_pending: false,
    environment: { id: 'env-1', name: 'Development', type: 'dev' },
    last_synced_at: '2024-01-15T10:00:00Z',
  },
  {
    id: 'n8n-user-2',
    email: 'developer@example.com',
    first_name: 'Developer',
    last_name: 'User',
    role: 'member',
    is_pending: false,
    environment: { id: 'env-2', name: 'Staging', type: 'staging' },
    last_synced_at: '2024-01-14T10:00:00Z',
  },
  {
    id: 'n8n-user-3',
    email: 'pending@example.com',
    first_name: 'Pending',
    last_name: 'User',
    role: 'member',
    is_pending: true,
    environment: { id: 'env-1', name: 'Development', type: 'dev' },
    last_synced_at: '2024-01-13T10:00:00Z',
  },
];

// API returns array directly for environments
const mockEnvironments = [
  { id: 'env-1', name: 'Development', type: 'dev' },
  { id: 'env-2', name: 'Staging', type: 'staging' },
];

describe('N8NUsersPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    server.use(
      http.get(`${API_BASE}/n8n-users`, () => {
        return HttpResponse.json(mockN8NUsers);
      }),
      http.get(`${API_BASE}/n8n-users/`, () => {
        return HttpResponse.json(mockN8NUsers);
      }),
      http.get(`${API_BASE}/environments`, () => {
        return HttpResponse.json(mockEnvironments);
      })
    );
  });

  describe('Loading State', () => {
    it('should show loading state initially', async () => {
      server.use(
        http.get(`${API_BASE}/n8n-users`, async () => {
          await new Promise((r) => setTimeout(r, 100));
          return HttpResponse.json(mockN8NUsers);
        }),
        http.get(`${API_BASE}/n8n-users/`, async () => {
          await new Promise((r) => setTimeout(r, 100));
          return HttpResponse.json(mockN8NUsers);
        })
      );

      render(<N8NUsersPage />);

      expect(screen.getByText(/loading n8n users/i)).toBeInTheDocument();
    });
  });

  describe('Success State', () => {
    it('should display page heading', async () => {
      render(<N8NUsersPage />);

      expect(screen.getByRole('heading', { level: 1, name: /n8n users/i })).toBeInTheDocument();
    });

    it('should display users after loading', async () => {
      render(<N8NUsersPage />);

      await waitFor(() => {
        expect(screen.getByText('admin@example.com')).toBeInTheDocument();
      });

      expect(screen.getByText('developer@example.com')).toBeInTheDocument();
      expect(screen.getByText('pending@example.com')).toBeInTheDocument();
    });

    it('should display user table with correct headers', async () => {
      render(<N8NUsersPage />);

      await waitFor(() => {
        expect(screen.getByText('admin@example.com')).toBeInTheDocument();
      });

      expect(screen.getByRole('columnheader', { name: /email/i })).toBeInTheDocument();
      expect(screen.getByRole('columnheader', { name: /name/i })).toBeInTheDocument();
      expect(screen.getByRole('columnheader', { name: /role/i })).toBeInTheDocument();
      expect(screen.getByRole('columnheader', { name: /status/i })).toBeInTheDocument();
    });

    it('should display user stats cards', async () => {
      render(<N8NUsersPage />);

      await waitFor(() => {
        expect(screen.getByText('admin@example.com')).toBeInTheDocument();
      });

      expect(screen.getByText('Total Users')).toBeInTheDocument();
      expect(screen.getByText('Active Users')).toBeInTheDocument();
      expect(screen.getByText('Pending Users')).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('should show empty state when no users exist', async () => {
      server.use(
        http.get(`${API_BASE}/n8n-users`, () => {
          return HttpResponse.json([]);
        }),
        http.get(`${API_BASE}/n8n-users/`, () => {
          return HttpResponse.json([]);
        })
      );

      render(<N8NUsersPage />);

      await waitFor(() => {
        expect(screen.getByText(/no n8n users found/i)).toBeInTheDocument();
      });
    });
  });

  describe('Filtering', () => {
    it('should filter users by search query', async () => {
      render(<N8NUsersPage />);

      await waitFor(() => {
        expect(screen.getByText('admin@example.com')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText(/search/i);
      await userEvent.type(searchInput, 'admin');

      await waitFor(() => {
        expect(screen.getByText('admin@example.com')).toBeInTheDocument();
        expect(screen.queryByText('developer@example.com')).not.toBeInTheDocument();
      });
    });

    it('should show no results when filter matches nothing', async () => {
      render(<N8NUsersPage />);

      await waitFor(() => {
        expect(screen.getByText('admin@example.com')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText(/search/i);
      await userEvent.type(searchInput, 'nonexistent user xyz');

      await waitFor(() => {
        expect(screen.getByText(/no users match/i)).toBeInTheDocument();
      });
    });
  });

  describe('Action Buttons', () => {
    it('should have refresh button', async () => {
      render(<N8NUsersPage />);

      expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
    });

    it('should have sync from N8N button', async () => {
      render(<N8NUsersPage />);

      expect(screen.getByRole('button', { name: /sync from n8n/i })).toBeInTheDocument();
    });
  });

  describe('Role Filtering', () => {
    it('should have role filter dropdown', async () => {
      render(<N8NUsersPage />);

      await waitFor(() => {
        expect(screen.getByText('admin@example.com')).toBeInTheDocument();
      });

      expect(screen.getByDisplayValue('All Roles')).toBeInTheDocument();
    });
  });

  describe('Status Filtering', () => {
    it('should have status filter dropdown', async () => {
      render(<N8NUsersPage />);

      await waitFor(() => {
        expect(screen.getByText('admin@example.com')).toBeInTheDocument();
      });

      expect(screen.getByDisplayValue('All Status')).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('should handle API error gracefully', async () => {
      server.use(
        http.get(`${API_BASE}/n8n-users`, () => {
          return new HttpResponse(JSON.stringify({ detail: 'Server error' }), {
            status: 500,
          });
        })
      );

      render(<N8NUsersPage />);

      await waitFor(
        () => {
          expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });
  });
});
