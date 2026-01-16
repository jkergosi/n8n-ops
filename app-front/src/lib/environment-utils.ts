import type { Environment, EnvironmentClass } from '@/types';

const CLASS_PRIORITY: Record<EnvironmentClass, number> = {
  dev: 0,
  staging: 1,
  production: 2,
};

function normalizeToEnvironmentClass(value: string | undefined): EnvironmentClass | undefined {
  if (!value) return undefined;
  const v = value.toLowerCase().trim();
  if (v === 'dev' || v === 'development') return 'dev';
  if (v === 'stage' || v === 'staging') return 'staging';
  if (v === 'prod' || v === 'production') return 'production';
  return undefined;
}

function getEnvironmentClass(env: Pick<Environment, 'environmentClass' | 'type'>): EnvironmentClass | undefined {
  return env.environmentClass || normalizeToEnvironmentClass(env.type);
}

export function sortEnvironments(environments: Environment[]): Environment[] {
  return [...environments].sort((a, b) => {
    const aClass = getEnvironmentClass(a);
    const bClass = getEnvironmentClass(b);
    const aPri = aClass ? CLASS_PRIORITY[aClass] : 999;
    const bPri = bClass ? CLASS_PRIORITY[bClass] : 999;

    if (aPri !== bPri) return aPri - bPri;

    const aName = (a.name || '').toLowerCase();
    const bName = (b.name || '').toLowerCase();
    if (aName !== bName) return aName.localeCompare(bName);

    return a.id.localeCompare(b.id);
  });
}

export function resolveEnvironment(
  environments: Environment[] | undefined,
  selected: string | undefined
): Environment | undefined {
  if (!environments || environments.length === 0 || !selected) return undefined;

  const byId = environments.find((e) => e.id === selected);
  if (byId) return byId;

  const selectedClass = normalizeToEnvironmentClass(selected);
  if (selectedClass) {
    const byClass = environments.find((e) => getEnvironmentClass(e) === selectedClass);
    if (byClass) return byClass;
  }

  const byType = environments.find((e) => e.type === selected);
  if (byType) return byType;

  return undefined;
}

export function getDefaultEnvironmentId(environments: Environment[] | undefined): string | undefined {
  if (!environments || environments.length === 0) return undefined;
  const sorted = sortEnvironments(environments);
  const devEnv = sorted.find((e) => getEnvironmentClass(e) === 'dev');
  return devEnv?.id || sorted[0]?.id;
}

export function getEnvironmentNameForSelection(
  environments: Environment[] | undefined,
  selected: string | undefined
): string | undefined {
  return resolveEnvironment(environments, selected)?.name;
}

/**
 * Badge variant type for consistent styling
 */
export type StateBadgeVariant = 'default' | 'secondary' | 'destructive' | 'outline';

/**
 * State badge status values
 */
export type StateBadgeStatus = 'in_sync' | 'pending_sync' | 'drift_detected' | 'new' | 'unknown' | 'error';

/**
 * State badge info returned by getStateBadgeInfo
 */
export interface StateBadgeInfo {
  status: StateBadgeStatus;
  label: string;
  variant: StateBadgeVariant;
  tooltip: string;
}

/**
 * Get environment state badge info based on drift status and environment class.
 *
 * DEV environments show "Pending Sync" instead of "Drift Detected" because
 * n8n is the source of truth for DEV - changes haven't been persisted to Git yet.
 *
 * Non-DEV environments (staging/prod) show "Drift Detected" because
 * Git is the source of truth - workflows in n8n differ from the canonical version.
 *
 * @param env - Environment object with driftStatus and environmentClass
 * @returns StateBadgeInfo with status, label, variant, and tooltip
 */
export function getStateBadgeInfo(env: Pick<Environment, 'driftStatus' | 'environmentClass'>): StateBadgeInfo {
  // Use case-insensitive comparison for drift_status
  const driftStatus = (env.driftStatus || 'UNKNOWN').toUpperCase();
  const isDev = env.environmentClass?.toLowerCase() === 'dev';

  switch (driftStatus) {
    case 'NEW':
      // Environment has no baseline - environment-level gate
      if (isDev) {
        return {
          status: 'new',
          label: 'No baseline',
          variant: 'outline',
          tooltip: 'No approved baseline exists. Save as Approved to create one.',
        };
      } else {
        return {
          status: 'new',
          label: 'Not onboarded',
          variant: 'outline',
          tooltip: 'No approved baseline exists. Promote from upstream to onboard.',
        };
      }
    case 'IN_SYNC':
      if (isDev) {
        return {
          status: 'in_sync',
          label: 'Matches baseline',
          variant: 'default',
          tooltip: 'Runtime matches the approved baseline.',
        };
      } else {
        return {
          status: 'in_sync',
          label: 'Matches approved',
          variant: 'default',
          tooltip: 'Runtime matches the approved version.',
        };
      }
    case 'DRIFT_DETECTED':
    case 'DRIFT_INCIDENT_ACTIVE':
      // DEV environments: n8n is source of truth, show "Different from baseline"
      // Non-DEV environments: Git is source of truth, show "Drift Detected"
      if (isDev) {
        return {
          status: 'pending_sync',
          label: 'Different from baseline',
          variant: 'secondary',
          tooltip: 'Runtime differs from baseline. Save as Approved to update.',
        };
      } else {
        return {
          status: 'drift_detected',
          label: 'Drift detected',
          variant: 'destructive',
          tooltip: 'Runtime differs from approved. Revert or Keep Hotfix.',
        };
      }
    case 'ERROR':
      return {
        status: 'error',
        label: 'Error',
        variant: 'secondary',
        tooltip: 'An error occurred while checking state.',
      };
    default:
      return {
        status: 'unknown',
        label: 'Unknown',
        variant: 'outline',
        tooltip: 'State has not been checked yet.',
      };
  }
}

