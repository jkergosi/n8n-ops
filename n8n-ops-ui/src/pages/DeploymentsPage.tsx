// @ts-nocheck
// TODO: Fix TypeScript errors in this file
import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { apiClient } from '@/lib/api-client';
import { useDeploymentsSSE } from '@/lib/use-deployments-sse';
import { Rocket, ArrowRight, Clock, CheckCircle, AlertCircle, XCircle, Loader2, Trash2, Radio } from 'lucide-react';
import type { Deployment } from '@/types';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Link } from 'react-router-dom';
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

export function DeploymentsPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deploymentToDelete, setDeploymentToDelete] = useState<Deployment | null>(null);

  // Force refetch when navigating to this page (e.g., after creating a deployment)
  useEffect(() => {
    queryClient.invalidateQueries({ queryKey: ['deployments'] });
  }, [location.key, queryClient]);

  const { data: deploymentsData, isLoading } = useQuery({
    queryKey: ['deployments'],
    queryFn: () => apiClient.getDeployments(),
    // SSE handles real-time updates, so we can use longer stale time
    staleTime: 30000, // 30 seconds
    // Only refetch on window focus as a fallback
    refetchOnWindowFocus: true,
  });

  // Use SSE for real-time updates (replaces polling)
  const { isConnected: sseConnected } = useDeploymentsSSE({ enabled: !isLoading });

  const { data: environments } = useQuery({
    queryKey: ['environments'],
    queryFn: () => apiClient.getEnvironments(),
  });

  const { data: pipelines } = useQuery({
    queryKey: ['pipelines'],
    queryFn: () => apiClient.getPipelines(),
  });

  const deployments = deploymentsData?.data?.deployments || [];
  const summary = deploymentsData?.data || {
    thisWeekSuccessCount: 0,
    pendingApprovalsCount: 0,
    runningCount: 0,
  };

  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'success':
        return 'success';
      case 'failed':
        return 'destructive';
      case 'running':
        return 'secondary';
      case 'pending':
        return 'outline';
      case 'canceled':
        return 'outline';
      default:
        return 'outline';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'running':
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
      case 'pending':
        return <Clock className="h-4 w-4 text-amber-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getEnvironmentName = (envId: string) => {
    return environments?.data?.find((e) => e.id === envId)?.name || envId;
  };

  const getPipelineName = (pipelineId?: string) => {
    if (!pipelineId) return '—';
    return pipelines?.data?.find((p) => p.id === pipelineId)?.name || pipelineId;
  };

  const getProgress = (deployment: Deployment) => {
    // Use backend-calculated progress fields if available
    // For completed deployments, backend calculates successful (created + updated)
    // For running deployments, backend calculates processed count
    const total = deployment.progressTotal ?? deployment.summaryJson?.total ?? 0;
    let current = deployment.progressCurrent;
    
    // Fallback to calculating from summary_json if backend fields not available
    if (current === undefined) {
      const summary = deployment.summaryJson || {};
      if (deployment.status === 'success' || deployment.status === 'failed') {
        // For completed: successful = created + updated
        current = (summary.created || 0) + (summary.updated || 0);
      } else if (deployment.status === 'running') {
        // For running: use processed count
        current = summary.processed || 0;
        if (total) {
          current = Math.min(current + 1, total);
        }
      } else {
        current = 0;
      }
    }
    
    return { current, total };
  };

  const formatDuration = (startedAt: string, finishedAt?: string) => {
    const start = new Date(startedAt).getTime();
    const end = finishedAt ? new Date(finishedAt).getTime() : Date.now();
    const seconds = Math.round((end - start) / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  const handlePromoteWorkflows = () => {
    navigate('/promote');
  };

  const deleteMutation = useMutation({
    mutationFn: (deploymentId: string) => apiClient.deleteDeployment(deploymentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deployments'] });
      toast.success('Deployment deleted successfully');
      setDeleteDialogOpen(false);
      setDeploymentToDelete(null);
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to delete deployment');
    },
  });

  const handleDeleteClick = (e: React.MouseEvent, deployment: Deployment) => {
    e.stopPropagation();
    setDeploymentToDelete(deployment);
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = () => {
    if (deploymentToDelete) {
      deleteMutation.mutate(deploymentToDelete.id);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Deployments</h1>
          <p className="text-muted-foreground">
            Track workflow deployments across environments
          </p>
        </div>
        <Button onClick={handlePromoteWorkflows}>
          <Rocket className="h-4 w-4 mr-2" />
          New Deployment
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-6 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Running Now</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              {summary.runningCount > 0 ? (
                <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
              ) : (
                <Radio className="h-5 w-5 text-muted-foreground" />
              )}
              <span className="text-2xl font-bold">{summary.runningCount || 0}</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Active deployments
              {sseConnected && <span className="ml-1 text-green-500">&#8226; Live</span>}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">This Week</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-500" />
              <span className="text-2xl font-bold">{summary.thisWeekSuccessCount}</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Successful deployments
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Pending Approvals</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-amber-500" />
              <span className="text-2xl font-bold">{summary.pendingApprovalsCount}</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Workflows awaiting approval
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Promotion Mode</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Rocket className="h-5 w-5 text-blue-500" />
              <span className="text-lg font-semibold">Manual</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              One-click promotion
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Deployment History Table */}
      <Card>
        <CardHeader>
          <CardTitle>Deployment History</CardTitle>
          <CardDescription>Recent workflow deployments and promotions</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8">Loading deployments...</div>
          ) : deployments.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Rocket className="h-12 w-12 mx-auto mb-4 opacity-20" />
              <p>No deployments yet</p>
              <Button variant="link" onClick={handlePromoteWorkflows} className="mt-2">
                Create your first deployment
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Pipeline</TableHead>
                  <TableHead>Stage</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {deployments.map((deployment) => {
                  const { current: progressCurrent, total: progressTotal } = getProgress(deployment);
                  const progressText = progressTotal > 0 ? `${progressCurrent} of ${progressTotal}` : null;

                  return (
                    <TableRow key={deployment.id}>
                      <TableCell>
                        <Link
                          to={`/deployments/${deployment.id}`}
                          className="text-primary hover:underline"
                        >
                          {getPipelineName(deployment.pipelineId)}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">
                            {getEnvironmentName(deployment.sourceEnvironmentId)}
                          </Badge>
                          <ArrowRight className="h-3 w-3" />
                          <Badge variant="outline">
                            {getEnvironmentName(deployment.targetEnvironmentId)}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-col items-center gap-1">
                          <Badge variant={getStatusVariant(deployment.status)}>
                            {deployment.status}
                          </Badge>
                          {progressText && (
                            <span className="text-xs text-muted-foreground">
                              {progressText}
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {new Date(deployment.startedAt).toLocaleString()}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDuration(deployment.startedAt, deployment.finishedAt)}
                      </TableCell>
                      <TableCell>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={(e) => handleDeleteClick(e, deployment)}
                          disabled={deployment.status === 'running'}
                          className="h-8 w-8"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Deployment</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this deployment? This action cannot be undone.
              {deploymentToDelete && (
                <div className="mt-2 space-y-1">
                  <p className="font-medium">Deployment Details:</p>
                  <p className="text-sm">
                    {deploymentToDelete.summaryJson?.total || 0} workflow(s) deployed from{' '}
                    {getEnvironmentName(deploymentToDelete.sourceEnvironmentId)} to{' '}
                    {getEnvironmentName(deploymentToDelete.targetEnvironmentId)}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Started: {new Date(deploymentToDelete.startedAt).toLocaleString()}
                  </p>
                </div>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              disabled={deleteMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
