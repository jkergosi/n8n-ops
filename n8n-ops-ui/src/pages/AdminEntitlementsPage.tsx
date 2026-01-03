// @ts-nocheck
// TODO: Fix TypeScript errors in this file
import { useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Loader2 } from 'lucide-react';

function renderValue(value: any) {
  if (typeof value === 'boolean') return value ? 'Enabled' : 'Disabled';
  if (value === null || value === undefined) return '—';
  if (typeof value === 'number') return String(value);
  if (typeof value === 'string') return value;
  return JSON.stringify(value);
}

export function AdminEntitlementsPage() {
  useEffect(() => {
    document.title = 'Entitlements - WorkflowOps';
    return () => {
      document.title = 'WorkflowOps';
    };
  }, []);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['auth-status'],
    queryFn: () => apiClient.getAuthStatus(),
    retry: 1,
  });

  const entitlements = data?.data?.entitlements || null;
  const plan = (data?.data?.tenant?.subscription_plan || 'free')?.toString?.() || 'free';

  const rows = useMemo(() => {
    const features = entitlements?.features || {};
    return Object.keys(features)
      .sort()
      .map((k) => ({ key: k, value: features[k] }));
  }, [entitlements]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Entitlements</h1>
          <p className="text-muted-foreground">Failed to load entitlements.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Entitlements</h1>
          <p className="text-muted-foreground">Your organization feature access and limits</p>
        </div>
        <Badge variant="secondary" className="capitalize">
          Plan: {plan}
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Feature Matrix (Tenant)</CardTitle>
          <CardDescription>Current effective entitlements for this tenant</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Key</TableHead>
                <TableHead>Value</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={2} className="text-muted-foreground">
                    No entitlements found.
                  </TableCell>
                </TableRow>
              ) : (
                rows.map((r) => (
                  <TableRow key={r.key}>
                    <TableCell className="font-mono text-sm">{r.key}</TableCell>
                    <TableCell>{renderValue(r.value)}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}


