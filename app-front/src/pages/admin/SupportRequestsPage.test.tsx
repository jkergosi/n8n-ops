import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { SupportRequestsPage } from './SupportRequestsPage';

const API_BASE = '/api/v1';

describe('SupportRequestsPage (admin)', () => {
  beforeEach(() => {
    server.resetHandlers();
  });

  it('renders requests + attachments and opens signed download URL on View', async () => {
    const user = userEvent.setup();

    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null as any);

    server.use(
      http.get(`${API_BASE}/admin/support/requests`, () => {
        return HttpResponse.json({
          data: [
            {
              id: 'req-1',
              intent_kind: 'bug',
              jsm_request_key: 'SUP-999',
              created_at: '2026-01-01T00:00:00Z',
              created_by_email: 'admin@test.com',
              attachments: [
                {
                  id: 'att-1',
                  filename: 'screenshot.png',
                  content_type: 'image/png',
                  size_bytes: 2048,
                  created_at: '2026-01-01T00:00:00Z',
                },
              ],
            },
          ],
        });
      }),
      http.get(`${API_BASE}/admin/support/attachments/:attachmentId/download-url`, () => {
        return HttpResponse.json({ url: 'https://signed.example.com/download' });
      })
    );

    render(<SupportRequestsPage />, { initialRoute: '/admin/support/requests' });

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: /support requests/i })).toBeInTheDocument();
      expect(screen.getByText(/bug/i)).toBeInTheDocument();
      expect(screen.getByText(/SUP-999/i)).toBeInTheDocument();
      expect(screen.getByText(/screenshot\.png/i)).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /view/i }));

    await waitFor(() => {
      expect(openSpy).toHaveBeenCalledWith('https://signed.example.com/download', '_blank', 'noopener,noreferrer');
    });

    openSpy.mockRestore();
  });
});


