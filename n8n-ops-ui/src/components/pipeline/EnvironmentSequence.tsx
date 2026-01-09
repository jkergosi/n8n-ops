import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ArrowRight } from 'lucide-react';
import type { Environment } from '@/types';
import { sortEnvironments } from '@/lib/environment-utils';

interface EnvironmentSequenceProps {
  environments: Environment[];
  selectedEnvironmentIds?: string[];
  onChange: (environmentIds: string[]) => void;
}

/**
 * Simplified environment selector for MVP single-hop pipelines.
 *
 * MVP Constraint: Pipelines support exactly 2 environments (source → target).
 * Multi-stage pipelines are not supported. Create separate pipelines for each hop
 * (e.g., dev→staging and staging→prod as two distinct pipelines).
 */
export function EnvironmentSequence({
  environments,
  selectedEnvironmentIds = [],
  onChange,
}: EnvironmentSequenceProps) {
  const sortedEnvironments = sortEnvironments(environments);

  // Extract source and target from the environment IDs array
  const sourceEnvId = selectedEnvironmentIds[0] || '';
  const targetEnvId = selectedEnvironmentIds[1] || '';

  const handleSourceChange = (newSourceId: string) => {
    // If new source equals current target, clear target
    if (newSourceId === targetEnvId) {
      onChange([newSourceId]);
    } else if (targetEnvId) {
      onChange([newSourceId, targetEnvId]);
    } else {
      onChange([newSourceId]);
    }
  };

  const handleTargetChange = (newTargetId: string) => {
    if (sourceEnvId) {
      onChange([sourceEnvId, newTargetId]);
    } else {
      // Shouldn't happen with UI constraints, but handle gracefully
      onChange(['', newTargetId]);
    }
  };

  const getEnvironment = (id: string) => {
    return environments.find((env) => env.id === id);
  };

  // Filter out the selected source from target options
  const targetOptions = sortedEnvironments.filter((env) => env.id !== sourceEnvId);

  const sourceEnv = getEnvironment(sourceEnvId);
  const targetEnv = getEnvironment(targetEnvId);

  const isComplete = sourceEnvId && targetEnvId;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Promotion Path</CardTitle>
        <CardDescription>
          Select the source and target environments for this pipeline. Each pipeline defines a single promotion hop.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Source/Target Selectors */}
        <div className="flex items-center gap-4">
          {/* Source Environment */}
          <div className="flex-1 space-y-2">
            <label className="text-sm font-medium text-muted-foreground">
              Source Environment
            </label>
            <Select
              value={sourceEnvId}
              onValueChange={handleSourceChange}
            >
              <SelectTrigger data-testid="source-environment-select">
                <SelectValue placeholder="Select source..." />
              </SelectTrigger>
              <SelectContent>
                {sortedEnvironments.map((env) => (
                  <SelectItem key={env.id} value={env.id}>
                    {env.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Arrow */}
          <div className="flex items-center justify-center pt-6">
            <ArrowRight className="h-5 w-5 text-muted-foreground" />
          </div>

          {/* Target Environment */}
          <div className="flex-1 space-y-2">
            <label className="text-sm font-medium text-muted-foreground">
              Target Environment
            </label>
            <Select
              value={targetEnvId}
              onValueChange={handleTargetChange}
              disabled={!sourceEnvId}
            >
              <SelectTrigger data-testid="target-environment-select">
                <SelectValue placeholder={sourceEnvId ? "Select target..." : "Select source first"} />
              </SelectTrigger>
              <SelectContent>
                {targetOptions.map((env) => (
                  <SelectItem key={env.id} value={env.id}>
                    {env.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Visual Summary */}
        {isComplete && (
          <div className="flex items-center justify-center gap-3 p-4 rounded-lg bg-muted/50 border">
            <div className="text-sm font-medium">{sourceEnv?.name}</div>
            <ArrowRight className="h-4 w-4 text-muted-foreground" />
            <div className="text-sm font-medium">{targetEnv?.name}</div>
          </div>
        )}

        {/* Help text */}
        {!isComplete && (
          <div className="text-sm text-muted-foreground">
            {!sourceEnvId
              ? 'Select a source environment to begin'
              : 'Select a target environment to complete the pipeline configuration'
            }
          </div>
        )}
      </CardContent>
    </Card>
  );
}
