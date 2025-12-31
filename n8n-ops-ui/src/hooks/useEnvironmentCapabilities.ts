import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

export interface EnvironmentCapabilities {
  environmentId: string;
  environmentClass: string;
  capabilities: {
    syncStatus: boolean;
    backup: boolean;
    manualSnapshot: boolean;
    diffCompare: boolean;
    restoreRollback: boolean;
    editInN8N: boolean;
  };
  policyFlags: Record<string, boolean>;
}

/**
 * Hook to fetch environment action capabilities.
 * Returns which actions are allowed for an environment based on:
 * - Environment class (dev/staging/production)
 * - User role
 * - Organization policy flags
 * - Subscription plan
 */
export function useEnvironmentCapabilities(environmentId: string | undefined) {
  return useQuery<EnvironmentCapabilities>({
    queryKey: ['environment-capabilities', environmentId],
    queryFn: async () => {
      if (!environmentId) throw new Error('Environment ID is required');
      const response = await apiClient.getEnvironmentCapabilities(environmentId);
      return response.data;
    },
    enabled: !!environmentId,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });
}

