import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { LoadingState, LoadingSpinner } from '@/components/ui/loading-state';
import { SkeletonCard } from '@/components/ui/skeleton';
import { apiClient } from '@/lib/api-client';
import {
  Shield,
  Clock,
  Bell,
  AlertTriangle,
  Save,
  CheckCircle,
  FileText,
  ShieldAlert,
  Ban,
} from 'lucide-react';
import { toast } from 'sonner';
import type { DriftPolicy, DriftPolicyUpdate } from '@/types';

export function DriftPoliciesPage() {
  const queryClient = useQueryClient();
  const [isDirty, setIsDirty] = useState(false);
  const [localPolicy, setLocalPolicy] = useState<DriftPolicyUpdate | null>(null);

  // Fetch current policy
  const { data: policyData, isLoading: policyLoading, error: policyError } = useQuery({
    queryKey: ['drift-policy'],
    queryFn: () => apiClient.getDriftPolicy(),
    retry: false,
  });

  // Fetch templates
  const { data: templatesData, isLoading: templatesLoading } = useQuery({
    queryKey: ['drift-policy-templates'],
    queryFn: () => apiClient.getDriftPolicyTemplates(),
    retry: false,
  });

  const policy = policyData?.data;
  const templates = templatesData?.data || [];

  // Update policy mutation
  const updateMutation = useMutation({
    mutationFn: (payload: DriftPolicyUpdate) => apiClient.updateDriftPolicy(payload),
    onSuccess: () => {
      toast.success('Drift policy updated successfully');
      queryClient.invalidateQueries({ queryKey: ['drift-policy'] });
      setIsDirty(false);
      setLocalPolicy(null);
    },
    onError: (error: any) => {
      toast.error(`Failed to update policy: ${error.message}`);
    },
  });

  // Apply template mutation
  const applyTemplateMutation = useMutation({
    mutationFn: (templateId: string) => apiClient.applyDriftPolicyTemplate(templateId),
    onSuccess: () => {
      toast.success('Template applied successfully');
      queryClient.invalidateQueries({ queryKey: ['drift-policy'] });
      setIsDirty(false);
      setLocalPolicy(null);
    },
    onError: (error: any) => {
      toast.error(`Failed to apply template: ${error.message}`);
    },
  });

  // Cleanup mutation
  const cleanupMutation = useMutation({
    mutationFn: () => apiClient.triggerDriftRetentionCleanup(),
    onSuccess: (data) => {
      const results = data.data.results;
      const total = results.closed_incidents_deleted + results.reconciliation_artifacts_deleted + results.approvals_deleted;
      if (total > 0) {
        toast.success(
          `Cleanup completed: ${results.closed_incidents_deleted} incidents, ` +
          `${results.reconciliation_artifacts_deleted} artifacts, ${results.approvals_deleted} approvals deleted`
        );
      } else {
        toast.info('No data to clean up based on current retention settings');
      }
    },
    onError: (error: any) => {
      toast.error(`Failed to run cleanup: ${error.message}`);
    },
  });

  const handleFieldChange = (field: keyof DriftPolicyUpdate, value: any) => {
    setLocalPolicy(prev => ({
      ...prev,
      [field]: value,
    }));
    setIsDirty(true);
  };

  const handleSave = () => {
    if (localPolicy) {
      updateMutation.mutate(localPolicy);
    }
  };

  const getValue = <K extends keyof DriftPolicy>(field: K): DriftPolicy[K] | undefined => {
    if (localPolicy && field in localPolicy) {
      return localPolicy[field as keyof DriftPolicyUpdate] as DriftPolicy[K];
    }
    return policy?.[field];
  };

  if (policyLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Drift Policies</h1>
            <p className="text-muted-foreground">Configure TTL/SLA enforcement and deployment blocking rules</p>
          </div>
        </div>
        <LoadingState
          resource="drift policy configuration"
          message="Loading your drift policy settings..."
          size="md"
        />
      </div>
    );
  }

  // Handle feature not available error
  if (policyError) {
    const errorDetail = (policyError as any)?.response?.data?.detail;
    if (errorDetail?.error === 'feature_not_available') {
      return (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Drift Policies</h1>
              <p className="text-muted-foreground">Configure TTL/SLA enforcement and deployment blocking rules</p>
            </div>
          </div>
          <Card>
            <CardContent className="pt-6">
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <ShieldAlert className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">Feature Not Available</h3>
                <p className="text-muted-foreground max-w-md">
                  Drift policies are an Enterprise feature. Upgrade your plan to configure TTL/SLA enforcement,
                  automatic incident creation, and deployment blocking rules.
                </p>
                <Button className="mt-4" variant="outline">
                  View Plans
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      );
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Drift Policies</h1>
          <p className="text-muted-foreground">Configure TTL/SLA enforcement and deployment blocking rules</p>
        </div>
        <div className="flex items-center gap-2">
          {isDirty && (
            <Badge variant="outline" className="text-amber-600 border-amber-600">
              Unsaved Changes
            </Badge>
          )}
          <Button
            onClick={handleSave}
            disabled={!isDirty || updateMutation.isPending}
          >
            {updateMutation.isPending ? (
              <LoadingSpinner size="sm" className="mr-2" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>

      <Tabs defaultValue="ttl" className="space-y-4">
        <TabsList>
          <TabsTrigger value="ttl" className="flex items-center gap-2">
            <Clock className="h-4 w-4" />
            TTL Settings
          </TabsTrigger>
          <TabsTrigger value="enforcement" className="flex items-center gap-2">
            <Shield className="h-4 w-4" />
            Enforcement
          </TabsTrigger>
          <TabsTrigger value="notifications" className="flex items-center gap-2">
            <Bell className="h-4 w-4" />
            Notifications
          </TabsTrigger>
          <TabsTrigger value="retention" className="flex items-center gap-2">
            <Ban className="h-4 w-4" />
            Retention
          </TabsTrigger>
          <TabsTrigger value="templates" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Templates
          </TabsTrigger>
        </TabsList>

        {/* TTL Settings Tab */}
        <TabsContent value="ttl" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Time-to-Live Settings
              </CardTitle>
              <CardDescription>
                Configure how long drift incidents can remain open before requiring action
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="default_ttl">Default TTL (hours)</Label>
                  <Input
                    id="default_ttl"
                    type="number"
                    min={1}
                    value={getValue('default_ttl_hours') ?? 72}
                    onChange={(e) => handleFieldChange('default_ttl_hours', parseInt(e.target.value))}
                  />
                  <p className="text-xs text-muted-foreground">
                    Default time before incidents require attention
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="warning_hours">Expiration Warning (hours before)</Label>
                  <Input
                    id="warning_hours"
                    type="number"
                    min={1}
                    value={getValue('expiration_warning_hours') ?? 24}
                    onChange={(e) => handleFieldChange('expiration_warning_hours', parseInt(e.target.value))}
                  />
                  <p className="text-xs text-muted-foreground">
                    Send warning notification this many hours before expiration
                  </p>
                </div>
              </div>

              <div className="border-t pt-4">
                <h4 className="font-medium mb-4">TTL by Severity</h4>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                  <div className="space-y-2">
                    <Label className="flex items-center gap-2">
                      <Badge variant="destructive" className="text-xs">Critical</Badge>
                    </Label>
                    <Input
                      type="number"
                      min={1}
                      value={getValue('critical_ttl_hours') ?? 24}
                      onChange={(e) => handleFieldChange('critical_ttl_hours', parseInt(e.target.value))}
                    />
                    <p className="text-xs text-muted-foreground">hours</p>
                  </div>

                  <div className="space-y-2">
                    <Label className="flex items-center gap-2">
                      <Badge variant="outline" className="text-orange-600 border-orange-600 text-xs">High</Badge>
                    </Label>
                    <Input
                      type="number"
                      min={1}
                      value={getValue('high_ttl_hours') ?? 48}
                      onChange={(e) => handleFieldChange('high_ttl_hours', parseInt(e.target.value))}
                    />
                    <p className="text-xs text-muted-foreground">hours</p>
                  </div>

                  <div className="space-y-2">
                    <Label className="flex items-center gap-2">
                      <Badge variant="outline" className="text-yellow-600 border-yellow-600 text-xs">Medium</Badge>
                    </Label>
                    <Input
                      type="number"
                      min={1}
                      value={getValue('medium_ttl_hours') ?? 72}
                      onChange={(e) => handleFieldChange('medium_ttl_hours', parseInt(e.target.value))}
                    />
                    <p className="text-xs text-muted-foreground">hours</p>
                  </div>

                  <div className="space-y-2">
                    <Label className="flex items-center gap-2">
                      <Badge variant="secondary" className="text-xs">Low</Badge>
                    </Label>
                    <Input
                      type="number"
                      min={1}
                      value={getValue('low_ttl_hours') ?? 168}
                      onChange={(e) => handleFieldChange('low_ttl_hours', parseInt(e.target.value))}
                    />
                    <p className="text-xs text-muted-foreground">hours</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Enforcement Tab */}
        <TabsContent value="enforcement" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Deployment Blocking
              </CardTitle>
              <CardDescription>
                Control when deployments are blocked due to drift
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label className="flex items-center gap-2">
                    <Ban className="h-4 w-4 text-red-500" />
                    Block on Expired TTL
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    Block deployments when drift incidents have exceeded their TTL
                  </p>
                </div>
                <Switch
                  checked={getValue('block_deployments_on_expired') ?? false}
                  onCheckedChange={(checked) => handleFieldChange('block_deployments_on_expired', checked)}
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label className="flex items-center gap-2">
                    <ShieldAlert className="h-4 w-4 text-amber-500" />
                    Block on Active Drift
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    Block all deployments when any active drift incident exists
                  </p>
                </div>
                <Switch
                  checked={getValue('block_deployments_on_drift') ?? false}
                  onCheckedChange={(checked) => handleFieldChange('block_deployments_on_drift', checked)}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5" />
                Automatic Incident Creation
              </CardTitle>
              <CardDescription>
                Control when drift incidents are automatically created
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Auto-Create Incidents</Label>
                  <p className="text-sm text-muted-foreground">
                    Automatically create incidents when drift is detected
                  </p>
                </div>
                <Switch
                  checked={getValue('auto_create_incidents') ?? false}
                  onCheckedChange={(checked) => handleFieldChange('auto_create_incidents', checked)}
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Production Only</Label>
                  <p className="text-sm text-muted-foreground">
                    Only auto-create incidents for production environments
                  </p>
                </div>
                <Switch
                  checked={getValue('auto_create_for_production_only') ?? true}
                  onCheckedChange={(checked) => handleFieldChange('auto_create_for_production_only', checked)}
                  disabled={!getValue('auto_create_incidents')}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Notifications Tab */}
        <TabsContent value="notifications" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell className="h-5 w-5" />
                Notification Settings
              </CardTitle>
              <CardDescription>
                Configure when notifications are sent for drift events
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Notify on Detection</Label>
                  <p className="text-sm text-muted-foreground">
                    Send notification when drift is first detected
                  </p>
                </div>
                <Switch
                  checked={getValue('notify_on_detection') ?? true}
                  onCheckedChange={(checked) => handleFieldChange('notify_on_detection', checked)}
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Notify on Expiration Warning</Label>
                  <p className="text-sm text-muted-foreground">
                    Send notification before TTL expires
                  </p>
                </div>
                <Switch
                  checked={getValue('notify_on_expiration_warning') ?? true}
                  onCheckedChange={(checked) => handleFieldChange('notify_on_expiration_warning', checked)}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Retention Tab */}
        <TabsContent value="retention" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Ban className="h-5 w-5" />
                Data Retention Settings
              </CardTitle>
              <CardDescription>
                Configure how long drift data is retained before automatic deletion.
                Retention periods are plan-based with configurable overrides.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Enable Retention Cleanup</Label>
                  <p className="text-sm text-muted-foreground">
                    Automatically delete old drift data based on retention periods
                  </p>
                </div>
                <Switch
                  checked={getValue('retention_enabled') ?? true}
                  onCheckedChange={(checked) => handleFieldChange('retention_enabled', checked)}
                />
              </div>

              {getValue('retention_enabled') && (
                <div className="border-t pt-6 space-y-6">
                  <div className="space-y-2">
                    <Label htmlFor="retention_closed_incidents">Closed Incidents Retention (days)</Label>
                    <Input
                      id="retention_closed_incidents"
                      type="number"
                      min={0}
                      value={getValue('retention_days_closed_incidents') ?? 365}
                      onChange={(e) => handleFieldChange('retention_days_closed_incidents', parseInt(e.target.value) || 0)}
                    />
                    <p className="text-xs text-muted-foreground">
                      Closed incidents older than this will be deleted. Set to 0 to never delete.
                      <br />
                      <strong>Plan defaults:</strong> Free: 90 days, Pro: 180 days, Agency: 365 days, Enterprise: 2555 days (7 years)
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="retention_artifacts">Reconciliation Artifacts Retention (days)</Label>
                    <Input
                      id="retention_artifacts"
                      type="number"
                      min={0}
                      value={getValue('retention_days_reconciliation_artifacts') ?? 180}
                      onChange={(e) => handleFieldChange('retention_days_reconciliation_artifacts', parseInt(e.target.value) || 0)}
                    />
                    <p className="text-xs text-muted-foreground">
                      Reconciliation artifacts older than this will be deleted. Set to 0 to never delete.
                      <br />
                      <strong>Plan defaults:</strong> Free: 30 days, Pro: 90 days, Agency: 180 days, Enterprise: 365 days
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="retention_approvals">Approval Records Retention (days)</Label>
                    <Input
                      id="retention_approvals"
                      type="number"
                      min={0}
                      value={getValue('retention_days_approvals') ?? 365}
                      onChange={(e) => handleFieldChange('retention_days_approvals', parseInt(e.target.value) || 0)}
                    />
                    <p className="text-xs text-muted-foreground">
                      Approval records older than this will be deleted. Set to 0 to never delete.
                      <br />
                      <strong>Plan defaults:</strong> Free: 90 days, Pro: 180 days, Agency: 365 days, Enterprise: 2555 days (7 years)
                    </p>
                  </div>

                  <div className="p-4 bg-blue-50 dark:bg-blue-950/30 rounded-lg border border-blue-200 dark:border-blue-800">
                    <p className="text-sm text-blue-900 dark:text-blue-100">
                      <strong>Note:</strong> Retention cleanup runs daily. Data is permanently deleted and cannot be recovered.
                      Ensure your retention periods meet compliance requirements.
                    </p>
                  </div>

                  <div className="border-t pt-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <Label>Manual Cleanup</Label>
                        <p className="text-sm text-muted-foreground">
                          Trigger cleanup immediately (runs the same logic as scheduled job)
                        </p>
                      </div>
                      <Button
                        variant="outline"
                        onClick={() => cleanupMutation.mutate()}
                        disabled={cleanupMutation.isPending}
                      >
                        {cleanupMutation.isPending ? (
                          <LoadingSpinner size="sm" className="mr-2" />
                        ) : (
                          <Ban className="mr-2 h-4 w-4" />
                        )}
                        {cleanupMutation.isPending ? 'Running cleanup...' : 'Run Cleanup Now'}
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Templates Tab */}
        <TabsContent value="templates" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Policy Templates
              </CardTitle>
              <CardDescription>
                Apply a predefined policy template to quickly configure settings
              </CardDescription>
            </CardHeader>
            <CardContent>
              {templatesLoading ? (
                <div className="grid gap-4 md:grid-cols-3">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <SkeletonCard key={i} showHeader={true} contentLines={3} />
                  ))}
                </div>
              ) : templates.length === 0 ? (
                <p className="text-muted-foreground text-center py-8">No templates available</p>
              ) : (
                <div className="grid gap-4 md:grid-cols-3">
                  {templates.map((template) => (
                    <Card key={template.id} className="relative">
                      <CardHeader className="pb-2">
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-base">{template.name}</CardTitle>
                          {template.is_system && (
                            <Badge variant="secondary" className="text-xs">System</Badge>
                          )}
                        </div>
                        <CardDescription className="text-xs">
                          {template.description || 'No description'}
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="pt-2">
                        <div className="text-xs text-muted-foreground space-y-1 mb-4">
                          <p>Default TTL: {template.policy_config.default_ttl_hours || 72}h</p>
                          <p>Critical TTL: {template.policy_config.critical_ttl_hours || 24}h</p>
                          <p>Block on expired: {template.policy_config.block_deployments_on_expired ? 'Yes' : 'No'}</p>
                        </div>
                        <Button
                          size="sm"
                          variant="outline"
                          className="w-full"
                          onClick={() => applyTemplateMutation.mutate(template.id)}
                          disabled={applyTemplateMutation.isPending}
                        >
                          {applyTemplateMutation.isPending ? (
                            <LoadingSpinner size="xs" className="mr-2" />
                          ) : (
                            <CheckCircle className="mr-2 h-3 w-3" />
                          )}
                          {applyTemplateMutation.isPending ? 'Applying...' : 'Apply Template'}
                        </Button>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
