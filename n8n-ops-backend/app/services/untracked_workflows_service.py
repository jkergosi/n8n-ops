"""
Untracked Workflows Service - Detect and onboard workflows not tracked in the canonical system.

An untracked workflow is one that exists in an n8n environment but has no corresponding
mapping in workflow_env_map for (tenant_id, environment_id, n8n_workflow_id).

This service provides:
1. Scanning environments to detect untracked workflows
2. Onboarding untracked workflows into the canonical system
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import uuid4

from app.services.database import db_service
from app.services.provider_registry import ProviderRegistry
from app.services.canonical_workflow_service import (
    CanonicalWorkflowService,
    compute_workflow_hash
)
from app.schemas.untracked_workflow import (
    UntrackedWorkflowItem,
    EnvironmentUntrackedWorkflows,
    UntrackedWorkflowsResponse,
    OnboardResultItem,
    OnboardWorkflowsResponse,
    ScanEnvironmentResult,
    ScanEnvironmentsResponse,
)

logger = logging.getLogger(__name__)


class UntrackedWorkflowsService:
    """Service for detecting and onboarding untracked workflows."""

    @staticmethod
    async def get_untracked_workflows(tenant_id: str) -> UntrackedWorkflowsResponse:
        """
        Get all untracked workflows across all active environments.

        A workflow is untracked if it exists in n8n but has no mapping
        in workflow_env_map for (tenant_id, environment_id, n8n_workflow_id).

        Returns cached data from workflow_env_map where canonical_id is NULL.
        Call scan_environments() first to refresh the data.
        """
        try:
            # Get all active environments for tenant
            environments = await db_service.get_environments(tenant_id)

            result_environments: List[EnvironmentUntrackedWorkflows] = []
            total_untracked = 0

            for env in environments:
                environment_id = env.get("id")
                environment_name = env.get("name") or env.get("n8n_name") or "Unknown"
                environment_class = env.get("environment_class") or "dev"

                # Query workflow_env_map for untracked workflows (canonical_id IS NULL)
                untracked_result = db_service.client.table("workflow_env_map").select(
                    "n8n_workflow_id, workflow_data, last_env_sync_at"
                ).eq("tenant_id", tenant_id).eq("environment_id", environment_id).is_("canonical_id", "null").execute()

                untracked_workflows: List[UntrackedWorkflowItem] = []
                for row in (untracked_result.data or []):
                    workflow_data = row.get("workflow_data") or {}
                    untracked_workflows.append(UntrackedWorkflowItem(
                        n8n_workflow_id=row.get("n8n_workflow_id"),
                        name=workflow_data.get("name", "Unknown"),
                        active=workflow_data.get("active", False),
                        created_at=workflow_data.get("createdAt"),
                        updated_at=workflow_data.get("updatedAt")
                    ))

                if untracked_workflows:
                    result_environments.append(EnvironmentUntrackedWorkflows(
                        environment_id=environment_id,
                        environment_name=environment_name,
                        environment_class=environment_class,
                        untracked_workflows=untracked_workflows
                    ))
                    total_untracked += len(untracked_workflows)

            return UntrackedWorkflowsResponse(
                environments=result_environments,
                total_untracked=total_untracked
            )
        except Exception as e:
            logger.error(f"Failed to get untracked workflows: {str(e)}", exc_info=True)
            raise

    @staticmethod
    async def scan_environments(tenant_id: str) -> ScanEnvironmentsResponse:
        """
        Scan all active environments to refresh untracked workflow data.

        This performs a live scan of each n8n environment, diffs against
        workflow_env_map, and creates rows for any n8n workflows not yet mapped.

        Partial failure handling: Each environment is scanned independently.
        Failure in one environment does not affect others.
        """
        environments = await db_service.get_environments(tenant_id)

        results: List[ScanEnvironmentResult] = []
        environments_scanned = 0
        environments_failed = 0

        for env in environments:
            environment_id = env.get("id")
            environment_name = env.get("name") or env.get("n8n_name") or "Unknown"

            try:
                # Get adapter for this environment
                adapter = ProviderRegistry.get_adapter_for_environment(env)

                # Fetch all workflows from n8n
                n8n_workflows = await adapter.get_workflows()

                # Get existing mappings for this environment
                existing_result = db_service.client.table("workflow_env_map").select(
                    "n8n_workflow_id"
                ).eq("tenant_id", tenant_id).eq("environment_id", environment_id).not_.is_("n8n_workflow_id", "null").execute()

                existing_n8n_ids = {row.get("n8n_workflow_id") for row in (existing_result.data or [])}

                # Find workflows not in mappings
                new_untracked_count = 0
                for n8n_workflow in n8n_workflows:
                    n8n_workflow_id = str(n8n_workflow.get("id"))

                    if n8n_workflow_id not in existing_n8n_ids:
                        # Fetch full workflow data if needed
                        try:
                            full_workflow = await adapter.get_workflow(n8n_workflow_id)
                        except Exception:
                            full_workflow = n8n_workflow

                        # Compute content hash
                        env_content_hash = compute_workflow_hash(full_workflow)

                        # Insert new untracked workflow entry (canonical_id = NULL means untracked)
                        db_service.client.table("workflow_env_map").upsert({
                            "tenant_id": tenant_id,
                            "environment_id": environment_id,
                            "canonical_id": None,  # NULL = untracked
                            "n8n_workflow_id": n8n_workflow_id,
                            "env_content_hash": env_content_hash,
                            "workflow_data": full_workflow,
                            "last_env_sync_at": datetime.utcnow().isoformat(),
                            "n8n_updated_at": full_workflow.get("updatedAt")
                        }, on_conflict="tenant_id,environment_id,n8n_workflow_id").execute()

                        new_untracked_count += 1

                results.append(ScanEnvironmentResult(
                    environment_id=environment_id,
                    environment_name=environment_name,
                    status="success",
                    workflows_found=len(n8n_workflows)
                ))
                environments_scanned += 1

            except Exception as e:
                logger.warning(f"Failed to scan environment {environment_id}: {str(e)}", exc_info=True)
                results.append(ScanEnvironmentResult(
                    environment_id=environment_id,
                    environment_name=environment_name,
                    status="failed",
                    error=str(e)
                ))
                environments_failed += 1

        return ScanEnvironmentsResponse(
            environments_scanned=environments_scanned,
            environments_failed=environments_failed,
            results=results
        )

    @staticmethod
    async def onboard_workflows(
        tenant_id: str,
        workflows: List[Dict[str, str]],
        created_by_user_id: Optional[str] = None
    ) -> OnboardWorkflowsResponse:
        """
        Onboard selected untracked workflows into the canonical system.

        For each workflow:
        1. Check if mapping already exists → skip (idempotent)
        2. Create new canonical workflow record
        3. Create/update mapping in workflow_env_map with canonical_id and status='linked'

        Atomic per-workflow: Each workflow is processed independently.
        """
        results: List[OnboardResultItem] = []
        total_onboarded = 0
        total_skipped = 0
        total_failed = 0

        for workflow_item in workflows:
            environment_id = workflow_item.get("environment_id")
            n8n_workflow_id = workflow_item.get("n8n_workflow_id")

            try:
                # Check if mapping already exists with a canonical_id
                existing = db_service.client.table("workflow_env_map").select(
                    "canonical_id"
                ).eq("tenant_id", tenant_id).eq("environment_id", environment_id).eq("n8n_workflow_id", n8n_workflow_id).maybe_single().execute()

                if existing.data and existing.data.get("canonical_id"):
                    # Already mapped - skip (idempotent)
                    results.append(OnboardResultItem(
                        environment_id=environment_id,
                        n8n_workflow_id=n8n_workflow_id,
                        status="skipped",
                        canonical_workflow_id=existing.data.get("canonical_id"),
                        reason="Workflow already mapped to canonical system"
                    ))
                    total_skipped += 1
                    continue

                # Get workflow data from existing mapping (or fetch from n8n if needed)
                workflow_data = None
                if existing.data:
                    # Get full row to access workflow_data
                    full_row = db_service.client.table("workflow_env_map").select(
                        "workflow_data"
                    ).eq("tenant_id", tenant_id).eq("environment_id", environment_id).eq("n8n_workflow_id", n8n_workflow_id).maybe_single().execute()

                    if full_row.data:
                        workflow_data = full_row.data.get("workflow_data")

                # If no workflow_data, fetch from n8n
                if not workflow_data:
                    env = await db_service.get_environment(environment_id, tenant_id)
                    if env:
                        adapter = ProviderRegistry.get_adapter_for_environment(env)
                        workflow_data = await adapter.get_workflow(n8n_workflow_id)

                workflow_name = workflow_data.get("name", "Unknown") if workflow_data else "Unknown"

                # Atomic: Create canonical workflow and update mapping
                canonical_workflow = await db_service.create_canonical_workflow_with_mapping(
                    tenant_id=tenant_id,
                    environment_id=environment_id,
                    n8n_workflow_id=n8n_workflow_id,
                    display_name=workflow_name,
                    created_by_user_id=created_by_user_id,
                    workflow_data=workflow_data
                )

                results.append(OnboardResultItem(
                    environment_id=environment_id,
                    n8n_workflow_id=n8n_workflow_id,
                    status="onboarded",
                    canonical_workflow_id=canonical_workflow["canonical_id"]
                ))
                total_onboarded += 1

            except Exception as e:
                logger.error(f"Failed to onboard workflow {n8n_workflow_id} in env {environment_id}: {str(e)}", exc_info=True)
                results.append(OnboardResultItem(
                    environment_id=environment_id,
                    n8n_workflow_id=n8n_workflow_id,
                    status="failed",
                    reason=str(e)
                ))
                total_failed += 1

        return OnboardWorkflowsResponse(
            results=results,
            total_onboarded=total_onboarded,
            total_skipped=total_skipped,
            total_failed=total_failed
        )
