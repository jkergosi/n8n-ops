// @ts-nocheck
// TODO: Fix TypeScript errors in this file
import { useEffect, useMemo, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { useAuth } from '@/lib/auth';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, UserCog } from 'lucide-react';
import { toast } from 'sonner';

export function SupportConsolePage() {
  useEffect(() => {
    document.title = 'Support Console - WorkflowOps';
    return () => {
      document.title = 'WorkflowOps';
    };
  }, []);

  const { startImpersonation } = useAuth();

  const [tenantName, setTenantName] = useState('');
  const [tenantSlug, setTenantSlug] = useState('');
  const [tenantId, setTenantId] = useState('');
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(null);

  const [userEmail, setUserEmail] = useState('');
  const [userName, setUserName] = useState('');
  const [userId, setUserId] = useState('');

  const tenantsMutation = useMutation({
    mutationFn: async () =>
      apiClient.consoleSearchTenants({
        name: tenantName.trim() || undefined,
        slug: tenantSlug.trim() || undefined,
        tenant_id: tenantId.trim() || undefined,
        limit: 25,
      }),
    onError: (e: any) => toast.error(e?.response?.data?.detail || 'Failed to search tenants'),
  });

  const usersMutation = useMutation({
    mutationFn: async (tenantFilter?: string | null) =>
      apiClient.consoleSearchUsers({
        email: userEmail.trim() || undefined,
        name: userName.trim() || undefined,
        user_id: userId.trim() || undefined,
        tenant_id: tenantFilter || undefined,
        limit: 50,
      }),
    onError: (e: any) => toast.error(e?.response?.data?.detail || 'Failed to search users'),
  });

  const tenants = tenantsMutation.data?.data?.tenants || [];
  const users = usersMutation.data?.data?.users || [];

  const effectiveTenantFilter = useMemo(() => selectedTenantId || null, [selectedTenantId]);

  const onSearchTenants = async () => {
    setSelectedTenantId(null);
    await tenantsMutation.mutateAsync();
  };

  const onSearchUsers = async () => {
    await usersMutation.mutateAsync(effectiveTenantFilter);
  };

  const onListUsersForTenant = async (tid: string) => {
    setSelectedTenantId(tid);
    await usersMutation.mutateAsync(tid);
  };

  const onImpersonate = async (targetUserId: string, isPlatformAdmin: boolean) => {
    if (isPlatformAdmin) {
      toast.error('Cannot impersonate another Platform Admin');
      return;
    }
    try {
      await startImpersonation(targetUserId);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || e?.message || 'Failed to start impersonation');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Support Console</h1>
        <p className="text-muted-foreground">
          Search tenants and users, then start an auditable impersonation session.
        </p>
      </div>

      <Alert>
        <AlertDescription>
          Impersonation is platform-only and should be used for support. You cannot impersonate another Platform Admin.
        </AlertDescription>
      </Alert>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Tenant Search</CardTitle>
            <CardDescription>Search by name, slug, or tenant ID</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <Label>Tenant name</Label>
                <Input value={tenantName} onChange={(e) => setTenantName(e.target.value)} placeholder="Acme" />
              </div>
              <div className="space-y-2">
                <Label>Tenant slug</Label>
                <Input value={tenantSlug} onChange={(e) => setTenantSlug(e.target.value)} placeholder="acme" />
              </div>
              <div className="space-y-2">
                <Label>Tenant ID</Label>
                <Input value={tenantId} onChange={(e) => setTenantId(e.target.value)} placeholder="UUID" />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button onClick={onSearchTenants} disabled={tenantsMutation.isPending}>
                {tenantsMutation.isPending ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                Search Tenants
              </Button>
              {selectedTenantId && (
                <Button variant="outline" onClick={() => setSelectedTenantId(null)}>
                  Clear Tenant Filter
                </Button>
              )}
            </div>

            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tenant Name</TableHead>
                  <TableHead>Tenant ID</TableHead>
                  <TableHead>Plan</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tenants.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-muted-foreground">
                      No tenant results.
                    </TableCell>
                  </TableRow>
                ) : (
                  tenants.map((t: any) => (
                    <TableRow key={t.id}>
                      <TableCell>{t.name || '—'}</TableCell>
                      <TableCell className="font-mono text-sm">{t.id}</TableCell>
                      <TableCell>{t.subscription_tier || 'free'}</TableCell>
                      <TableCell className="text-right">
                        <Button size="sm" variant="outline" onClick={() => onListUsersForTenant(t.id)}>
                          List Users
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>User Search</CardTitle>
            <CardDescription>Search by email, name, or user ID{selectedTenantId ? ' (filtered by tenant)' : ''}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <Label>Email</Label>
                <Input value={userEmail} onChange={(e) => setUserEmail(e.target.value)} placeholder="jane@customer.com" />
              </div>
              <div className="space-y-2">
                <Label>Name</Label>
                <Input value={userName} onChange={(e) => setUserName(e.target.value)} placeholder="Jane Doe" />
              </div>
              <div className="space-y-2">
                <Label>User ID</Label>
                <Input value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="UUID" />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button onClick={onSearchUsers} disabled={usersMutation.isPending}>
                {usersMutation.isPending ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                Search Users
              </Button>
              {selectedTenantId && (
                <div className="text-xs text-muted-foreground">
                  Tenant filter: <span className="font-mono">{selectedTenantId}</span>
                </div>
              )}
            </div>

            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Tenant</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-muted-foreground">
                      No user results.
                    </TableCell>
                  </TableRow>
                ) : (
                  users.map((u: any) => (
                    <TableRow key={u.id}>
                      <TableCell>{u.name || '—'}</TableCell>
                      <TableCell className="font-mono text-sm">{u.email}</TableCell>
                      <TableCell>{u.tenant?.name || u.tenant?.slug || u.tenant?.id || '—'}</TableCell>
                      <TableCell>{u.is_platform_admin ? 'platform_admin' : (u.role || 'viewer')}</TableCell>
                      <TableCell className="text-right">
                        <Button
                          size="sm"
                          onClick={() => onImpersonate(u.id, !!u.is_platform_admin)}
                          disabled={!!u.is_platform_admin}
                        >
                          <UserCog className="h-4 w-4 mr-2" />
                          Impersonate
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}


