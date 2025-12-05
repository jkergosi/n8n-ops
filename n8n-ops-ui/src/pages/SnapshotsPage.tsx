import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Camera, History } from 'lucide-react';

export function SnapshotsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Snapshots</h1>
          <p className="text-muted-foreground">
            Version control for your workflows
          </p>
        </div>
        <Button>
          <Camera className="h-4 w-4 mr-2" />
          Create Snapshot
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <History className="h-5 w-5" />
            Snapshot History
          </CardTitle>
          <CardDescription>
            View and manage workflow snapshots across environments
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">
            Select a workflow to view its snapshot history
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
