import { describe, expect, it } from 'vitest';
import {
  canAccessRoute,
  mapBackendRoleToFrontendRole,
} from '../permissions';

describe('permissions helpers', () => {
  it('allows platform_admin for platform routes (no plan gating)', () => {
    expect(canAccessRoute('/platform/tenants', 'platform_admin', 'free')).toBe(true);
    expect(canAccessRoute('/platform/admins', 'platform_admin', 'free')).toBe(true);
  });

  it('denies platform routes for non-platform users', () => {
    expect(canAccessRoute('/platform/tenants', 'admin', 'free')).toBe(false);
    expect(canAccessRoute('/platform/tenants', 'developer', 'free')).toBe(false);
    expect(canAccessRoute('/platform/tenants', 'viewer', 'free')).toBe(false);
  });

  it('org admin routes are admin only', () => {
    expect(canAccessRoute('/admin/members', 'admin', 'free')).toBe(true);
    expect(canAccessRoute('/admin/members', 'developer', 'free')).toBe(false);
    expect(canAccessRoute('/admin/members', 'viewer', 'free')).toBe(false);
  });

  it('observability is Pro+ and viewer+', () => {
    expect(canAccessRoute('/observability', 'viewer', 'free')).toBe(false);
    expect(canAccessRoute('/observability', 'viewer', 'pro')).toBe(true);
  });

  it('maps backend roles to frontend roles (with back-compat)', () => {
    expect(mapBackendRoleToFrontendRole('super_admin')).toBe('platform_admin');
    expect(mapBackendRoleToFrontendRole('admin')).toBe('admin');
    expect(mapBackendRoleToFrontendRole('developer')).toBe('developer');
    expect(mapBackendRoleToFrontendRole('viewer')).toBe('viewer');
    expect(mapBackendRoleToFrontendRole(undefined)).toBe('viewer');
  });
});

