import React, { useMemo } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '@/lib/auth';
import { useFeatures } from '@/lib/features';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  ChevronRight,
  ChevronDown,
  Home,
  History,
  LayoutDashboard,
  Server,
  Workflow,
  ListChecks,
  Activity,
  Users,
  UserCog,
  CreditCard,
  Building2,
  Shield,
  BarChart3,
  Settings,
  Key,
  HelpCircle,
  Table,
  Camera,
  GitBranch,
  LayoutGrid,
  FileQuestion,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  canSeePlatformNav,
  isAtLeastPlan,
  mapBackendRoleToFrontendRole,
  normalizePlan,
  type Plan,
  type Role,
} from '@/lib/permissions';
import { getRecentlyVisited, type RecentRoute } from '@/lib/recentlyVisited';

// Navigation structure matching AppLayout
interface NavItem {
  id: string;
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  minPlan?: Plan;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const navigationSections: NavSection[] = [
  {
    title: 'Operations',
    items: [
      { id: 'dashboard', name: 'Dashboard', href: '/', icon: LayoutDashboard },
      { id: 'environments', name: 'Environments', href: '/environments', icon: Server },
      { id: 'workflows', name: 'Workflows', href: '/workflows', icon: Workflow },
      { id: 'untracked', name: 'Untracked', href: '/canonical/untracked', icon: FileQuestion },
      { id: 'deployments', name: 'Deployments', href: '/deployments', icon: GitBranch, minPlan: 'pro' },
      { id: 'snapshots', name: 'Snapshots', href: '/snapshots', icon: Camera, minPlan: 'pro' },
    ],
  },
  {
    title: 'Observability',
    items: [
      { id: 'observability', name: 'Overview', href: '/observability', icon: Activity, minPlan: 'pro' },
      { id: 'executions', name: 'Executions', href: '/executions', icon: ListChecks },
      { id: 'activity', name: 'Activity', href: '/activity', icon: History },
    ],
  },
  {
    title: 'Identity & Secrets',
    items: [
      { id: 'credentials', name: 'Credentials', href: '/credentials', icon: Key },
      { id: 'n8nUsers', name: 'n8n Users', href: '/n8n-users', icon: UserCog, minPlan: 'pro' },
    ],
  },
  {
    title: 'Admin',
    items: [
      { id: 'adminDashboard', name: 'Admin Dashboard', href: '/admin', icon: LayoutGrid, minPlan: 'pro' },
      { id: 'members', name: 'Members', href: '/admin/members', icon: Users },
      { id: 'usage', name: 'Usage', href: '/admin/usage', icon: BarChart3, minPlan: 'pro' },
      { id: 'providers', name: 'Billing & Plans', href: '/admin/providers', icon: CreditCard },
      { id: 'credentialHealth', name: 'Credential Health', href: '/admin/credential-health', icon: Shield, minPlan: 'pro' },
      { id: 'settings', name: 'Settings', href: '/admin/settings', icon: Settings },
    ],
  },
  {
    title: 'Platform',
    items: [
      { id: 'platformDashboard', name: 'Platform Dashboard', href: '/platform', icon: LayoutGrid },
      { id: 'platformTenants', name: 'Tenants', href: '/platform/tenants', icon: Building2 },
      { id: 'platformConsole', name: 'Support', href: '/platform/support', icon: HelpCircle },
      { id: 'platformFeatureMatrix', name: 'Feature Matrix', href: '/platform/feature-matrix', icon: Table },
      { id: 'platformEntitlements', name: 'Entitlements', href: '/platform/entitlements', icon: LayoutGrid },
      { id: 'platformOverrides', name: 'Tenant Overrides', href: '/platform/tenant-overrides', icon: Shield },
      { id: 'platformEntitlementsAudit', name: 'Entitlements Audit', href: '/platform/entitlements-audit', icon: History },
      { id: 'platformAdmins', name: 'Platform Admins', href: '/platform/admins', icon: Shield },
      { id: 'platformSettings', name: 'Settings', href: '/platform/settings', icon: Settings },
    ],
  },
];

interface BreadcrumbSegment {
  label: string;
  href: string;
  isActive: boolean;
  siblings?: NavItem[];
  section?: NavSection;
}

export function Breadcrumb() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { planName } = useFeatures();
  const [recentRoutes, setRecentRoutes] = React.useState<RecentRoute[]>([]);

