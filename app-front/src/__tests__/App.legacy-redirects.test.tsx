import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';
import {
  LegacyEnvironmentWorkflowsRedirect,
  LegacyEnvironmentDeploymentsRedirect,
  LegacyEnvironmentSnapshotsRedirect,
  LegacyEnvironmentExecutionsRedirect,
  LegacyEnvironmentActivityRedirect,
  LegacyEnvironmentCredentialsRedirect,
} from '../App';

// Component to display current location for testing
function LocationDisplay() {
  const location = useLocation();
  return (
    <div data-testid="location-display">
      {location.pathname}
      {location.search}
    </div>
  );
}

describe('Legacy Environment Route Redirects', () => {
  describe('LegacyEnvironmentWorkflowsRedirect', () => {
    it('redirects /environments/:id/workflows to /workflows?env_id=:id', async () => {
      const testEnvId = 'test-env-123';

      render(
        <MemoryRouter initialEntries={[`/environments/${testEnvId}/workflows`]}>
          <Routes>
            <Route path="/environments/:id/workflows" element={<LegacyEnvironmentWorkflowsRedirect />} />
            <Route path="/workflows" element={<LocationDisplay />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        const locationDisplay = screen.getByTestId('location-display');
        expect(locationDisplay.textContent).toBe(`/workflows?env_id=${testEnvId}`);
      });
    });

    it('redirects to /workflows without env_id if no id provided', async () => {
      render(
        <MemoryRouter initialEntries={['/environments//workflows']}>
          <Routes>
            <Route path="/environments/:id/workflows" element={<LegacyEnvironmentWorkflowsRedirect />} />
            <Route path="/workflows" element={<LocationDisplay />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        const locationDisplay = screen.getByTestId('location-display');
        expect(locationDisplay.textContent).toBe('/workflows');
      });
    });

    it('preserves UUID format env_ids', async () => {
      const uuidEnvId = '550e8400-e29b-41d4-a716-446655440000';

      render(
        <MemoryRouter initialEntries={[`/environments/${uuidEnvId}/workflows`]}>
          <Routes>
            <Route path="/environments/:id/workflows" element={<LegacyEnvironmentWorkflowsRedirect />} />
            <Route path="/workflows" element={<LocationDisplay />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        const locationDisplay = screen.getByTestId('location-display');
        expect(locationDisplay.textContent).toBe(`/workflows?env_id=${uuidEnvId}`);
      });
    });
  });

  describe('LegacyEnvironmentDeploymentsRedirect', () => {
    it('redirects /environments/:id/deployments to /deployments?env_id=:id', async () => {
      const testEnvId = 'test-env-456';

      render(
        <MemoryRouter initialEntries={[`/environments/${testEnvId}/deployments`]}>
          <Routes>
            <Route path="/environments/:id/deployments" element={<LegacyEnvironmentDeploymentsRedirect />} />
            <Route path="/deployments" element={<LocationDisplay />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        const locationDisplay = screen.getByTestId('location-display');
        expect(locationDisplay.textContent).toBe(`/deployments?env_id=${testEnvId}`);
      });
    });

    it('redirects to /deployments without env_id if no id provided', async () => {
      render(
        <MemoryRouter initialEntries={['/environments//deployments']}>
          <Routes>
            <Route path="/environments/:id/deployments" element={<LegacyEnvironmentDeploymentsRedirect />} />
            <Route path="/deployments" element={<LocationDisplay />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        const locationDisplay = screen.getByTestId('location-display');
        expect(locationDisplay.textContent).toBe('/deployments');
      });
    });
  });

  describe('LegacyEnvironmentSnapshotsRedirect', () => {
    it('redirects /environments/:id/snapshots to /snapshots?env_id=:id', async () => {
      const testEnvId = 'test-env-789';

      render(
        <MemoryRouter initialEntries={[`/environments/${testEnvId}/snapshots`]}>
          <Routes>
            <Route path="/environments/:id/snapshots" element={<LegacyEnvironmentSnapshotsRedirect />} />
            <Route path="/snapshots" element={<LocationDisplay />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        const locationDisplay = screen.getByTestId('location-display');
        expect(locationDisplay.textContent).toBe(`/snapshots?env_id=${testEnvId}`);
      });
    });

    it('redirects to /snapshots without env_id if no id provided', async () => {
      render(
        <MemoryRouter initialEntries={['/environments//snapshots']}>
          <Routes>
            <Route path="/environments/:id/snapshots" element={<LegacyEnvironmentSnapshotsRedirect />} />
            <Route path="/snapshots" element={<LocationDisplay />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        const locationDisplay = screen.getByTestId('location-display');
        expect(locationDisplay.textContent).toBe('/snapshots');
      });
    });
  });

  describe('LegacyEnvironmentExecutionsRedirect', () => {
    it('redirects /environments/:id/executions to /executions?env_id=:id', async () => {
      const testEnvId = 'test-env-abc';

      render(
        <MemoryRouter initialEntries={[`/environments/${testEnvId}/executions`]}>
          <Routes>
            <Route path="/environments/:id/executions" element={<LegacyEnvironmentExecutionsRedirect />} />
            <Route path="/executions" element={<LocationDisplay />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        const locationDisplay = screen.getByTestId('location-display');
        expect(locationDisplay.textContent).toBe(`/executions?env_id=${testEnvId}`);
      });
    });

    it('redirects to /executions without env_id if no id provided', async () => {
      render(
        <MemoryRouter initialEntries={['/environments//executions']}>
          <Routes>
            <Route path="/environments/:id/executions" element={<LegacyEnvironmentExecutionsRedirect />} />
            <Route path="/executions" element={<LocationDisplay />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        const locationDisplay = screen.getByTestId('location-display');
        expect(locationDisplay.textContent).toBe('/executions');
      });
    });
  });

  describe('LegacyEnvironmentActivityRedirect', () => {
    it('redirects /environments/:id/activity to /activity?env_id=:id', async () => {
      const testEnvId = 'test-env-def';

      render(
        <MemoryRouter initialEntries={[`/environments/${testEnvId}/activity`]}>
          <Routes>
            <Route path="/environments/:id/activity" element={<LegacyEnvironmentActivityRedirect />} />
            <Route path="/activity" element={<LocationDisplay />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        const locationDisplay = screen.getByTestId('location-display');
        expect(locationDisplay.textContent).toBe(`/activity?env_id=${testEnvId}`);
      });
    });

    it('redirects to /activity without env_id if no id provided', async () => {
      render(
        <MemoryRouter initialEntries={['/environments//activity']}>
          <Routes>
            <Route path="/environments/:id/activity" element={<LegacyEnvironmentActivityRedirect />} />
            <Route path="/activity" element={<LocationDisplay />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        const locationDisplay = screen.getByTestId('location-display');
        expect(locationDisplay.textContent).toBe('/activity');
      });
    });
  });

  describe('LegacyEnvironmentCredentialsRedirect', () => {
    it('redirects /environments/:id/credentials to /credentials?env_id=:id', async () => {
      const testEnvId = 'test-env-ghi';

      render(
        <MemoryRouter initialEntries={[`/environments/${testEnvId}/credentials`]}>
          <Routes>
            <Route path="/environments/:id/credentials" element={<LegacyEnvironmentCredentialsRedirect />} />
            <Route path="/credentials" element={<LocationDisplay />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        const locationDisplay = screen.getByTestId('location-display');
        expect(locationDisplay.textContent).toBe(`/credentials?env_id=${testEnvId}`);
      });
    });

    it('redirects to /credentials without env_id if no id provided', async () => {
      render(
        <MemoryRouter initialEntries={['/environments//credentials']}>
          <Routes>
            <Route path="/environments/:id/credentials" element={<LegacyEnvironmentCredentialsRedirect />} />
            <Route path="/credentials" element={<LocationDisplay />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        const locationDisplay = screen.getByTestId('location-display');
        expect(locationDisplay.textContent).toBe('/credentials');
      });
    });
  });

  describe('Special Characters and Edge Cases', () => {
    it('handles env_id with special characters correctly', async () => {
      const specialEnvId = 'env-with-dashes_and_underscores';

      render(
        <MemoryRouter initialEntries={[`/environments/${specialEnvId}/workflows`]}>
          <Routes>
            <Route path="/environments/:id/workflows" element={<LegacyEnvironmentWorkflowsRedirect />} />
            <Route path="/workflows" element={<LocationDisplay />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        const locationDisplay = screen.getByTestId('location-display');
        expect(locationDisplay.textContent).toBe(`/workflows?env_id=${specialEnvId}`);
      });
    });

    it('handles numeric env_id correctly', async () => {
      const numericEnvId = '12345';

      render(
        <MemoryRouter initialEntries={[`/environments/${numericEnvId}/deployments`]}>
          <Routes>
            <Route path="/environments/:id/deployments" element={<LegacyEnvironmentDeploymentsRedirect />} />
            <Route path="/deployments" element={<LocationDisplay />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        const locationDisplay = screen.getByTestId('location-display');
        expect(locationDisplay.textContent).toBe(`/deployments?env_id=${numericEnvId}`);
      });
    });
  });

  describe('All Redirect Components Together', () => {
    it('redirects all legacy environment routes correctly', async () => {
      const testEnvId = 'production-env';

      const routes = [
        { from: `/environments/${testEnvId}/workflows`, to: `/workflows?env_id=${testEnvId}` },
        { from: `/environments/${testEnvId}/deployments`, to: `/deployments?env_id=${testEnvId}` },
        { from: `/environments/${testEnvId}/snapshots`, to: `/snapshots?env_id=${testEnvId}` },
        { from: `/environments/${testEnvId}/executions`, to: `/executions?env_id=${testEnvId}` },
        { from: `/environments/${testEnvId}/activity`, to: `/activity?env_id=${testEnvId}` },
        { from: `/environments/${testEnvId}/credentials`, to: `/credentials?env_id=${testEnvId}` },
      ];

      for (const route of routes) {
        const { unmount } = render(
          <MemoryRouter initialEntries={[route.from]}>
            <Routes>
              <Route path="/environments/:id/workflows" element={<LegacyEnvironmentWorkflowsRedirect />} />
              <Route path="/environments/:id/deployments" element={<LegacyEnvironmentDeploymentsRedirect />} />
              <Route path="/environments/:id/snapshots" element={<LegacyEnvironmentSnapshotsRedirect />} />
              <Route path="/environments/:id/executions" element={<LegacyEnvironmentExecutionsRedirect />} />
              <Route path="/environments/:id/activity" element={<LegacyEnvironmentActivityRedirect />} />
              <Route path="/environments/:id/credentials" element={<LegacyEnvironmentCredentialsRedirect />} />
              <Route path="/workflows" element={<LocationDisplay />} />
              <Route path="/deployments" element={<LocationDisplay />} />
              <Route path="/snapshots" element={<LocationDisplay />} />
              <Route path="/executions" element={<LocationDisplay />} />
              <Route path="/activity" element={<LocationDisplay />} />
              <Route path="/credentials" element={<LocationDisplay />} />
            </Routes>
          </MemoryRouter>
        );

        await waitFor(() => {
          const locationDisplay = screen.getByTestId('location-display');
          expect(locationDisplay.textContent).toBe(route.to);
        });

        unmount();
      }
    });
  });
});
