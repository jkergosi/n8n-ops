/**
 * Recently Visited Routes History Utility
 *
 * Stores the last N visited routes in localStorage for quick navigation
 * back to frequently accessed pages.
 */

const RECENTLY_VISITED_KEY = 'recently_visited_routes';
const MAX_RECENT_ROUTES = 8;

export interface RecentRoute {
  path: string;
  label: string;
  timestamp: number;
}

/**
 * Routes to exclude from recently visited tracking
 */
const EXCLUDED_ROUTES = [
  '/login',
  '/onboarding',
  '/auth',
  '/dev',
];

/**
 * Check if a route should be excluded from tracking
 */
function shouldExcludeRoute(pathname: string): boolean {
  return EXCLUDED_ROUTES.some(excluded => pathname.startsWith(excluded));
}

/**
 * Get the label for a route path based on known routes
 */
export function getRouteLabel(pathname: string): string {
  // Route label mappings for all known routes
  const routeLabels: Record<string, string> = {
    '/': 'Dashboard',
    '/dashboard': 'Dashboard',
    '/environments': 'Environments',
    '/workflows': 'Workflows',
    '/executions': 'Executions',
    '/deployments': 'Deployments',
    '/snapshots': 'Snapshots',
    '/observability': 'Overview',
    '/activity': 'Activity',
    '/credentials': 'Credentials',
    '/n8n-users': 'n8n Users',
    '/admin': 'Admin Dashboard',
    '/admin/members': 'Members',
    '/admin/usage': 'Usage',
    '/admin/providers': 'Billing & Plans',
    '/admin/credential-health': 'Credential Health',
    '/admin/settings': 'Settings',
    '/platform': 'Platform Dashboard',
    '/platform/tenants': 'Tenants',
    '/platform/support': 'Support',
    '/platform/feature-matrix': 'Feature Matrix',
    '/platform/entitlements': 'Entitlements',
    '/platform/tenant-overrides': 'Tenant Overrides',
    '/platform/entitlements-audit': 'Entitlements Audit',
    '/platform/admins': 'Platform Admins',
    '/platform/settings': 'Platform Settings',
    '/canonical/untracked': 'Untracked',
    '/canonical/workflows': 'Canonical Workflows',
    '/canonical/onboarding': 'Canonical Onboarding',
    '/support': 'Support Center',
    '/profile': 'Profile',
    '/promote': 'Promote',
    '/alerts': 'Alerts',
    '/incidents': 'Incidents',
    '/drift-dashboard': 'Drift Dashboard',
    '/workflows-overview': 'Workflows Overview',
    '/analytics/executions': 'Execution Analytics',
  };

  // Check for exact match first
  if (routeLabels[pathname]) {
    return routeLabels[pathname];
  }

  // Handle dynamic routes (e.g., /environments/:id, /workflows/:id)
  const segments = pathname.split('/').filter(Boolean);

  if (segments.length >= 2) {
    const baseRoute = '/' + segments[0];
    const baseLabel = routeLabels[baseRoute];

    if (baseLabel) {
      // For detail pages, try to extract a meaningful ID
      if (segments.length === 2) {
        // Shorten UUID-like IDs
        const id = segments[1];
        const displayId = id.length > 12 ? id.substring(0, 8) + '...' : id;
        return `${baseLabel} / ${displayId}`;
      }

      // For sub-pages like /environments/:id/edit
      if (segments.length >= 3) {
        const action = segments[2];
        const actionLabels: Record<string, string> = {
          'edit': 'Edit',
          'restore': 'Restore',
          'new': 'New',
          'users': 'Users',
        };
        return `${baseLabel} / ${actionLabels[action] || action}`;
      }
    }
  }

  // Fallback: capitalize the last segment
  const lastSegment = segments[segments.length - 1] || 'Page';
  return lastSegment.charAt(0).toUpperCase() + lastSegment.slice(1).replace(/-/g, ' ');
}

/**
 * Get the recently visited routes
 */
export function getRecentlyVisited(): RecentRoute[] {
  try {
    const stored = localStorage.getItem(RECENTLY_VISITED_KEY);
    if (!stored) return [];

    const routes: RecentRoute[] = JSON.parse(stored);

    // Filter out excluded routes and validate structure
    return routes
      .filter(route =>
        route &&
        typeof route.path === 'string' &&
        !shouldExcludeRoute(route.path)
      )
      .slice(0, MAX_RECENT_ROUTES);
  } catch (error) {
    console.warn('Failed to get recently visited routes:', error);
    return [];
  }
}

/**
 * Add a route to the recently visited list
 */
export function addRecentlyVisited(pathname: string): void {
  try {
    if (shouldExcludeRoute(pathname)) {
      return;
    }

    const label = getRouteLabel(pathname);
    const newRoute: RecentRoute = {
      path: pathname,
      label,
      timestamp: Date.now(),
    };

    // Get existing routes
    const existing = getRecentlyVisited();

    // Remove duplicate if exists (move to front)
    const filtered = existing.filter(route => route.path !== pathname);

    // Add new route at the beginning
    const updated = [newRoute, ...filtered].slice(0, MAX_RECENT_ROUTES);

    localStorage.setItem(RECENTLY_VISITED_KEY, JSON.stringify(updated));
  } catch (error) {
    console.warn('Failed to add recently visited route:', error);
  }
}

/**
 * Clear the recently visited routes
 */
export function clearRecentlyVisited(): void {
  try {
    localStorage.removeItem(RECENTLY_VISITED_KEY);
  } catch (error) {
    console.warn('Failed to clear recently visited routes:', error);
  }
}
