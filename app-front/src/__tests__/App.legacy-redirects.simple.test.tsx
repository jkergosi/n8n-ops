import { describe, it, expect } from 'vitest';
import { useParams, Navigate } from 'react-router-dom';
import { vi } from 'vitest';

// Mock react-router-dom
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useParams: vi.fn(),
    Navigate: vi.fn((props) => null),
  };
});

describe('Legacy Environment Route Redirect Logic', () => {
  it('LegacyEnvironmentWorkflowsRedirect - redirects with env_id when id is present', () => {
    const mockUseParams = useParams as ReturnType<typeof vi.fn>;
    const mockNavigate = Navigate as unknown as ReturnType<typeof vi.fn>;

    mockUseParams.mockReturnValue({ id: 'test-env-123' });

    // Import the component
    const {
      LegacyEnvironmentWorkflowsRedirect,
    } = require('../App');

    const result = LegacyEnvironmentWorkflowsRedirect();

    // Verify Navigate was called with correct props
    expect(mockNavigate).toHaveBeenCalledWith(
      expect.objectContaining({
        to: '/workflows?env_id=test-env-123',
        replace: true,
      }),
      expect.anything()
    );
  });

  it('LegacyEnvironmentWorkflowsRedirect - redirects without env_id when id is missing', () => {
    const mockUseParams = useParams as ReturnType<typeof vi.fn>;
    const mockNavigate = Navigate as unknown as ReturnType<typeof vi.fn>;

    mockUseParams.mockReturnValue({ id: undefined });

    const {
      LegacyEnvironmentWorkflowsRedirect,
    } = require('../App');

    LegacyEnvironmentWorkflowsRedirect();

    expect(mockNavigate).toHaveBeenCalledWith(
      expect.objectContaining({
        to: '/workflows',
        replace: true,
      }),
      expect.anything()
    );
  });

  it('LegacyEnvironmentDeploymentsRedirect - redirects with env_id', () => {
    const mockUseParams = useParams as ReturnType<typeof vi.fn>;
    const mockNavigate = Navigate as unknown as ReturnType<typeof vi.fn>;

    mockUseParams.mockReturnValue({ id: 'test-env-456' });

    const {
      LegacyEnvironmentDeploymentsRedirect,
    } = require('../App');

    LegacyEnvironmentDeploymentsRedirect();

    expect(mockNavigate).toHaveBeenCalledWith(
      expect.objectContaining({
        to: '/deployments?env_id=test-env-456',
        replace: true,
      }),
      expect.anything()
    );
  });

  it('LegacyEnvironmentSnapshotsRedirect - redirects with env_id', () => {
    const mockUseParams = useParams as ReturnType<typeof vi.fn>;
    const mockNavigate = Navigate as unknown as ReturnType<typeof vi.fn>;

    mockUseParams.mockReturnValue({ id: 'test-env-789' });

    const {
      LegacyEnvironmentSnapshotsRedirect,
    } = require('../App');

    LegacyEnvironmentSnapshotsRedirect();

    expect(mockNavigate).toHaveBeenCalledWith(
      expect.objectContaining({
        to: '/snapshots?env_id=test-env-789',
        replace: true,
      }),
      expect.anything()
    );
  });

  it('LegacyEnvironmentExecutionsRedirect - redirects with env_id', () => {
    const mockUseParams = useParams as ReturnType<typeof vi.fn>;
    const mockNavigate = Navigate as unknown as ReturnType<typeof vi.fn>;

    mockUseParams.mockReturnValue({ id: 'test-env-abc' });

    const {
      LegacyEnvironmentExecutionsRedirect,
    } = require('../App');

    LegacyEnvironmentExecutionsRedirect();

    expect(mockNavigate).toHaveBeenCalledWith(
      expect.objectContaining({
        to: '/executions?env_id=test-env-abc',
        replace: true,
      }),
      expect.anything()
    );
  });

  it('LegacyEnvironmentActivityRedirect - redirects with env_id', () => {
    const mockUseParams = useParams as ReturnType<typeof vi.fn>;
    const mockNavigate = Navigate as unknown as ReturnType<typeof vi.fn>;

    mockUseParams.mockReturnValue({ id: 'test-env-def' });

    const {
      LegacyEnvironmentActivityRedirect,
    } = require('../App');

    LegacyEnvironmentActivityRedirect();

    expect(mockNavigate).toHaveBeenCalledWith(
      expect.objectContaining({
        to: '/activity?env_id=test-env-def',
        replace: true,
      }),
      expect.anything()
    );
  });

  it('LegacyEnvironmentCredentialsRedirect - redirects with env_id', () => {
    const mockUseParams = useParams as ReturnType<typeof vi.fn>;
    const mockNavigate = Navigate as unknown as ReturnType<typeof vi.fn>;

    mockUseParams.mockReturnValue({ id: 'test-env-ghi' });

    const {
      LegacyEnvironmentCredentialsRedirect,
    } = require('../App');

    LegacyEnvironmentCredentialsRedirect();

    expect(mockNavigate).toHaveBeenCalledWith(
      expect.objectContaining({
        to: '/credentials?env_id=test-env-ghi',
        replace: true,
      }),
      expect.anything()
    );
  });

  it('handles UUID format env_ids correctly', () => {
    const mockUseParams = useParams as ReturnType<typeof vi.fn>;
    const mockNavigate = Navigate as unknown as ReturnType<typeof vi.fn>;

    const uuidEnvId = '550e8400-e29b-41d4-a716-446655440000';
    mockUseParams.mockReturnValue({ id: uuidEnvId });

    const {
      LegacyEnvironmentWorkflowsRedirect,
    } = require('../App');

    LegacyEnvironmentWorkflowsRedirect();

    expect(mockNavigate).toHaveBeenCalledWith(
      expect.objectContaining({
        to: `/workflows?env_id=${uuidEnvId}`,
        replace: true,
      }),
      expect.anything()
    );
  });

  it('handles env_ids with special characters', () => {
    const mockUseParams = useParams as ReturnType<typeof vi.fn>;
    const mockNavigate = Navigate as unknown as ReturnType<typeof vi.fn>;

    const specialId = 'env-with-dashes_and_underscores';
    mockUseParams.mockReturnValue({ id: specialId });

    const {
      LegacyEnvironmentDeploymentsRedirect,
    } = require('../App');

    LegacyEnvironmentDeploymentsRedirect();

    expect(mockNavigate).toHaveBeenCalledWith(
      expect.objectContaining({
        to: `/deployments?env_id=${specialId}`,
        replace: true,
      }),
      expect.anything()
    );
  });
});

