import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { EnvironmentTypeConfig } from '@/types';

const DEFAULT_ENVIRONMENT_TYPES: EnvironmentTypeConfig[] = [
  { id: 'dev', tenantId: 'local', key: 'dev', label: 'Development', sortOrder: 10, isActive: true },
  { id: 'staging', tenantId: 'local', key: 'staging', label: 'Staging', sortOrder: 20, isActive: true },
  { id: 'production', tenantId: 'local', key: 'production', label: 'Production', sortOrder: 30, isActive: true },
];

export function useEnvironmentTypes(options?: { activeOnly?: boolean }) {
  const { activeOnly = true } = options || {};

  const query = useQuery({
    queryKey: ['environment-types'],
    queryFn: () => apiClient.getEnvironmentTypes(),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    retry: 1,
  });

  const allTypes = query.data?.data || [];
  const hasData = allTypes.length > 0;

  // Use API data if available, otherwise fallback to defaults
  const environmentTypes = hasData
    ? (activeOnly ? allTypes.filter((t) => t.isActive) : allTypes)
    : DEFAULT_ENVIRONMENT_TYPES;

  // Sort by sortOrder
  const sortedTypes = [...environmentTypes].sort((a, b) => (a.sortOrder ?? 0) - (b.sortOrder ?? 0));

  return {
    environmentTypes: sortedTypes,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    isUsingDefaults: !hasData,
    refetch: query.refetch,
  };
}

export function getEnvironmentTypeLabel(
  types: EnvironmentTypeConfig[],
  key: string | undefined
): string {
  if (!key) return 'Unknown';
  const type = types.find((t) => t.key === key);
  return type?.label || key;
}

export function getEnvironmentTypeSortOrder(
  types: EnvironmentTypeConfig[],
  key: string | undefined
): number {
  if (!key) return 999;
  const type = types.find((t) => t.key === key);
  return type?.sortOrder ?? 999;
}
