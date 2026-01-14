import { describe, it, expect } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { BillingPage } from './BillingPage';

describe('BillingPage', () => {
  it('renders and loads billing overview', async () => {
    render(<BillingPage />);

    expect(screen.getByText(/loading billing information/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Billing & Subscription')).toBeInTheDocument();
    });

    // Plan name comes from MSW /billing/overview handler
    expect(screen.getByText('Pro')).toBeInTheDocument();
    expect(screen.getByText(/subscription overview/i)).toBeInTheDocument();
  });
});


