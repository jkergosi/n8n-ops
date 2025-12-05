import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '@/lib/auth';
import { useAppStore } from '@/store/use-app-store';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ThemeToggle } from '@/components/ThemeToggle';
import {
  LayoutDashboard,
  Server,
  Workflow,
  ListChecks,
  Tag,
  Camera,
  Rocket,
  Activity,
  Users,
  UserCog,
  CreditCard,
  LogOut,
  Menu,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Environments', href: '/environments', icon: Server },
  { name: 'Workflows', href: '/workflows', icon: Workflow },
  { name: 'Executions', href: '/executions', icon: ListChecks },
  { name: 'Tags', href: '/tags', icon: Tag },
  { name: 'Snapshots', href: '/snapshots', icon: Camera },
  { name: 'Deployments', href: '/deployments', icon: Rocket },
  { name: 'Observability', href: '/observability', icon: Activity },
  { name: 'N8N Users', href: '/n8n-users', icon: UserCog },
  { name: 'Team', href: '/team', icon: Users },
  { name: 'Billing', href: '/billing', icon: CreditCard },
];

export function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { sidebarOpen, toggleSidebar } = useAppStore();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar */}
      <div
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 bg-card border-r transform transition-transform duration-200 ease-in-out',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center justify-between h-16 px-6 border-b">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
                <Workflow className="h-5 w-5 text-primary-foreground" />
              </div>
              <span className="text-lg font-bold">N8N Ops</span>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={toggleSidebar}
            >
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
            {navigation.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.href;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-colors',
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'text-foreground/80 hover:bg-accent hover:text-accent-foreground'
                  )}
                >
                  <Icon className="h-5 w-5" />
                  {item.name}
                </Link>
              );
            })}
          </nav>

          {/* User Info & Logout */}
          <div className="p-4 border-t">
            <div className="flex items-center justify-between mb-3">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{user?.name}</p>
                <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 mb-3">
              <Badge variant="outline" className="text-xs">
                {user?.subscriptionTier}
              </Badge>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={handleLogout}
            >
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div
        className={cn(
          'transition-all duration-200',
          sidebarOpen ? 'lg:pl-64' : 'pl-0'
        )}
      >
        {/* Top Bar */}
        <div className="sticky top-0 z-40 h-16 bg-card border-b">
          <div className="flex items-center justify-between h-full px-6">
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleSidebar}
            >
              <Menu className="h-5 w-5" />
            </Button>

            <div className="flex items-center gap-4">
              <Badge variant="outline">
                Environment: <span className="ml-1 font-semibold">dev</span>
              </Badge>
              <ThemeToggle />
            </div>
          </div>
        </div>

        {/* Page Content */}
        <main className="p-6">
          <Outlet />
        </main>
      </div>

      {/* Mobile Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={toggleSidebar}
        />
      )}
    </div>
  );
}
