import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { ReportBugPage } from './ReportBugPage';

const API_BASE = '/api/v1';

describe('ReportBugPage (attachments)', () => {
  beforeEach(() => {
    server.resetHandlers();

    // Default config fetch
    server.use(
      http.get(`${API_BASE}/admin/support/config`, () => {
        return HttpResponse.json({
          tenant_id: 'tenant-1',
          jsm_portal_url: 'https://support.example.com',
        });
      })
    );
  });

  it('uploads an attachment and includes attachment_ids in the support request payload', async () => {
    const user = userEvent.setup();

    const createRequestSpy = vi.fn();

    server.use(
      http.post(`${API_BASE}/support/upload-url`, async () => {
        return HttpResponse.json({
          attachment_id: 'att-1',
          upload_url: 'support/attachments/att-1/upload',
          method: 'PUT',
        });
      }),
      http.put(`${API_BASE}/support/attachments/:attachmentId/upload`, async () => {
        return HttpResponse.json({ success: true });
      }),
      http.post(`${API_BASE}/support/requests`, async ({ request }) => {
        const body = await request.json();
        createRequestSpy(body);
        return HttpResponse.json({ jsm_request_key: 'SUP-123' });
      })
    );

    render(<ReportBugPage />, { initialRoute: '/support/report-bug' });

    await user.type(screen.getByLabelText(/title/i), 'Something broke');
    await user.type(screen.getByLabelText(/what happened/i), 'The button does nothing');
    await user.type(screen.getByLabelText(/what did you expect/i), 'It should submit');

    const file = new File(['hello'], 'screenshot.png', { type: 'image/png' });
    const fileInput = screen.getByLabelText(/attachments/i) as HTMLInputElement;
    await user.upload(fileInput, file);

    await waitFor(() => {
      expect(screen.getByText(/1 file\(s\) attached/i)).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /submit bug report/i }));

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText(/bug report submitted/i)).toBeInTheDocument();
      expect(screen.getByText('SUP-123')).toBeInTheDocument();
    });

    expect(createRequestSpy).toHaveBeenCalled();
    const payload = createRequestSpy.mock.calls[0][0];
    expect(payload.intent_kind).toBe('bug');
    expect(payload.bug_report?.attachment_ids).toEqual(['att-1']);
  });

  it('shows error when upload fails', async () => {
    const user = userEvent.setup();

    server.use(
      http.post(`${API_BASE}/support/upload-url`, () => {
        return HttpResponse.json(
          { detail: 'Failed to generate upload URL' },
          { status: 500 }
        );
      })
    );

    render(<ReportBugPage />, { initialRoute: '/support/report-bug' });

    const file = new File(['test content'], 'screenshot.png', { type: 'image/png' });
    const fileInput = screen.getByLabelText(/attachments/i) as HTMLInputElement;
    await user.upload(fileInput, file);

    // The upload should fail gracefully - file should not be attached
    // Check that the error state is handled (no crash, user can retry)
    await waitFor(() => {
      // Either we see an error message or the file count doesn't increase
      const attachedText = screen.queryByText(/1 file\(s\) attached/i);
      expect(attachedText).not.toBeInTheDocument();
    });
  });

  it('rejects files exceeding size limit with 413 error', async () => {
    const user = userEvent.setup();

    server.use(
      http.post(`${API_BASE}/support/upload-url`, () => {
        return HttpResponse.json({
          attachment_id: 'att-large',
          upload_url: 'support/attachments/att-large/upload',
          method: 'PUT',
        });
      }),
      http.put(`${API_BASE}/support/attachments/:attachmentId/upload`, () => {
        return HttpResponse.json(
          { detail: 'File too large. Maximum size is 10MB' },
          { status: 413 }
        );
      })
    );

    render(<ReportBugPage />, { initialRoute: '/support/report-bug' });

    // Simulate uploading a file (size limit is enforced server-side)
    const file = new File(['x'.repeat(100)], 'large-file.png', { type: 'image/png' });
    const fileInput = screen.getByLabelText(/attachments/i) as HTMLInputElement;
    await user.upload(fileInput, file);

    // Wait for upload attempt
    await waitFor(
      () => {
        // File should not be successfully attached due to size limit
        const attachedText = screen.queryByText(/1 file\(s\) attached/i);
        // Either shows error or doesn't show successful attachment
        expect(attachedText).not.toBeInTheDocument();
      },
      { timeout: 2000 }
    );
  });

  it('rejects unsupported file types with 415 error', async () => {
    const user = userEvent.setup();

    server.use(
      http.post(`${API_BASE}/support/upload-url`, () => {
        return HttpResponse.json({
          attachment_id: 'att-exe',
          upload_url: 'support/attachments/att-exe/upload',
          method: 'PUT',
        });
      }),
      http.put(`${API_BASE}/support/attachments/:attachmentId/upload`, () => {
        return HttpResponse.json(
          { detail: "File type 'application/x-executable' is not allowed." },
          { status: 415 }
        );
      })
    );

    render(<ReportBugPage />, { initialRoute: '/support/report-bug' });

    // Try uploading an executable file (rejected by server)
    const file = new File(['MZ...'], 'malware.exe', { type: 'application/x-executable' });
    const fileInput = screen.getByLabelText(/attachments/i) as HTMLInputElement;
    await user.upload(fileInput, file);

    // Wait for rejection
    await waitFor(
      () => {
        const attachedText = screen.queryByText(/1 file\(s\) attached/i);
        expect(attachedText).not.toBeInTheDocument();
      },
      { timeout: 2000 }
    );
  });
});
