import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { AuthProvider, useAuth } from '@/lib/auth';
import { ThemeProvider } from '@/components/ThemeProvider';
import { Toaster } from 'sonner';
import { AppLayout } from '@/components/AppLayout';
import { LoginPage } from '@/pages/LoginPage';
import { OnboardingPage } from '@/pages/OnboardingPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { EnvironmentsPage } from '@/pages/EnvironmentsPage';
import { WorkflowsPage } from '@/pages/WorkflowsPage';
import { ExecutionsPage } from '@/pages/ExecutionsPage';
import { TagsPage } from '@/pages/TagsPage';
import { SnapshotsPage } from '@/pages/SnapshotsPage';
import { DeploymentsPage } from '@/pages/DeploymentsPage';
import { ObservabilityPage } from '@/pages/ObservabilityPage';
import { TeamPage } from '@/pages/TeamPage';
import { BillingPage } from '@/pages/BillingPage';
import { N8NUsersPage } from '@/pages/N8NUsersPage';
import { useEffect } from 'react';

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
  const { isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (isAuthenticated && !loading) {
      const onboardingComplete = localStorage.getItem('onboarding_complete');
      if (!onboardingComplete && window.location.pathname !== '/onboarding') {
        navigate('/onboarding');
      }
    }
  }, [isAuthenticated, loading, navigate]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]"></div>
          <p className="mt-4 text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

function App() {
  return (
    <ThemeProvider defaultTheme="system" storageKey="n8n-ops-theme">
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <BrowserRouter>
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
                <Route path="/" element={<DashboardPage />} />
                <Route path="/environments" element={<EnvironmentsPage />} />
                <Route path="/workflows" element={<WorkflowsPage />} />
                <Route path="/executions" element={<ExecutionsPage />} />
                <Route path="/tags" element={<TagsPage />} />
                <Route path="/snapshots" element={<SnapshotsPage />} />
                <Route path="/deployments" element={<DeploymentsPage />} />
                <Route path="/observability" element={<ObservabilityPage />} />
                <Route path="/n8n-users" element={<N8NUsersPage />} />
                <Route path="/team" element={<TeamPage />} />
                <Route path="/billing" element={<BillingPage />} />
              </Route>
            </Routes>
          </BrowserRouter>
          <Toaster position="top-right" />
        </AuthProvider>
        <ReactQueryDevtools initialIsOpen={false} />
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export default App;
