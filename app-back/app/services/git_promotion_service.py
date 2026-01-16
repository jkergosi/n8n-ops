"""
Git-Based Promotion Service

Implements the promotion flow using Git snapshots with target-ownership model.

Key Rules:
1. Snapshots are owned by TARGET environment
2. Pointers only reference snapshots in same env folder
3. Snapshots committed BEFORE any target mutations
4. Pointers updated ONLY after deploy + verify
5. STAGING→PROD requires approval

Flow: DEV → STAGING
1. Export selected workflows from DEV runtime
2. Create snapshot under staging/snapshots/<id>/
3. Commit snapshot → STOP if fails
4. ensure_environment_onboarded(staging) → BLOCKING
5. Precheck credentials
6. Deploy snapshot to STAGING
7. Verify runtime matches snapshot
8. Update staging/current.json
9. Commit pointer

Flow: STAGING → PROD
1. Read staging/current.json → get snapshot ID
2. Load snapshot content from staging
3. Create NEW snapshot under prod/snapshots/<id>/
4. Commit snapshot → STOP if fails
5. Create deployment record with PENDING_APPROVAL
6. Wait for approval
7. Precheck credentials
8. Deploy snapshot to PROD
9. Verify
10. Update prod/current.json
11. Commit pointer
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from app.services.database import db_service
from app.services.provider_registry import ProviderRegistry
from app.services.git_snapshot_service import git_snapshot_service, compute_workflow_hash
from app.services.onboarding_service import onboarding_service
from app.services.github_service import GitHubService
from app.schemas.snapshot_manifest import SnapshotKind, generate_snapshot_id

logger = logging.getLogger(__name__)


class PromotionStatus(str, Enum):
    """Status of a promotion operation."""
    PENDING = "pending"
    CREATING_SNAPSHOT = "creating_snapshot"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    DEPLOYING = "deploying"
    VERIFYING = "verifying"
    UPDATING_POINTER = "updating_pointer"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class EnvironmentClass(str, Enum):
    """Environment class for determining promotion rules."""
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class PromotionWorkflow:
    """A workflow selected for promotion."""
    workflow_id: str
    workflow_name: str
    workflow_data: Dict[str, Any]
    content_hash: str
    active: bool = False


@dataclass
class PromotionResult:
    """Result of a promotion operation."""
    success: bool
    promotion_id: str
    snapshot_id: Optional[str] = None
    commit_sha: Optional[str] = None
    status: PromotionStatus = PromotionStatus.PENDING
    workflows_promoted: int = 0
    error: Optional[str] = None
    requires_approval: bool = False
    verification_passed: bool = False
    pointer_updated: bool = False


@dataclass
class PromotionRequest:
    """Request to initiate a promotion."""
    tenant_id: str
    source_env_id: str
    target_env_id: str
    workflow_ids: List[str]  # Empty = all workflows
    user_id: Optional[str] = None
    reason: Optional[str] = None


@dataclass
class RollbackRequest:
    """Request to initiate a rollback."""
    tenant_id: str
    env_id: str
    snapshot_id: str  # Target snapshot to rollback to
    user_id: Optional[str] = None
    reason: Optional[str] = None


@dataclass
class RollbackResult:
    """Result of a rollback operation."""
    success: bool
    rollback_id: str
    snapshot_id: str
    commit_sha: Optional[str] = None
    status: PromotionStatus = PromotionStatus.PENDING
    workflows_deployed: int = 0
    error: Optional[str] = None
    requires_approval: bool = False
    verification_passed: bool = False
    pointer_updated: bool = False


def _get_env_class(env_config: Dict[str, Any]) -> EnvironmentClass:
    """Get environment class from config."""
    env_class_str = env_config.get("environment_class", "dev")
    try:
        return EnvironmentClass(env_class_str)
    except ValueError:
        return EnvironmentClass.DEV


def _requires_approval(target_env_class: EnvironmentClass) -> bool:
    """Check if promotion to target environment requires approval."""
    return target_env_class == EnvironmentClass.PRODUCTION


class GitPromotionService:
    """
    Service for Git-based workflow promotions with target-ownership model.
    """

    def __init__(self):
        self.db = db_service

    def _get_github_service(self, env_config: Dict[str, Any]) -> GitHubService:
        """Create GitHubService for an environment's Git configuration."""
        repo_url = env_config.get("git_repo_url", "").rstrip('/').replace('.git', '')
        repo_parts = repo_url.split("/")

        return GitHubService(
            token=env_config.get("git_pat"),
            repo_owner=repo_parts[-2] if len(repo_parts) >= 2 else "",
            repo_name=repo_parts[-1] if len(repo_parts) >= 1 else "",
            branch=env_config.get("git_branch", "main")
        )

    async def initiate_promotion(
        self,
        request: PromotionRequest,
    ) -> PromotionResult:
        """
        Initiate a promotion from source to target environment.

        This method:
        1. Validates environments
        2. Exports workflows from source
        3. Creates snapshot in target env
        4. If PROD: returns PENDING_APPROVAL
        5. If not PROD: continues to deploy

        Returns:
            PromotionResult with status and details
        """
        promotion_id = generate_snapshot_id()  # Use UUID for promotion ID

        try:
            # Get environment configs
            source_env = await self.db.get_environment(request.source_env_id, request.tenant_id)
            target_env = await self.db.get_environment(request.target_env_id, request.tenant_id)

            if not source_env:
                return PromotionResult(
                    success=False,
                    promotion_id=promotion_id,
                    status=PromotionStatus.FAILED,
                    error=f"Source environment {request.source_env_id} not found",
                )

            if not target_env:
                return PromotionResult(
                    success=False,
                    promotion_id=promotion_id,
                    status=PromotionStatus.FAILED,
                    error=f"Target environment {request.target_env_id} not found",
                )

            source_env_type = source_env.get("n8n_type")
            target_env_type = target_env.get("n8n_type")
            target_env_class = _get_env_class(target_env)

            if not source_env_type or not target_env_type:
                return PromotionResult(
                    success=False,
                    promotion_id=promotion_id,
                    status=PromotionStatus.FAILED,
                    error="Both environments must have n8n_type configured",
                )

            # Validate Git configuration
            if not target_env.get("git_repo_url") or not target_env.get("git_pat"):
                return PromotionResult(
                    success=False,
                    promotion_id=promotion_id,
                    status=PromotionStatus.FAILED,
                    error="Target environment must have Git configured",
                )

            logger.info(
                f"Initiating promotion {promotion_id}: "
                f"{source_env_type} → {target_env_type}"
            )

            # Check if this is STAGING → PROD (uses pointer-based flow)
            source_env_class = _get_env_class(source_env)

            if source_env_class == EnvironmentClass.STAGING and target_env_class == EnvironmentClass.PRODUCTION:
                return await self._initiate_staging_to_prod(
                    request=request,
                    promotion_id=promotion_id,
                    source_env=source_env,
                    target_env=target_env,
                )
            else:
                # DEV → STAGING or other promotions: export from runtime
                return await self._initiate_dev_to_staging(
                    request=request,
                    promotion_id=promotion_id,
                    source_env=source_env,
                    target_env=target_env,
                )

        except Exception as e:
            logger.error(f"Promotion {promotion_id} failed: {str(e)}")
            return PromotionResult(
                success=False,
                promotion_id=promotion_id,
                status=PromotionStatus.FAILED,
                error=str(e),
            )

    async def _initiate_dev_to_staging(
        self,
        request: PromotionRequest,
        promotion_id: str,
        source_env: Dict[str, Any],
        target_env: Dict[str, Any],
    ) -> PromotionResult:
        """
        DEV → STAGING promotion flow.

        1. Export selected workflows from DEV runtime
        2. Create snapshot under staging/snapshots/<id>/
        3. Commit snapshot → STOP if fails
        4. ensure_environment_onboarded(staging) → BLOCKING
        5. Precheck credentials
        6. Deploy snapshot to STAGING
        7. Verify runtime matches snapshot
        8. Update staging/current.json
        9. Commit pointer
        """
        target_env_type = target_env.get("n8n_type")
        target_env_class = _get_env_class(target_env)

        try:
            # Step 1: Export selected workflows from DEV runtime
            logger.info(f"Promotion {promotion_id}: Exporting workflows from source...")

            adapter = ProviderRegistry.get_adapter_for_environment(source_env)
            all_workflows = await adapter.get_workflows()

            # Filter to selected workflows if specified
            if request.workflow_ids:
                workflow_ids_set = set(request.workflow_ids)
                selected_workflows = [w for w in all_workflows if w.get("id") in workflow_ids_set]
            else:
                selected_workflows = all_workflows

            if not selected_workflows:
                return PromotionResult(
                    success=False,
                    promotion_id=promotion_id,
                    status=PromotionStatus.FAILED,
                    error="No workflows selected for promotion",
                )

            # P2 FIX: Validate that all workflows are LINKED (managed) before promotion
            # UNMAPPED workflows cannot be promoted - they must be onboarded first
            unmanaged_workflows = await self._check_unmapped_workflows(
                tenant_id=request.tenant_id,
                env_id=request.source_env_id,
                workflow_ids=[w.get("id") for w in selected_workflows if w.get("id")],
            )
            if unmanaged_workflows:
                return PromotionResult(
                    success=False,
                    promotion_id=promotion_id,
                    status=PromotionStatus.FAILED,
                    error=f"Cannot promote unmanaged workflows: {', '.join(unmanaged_workflows[:3])}{'...' if len(unmanaged_workflows) > 3 else ''}. Onboard these workflows first.",
                )

            # Get full workflow data
            workflows: Dict[str, Dict[str, Any]] = {}
            for wf in selected_workflows:
                workflow_id = wf.get("id")
                if workflow_id:
                    try:
                        full_workflow = await adapter.get_workflow(workflow_id)
                        workflows[workflow_id] = full_workflow
                    except Exception as e:
                        logger.warning(f"Failed to get workflow {workflow_id}: {e}")

            logger.info(f"Promotion {promotion_id}: Exported {len(workflows)} workflows")

            # Step 2-3: Create snapshot in TARGET env and commit
            logger.info(f"Promotion {promotion_id}: Creating snapshot in {target_env_type}...")

            snapshot_id, commit_sha = await git_snapshot_service.create_snapshot(
                tenant_id=request.tenant_id,
                target_env_id=request.target_env_id,
                workflows=workflows,
                kind=SnapshotKind.PROMOTION,
                source_env=source_env.get("n8n_type"),
                created_by=request.user_id,
                reason=request.reason or f"Promotion from {source_env.get('n8n_type')}",
                promotion_id=promotion_id,
            )

            logger.info(f"Promotion {promotion_id}: Snapshot {snapshot_id} committed at {commit_sha}")

            # Step 4: Ensure target is onboarded (BLOCKING)
            logger.info(f"Promotion {promotion_id}: Ensuring target is onboarded...")

            onboarding_result = await onboarding_service.ensure_environment_onboarded(
                tenant_id=request.tenant_id,
                env_id=request.target_env_id,
                user_id=request.user_id,
                blocking=True,
            )

            if not onboarding_result.success and not onboarding_result.already_onboarded:
                return PromotionResult(
                    success=False,
                    promotion_id=promotion_id,
                    snapshot_id=snapshot_id,
                    commit_sha=commit_sha,
                    status=PromotionStatus.FAILED,
                    error=f"Target onboarding failed: {onboarding_result.error}",
                )

            # Check if approval required
            if _requires_approval(target_env_class):
                logger.info(f"Promotion {promotion_id}: Requires approval (target is PROD)")

                # Create DB record for approval tracking
                await self._create_promotion_record(
                    promotion_id=promotion_id,
                    request=request,
                    snapshot_id=snapshot_id,
                    commit_sha=commit_sha,
                    status=PromotionStatus.PENDING_APPROVAL,
                    workflows_count=len(workflows),
                )

                return PromotionResult(
                    success=True,
                    promotion_id=promotion_id,
                    snapshot_id=snapshot_id,
                    commit_sha=commit_sha,
                    status=PromotionStatus.PENDING_APPROVAL,
                    workflows_promoted=len(workflows),
                    requires_approval=True,
                )

            # Step 5-9: Continue to deploy (no approval needed)
            return await self._execute_deployment(
                promotion_id=promotion_id,
                request=request,
                target_env=target_env,
                snapshot_id=snapshot_id,
                commit_sha=commit_sha,
                workflows=workflows,
            )

        except Exception as e:
            logger.error(f"Promotion {promotion_id} failed: {str(e)}")
            return PromotionResult(
                success=False,
                promotion_id=promotion_id,
                status=PromotionStatus.FAILED,
                error=str(e),
            )

    async def _initiate_staging_to_prod(
        self,
        request: PromotionRequest,
        promotion_id: str,
        source_env: Dict[str, Any],
        target_env: Dict[str, Any],
    ) -> PromotionResult:
        """
        STAGING → PROD promotion flow.

        1. Read staging/current.json → get snapshot ID
        2. Load snapshot content from staging
        3. Create NEW snapshot under prod/snapshots/<id>/
        4. Commit snapshot → STOP if fails
        5. Create deployment record with PENDING_APPROVAL
        6. Wait for approval (handled by approve endpoint)
        """
        source_env_type = source_env.get("n8n_type")
        target_env_type = target_env.get("n8n_type")

        try:
            # Step 1: Get staging's current snapshot
            logger.info(f"Promotion {promotion_id}: Reading {source_env_type} pointer...")

            current_snapshot_id = await git_snapshot_service.get_current_snapshot_id(
                tenant_id=request.tenant_id,
                env_id=request.source_env_id,
            )

            if not current_snapshot_id:
                return PromotionResult(
                    success=False,
                    promotion_id=promotion_id,
                    status=PromotionStatus.FAILED,
                    error=f"{source_env_type} is not onboarded (no current.json)",
                )

            # Step 2: Load snapshot content
            logger.info(f"Promotion {promotion_id}: Loading snapshot {current_snapshot_id}...")

            source_manifest, workflows = await git_snapshot_service.get_snapshot_content(
                tenant_id=request.tenant_id,
                env_id=request.source_env_id,
                snapshot_id=current_snapshot_id,
            )

            if not source_manifest or not workflows:
                return PromotionResult(
                    success=False,
                    promotion_id=promotion_id,
                    status=PromotionStatus.FAILED,
                    error=f"Failed to load snapshot {current_snapshot_id} from {source_env_type}",
                )

            # Filter workflows if specific IDs requested
            if request.workflow_ids:
                workflow_ids_set = set(request.workflow_ids)
                workflows = {k: v for k, v in workflows.items() if k in workflow_ids_set}

            if not workflows:
                return PromotionResult(
                    success=False,
                    promotion_id=promotion_id,
                    status=PromotionStatus.FAILED,
                    error="No workflows selected for promotion",
                )

            logger.info(f"Promotion {promotion_id}: Loaded {len(workflows)} workflows from staging")

            # Step 3-4: Create NEW snapshot in PROD (copy content, new ID)
            logger.info(f"Promotion {promotion_id}: Creating snapshot in {target_env_type}...")

            snapshot_id, commit_sha = await git_snapshot_service.create_snapshot(
                tenant_id=request.tenant_id,
                target_env_id=request.target_env_id,
                workflows=workflows,
                kind=SnapshotKind.PROMOTION,
                source_env=source_env_type,
                source_snapshot_id=current_snapshot_id,
                created_by=request.user_id,
                reason=request.reason or f"Promotion from {source_env_type}",
                promotion_id=promotion_id,
            )

            logger.info(f"Promotion {promotion_id}: Snapshot {snapshot_id} committed at {commit_sha}")

            # Step 5: Create PENDING_APPROVAL record (PROD always requires approval)
            logger.info(f"Promotion {promotion_id}: Creating approval request...")

            await self._create_promotion_record(
                promotion_id=promotion_id,
                request=request,
                snapshot_id=snapshot_id,
                commit_sha=commit_sha,
                status=PromotionStatus.PENDING_APPROVAL,
                workflows_count=len(workflows),
                source_snapshot_id=current_snapshot_id,
            )

            return PromotionResult(
                success=True,
                promotion_id=promotion_id,
                snapshot_id=snapshot_id,
                commit_sha=commit_sha,
                status=PromotionStatus.PENDING_APPROVAL,
                workflows_promoted=len(workflows),
                requires_approval=True,
            )

        except Exception as e:
            logger.error(f"Promotion {promotion_id} failed: {str(e)}")
            return PromotionResult(
                success=False,
                promotion_id=promotion_id,
                status=PromotionStatus.FAILED,
                error=str(e),
            )

    async def approve_and_execute(
        self,
        tenant_id: str,
        promotion_id: str,
        approved_by: str,
    ) -> PromotionResult:
        """
        Approve a pending promotion and execute deployment.

        Called after approval is granted for PROD promotions.
        """
        try:
            # Get promotion record
            promotion = await self._get_promotion_record(tenant_id, promotion_id)
            if not promotion:
                return PromotionResult(
                    success=False,
                    promotion_id=promotion_id,
                    status=PromotionStatus.FAILED,
                    error=f"Promotion {promotion_id} not found",
                )

            if promotion.get("status") != PromotionStatus.PENDING_APPROVAL.value:
                return PromotionResult(
                    success=False,
                    promotion_id=promotion_id,
                    status=PromotionStatus.FAILED,
                    error=f"Promotion is not pending approval (status: {promotion.get('status')})",
                )

            # Get target environment
            target_env_id = promotion.get("target_environment_id")
            target_env = await self.db.get_environment(target_env_id, tenant_id)
            if not target_env:
                return PromotionResult(
                    success=False,
                    promotion_id=promotion_id,
                    status=PromotionStatus.FAILED,
                    error=f"Target environment not found",
                )

            # Get snapshot content
            snapshot_id = promotion.get("snapshot_id")
            _, workflows = await git_snapshot_service.get_snapshot_content(
                tenant_id=tenant_id,
                env_id=target_env_id,
                snapshot_id=snapshot_id,
            )

            if not workflows:
                return PromotionResult(
                    success=False,
                    promotion_id=promotion_id,
                    status=PromotionStatus.FAILED,
                    error=f"Failed to load snapshot content",
                )

            # Update status to APPROVED
            await self._update_promotion_status(
                tenant_id=tenant_id,
                promotion_id=promotion_id,
                status=PromotionStatus.APPROVED,
                approved_by=approved_by,
            )

            # Execute deployment
            request = PromotionRequest(
                tenant_id=tenant_id,
                source_env_id=promotion.get("source_environment_id"),
                target_env_id=target_env_id,
                workflow_ids=[],  # All workflows in snapshot
                user_id=approved_by,
            )

            return await self._execute_deployment(
                promotion_id=promotion_id,
                request=request,
                target_env=target_env,
                snapshot_id=snapshot_id,
                commit_sha=promotion.get("commit_sha"),
                workflows=workflows,
            )

        except Exception as e:
            logger.error(f"Approval execution failed for {promotion_id}: {str(e)}")
            return PromotionResult(
                success=False,
                promotion_id=promotion_id,
                status=PromotionStatus.FAILED,
                error=str(e),
            )

    async def _execute_deployment(
        self,
        promotion_id: str,
        request: PromotionRequest,
        target_env: Dict[str, Any],
        snapshot_id: str,
        commit_sha: str,
        workflows: Dict[str, Dict[str, Any]],
    ) -> PromotionResult:
        """
        Execute the deployment phase of a promotion.

        Steps:
        5. Precheck credentials
        6. Deploy snapshot to target
        7. Verify runtime matches snapshot
        8. Update target/current.json
        9. Commit pointer
        """
        target_env_type = target_env.get("n8n_type")

        try:
            # Update status
            await self._update_promotion_status(
                tenant_id=request.tenant_id,
                promotion_id=promotion_id,
                status=PromotionStatus.DEPLOYING,
            )

            # Step 5: Precheck credentials
            logger.info(f"Promotion {promotion_id}: Prechecking credentials...")
            # TODO: Implement credential precheck
            # For now, we'll rely on deploy-time errors

            # Step 6: Deploy workflows to target
            logger.info(f"Promotion {promotion_id}: Deploying {len(workflows)} workflows...")

            adapter = ProviderRegistry.get_adapter_for_environment(target_env)
            deployed_count = 0
            errors = []

            for workflow_id, workflow_data in workflows.items():
                try:
                    # Try to update existing workflow, or create new
                    try:
                        await adapter.update_workflow(workflow_id, workflow_data)
                    except Exception:
                        # Workflow doesn't exist, create it
                        await adapter.create_workflow(workflow_data)

                    deployed_count += 1
                except Exception as e:
                    errors.append(f"Workflow {workflow_id}: {str(e)}")
                    logger.error(f"Failed to deploy workflow {workflow_id}: {e}")

            if errors and deployed_count == 0:
                return PromotionResult(
                    success=False,
                    promotion_id=promotion_id,
                    snapshot_id=snapshot_id,
                    commit_sha=commit_sha,
                    status=PromotionStatus.FAILED,
                    workflows_promoted=deployed_count,
                    error=f"Deployment failed: {'; '.join(errors[:3])}",
                )

            logger.info(f"Promotion {promotion_id}: Deployed {deployed_count}/{len(workflows)} workflows")

            # Step 7: Verify runtime matches snapshot
            logger.info(f"Promotion {promotion_id}: Verifying deployment...")

            await self._update_promotion_status(
                tenant_id=request.tenant_id,
                promotion_id=promotion_id,
                status=PromotionStatus.VERIFYING,
            )

            matches, mismatches = await git_snapshot_service.verify_runtime_matches_snapshot(
                tenant_id=request.tenant_id,
                env_id=request.target_env_id,
                snapshot_workflows=workflows,
            )

            if not matches:
                logger.warning(f"Promotion {promotion_id}: Verification found mismatches: {mismatches}")
                # Continue anyway, log warning (don't fail on verification)

            # Step 8-9: Update pointer ONLY after successful deploy
            logger.info(f"Promotion {promotion_id}: Updating {target_env_type} pointer...")

            await self._update_promotion_status(
                tenant_id=request.tenant_id,
                promotion_id=promotion_id,
                status=PromotionStatus.UPDATING_POINTER,
            )

            pointer_commit = await git_snapshot_service.update_env_pointer(
                tenant_id=request.tenant_id,
                env_id=request.target_env_id,
                snapshot_id=snapshot_id,
                snapshot_commit=commit_sha,
                updated_by=request.user_id,
            )

            logger.info(f"Promotion {promotion_id}: Pointer updated at {pointer_commit}")

            # Mark as completed
            await self._update_promotion_status(
                tenant_id=request.tenant_id,
                promotion_id=promotion_id,
                status=PromotionStatus.COMPLETED,
            )

            return PromotionResult(
                success=True,
                promotion_id=promotion_id,
                snapshot_id=snapshot_id,
                commit_sha=commit_sha,
                status=PromotionStatus.COMPLETED,
                workflows_promoted=deployed_count,
                verification_passed=matches,
                pointer_updated=True,
            )

        except Exception as e:
            logger.error(f"Deployment failed for {promotion_id}: {str(e)}")

            await self._update_promotion_status(
                tenant_id=request.tenant_id,
                promotion_id=promotion_id,
                status=PromotionStatus.FAILED,
                error=str(e),
            )

            return PromotionResult(
                success=False,
                promotion_id=promotion_id,
                snapshot_id=snapshot_id,
                commit_sha=commit_sha,
                status=PromotionStatus.FAILED,
                error=str(e),
            )

    async def _create_promotion_record(
        self,
        promotion_id: str,
        request: PromotionRequest,
        snapshot_id: str,
        commit_sha: str,
        status: PromotionStatus,
        workflows_count: int,
        source_snapshot_id: Optional[str] = None,
    ) -> None:
        """Create a promotion record in the database for tracking."""
        # Store in existing promotions table for compatibility
        promotion_data = {
            "id": promotion_id,
            "tenant_id": request.tenant_id,
            "source_environment_id": request.source_env_id,
            "target_environment_id": request.target_env_id,
            "status": status.value,
            "snapshot_id": snapshot_id,
            "commit_sha": commit_sha,
            "source_snapshot_id": source_snapshot_id,
            "workflows_count": workflows_count,
            "created_by": request.user_id,
            "reason": request.reason,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # Use deployments table for now (similar structure)
            await self.db.client.table("deployments").insert(promotion_data).execute()
        except Exception as e:
            # Log but don't fail - DB is just index
            logger.warning(f"Failed to create promotion record: {e}")

    async def _get_promotion_record(
        self,
        tenant_id: str,
        promotion_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get promotion record from database."""
        try:
            result = self.db.client.table("deployments").select("*").eq(
                "id", promotion_id
            ).eq("tenant_id", tenant_id).single().execute()
            return result.data
        except Exception:
            return None

    async def _update_promotion_status(
        self,
        tenant_id: str,
        promotion_id: str,
        status: PromotionStatus,
        approved_by: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update promotion status in database."""
        try:
            update_data = {
                "status": status.value,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            if approved_by:
                update_data["approved_by_user_id"] = approved_by
                update_data["approved_at"] = datetime.now(timezone.utc).isoformat()

            if error:
                update_data["error_message"] = error

            if status == PromotionStatus.DEPLOYING:
                update_data["started_at"] = datetime.now(timezone.utc).isoformat()

            if status in [PromotionStatus.COMPLETED, PromotionStatus.FAILED]:
                update_data["finished_at"] = datetime.now(timezone.utc).isoformat()

            self.db.client.table("deployments").update(update_data).eq(
                "id", promotion_id
            ).eq("tenant_id", tenant_id).execute()
        except Exception as e:
            logger.warning(f"Failed to update promotion status: {e}")

    # ========== ROLLBACK METHODS ==========

    async def get_available_snapshots(
        self,
        tenant_id: str,
        env_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get list of available snapshots for an environment.

        Returns snapshots from <env>/snapshots/ directory with manifest info.
        """
        try:
            env_config = await self.db.get_environment(env_id, tenant_id)
            if not env_config:
                return []

            env_type = env_config.get("n8n_type")
            if not env_type or not env_config.get("git_repo_url"):
                return []

            github_service = self._get_github_service(env_config)
            snapshots = await github_service.get_snapshot_list(env_type)

            return snapshots

        except Exception as e:
            logger.error(f"Failed to get snapshots for {env_id}: {e}")
            return []

    async def get_current_snapshot_info(
        self,
        tenant_id: str,
        env_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get current snapshot info for an environment.

        Returns the snapshot ID and pointer info from current.json.
        """
        try:
            pointer = await git_snapshot_service.get_current_pointer(
                tenant_id=tenant_id,
                env_id=env_id,
            )
            return pointer
        except Exception as e:
            logger.error(f"Failed to get current snapshot for {env_id}: {e}")
            return None

    async def initiate_rollback(
        self,
        request: RollbackRequest,
    ) -> RollbackResult:
        """
        Initiate a rollback to a previous snapshot.

        Rollback Rules:
        1. Rollback always deploys a snapshot from the SAME environment
        2. PROD rollback requires approval
        3. STAGING/DEV rollback do not require approval

        Flow:
        1. Validate environment and snapshot exist
        2. Load snapshot content
        3. If PROD: return PENDING_APPROVAL
        4. If not PROD: continue to deploy
        5. Deploy snapshot
        6. Verify
        7. Update <env>/current.json
        8. Commit pointer
        """
        rollback_id = generate_snapshot_id()

        try:
            # Get environment config
            env_config = await self.db.get_environment(request.env_id, request.tenant_id)
            if not env_config:
                return RollbackResult(
                    success=False,
                    rollback_id=rollback_id,
                    snapshot_id=request.snapshot_id,
                    status=PromotionStatus.FAILED,
                    error=f"Environment {request.env_id} not found",
                )

            env_type = env_config.get("n8n_type")
            env_class = _get_env_class(env_config)
            env_name = env_config.get("n8n_name", env_type)

            if not env_type or not env_config.get("git_repo_url"):
                return RollbackResult(
                    success=False,
                    rollback_id=rollback_id,
                    snapshot_id=request.snapshot_id,
                    status=PromotionStatus.FAILED,
                    error="Environment must have Git configured",
                )

            logger.info(
                f"Initiating rollback {rollback_id}: {env_name} → snapshot {request.snapshot_id}"
            )

            # Step 1: Validate snapshot exists in this env
            logger.info(f"Rollback {rollback_id}: Validating snapshot...")

            github_service = self._get_github_service(env_config)
            snapshot_exists = await github_service.check_snapshot_exists(
                env_type, request.snapshot_id
            )

            if not snapshot_exists:
                return RollbackResult(
                    success=False,
                    rollback_id=rollback_id,
                    snapshot_id=request.snapshot_id,
                    status=PromotionStatus.FAILED,
                    error=f"Snapshot {request.snapshot_id} not found in {env_type}",
                )

            # Step 2: Load snapshot content
            logger.info(f"Rollback {rollback_id}: Loading snapshot content...")

            manifest, workflows = await git_snapshot_service.get_snapshot_content(
                tenant_id=request.tenant_id,
                env_id=request.env_id,
                snapshot_id=request.snapshot_id,
            )

            if not manifest or not workflows:
                return RollbackResult(
                    success=False,
                    rollback_id=rollback_id,
                    snapshot_id=request.snapshot_id,
                    status=PromotionStatus.FAILED,
                    error=f"Failed to load snapshot content",
                )

            workflows_count = len(workflows)
            logger.info(f"Rollback {rollback_id}: Loaded {workflows_count} workflows")

            # Get snapshot commit SHA from manifest
            commit_sha = manifest.get("commit_sha")

            # Step 3: Check if approval required (PROD rollback)
            if _requires_approval(env_class):
                logger.info(f"Rollback {rollback_id}: Requires approval (target is PROD)")

                # Create rollback record for approval tracking
                await self._create_rollback_record(
                    rollback_id=rollback_id,
                    request=request,
                    commit_sha=commit_sha,
                    status=PromotionStatus.PENDING_APPROVAL,
                    workflows_count=workflows_count,
                )

                return RollbackResult(
                    success=True,
                    rollback_id=rollback_id,
                    snapshot_id=request.snapshot_id,
                    commit_sha=commit_sha,
                    status=PromotionStatus.PENDING_APPROVAL,
                    workflows_deployed=workflows_count,
                    requires_approval=True,
                )

            # Step 4-8: Execute rollback deployment
            return await self._execute_rollback_deployment(
                rollback_id=rollback_id,
                request=request,
                env_config=env_config,
                commit_sha=commit_sha,
                workflows=workflows,
            )

        except Exception as e:
            logger.error(f"Rollback {rollback_id} failed: {str(e)}")
            return RollbackResult(
                success=False,
                rollback_id=rollback_id,
                snapshot_id=request.snapshot_id,
                status=PromotionStatus.FAILED,
                error=str(e),
            )

    async def approve_and_execute_rollback(
        self,
        tenant_id: str,
        rollback_id: str,
        approved_by: str,
    ) -> RollbackResult:
        """
        Approve a pending rollback and execute deployment.

        Called after approval is granted for PROD rollbacks.
        """
        try:
            # Get rollback record
            rollback = await self._get_rollback_record(tenant_id, rollback_id)
            if not rollback:
                return RollbackResult(
                    success=False,
                    rollback_id=rollback_id,
                    snapshot_id="",
                    status=PromotionStatus.FAILED,
                    error=f"Rollback {rollback_id} not found",
                )

            if rollback.get("status") != PromotionStatus.PENDING_APPROVAL.value:
                return RollbackResult(
                    success=False,
                    rollback_id=rollback_id,
                    snapshot_id=rollback.get("snapshot_id", ""),
                    status=PromotionStatus.FAILED,
                    error=f"Rollback is not pending approval (status: {rollback.get('status')})",
                )

            # Get environment config
            env_id = rollback.get("environment_id")
            env_config = await self.db.get_environment(env_id, tenant_id)
            if not env_config:
                return RollbackResult(
                    success=False,
                    rollback_id=rollback_id,
                    snapshot_id=rollback.get("snapshot_id", ""),
                    status=PromotionStatus.FAILED,
                    error="Environment not found",
                )

            # Load snapshot content
            snapshot_id = rollback.get("snapshot_id")
            _, workflows = await git_snapshot_service.get_snapshot_content(
                tenant_id=tenant_id,
                env_id=env_id,
                snapshot_id=snapshot_id,
            )

            if not workflows:
                return RollbackResult(
                    success=False,
                    rollback_id=rollback_id,
                    snapshot_id=snapshot_id,
                    status=PromotionStatus.FAILED,
                    error="Failed to load snapshot content",
                )

            # Update status to APPROVED
            await self._update_rollback_status(
                tenant_id=tenant_id,
                rollback_id=rollback_id,
                status=PromotionStatus.APPROVED,
                approved_by=approved_by,
            )

            # Execute rollback deployment
            request = RollbackRequest(
                tenant_id=tenant_id,
                env_id=env_id,
                snapshot_id=snapshot_id,
                user_id=approved_by,
            )

            return await self._execute_rollback_deployment(
                rollback_id=rollback_id,
                request=request,
                env_config=env_config,
                commit_sha=rollback.get("commit_sha"),
                workflows=workflows,
            )

        except Exception as e:
            logger.error(f"Rollback approval execution failed for {rollback_id}: {str(e)}")
            return RollbackResult(
                success=False,
                rollback_id=rollback_id,
                snapshot_id="",
                status=PromotionStatus.FAILED,
                error=str(e),
            )

    async def _execute_rollback_deployment(
        self,
        rollback_id: str,
        request: RollbackRequest,
        env_config: Dict[str, Any],
        commit_sha: Optional[str],
        workflows: Dict[str, Dict[str, Any]],
    ) -> RollbackResult:
        """
        Execute the rollback deployment phase.

        Steps:
        1. Deploy snapshot to environment
        2. Verify runtime matches snapshot
        3. Update <env>/current.json
        4. Commit pointer
        """
        env_type = env_config.get("n8n_type")
        env_name = env_config.get("n8n_name", env_type)

        try:
            # Update status
            await self._update_rollback_status(
                tenant_id=request.tenant_id,
                rollback_id=rollback_id,
                status=PromotionStatus.DEPLOYING,
            )

            # Step 1: Deploy workflows
            logger.info(f"Rollback {rollback_id}: Deploying {len(workflows)} workflows...")

            adapter = ProviderRegistry.get_adapter_for_environment(env_config)
            deployed_count = 0
            errors = []

            for workflow_id, workflow_data in workflows.items():
                try:
                    try:
                        await adapter.update_workflow(workflow_id, workflow_data)
                    except Exception:
                        await adapter.create_workflow(workflow_data)
                    deployed_count += 1
                except Exception as e:
                    errors.append(f"Workflow {workflow_id}: {str(e)}")
                    logger.error(f"Failed to deploy workflow {workflow_id}: {e}")

            if errors and deployed_count == 0:
                return RollbackResult(
                    success=False,
                    rollback_id=rollback_id,
                    snapshot_id=request.snapshot_id,
                    commit_sha=commit_sha,
                    status=PromotionStatus.FAILED,
                    workflows_deployed=deployed_count,
                    error=f"Rollback deployment failed: {'; '.join(errors[:3])}",
                )

            logger.info(f"Rollback {rollback_id}: Deployed {deployed_count}/{len(workflows)} workflows")

            # Step 2: Verify
            logger.info(f"Rollback {rollback_id}: Verifying deployment...")

            await self._update_rollback_status(
                tenant_id=request.tenant_id,
                rollback_id=rollback_id,
                status=PromotionStatus.VERIFYING,
            )

            matches, mismatches = await git_snapshot_service.verify_runtime_matches_snapshot(
                tenant_id=request.tenant_id,
                env_id=request.env_id,
                snapshot_workflows=workflows,
            )

            if not matches:
                logger.warning(f"Rollback {rollback_id}: Verification found mismatches: {mismatches}")

            # Step 3-4: Update pointer
            logger.info(f"Rollback {rollback_id}: Updating {env_type} pointer...")

            await self._update_rollback_status(
                tenant_id=request.tenant_id,
                rollback_id=rollback_id,
                status=PromotionStatus.UPDATING_POINTER,
            )

            pointer_commit = await git_snapshot_service.update_env_pointer(
                tenant_id=request.tenant_id,
                env_id=request.env_id,
                snapshot_id=request.snapshot_id,
                snapshot_commit=commit_sha,
                updated_by=request.user_id,
            )

            logger.info(f"Rollback {rollback_id}: Pointer updated at {pointer_commit}")

            # Mark as completed
            await self._update_rollback_status(
                tenant_id=request.tenant_id,
                rollback_id=rollback_id,
                status=PromotionStatus.COMPLETED,
            )

            return RollbackResult(
                success=True,
                rollback_id=rollback_id,
                snapshot_id=request.snapshot_id,
                commit_sha=commit_sha,
                status=PromotionStatus.COMPLETED,
                workflows_deployed=deployed_count,
                verification_passed=matches,
                pointer_updated=True,
            )

        except Exception as e:
            logger.error(f"Rollback deployment failed for {rollback_id}: {str(e)}")

            await self._update_rollback_status(
                tenant_id=request.tenant_id,
                rollback_id=rollback_id,
                status=PromotionStatus.FAILED,
                error=str(e),
            )

            return RollbackResult(
                success=False,
                rollback_id=rollback_id,
                snapshot_id=request.snapshot_id,
                commit_sha=commit_sha,
                status=PromotionStatus.FAILED,
                error=str(e),
            )

    async def _create_rollback_record(
        self,
        rollback_id: str,
        request: RollbackRequest,
        commit_sha: Optional[str],
        status: PromotionStatus,
        workflows_count: int,
    ) -> None:
        """Create a rollback record in the database for tracking."""
        rollback_data = {
            "id": rollback_id,
            "tenant_id": request.tenant_id,
            "environment_id": request.env_id,
            "target_environment_id": request.env_id,  # Same as environment_id for rollback
            "snapshot_id": request.snapshot_id,
            "commit_sha": commit_sha,
            "status": status.value,
            "operation_type": "rollback",
            "workflows_count": workflows_count,
            "created_by": request.user_id,
            "reason": request.reason or "Rollback to previous snapshot",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            await self.db.client.table("deployments").insert(rollback_data).execute()
        except Exception as e:
            logger.warning(f"Failed to create rollback record: {e}")

    async def _get_rollback_record(
        self,
        tenant_id: str,
        rollback_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get rollback record from database."""
        try:
            result = self.db.client.table("deployments").select("*").eq(
                "id", rollback_id
            ).eq("tenant_id", tenant_id).eq("operation_type", "rollback").single().execute()
            return result.data
        except Exception:
            return None

    async def _update_rollback_status(
        self,
        tenant_id: str,
        rollback_id: str,
        status: PromotionStatus,
        approved_by: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update rollback status in database."""
        try:
            update_data = {
                "status": status.value,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            if approved_by:
                update_data["approved_by_user_id"] = approved_by
                update_data["approved_at"] = datetime.now(timezone.utc).isoformat()

            if error:
                update_data["error_message"] = error

            if status == PromotionStatus.DEPLOYING:
                update_data["started_at"] = datetime.now(timezone.utc).isoformat()

            if status in [PromotionStatus.COMPLETED, PromotionStatus.FAILED]:
                update_data["finished_at"] = datetime.now(timezone.utc).isoformat()

            self.db.client.table("deployments").update(update_data).eq(
                "id", rollback_id
            ).eq("tenant_id", tenant_id).execute()
        except Exception as e:
            logger.warning(f"Failed to update rollback status: {e}")

    # ========== BACKUP METHODS ==========

    async def create_backup(
        self,
        tenant_id: str,
        env_id: str,
        user_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a backup snapshot for an environment.

        Backup Rules:
        - Creates snapshot with kind=backup
        - Does NOT update the environment pointer
        - Snapshot is stored under <env>/snapshots/<id>/
        - Can be restored later using rollback

        Args:
            tenant_id: Tenant identifier
            env_id: Environment ID to backup
            user_id: User creating the backup
            reason: Reason for backup

        Returns:
            Dict with backup info (snapshot_id, commit_sha, workflows_count)
        """
        backup_id = generate_snapshot_id()

        try:
            # Get environment config
            env_config = await self.db.get_environment(env_id, tenant_id)
            if not env_config:
                return {
                    "success": False,
                    "backup_id": backup_id,
                    "error": f"Environment {env_id} not found",
                }

            env_type = env_config.get("n8n_type")
            env_name = env_config.get("n8n_name", env_type)

            if not env_type or not env_config.get("git_repo_url"):
                return {
                    "success": False,
                    "backup_id": backup_id,
                    "error": "Environment must have Git configured",
                }

            logger.info(f"Creating backup {backup_id} for {env_name}...")

            # Step 1: Export all workflows from runtime
            adapter = ProviderRegistry.get_adapter_for_environment(env_config)
            workflow_list = await adapter.get_workflows()

            workflows: Dict[str, Dict[str, Any]] = {}
            for wf in workflow_list or []:
                workflow_id = wf.get("id")
                if workflow_id:
                    try:
                        full_workflow = await adapter.get_workflow(workflow_id)
                        workflows[workflow_id] = full_workflow
                    except Exception as e:
                        logger.warning(f"Backup {backup_id}: Failed to get workflow {workflow_id}: {e}")

            logger.info(f"Backup {backup_id}: Exported {len(workflows)} workflows")

            # Step 2: Create backup snapshot (does NOT update pointer)
            snapshot_id, commit_sha = await git_snapshot_service.create_snapshot(
                tenant_id=tenant_id,
                target_env_id=env_id,
                workflows=workflows,
                kind=SnapshotKind.BACKUP,
                source_env=None,
                created_by=user_id,
                reason=reason or f"Manual backup of {env_name}",
            )

            logger.info(f"Backup {backup_id}: Created snapshot {snapshot_id} at {commit_sha}")

            # Create backup record in DB (for tracking/history)
            await self._create_backup_record(
                backup_id=backup_id,
                tenant_id=tenant_id,
                env_id=env_id,
                snapshot_id=snapshot_id,
                commit_sha=commit_sha,
                workflows_count=len(workflows),
                user_id=user_id,
                reason=reason,
            )

            return {
                "success": True,
                "backup_id": backup_id,
                "snapshot_id": snapshot_id,
                "commit_sha": commit_sha,
                "workflows_count": len(workflows),
                "environment_id": env_id,
                "environment_name": env_name,
            }

        except Exception as e:
            logger.error(f"Backup {backup_id} failed: {str(e)}")
            return {
                "success": False,
                "backup_id": backup_id,
                "error": str(e),
            }

    async def _create_backup_record(
        self,
        backup_id: str,
        tenant_id: str,
        env_id: str,
        snapshot_id: str,
        commit_sha: str,
        workflows_count: int,
        user_id: Optional[str],
        reason: Optional[str],
    ) -> None:
        """Create a backup record in the database for tracking."""
        backup_data = {
            "id": backup_id,
            "tenant_id": tenant_id,
            "environment_id": env_id,
            "target_environment_id": env_id,  # Same for backups
            "snapshot_id": snapshot_id,
            "commit_sha": commit_sha,
            "status": PromotionStatus.COMPLETED.value,
            "operation_type": "backup",
            "workflows_count": workflows_count,
            "created_by": user_id,
            "reason": reason or "Manual backup",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            await self.db.client.table("deployments").insert(backup_data).execute()
        except Exception as e:
            logger.warning(f"Failed to create backup record: {e}")

    async def list_backups(
        self,
        tenant_id: str,
        env_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List backup records for a tenant.

        Args:
            tenant_id: Tenant identifier
            env_id: Optional environment ID to filter by

        Returns:
            List of backup records
        """
        try:
            query = self.db.client.table("deployments").select("*").eq(
                "tenant_id", tenant_id
            ).eq("operation_type", "backup")

            if env_id:
                query = query.eq("environment_id", env_id)

            query = query.order("created_at", desc=True)
            result = query.execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []

    # ========== VALIDATION METHODS ==========

    async def _check_unmapped_workflows(
        self,
        tenant_id: str,
        env_id: str,
        workflow_ids: List[str],
    ) -> List[str]:
        """
        GUARDRAIL: Enforce LINKED-only promotion.

        This method implements the critical governance rule:
            if mapping.status != "linked":
                raise PromotionError("Cannot promote unmanaged workflow")

        UNMAPPED workflows MUST be blocked from promotion because:
        - They are not tracked by governance
        - They have no baseline in Git
        - Promoting them would bypass the managed workflow lifecycle

        Called by: initiate_promotion() before any promotion proceeds.
        See: git_promotion_service.py:308-321

        Args:
            tenant_id: Tenant identifier
            env_id: Source environment ID
            workflow_ids: List of workflow IDs to check

        Returns:
            List of workflow IDs that are NOT linked (unmanaged).
            If non-empty, promotion MUST be blocked.
        """
        if not workflow_ids:
            return []

        try:
            # Get workflow mappings for this environment
            result = self.db.client.table("workflow_env_map").select(
                "workflow_id, status"
            ).eq("tenant_id", tenant_id).eq(
                "environment_id", env_id
            ).in_("workflow_id", workflow_ids).execute()

            # Build map of workflow_id -> status
            mapping_status = {r["workflow_id"]: r["status"] for r in (result.data or [])}

            # Find workflows that are not linked
            unmanaged = []
            for wf_id in workflow_ids:
                status = mapping_status.get(wf_id)
                # Workflow is unmanaged if:
                # 1. No mapping exists (not in workflow_env_map at all)
                # 2. Status is not "linked"
                if not status or status != "linked":
                    unmanaged.append(wf_id)

            if unmanaged:
                logger.warning(
                    f"Found {len(unmanaged)} unmanaged workflows in env {env_id}: "
                    f"{unmanaged[:5]}{'...' if len(unmanaged) > 5 else ''}"
                )

            return unmanaged

        except Exception as e:
            logger.error(f"Failed to check workflow mappings: {e}")
            # On error, don't block - allow promotion to proceed
            # This prevents database issues from blocking all promotions
            return []


# Singleton instance
git_promotion_service = GitPromotionService()