describe('Redirect Component Properties', () => {
  it('all redirects use replace: true to avoid polluting history', () => {
    const mockUseParams = useParams as ReturnType<typeof vi.fn>;
    const mockNavigate = Navigate as unknown as ReturnType<typeof vi.fn>;

    mockUseParams.mockReturnValue({ id: 'test-id' });

    const {
      LegacyEnvironmentWorkflowsRedirect,
      LegacyEnvironmentDeploymentsRedirect,
      LegacyEnvironmentSnapshotsRedirect,
      LegacyEnvironmentExecutionsRedirect,
      LegacyEnvironmentActivityRedirect,
      LegacyEnvironmentCredentialsRedirect,
    } = require('../App');

    const redirects = [
      LegacyEnvironmentWorkflowsRedirect,
      LegacyEnvironmentDeploymentsRedirect,
      LegacyEnvironmentSnapshotsRedirect,
      LegacyEnvironmentExecutionsRedirect,
      LegacyEnvironmentActivityRedirect,
      LegacyEnvironmentCredentialsRedirect,
    ];

    redirects.forEach((redirect) => {
      mockNavigate.mockClear();
      redirect();
      expect(mockNavigate).toHaveBeenCalledWith(
        expect.objectContaining({
          replace: true,
        }),
        expect.anything()
      );
    });
  });

  it('all redirects handle missing id consistently', () => {
    const mockUseParams = useParams as ReturnType<typeof vi.fn>;
    const mockNavigate = Navigate as unknown as ReturnType<typeof vi.fn>;

    mockUseParams.mockReturnValue({ id: undefined });

    const {
      LegacyEnvironmentWorkflowsRedirect,
      LegacyEnvironmentDeploymentsRedirect,
      LegacyEnvironmentSnapshotsRedirect,
      LegacyEnvironmentExecutionsRedirect,
      LegacyEnvironmentActivityRedirect,
      LegacyEnvironmentCredentialsRedirect,
    } = require('../App');

    const testCases = [
      { redirect: LegacyEnvironmentWorkflowsRedirect, expectedPath: '/workflows' },
      { redirect: LegacyEnvironmentDeploymentsRedirect, expectedPath: '/deployments' },
      { redirect: LegacyEnvironmentSnapshotsRedirect, expectedPath: '/snapshots' },
      { redirect: LegacyEnvironmentExecutionsRedirect, expectedPath: '/executions' },
      { redirect: LegacyEnvironmentActivityRedirect, expectedPath: '/activity' },
      { redirect: LegacyEnvironmentCredentialsRedirect, expectedPath: '/credentials' },
    ];

    testCases.forEach(({ redirect, expectedPath }) => {
      mockNavigate.mockClear();
      redirect();
      expect(mockNavigate).toHaveBeenCalledWith(
        expect.objectContaining({
          to: expectedPath,
          replace: true,
        }),
        expect.anything()
      );
    });
  });
});
