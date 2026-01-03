// @ts-nocheck
// TODO: Fix TypeScript errors in this file
import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { useAuth } from '@/lib/auth';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Checkbox } from '@/components/ui/checkbox';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Loader2, ShieldAlert, UserPlus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

type PlatformAdminRow = {
  user: { id: string; email: string; name?: string | null };
  granted_at?: string | null;
  granted_by?: { id: string; email: string; name?: string | null } | null;
};

export function PlatformAdminsPage() {
  useEffect(() => {
    document.title = 'Platform Admins - WorkflowOps';
    return () => {
      document.title = 'WorkflowOps';
    };
  }, []);

  const { user } = useAuth();
  const queryClient = useQueryClient();

  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [confirmed, setConfirmed] = useState(false);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['platform-admins'],
    queryFn: () => apiClient.getPlatformAdmins(),
  });

  const admins: PlatformAdminRow[] = data?.data?.admins || [];
  
  // Extract error message for better debugging
  const errorMessage = error ? (error as any)?.response?.data?.detail || (error as any)?.message || 'Unknown error' : null;

  const isLastPlatformAdmin = useMemo(() => {
    const me = user?.id;
    if (!me) return false;
    return admins.length === 1 && admins[0]?.user?.id === me;
  }, [admins, user?.id]);

  const addMutation = useMutation({
    mutationFn: async () => {
      if (!email.trim()) throw new Error('Email is required');
      return apiClient.addPlatformAdmin({ email: email.trim() });
    },
    onSuccess: () => {
      toast.success('Platform Admin granted');
      queryClient.invalidateQueries({ queryKey: ['platform-admins'] });
      setOpen(false);
      setEmail('');
      setConfirmed(false);
    },
    onError: (e: any) => {
      toast.error(e?.response?.data?.detail || e?.message || 'Failed to add Platform Admin');
    },
  });

  const removeMutation = useMutation({
    mutationFn: async (targetUserId: string) => apiClient.removePlatformAdmin(targetUserId),
    onSuccess: () => {
      toast.success('Platform Admin removed');
      queryClient.invalidateQueries({ queryKey: ['platform-admins'] });
    },
    onError: (e: any) => {
      toast.error(e?.response?.data?.detail || 'Failed to remove Platform Admin');
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Platform Admins</h1>
          <p className="text-muted-foreground">
            Users with full, cross-tenant administrative access to WorkflowOps. This access applies globally across all organizations.
          </p>
        </div>
        <Button onClick={() => setOpen(true)}>
          <UserPlus className="h-4 w-4 mr-2" />
          Add Platform Admin
        </Button>
      </div>

      <Alert variant="destructive">
        <ShieldAlert className="h-4 w-4" />
        <AlertDescription>
          Platform Admins can view and modify any tenant. Grant sparingly.
        </AlertDescription>
      </Alert>

      <Card>
        <CardHeader>
          <CardTitle>Platform Admins</CardTitle>
          <CardDescription>{admins.length} users</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center h-40">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : isError ? (
            <div className="space-y-2">
              <div className="text-sm text-destructive font-medium">Failed to load Platform Admins.</div>
              {errorMessage && (
                <div className="text-xs text-muted-foreground">
                  Error: {errorMessage}
                </div>
              )}
              {(error as any)?.response?.status === 403 && (
                <div className="text-xs text-muted-foreground">
                  You must be a Platform Admin to view this page. Please ensure you are logged in as a Platform Admin.
                </div>
              )}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Granted At</TableHead>
                  <TableHead>Granted By</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {admins.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-muted-foreground">
                      No Platform Admins found.
                    </TableCell>
                  </TableRow>
                ) : (
                  admins.map((a) => {
                    const isSelf = a.user.id === user?.id;
                    const disableRemove = isSelf && isLastPlatformAdmin;
                    return (
                      <TableRow key={a.user.id}>
                        <TableCell>{a.user.name || '—'}</TableCell>
                        <TableCell className="font-mono text-sm">{a.user.email}</TableCell>
                        <TableCell>{a.granted_at ? new Date(a.granted_at).toLocaleString() : '—'}</TableCell>
                        <TableCell>{a.granted_by?.email || '—'}</TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => removeMutation.mutate(a.user.id)}
                            disabled={removeMutation.isPending || disableRemove}
                            title={disableRemove ? 'You cannot remove yourself as the last Platform Admin' : undefined}
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Remove access
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add Platform Admin</DialogTitle>
            <DialogDescription>
              User must already exist. This grants global platform access.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Email</Label>
              <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="user@company.com" />
            </div>

            <div className="flex items-start gap-2">
              <Checkbox checked={confirmed} onCheckedChange={(v) => setConfirmed(!!v)} />
              <div className="text-sm">
                I understand this grants global platform access.
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)} disabled={addMutation.isPending}>
              Cancel
            </Button>
            <Button
              onClick={() => addMutation.mutate()}
              disabled={addMutation.isPending || !confirmed || !email.trim()}
            >
              {addMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Adding...
                </>
              ) : (
                'Add Platform Admin'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}


