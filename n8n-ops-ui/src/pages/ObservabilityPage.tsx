import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { apiClient } from '@/lib/api-client';
import type { TimeRange, EnvironmentStatus, DriftState } from '@/types';
import {
  Activity,
  TrendingUp,
  TrendingDown,
  AlertCircle,
  Clock,
  RefreshCw,
  CheckCircle,
  XCircle,
  Minus,
  Server,
  Loader2,
  ArrowRight,
  Camera,
  Rocket,
  GitCompare,
} from 'lucide-react';

const TIME_RANGE_OPTIONS: { value: TimeRange; label: string }[] = [
  { value: '1h', label: 'Last 1 hour' },
  { value: '6h', label: 'Last 6 hours' },
  { value: '24h', label: 'Last 24 hours' },
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
];

function getStatusBadgeVariant(status: EnvironmentStatus): 'success' | 'warning' | 'destructive' {
  switch (status) {
    case 'healthy':
      return 'success';
    case 'degraded':
      return 'warning';
    case 'unreachable':
      return 'destructive';
    default:
      return 'warning';
  }
}

function getStatusIcon(status: EnvironmentStatus) {
  switch (status) {
    case 'healthy':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'degraded':
      return <AlertCircle className="h-4 w-4 text-yellow-500" />;
    case 'unreachable':
      return <XCircle className="h-4 w-4 text-red-500" />;
    default:
      return <Minus className="h-4 w-4 text-gray-500" />;
  }
}

