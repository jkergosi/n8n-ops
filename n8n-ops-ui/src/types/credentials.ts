import type { Provider } from "./index";

export interface LogicalCredential {
  id: string;
  tenantId?: string;
  name: string;
  description?: string;
  requiredType?: string;
  createdAt?: string;
}

export interface CredentialMapping {
  id: string;
  tenantId?: string;
  logicalCredentialId: string;
  environmentId: string;
  provider: Provider;
  physicalCredentialId: string;
  physicalName?: string;
  physicalType?: string;
  status?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface WorkflowCredentialDependency {
  workflowId: string;
  provider: Provider;
  logicalCredentialIds: string[];
  updatedAt?: string;
}

// Preflight validation types

export interface CredentialIssue {
  workflow_id: string;
  workflow_name: string;
  logical_credential_key: string;
  issue_type: 'missing_mapping' | 'mapped_missing_in_target' | 'no_logical_credential' | 'workflow_not_found';
  message: string;
  is_blocking: boolean;
}

export interface ResolvedMapping {
  logical_key: string;
  source_physical_name: string;
  target_physical_name: string;
  target_physical_id: string;
}

export interface CredentialPreflightResult {
  valid: boolean;
  blocking_issues: CredentialIssue[];
  warnings: CredentialIssue[];
  resolved_mappings: ResolvedMapping[];
}

export interface CredentialDetail {
  logical_key: string;
  credential_type: string;
  credential_name: string;
  is_mapped: boolean;
  mapping_status?: 'valid' | 'invalid' | 'missing';
  target_environments: string[];
}

export interface WorkflowCredentialDependencyResponse {
  workflow_id: string;
  provider: string;
  logical_credential_ids: string[];
  credentials: CredentialDetail[];
  updated_at?: string;
}

export interface DiscoveredCredentialWorkflow {
  id: string;
  name: string;
}

export interface DiscoveredCredential {
  type: string;
  name: string;
  logicalKey: string;
  workflowCount: number;
  workflows: DiscoveredCredentialWorkflow[];
  existingLogicalId?: string;
  mappingStatus: 'mapped' | 'unmapped' | 'partial';
}

export interface CredentialMatrixCell {
  mappingId?: string;
  physicalCredentialId?: string;
  physicalName?: string;
  physicalType?: string;
  status?: string;
}

export interface CredentialMatrixEnvironment {
  id: string;
  name: string;
  type: string;
}

export interface CredentialMatrixData {
  logicalCredentials: LogicalCredential[];
  environments: CredentialMatrixEnvironment[];
  matrix: Record<string, Record<string, CredentialMatrixCell | null>>;
}

export interface MappingIssue {
  mappingId: string;
  logicalName: string;
  environmentId: string;
  environmentName: string;
  issue: 'credential_not_found' | 'type_mismatch' | 'name_changed';
  message: string;
}

export interface MappingValidationReport {
  total: number;
  valid: number;
  invalid: number;
  stale: number;
  issues: MappingIssue[];
}

export interface N8NCredentialRef {
  id: string;
  name: string;
  type: string;
  createdAt?: string;
  updatedAt?: string;
}

