import { BrowserRouter, Routes, Route, Navigate, useNavigate, useParams } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { AuthProvider, useAuth } from '@/lib/auth';
import { FeaturesProvider, useFeatures } from '@/lib/features';
import { ThemeProvider } from '@/components/ThemeProvider';
import { Toaster, toast } from 'sonner';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { ServiceStatusIndicator } from '@/components/ServiceStatusIndicator';
import { RouteTracker } from '@/components/RouteTracker';
import { useEffect } from 'react';
import { AppLayout } from '@/components/AppLayout';
import { LoginPage } from '@/pages/LoginPage';
import { OnboardingPage } from '@/pages/OnboardingPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { EnvironmentsPage } from '@/pages/EnvironmentsPage';
import { EnvironmentDetailPage } from '@/pages/EnvironmentDetailPage';
import { WorkflowsPage } from '@/pages/WorkflowsPage';
import { WorkflowDetailPage } from '@/pages/WorkflowDetailPage';
import { ExecutionsPage } from '@/pages/ExecutionsPage';
import { SnapshotsPage } from '@/pages/SnapshotsPage';
import { DeploymentsPage } from '@/pages/DeploymentsPage';
import { DeploymentDetailPage } from '@/pages/DeploymentDetailPage';
import { ObservabilityPage } from '@/pages/ObservabilityPage';
import { AlertsPage } from '@/pages/AlertsPage';
import { ActivityCenterPage } from '@/pages/ActivityCenterPage';
import { ActivityDetailPage } from '@/pages/ActivityDetailPage';
import { TeamPage } from '@/pages/TeamPage';
import { BillingPage } from '@/pages/BillingPage';
import { N8NUsersPage } from '@/pages/N8NUsersPage';
import { CredentialsPage } from '@/pages/CredentialsPage';
import { IncidentsPage } from '@/pages/IncidentsPage';
import { IncidentDetailPage } from '@/pages/IncidentDetailPage';
import { DriftDashboardPage } from '@/pages/DriftDashboardPage';
import { EnvironmentSetupPage } from '@/pages/EnvironmentSetupPage';
import { RestorePage } from '@/pages/RestorePage';
import { ProfilePage } from '@/pages/ProfilePage';
import { PipelineEditorPage } from '@/pages/PipelineEditorPage';
import { NewDeploymentPage } from '@/pages/NewDeploymentPage';
import {
  TenantsPage,
  TenantDetailPage,
  SecurityPage,
  SettingsPage,
  TenantOverridesPage,
  EntitlementsAuditPage,
  CredentialHealthPage,
  SupportConfigPage,
  SupportRequestsPage,
} from '@/pages/admin';
import {
  SupportHomePage,
  ReportBugPage,
  RequestFeaturePage,
  GetHelpPage,
} from '@/pages/support';
import { useLocation } from 'react-router-dom';
import { canAccessRoute, mapBackendRoleToFrontendRole, normalizePlan } from '@/lib/permissions';
import { setLastRoute } from '@/lib/lastRoute';
import { AdminUsagePage } from '@/pages/AdminUsagePage';
import { AdminEntitlementsPage } from '@/pages/AdminEntitlementsPage';
import { PlatformAdminsPage } from '@/pages/platform/PlatformAdminsPage';
import { SupportConsolePage } from '@/pages/platform/SupportConsolePage';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
});

// Protected Route Component with Onboarding Check
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, initComplete, needsOnboarding } = useAuth();
  const navigate = useNavigate();
  const currentPath = window.location.pathname;

  // Debug logging
  console.log('[ProtectedRoute] Render:', { currentPath, isAuthenticated, isLoading, initComplete, needsOnboarding });

  useEffect(() => {
    // If user needs onboarding and not already on onboarding page, redirect
    if (!isLoading && initComplete && needsOnboarding && window.location.pathname !== '/onboarding') {
      console.log('[ProtectedRoute] Redirecting to onboarding');
      navigate('/onboarding', { replace: true });
    }
  }, [isLoading, initComplete, needsOnboarding, navigate]);

  // Wait for both loading to complete AND initialization to be done
  // This prevents redirects during the brief moment between state updates
  if (isLoading || !initComplete) {
    console.log('[ProtectedRoute] Showing loading spinner');
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]"></div>
          <p className="mt-4 text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  // Check if user is authenticated (login completed)
  // isAuthenticated is true when user is logged in AND has completed onboarding
  // Only redirect if we're not already on login or onboarding page to prevent loops
  if (!isAuthenticated && !needsOnboarding && currentPath !== '/login' && currentPath !== '/onboarding') {
    console.log('[ProtectedRoute] Not authenticated, redirecting to login');
    return <Navigate to="/login" replace />;
  }

  console.log('[ProtectedRoute] Rendering children');
  return <>{children}</>;
}

