import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { mockApi } from '@/lib/mock-api';
import { Rocket, ArrowRight } from 'lucide-react';

export function DeploymentsPage() {
  const { data: deployments, isLoading } = useQuery({
    queryKey: ['deployments'],
    queryFn: () => mockApi.getDeployments(),
  });

  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'success':
        return 'success';
      case 'failed':
        return 'destructive';
      case 'running':
        return 'default';
      default:
        return 'outline';
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Deployments</h1>
        <p className="text-muted-foreground">
          Track workflow deployments across environments
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Rocket className="h-5 w-5" />
            Deployment History
          </CardTitle>
          <CardDescription>Recent workflow deployments and promotions</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8">Loading deployments...</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Workflow</TableHead>
                  <TableHead>Environments</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Triggered By</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Duration</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {deployments?.data?.map((deployment) => (
                  <TableRow key={deployment.id}>
                    <TableCell className="font-medium">{deployment.workflowName}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">{deployment.sourceEnvironment}</Badge>
                        <ArrowRight className="h-3 w-3" />
                        <Badge variant="outline">{deployment.targetEnvironment}</Badge>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={getStatusVariant(deployment.status)}>
                        {deployment.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {deployment.triggeredBy}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {new Date(deployment.startedAt).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {deployment.completedAt
                        ? `${Math.round(
                            (new Date(deployment.completedAt).getTime() -
                              new Date(deployment.startedAt).getTime()) /
                              1000
                          )}s`
                        : '-'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
