"""
Git Snapshot Service - Core snapshot operations with target-ownership model

This service handles:
- Snapshot creation with proper manifest generation
- Content hash computation (credential-agnostic)
- Snapshot verification against runtime
- Orchestration of snapshot operations

Key Rules:
- Snapshots are owned by TARGET environment
- Snapshots are immutable (append-only)
- Hash computation excludes env-specific fields (credential IDs, etc.)
"""
import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from uuid import uuid4

from app.services.github_service import GitHubService
from app.services.provider_registry import ProviderRegistry
from app.services.database import db_service
from app.schemas.snapshot_manifest import (
    SnapshotKind,
    SnapshotManifest,
    WorkflowFileEntry,
    EnvironmentPointer,
    generate_snapshot_id,
)

logger = logging.getLogger(__name__)


def normalize_workflow_for_hash(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize workflow data for hash computation.

    Removes/normalizes fields that vary between environments but don't
    represent actual workflow logic changes:
    - Credential IDs (compare by name only)
    - Timestamps (createdAt, updatedAt)
    - Runtime metadata (id, versionId, triggerCount, etc.)
    - UI-specific fields (position, pinData, etc.)

    This ensures the same workflow logic produces the same hash
    regardless of which environment it's in.
    """
    # Deep copy to avoid modifying original
    normalized = json.loads(json.dumps(workflow))

    # Fields to completely remove (metadata that varies per-env)
    remove_fields = [
        'id', 'createdAt', 'updatedAt', 'versionId',
        'triggerCount', 'staticData', 'meta', 'hash',
        'executionOrder', 'homeProject', 'sharedWithProjects',
        '_comment', 'pinData',
        'active',  # Active state may differ
        'tags', 'tagIds',  # Tags have different IDs per env
        'shared', 'scopes', 'usedCredentials',
    ]

    for field in remove_fields:
        normalized.pop(field, None)

    # Normalize settings - remove env-specific settings
    if 'settings' in normalized and isinstance(normalized['settings'], dict):
        settings_remove = [
            'executionOrder', 'saveDataErrorExecution', 'saveDataSuccessExecution',
            'callerPolicy', 'timezone', 'saveManualExecutions', 'availableInMCP',
        ]
        for field in settings_remove:
            normalized['settings'].pop(field, None)
        if not normalized['settings']:
            normalized.pop('settings', None)

    # Normalize nodes - remove UI/runtime data, normalize credentials
    if 'nodes' in normalized and isinstance(normalized['nodes'], list):
        for node in normalized['nodes']:
            # Remove UI/position fields
            ui_fields = [
                'position', 'positionAbsolute', 'selected', 'selectedNodes',
                'executionData', 'typeVersion', 'onError', 'id',
                'webhookId', 'extendsCredential', 'notesInFlow',
            ]
            for field in ui_fields:
                node.pop(field, None)

            # Normalize credentials - compare by NAME only, not ID
            if 'credentials' in node and isinstance(node['credentials'], dict):
                normalized_creds = {}
                for cred_type, cred_ref in node['credentials'].items():
                    if isinstance(cred_ref, dict):
                        # Keep only name for comparison
                        normalized_creds[cred_type] = {'name': cred_ref.get('name')}
                    else:
                        normalized_creds[cred_type] = cred_ref
                node['credentials'] = normalized_creds

        # Sort nodes by name for consistent ordering
        normalized['nodes'] = sorted(
            normalized['nodes'],
            key=lambda n: n.get('name', '')
        )

    return normalized


def compute_workflow_hash(workflow: Dict[str, Any]) -> str:
    """
    Compute SHA256 hash of normalized workflow content.

    Returns hash prefixed with 'sha256:' for clarity.
    """
    normalized = normalize_workflow_for_hash(workflow)
    json_str = json.dumps(normalized, sort_keys=True, separators=(',', ':'))
    hash_bytes = hashlib.sha256(json_str.encode('utf-8')).hexdigest()
    return f"sha256:{hash_bytes}"


def compute_overall_hash(workflow_hashes: List[str]) -> str:
    """
    Compute overall snapshot hash from individual workflow hashes.

    Sorts hashes for deterministic ordering.
    """
    sorted_hashes = sorted(workflow_hashes)
    combined = '\n'.join(sorted_hashes)
    hash_bytes = hashlib.sha256(combined.encode('utf-8')).hexdigest()
    return f"sha256:{hash_bytes}"


class GitSnapshotService:
    """
    Service for creating and managing Git-based snapshots.

    Implements the target-ownership model where snapshots are stored
    under the target environment's folder.
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

    async def create_snapshot(
        self,
        tenant_id: str,
        target_env_id: str,
        workflows: Dict[str, Dict[str, Any]],
        kind: SnapshotKind,
        source_env: Optional[str] = None,
        source_snapshot_id: Optional[str] = None,
        created_by: Optional[str] = None,
        reason: Optional[str] = None,
        promotion_id: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Create a snapshot in the target environment's Git folder.

        Args:
            tenant_id: Tenant identifier
            target_env_id: Target environment ID (snapshot owner)
            workflows: Dict mapping workflow_key to workflow_data
            kind: Type of snapshot (onboarding, promotion, backup)
            source_env: Source environment type (for promotions)
            source_snapshot_id: Source snapshot ID (for STAGING→PROD)
            created_by: User ID
            reason: Human-readable reason
            promotion_id: Associated promotion ID

        Returns:
            Tuple of (snapshot_id, git_commit_sha)

        Raises:
            ValueError: If Git not configured or commit fails
        """
        # Get target environment config
        target_env = await self.db.get_environment(target_env_id, tenant_id)
        if not target_env:
            raise ValueError(f"Target environment {target_env_id} not found")

        target_env_type = target_env.get("n8n_type")
        if not target_env_type:
            raise ValueError("Target environment must have n8n_type configured")

        if not target_env.get("git_repo_url") or not target_env.get("git_pat"):
            raise ValueError("Target environment must have Git configured")

        github_service = self._get_github_service(target_env)
        if not github_service.is_configured():
            raise ValueError("GitHub is not properly configured")

        # Generate snapshot ID
        snapshot_id = generate_snapshot_id()

        # Build workflow file entries with hashes
        workflow_entries = []
        workflow_hashes = []

        for workflow_key, workflow_data in workflows.items():
            content_hash = compute_workflow_hash(workflow_data)
            workflow_hashes.append(content_hash)

            workflow_entries.append({
                "workflow_key": workflow_key,
                "workflow_name": workflow_data.get("name", "Unknown"),
                "file_path": f"workflows/{workflow_key}.json",
                "content_hash": content_hash,
                "active": workflow_data.get("active", False),
            })

        # Compute overall hash
        overall_hash = compute_overall_hash(workflow_hashes)

        # Build manifest
        manifest = {
            "snapshot_id": snapshot_id,
            "kind": kind.value,
            "target_env": target_env_type,
            "source_env": source_env,
            "source_snapshot_id": source_snapshot_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": created_by,
            "workflows": workflow_entries,
            "workflows_count": len(workflows),
            "overall_hash": overall_hash,
            "reason": reason or f"{kind.value} snapshot",
            "promotion_id": promotion_id,
        }

        # Write snapshot to Git
        commit_message = f"Create {kind.value} snapshot {snapshot_id} for {target_env_type}"
        if reason:
            commit_message += f": {reason}"

        try:
            commit_sha = await github_service.write_snapshot(
                env_type=target_env_type,
                snapshot_id=snapshot_id,
                manifest=manifest,
                workflows=workflows,
                commit_message=commit_message
            )
        except Exception as e:
            logger.error(f"Failed to write snapshot to Git: {str(e)}")
            raise ValueError(f"Snapshot commit failed: {str(e)}")

        # Index snapshot in database (cache only)
        await self._index_snapshot_in_db(
            tenant_id=tenant_id,
            environment_id=target_env_id,
            snapshot_id=snapshot_id,
            commit_sha=commit_sha,
            manifest=manifest,
        )

        logger.info(f"Created {kind.value} snapshot {snapshot_id} for {target_env_type} at {commit_sha}")
        return snapshot_id, commit_sha

    async def _index_snapshot_in_db(
        self,
        tenant_id: str,
        environment_id: str,
        snapshot_id: str,
        commit_sha: str,
        manifest: Dict[str, Any],
    ) -> None:
        """
        Index snapshot metadata in database (cache/index only).

        DB is NOT authoritative - Git is. This is for query performance.
        """
        from app.schemas.deployment import SnapshotType

        # Map our SnapshotKind to existing SnapshotType for DB compatibility
        kind = manifest.get("kind", "backup")
        snapshot_type_map = {
            "onboarding": SnapshotType.AUTO_BACKUP.value,
            "promotion": SnapshotType.PRE_PROMOTION.value,
            "backup": SnapshotType.MANUAL_BACKUP.value,
            "rollback": SnapshotType.POST_PROMOTION.value,
        }
        db_type = snapshot_type_map.get(kind, SnapshotType.MANUAL_BACKUP.value)

        snapshot_data = {
            "id": snapshot_id,
            "tenant_id": tenant_id,
            "environment_id": environment_id,
            "git_commit_sha": commit_sha,
            "type": db_type,
            "created_by_user_id": manifest.get("created_by"),
            "related_deployment_id": None,
            "metadata_json": {
                "kind": kind,
                "source_env": manifest.get("source_env"),
                "source_snapshot_id": manifest.get("source_snapshot_id"),
                "workflows_count": manifest.get("workflows_count"),
                "overall_hash": manifest.get("overall_hash"),
                "reason": manifest.get("reason"),
                "promotion_id": manifest.get("promotion_id"),
            },
        }

        try:
            await self.db.create_snapshot(snapshot_data)
        except Exception as e:
            # Don't fail if DB indexing fails - Git is authoritative
            logger.warning(f"Failed to index snapshot in DB (non-fatal): {str(e)}")

    async def update_env_pointer(
        self,
        tenant_id: str,
        env_id: str,
        snapshot_id: str,
        snapshot_commit: str,
        updated_by: Optional[str] = None,
    ) -> str:
        """
        Update environment pointer AFTER successful deploy + verify.

        Args:
            tenant_id: Tenant ID
            env_id: Environment ID
            snapshot_id: Snapshot ID to point to
            snapshot_commit: Git commit SHA of the snapshot
            updated_by: User ID

        Returns:
            Git commit SHA of the pointer update
        """
        env_config = await self.db.get_environment(env_id, tenant_id)
        if not env_config:
            raise ValueError(f"Environment {env_id} not found")

        env_type = env_config.get("n8n_type")
        if not env_type:
            raise ValueError("Environment must have n8n_type configured")

        github_service = self._get_github_service(env_config)

        return await github_service.write_env_pointer(
            env_type=env_type,
            snapshot_id=snapshot_id,
            snapshot_commit=snapshot_commit,
            updated_by=updated_by,
        )

    async def is_env_onboarded(
        self,
        tenant_id: str,
        env_id: str,
    ) -> Tuple[bool, str]:
        """
        Check if environment is onboarded (has valid baseline).

        Returns:
            Tuple of (is_onboarded, reason) where reason is one of:
            - "onboarded" - Has valid baseline
            - "new" - No baseline exists (no current.json or pointer)
            - "git_unavailable" - Cannot access Git repo (403/404/network error)
            - "no_git_config" - Git not configured for this environment
            - "env_not_found" - Environment record doesn't exist
            - "invalid_pointer" - current.json exists but points to missing snapshot
        """
        from github import GithubException

        env_config = await self.db.get_environment(env_id, tenant_id)
        if not env_config:
            return (False, "env_not_found")

        env_type = env_config.get("n8n_type")
        if not env_type:
            return (False, "no_git_config")

        if not env_config.get("git_repo_url"):
            return (False, "no_git_config")

        github_service = self._get_github_service(env_config)

        # Check if pointer exists
        try:
            if not await github_service.env_is_onboarded(env_type):
                return (False, "new")
        except GithubException as e:
            if e.status in (403, 404, 401):
                return (False, "git_unavailable")
            raise
        except Exception as e:
            logger.warning(f"Failed to check onboarding for env {env_id}: {e}")
            return (False, "git_unavailable")

        # Validate pointer resolves to valid snapshot
        try:
            pointer = await github_service.read_env_pointer(env_type)
            if not pointer or not pointer.get("current_snapshot_id"):
                return (False, "new")

            snapshot_id = pointer["current_snapshot_id"]

            # Verify snapshot manifest exists and is readable
            manifest = await github_service.read_snapshot_manifest(env_type, snapshot_id)
            if not manifest:
                return (False, "invalid_pointer")

            return (True, "onboarded")
        except GithubException as e:
            if e.status in (403, 404, 401):
                return (False, "git_unavailable")
            logger.warning(f"GitHub error validating baseline for env {env_id}: {e}")
            return (False, "git_unavailable")
        except Exception as e:
            logger.warning(f"Failed to validate baseline for env {env_id}: {e}")
            return (False, "git_unavailable")

    async def get_current_snapshot_id(
        self,
        tenant_id: str,
        env_id: str,
    ) -> Optional[str]:
        """
        Get the current snapshot ID from environment pointer.

        Returns:
            Snapshot ID or None if environment is NEW
        """
        env_config = await self.db.get_environment(env_id, tenant_id)
        if not env_config:
            return None

        env_type = env_config.get("n8n_type")
        if not env_type or not env_config.get("git_repo_url"):
            return None

        github_service = self._get_github_service(env_config)
        pointer = await github_service.read_env_pointer(env_type)

        if pointer:
            return pointer.get("current_snapshot_id")
        return None

    async def get_current_pointer(
        self,
        tenant_id: str,
        env_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get the full current pointer for an environment.

        Returns:
            Full pointer dict or None if environment is NEW
        """
        env_config = await self.db.get_environment(env_id, tenant_id)
        if not env_config:
            return None

        env_type = env_config.get("n8n_type")
        if not env_type or not env_config.get("git_repo_url"):
            return None

        github_service = self._get_github_service(env_config)
        return await github_service.read_env_pointer(env_type)

    async def get_snapshot_content(
        self,
        tenant_id: str,
        env_id: str,
        snapshot_id: str,
    ) -> Tuple[Optional[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """
        Get snapshot manifest and workflow content from Git.

        Returns:
            Tuple of (manifest, workflows_dict)
        """
        env_config = await self.db.get_environment(env_id, tenant_id)
        if not env_config:
            return None, {}

        env_type = env_config.get("n8n_type")
        if not env_type or not env_config.get("git_repo_url"):
            return None, {}

        github_service = self._get_github_service(env_config)

        manifest = await github_service.read_snapshot_manifest(env_type, snapshot_id)
        workflows = await github_service.read_snapshot_workflows(env_type, snapshot_id)

        return manifest, workflows

    async def verify_runtime_matches_snapshot(
        self,
        tenant_id: str,
        env_id: str,
        snapshot_workflows: Dict[str, Dict[str, Any]],
    ) -> Tuple[bool, List[str]]:
        """
        Verify that runtime workflows match snapshot content.

        Compares by content hash to ensure deployed workflows match expected state.

        Returns:
            Tuple of (matches, list_of_mismatches)
        """
        env_config = await self.db.get_environment(env_id, tenant_id)
        if not env_config:
            return False, ["Environment not found"]

        adapter = ProviderRegistry.get_adapter_for_environment(env_config)

        mismatches = []

        for workflow_key, expected_workflow in snapshot_workflows.items():
            try:
                # Fetch runtime workflow
                runtime_workflow = await adapter.get_workflow(workflow_key)

                # Compare hashes
                expected_hash = compute_workflow_hash(expected_workflow)
                runtime_hash = compute_workflow_hash(runtime_workflow)

                if expected_hash != runtime_hash:
                    mismatches.append(
                        f"Workflow {workflow_key} hash mismatch: "
                        f"expected {expected_hash[:20]}..., got {runtime_hash[:20]}..."
                    )
            except Exception as e:
                mismatches.append(f"Workflow {workflow_key}: {str(e)}")

        return len(mismatches) == 0, mismatches

    async def list_snapshots(
        self,
        tenant_id: str,
        env_id: str,
    ) -> List[Dict[str, Any]]:
        """
        List all snapshots for an environment (for history/rollback UI).

        Returns:
            List of snapshot summaries
        """
        env_config = await self.db.get_environment(env_id, tenant_id)
        if not env_config:
            return []

        env_type = env_config.get("n8n_type")
        if not env_type or not env_config.get("git_repo_url"):
            return []

        github_service = self._get_github_service(env_config)
        return await github_service.get_snapshot_list(env_type)


# Singleton instance
git_snapshot_service = GitSnapshotService()
