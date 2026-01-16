"""
Environment Onboarding Service

Handles automatic onboarding of new environments to the Git snapshot system.

Definition:
- Environment is NEW if `<env>/current.json` does not exist in Git

Triggers:
- Environment connection test (async allowed)
- Promotion involving that environment (BLOCKING required)

Steps:
1. Export all workflows from runtime
2. Create snapshot under `<env>/snapshots/<id>/`
3. Commit snapshot to Git
4. Create `<env>/current.json`
5. Commit pointer
6. Verify runtime matches snapshot
"""
import asyncio
import logging
from typing import Optional, Dict, Any, Set
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.services.database import db_service
from app.services.provider_registry import ProviderRegistry
from app.services.git_snapshot_service import git_snapshot_service
from app.schemas.snapshot_manifest import SnapshotKind

logger = logging.getLogger(__name__)


# Simple in-memory lock for onboarding operations
# Key: environment_id, Value: True if lock held
_onboarding_locks: Dict[str, bool] = {}
_onboarding_lock = asyncio.Lock()


@dataclass
class OnboardingResult:
    """Result of an onboarding operation."""
    success: bool
    snapshot_id: Optional[str] = None
    commit_sha: Optional[str] = None
    workflows_count: int = 0
    error: Optional[str] = None
    already_onboarded: bool = False


class OnboardingConflictError(HTTPException):
    """Raised when onboarding is already in progress for an environment."""

    def __init__(self, env_id: str, env_name: Optional[str] = None):
        detail = {
            "error": "onboarding_conflict",
            "message": f"Onboarding is already in progress for environment {env_name or env_id}",
            "environment_id": env_id,
        }
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )


