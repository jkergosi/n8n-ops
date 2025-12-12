import { describe, it, expect } from 'vitest';
import {
  canAccessRoute,
  isMenuItemVisible,
  mapBackendRoleToFrontendRole,
  Role,
  MENU_VISIBILITY,
  ROUTE_TO_MENU_ID,
} from './permissions';

describe('permissions', () => {
  describe('mapBackendRoleToFrontendRole', () => {
    it('should map admin role correctly', () => {
      expect(mapBackendRoleToFrontendRole('admin')).toBe('admin');
      expect(mapBackendRoleToFrontendRole('Admin')).toBe('admin');
      expect(mapBackendRoleToFrontendRole('ADMIN')).toBe('admin');
    });

    it('should map superuser roles correctly', () => {
      expect(mapBackendRoleToFrontendRole('superuser')).toBe('superuser');
      expect(mapBackendRoleToFrontendRole('super_admin')).toBe('superuser');
      expect(mapBackendRoleToFrontendRole('Superuser')).toBe('superuser');
    });

    it('should map agency role correctly', () => {
      expect(mapBackendRoleToFrontendRole('agency')).toBe('agency');
      expect(mapBackendRoleToFrontendRole('Agency')).toBe('agency');
    });

    it('should map developer and viewer to user', () => {
      expect(mapBackendRoleToFrontendRole('developer')).toBe('user');
      expect(mapBackendRoleToFrontendRole('viewer')).toBe('user');
      expect(mapBackendRoleToFrontendRole('Developer')).toBe('user');
    });

    it('should default to user for unknown roles', () => {
      expect(mapBackendRoleToFrontendRole('unknown')).toBe('user');
      expect(mapBackendRoleToFrontendRole('guest')).toBe('user');
      expect(mapBackendRoleToFrontendRole('')).toBe('user');
    });

    it('should handle undefined/null input', () => {
      expect(mapBackendRoleToFrontendRole(undefined)).toBe('user');
    });
  });

  describe('canAccessRoute', () => {
    it('should allow superuser to access all routes', () => {
      expect(canAccessRoute('/', 'superuser')).toBe(true);
      expect(canAccessRoute('/admin/tenants', 'superuser')).toBe(true);
      expect(canAccessRoute('/admin/billing', 'superuser')).toBe(true);
      expect(canAccessRoute('/workflows', 'superuser')).toBe(true);
      expect(canAccessRoute('/pipelines', 'superuser')).toBe(true);
    });

    it('should allow user to access standard routes', () => {
      expect(canAccessRoute('/', 'user')).toBe(true);
      expect(canAccessRoute('/workflows', 'user')).toBe(true);
      expect(canAccessRoute('/environments', 'user')).toBe(true);
      expect(canAccessRoute('/executions', 'user')).toBe(true);
      expect(canAccessRoute('/pipelines', 'user')).toBe(true);
    });

    it('should restrict user from admin-only routes', () => {
      expect(canAccessRoute('/admin/tenants', 'user')).toBe(false);
      expect(canAccessRoute('/admin/plans', 'user')).toBe(false);
      expect(canAccessRoute('/admin/usage', 'user')).toBe(false);
    });

    it('should allow admin to access admin routes', () => {
      expect(canAccessRoute('/admin/tenants', 'admin')).toBe(true);
      expect(canAccessRoute('/admin/billing', 'admin')).toBe(true);
      expect(canAccessRoute('/admin/audit-logs', 'admin')).toBe(true);
    });

    it('should handle dynamic routes correctly', () => {
      expect(canAccessRoute('/workflows/123', 'user')).toBe(true);
      expect(canAccessRoute('/environments/abc-123', 'user')).toBe(true);
      expect(canAccessRoute('/pipelines/test-pipeline', 'user')).toBe(true);
    });

    it('should allow access to profile and team routes for all authenticated users', () => {
      expect(canAccessRoute('/profile', 'user')).toBe(true);
      expect(canAccessRoute('/team', 'user')).toBe(true);
      expect(canAccessRoute('/billing', 'user')).toBe(true);
    });

    it('should default to accessible for unmapped routes', () => {
      expect(canAccessRoute('/some-unknown-route', 'user')).toBe(true);
      expect(canAccessRoute('/not-configured', 'admin')).toBe(true);
    });
  });

  describe('isMenuItemVisible', () => {
    it('should show all menu items to superuser', () => {
      expect(isMenuItemVisible('dashboard', 'superuser')).toBe(true);
      expect(isMenuItemVisible('tenants', 'superuser')).toBe(true);
      expect(isMenuItemVisible('plans', 'superuser')).toBe(true);
      expect(isMenuItemVisible('usage', 'superuser')).toBe(true);
    });

    it('should show standard items to user role', () => {
      expect(isMenuItemVisible('dashboard', 'user')).toBe(true);
      expect(isMenuItemVisible('workflows', 'user')).toBe(true);
      expect(isMenuItemVisible('environments', 'user')).toBe(true);
      expect(isMenuItemVisible('executions', 'user')).toBe(true);
    });

    it('should hide admin-only items from user role', () => {
      expect(isMenuItemVisible('tenants', 'user')).toBe(false);
      expect(isMenuItemVisible('plans', 'user')).toBe(false);
      expect(isMenuItemVisible('usage', 'user')).toBe(false);
    });

    it('should show admin items to admin role', () => {
      expect(isMenuItemVisible('tenants', 'admin')).toBe(true);
      expect(isMenuItemVisible('billing', 'admin')).toBe(true);
      expect(isMenuItemVisible('auditLogs', 'admin')).toBe(true);
    });

    it('should hide superuser-only items from admin', () => {
      // Plans is superuser only (admin + superuser)
      expect(isMenuItemVisible('plans', 'admin')).toBe(true);
      expect(isMenuItemVisible('usage', 'admin')).toBe(true);
    });

    it('should show agency role items correctly', () => {
      expect(isMenuItemVisible('dashboard', 'agency')).toBe(true);
      expect(isMenuItemVisible('tenants', 'agency')).toBe(true);
      expect(isMenuItemVisible('billing', 'agency')).toBe(true);
    });

    it('should default to visible for unconfigured items', () => {
      expect(isMenuItemVisible('nonexistent', 'user')).toBe(true);
      expect(isMenuItemVisible('unknown-item', 'admin')).toBe(true);
    });
  });

  describe('MENU_VISIBILITY configuration', () => {
    it('should have all expected menu items defined', () => {
      const expectedItems = [
        'dashboard',
        'environments',
        'workflows',
        'executions',
        'pipelines',
        'deployments',
        'snapshots',
        'credentials',
        'users',
        'tenants',
        'billing',
      ];

      expectedItems.forEach((item) => {
        const visibility = MENU_VISIBILITY.find((v) => v.id === item);
        expect(visibility).toBeDefined();
        expect(visibility?.roles).toBeDefined();
        expect(visibility?.roles.length).toBeGreaterThan(0);
      });
    });

    it('should have valid role arrays for all items', () => {
      const validRoles: Role[] = ['user', 'admin', 'agency', 'superuser'];

      MENU_VISIBILITY.forEach((item) => {
        item.roles.forEach((role) => {
          expect(validRoles).toContain(role);
        });
      });
    });
  });

  describe('ROUTE_TO_MENU_ID mapping', () => {
    it('should map core routes correctly', () => {
      expect(ROUTE_TO_MENU_ID['/']).toBe('dashboard');
      expect(ROUTE_TO_MENU_ID['/workflows']).toBe('workflows');
      expect(ROUTE_TO_MENU_ID['/environments']).toBe('environments');
      expect(ROUTE_TO_MENU_ID['/pipelines']).toBe('pipelines');
    });

    it('should map admin routes correctly', () => {
      expect(ROUTE_TO_MENU_ID['/admin/tenants']).toBe('tenants');
      expect(ROUTE_TO_MENU_ID['/admin/billing']).toBe('billing');
      expect(ROUTE_TO_MENU_ID['/admin/audit-logs']).toBe('auditLogs');
    });
  });
});
