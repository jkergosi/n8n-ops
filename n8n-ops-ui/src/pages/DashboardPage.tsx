import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { mockApi } from '@/lib/mock-api';
import { Activity, Workflow, Database, Server } from 'lucide-react';

export function DashboardPage() {
  const { data: tenant } = useQuery({
    queryKey: ['tenant'],
    queryFn: () => mockApi.getTenant(),
  });

  const { data: environments } = useQuery({
    queryKey: ['environments'],
    queryFn: () => mockApi.getEnvironments(),
  });

  const { data: metrics } = useQuery({
    queryKey: ['metrics'],
    queryFn: () => mockApi.getWorkflowMetrics(),
  });

  const stats = [
    {
      title: 'Active Workflows',
      value: metrics?.data?.reduce((sum, m) => sum + (m.totalExecutions > 0 ? 1 : 0), 0) || 0,
      icon: Workflow,
      description: 'Across all environments',
    },
    {
      title: 'Total Executions',
      value: metrics?.data?.reduce((sum, m) => sum + m.totalExecutions, 0) || 0,
      icon: Activity,
      description: 'Last 30 days',
    },
    {
      title: 'Environments',
      value: environments?.data?.filter((e) => e.isActive).length || 0,
      icon: Server,
      description: 'Connected and active',
    },
    {
      title: 'Success Rate',
      value: metrics?.data
        ? `${(
            (metrics.data.reduce((sum, m) => sum + m.successfulExecutions, 0) /
              metrics.data.reduce((sum, m) => sum + m.totalExecutions, 0)) *
            100
          ).toFixed(1)}%`
        : '0%',
      icon: Database,
      description: 'Overall performance',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome back, {tenant?.data?.name || 'User'}
        </p>
      </div>

      <div className="flex items-center gap-2">
        <Badge variant="outline">Subscription: {tenant?.data?.subscriptionTier}</Badge>
        <Badge variant={tenant?.data?.subscriptionTier === 'free' ? 'warning' : 'success'}>
          {tenant?.data?.subscriptionTier === 'free' ? 'Upgrade Available' : 'Active'}
        </Badge>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.title}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
                <Icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value}</div>
                <p className="text-xs text-muted-foreground">{stat.description}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>Latest workflow executions</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {metrics?.data?.slice(0, 5).map((metric) => (
                <div
                  key={metric.workflowId}
                  className="flex items-center justify-between p-2 rounded-md border"
                >
                  <div>
                    <p className="font-medium">{metric.workflowName}</p>
                    <p className="text-sm text-muted-foreground">
                      {metric.totalExecutions} executions
                    </p>
                  </div>
                  <Badge variant={metric.errorRate < 5 ? 'success' : 'destructive'}>
                    {metric.errorRate.toFixed(1)}% errors
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Environment Status</CardTitle>
            <CardDescription>Connected n8n instances</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {environments?.data?.map((env) => (
                <div
                  key={env.id}
                  className="flex items-center justify-between p-2 rounded-md border"
                >
                  <div>
                    <p className="font-medium">{env.name}</p>
                    <p className="text-sm text-muted-foreground">{env.type}</p>
                  </div>
                  <Badge variant={env.isActive ? 'success' : 'outline'}>
                    {env.isActive ? 'Active' : 'Inactive'}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
