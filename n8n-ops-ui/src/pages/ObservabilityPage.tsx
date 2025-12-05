import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { mockApi } from '@/lib/mock-api';
import { Activity, TrendingUp, AlertCircle, Clock } from 'lucide-react';

export function ObservabilityPage() {
  const { data: metrics } = useQuery({
    queryKey: ['metrics'],
    queryFn: () => mockApi.getWorkflowMetrics(),
  });

  const { data: envHealth } = useQuery({
    queryKey: ['env-health'],
    queryFn: () => mockApi.getEnvironmentHealth(),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Observability</h1>
        <p className="text-muted-foreground">
          Monitor workflow performance and environment health
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Executions</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {metrics?.data?.reduce((sum, m) => sum + m.totalExecutions, 0) || 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {metrics?.data
                ? (
                    (metrics.data.reduce((sum, m) => sum + m.successfulExecutions, 0) /
                      metrics.data.reduce((sum, m) => sum + m.totalExecutions, 0)) *
                    100
                  ).toFixed(1)
                : 0}
              %
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Duration</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {metrics?.data
                ? Math.round(
                    metrics.data.reduce((sum, m) => sum + m.averageDuration, 0) /
                      metrics.data.length
                  )
                : 0}
              ms
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed Executions</CardTitle>
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {metrics?.data?.reduce((sum, m) => sum + m.failedExecutions, 0) || 0}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Workflow Performance</CardTitle>
            <CardDescription>Execution metrics by workflow</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {metrics?.data?.map((metric) => (
                <div key={metric.workflowId} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{metric.workflowName}</span>
                    <Badge variant={metric.errorRate < 5 ? 'success' : 'destructive'}>
                      {metric.errorRate.toFixed(1)}% error
                    </Badge>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-sm text-muted-foreground">
                    <div>Executions: {metric.totalExecutions}</div>
                    <div>Success: {metric.successfulExecutions}</div>
                    <div>Failed: {metric.failedExecutions}</div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Environment Health</CardTitle>
            <CardDescription>n8n instance status and metrics</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {envHealth?.data?.map((health) => (
                <div key={health.environment} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-medium capitalize">{health.environment}</span>
                    <Badge
                      variant={
                        health.status === 'healthy'
                          ? 'success'
                          : health.status === 'degraded'
                            ? 'warning'
                            : 'destructive'
                      }
                    >
                      {health.status}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-sm text-muted-foreground">
                    <div>Latency: {health.latency}ms</div>
                    <div>Uptime: {health.uptime}%</div>
                    <div>
                      Active: {health.workflowsActive}/{health.workflowsTotal}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
