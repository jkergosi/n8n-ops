import { describe, expect, it } from 'vitest';
import {
  canAccessRoute,
  isMenuItemVisible,
  mapBackendRoleToFrontendRole,
} from '../permissions';

describe('permissions helpers', () => {
  it('allows superuser for any route or menu', () => {
    expect(canAccessRoute('/admin/plans', 'superuser')).toBe(true);
    expect(isMenuItemVisible('plans', 'superuser')).toBe(true);
  });

  it('denies restricted admin route for regular user', () => {
    expect(canAccessRoute('/admin/plans', 'user')).toBe(false);
  });

  it('allows dynamic workflow routes for default user', () => {
    expect(canAccessRoute('/workflows/123', 'user')).toBe(true);
  });

  it('maps backend roles to frontend roles', () => {
    expect(mapBackendRoleToFrontendRole('super_admin')).toBe('superuser');
    expect(mapBackendRoleToFrontendRole('agency')).toBe('agency');
    expect(mapBackendRoleToFrontendRole(undefined)).toBe('user');
  });
});

