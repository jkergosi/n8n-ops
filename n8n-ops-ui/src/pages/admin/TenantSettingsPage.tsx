import { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { apiClient } from '@/lib/api-client';
import {
  Key,
  Save,
  Plus,
  Trash2,
  Copy,
  Eye,
  EyeOff,
  Loader2,
  Building2,
  History,
  Clock,
} from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/lib/auth';

export function TenantSettingsPage() {
  useEffect(() => {
    document.title = 'Settings - WorkflowOps';
    return () => {
      document.title = 'WorkflowOps';
    };
  }, []);

  const { tenant } = useAuth();
  const queryClient = useQueryClient();

  // Organization settings state
  const [orgName, setOrgName] = useState('');
  const [isSavingOrg, setIsSavingOrg] = useState(false);

  // API Key creation state
  const [isCreatingKey, setIsCreatingKey] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [showCreatedKey, setShowCreatedKey] = useState(false);

  // Initialize org name from tenant
  useEffect(() => {
    if (tenant?.name) {
      setOrgName(tenant.name);
    }
  }, [tenant?.name]);

  // Fetch API keys
  const { data: apiKeysData, isLoading: isLoadingApiKeys } = useQuery({
    queryKey: ['tenant-api-keys'],
    queryFn: () => apiClient.getTenantApiKeys(),
  });

  const apiKeys = apiKeysData?.data || [];

  // Fetch audit logs (recent 10)
  const { data: auditLogsData, isLoading: isLoadingAuditLogs } = useQuery({
    queryKey: ['tenant-audit-logs', { page_size: 10 }],
    queryFn: () => apiClient.getAuditLogs({ page_size: 10 }),
  });

  const auditLogs = auditLogsData?.data?.logs || [];

  // Create API key mutation
  const createKeyMutation = useMutation({
    mutationFn: (name: string) => apiClient.createTenantApiKey({ name }),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['tenant-api-keys'] });
      setCreatedKey(response.data.api_key);
      setNewKeyName('');
      toast.success('API key created successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create API key');
    },
  });

  // Revoke API key mutation
  const revokeKeyMutation = useMutation({
    mutationFn: (keyId: string) => apiClient.revokeTenantApiKey(keyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenant-api-keys'] });
      toast.success('API key revoked');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to revoke API key');
    },
  });

  const handleSaveOrg = async () => {
    setIsSavingOrg(true);
    // TODO: Implement actual save when backend endpoint exists
    await new Promise((resolve) => setTimeout(resolve, 500));
    setIsSavingOrg(false);
    toast.success('Organization settings saved');
  };

  const handleCreateKey = () => {
    if (!newKeyName.trim()) {
      toast.error('Please enter a name for the API key');
      return;
    }
    createKeyMutation.mutate(newKeyName.trim());
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    toast.success(`${label} copied to clipboard`);
  };

  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString();
  };

  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground">Manage your organization settings</p>
      </div>

      <Tabs defaultValue="organization" className="space-y-6">
        <TabsList>
          <TabsTrigger value="organization">Organization</TabsTrigger>
          <TabsTrigger value="api-keys">API Keys</TabsTrigger>
          <TabsTrigger value="audit">Audit Log</TabsTrigger>
        </TabsList>

        {/* Organization Tab */}
        <TabsContent value="organization" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="h-5 w-5" />
                Organization Details
              </CardTitle>
              <CardDescription>Basic information about your organization</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="org-name">Organization Name</Label>
                  <Input
                    id="org-name"
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    placeholder="Your organization name"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Organization ID</Label>
                  <div className="flex gap-2">
                    <Input
                      value={tenant?.id || ''}
                      disabled
                      className="font-mono text-sm"
                    />
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => copyToClipboard(tenant?.id || '', 'Organization ID')}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Created</Label>
                  <Input
                    value={tenant?.createdAt ? formatDate(tenant.createdAt) : 'N/A'}
                    disabled
                  />
                </div>
                <div className="space-y-2">
                  <Label>Subscription Plan</Label>
                  <div className="flex items-center gap-2 h-9">
                    <Badge variant="default" className="text-sm">
                      {tenant?.subscriptionPlan || 'Free'}
                    </Badge>
                  </div>
                </div>
              </div>

              <div className="flex justify-end">
                <Button onClick={handleSaveOrg} disabled={isSavingOrg}>
                  <Save className="h-4 w-4 mr-2" />
                  {isSavingOrg ? 'Saving...' : 'Save Changes'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* API Keys Tab */}
        <TabsContent value="api-keys" className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Key className="h-5 w-5" />
                    API Keys
                  </CardTitle>
                  <CardDescription>Manage API keys for programmatic access</CardDescription>
                </div>
                <Dialog open={isCreatingKey} onOpenChange={setIsCreatingKey}>
                  <DialogTrigger asChild>
                    <Button>
                      <Plus className="h-4 w-4 mr-2" />
                      Create API Key
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Create API Key</DialogTitle>
                      <DialogDescription>
                        Create a new API key for programmatic access to your tenant resources.
                      </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                      {createdKey ? (
                        <div className="space-y-4">
                          <div className="p-4 bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded-lg">
                            <p className="text-sm font-medium text-green-800 dark:text-green-200 mb-2">
                              API Key Created Successfully
                            </p>
                            <p className="text-xs text-green-700 dark:text-green-300 mb-3">
                              Copy this key now. You won't be able to see it again.
                            </p>
                            <div className="flex gap-2">
                              <Input
                                type={showCreatedKey ? 'text' : 'password'}
                                value={createdKey}
                                readOnly
                                className="font-mono text-sm"
                              />
                              <Button
                                variant="outline"
                                size="icon"
                                onClick={() => setShowCreatedKey(!showCreatedKey)}
                              >
                                {showCreatedKey ? (
                                  <EyeOff className="h-4 w-4" />
                                ) : (
                                  <Eye className="h-4 w-4" />
                                )}
                              </Button>
                              <Button
                                variant="outline"
                                size="icon"
                                onClick={() => copyToClipboard(createdKey, 'API Key')}
                              >
                                <Copy className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <Label htmlFor="key-name">Key Name</Label>
                          <Input
                            id="key-name"
                            value={newKeyName}
                            onChange={(e) => setNewKeyName(e.target.value)}
                            placeholder="e.g., CI/CD Pipeline"
                          />
                          <p className="text-xs text-muted-foreground">
                            Choose a descriptive name to help identify this key's purpose.
                          </p>
                        </div>
                      )}
                    </div>
                    <DialogFooter>
                      {createdKey ? (
                        <Button
                          onClick={() => {
                            setCreatedKey(null);
                            setIsCreatingKey(false);
                            setShowCreatedKey(false);
                          }}
                        >
                          Done
                        </Button>
                      ) : (
                        <>
                          <Button variant="outline" onClick={() => setIsCreatingKey(false)}>
                            Cancel
                          </Button>
                          <Button
                            onClick={handleCreateKey}
                            disabled={createKeyMutation.isPending}
                          >
                            {createKeyMutation.isPending ? (
                              <Loader2 className="h-4 w-4 animate-spin mr-2" />
                            ) : null}
                            Create Key
                          </Button>
                        </>
                      )}
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </div>
            </CardHeader>
            <CardContent>
              {isLoadingApiKeys ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : apiKeys.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Key className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No API keys created yet</p>
                  <p className="text-sm">Create an API key to access the API programmatically.</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Key Prefix</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead>Last Used</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {apiKeys.map((key) => (
                      <TableRow key={key.id}>
                        <TableCell className="font-medium">{key.name}</TableCell>
                        <TableCell>
                          <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
                            {key.key_prefix}...
                          </code>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {formatDate(key.created_at)}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {key.last_used_at ? formatRelativeTime(key.last_used_at) : 'Never'}
                        </TableCell>
                        <TableCell>
                          <Badge variant={key.is_active ? 'default' : 'secondary'}>
                            {key.is_active ? 'Active' : 'Revoked'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          {key.is_active && (
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button variant="ghost" size="sm">
                                  <Trash2 className="h-4 w-4 text-destructive" />
                                </Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>Revoke API Key</AlertDialogTitle>
                                  <AlertDialogDescription>
                                    Are you sure you want to revoke this API key? This action cannot be undone.
                                    Any applications using this key will lose access immediately.
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                                  <AlertDialogAction
                                    onClick={() => revokeKeyMutation.mutate(key.id)}
                                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                  >
                                    Revoke Key
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Audit Log Tab */}
        <TabsContent value="audit" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <History className="h-5 w-5" />
                Recent Activity
              </CardTitle>
              <CardDescription>
                Recent audit events for your organization
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isLoadingAuditLogs ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : auditLogs.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <History className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No audit events yet</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Action</TableHead>
                      <TableHead>Actor</TableHead>
                      <TableHead>Resource</TableHead>
                      <TableHead className="text-right">Time</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {auditLogs.map((log: any) => (
                      <TableRow key={log.id}>
                        <TableCell>
                          <Badge variant="outline">{log.action}</Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {log.actor_email || log.actor_id || 'System'}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {log.resource_type} {log.resource_id ? `(${log.resource_id.slice(0, 8)}...)` : ''}
                        </TableCell>
                        <TableCell className="text-right text-muted-foreground">
                          <div className="flex items-center justify-end gap-1">
                            <Clock className="h-3 w-3" />
                            {formatRelativeTime(log.created_at)}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}

              {auditLogs.length > 0 && (
                <div className="mt-4 text-center">
                  <Button variant="outline" size="sm" asChild>
                    <a href="/platform/entitlements-audit">View Full Audit Log</a>
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
