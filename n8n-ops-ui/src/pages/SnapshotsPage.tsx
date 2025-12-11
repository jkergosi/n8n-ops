import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams, Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Camera, History, RotateCcw, Loader2, Eye } from 'lucide-react';
import { toast } from 'sonner';
import { apiClient } from '@/lib/api-client';
import { useAppStore } from '@/store/use-app-store';
import type { Snapshot } from '@/types';

export function SnapshotsPage() {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedEnvironment = useAppStore((state) => state.selectedEnvironment);
  const [selectedSnapshot, setSelectedSnapshot] = useState<Snapshot | null>(null);
  const [restoreSnapshot, setRestoreSnapshot] = useState<Snapshot | null>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);

  // Get snapshot ID from URL if present
  const snapshotIdFromUrl = searchParams.get('snapshot');

  // Fetch environments
  const { data: environments } = useQuery({
    queryKey: ['environments'],
    queryFn: () => apiClient.getEnvironments(),
  });

  // Get current environment ID (use selectedEnvironment or first available)
  const currentEnvironmentId = selectedEnvironment || environments?.data?.[0]?.id;

  // Fetch snapshots for current environment
  const { data: snapshots, isLoading } = useQuery({
    queryKey: ['snapshots', currentEnvironmentId],
    queryFn: () =>
      apiClient.getSnapshots({
        environmentId: currentEnvironmentId,
      }),
    enabled: !!currentEnvironmentId,
  });

  // Fetch specific snapshot if ID in URL
  const { data: snapshotDetail } = useQuery({
    queryKey: ['snapshot', snapshotIdFromUrl],
    queryFn: () => apiClient.getSnapshot(snapshotIdFromUrl!),
    enabled: !!snapshotIdFromUrl,
  });

  // Open detail dialog if snapshot ID in URL
  useEffect(() => {
    if (snapshotDetail?.data) {
      setSelectedSnapshot(snapshotDetail.data);
      setDetailDialogOpen(true);
    }
  }, [snapshotDetail]);

  // Restore mutation
  const restoreMutation = useMutation({
    mutationFn: (snapshotId: string) => apiClient.restoreSnapshot(snapshotId),
    onSuccess: (response) => {
      toast.success(response.data.message || 'Snapshot restored successfully');
      queryClient.invalidateQueries({ queryKey: ['snapshots'] });
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      setRestoreSnapshot(null);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to restore snapshot');
    },
  });

  const handleViewDetails = (snapshot: Snapshot) => {
    setSelectedSnapshot(snapshot);
    setDetailDialogOpen(true);
  };

  const handleRestore = (snapshot: Snapshot) => {
    setRestoreSnapshot(snapshot);
  };

  const confirmRestore = () => {
    if (restoreSnapshot) {
      restoreMutation.mutate(restoreSnapshot.id);
    }
  };

  const formatSnapshotType = (type: string) => {
    switch (type) {
      case 'auto_backup':
        return 'Auto backup';
      case 'pre_promotion':
        return 'Pre-promotion';
      case 'post_promotion':
        return 'Post-promotion';
      case 'manual_backup':
        return 'Manual backup';
      default:
        return type;
    }
  };

  const getTypeBadgeVariant = (type: string) => {
    switch (type) {
      case 'pre_promotion':
      case 'post_promotion':
        return 'default';
      case 'auto_backup':
        return 'secondary';
      case 'manual_backup':
        return 'outline';
      default:
        return 'outline';
    }
  };

  const getEnvironmentName = (envId: string) => {
    return environments?.data?.find((e) => e.id === envId)?.name || envId;
  };

  const snapshotsList = snapshots?.data || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Snapshots</h1>
          <p className="text-muted-foreground">
            Version control and rollback for your workflows
          </p>
        </div>
      </div>

      {/* Environment Selector */}
      {environments?.data && environments.data.length > 1 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Environment</CardTitle>
          </CardHeader>
          <CardContent>
            <Select
              value={currentEnvironmentId || ''}
              onValueChange={(value) => {
                useAppStore.getState().setSelectedEnvironment(value);
              }}
            >
              <SelectTrigger className="w-[300px]">
                <SelectValue placeholder="Select environment" />
              </SelectTrigger>
              <SelectContent>
                {environments.data.map((env) => (
                  <SelectItem key={env.id} value={env.id}>
                    {env.name} {env.type ? `(${env.type})` : ''}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </CardContent>
        </Card>
      )}

      {/* Snapshot History Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <History className="h-5 w-5" />
            Snapshot History
          </CardTitle>
          <CardDescription>
            {currentEnvironmentId
              ? `Snapshots for ${getEnvironmentName(currentEnvironmentId)}`
              : 'Select an environment to view snapshots'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!currentEnvironmentId ? (
            <p className="text-muted-foreground text-center py-8">
              Select an environment above to view its snapshot history
            </p>
          ) : isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
              <span className="ml-2">Loading snapshots...</span>
            </div>
          ) : snapshotsList.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">
              No snapshots found for this environment. Snapshots are created automatically
              during promotions and manual backups.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Created At</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Triggered By</TableHead>
                  <TableHead>Deployment</TableHead>
                  <TableHead>Notes</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {snapshotsList.map((snapshot) => (
                  <TableRow key={snapshot.id}>
                    <TableCell className="text-muted-foreground">
                      {new Date(snapshot.createdAt).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Badge variant={getTypeBadgeVariant(snapshot.type)}>
                        {formatSnapshotType(snapshot.type)}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {snapshot.createdByUserId || 'System'}
                    </TableCell>
                    <TableCell>
                      {snapshot.relatedDeploymentId ? (
                        <Link
                          to={`/deployments?deployment=${snapshot.relatedDeploymentId}`}
                          className="text-primary hover:underline"
                        >
                          #{snapshot.relatedDeploymentId.substring(0, 8)}...
                        </Link>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {snapshot.metadataJson?.reason || '—'}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleViewDetails(snapshot)}
                        >
                          <Eye className="h-3 w-3 mr-1" />
                          View
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleRestore(snapshot)}
                        >
                          <RotateCcw className="h-3 w-3 mr-1" />
                          Restore
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Snapshot Detail Dialog */}
      <Dialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Snapshot Details</DialogTitle>
            <DialogDescription>View detailed information about this snapshot</DialogDescription>
          </DialogHeader>

          {selectedSnapshot && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Environment</p>
                  <p className="text-base">{getEnvironmentName(selectedSnapshot.environmentId)}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Type</p>
                  <Badge variant={getTypeBadgeVariant(selectedSnapshot.type)}>
                    {formatSnapshotType(selectedSnapshot.type)}
                  </Badge>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Created At</p>
                  <p className="text-base">
                    {new Date(selectedSnapshot.createdAt).toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Triggered By</p>
                  <p className="text-base">{selectedSnapshot.createdByUserId || 'System'}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Git Commit SHA</p>
                  <p className="text-base font-mono text-sm">
                    {selectedSnapshot.gitCommitSha || '—'}
                  </p>
                </div>
                {selectedSnapshot.relatedDeploymentId && (
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Deployment</p>
                    <Link
                      to={`/deployments?deployment=${selectedSnapshot.relatedDeploymentId}`}
                      className="text-primary hover:underline"
                    >
                      #{selectedSnapshot.relatedDeploymentId.substring(0, 8)}...
                    </Link>
                  </div>
                )}
              </div>

              {selectedSnapshot.metadataJson && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-2">Metadata</p>
                  <div className="bg-muted p-3 rounded-md">
                    <pre className="text-xs overflow-auto">
                      {JSON.stringify(selectedSnapshot.metadataJson, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Restore Confirmation Dialog */}
      <AlertDialog
        open={!!restoreSnapshot}
        onOpenChange={(open) => !open && setRestoreSnapshot(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirm Restore</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to restore the environment to this snapshot?
              <br />
              <br />
              This will replace all workflows in the environment with the versions from this
              snapshot. A new backup snapshot will be created automatically before the restore.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmRestore}
              disabled={restoreMutation.isPending}
            >
              {restoreMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Restoring...
                </>
              ) : (
                <>
                  <RotateCcw className="h-4 w-4 mr-2" />
                  Restore
                </>
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