function getDriftBadgeVariant(drift: DriftState): 'success' | 'warning' | 'outline' {
  switch (drift) {
    case 'in_sync':
      return 'success';
    case 'drift':
      return 'warning';
    case 'unknown':
    default:
      return 'outline';
  }
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

function formatDelta(value: number | undefined, suffix: string = ''): React.ReactNode {
  if (value === undefined || value === null) return null;
  const isPositive = value > 0;
  const Icon = isPositive ? TrendingUp : TrendingDown;
  const color = isPositive ? 'text-green-600' : 'text-red-600';
  return (
    <span className={`flex items-center gap-1 text-xs ${color}`}>
      <Icon className="h-3 w-3" />
      {isPositive ? '+' : ''}{value.toFixed(1)}{suffix}
    </span>
  );
}

export function ObservabilityPage() {
  const [timeRange, setTimeRange] = useState<TimeRange>('24h');
  const [sortBy, setSortBy] = useState<'executions' | 'failures'>('executions');
  const queryClient = useQueryClient();

  const { data: overview, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['observability-overview', timeRange],
    queryFn: () => apiClient.getObservabilityOverview(timeRange),
  });

  const handleRefresh = () => {
    refetch();
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <AlertCircle className="h-12 w-12 text-red-500" />
        <p className="text-muted-foreground">Failed to load observability data</p>
        <Button onClick={handleRefresh}>Retry</Button>
      </div>
    );
  }

  const kpi = overview?.data.kpiMetrics;
  const workflows = overview?.data.workflowPerformance || [];
  const envHealth = overview?.data.environmentHealth || [];
  const syncStats = overview?.data.promotionSyncStats;

  // Sort workflows based on sortBy
  const sortedWorkflows = [...workflows].sort((a, b) => {
    if (sortBy === 'failures') {
      return b.failureCount - a.failureCount;
    }
    return b.executionCount - a.executionCount;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Observability</h1>
          <p className="text-muted-foreground">
            Monitor workflow performance and environment health
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Select value={timeRange} onValueChange={(value) => setTimeRange(value as TimeRange)}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Select time range" />
            </SelectTrigger>
            <SelectContent>
              {TIME_RANGE_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={handleRefresh} disabled={isFetching}>
            <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Executions</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{kpi?.totalExecutions.toLocaleString() || 0}</div>
            {formatDelta(kpi?.deltaExecutions)}
            <p className="text-xs text-muted-foreground mt-1">vs previous period</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(kpi?.successRate || 0).toFixed(1)}%</div>
            {formatDelta(kpi?.deltaSuccessRate, '%')}
            <p className="text-xs text-muted-foreground mt-1">vs previous period</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Duration</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatDuration(kpi?.avgDurationMs || 0)}</div>
            {kpi?.p95DurationMs && (
              <p className="text-xs text-muted-foreground mt-1">
                p95: {formatDuration(kpi.p95DurationMs)}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed Executions</CardTitle>
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {kpi?.failureCount.toLocaleString() || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {((kpi?.failureCount || 0) / Math.max(kpi?.totalExecutions || 1, 1) * 100).toFixed(1)}% of total
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Workflow Performance */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Workflow Performance</CardTitle>
                <CardDescription>Execution metrics by workflow</CardDescription>
              </div>
              <Select value={sortBy} onValueChange={(value) => setSortBy(value as 'executions' | 'failures')}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="executions">By Executions</SelectItem>
                  <SelectItem value="failures">By Failures</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardHeader>
          <CardContent>
            {sortedWorkflows.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No workflow data for this time period
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Workflow</TableHead>
                    <TableHead className="text-right">Runs</TableHead>
                    <TableHead className="text-right">Success</TableHead>
                    <TableHead className="text-right">Failed</TableHead>
                    <TableHead className="text-right">Error %</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sortedWorkflows.slice(0, 10).map((wf) => (
                    <TableRow key={wf.workflowId} className="cursor-pointer hover:bg-muted/50">
                      <TableCell className="font-medium truncate max-w-[200px]">
                        {wf.workflowName}
                      </TableCell>
                      <TableCell className="text-right">{wf.executionCount}</TableCell>
                      <TableCell className="text-right text-green-600">{wf.successCount}</TableCell>
                      <TableCell className="text-right text-red-600">{wf.failureCount}</TableCell>
                      <TableCell className="text-right">
                        <Badge variant={wf.errorRate < 5 ? 'success' : wf.errorRate < 20 ? 'warning' : 'destructive'}>
                          {wf.errorRate.toFixed(1)}%
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Environment Health */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5" />
              Environment Health
            </CardTitle>
            <CardDescription>N8N instance status and metrics</CardDescription>
          </CardHeader>
          <CardContent>
            {envHealth.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No environments configured
              </div>
            ) : (
              <div className="space-y-4">
                {envHealth.map((health) => (
                  <div key={health.environmentId} className="p-4 border rounded-lg space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(health.status)}
                        <span className="font-medium">{health.environmentName}</span>
                        {health.environmentType && (
                          <Badge variant="outline" className="text-xs">
                            {health.environmentType}
                          </Badge>
                        )}
                      </div>
                      <Badge variant={getStatusBadgeVariant(health.status)}>
                        {health.status}
                      </Badge>
                    </div>

                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Latency:</span>
                        <span className="ml-2 font-medium">
                          {health.latencyMs ? `${health.latencyMs}ms` : '—'}
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Uptime:</span>
                        <span className="ml-2 font-medium">{health.uptimePercent.toFixed(1)}%</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Workflows:</span>
                        <span className="ml-2 font-medium">
                          {health.activeWorkflows}/{health.totalWorkflows}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      {health.lastDeploymentAt && (
                        <div className="flex items-center gap-1">
                          <Rocket className="h-3 w-3" />
                          Last deploy: {new Date(health.lastDeploymentAt).toLocaleDateString()}
                        </div>
                      )}
                      {health.lastSnapshotAt && (
                        <div className="flex items-center gap-1">
                          <Camera className="h-3 w-3" />
                          Last snapshot: {new Date(health.lastSnapshotAt).toLocaleDateString()}
                        </div>
                      )}
                      <Badge variant={getDriftBadgeVariant(health.driftState)} className="text-xs">
                        <GitCompare className="h-3 w-3 mr-1" />
                        {health.driftState.replace('_', ' ')}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Promotion & Sync Stats */}
      {syncStats && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Rocket className="h-5 w-5" />
              Promotion & Sync (Last 7 Days)
            </CardTitle>
            <CardDescription>Deployment activity and drift summary</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-6 md:grid-cols-2">
              {/* Stats */}
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 border rounded-lg">
                    <div className="text-2xl font-bold">{syncStats.promotionsTotal}</div>
                    <div className="text-sm text-muted-foreground">Total Promotions</div>
                  </div>
                  <div className="p-4 border rounded-lg">
                    <div className="text-2xl font-bold text-green-600">{syncStats.promotionsSuccess}</div>
                    <div className="text-sm text-muted-foreground">Successful</div>
                  </div>
                  <div className="p-4 border rounded-lg">
                    <div className="text-2xl font-bold text-red-600">{syncStats.promotionsFailed}</div>
                    <div className="text-sm text-muted-foreground">Failed</div>
                  </div>
                  <div className="p-4 border rounded-lg">
                    <div className="text-2xl font-bold">{syncStats.snapshotsCreated}</div>
                    <div className="text-sm text-muted-foreground">Snapshots Created</div>
                  </div>
                </div>
                {syncStats.driftCount > 0 && (
                  <div className="p-4 border border-yellow-200 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="h-5 w-5 text-yellow-600" />
                      <span className="font-medium text-yellow-800 dark:text-yellow-200">
                        {syncStats.driftCount} workflow(s) with drift detected
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Recent Deployments */}
              <div>
                <h4 className="font-medium mb-3">Recent Deployments</h4>
                {syncStats.recentDeployments.length === 0 ? (
                  <div className="text-sm text-muted-foreground">No recent deployments</div>
                ) : (
                  <div className="space-y-2">
                    {syncStats.recentDeployments.map((d) => (
                      <div key={d.id} className="flex items-center justify-between p-2 border rounded text-sm">
                        <div className="flex items-center gap-2">
                          <span className="truncate max-w-[100px]">{d.sourceEnvironmentName}</span>
                          <ArrowRight className="h-3 w-3" />
                          <span className="truncate max-w-[100px]">{d.targetEnvironmentName}</span>
                        </div>
                        <Badge
                          variant={
                            d.status === 'success'
                              ? 'success'
                              : d.status === 'failed'
                              ? 'destructive'
                              : 'outline'
                          }
                        >
                          {d.status}
                        </Badge>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
