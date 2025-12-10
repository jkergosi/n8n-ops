import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { GitCompare } from 'lucide-react';

export function DriftPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Drift</h1>
        <p className="text-muted-foreground">Monitor and manage workflow drift between Git and runtime environments</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GitCompare className="h-5 w-5" />
            Drift Detection
          </CardTitle>
          <CardDescription>
            Track differences between your Git repository and runtime workflow configurations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            This page will display workflow drift analysis and allow you to sync changes between Git and runtime environments.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

