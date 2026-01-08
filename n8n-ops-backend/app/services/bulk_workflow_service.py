"""
Bulk Workflow Service - Execute operations across multiple workflows

This service handles bulk operations (sync, promote, snapshot) across multiple workflows.
Operations are processed sequentially with per-workflow error tracking and progress updates.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.services.database import db_service
from app.services.background_job_service import (
    background_job_service,
    BackgroundJobStatus
)
from app.services.canonical_env_sync_service import CanonicalEnvSyncService
from app.schemas.bulk_operations import BulkOperationResult
from app.core.config import settings

logger = logging.getLogger(__name__)

# Maximum number of workflows allowed in a single bulk operation
MAX_BULK_WORKFLOWS = settings.MAX_BULK_WORKFLOWS


class BulkWorkflowService:
    """Service for executing bulk workflow operations"""

    @staticmethod
    def _create_workflow_result(workflow_id: str, success: bool = False, error_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a per-workflow result entry for error tracking.

        Args:
            workflow_id: The workflow ID being processed
            success: Whether the operation succeeded
            error_message: Error details if operation failed

        Returns:
            Dictionary with workflow_id, success, and error_message
        """
        return {
            "workflow_id": workflow_id,
            "success": success,
            "error_message": error_message
        }

    @staticmethod
    def _aggregate_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate per-workflow results into summary statistics.

        Args:
            results: List of per-workflow result dictionaries

        Returns:
            Dictionary containing:
                - total: Total number of workflows
                - succeeded: Number of successful operations
                - failed: Number of failed operations
                - errors: List of error messages from failed workflows
        """
        total = len(results)
        succeeded = sum(1 for r in results if r.get("success"))
        failed = total - succeeded
        errors = [r["error_message"] for r in results if not r.get("success") and r.get("error_message")]

        return {
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
            "errors": errors
        }

    @staticmethod
    async def _update_job_progress(
        job_id: str,
        current: int,
        total: int,
        succeeded: int,
        failed: int,
        results: List[Dict[str, Any]],
        operation_name: str,
        status: BackgroundJobStatus = BackgroundJobStatus.RUNNING,
        current_workflow_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> None:
        """
        Update background job with current progress and results.

        Args:
            job_id: Background job ID
            current: Number of workflows processed so far
            total: Total number of workflows
            succeeded: Number of successful operations
            failed: Number of failed operations
            results: List of per-workflow results
            operation_name: Name of the operation (e.g., "sync", "promote", "snapshot")
            status: Job status (default: RUNNING)
            current_workflow_id: ID of workflow currently being processed (for SSE)
            tenant_id: Tenant ID for SSE event routing (optional)
        """
        percentage = int((current / total) * 100) if total > 0 else 0
        message = f"{operation_name.capitalize()}ed {current}/{total} workflow(s) ({succeeded} succeeded, {failed} failed)"

        await background_job_service.update_job_status(
            job_id=job_id,
            status=status,
            progress={
                "current": current,
                "total": total,
                "percentage": percentage,
                "succeeded": succeeded,
                "failed": failed,
                "message": message
            },
            result={
                "results": results,
                "completed": current,
                "succeeded": succeeded,
                "failed": failed
            }
        )

        # Emit SSE progress event if tenant_id is provided
        if tenant_id:
            try:
                from app.api.endpoints.sse import emit_bulk_operation_progress

                # Determine status string for SSE
                sse_status = "running" if status == BackgroundJobStatus.RUNNING else (
                    "completed" if status == BackgroundJobStatus.COMPLETED else "failed"
                )

                await emit_bulk_operation_progress(
                    job_id=job_id,
                    operation_type=operation_name,
                    status=sse_status,
                    current=current,
                    total=total,
                    succeeded=succeeded,
                    failed=failed,
                    current_workflow_id=current_workflow_id,
                    message=message,
                    percentage=percentage,
                    tenant_id=tenant_id
                )
                logger.debug(f"Emitted SSE progress for {operation_name}: {current}/{total}")
            except Exception as e:
                # Don't fail the operation if SSE emission fails
                logger.warning(f"Failed to emit SSE progress event: {str(e)}")

    @staticmethod
    async def _finalize_job(
        job_id: str,
        total: int,
        succeeded: int,
        failed: int,
        results: List[Dict[str, Any]],
        operation_name: str,
        tenant_id: Optional[str] = None
    ) -> None:
        """
        Mark a bulk operation job as completed with final results.

        Args:
            job_id: Background job ID
            total: Total number of workflows
            succeeded: Number of successful operations
            failed: Number of failed operations
            results: List of per-workflow results
            operation_name: Name of the operation (e.g., "sync", "promote", "snapshot")
            tenant_id: Tenant ID for SSE event routing (optional)
        """
        final_message = f"Bulk {operation_name} completed: {succeeded} succeeded, {failed} failed out of {total} workflow(s)"

        await background_job_service.update_job_status(
            job_id=job_id,
            status=BackgroundJobStatus.COMPLETED,
            progress={
                "current": total,
                "total": total,
                "percentage": 100,
                "succeeded": succeeded,
                "failed": failed,
                "message": final_message
            },
            result={
                "total": total,
                "succeeded": succeeded,
                "failed": failed,
                "results": results,
                "completed": total,
                "completed_at": datetime.utcnow().isoformat()
            }
        )

        logger.info(final_message)

        # Emit final SSE progress event if tenant_id is provided
        if tenant_id:
            try:
                from app.api.endpoints.sse import emit_bulk_operation_progress

                await emit_bulk_operation_progress(
                    job_id=job_id,
                    operation_type=operation_name,
                    status="completed",
                    current=total,
                    total=total,
                    succeeded=succeeded,
                    failed=failed,
                    current_workflow_id=None,
                    message=final_message,
                    percentage=100,
                    tenant_id=tenant_id
                )
                logger.debug(f"Emitted final SSE completion event for {operation_name}")
            except Exception as e:
                # Don't fail the operation if SSE emission fails
                logger.warning(f"Failed to emit SSE completion event: {str(e)}")

    @staticmethod
    async def _handle_catastrophic_failure(
        job_id: str,
        error: Exception,
        total: int,
        succeeded: int,
        failed: int,
        results: List[Dict[str, Any]],
        operation_name: str,
        tenant_id: Optional[str] = None
    ) -> None:
        """
        Handle catastrophic failure during bulk operation.

        Args:
            job_id: Background job ID
            error: The exception that caused the failure
            total: Total number of workflows
            succeeded: Number of successful operations before failure
            failed: Number of failed operations before failure
            results: List of per-workflow results before failure
            operation_name: Name of the operation (e.g., "sync", "promote", "snapshot")
            tenant_id: Tenant ID for SSE event routing (optional)
        """
        error_msg = f"Bulk {operation_name} operation failed: {str(error)}"
        logger.error(error_msg, exc_info=True)

        await background_job_service.update_job_status(
            job_id=job_id,
            status=BackgroundJobStatus.FAILED,
            error_message=error_msg,
            result={
                "total": total,
                "succeeded": succeeded,
                "failed": failed,
                "results": results,
                "completed": len(results)
            }
        )

        # Emit SSE failure event if tenant_id is provided
        if tenant_id:
            try:
                from app.api.endpoints.sse import emit_bulk_operation_progress

                await emit_bulk_operation_progress(
                    job_id=job_id,
                    operation_type=operation_name,
                    status="failed",
                    current=len(results),
                    total=total,
                    succeeded=succeeded,
                    failed=failed,
                    current_workflow_id=None,
                    message=error_msg,
                    percentage=int((len(results) / total) * 100) if total > 0 else 0,
                    tenant_id=tenant_id
                )
                logger.debug(f"Emitted SSE failure event for {operation_name}")
            except Exception as e:
                # Don't fail the operation if SSE emission fails
                logger.warning(f"Failed to emit SSE failure event: {str(e)}")

    @staticmethod
    async def execute_bulk_sync(
        tenant_id: str,
        workflow_ids: List[str],
        environment_id: str,
        job_id: str,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute bulk sync operation on multiple workflows.

        Syncs workflows sequentially from their n8n environment to the database.
        Each workflow is synced independently with per-workflow error tracking.

        Args:
            tenant_id: Tenant ID
            workflow_ids: List of workflow IDs to sync (max MAX_BULK_WORKFLOWS)
            environment_id: Environment ID to sync from
            job_id: Background job ID for progress tracking
            created_by: User ID who initiated the operation

        Returns:
            Dictionary containing:
                - total: Total number of workflows
                - succeeded: Number of successful syncs
                - failed: Number of failed syncs
                - results: List of BulkOperationResult for each workflow
                - errors: List of error messages
        """
        logger.info(
            f"Starting bulk sync for {len(workflow_ids)} workflows in environment "
            f"{environment_id} for tenant {tenant_id}"
        )

        # Validate batch size
        if len(workflow_ids) > MAX_BULK_WORKFLOWS:
            error_msg = f"Exceeded maximum batch size of {MAX_BULK_WORKFLOWS} workflows"
            logger.error(error_msg)
            await background_job_service.update_job_status(
                job_id=job_id,
                status=BackgroundJobStatus.FAILED,
                error_message=error_msg
            )
            raise ValueError(error_msg)

        # Initialize results tracking
        results: List[Dict[str, Any]] = []
        succeeded = 0
        failed = 0
        total = len(workflow_ids)

        # Update job status to running
        await background_job_service.update_job_status(
            job_id=job_id,
            status=BackgroundJobStatus.RUNNING,
            progress={
                "current": 0,
                "total": total,
                "percentage": 0,
                "message": f"Starting bulk sync of {total} workflow(s)..."
            }
        )

        try:
            # Fetch environment details
            environment = await db_service.get_environment(environment_id, tenant_id)
            if not environment:
                error_msg = f"Environment {environment_id} not found"
                logger.error(error_msg)
                await background_job_service.update_job_status(
                    job_id=job_id,
                    status=BackgroundJobStatus.FAILED,
                    error_message=error_msg
                )
                raise ValueError(error_msg)

            # Process each workflow sequentially
            for index, workflow_id in enumerate(workflow_ids, start=1):
                workflow_result = BulkWorkflowService._create_workflow_result(workflow_id)

                try:
                    logger.info(
                        f"Syncing workflow {workflow_id} ({index}/{total}) in "
                        f"environment {environment_id}"
                    )

                    # Fetch workflow mapping to get the canonical_id
                    mapping = await db_service.client.table("workflow_mappings").select(
                        "canonical_id, environment_n8n_id"
                    ).eq(
                        "tenant_id", tenant_id
                    ).eq(
                        "environment_id", environment_id
                    ).eq(
                        "canonical_id", workflow_id
                    ).maybe_single().execute()

                    if not mapping or not mapping.data:
                        # Workflow not found in this environment
                        error_msg = f"Workflow {workflow_id} not found in environment {environment_id}"
                        logger.warning(error_msg)
                        workflow_result["error_message"] = error_msg
                        failed += 1
                    else:
                        # Sync the entire environment (this will sync all workflows including this one)
                        # Note: The spec says to sync individual workflows, but the existing
                        # sync_environment method is designed to sync the entire environment.
                        # For MVP, we'll sync the environment which will include this workflow.
                        # A future optimization could add single-workflow sync capability.
                        sync_result = await CanonicalEnvSyncService.sync_environment(
                            tenant_id=tenant_id,
                            environment_id=environment_id,
                            environment=environment,
                            job_id=None,  # Don't pass job_id to avoid nested progress updates
                            checkpoint=None,
                            tenant_id_for_sse=None  # No SSE for individual syncs in bulk
                        )

                        # Check if sync was successful
                        if sync_result.get("workflows_synced", 0) > 0 or sync_result.get("workflows_skipped", 0) > 0:
                            workflow_result["success"] = True
                            succeeded += 1
                            logger.info(f"Successfully synced workflow {workflow_id}")
                        else:
                            # Check for errors
                            errors = sync_result.get("errors", [])
                            if errors:
                                error_msg = "; ".join(str(e) for e in errors[:3])  # First 3 errors
                                workflow_result["error_message"] = error_msg
                            else:
                                workflow_result["error_message"] = "Sync completed but no workflows were synced"
                            failed += 1
                            logger.warning(f"Failed to sync workflow {workflow_id}: {workflow_result['error_message']}")

                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Error syncing workflow {workflow_id}: {error_msg}", exc_info=True)
                    workflow_result["error_message"] = error_msg
                    failed += 1

                # Add result to list
                results.append(workflow_result)

                # Update job progress after each workflow
                await BulkWorkflowService._update_job_progress(
                    job_id=job_id,
                    current=index,
                    total=total,
                    succeeded=succeeded,
                    failed=failed,
                    results=results,
                    operation_name="sync",
                    current_workflow_id=workflow_id,
                    tenant_id=tenant_id
                )

            # Mark job as completed
            await BulkWorkflowService._finalize_job(
                job_id=job_id,
                total=total,
                succeeded=succeeded,
                failed=failed,
                results=results,
                operation_name="sync",
                tenant_id=tenant_id
            )

            # Return aggregated results
            aggregated = BulkWorkflowService._aggregate_results(results)
            return {
                **aggregated,
                "results": results
            }

        except Exception as e:
            # Handle catastrophic failure
            await BulkWorkflowService._handle_catastrophic_failure(
                job_id=job_id,
                error=e,
                total=total,
                succeeded=succeeded,
                failed=failed,
                results=results,
                operation_name="sync",
                tenant_id=tenant_id
            )

            raise

    @staticmethod
    async def execute_bulk_promote(
        tenant_id: str,
        workflow_ids: List[str],
        source_environment_id: str,
        target_environment_id: str,
        job_id: str,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute bulk promote operation on multiple workflows.

        Promotes workflows sequentially from source environment to target environment.
        Each workflow is promoted independently with per-workflow error tracking.

        Note: Uses a single source/target environment pair for all workflows in the batch.

        Args:
            tenant_id: Tenant ID
            workflow_ids: List of workflow IDs to promote (max MAX_BULK_WORKFLOWS)
            source_environment_id: Source environment ID to promote from
            target_environment_id: Target environment ID to promote to
            job_id: Background job ID for progress tracking
            created_by: User ID who initiated the operation

        Returns:
            Dictionary containing:
                - total: Total number of workflows
                - succeeded: Number of successful promotions
                - failed: Number of failed promotions
                - results: List of BulkOperationResult for each workflow
                - errors: List of error messages
        """
        logger.info(
            f"Starting bulk promote for {len(workflow_ids)} workflows from "
            f"environment {source_environment_id} to {target_environment_id} "
            f"for tenant {tenant_id}"
        )

        # Validate batch size
        if len(workflow_ids) > MAX_BULK_WORKFLOWS:
            error_msg = f"Exceeded maximum batch size of {MAX_BULK_WORKFLOWS} workflows"
            logger.error(error_msg)
            await background_job_service.update_job_status(
                job_id=job_id,
                status=BackgroundJobStatus.FAILED,
                error_message=error_msg
            )
            raise ValueError(error_msg)

        # Initialize results tracking
        results: List[Dict[str, Any]] = []
        succeeded = 0
        failed = 0
        total = len(workflow_ids)

        # Update job status to running
        await background_job_service.update_job_status(
            job_id=job_id,
            status=BackgroundJobStatus.RUNNING,
            progress={
                "current": 0,
                "total": total,
                "percentage": 0,
                "message": f"Starting bulk promote of {total} workflow(s)..."
            }
        )

        try:
            # Fetch environment details
            source_env = await db_service.get_environment(source_environment_id, tenant_id)
            target_env = await db_service.get_environment(target_environment_id, tenant_id)

            if not source_env:
                error_msg = f"Source environment {source_environment_id} not found"
                logger.error(error_msg)
                await background_job_service.update_job_status(
                    job_id=job_id,
                    status=BackgroundJobStatus.FAILED,
                    error_message=error_msg
                )
                raise ValueError(error_msg)

            if not target_env:
                error_msg = f"Target environment {target_environment_id} not found"
                logger.error(error_msg)
                await background_job_service.update_job_status(
                    job_id=job_id,
                    status=BackgroundJobStatus.FAILED,
                    error_message=error_msg
                )
                raise ValueError(error_msg)

            # Import required services for promotion
            from app.services.promotion_service import promotion_service
            from app.services.provider_registry import ProviderRegistry
            from app.services.github_service import GitHubService

            # Create provider adapters
            source_adapter = ProviderRegistry.get_adapter_for_environment(source_env)
            target_adapter = ProviderRegistry.get_adapter_for_environment(target_env)

            # Get GitHub service for source environment
            source_git_folder = source_env.get("git_folder")
            if not source_git_folder:
                error_msg = "Git folder is required for canonical workflow promotions"
                logger.error(error_msg)
                await background_job_service.update_job_status(
                    job_id=job_id,
                    status=BackgroundJobStatus.FAILED,
                    error_message=error_msg
                )
                raise ValueError(error_msg)

            # Get GitHub service
            repo_url = source_env.get("git_repo_url", "").rstrip('/').replace('.git', '')
            repo_parts = repo_url.split("/")
            source_github = GitHubService(
                token=source_env.get("git_pat"),
                repo_owner=repo_parts[-2] if len(repo_parts) >= 2 else "",
                repo_name=repo_parts[-1] if len(repo_parts) >= 1 else "",
                branch=source_env.get("git_branch", "main")
            )

            # Load workflows from Git
            from app.services.canonical_workflow_service import CanonicalWorkflowService, compute_workflow_hash

            # Get all canonical workflows for this tenant
            canonical_workflows = await CanonicalWorkflowService.list_canonical_workflows(tenant_id)

            # Build a map of workflow_id to workflow data from Git
            source_workflow_map = {}
            canonical_id_map = {}  # Map workflow_id -> canonical_id

            for canonical in canonical_workflows:
                canonical_id = canonical["canonical_id"]

                # Get Git state for source environment
                git_state = await CanonicalWorkflowService.get_canonical_workflow_git_state(
                    tenant_id, source_environment_id, canonical_id
                )

                if not git_state:
                    continue

                # Load workflow from Git
                workflow_data = await source_github.get_file_content(
                    git_state["git_path"],
                    git_state.get("git_commit_sha") or source_env.get("git_branch", "main")
                )

                if workflow_data:
                    # Remove metadata
                    workflow_data.pop("_comment", None)

                    # Get mapping to find n8n_workflow_id
                    mappings = await db_service.get_workflow_mappings(
                        tenant_id=tenant_id,
                        environment_id=source_environment_id,
                        canonical_id=canonical_id
                    )

                    # Store workflow data with both n8n ID and canonical ID
                    if mappings and mappings[0].get("n8n_workflow_id"):
                        n8n_id = mappings[0]["n8n_workflow_id"]
                        source_workflow_map[n8n_id] = workflow_data
                        canonical_id_map[n8n_id] = canonical_id
                    else:
                        # Fallback: use canonical_id as key
                        source_workflow_map[canonical_id] = workflow_data
                        canonical_id_map[canonical_id] = canonical_id

            # Preload logical credentials and mappings for credential rewrite
            logical_creds = await db_service.list_logical_credentials(tenant_id)
            logical_name_by_id = {lc.get("id"): lc.get("name") for lc in (logical_creds or [])}

            target_provider = target_env.get("provider", "n8n") if isinstance(target_env, dict) else "n8n"
            target_mappings = await db_service.list_credential_mappings(
                tenant_id=tenant_id,
                environment_id=target_environment_id,
                provider=target_provider
            )
            mapping_lookup = {}
            for m in target_mappings:
                logical_name = logical_name_by_id.get(m.get("logical_credential_id"))
                if not logical_name:
                    continue
                mapping_lookup[logical_name] = m

            # Process each workflow sequentially
            for index, workflow_id in enumerate(workflow_ids, start=1):
                workflow_result = BulkWorkflowService._create_workflow_result(workflow_id)

                try:
                    logger.info(
                        f"Promoting workflow {workflow_id} ({index}/{total}) from "
                        f"{source_environment_id} to {target_environment_id}"
                    )

                    # Get workflow data from source
                    workflow_data = source_workflow_map.get(workflow_id)
                    if not workflow_data:
                        error_msg = f"Workflow {workflow_id} not found in source environment or Git"
                        logger.warning(error_msg)
                        workflow_result["error_message"] = error_msg
                        failed += 1
                    else:
                        # Get canonical_id for this workflow
                        canonical_id = canonical_id_map.get(workflow_id)

                        # Create a copy of workflow data to avoid modifying the original
                        import json
                        promote_workflow_data = json.loads(json.dumps(workflow_data))

                        # Rewrite credential references using mappings
                        if mapping_lookup:
                            try:
                                from app.services.adapters.n8n_adapter import N8NProviderAdapter
                                promote_workflow_data = N8NProviderAdapter.rewrite_credentials_with_mappings(
                                    promote_workflow_data,
                                    mapping_lookup,
                                )
                                logger.info(f"Rewrote credential references for workflow {workflow_id}")
                            except Exception as e:
                                logger.error(f"Failed to rewrite credentials for {workflow_id}: {e}")
                                workflow_result["error_message"] = f"Credential rewrite failed: {str(e)}"
                                failed += 1
                                results.append(workflow_result)
                                continue

                        # Try to promote workflow to target
                        workflow_n8n_id = promote_workflow_data.get("id")

                        # Check if workflow exists in target
                        try:
                            existing_workflow = await target_adapter.get_workflow(workflow_n8n_id)
                            # Update existing workflow
                            await target_adapter.update_workflow(workflow_n8n_id, promote_workflow_data)
                            logger.info(f"Updated existing workflow {workflow_id} in target")
                        except Exception as e:
                            # Workflow doesn't exist, create new one
                            error_str = str(e).lower()
                            if '404' in error_str or '400' in error_str or 'not found' in error_str:
                                logger.info(f"Workflow {workflow_id} not found in target, creating new")
                                await target_adapter.create_workflow(promote_workflow_data)
                                logger.info(f"Created new workflow {workflow_id} in target")
                            else:
                                # Re-raise if it's a different error
                                raise

                        # Update workflow mapping for target environment
                        if canonical_id:
                            try:
                                # Get target workflow to get its n8n ID
                                target_workflow = await target_adapter.get_workflow(workflow_n8n_id)
                                target_n8n_id = target_workflow.get("id") if target_workflow else workflow_n8n_id

                                # Compute content hash
                                content_hash = compute_workflow_hash(promote_workflow_data)

                                # Create or update mapping
                                from app.services.canonical_env_sync_service import CanonicalEnvSyncService
                                from app.schemas.canonical_workflow import WorkflowMappingStatus
                                await CanonicalEnvSyncService._create_workflow_mapping(
                                    tenant_id=tenant_id,
                                    environment_id=target_environment_id,
                                    canonical_id=canonical_id,
                                    n8n_workflow_id=target_n8n_id,
                                    content_hash=content_hash,
                                    status=WorkflowMappingStatus.LINKED,
                                    linked_by_user_id=created_by
                                )

                                # Update sidecar file in Git
                                target_git_folder = target_env.get("git_folder")
                                if target_git_folder:
                                    target_github = GitHubService(
                                        token=target_env.get("git_pat"),
                                        repo_owner=repo_parts[-2] if len(repo_parts) >= 2 else "",
                                        repo_name=repo_parts[-1] if len(repo_parts) >= 1 else "",
                                        branch=target_env.get("git_branch", "main")
                                    )

                                    git_state = await CanonicalWorkflowService.get_canonical_workflow_git_state(
                                        tenant_id, target_environment_id, canonical_id
                                    )

                                    if git_state:
                                        sidecar_path = git_state["git_path"].replace('.json', '.env-map.json')

                                        # Get existing sidecar or create new
                                        sidecar_data = await target_github.get_file_content(sidecar_path) or {
                                            "canonical_workflow_id": canonical_id,
                                            "workflow_name": promote_workflow_data.get("name", "Unknown"),
                                            "environments": {}
                                        }

                                        # Update target environment mapping
                                        if "environments" not in sidecar_data:
                                            sidecar_data["environments"] = {}

                                        sidecar_data["environments"][target_environment_id] = {
                                            "n8n_workflow_id": target_n8n_id,
                                            "content_hash": f"sha256:{content_hash}",
                                            "last_seen_at": datetime.utcnow().isoformat()
                                        }

                                        # Write sidecar file
                                        await target_github.write_sidecar_file(
                                            canonical_id=canonical_id,
                                            sidecar_data=sidecar_data,
                                            git_folder=target_git_folder,
                                            commit_message=f"Update sidecar after bulk promotion: {promote_workflow_data.get('name', 'Unknown')}"
                                        )
                                        
                                        # Update canonical_workflow_git_state for target environment
                                        git_path = git_state.get("git_path") or f"workflows/{target_git_folder}/{canonical_id}.json"
                                        db_service.client.table("canonical_workflow_git_state").upsert({
                                            "tenant_id": tenant_id,
                                            "environment_id": target_environment_id,
                                            "canonical_id": canonical_id,
                                            "git_path": git_path,
                                            "git_content_hash": content_hash,
                                            "last_repo_sync_at": datetime.utcnow().isoformat()
                                        }, on_conflict="tenant_id,environment_id,canonical_id").execute()
                                        logger.info(f"Updated git_state for {canonical_id} in target env {target_environment_id}")
                                    else:
                                        # No existing git_state - create new one
                                        git_path = f"workflows/{target_git_folder}/{canonical_id}.json"
                                        db_service.client.table("canonical_workflow_git_state").upsert({
                                            "tenant_id": tenant_id,
                                            "environment_id": target_environment_id,
                                            "canonical_id": canonical_id,
                                            "git_path": git_path,
                                            "git_content_hash": content_hash,
                                            "last_repo_sync_at": datetime.utcnow().isoformat()
                                        }, on_conflict="tenant_id,environment_id,canonical_id").execute()
                                        logger.info(f"Created git_state for {canonical_id} in target env {target_environment_id}")
                            except Exception as e:
                                logger.warning(f"Failed to update mapping/sidecar/git_state for {workflow_id}: {str(e)}")
                                # Don't fail promotion if mapping/git_state update fails

                        workflow_result["success"] = True
                        succeeded += 1
                        logger.info(f"Successfully promoted workflow {workflow_id}")

                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Error promoting workflow {workflow_id}: {error_msg}", exc_info=True)
                    workflow_result["error_message"] = error_msg
                    failed += 1

                # Add result to list
                results.append(workflow_result)

                # Update job progress after each workflow
                await BulkWorkflowService._update_job_progress(
                    job_id=job_id,
                    current=index,
                    total=total,
                    succeeded=succeeded,
                    failed=failed,
                    results=results,
                    operation_name="promote",
                    current_workflow_id=workflow_id,
                    tenant_id=tenant_id
                )

            # Mark job as completed
            await BulkWorkflowService._finalize_job(
                job_id=job_id,
                total=total,
                succeeded=succeeded,
                failed=failed,
                results=results,
                operation_name="promote",
                tenant_id=tenant_id
            )

            # Return aggregated results
            aggregated = BulkWorkflowService._aggregate_results(results)
            return {
                **aggregated,
                "results": results
            }

        except Exception as e:
            # Handle catastrophic failure
            await BulkWorkflowService._handle_catastrophic_failure(
                job_id=job_id,
                error=e,
                total=total,
                succeeded=succeeded,
                failed=failed,
                results=results,
                operation_name="promote",
                tenant_id=tenant_id
            )

            raise

    @staticmethod
    async def execute_bulk_snapshot(
        tenant_id: str,
        workflow_ids: List[str],
        environment_id: str,
        job_id: str,
        created_by: Optional[str] = None,
        reason: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute bulk snapshot operation on multiple workflows.

        Creates one snapshot per workflow. Each workflow is exported to Git
        independently with per-workflow error tracking.

        Args:
            tenant_id: Tenant ID
            workflow_ids: List of workflow IDs to snapshot (max MAX_BULK_WORKFLOWS)
            environment_id: Environment ID to snapshot from
            job_id: Background job ID for progress tracking
            created_by: User ID who initiated the operation
            reason: Optional reason for the snapshots
            notes: Optional notes for the snapshots

        Returns:
            Dictionary containing:
                - total: Total number of workflows
                - succeeded: Number of successful snapshots
                - failed: Number of failed snapshots
                - results: List of BulkOperationResult for each workflow
                - errors: List of error messages
        """
        logger.info(
            f"Starting bulk snapshot for {len(workflow_ids)} workflows in environment "
            f"{environment_id} for tenant {tenant_id}"
        )

        # Validate batch size
        if len(workflow_ids) > MAX_BULK_WORKFLOWS:
            error_msg = f"Exceeded maximum batch size of {MAX_BULK_WORKFLOWS} workflows"
            logger.error(error_msg)
            await background_job_service.update_job_status(
                job_id=job_id,
                status=BackgroundJobStatus.FAILED,
                error_message=error_msg
            )
            raise ValueError(error_msg)

        # Initialize results tracking
        results: List[Dict[str, Any]] = []
        succeeded = 0
        failed = 0
        total = len(workflow_ids)

        # Update job status to running
        await background_job_service.update_job_status(
            job_id=job_id,
            status=BackgroundJobStatus.RUNNING,
            progress={
                "current": 0,
                "total": total,
                "percentage": 0,
                "message": f"Starting bulk snapshot of {total} workflow(s)..."
            }
        )

        try:
            # Fetch environment details
            environment = await db_service.get_environment(environment_id, tenant_id)
            if not environment:
                error_msg = f"Environment {environment_id} not found"
                logger.error(error_msg)
                await background_job_service.update_job_status(
                    job_id=job_id,
                    status=BackgroundJobStatus.FAILED,
                    error_message=error_msg
                )
                raise ValueError(error_msg)

            # Check GitHub configuration
            if not environment.get("git_repo_url") or not environment.get("git_pat"):
                error_msg = "GitHub not configured for this environment. Configure Git integration first."
                logger.error(error_msg)
                await background_job_service.update_job_status(
                    job_id=job_id,
                    status=BackgroundJobStatus.FAILED,
                    error_message=error_msg
                )
                raise ValueError(error_msg)

            # Get environment type (required for GitHub operations)
            env_type = environment.get("n8n_type")
            if not env_type:
                error_msg = "Environment type is required for GitHub workflow operations"
                logger.error(error_msg)
                await background_job_service.update_job_status(
                    job_id=job_id,
                    status=BackgroundJobStatus.FAILED,
                    error_message=error_msg
                )
                raise ValueError(error_msg)

            # Create GitHub service
            from app.services.github_service import GitHubService
            repo_url = environment.get("git_repo_url", "").rstrip('/').replace('.git', '')
            repo_parts = repo_url.split("/")
            github_service = GitHubService(
                token=environment.get("git_pat"),
                repo_owner=repo_parts[-2] if len(repo_parts) >= 2 else "",
                repo_name=repo_parts[-1] if len(repo_parts) >= 1 else "",
                branch=environment.get("git_branch", "main")
            )

            if not github_service.is_configured():
                error_msg = "GitHub is not properly configured"
                logger.error(error_msg)
                await background_job_service.update_job_status(
                    job_id=job_id,
                    status=BackgroundJobStatus.FAILED,
                    error_message=error_msg
                )
                raise ValueError(error_msg)

            # Create provider adapter
            from app.services.provider_registry import ProviderRegistry
            adapter = ProviderRegistry.get_adapter_for_environment(environment)

            # Import snapshot-related dependencies
            from app.schemas.deployment import SnapshotType
            from uuid import uuid4

            # Set default reason
            snapshot_reason = reason or "Bulk snapshot operation"

            # Process each workflow sequentially
            for index, workflow_id in enumerate(workflow_ids, start=1):
                workflow_result = BulkWorkflowService._create_workflow_result(workflow_id)

                try:
                    logger.info(
                        f"Creating snapshot for workflow {workflow_id} ({index}/{total}) "
                        f"in environment {environment_id}"
                    )

                    # Fetch the workflow from the provider
                    workflow_data = await adapter.get_workflow(workflow_id)
                    if not workflow_data:
                        error_msg = f"Workflow {workflow_id} not found in environment {environment_id}"
                        logger.warning(error_msg)
                        workflow_result["error_message"] = error_msg
                        failed += 1
                    else:
                        workflow_name = workflow_data.get("name", f"workflow-{workflow_id}")

                        # Export workflow to GitHub
                        try:
                            await github_service.sync_workflow_to_github(
                                workflow_id=workflow_id,
                                workflow_name=workflow_name,
                                workflow_data=workflow_data,
                                commit_message=f"Bulk snapshot: {snapshot_reason} - {workflow_name}",
                                environment_type=env_type
                            )
                            logger.info(f"Successfully exported workflow {workflow_id} to GitHub")
                        except Exception as e:
                            error_msg = f"Failed to export workflow to GitHub: {str(e)}"
                            logger.error(error_msg, exc_info=True)
                            workflow_result["error_message"] = error_msg
                            failed += 1
                            results.append(workflow_result)
                            continue

                        # Get the latest commit SHA for this workflow
                        commit_sha = None
                        try:
                            sanitized_folder = github_service._sanitize_foldername(env_type)
                            commits = github_service.repo.get_commits(
                                path=f"workflows/{sanitized_folder}",
                                sha=github_service.branch
                            )
                            if commits:
                                commit_sha = commits[0].sha
                        except Exception as e:
                            logger.warning(f"Could not get commit SHA for workflow {workflow_id}: {str(e)}")

                        # Create snapshot record in database
                        snapshot_id = str(uuid4())
                        snapshot_data = {
                            "id": snapshot_id,
                            "tenant_id": tenant_id,
                            "environment_id": environment_id,
                            "git_commit_sha": commit_sha or "",
                            "type": SnapshotType.MANUAL_BACKUP.value,
                            "created_by_user_id": created_by,
                            "related_deployment_id": None,
                            "metadata_json": {
                                "reason": snapshot_reason,
                                "notes": notes,
                                "workflow_id": workflow_id,
                                "workflow_name": workflow_name,
                                "environment_name": environment.get("name"),
                                "environment_type": env_type,
                                "bulk_operation": True,
                                "bulk_job_id": job_id
                            },
                        }

                        await db_service.create_snapshot(snapshot_data)
                        logger.info(f"Created snapshot {snapshot_id} for workflow {workflow_id}")

                        # Mark as successful
                        workflow_result["success"] = True
                        workflow_result["snapshot_id"] = snapshot_id
                        succeeded += 1

                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Error creating snapshot for workflow {workflow_id}: {error_msg}", exc_info=True)
                    workflow_result["error_message"] = error_msg
                    failed += 1

                # Add result to list
                results.append(workflow_result)

                # Update job progress after each workflow
                await BulkWorkflowService._update_job_progress(
                    job_id=job_id,
                    current=index,
                    total=total,
                    succeeded=succeeded,
                    failed=failed,
                    results=results,
                    operation_name="snapshot",
                    current_workflow_id=workflow_id,
                    tenant_id=tenant_id
                )

            # Mark job as completed
            await BulkWorkflowService._finalize_job(
                job_id=job_id,
                total=total,
                succeeded=succeeded,
                failed=failed,
                results=results,
                operation_name="snapshot",
                tenant_id=tenant_id
            )

            # Return aggregated results
            aggregated = BulkWorkflowService._aggregate_results(results)
            return {
                **aggregated,
                "results": results
            }

        except Exception as e:
            # Handle catastrophic failure
            await BulkWorkflowService._handle_catastrophic_failure(
                job_id=job_id,
                error=e,
                total=total,
                succeeded=succeeded,
                failed=failed,
                results=results,
                operation_name="snapshot",
                tenant_id=tenant_id
            )

            raise


# Singleton instance
bulk_workflow_service = BulkWorkflowService()
