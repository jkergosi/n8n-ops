import { describe, it, expect } from 'vitest';
import { canAccessRoute, mapBackendRoleToFrontendRole } from './permissions';

describe('permissions', () => {
  describe('mapBackendRoleToFrontendRole', () => {
    it('should map admin role correctly', () => {
      expect(mapBackendRoleToFrontendRole('admin')).toBe('admin');
      expect(mapBackendRoleToFrontendRole('Admin')).toBe('admin');
      expect(mapBackendRoleToFrontendRole('ADMIN')).toBe('admin');
    });

    it('should map platform admin roles correctly (back-compat)', () => {
      expect(mapBackendRoleToFrontendRole('platform_admin')).toBe('platform_admin');
      expect(mapBackendRoleToFrontendRole('super_admin')).toBe('platform_admin');
      expect(mapBackendRoleToFrontendRole('superuser')).toBe('platform_admin');
    });

    it('should map org roles correctly', () => {
      expect(mapBackendRoleToFrontendRole('developer')).toBe('developer');
      expect(mapBackendRoleToFrontendRole('viewer')).toBe('viewer');
      expect(mapBackendRoleToFrontendRole('Developer')).toBe('developer');
    });

    it('should default to viewer for unknown/undefined roles', () => {
      expect(mapBackendRoleToFrontendRole('unknown')).toBe('viewer');
      expect(mapBackendRoleToFrontendRole('')).toBe('viewer');
      expect(mapBackendRoleToFrontendRole(undefined)).toBe('viewer');
    });
  });

  describe('canAccessRoute', () => {
    it('platform_admin can access platform routes regardless of plan', () => {
      expect(canAccessRoute('/platform', 'platform_admin', 'free')).toBe(true);
      expect(canAccessRoute('/platform/admins', 'platform_admin', 'free')).toBe(true);
    });

    it('admin can access org admin routes (Free+)', () => {
      expect(canAccessRoute('/admin', 'admin', 'free')).toBe(true);
      expect(canAccessRoute('/admin/members', 'admin', 'free')).toBe(true);
    });

    it('non-admin cannot access org admin routes', () => {
      expect(canAccessRoute('/admin/members', 'developer', 'free')).toBe(false);
      expect(canAccessRoute('/admin/members', 'viewer', 'free')).toBe(false);
    });

    it('observability requires Pro+', () => {
      expect(canAccessRoute('/observability', 'viewer', 'free')).toBe(false);
      expect(canAccessRoute('/observability', 'viewer', 'pro')).toBe(true);
    });
  });
});