class OnboardingService:
    """
    Service for managing environment onboarding to Git snapshot system.

    Onboarding creates the initial snapshot and pointer for a NEW environment.
    An environment is NEW if it has no `<env>/current.json` pointer in Git.
    """

    def __init__(self):
        self.db = db_service

    async def _acquire_lock(self, env_id: str) -> bool:
        """
        Acquire onboarding lock for an environment.

        Returns:
            True if lock acquired, False if already held
        """
        async with _onboarding_lock:
            if _onboarding_locks.get(env_id):
                return False
            _onboarding_locks[env_id] = True
            return True

    async def _release_lock(self, env_id: str) -> None:
        """Release onboarding lock for an environment."""
        async with _onboarding_lock:
            _onboarding_locks.pop(env_id, None)

    async def ensure_environment_onboarded(
        self,
        tenant_id: str,
        env_id: str,
        user_id: Optional[str] = None,
        blocking: bool = True,
    ) -> OnboardingResult:
        """
        Ensure an environment is onboarded to the Git snapshot system.

        This is IDEMPOTENT - if already onboarded, returns immediately.

        Args:
            tenant_id: Tenant identifier
            env_id: Environment identifier
            user_id: User ID initiating onboarding
            blocking: If True, waits for completion. If False, runs async.

        Returns:
            OnboardingResult with success status and details

        Raises:
            OnboardingConflictError: If onboarding is already in progress
            ValueError: If environment not found or not configured
        """
        # Check if already onboarded (idempotent)
        is_onboarded, _ = await git_snapshot_service.is_env_onboarded(tenant_id, env_id)
        if is_onboarded:
            logger.info(f"Environment {env_id} is already onboarded")
            return OnboardingResult(
                success=True,
                already_onboarded=True,
            )

        # Get environment config
        env_config = await self.db.get_environment(env_id, tenant_id)
        if not env_config:
            raise ValueError(f"Environment {env_id} not found")

        env_name = env_config.get("n8n_name", env_id)
        env_type = env_config.get("n8n_type")

        if not env_type:
            raise ValueError(
                f"Environment {env_name} must have n8n_type configured for onboarding"
            )

        if not env_config.get("git_repo_url") or not env_config.get("git_pat"):
            raise ValueError(
                f"Environment {env_name} must have Git configured for onboarding"
            )

        # Acquire lock
        if not await self._acquire_lock(env_id):
            raise OnboardingConflictError(env_id, env_name)

        try:
            logger.info(f"Starting onboarding for environment {env_name} ({env_id})")

            # Execute onboarding
            result = await self._execute_onboarding(
                tenant_id=tenant_id,
                env_id=env_id,
                env_config=env_config,
                user_id=user_id,
            )

            return result

        finally:
            await self._release_lock(env_id)

    async def _execute_onboarding(
        self,
        tenant_id: str,
        env_id: str,
        env_config: Dict[str, Any],
        user_id: Optional[str],
    ) -> OnboardingResult:
        """
        Execute the onboarding process for an environment.

        Steps:
        1. Export all workflows from runtime
        2. Create onboarding snapshot
        3. Commit snapshot to Git
        4. Create env pointer
        5. Commit pointer
        6. Verify runtime matches snapshot
        """
        env_name = env_config.get("n8n_name", env_id)
        env_type = env_config.get("n8n_type")

        try:
            # Step 1: Export all workflows from runtime
            logger.info(f"Onboarding {env_name}: Exporting workflows from runtime...")

            adapter = ProviderRegistry.get_adapter_for_environment(env_config)
            workflow_list = await adapter.get_workflows()

            if not workflow_list:
                logger.warning(f"Onboarding {env_name}: No workflows found in environment")
                # Still create snapshot with empty workflows
                workflow_list = []

            # Get full workflow data for each workflow
            workflows: Dict[str, Dict[str, Any]] = {}
            for wf in workflow_list:
                workflow_id = wf.get("id")
                if workflow_id:
                    try:
                        full_workflow = await adapter.get_workflow(workflow_id)
                        workflows[workflow_id] = full_workflow
                    except Exception as e:
                        logger.warning(
                            f"Onboarding {env_name}: Failed to get workflow {workflow_id}: {e}"
                        )

            logger.info(f"Onboarding {env_name}: Exported {len(workflows)} workflows")

            # Step 2-3: Create onboarding snapshot and commit to Git
            logger.info(f"Onboarding {env_name}: Creating onboarding snapshot...")

            snapshot_id, commit_sha = await git_snapshot_service.create_snapshot(
                tenant_id=tenant_id,
                target_env_id=env_id,
                workflows=workflows,
                kind=SnapshotKind.ONBOARDING,
                source_env=None,
                created_by=user_id,
                reason=f"Initial onboarding for {env_name}",
            )

            logger.info(
                f"Onboarding {env_name}: Created snapshot {snapshot_id} at {commit_sha}"
            )

            # Step 4-5: Create env pointer and commit
            logger.info(f"Onboarding {env_name}: Updating environment pointer...")

            pointer_commit = await git_snapshot_service.update_env_pointer(
                tenant_id=tenant_id,
                env_id=env_id,
                snapshot_id=snapshot_id,
                snapshot_commit=commit_sha,
                updated_by=user_id,
            )

            logger.info(
                f"Onboarding {env_name}: Updated pointer at {pointer_commit}"
            )

            # Step 6: Verify runtime matches snapshot (optional, log warning if mismatch)
            logger.info(f"Onboarding {env_name}: Verifying snapshot...")

            matches, mismatches = await git_snapshot_service.verify_runtime_matches_snapshot(
                tenant_id=tenant_id,
                env_id=env_id,
                snapshot_workflows=workflows,
            )

            if not matches:
                logger.warning(
                    f"Onboarding {env_name}: Verification found mismatches: {mismatches}"
                )
            else:
                logger.info(f"Onboarding {env_name}: Verification successful")

            logger.info(f"Onboarding {env_name}: Complete!")

            return OnboardingResult(
                success=True,
                snapshot_id=snapshot_id,
                commit_sha=commit_sha,
                workflows_count=len(workflows),
            )

        except Exception as e:
            logger.error(f"Onboarding {env_name} failed: {str(e)}")
            return OnboardingResult(
                success=False,
                error=str(e),
            )

    async def trigger_onboarding_async(
        self,
        tenant_id: str,
        env_id: str,
        user_id: Optional[str] = None,
    ) -> None:
        """
        Trigger onboarding asynchronously (fire and forget).

        Used for env connect/test triggers where blocking is not required.
        Failures are logged but not raised.
        """
        try:
            # Create background task
            asyncio.create_task(
                self._async_onboarding_wrapper(tenant_id, env_id, user_id)
            )
            logger.info(f"Triggered async onboarding for environment {env_id}")
        except Exception as e:
            logger.warning(f"Failed to trigger async onboarding for {env_id}: {e}")

    async def _async_onboarding_wrapper(
        self,
        tenant_id: str,
        env_id: str,
        user_id: Optional[str],
    ) -> None:
        """Wrapper for async onboarding that handles errors gracefully."""
        try:
            result = await self.ensure_environment_onboarded(
                tenant_id=tenant_id,
                env_id=env_id,
                user_id=user_id,
                blocking=True,
            )
            if result.success:
                logger.info(
                    f"Async onboarding completed for {env_id}: "
                    f"snapshot={result.snapshot_id}, workflows={result.workflows_count}"
                )
            else:
                logger.warning(f"Async onboarding failed for {env_id}: {result.error}")
        except OnboardingConflictError:
            logger.info(f"Async onboarding skipped for {env_id}: already in progress")
        except Exception as e:
            logger.error(f"Async onboarding error for {env_id}: {str(e)}")


# Singleton instance
onboarding_service = OnboardingService()
