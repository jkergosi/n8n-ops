// @ts-nocheck
// TODO: Fix TypeScript errors in this file
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2, ArrowLeft } from 'lucide-react';
import { UsageLimitsSummaryCard } from '@/components/billing/UsageLimitsSummaryCard';

export function AdminUsagePage() {
  useEffect(() => {
    document.title = 'Usage & Limits - WorkflowOps';
    return () => {
      document.title = 'WorkflowOps';
    };
  }, []);

  const navigate = useNavigate();

  const { data: overview, isLoading, isError, refetch } = useQuery({
    queryKey: ['billing-overview'],
    queryFn: () => api.getBillingOverview(),
    retry: 1,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (isError || !overview?.data) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Usage & Limits</h1>
            <p className="text-muted-foreground">View your organization usage and limits</p>
          </div>
          <Button variant="outline" onClick={() => navigate('/admin')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
        </div>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div className="text-sm text-muted-foreground">Failed to load usage.</div>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              Retry
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  const data = overview.data;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Usage & Limits</h1>
          <p className="text-muted-foreground">View your organization usage and limits</p>
        </div>
        <Button variant="outline" onClick={() => navigate('/admin')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
      </div>

      <UsageLimitsSummaryCard
        usage={data.usage}
        entitlements={data.entitlements}
        usageLimitsUrl={data.links.usage_limits_url}
        onViewFullUsage={() => {}}
      />
    </div>
  );
}


