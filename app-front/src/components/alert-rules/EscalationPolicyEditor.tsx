import React from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Plus, Trash2, ArrowUp, ArrowDown, AlertCircle, AlertTriangle, Bell, Siren } from 'lucide-react';
import type { EscalationPolicy, EscalationLevel, AlertSeverity, NotificationChannel } from '@/types';

interface EscalationPolicyEditorProps {
  policy: EscalationPolicy | undefined;
  onChange: (policy: EscalationPolicy | undefined) => void;
  channels: NotificationChannel[];
}

const SEVERITY_CONFIG: Record<AlertSeverity, { label: string; icon: React.ReactNode; color: string }> = {
  info: { label: 'Info', icon: <Bell className="h-4 w-4" />, color: 'text-blue-500' },
  warning: { label: 'Warning', icon: <AlertTriangle className="h-4 w-4" />, color: 'text-yellow-500' },
  critical: { label: 'Critical', icon: <AlertCircle className="h-4 w-4" />, color: 'text-orange-500' },
  page: { label: 'Page', icon: <Siren className="h-4 w-4" />, color: 'text-red-500' },
};

const DEFAULT_LEVEL: EscalationLevel = {
  delay_minutes: 0,
  channel_ids: [],
  severity: 'warning',
};

const DEFAULT_POLICY: EscalationPolicy = {
  levels: [{ ...DEFAULT_LEVEL }],
  notify_on_resolve: true,
};

export function EscalationPolicyEditor({
  policy,
  onChange,
  channels,
}: EscalationPolicyEditorProps) {
  const isEnabled = policy !== undefined;

  const handleToggle = (enabled: boolean) => {
    if (enabled) {
      onChange({ ...DEFAULT_POLICY });
    } else {
      onChange(undefined);
    }
  };

  const updateLevel = (index: number, updates: Partial<EscalationLevel>) => {
    if (!policy) return;
    const newLevels = [...policy.levels];
    newLevels[index] = { ...newLevels[index], ...updates };
    onChange({ ...policy, levels: newLevels });
  };

  const addLevel = () => {
    if (!policy) return;
    const lastLevel = policy.levels[policy.levels.length - 1];
    const newLevel: EscalationLevel = {
      delay_minutes: (lastLevel?.delay_minutes || 0) + 15,
      channel_ids: [],
      severity: 'critical',
    };
    onChange({ ...policy, levels: [...policy.levels, newLevel] });
  };

  const removeLevel = (index: number) => {
    if (!policy || policy.levels.length <= 1) return;
    const newLevels = policy.levels.filter((_, i) => i !== index);
    onChange({ ...policy, levels: newLevels });
  };

  const moveLevel = (index: number, direction: 'up' | 'down') => {
    if (!policy) return;
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= policy.levels.length) return;

    const newLevels = [...policy.levels];
    [newLevels[index], newLevels[newIndex]] = [newLevels[newIndex], newLevels[index]];
    onChange({ ...policy, levels: newLevels });
  };

  const toggleChannelForLevel = (levelIndex: number, channelId: string) => {
    if (!policy) return;
    const level = policy.levels[levelIndex];
    const newChannelIds = level.channel_ids.includes(channelId)
      ? level.channel_ids.filter((id) => id !== channelId)
      : [...level.channel_ids, channelId];
    updateLevel(levelIndex, { channel_ids: newChannelIds });
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Escalation Policy</CardTitle>
          <Switch checked={isEnabled} onCheckedChange={handleToggle} />
        </div>
        <p className="text-sm text-muted-foreground">
          Configure automatic escalation when alerts remain unresolved
        </p>
      </CardHeader>

      {isEnabled && policy && (
        <CardContent className="space-y-6">
          {/* Escalation Levels */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>Escalation Levels</Label>
              {policy.levels.length < 5 && (
                <Button variant="outline" size="sm" onClick={addLevel}>
                  <Plus className="h-4 w-4 mr-1" />
                  Add Level
                </Button>
              )}
            </div>

            {policy.levels.map((level, index) => (
              <div
                key={index}
                className="border rounded-lg p-4 space-y-3 bg-muted/30"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm">Level {index + 1}</span>
                  <div className="flex items-center gap-1">
                    {index > 0 && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => moveLevel(index, 'up')}
                      >
                        <ArrowUp className="h-4 w-4" />
                      </Button>
                    )}
                    {index < policy.levels.length - 1 && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => moveLevel(index, 'down')}
                      >
                        <ArrowDown className="h-4 w-4" />
                      </Button>
                    )}
                    {policy.levels.length > 1 && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-destructive"
                        onClick={() => removeLevel(index)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs">Delay (minutes)</Label>
                    <Input
                      type="number"
                      min={0}
                      value={level.delay_minutes}
                      onChange={(e) =>
                        updateLevel(index, { delay_minutes: Number(e.target.value) })
                      }
                      className="mt-1 h-8"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      {index === 0
                        ? 'Immediate notification'
                        : `Wait ${level.delay_minutes} min after first trigger`}
                    </p>
                  </div>

                  <div>
                    <Label className="text-xs">Severity</Label>
                    <Select
                      value={level.severity}
                      onValueChange={(v) =>
                        updateLevel(index, { severity: v as AlertSeverity })
                      }
                    >
                      <SelectTrigger className="mt-1 h-8">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(SEVERITY_CONFIG).map(([key, config]) => (
                          <SelectItem key={key} value={key}>
                            <div className={`flex items-center gap-2 ${config.color}`}>
                              {config.icon}
                              <span>{config.label}</span>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div>
                  <Label className="text-xs">Channels</Label>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {channels.length === 0 ? (
                      <span className="text-xs text-muted-foreground">
                        No channels available
                      </span>
                    ) : (
                      channels.map((channel) => (
                        <Badge
                          key={channel.id}
                          variant={
                            level.channel_ids.includes(channel.id)
                              ? 'default'
                              : 'outline'
                          }
                          className="cursor-pointer text-xs"
                          onClick={() => toggleChannelForLevel(index, channel.id)}
                        >
                          {channel.name}
                        </Badge>
                      ))
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Additional Options */}
          <div className="space-y-4 pt-4 border-t">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-xs">Auto-resolve after (minutes)</Label>
                <Input
                  type="number"
                  min={1}
                  placeholder="Optional"
                  value={policy.auto_resolve_after_minutes || ''}
                  onChange={(e) =>
                    onChange({
                      ...policy,
                      auto_resolve_after_minutes: e.target.value
                        ? Number(e.target.value)
                        : undefined,
                    })
                  }
                  className="mt-1 h-8"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Auto-resolve if condition clears
                </p>
              </div>

              <div>
                <Label className="text-xs">Repeat interval (minutes)</Label>
                <Input
                  type="number"
                  min={5}
                  placeholder="Optional"
                  value={policy.repeat_interval_minutes || ''}
                  onChange={(e) =>
                    onChange({
                      ...policy,
                      repeat_interval_minutes: e.target.value
                        ? Number(e.target.value)
                        : undefined,
                    })
                  }
                  className="mt-1 h-8"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Repeat notifications at this interval
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                id="notifyResolve"
                checked={policy.notify_on_resolve !== false}
                onCheckedChange={(v) =>
                  onChange({ ...policy, notify_on_resolve: v })
                }
              />
              <Label htmlFor="notifyResolve" className="text-sm">
                Notify when alert resolves
              </Label>
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  );
}