// Role Protected Route Component - checks role permissions and redirects to dashboard if unauthorized
function RoleProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const { planName } = useFeatures();
  const location = useLocation();
  const navigate = useNavigate();

  const effectiveRole = user
    ? ((user as any)?.isPlatformAdmin ? 'platform_admin' : mapBackendRoleToFrontendRole(user.role))
    : null;
  const plan = normalizePlan(planName);
  const canAccess = user ? canAccessRoute(location.pathname, effectiveRole!, plan) : true;

  console.log('[RoleProtectedRoute] Render:', {
    pathname: location.pathname,
    hasUser: !!user,
    userRole: effectiveRole,
    plan: plan,
    canAccess
  });

  useEffect(() => {
    if (user) {
      const role = (user as any)?.isPlatformAdmin ? 'platform_admin' : mapBackendRoleToFrontendRole(user.role);
      const pathname = location.pathname;

      // Check if user can access this route
      if (!canAccessRoute(pathname, role, plan)) {
        console.log('[RoleProtectedRoute] Redirecting to dashboard - unauthorized');
        // Redirect to dashboard if unauthorized
        navigate('/', { replace: true });
      }
    }
  }, [user, location.pathname, navigate, plan]);

  // If no user, let ProtectedRoute handle it
  if (!user) {
    console.log('[RoleProtectedRoute] No user, rendering children');
    return <>{children}</>;
  }

  if (!canAccess) {
    console.log('[RoleProtectedRoute] Cannot access, showing redirect spinner');
    // Show loading while redirecting
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]"></div>
          <p className="mt-4 text-muted-foreground">Redirecting...</p>
        </div>
      </div>
    );
  }

  console.log('[RoleProtectedRoute] Rendering children');
  return <>{children}</>;
}

function LegacyPlatformTenantRedirect() {
  const { tenantId } = useParams();
  if (!tenantId) return <Navigate to="/platform/tenants" replace />;
  return <Navigate to={`/platform/tenants/${tenantId}`} replace />;
}

