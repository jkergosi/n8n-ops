import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Bell,
  Plus,
  Workflow,
  CheckCircle,
  AlertTriangle,
  Info,
  Edit,
  Trash2,
  Send,
  Play,
  RefreshCw,
  Loader2,
  XCircle,
  Clock,
} from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import type {
  NotificationChannel,
  NotificationRule,
  AlertEvent,
  EventCatalogItem,
  Environment,
} from '@/types';

export function AlertsPage() {
  const queryClient = useQueryClient();
  const [createChannelOpen, setCreateChannelOpen] = useState(false);
  const [editChannelOpen, setEditChannelOpen] = useState(false);
  const [createRuleOpen, setCreateRuleOpen] = useState(false);
  const [editRuleOpen, setEditRuleOpen] = useState(false);
  const [selectedChannel, setSelectedChannel] = useState<NotificationChannel | null>(null);
  const [selectedRule, setSelectedRule] = useState<NotificationRule | null>(null);

  const [channelForm, setChannelForm] = useState({
    name: '',
    environmentId: '',
    workflowId: '',
    webhookPath: '/webhook',
    isEnabled: true,
  });

  const [ruleForm, setRuleForm] = useState({
    eventType: '',
    channelIds: [] as string[],
    isEnabled: true,
  });

  // Queries
  const { data: channelsData, isLoading: channelsLoading, refetch: refetchChannels } = useQuery({
    queryKey: ['notification-channels'],
    queryFn: () => apiClient.getNotificationChannels(),
  });

  const { data: rulesData, isLoading: rulesLoading, refetch: refetchRules } = useQuery({
    queryKey: ['notification-rules'],
    queryFn: () => apiClient.getNotificationRules(),
  });

  const { data: eventsData, isLoading: eventsLoading, refetch: refetchEvents } = useQuery({
    queryKey: ['alert-events'],
    queryFn: () => apiClient.getAlertEvents({ limit: 50 }),
  });

  const { data: catalogData } = useQuery({
    queryKey: ['event-catalog'],
    queryFn: () => apiClient.getEventCatalog(),
  });

  const { data: environmentsData } = useQuery({
    queryKey: ['environments'],
    queryFn: () => apiClient.getEnvironments(),
  });

  const channels = channelsData?.data ?? [];
  const rules = rulesData?.data ?? [];
  const events = eventsData?.data ?? [];
  const eventCatalog = catalogData?.data ?? [];
  const environments = environmentsData?.data ?? [];

  // Mutations
  const createChannelMutation = useMutation({
    mutationFn: (data: { name: string; configJson: { environmentId: string; workflowId: string; webhookPath: string }; isEnabled: boolean }) =>
      apiClient.createNotificationChannel(data),
    onSuccess: () => {
      toast.success('Notification channel created');
      queryClient.invalidateQueries({ queryKey: ['notification-channels'] });
      setCreateChannelOpen(false);
      resetChannelForm();
    },
    onError: (error: Error) => {
      toast.error(`Failed to create channel: ${error.message}`);
    },
  });

  const updateChannelMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<NotificationChannel> }) =>
      apiClient.updateNotificationChannel(id, data),
    onSuccess: () => {
      toast.success('Notification channel updated');
      queryClient.invalidateQueries({ queryKey: ['notification-channels'] });
      setEditChannelOpen(false);
      setSelectedChannel(null);
    },
    onError: (error: Error) => {
      toast.error(`Failed to update channel: ${error.message}`);
    },
  });

  const deleteChannelMutation = useMutation({
    mutationFn: (id: string) => apiClient.deleteNotificationChannel(id),
    onSuccess: () => {
      toast.success('Notification channel deleted');
      queryClient.invalidateQueries({ queryKey: ['notification-channels'] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to delete channel: ${error.message}`);
    },
  });

  const testChannelMutation = useMutation({
    mutationFn: (id: string) => apiClient.testNotificationChannel(id),
    onSuccess: (result) => {
      if (result.data.success) {
        toast.success(result.data.message || 'Test notification sent successfully');
      } else {
        toast.error(result.data.message || 'Test notification failed');
      }
    },
    onError: (error: Error) => {
      toast.error(`Test failed: ${error.message}`);
    },
  });

  const createRuleMutation = useMutation({
    mutationFn: (data: { eventType: string; channelIds: string[]; isEnabled: boolean }) =>
      apiClient.createNotificationRule(data),
    onSuccess: () => {
      toast.success('Notification rule created');
      queryClient.invalidateQueries({ queryKey: ['notification-rules'] });
      setCreateRuleOpen(false);
      resetRuleForm();
    },
    onError: (error: Error) => {
      toast.error(`Failed to create rule: ${error.message}`);
    },
  });

  const updateRuleMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<NotificationRule> }) =>
      apiClient.updateNotificationRule(id, data),
    onSuccess: () => {
      toast.success('Notification rule updated');
      queryClient.invalidateQueries({ queryKey: ['notification-rules'] });
      setEditRuleOpen(false);
      setSelectedRule(null);
    },
    onError: (error: Error) => {
      toast.error(`Failed to update rule: ${error.message}`);
    },
  });

  const deleteRuleMutation = useMutation({
    mutationFn: (id: string) => apiClient.deleteNotificationRule(id),
    onSuccess: () => {
      toast.success('Notification rule deleted');
      queryClient.invalidateQueries({ queryKey: ['notification-rules'] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to delete rule: ${error.message}`);
    },
  });

  // Helpers
  const resetChannelForm = () => {
    setChannelForm({
      name: '',
      environmentId: '',
      workflowId: '',
      webhookPath: '/webhook',
      isEnabled: true,
    });
  };

  const resetRuleForm = () => {
    setRuleForm({
      eventType: '',
      channelIds: [],
      isEnabled: true,
    });
  };

  const handleCreateChannel = () => {
    if (!channelForm.name || !channelForm.environmentId || !channelForm.workflowId) {
      toast.error('Please fill in all required fields');
      return;
    }
    createChannelMutation.mutate({
      name: channelForm.name,
      configJson: {
        environmentId: channelForm.environmentId,
        workflowId: channelForm.workflowId,
        webhookPath: channelForm.webhookPath,
      },
      isEnabled: channelForm.isEnabled,
    });
  };

  const handleUpdateChannel = () => {
    if (!selectedChannel) return;
    updateChannelMutation.mutate({
      id: selectedChannel.id,
      data: {
        name: channelForm.name,
        configJson: {
          environmentId: channelForm.environmentId,
          workflowId: channelForm.workflowId,
          webhookPath: channelForm.webhookPath,
        },
        isEnabled: channelForm.isEnabled,
      },
    });
  };

  const handleEditChannel = (channel: NotificationChannel) => {
    setSelectedChannel(channel);
    setChannelForm({
      name: channel.name,
      environmentId: channel.configJson.environmentId,
      workflowId: channel.configJson.workflowId,
      webhookPath: channel.configJson.webhookPath || '/webhook',
      isEnabled: channel.isEnabled,
    });
    setEditChannelOpen(true);
  };

  const handleCreateRule = () => {
    if (!ruleForm.eventType || ruleForm.channelIds.length === 0) {
      toast.error('Please select an event type and at least one channel');
      return;
    }
    createRuleMutation.mutate(ruleForm);
  };

  const handleUpdateRule = () => {
    if (!selectedRule) return;
    updateRuleMutation.mutate({
      id: selectedRule.id,
      data: {
        channelIds: ruleForm.channelIds,
        isEnabled: ruleForm.isEnabled,
      },
    });
  };

  const handleEditRule = (rule: NotificationRule) => {
    setSelectedRule(rule);
    setRuleForm({
      eventType: rule.eventType,
      channelIds: rule.channelIds,
      isEnabled: rule.isEnabled,
    });
    setEditRuleOpen(true);
  };

  const toggleRuleChannel = (channelId: string) => {
    setRuleForm((prev) => ({
      ...prev,
      channelIds: prev.channelIds.includes(channelId)
        ? prev.channelIds.filter((id) => id !== channelId)
        : [...prev.channelIds, channelId],
    }));
  };

  const getEventDisplayName = (eventType: string): string => {
    const catalogItem = eventCatalog.find((item) => item.eventType === eventType);
    return catalogItem?.displayName || eventType;
  };

  const getEventCategory = (eventType: string): string => {
    const catalogItem = eventCatalog.find((item) => item.eventType === eventType);
    return catalogItem?.category || 'Other';
  };

  const getEnvironmentName = (envId: string): string => {
    const env = environments.find((e) => e.id === envId);
    return env?.name || envId;
  };

  const getChannelName = (channelId: string): string => {
    const channel = channels.find((c) => c.id === channelId);
    return channel?.name || channelId;
  };

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'sent':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'pending':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'skipped':
        return <AlertTriangle className="h-4 w-4 text-muted-foreground" />;
      default:
        return <Info className="h-4 w-4 text-blue-500" />;
    }
  };

  const getEventTypeIcon = (eventType: string) => {
    if (eventType.includes('fail') || eventType.includes('error') || eventType.includes('unhealthy')) {
      return <AlertTriangle className="h-5 w-5 text-red-500" />;
    }
    if (eventType.includes('success') || eventType.includes('completed') || eventType.includes('recovered')) {
      return <CheckCircle className="h-5 w-5 text-green-500" />;
    }
    if (eventType.includes('started') || eventType.includes('pending')) {
      return <Info className="h-5 w-5 text-blue-500" />;
    }
    return <Bell className="h-5 w-5 text-muted-foreground" />;
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    return date.toLocaleDateString();
  };

  // Group event catalog by category
  const catalogByCategory = eventCatalog.reduce((acc, item) => {
    if (!acc[item.category]) {
      acc[item.category] = [];
    }
    acc[item.category].push(item);
    return acc;
  }, {} as Record<string, EventCatalogItem[]>);

  const handleRefreshAll = () => {
    refetchChannels();
    refetchRules();
    refetchEvents();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Alerts</h1>
          <p className="text-muted-foreground">Configure notification channels and event rules</p>
        </div>
        <Button variant="outline" onClick={handleRefreshAll}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Notification Channels */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Workflow className="h-5 w-5" />
                  Notification Channels
                </CardTitle>
                <CardDescription>n8n workflows that receive event notifications</CardDescription>
              </div>
              <Button size="sm" onClick={() => setCreateChannelOpen(true)}>
                <Plus className="h-4 w-4 mr-1" />
                Add Channel
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {channelsLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : channels.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Bell className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>No notification channels configured</p>
                <p className="text-sm">Add a channel to start receiving alerts</p>
              </div>
            ) : (
              channels.map((channel) => (
                <div
                  key={channel.id}
                  className="flex items-center justify-between p-4 rounded-lg border"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-muted">
                      <Workflow className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="font-medium">{channel.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {getEnvironmentName(channel.configJson.environmentId)} → {channel.configJson.workflowId}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={channel.isEnabled ? 'success' : 'outline'}>
                      {channel.isEnabled ? 'Active' : 'Disabled'}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => testChannelMutation.mutate(channel.id)}
                      disabled={testChannelMutation.isPending}
                      title="Test channel"
                    >
                      {testChannelMutation.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Play className="h-4 w-4" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleEditChannel(channel)}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => {
                        if (confirm('Delete this notification channel?')) {
                          deleteChannelMutation.mutate(channel.id);
                        }
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Notification Rules */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5" />
                  Notification Rules
                </CardTitle>
                <CardDescription>Define which events trigger which channels</CardDescription>
              </div>
              <Button
                size="sm"
                onClick={() => setCreateRuleOpen(true)}
                disabled={channels.length === 0}
              >
                <Plus className="h-4 w-4 mr-1" />
                Add Rule
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {rulesLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : rules.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <CheckCircle className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>No notification rules configured</p>
                <p className="text-sm">
                  {channels.length === 0
                    ? 'Add a channel first, then create rules'
                    : 'Create rules to route events to channels'}
                </p>
              </div>
            ) : (
              rules.map((rule) => (
                <div
                  key={rule.id}
                  className="flex items-center justify-between p-4 rounded-lg border"
                >
                  <div>
                    <p className="font-medium">{getEventDisplayName(rule.eventType)}</p>
                    <p className="text-sm text-muted-foreground">
                      <code className="bg-muted px-1 rounded">{rule.eventType}</code>
                      <span className="mx-2">→</span>
                      {rule.channelIds.length} channel(s)
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={rule.isEnabled ? 'success' : 'outline'}>
                      {rule.isEnabled ? 'Active' : 'Disabled'}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleEditRule(rule)}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => {
                        if (confirm('Delete this notification rule?')) {
                          deleteRuleMutation.mutate(rule.id);
                        }
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Events */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Send className="h-5 w-5" />
            Recent Activity
          </CardTitle>
          <CardDescription>Log of recent events and notification status</CardDescription>
        </CardHeader>
        <CardContent>
          {eventsLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : events.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Send className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>No recent events</p>
              <p className="text-sm">Events will appear here as they occur</p>
            </div>
          ) : (
            <div className="space-y-4">
              {events.map((event) => (
                <div
                  key={event.id}
                  className="flex items-start gap-4 p-4 rounded-lg border"
                >
                  {getEventTypeIcon(event.eventType)}
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <p className="font-medium">{getEventDisplayName(event.eventType)}</p>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">
                          {formatTimestamp(event.timestamp)}
                        </span>
                        <div className="flex items-center gap-1">
                          {getStatusIcon(event.notificationStatus)}
                          <Badge
                            variant={
                              event.notificationStatus === 'sent'
                                ? 'success'
                                : event.notificationStatus === 'failed'
                                  ? 'destructive'
                                  : 'outline'
                            }
                            className="text-xs"
                          >
                            {event.notificationStatus || 'no rule'}
                          </Badge>
                        </div>
                      </div>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      <code className="bg-muted px-1 rounded text-xs">{event.eventType}</code>
                      {event.environmentId && (
                        <span className="ml-2">
                          Environment: {getEnvironmentName(event.environmentId)}
                        </span>
                      )}
                    </p>
                    {event.metadataJson && Object.keys(event.metadataJson).length > 0 && (
                      <div className="mt-2 text-xs text-muted-foreground">
                        {Object.entries(event.metadataJson).map(([key, value]) => (
                          <span key={key} className="mr-3">
                            {key}: {String(value)}
                          </span>
                        ))}
                      </div>
                    )}
                    {event.channelsNotified && event.channelsNotified.length > 0 && (
                      <div className="mt-2 flex gap-1">
                        {event.channelsNotified.map((channelId) => (
                          <Badge key={channelId} variant="outline" className="text-xs">
                            {getChannelName(channelId)}
                          </Badge>
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

      {/* Create Channel Dialog */}
      <Dialog open={createChannelOpen} onOpenChange={setCreateChannelOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add Notification Channel</DialogTitle>
            <DialogDescription>
              Configure an n8n workflow to receive event notifications
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="channel-name">Channel Name</Label>
              <Input
                id="channel-name"
                placeholder="My Alert Workflow"
                value={channelForm.name}
                onChange={(e) => setChannelForm({ ...channelForm, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="channel-env">n8n Environment</Label>
              <Select
                value={channelForm.environmentId}
                onValueChange={(value) => setChannelForm({ ...channelForm, environmentId: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select environment" />
                </SelectTrigger>
                <SelectContent>
                  {environments.map((env) => (
                    <SelectItem key={env.id} value={env.id}>
                      {env.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="channel-workflow">Workflow ID</Label>
              <Input
                id="channel-workflow"
                placeholder="workflow-id-123"
                value={channelForm.workflowId}
                onChange={(e) => setChannelForm({ ...channelForm, workflowId: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">
                The n8n workflow ID that will receive webhook calls
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="channel-webhook">Webhook Path</Label>
              <Input
                id="channel-webhook"
                placeholder="/webhook"
                value={channelForm.webhookPath}
                onChange={(e) => setChannelForm({ ...channelForm, webhookPath: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">
                The webhook trigger path in your n8n workflow
              </p>
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="channel-enabled">Enable channel</Label>
              <Switch
                id="channel-enabled"
                checked={channelForm.isEnabled}
                onCheckedChange={(checked) => setChannelForm({ ...channelForm, isEnabled: checked })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateChannelOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateChannel} disabled={createChannelMutation.isPending}>
              {createChannelMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Create Channel
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Channel Dialog */}
      <Dialog open={editChannelOpen} onOpenChange={setEditChannelOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Notification Channel</DialogTitle>
            <DialogDescription>
              Update the n8n workflow notification settings
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="edit-channel-name">Channel Name</Label>
              <Input
                id="edit-channel-name"
                value={channelForm.name}
                onChange={(e) => setChannelForm({ ...channelForm, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-channel-env">n8n Environment</Label>
              <Select
                value={channelForm.environmentId}
                onValueChange={(value) => setChannelForm({ ...channelForm, environmentId: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select environment" />
                </SelectTrigger>
                <SelectContent>
                  {environments.map((env) => (
                    <SelectItem key={env.id} value={env.id}>
                      {env.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-channel-workflow">Workflow ID</Label>
              <Input
                id="edit-channel-workflow"
                value={channelForm.workflowId}
                onChange={(e) => setChannelForm({ ...channelForm, workflowId: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-channel-webhook">Webhook Path</Label>
              <Input
                id="edit-channel-webhook"
                value={channelForm.webhookPath}
                onChange={(e) => setChannelForm({ ...channelForm, webhookPath: e.target.value })}
              />
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="edit-channel-enabled">Enable channel</Label>
              <Switch
                id="edit-channel-enabled"
                checked={channelForm.isEnabled}
                onCheckedChange={(checked) => setChannelForm({ ...channelForm, isEnabled: checked })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditChannelOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdateChannel} disabled={updateChannelMutation.isPending}>
              {updateChannelMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Rule Dialog */}
      <Dialog open={createRuleOpen} onOpenChange={setCreateRuleOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add Notification Rule</DialogTitle>
            <DialogDescription>Define which events trigger notifications</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="rule-event">Event Type</Label>
              <Select
                value={ruleForm.eventType}
                onValueChange={(value) => setRuleForm({ ...ruleForm, eventType: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select event type" />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(catalogByCategory).map(([category, items]) => (
                    <div key={category}>
                      <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                        {category}
                      </div>
                      {items.map((item) => (
                        <SelectItem key={item.eventType} value={item.eventType}>
                          {item.displayName}
                        </SelectItem>
                      ))}
                    </div>
                  ))}
                </SelectContent>
              </Select>
              {ruleForm.eventType && (
                <p className="text-xs text-muted-foreground">
                  {eventCatalog.find((e) => e.eventType === ruleForm.eventType)?.description}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label>Channels</Label>
              <div className="space-y-2 max-h-48 overflow-y-auto border rounded-md p-2">
                {channels.map((channel) => (
                  <label key={channel.id} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      className="rounded border-input"
                      checked={ruleForm.channelIds.includes(channel.id)}
                      onChange={() => toggleRuleChannel(channel.id)}
                    />
                    <span className="text-sm">{channel.name}</span>
                    {!channel.isEnabled && (
                      <Badge variant="outline" className="text-xs">disabled</Badge>
                    )}
                  </label>
                ))}
              </div>
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="rule-enabled">Enable rule</Label>
              <Switch
                id="rule-enabled"
                checked={ruleForm.isEnabled}
                onCheckedChange={(checked) => setRuleForm({ ...ruleForm, isEnabled: checked })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateRuleOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateRule} disabled={createRuleMutation.isPending}>
              {createRuleMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Create Rule
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Rule Dialog */}
      <Dialog open={editRuleOpen} onOpenChange={setEditRuleOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Notification Rule</DialogTitle>
            <DialogDescription>
              Update channels for {selectedRule && getEventDisplayName(selectedRule.eventType)}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Event Type</Label>
              <div className="p-2 border rounded-md bg-muted">
                <p className="font-medium">{selectedRule && getEventDisplayName(selectedRule.eventType)}</p>
                <code className="text-xs text-muted-foreground">{selectedRule?.eventType}</code>
              </div>
            </div>
            <div className="space-y-2">
              <Label>Channels</Label>
              <div className="space-y-2 max-h-48 overflow-y-auto border rounded-md p-2">
                {channels.map((channel) => (
                  <label key={channel.id} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      className="rounded border-input"
                      checked={ruleForm.channelIds.includes(channel.id)}
                      onChange={() => toggleRuleChannel(channel.id)}
                    />
                    <span className="text-sm">{channel.name}</span>
                    {!channel.isEnabled && (
                      <Badge variant="outline" className="text-xs">disabled</Badge>
                    )}
                  </label>
                ))}
              </div>
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="edit-rule-enabled">Enable rule</Label>
              <Switch
                id="edit-rule-enabled"
                checked={ruleForm.isEnabled}
                onCheckedChange={(checked) => setRuleForm({ ...ruleForm, isEnabled: checked })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditRuleOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdateRule} disabled={updateRuleMutation.isPending}>
              {updateRuleMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