  // Get user's role
  const getUserRole = React.useCallback((): Role => {
    if ((user as any)?.isPlatformAdmin) return 'platform_admin';
    if (!user?.role) return 'viewer';
    return mapBackendRoleToFrontendRole(user.role);
  }, [user?.role, (user as any)?.isPlatformAdmin]);

  const normalizedPlan = normalizePlan(planName);
  const userRole = getUserRole();
  const showPlatform = canSeePlatformNav(userRole);

  // Check if nav item is visible based on role and plan
  const isNavItemVisible = React.useCallback(
    (sectionTitle: string, item: NavItem): boolean => {
      if (sectionTitle === 'Platform' && !showPlatform) return false;
      if (sectionTitle === 'Admin' && userRole !== 'admin' && userRole !== 'platform_admin') return false;
      if (sectionTitle === 'Identity & Secrets') {
        if (item.href === '/credentials' && userRole !== 'admin') return false;
        if (item.href === '/n8n-users' && userRole !== 'admin') return false;
      }
      if (item.minPlan && !isAtLeastPlan(normalizedPlan, item.minPlan)) return false;
      return true;
    },
    [normalizedPlan, showPlatform, userRole]
  );

  // Load recently visited routes
  React.useEffect(() => {
    setRecentRoutes(getRecentlyVisited());
  }, [location.pathname]);

  // Build breadcrumb segments from current path
  const breadcrumbs = useMemo((): BreadcrumbSegment[] => {
    const pathname = location.pathname;
    const segments: BreadcrumbSegment[] = [];

    // Always start with Home
    segments.push({
      label: 'WorkflowOps',
      href: '/',
      isActive: pathname === '/',
      siblings: undefined,
    });

    if (pathname === '/') {
      return segments;
    }

    // Find the current section and item
    let currentSection: NavSection | undefined;
    let currentItem: NavItem | undefined;

    for (const section of navigationSections) {
      for (const item of section.items) {
        // Check for exact match or if current path starts with the item's href (for nested routes)
        if (pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href + '/'))) {
          currentSection = section;
          currentItem = item;
          break;
        }
        // Also check for paths that start with the section prefix
        if (pathname.startsWith(item.href) && item.href !== '/' && item.href.length > (currentItem?.href.length || 0)) {
          currentSection = section;
          currentItem = item;
        }
      }
      if (currentItem) break;
    }

    // Handle special cases for nested routes
    const pathSegments = pathname.split('/').filter(Boolean);

    // For detail pages (e.g., /environments/:id), try to find the parent section
    if (!currentSection && pathSegments.length >= 1) {
      const baseRoute = '/' + pathSegments[0];
      for (const section of navigationSections) {
        for (const item of section.items) {
          if (item.href === baseRoute || item.href.startsWith(baseRoute + '/')) {
            currentSection = section;
            // Find the closest matching item
            if (item.href === baseRoute) {
              currentItem = item;
              break;
            }
          }
        }
        if (currentItem) break;
      }
    }

    // Add section breadcrumb with siblings dropdown
    if (currentSection) {
      const visibleSiblings = currentSection.items.filter(item =>
        isNavItemVisible(currentSection!.title, item)
      );

      segments.push({
        label: currentSection.title,
        href: currentItem?.href || pathname,
        isActive: false,
        siblings: visibleSiblings,
        section: currentSection,
      });
    }

    // Add current page
    if (currentItem) {
      // Get visible items in the same section for sibling navigation
      const visibleSectionItems = currentSection?.items.filter(item =>
        isNavItemVisible(currentSection!.title, item)
      );

      segments.push({
        label: currentItem.name,
        href: currentItem.href,
        isActive: pathname === currentItem.href,
        siblings: visibleSectionItems,
      });
    }

