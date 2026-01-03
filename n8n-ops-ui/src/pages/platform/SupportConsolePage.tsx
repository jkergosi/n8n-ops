// @ts-nocheck
// TODO: Fix TypeScript errors in this file
import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { apiClient } from '@/lib/api-client';
import { useAuth } from '@/lib/auth';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  UserCog,
  ExternalLink,
  Save,
  TestTube,
  CheckCircle,
  XCircle,
  Webhook,
  Settings2,
  FileText,
  HelpCircle,
  Search,
} from 'lucide-react';
import { toast } from 'sonner';

// Support Config form data interface
interface SupportConfigFormData {
  n8n_webhook_url: string;
  n8n_api_key: string;
  jsm_portal_url: string;
  jsm_cloud_instance: string;
  jsm_api_token: string;
  jsm_project_key: string;
  jsm_bug_request_type_id: string;
  jsm_feature_request_type_id: string;
  jsm_help_request_type_id: string;
  jsm_widget_embed_code: string;
  storage_bucket: string;
  storage_prefix: string;
}

// Impersonation Tab Component
function ImpersonationTab() {
  const { startImpersonation } = useAuth();

  // Tenant search state
  const [tenantName, setTenantName] = useState('');
  const [tenantSlug, setTenantSlug] = useState('');
  const [tenantId, setTenantId] = useState('');
  const [tenantSearchTrigger, setTenantSearchTrigger] = useState(0);
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(null);

  // User search state
  const [userEmail, setUserEmail] = useState('');
  const [userName, setUserName] = useState('');
  const [userId, setUserId] = useState('');
  const [userSearchTrigger, setUserSearchTrigger] = useState(0);
  const [userTenantFilter, setUserTenantFilter] = useState<string | null>(null);

  // Tenant search query - similar pattern to TenantsPage
  const { data: tenantsData, isLoading: tenantsLoading } = useQuery({
    queryKey: ['console-tenants', tenantSearchTrigger, tenantName, tenantSlug, tenantId],
    queryFn: () => apiClient.consoleSearchTenants({
      name: tenantName.trim() || undefined,
      slug: tenantSlug.trim() || undefined,
      tenant_id: tenantId.trim() || undefined,
      limit: 25,
    }),
    enabled: tenantSearchTrigger > 0,
  });

  // User search query - similar pattern to TenantsPage
  const { data: usersData, isLoading: usersLoading } = useQuery({
    queryKey: ['console-users', userSearchTrigger, userEmail, userName, userId, userTenantFilter],
    queryFn: () => apiClient.consoleSearchUsers({
      email: userEmail.trim() || undefined,
      name: userName.trim() || undefined,
      user_id: userId.trim() || undefined,
      tenant_id: userTenantFilter || undefined,
      limit: 50,
    }),
    enabled: userSearchTrigger > 0,
  });

  // Extract data same way as TenantsPage
  const tenantsArray = tenantsData?.data && "tenants" in tenantsData.data ? tenantsData.data.tenants : [];
  const tenants: any[] = Array.isArray(tenantsArray) ? tenantsArray : [];

  const usersArray = usersData?.data && "users" in usersData.data ? usersData.data.users : [];
  const users: any[] = Array.isArray(usersArray) ? usersArray : [];

  const onSearchTenants = () => {
    setSelectedTenantId(null);
    setTenantSearchTrigger(prev => prev + 1);
  };

  const onSearchUsers = () => {
    setUserTenantFilter(selectedTenantId);
    setUserSearchTrigger(prev => prev + 1);
  };

  const onListUsersForTenant = (tid: string) => {
    setSelectedTenantId(tid);
    setUserTenantFilter(tid);
    setUserSearchTrigger(prev => prev + 1);
  };

  const onImpersonate = async (targetUserId: string, isPlatformAdmin: boolean) => {
    if (isPlatformAdmin) {
      toast.error('Cannot impersonate another Platform Admin');
      return;
    }
    try {
      await startImpersonation(targetUserId);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || e?.message || 'Failed to start impersonation');
    }
  };

  return (
    <div className="space-y-6">
      <Alert>
        <AlertDescription>
          Impersonation is platform-only and should be used for support. You cannot impersonate another Platform Admin.
        </AlertDescription>
      </Alert>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Tenant Search</CardTitle>
            <CardDescription>Search by name, slug, or tenant ID</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <Label>Tenant name</Label>
                <Input value={tenantName} onChange={(e) => setTenantName(e.target.value)} placeholder="Acme" />
              </div>
              <div className="space-y-2">
                <Label>Tenant slug</Label>
                <Input value={tenantSlug} onChange={(e) => setTenantSlug(e.target.value)} placeholder="acme" />
              </div>
              <div className="space-y-2">
                <Label>Tenant ID</Label>
                <Input value={tenantId} onChange={(e) => setTenantId(e.target.value)} placeholder="UUID" />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button onClick={onSearchTenants} disabled={tenantsLoading}>
                {tenantsLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                Search Tenants
              </Button>
              {selectedTenantId && (
                <Button variant="outline" onClick={() => setSelectedTenantId(null)}>
                  Clear Tenant Filter
                </Button>
              )}
            </div>

            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tenant Name</TableHead>
                  <TableHead>Tenant ID</TableHead>
                  <TableHead>Plan</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tenants.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-muted-foreground">
                      No tenant results.
                    </TableCell>
                  </TableRow>
                ) : (
                  tenants.map((t: any) => (
                    <TableRow key={t.id}>
                      <TableCell>{t.name || '—'}</TableCell>
                      <TableCell className="font-mono text-sm">{t.id}</TableCell>
                      <TableCell>{t.subscription_tier || 'free'}</TableCell>
                      <TableCell className="text-right">
                        <Button size="sm" variant="outline" onClick={() => onListUsersForTenant(t.id)}>
                          List Users
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>User Search</CardTitle>
            <CardDescription>Search by email, name, or user ID{selectedTenantId ? ' (filtered by tenant)' : ''}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <Label>Email</Label>
                <Input value={userEmail} onChange={(e) => setUserEmail(e.target.value)} placeholder="jane@customer.com" />
              </div>
              <div className="space-y-2">
                <Label>Name</Label>
                <Input value={userName} onChange={(e) => setUserName(e.target.value)} placeholder="Jane Doe" />
              </div>
              <div className="space-y-2">
                <Label>User ID</Label>
                <Input value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="UUID" />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button onClick={onSearchUsers} disabled={usersLoading}>
                {usersLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                Search Users
              </Button>
              {selectedTenantId && (
                <div className="text-xs text-muted-foreground">
                  Tenant filter: <span className="font-mono">{selectedTenantId}</span>
                </div>
              )}
            </div>

            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Tenant</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-muted-foreground">
                      No user results.
                    </TableCell>
                  </TableRow>
                ) : (
                  users.map((u: any) => (
                    <TableRow key={u.id}>
                      <TableCell>{u.name || '—'}</TableCell>
                      <TableCell className="font-mono text-sm">{u.email}</TableCell>
                      <TableCell>{u.tenant?.name || u.tenant?.slug || u.tenant?.id || '—'}</TableCell>
                      <TableCell>{u.is_platform_admin ? 'platform_admin' : (u.role || 'viewer')}</TableCell>
                      <TableCell className="text-right">
                        <Button
                          size="sm"
                          onClick={() => onImpersonate(u.id, !!u.is_platform_admin)}
                          disabled={!!u.is_platform_admin}
                        >
                          <UserCog className="h-4 w-4 mr-2" />
                          Impersonate
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// Support Requests Tab Component
function RequestsTab() {
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
      <div className="text-center py-8">
        <p className="text-muted-foreground">Failed to load support requests.</p>
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Support Requests</CardTitle>
        <CardDescription>{requests.length} requests submitted from the app</CardDescription>
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
  );
}

// Support Config Tab Component
function ConfigTab() {
  const queryClient = useQueryClient();

  const [formData, setFormData] = useState<SupportConfigFormData>({
    n8n_webhook_url: '',
    n8n_api_key: '',
    jsm_portal_url: '',
    jsm_cloud_instance: '',
    jsm_api_token: '',
    jsm_project_key: '',
    jsm_bug_request_type_id: '',
    jsm_feature_request_type_id: '',
    jsm_help_request_type_id: '',
    jsm_widget_embed_code: '',
    storage_bucket: '',
    storage_prefix: '',
  });

  const [configTab, setConfigTab] = useState('n8n');
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  const { data: configData, isLoading } = useQuery({
    queryKey: ['support-config'],
    queryFn: () => apiClient.getSupportConfig(),
  });

  useEffect(() => {
    if (configData?.data) {
      setFormData({
        n8n_webhook_url: configData.data.n8n_webhook_url || '',
        n8n_api_key: configData.data.n8n_api_key || '',
        jsm_portal_url: configData.data.jsm_portal_url || '',
        jsm_cloud_instance: configData.data.jsm_cloud_instance || '',
        jsm_api_token: configData.data.jsm_api_token || '',
        jsm_project_key: configData.data.jsm_project_key || '',
        jsm_bug_request_type_id: configData.data.jsm_bug_request_type_id || '',
        jsm_feature_request_type_id: configData.data.jsm_feature_request_type_id || '',
        jsm_help_request_type_id: configData.data.jsm_help_request_type_id || '',
        jsm_widget_embed_code: configData.data.jsm_widget_embed_code || '',
        storage_bucket: configData.data.storage_bucket || '',
        storage_prefix: configData.data.storage_prefix || '',
      });
    }
  }, [configData]);

  const updateMutation = useMutation({
    mutationFn: (data: Partial<SupportConfigFormData>) => apiClient.updateSupportConfig(data),
    onSuccess: () => {
      toast.success('Configuration saved successfully');
      queryClient.invalidateQueries({ queryKey: ['support-config'] });
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to save configuration';
      toast.error(message);
    },
  });

  const testMutation = useMutation({
    mutationFn: () => apiClient.testN8nConnection(),
    onSuccess: (response) => {
      setTestResult(response.data);
      if (response.data.success) {
        toast.success('Connection successful');
      } else {
        toast.error(response.data.message);
      }
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Connection test failed';
      setTestResult({ success: false, message });
      toast.error(message);
    },
  });

  const handleSave = () => {
    const dataToSave: Partial<SupportConfigFormData> = {};
    Object.entries(formData).forEach(([key, value]) => {
      if (value) {
        dataToSave[key as keyof SupportConfigFormData] = value;
      }
    });
    updateMutation.mutate(dataToSave);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <Tabs value={configTab} onValueChange={setConfigTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="n8n" className="gap-2">
            <Webhook className="h-4 w-4" />
            n8n Integration
          </TabsTrigger>
          <TabsTrigger value="jsm" className="gap-2">
            <Settings2 className="h-4 w-4" />
            JSM Settings
          </TabsTrigger>
          <TabsTrigger value="request-types" className="gap-2">
            <FileText className="h-4 w-4" />
            Request Types
          </TabsTrigger>
          <TabsTrigger value="storage" className="gap-2">
            <Save className="h-4 w-4" />
            Storage
          </TabsTrigger>
        </TabsList>

        <TabsContent value="n8n" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>n8n Webhook Configuration</CardTitle>
              <CardDescription>
                Configure the n8n webhook endpoint that receives support requests
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="n8n_webhook_url">Webhook URL</Label>
                <Input
                  id="n8n_webhook_url"
                  type="url"
                  placeholder="https://your-n8n.com/webhook/support"
                  value={formData.n8n_webhook_url}
                  onChange={(e) => setFormData({ ...formData, n8n_webhook_url: e.target.value })}
                />
                <p className="text-sm text-muted-foreground">
                  The n8n webhook URL that will receive support request payloads
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="n8n_api_key">API Key (optional)</Label>
                <Input
                  id="n8n_api_key"
                  type="password"
                  placeholder="Enter API key for authentication"
                  value={formData.n8n_api_key}
                  onChange={(e) => setFormData({ ...formData, n8n_api_key: e.target.value })}
                />
                <p className="text-sm text-muted-foreground">
                  Optional API key for authenticating with the n8n webhook
                </p>
              </div>

              <div className="flex items-center gap-4 pt-4">
                <Button
                  variant="outline"
                  onClick={() => testMutation.mutate()}
                  disabled={!formData.n8n_webhook_url || testMutation.isPending}
                >
                  {testMutation.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <TestTube className="mr-2 h-4 w-4" />
                  )}
                  Test Connection
                </Button>
                {testResult && (
                  <Badge variant={testResult.success ? 'default' : 'destructive'} className="gap-1">
                    {testResult.success ? (
                      <CheckCircle className="h-3 w-3" />
                    ) : (
                      <XCircle className="h-3 w-3" />
                    )}
                    {testResult.message}
                  </Badge>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="jsm" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Jira Service Management Settings</CardTitle>
              <CardDescription>
                Configure your JSM portal and API connection
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="jsm_cloud_instance">Cloud Instance URL</Label>
                  <Input
                    id="jsm_cloud_instance"
                    type="url"
                    placeholder="https://yourcompany.atlassian.net"
                    value={formData.jsm_cloud_instance}
                    onChange={(e) => setFormData({ ...formData, jsm_cloud_instance: e.target.value })}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="jsm_project_key">Project Key</Label>
                  <Input
                    id="jsm_project_key"
                    placeholder="SUP"
                    value={formData.jsm_project_key}
                    onChange={(e) => setFormData({ ...formData, jsm_project_key: e.target.value })}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="jsm_portal_url">Customer Portal URL</Label>
                <Input
                  id="jsm_portal_url"
                  type="url"
                  placeholder="https://yourcompany.atlassian.net/servicedesk/customer/portal/1"
                  value={formData.jsm_portal_url}
                  onChange={(e) => setFormData({ ...formData, jsm_portal_url: e.target.value })}
                />
                <p className="text-sm text-muted-foreground">
                  Used for "View in portal" links shown to users after submitting requests
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="jsm_api_token">API Token (optional)</Label>
                <Input
                  id="jsm_api_token"
                  type="password"
                  placeholder="Enter Atlassian API token"
                  value={formData.jsm_api_token}
                  onChange={(e) => setFormData({ ...formData, jsm_api_token: e.target.value })}
                />
                <p className="text-sm text-muted-foreground">
                  Optional token for fetching live request status from JSM
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="jsm_widget_embed_code">Widget Embed Code (optional)</Label>
                <Textarea
                  id="jsm_widget_embed_code"
                  placeholder="<script>...</script>"
                  value={formData.jsm_widget_embed_code}
                  onChange={(e) => setFormData({ ...formData, jsm_widget_embed_code: e.target.value })}
                  rows={4}
                />
                <p className="text-sm text-muted-foreground">
                  JavaScript embed code for the JSM help widget
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="request-types" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>JSM Request Type Mapping</CardTitle>
              <CardDescription>
                Map support request types to their corresponding JSM request type IDs
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="jsm_bug_request_type_id">Bug Report Request Type ID</Label>
                <Input
                  id="jsm_bug_request_type_id"
                  placeholder="e.g., 10001"
                  value={formData.jsm_bug_request_type_id}
                  onChange={(e) => setFormData({ ...formData, jsm_bug_request_type_id: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="jsm_feature_request_type_id">Feature Request Type ID</Label>
                <Input
                  id="jsm_feature_request_type_id"
                  placeholder="e.g., 10002"
                  value={formData.jsm_feature_request_type_id}
                  onChange={(e) => setFormData({ ...formData, jsm_feature_request_type_id: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="jsm_help_request_type_id">Help / Question Request Type ID</Label>
                <Input
                  id="jsm_help_request_type_id"
                  placeholder="e.g., 10003"
                  value={formData.jsm_help_request_type_id}
                  onChange={(e) => setFormData({ ...formData, jsm_help_request_type_id: e.target.value })}
                />
              </div>

              <p className="text-sm text-muted-foreground pt-2">
                You can find request type IDs in your JSM project settings under Request Types.
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="storage" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Supabase Storage (Private)</CardTitle>
              <CardDescription>
                Configure where support attachments are stored. Bucket should be private.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="storage_bucket">Bucket</Label>
                <Input
                  id="storage_bucket"
                  placeholder="support-attachments"
                  value={formData.storage_bucket}
                  onChange={(e) => setFormData({ ...formData, storage_bucket: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="storage_prefix">Prefix</Label>
                <Input
                  id="storage_prefix"
                  placeholder="support"
                  value={formData.storage_prefix}
                  onChange={(e) => setFormData({ ...formData, storage_prefix: e.target.value })}
                />
                <p className="text-sm text-muted-foreground">
                  Objects are stored under: <code className="bg-muted px-1 rounded">{'{prefix}/{tenant_id}/{attachment_id}/{filename}'}</code>
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={updateMutation.isPending}>
          {updateMutation.isPending ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Save className="mr-2 h-4 w-4" />
          )}
          Save Configuration
        </Button>
      </div>
    </div>
  );
}

export function SupportConsolePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get('tab') || 'impersonation';

  useEffect(() => {
    document.title = 'Support - WorkflowOps';
    return () => {
      document.title = 'WorkflowOps';
    };
  }, []);

  const handleTabChange = (value: string) => {
    setSearchParams({ tab: value });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Support</h1>
        <p className="text-muted-foreground">
          Search tenants and users, view support requests, and configure support settings.
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={handleTabChange} className="space-y-4">
        <TabsList>
          <TabsTrigger value="impersonation" className="gap-2">
            <Search className="h-4 w-4" />
            Impersonation
          </TabsTrigger>
          <TabsTrigger value="requests" className="gap-2">
            <HelpCircle className="h-4 w-4" />
            Requests
          </TabsTrigger>
          <TabsTrigger value="config" className="gap-2">
            <Settings2 className="h-4 w-4" />
            Config
          </TabsTrigger>
        </TabsList>

        <TabsContent value="impersonation">
          <ImpersonationTab />
        </TabsContent>

        <TabsContent value="requests">
          <RequestsTab />
        </TabsContent>

        <TabsContent value="config">
          <ConfigTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
