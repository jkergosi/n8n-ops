import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2, ExternalLink } from 'lucide-react';
import { apiClient } from '@/lib/api-client';

export function SupportRequestsPage() {
  useEffect(() => {
    document.title = 'Support Requests - WorkflowOps';
    return () => {
      document.title = 'WorkflowOps';
    };
  }, []);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin-support-requests'],
    queryFn: () => apiClient.getAdminSupportRequests(100),
  });

  const requests = data?.data?.data || [];

  const handleView = async (attachmentId: string) => {
    try {
      const resp = await apiClient.getAdminSupportAttachmentDownloadUrl(attachmentId, 3600);
      window.open(resp.data.url, '_blank', 'noopener,noreferrer');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to get attachment URL');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Support Requests</h1>
          <p className="text-muted-foreground">Failed to load support requests.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Support Requests</h1>
        <p className="text-muted-foreground">Recent support requests submitted from the app.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent</CardTitle>
          <CardDescription>{requests.length} requests</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {requests.length === 0 ? (
            <div className="text-sm text-muted-foreground">No support requests found.</div>
          ) : (
            <div className="space-y-3">
              {requests.map((r: any) => (
                <div key={r.id} className="rounded-lg border p-4 space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="font-medium">
                      {r.intent_kind?.toUpperCase?.() || 'REQUEST'} — {r.jsm_request_key}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {r.created_at ? new Date(r.created_at).toLocaleString() : ''}
                    </div>
                  </div>

                  {r.created_by_email ? (
                    <div className="text-sm text-muted-foreground">Submitted by {r.created_by_email}</div>
                  ) : null}

                  <div className="space-y-1">
                    <div className="text-sm font-medium">Attachments</div>
                    {(r.attachments || []).length === 0 ? (
                      <div className="text-sm text-muted-foreground">None</div>
                    ) : (
                      <div className="space-y-1">
                        {(r.attachments || []).map((a: any) => (
                          <div key={a.id} className="flex items-center justify-between gap-2">
                            <div className="text-sm">
                              {a.filename}{' '}
                              <span className="text-muted-foreground">
                                ({a.content_type || 'unknown'}
                                {a.size_bytes ? `, ${Math.round(a.size_bytes / 1024)} KB` : ''})
                              </span>
                            </div>
                            <Button variant="outline" size="sm" onClick={() => handleView(a.id)} className="gap-2">
                              <ExternalLink className="h-4 w-4" />
                              View
                            </Button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}