    // Handle nested detail pages (e.g., /environments/:id, /workflows/:id)
    if (pathSegments.length > 1 && currentItem) {
      const detailId = pathSegments[1];

      // Skip if it's a known sub-route like 'new'
      if (detailId !== 'new') {
        const displayId = detailId.length > 12 ? detailId.substring(0, 8) + '...' : detailId;

        segments.push({
          label: displayId,
          href: pathname.split('/').slice(0, 3).join('/'),
          isActive: pathSegments.length === 2,
        });

        // Handle action pages like /environments/:id/edit
        if (pathSegments.length > 2) {
          const action = pathSegments[2];
          const actionLabels: Record<string, string> = {
            'edit': 'Edit',
            'restore': 'Restore',
            'new': 'New',
            'users': 'Users',
          };

          segments.push({
            label: actionLabels[action] || action.charAt(0).toUpperCase() + action.slice(1),
            href: pathname,
            isActive: true,
          });
        }
      } else {
        // For 'new' pages
        segments.push({
          label: 'New',
          href: pathname,
          isActive: true,
        });
      }
    }

    return segments;
  }, [location.pathname, isNavItemVisible]);

  const handleNavigate = (href: string) => {
    navigate(href);
  };

  // Filter recent routes to exclude current path and only show valid ones
  const filteredRecentRoutes = recentRoutes
    .filter(route => route.path !== location.pathname)
    .slice(0, 5);

  return (
    <nav
      className="flex items-center gap-1 text-sm"
      aria-label="Breadcrumb"
      data-testid="breadcrumb-nav"
    >
      {/* Recently Visited Dropdown */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            className="flex items-center gap-1 px-2 py-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            aria-label="Recently visited pages"
            data-testid="recent-pages-trigger"
          >
            <History className="h-4 w-4" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-64" data-testid="recent-pages-menu">
          <DropdownMenuLabel>Recently Visited</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {filteredRecentRoutes.length > 0 ? (
            filteredRecentRoutes.map((route, index) => (
              <DropdownMenuItem
                key={route.path + index}
                onClick={() => handleNavigate(route.path)}
                className="cursor-pointer"
                data-testid={`recent-page-${index}`}
              >
                <span className="truncate">{route.label}</span>
              </DropdownMenuItem>
            ))
          ) : (
            <div className="px-2 py-4 text-center text-sm text-muted-foreground">
              No recent pages
            </div>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      <span className="text-muted-foreground/50">/</span>

      {/* Breadcrumb segments */}
      {breadcrumbs.map((segment, index) => {
        const isLast = index === breadcrumbs.length - 1;
        const hasSiblings = segment.siblings && segment.siblings.length > 1;

        return (
          <React.Fragment key={segment.href + index}>
            {index > 0 && (
              <ChevronRight className="h-4 w-4 text-muted-foreground/50 flex-shrink-0" />
            )}

            {hasSiblings ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    className={cn(
                      'flex items-center gap-1 px-2 py-1 rounded-md transition-colors',
                      isLast
                        ? 'text-foreground font-medium'
                        : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                    )}
                    data-testid={`breadcrumb-${index}`}
                  >
                    {index === 0 && <Home className="h-4 w-4" />}
                    <span className="max-w-[150px] truncate">{segment.label}</span>
                    <ChevronDown className="h-3 w-3 ml-0.5" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="w-56" data-testid={`breadcrumb-menu-${index}`}>
                  {segment.section && (
                    <>
                      <DropdownMenuLabel>{segment.section.title}</DropdownMenuLabel>
                      <DropdownMenuSeparator />
                    </>
                  )}
                  {segment.siblings?.map((sibling) => {
                    const Icon = sibling.icon;
                    const isCurrentItem = location.pathname === sibling.href ||
                      (sibling.href !== '/' && location.pathname.startsWith(sibling.href + '/'));

                    return (
                      <DropdownMenuItem
                        key={sibling.id}
                        onClick={() => handleNavigate(sibling.href)}
                        className={cn(
                          'cursor-pointer',
                          isCurrentItem && 'bg-accent'
                        )}
                        data-testid={`sibling-${sibling.id}`}
                      >
                        <Icon className="mr-2 h-4 w-4" />
                        <span>{sibling.name}</span>
                      </DropdownMenuItem>
                    );
                  })}
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <Link
                to={segment.href}
                className={cn(
                  'flex items-center gap-1 px-2 py-1 rounded-md transition-colors max-w-[150px]',
                  isLast
                    ? 'text-foreground font-medium cursor-default pointer-events-none'
                    : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                )}
                data-testid={`breadcrumb-${index}`}
              >
                {index === 0 && <Home className="h-4 w-4" />}
                <span className="truncate">{segment.label}</span>
              </Link>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
}
