import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Loader2, AlertTriangle, Info, Zap, Clock, XCircle, Hash } from 'lucide-react';
import type {
  AlertRule,
  AlertRuleCreate,
  AlertRuleType,
  AlertRuleTypeCatalogItem,
  NotificationChannel,
  Environment,
} from '@/types';

interface AlertRuleBuilderProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (data: AlertRuleCreate) => Promise<void>;
  editingRule?: AlertRule;
  ruleTypeCatalog: AlertRuleTypeCatalogItem[];
  channels: NotificationChannel[];
  environments: Environment[];
  isLoading?: boolean;
}

const RULE_TYPE_ICONS: Record<AlertRuleType, React.ReactNode> = {
  error_rate: <AlertTriangle className="h-4 w-4" />,
  error_type: <XCircle className="h-4 w-4" />,
  workflow_failure: <Zap className="h-4 w-4" />,
  consecutive_failures: <Hash className="h-4 w-4" />,
  execution_duration: <Clock className="h-4 w-4" />,
};

export function AlertRuleBuilder({
  open,
  onOpenChange,
  onSave,
  editingRule,
  ruleTypeCatalog,
  channels,
  environments,
  isLoading = false,
}: AlertRuleBuilderProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [ruleType, setRuleType] = useState<AlertRuleType>('error_rate');
  const [environmentId, setEnvironmentId] = useState<string>('');
  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);
  const [isEnabled, setIsEnabled] = useState(true);
  const [saving, setSaving] = useState(false);

  // Threshold config state
  const [thresholdPercent, setThresholdPercent] = useState(10);
  const [timeWindowMinutes, setTimeWindowMinutes] = useState(60);
  const [minExecutions, setMinExecutions] = useState(10);
  const [errorTypes, setErrorTypes] = useState<string[]>([]);
  const [minOccurrences, setMinOccurrences] = useState(1);
  const [workflowIds, setWorkflowIds] = useState('');
  const [anyWorkflow, setAnyWorkflow] = useState(false);
  const [failureCount, setFailureCount] = useState(3);
  const [maxDurationMs, setMaxDurationMs] = useState(60000);

  // Available error types for error_type rule
  const ERROR_TYPES = [
    'Credential Error',
    'Timeout',
    'Connection Error',
    'HTTP 5xx',
    'HTTP 404',
    'HTTP 400',
    'Rate Limit',
    'Permission Error',
    'Validation Error',
    'Node Error',
    'Data Error',
    'Execution Error',
    'Unknown Error',
  ];

  useEffect(() => {
    if (editingRule) {
      setName(editingRule.name);
      setDescription(editingRule.description || '');
      setRuleType(editingRule.ruleType);
      setEnvironmentId(editingRule.environmentId || '');
      setSelectedChannels(editingRule.channelIds);
      setIsEnabled(editingRule.isEnabled);

      // Parse threshold config based on rule type
      const config = editingRule.thresholdConfig || {};
      switch (editingRule.ruleType) {
        case 'error_rate':
          setThresholdPercent((config.threshold_percent as number) || 10);
          setTimeWindowMinutes((config.time_window_minutes as number) || 60);
          setMinExecutions((config.min_executions as number) || 10);
          break;
        case 'error_type':
          setErrorTypes((config.error_types as string[]) || []);
          setTimeWindowMinutes((config.time_window_minutes as number) || 60);
          setMinOccurrences((config.min_occurrences as number) || 1);
          break;
        case 'workflow_failure':
          setWorkflowIds(((config.workflow_ids as string[]) || []).join(', '));
          setAnyWorkflow((config.any_workflow as boolean) || false);
          break;
        case 'consecutive_failures':
          setFailureCount((config.failure_count as number) || 3);
          setWorkflowIds(((config.workflow_ids as string[]) || []).join(', '));
          break;
        case 'execution_duration':
          setMaxDurationMs((config.max_duration_ms as number) || 60000);
          setWorkflowIds(((config.workflow_ids as string[]) || []).join(', '));
          break;
      }
    } else {
      // Reset form for new rule
      setName('');
      setDescription('');
      setRuleType('error_rate');
      setEnvironmentId('');
      setSelectedChannels([]);
      setIsEnabled(true);
      setThresholdPercent(10);
      setTimeWindowMinutes(60);
      setMinExecutions(10);
      setErrorTypes([]);
      setMinOccurrences(1);
      setWorkflowIds('');
      setAnyWorkflow(false);
      setFailureCount(3);
      setMaxDurationMs(60000);
    }
  }, [editingRule, open]);

  const buildThresholdConfig = (): Record<string, unknown> => {
    switch (ruleType) {
      case 'error_rate':
        return {
          threshold_percent: thresholdPercent,
          time_window_minutes: timeWindowMinutes,
          min_executions: minExecutions,
        };
      case 'error_type':
        return {
          error_types: errorTypes,
          time_window_minutes: timeWindowMinutes,
          min_occurrences: minOccurrences,
        };
      case 'workflow_failure':
        return {
          workflow_ids: workflowIds.split(',').map((s) => s.trim()).filter(Boolean),
          any_workflow: anyWorkflow,
        };
      case 'consecutive_failures':
        return {
          failure_count: failureCount,
          workflow_ids: workflowIds ? workflowIds.split(',').map((s) => s.trim()).filter(Boolean) : undefined,
        };
      case 'execution_duration':
        return {
          max_duration_ms: maxDurationMs,
          workflow_ids: workflowIds ? workflowIds.split(',').map((s) => s.trim()).filter(Boolean) : undefined,
        };
      default:
        return {};
    }
  };

  const handleSave = async () => {
    if (!name.trim()) return;

    setSaving(true);
    try {
      const data: AlertRuleCreate = {
        name: name.trim(),
        description: description.trim() || undefined,
        ruleType,
        thresholdConfig: buildThresholdConfig(),
        environmentId: environmentId || undefined,
        channelIds: selectedChannels,
        isEnabled,
      };

      await onSave(data);
      onOpenChange(false);
    } catch (error) {
      console.error('Failed to save alert rule:', error);
    } finally {
      setSaving(false);
    }
  };

  const toggleChannel = (channelId: string) => {
    setSelectedChannels((prev) =>
      prev.includes(channelId)
        ? prev.filter((id) => id !== channelId)
        : [...prev, channelId]
    );
  };

  const toggleErrorType = (errorType: string) => {
    setErrorTypes((prev) =>
      prev.includes(errorType)
        ? prev.filter((t) => t !== errorType)
        : [...prev, errorType]
    );
  };

  const selectedRuleTypeInfo = ruleTypeCatalog.find((r) => r.ruleType === ruleType);

  const renderThresholdConfig = () => {
    switch (ruleType) {
      case 'error_rate':
        return (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="threshold">Error Rate Threshold (%)</Label>
                <Input
                  id="threshold"
                  type="number"
                  min={0}
                  max={100}
                  value={thresholdPercent}
                  onChange={(e) => setThresholdPercent(Number(e.target.value))}
                  className="mt-1"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Alert when error rate exceeds this percentage
                </p>
              </div>
              <div>
                <Label htmlFor="timeWindow">Time Window (minutes)</Label>
                <Input
                  id="timeWindow"
                  type="number"
                  min={1}
                  max={1440}
                  value={timeWindowMinutes}
                  onChange={(e) => setTimeWindowMinutes(Number(e.target.value))}
                  className="mt-1"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Evaluate executions within this time window
                </p>
              </div>
            </div>
            <div>
              <Label htmlFor="minExec">Minimum Executions</Label>
              <Input
                id="minExec"
                type="number"
                min={1}
                value={minExecutions}
                onChange={(e) => setMinExecutions(Number(e.target.value))}
                className="mt-1"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Require at least this many executions before alerting
              </p>
            </div>
          </div>
        );

      case 'error_type':
        return (
          <div className="space-y-4">
            <div>
              <Label>Error Types to Match</Label>
              <div className="flex flex-wrap gap-2 mt-2">
                {ERROR_TYPES.map((type) => (
                  <Badge
                    key={type}
                    variant={errorTypes.includes(type) ? 'default' : 'outline'}
                    className="cursor-pointer"
                    onClick={() => toggleErrorType(type)}
                  >
                    {type}
                  </Badge>
                ))}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Select one or more error types to monitor
              </p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="timeWindow2">Time Window (minutes)</Label>
                <Input
                  id="timeWindow2"
                  type="number"
                  min={1}
                  max={1440}
                  value={timeWindowMinutes}
                  onChange={(e) => setTimeWindowMinutes(Number(e.target.value))}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="minOccur">Minimum Occurrences</Label>
                <Input
                  id="minOccur"
                  type="number"
                  min={1}
                  value={minOccurrences}
                  onChange={(e) => setMinOccurrences(Number(e.target.value))}
                  className="mt-1"
                />
              </div>
            </div>
          </div>
        );

      case 'workflow_failure':
        return (
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <Switch
                id="anyWorkflow"
                checked={anyWorkflow}
                onCheckedChange={setAnyWorkflow}
              />
              <Label htmlFor="anyWorkflow">Alert on any workflow failure</Label>
            </div>
            {!anyWorkflow && (
              <div>
                <Label htmlFor="wfIds">Workflow IDs (comma-separated)</Label>
                <Input
                  id="wfIds"
                  value={workflowIds}
                  onChange={(e) => setWorkflowIds(e.target.value)}
                  placeholder="workflow-id-1, workflow-id-2"
                  className="mt-1"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Specific n8n workflow IDs to monitor for failures
                </p>
              </div>
            )}
          </div>
        );

      case 'consecutive_failures':
        return (
          <div className="space-y-4">
            <div>
              <Label htmlFor="failCount">Consecutive Failure Threshold</Label>
              <Input
                id="failCount"
                type="number"
                min={1}
                max={100}
                value={failureCount}
                onChange={(e) => setFailureCount(Number(e.target.value))}
                className="mt-1"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Alert after this many consecutive failures
              </p>
            </div>
            <div>
              <Label htmlFor="wfIds2">Workflow IDs (optional, comma-separated)</Label>
              <Input
                id="wfIds2"
                value={workflowIds}
                onChange={(e) => setWorkflowIds(e.target.value)}
                placeholder="Leave empty for all workflows"
                className="mt-1"
              />
            </div>
          </div>
        );

      case 'execution_duration':
        return (
          <div className="space-y-4">
            <div>
              <Label htmlFor="maxDuration">Maximum Duration (milliseconds)</Label>
              <Input
                id="maxDuration"
                type="number"
                min={1000}
                value={maxDurationMs}
                onChange={(e) => setMaxDurationMs(Number(e.target.value))}
                className="mt-1"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Alert when executions exceed this duration ({(maxDurationMs / 1000).toFixed(1)} seconds)
              </p>
            </div>
            <div>
              <Label htmlFor="wfIds3">Workflow IDs (optional, comma-separated)</Label>
              <Input
                id="wfIds3"
                value={workflowIds}
                onChange={(e) => setWorkflowIds(e.target.value)}
                placeholder="Leave empty for all workflows"
                className="mt-1"
              />
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {editingRule ? 'Edit Alert Rule' : 'Create Alert Rule'}
          </DialogTitle>
          <DialogDescription>
            Configure threshold-based alerts with escalation policies
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Basic Info */}
          <div className="space-y-4">
            <div>
              <Label htmlFor="name">Rule Name *</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., High Error Rate Alert"
                className="mt-1"
              />
            </div>

            <div>
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe what this alert monitors..."
                className="mt-1"
                rows={2}
              />
            </div>
          </div>

          {/* Rule Type Selection */}
          <div>
            <Label>Rule Type *</Label>
            <Select value={ruleType} onValueChange={(v) => setRuleType(v as AlertRuleType)}>
              <SelectTrigger className="mt-1">
                <SelectValue placeholder="Select rule type" />
              </SelectTrigger>
              <SelectContent>
                {ruleTypeCatalog.map((type) => (
                  <SelectItem key={type.ruleType} value={type.ruleType}>
                    <div className="flex items-center gap-2">
                      {RULE_TYPE_ICONS[type.ruleType as AlertRuleType]}
                      <span>{type.displayName}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {selectedRuleTypeInfo && (
              <p className="text-xs text-muted-foreground mt-2 flex items-start gap-1">
                <Info className="h-3 w-3 mt-0.5 flex-shrink-0" />
                {selectedRuleTypeInfo.description}
              </p>
            )}
          </div>

          {/* Threshold Configuration */}
          <div className="border rounded-lg p-4">
            <h4 className="font-medium mb-4">Threshold Configuration</h4>
            {renderThresholdConfig()}
          </div>

          {/* Environment Scope */}
          <div>
            <Label>Environment Scope</Label>
            <Select value={environmentId || '__all__'} onValueChange={(v) => setEnvironmentId(v === '__all__' ? '' : v)}>
              <SelectTrigger className="mt-1">
                <SelectValue placeholder="All environments" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">All environments</SelectItem>
                {environments.map((env) => (
                  <SelectItem key={env.id} value={env.id}>
                    {env.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground mt-1">
              Optionally limit this rule to a specific environment
            </p>
          </div>

          {/* Notification Channels */}
          <div>
            <Label>Notification Channels</Label>
            <div className="flex flex-wrap gap-2 mt-2">
              {channels.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No channels configured. Create channels first.
                </p>
              ) : (
                channels.map((channel) => (
                  <Badge
                    key={channel.id}
                    variant={selectedChannels.includes(channel.id) ? 'default' : 'outline'}
                    className="cursor-pointer"
                    onClick={() => toggleChannel(channel.id)}
                  >
                    {channel.name}
                  </Badge>
                ))
              )}
            </div>
          </div>

          {/* Enable/Disable */}
          <div className="flex items-center space-x-2">
            <Switch id="enabled" checked={isEnabled} onCheckedChange={setIsEnabled} />
            <Label htmlFor="enabled">Rule enabled</Label>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving || !name.trim() || isLoading}>
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : editingRule ? (
              'Update Rule'
            ) : (
              'Create Rule'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
