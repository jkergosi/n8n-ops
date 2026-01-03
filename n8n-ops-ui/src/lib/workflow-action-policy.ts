/**
 * Workflow Action Policy - Pure functions for determining workflow actions based on environment
 *
 * CRITICAL: Use getWorkflowActionPolicy() (pure function) inside event handlers.
 *           Use useWorkflowActionPolicy() (hook) only at component level.
 */

import type { Environment, EnvironmentClass } from '@/types';

export type DeleteMode = 'soft' | 'hard' | 'none';

export interface WorkflowActionPolicy {
  canViewDetails: boolean;
  canOpenInN8N: boolean;
  canCreateDeployment: boolean;
  canEditDirectly: boolean;
  canSoftDelete: boolean;        // Archive/hide workflow
  canHardDelete: boolean;        // Permanently remove (admin-only with confirmation)
  canCreateDriftIncident: boolean;
  driftIncidentRequired: boolean; // Agency+: must create incident to resolve drift
  editRequiresConfirmation: boolean;
  editRequiresAdmin: boolean;
}

/**
 * Legacy type inference - only used for migration from existing data without environmentClass.
 * DEPRECATED: Use environmentClass field directly.
 */
export function inferEnvironmentClass(legacyType?: string): EnvironmentClass {
  console.warn('inferEnvironmentClass: Legacy type field used. Migrate to environmentClass.');
  if (!legacyType) return 'dev'; // Safe default
  const normalized = legacyType.toLowerCase();

  if (normalized.includes('prod') || normalized === 'live') return 'production';
  if (normalized.includes('stag') || normalized === 'uat') return 'staging';
  return 'dev';
}

// Default action policy matrix
const DEFAULT_POLICY_MATRIX: Record<EnvironmentClass, WorkflowActionPolicy> = {
  dev: {
    canViewDetails: true,
    canOpenInN8N: true,
    canCreateDeployment: true,
    canEditDirectly: true,
    canSoftDelete: true,          // Default delete = soft (archive)
    canHardDelete: false,         // Hard delete requires explicit admin action
    canCreateDriftIncident: true, // Plan-gated below
    driftIncidentRequired: false, // Plan-gated below
    editRequiresConfirmation: true, // Warn about drift
    editRequiresAdmin: false,
  },
  staging: {
    canViewDetails: true,
    canOpenInN8N: true,
    canCreateDeployment: true,
    canEditDirectly: true,        // Admin-gated below
    canSoftDelete: false,         // Route to deployment
    canHardDelete: false,         // Never in staging
    canCreateDriftIncident: true,
    driftIncidentRequired: false, // Plan-gated below
    editRequiresConfirmation: true,
    editRequiresAdmin: true,      // Admin only
  },
  production: {
    canViewDetails: true,
    canOpenInN8N: true,
    canCreateDeployment: true,
    canEditDirectly: false,       // Never in production
    canSoftDelete: false,         // Never in production
    canHardDelete: false,         // Never in production
    canCreateDriftIncident: true,
    driftIncidentRequired: true,  // Always required in production
    editRequiresConfirmation: false, // N/A
    editRequiresAdmin: false,     // N/A
  },
};

/**
 * Pure function to compute workflow action policy.
 * USE THIS inside event handlers (not hooks).
 *
 * @param environment - The current environment (or null)
 * @param planName - The tenant's subscription plan
 * @param userRole - The user's role
 * @param hasDrift - Whether the workflow has drift
 * @returns The computed policy
 */
export function getWorkflowActionPolicy(
  environment: Environment | null,
  planName: string,
  userRole: string,
  hasDrift: boolean
): WorkflowActionPolicy {
  // Use environmentClass if available, otherwise infer from legacy type field
  const envClass: EnvironmentClass = environment?.environmentClass ||
    inferEnvironmentClass(environment?.type);

  const basePolicy = { ...DEFAULT_POLICY_MATRIX[envClass] };
  const planTier = planName.toLowerCase();
  const isAgencyPlus = planTier === 'agency' || planTier === 'agency_plus' || planTier === 'enterprise';
  const isAdmin = userRole === 'admin' || userRole === 'platform_admin' || userRole === 'superuser' || userRole === 'super_admin';

  // =============================================
  // PLAN-BASED RESTRICTIONS
  // =============================================

  // Free tier: No drift incident workflow at all
  if (planTier === 'free') {
    basePolicy.canCreateDriftIncident = false;
    basePolicy.driftIncidentRequired = false;
  }

  // Pro tier: Drift incidents optional (not required)
  if (planTier === 'pro') {
    basePolicy.driftIncidentRequired = false;
  }

  // Agency+: Drift incidents required by default in staging/production
  if (isAgencyPlus) {
    if (envClass === 'staging') {
      basePolicy.canEditDirectly = false; // Even stricter for agency+
      basePolicy.driftIncidentRequired = true;
    }
    // Production already has driftIncidentRequired = true
  }

  // =============================================
  // ROLE-BASED RESTRICTIONS
  // =============================================

  // Admin-gated actions
  if (basePolicy.editRequiresAdmin && !isAdmin) {
    basePolicy.canEditDirectly = false;
  }

  // Hard delete: Admin-only in dev, never elsewhere
  if (envClass === 'dev' && isAdmin) {
    basePolicy.canHardDelete = true; // Unlocks "Permanently delete" option
  }

  // =============================================
  // DRIFT STATE RESTRICTIONS
  // =============================================

  // Drift incident only if drift exists
  if (!hasDrift) {
    basePolicy.canCreateDriftIncident = false;
    basePolicy.driftIncidentRequired = false;
  }

  return basePolicy;
}