function App() {
  // Listen for service recovery notifications
  useEffect(() => {
    const handleServiceRecovery = (event: CustomEvent) => {
      const { from, to } = event.detail;
      if (from === 'unhealthy' && (to === 'healthy' || to === 'degraded')) {
        toast.success('Service recovered', {
          description: to === 'healthy' 
            ? 'All systems are now operational' 
            : 'Some services have recovered',
          duration: 5000,
        });
      }
    };

    window.addEventListener('service-recovered', handleServiceRecovery as EventListener);
    return () => {
      window.removeEventListener('service-recovered', handleServiceRecovery as EventListener);
    };
  }, []);

  return (
    <ThemeProvider defaultTheme="system" storageKey="n8n-ops-theme">
      <QueryClientProvider client={queryClient}>
        <ErrorBoundary showDetails={true}>
          <AuthProvider>
            <FeaturesProvider>
              <BrowserRouter>
                {/* Route Tracker - tracks lastRoute for navigation persistence */}
                <RouteTracker />
                {/* Service Status Indicator - shows when services are unhealthy */}
                <ServiceStatusIndicator position="fixed" />
                <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route
                path="/onboarding"
                element={
                  <ProtectedRoute>
                    <OnboardingPage />
                  </ProtectedRoute>
                }
              />
              <Route
                element={
                  <ProtectedRoute>
                    <AppLayout />
                  </ProtectedRoute>
                }
              >
                {/* Core */}
                <Route path="/dashboard" element={<Navigate to="/" replace />} />
                <Route path="/" element={<RoleProtectedRoute><DashboardPage /></RoleProtectedRoute>} />
                <Route path="/environments" element={<RoleProtectedRoute><EnvironmentsPage /></RoleProtectedRoute>} />
                <Route path="/environments/new" element={<RoleProtectedRoute><EnvironmentSetupPage /></RoleProtectedRoute>} />
                <Route path="/environments/:id" element={<RoleProtectedRoute><EnvironmentDetailPage /></RoleProtectedRoute>} />
                <Route path="/environments/:id/edit" element={<RoleProtectedRoute><EnvironmentSetupPage /></RoleProtectedRoute>} />
                <Route path="/environments/:id/restore" element={<RoleProtectedRoute><RestorePage /></RoleProtectedRoute>} />
                <Route path="/workflows" element={<RoleProtectedRoute><WorkflowsPage /></RoleProtectedRoute>} />
                <Route path="/workflows/:id" element={<RoleProtectedRoute><WorkflowDetailPage /></RoleProtectedRoute>} />
                <Route path="/executions" element={<RoleProtectedRoute><ExecutionsPage /></RoleProtectedRoute>} />
                <Route path="/snapshots" element={<RoleProtectedRoute><SnapshotsPage /></RoleProtectedRoute>} />
                <Route path="/deployments" element={<RoleProtectedRoute><DeploymentsPage /></RoleProtectedRoute>} />
                <Route path="/deployments/:id" element={<RoleProtectedRoute><DeploymentDetailPage /></RoleProtectedRoute>} />
                <Route path="/pipelines" element={<Navigate to="/deployments?tab=pipelines" replace />} />
                <Route path="/pipelines/new" element={<RoleProtectedRoute><PipelineEditorPage /></RoleProtectedRoute>} />
                <Route path="/pipelines/:id" element={<RoleProtectedRoute><PipelineEditorPage /></RoleProtectedRoute>} />
                <Route path="/deployments/new" element={<RoleProtectedRoute><NewDeploymentPage /></RoleProtectedRoute>} />
                <Route path="/observability" element={<RoleProtectedRoute><ObservabilityPage /></RoleProtectedRoute>} />
                <Route path="/alerts" element={<RoleProtectedRoute><AlertsPage /></RoleProtectedRoute>} />
                <Route path="/activity" element={<RoleProtectedRoute><ActivityCenterPage /></RoleProtectedRoute>} />
                <Route path="/activity/:id" element={<RoleProtectedRoute><ActivityDetailPage /></RoleProtectedRoute>} />
                <Route path="/n8n-users" element={<RoleProtectedRoute><N8NUsersPage /></RoleProtectedRoute>} />
                <Route path="/credentials" element={<RoleProtectedRoute><CredentialsPage /></RoleProtectedRoute>} />
                <Route path="/incidents" element={<RoleProtectedRoute><IncidentsPage /></RoleProtectedRoute>} />
                <Route path="/incidents/:id" element={<RoleProtectedRoute><IncidentDetailPage /></RoleProtectedRoute>} />
                <Route path="/drift-dashboard" element={<RoleProtectedRoute><DriftDashboardPage /></RoleProtectedRoute>} />

                {/* Org Admin */}
                <Route path="/admin" element={<RoleProtectedRoute><Navigate to="/admin/members" replace /></RoleProtectedRoute>} />
                <Route path="/admin/members" element={<RoleProtectedRoute><TeamPage /></RoleProtectedRoute>} />
                <Route path="/admin/plans" element={<RoleProtectedRoute><Navigate to="/admin/billing" replace /></RoleProtectedRoute>} />
                <Route path="/admin/billing" element={<RoleProtectedRoute><BillingPage /></RoleProtectedRoute>} />
                <Route path="/admin/usage" element={<RoleProtectedRoute><AdminUsagePage /></RoleProtectedRoute>} />
                <Route path="/admin/feature-matrix" element={<RoleProtectedRoute><AdminEntitlementsPage /></RoleProtectedRoute>} />
                <Route path="/admin/entitlements" element={<RoleProtectedRoute><AdminEntitlementsPage /></RoleProtectedRoute>} />
                <Route path="/admin/credential-health" element={<RoleProtectedRoute><CredentialHealthPage /></RoleProtectedRoute>} />
                <Route path="/admin/settings" element={<RoleProtectedRoute><SecurityPage /></RoleProtectedRoute>} />

                {/* Platform (Hidden) */}
                <Route path="/platform" element={<RoleProtectedRoute><Navigate to="/platform/tenants" replace /></RoleProtectedRoute>} />
                <Route path="/platform/console" element={<RoleProtectedRoute><SupportConsolePage /></RoleProtectedRoute>} />
                <Route path="/platform/tenants" element={<RoleProtectedRoute><TenantsPage /></RoleProtectedRoute>} />
                <Route path="/platform/tenants/:tenantId" element={<RoleProtectedRoute><TenantDetailPage /></RoleProtectedRoute>} />
                <Route path="/platform/tenant-overrides" element={<RoleProtectedRoute><TenantOverridesPage /></RoleProtectedRoute>} />
                <Route path="/platform/entitlements-audit" element={<RoleProtectedRoute><EntitlementsAuditPage /></RoleProtectedRoute>} />
                <Route path="/platform/support/requests" element={<RoleProtectedRoute><SupportRequestsPage /></RoleProtectedRoute>} />
                <Route path="/platform/support/config" element={<RoleProtectedRoute><SupportConfigPage /></RoleProtectedRoute>} />
                <Route path="/platform/settings" element={<RoleProtectedRoute><SettingsPage /></RoleProtectedRoute>} />
                <Route path="/platform/admins" element={<RoleProtectedRoute><PlatformAdminsPage /></RoleProtectedRoute>} />

                {/* Legacy redirects */}
                <Route path="/team" element={<Navigate to="/admin/members" replace />} />
                <Route path="/billing" element={<Navigate to="/admin/billing" replace />} />
                <Route path="/admin/tenants" element={<Navigate to="/platform/tenants" replace />} />
                <Route path="/admin/tenants/:tenantId" element={<RoleProtectedRoute><LegacyPlatformTenantRedirect /></RoleProtectedRoute>} />
                <Route path="/admin/entitlements/overrides" element={<Navigate to="/platform/tenant-overrides" replace />} />
                <Route path="/admin/entitlements/audit" element={<Navigate to="/platform/entitlements-audit" replace />} />
                <Route path="/admin/entitlements-audit" element={<Navigate to="/platform/entitlements-audit" replace />} />
                <Route path="/admin/support" element={<Navigate to="/platform/support/requests" replace />} />
                <Route path="/admin/support-config" element={<Navigate to="/platform/support/config" replace />} />
                <Route path="/admin/audit-logs" element={<Navigate to="/platform/entitlements-audit" replace />} />
                <Route path="/admin/security" element={<Navigate to="/admin/settings" replace />} />
                <Route path="/admin/entitlements/matrix" element={<Navigate to="/admin/feature-matrix" replace />} />
                <Route path="/admin/plans-old" element={<Navigate to="/platform/tenants" replace />} />
                <Route path="/admin/usage-old" element={<Navigate to="/platform/tenants" replace />} />
                <Route path="/admin/billing-old" element={<Navigate to="/platform/tenants" replace />} />

                <Route path="/profile" element={<RoleProtectedRoute><ProfilePage /></RoleProtectedRoute>} />
                {/* Support Routes */}
                <Route path="/support" element={<RoleProtectedRoute><SupportHomePage /></RoleProtectedRoute>} />
                <Route path="/support/bug/new" element={<RoleProtectedRoute><ReportBugPage /></RoleProtectedRoute>} />
                <Route path="/support/feature/new" element={<RoleProtectedRoute><RequestFeaturePage /></RoleProtectedRoute>} />
                <Route path="/support/help/new" element={<RoleProtectedRoute><GetHelpPage /></RoleProtectedRoute>} />
              </Route>
              </Routes>
            </BrowserRouter>
            <Toaster
              position="top-right"
              expand={true}
              richColors={false}
              toastOptions={{
                classNames: {
                  toast: '!rounded-lg !shadow-lg !border-l-4 !font-medium !px-4 !py-3 !text-sm',
                  success: '!bg-green-50 dark:!bg-green-950/90 !text-green-900 dark:!text-green-50 !border-green-500',
                  error: '!bg-red-50 dark:!bg-red-950/90 !text-red-900 dark:!text-red-50 !border-red-500',
                },
              }}
            />
          </FeaturesProvider>
        </AuthProvider>
      </ErrorBoundary>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
    </ThemeProvider>
  );
}

export default App;
