/**
 * Hook for computing workflow action policy.
 *
 * USE THIS at component level (valid React hook usage).
 * For event handlers, use getWorkflowActionPolicy() pure function instead.
 */

import { useMemo } from 'react';
import { useFeatures } from '@/lib/features';
import { useAuth } from '@/lib/auth';
import { getWorkflowActionPolicy } from '@/lib/workflow-action-policy';
import type { WorkflowActionPolicy } from '@/lib/workflow-action-policy';
import type { Environment, Workflow } from '@/types';

/**
 * Hook to get workflow action policy based on environment, plan, role, and workflow state.
 *
 * @param environment - The current environment
 * @param workflow - Optional workflow to check drift status
 * @returns The computed workflow action policy
 */
export function useWorkflowActionPolicy(
  environment: Environment | null,
  workflow?: Workflow
): WorkflowActionPolicy {
  const { planName } = useFeatures();
  const { user } = useAuth();

  return useMemo(() => {
    const hasDrift = workflow?.syncStatus === 'local_changes' ||
                     workflow?.syncStatus === 'conflict';

    return getWorkflowActionPolicy(
      environment,
      planName,
      (user as any)?.isPlatformAdmin ? 'platform_admin' : (user?.role || 'viewer'),
      hasDrift
    );
  }, [environment, planName, user?.role, (user as any)?.isPlatformAdmin, workflow?.syncStatus]);
}

/**
 * Hook to get the environment class with fallback logic.
 *
 * @param environment - The current environment
 * @returns The environment class ('dev' | 'staging' | 'production')
 */
export function useEnvironmentClass(environment: Environment | null): 'dev' | 'staging' | 'production' {
  return useMemo(() => {
    if (!environment) return 'dev';
    return environment.environmentClass || 'dev';
  }, [environment]);
}
