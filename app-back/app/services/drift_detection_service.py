"""
Drift Detection Service - Centralized environment-level drift detection

Compares all workflows in an environment against their GitHub source of truth
and updates environment drift status.
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

from github import GithubException

from app.services.database import db_service
from app.services.provider_registry import ProviderRegistry
from app.services.github_service import GitHubService
from app.services.diff_service import compare_workflows, DriftResult

logger = logging.getLogger(__name__)


class DriftStatus:
    """Drift status constants — Authoritative Environment State Reference.

    SCENARIO MAPPING (aligned with Environment State Scenarios checklist):
    ┌────┬─────────────────────────┬──────────────────┬────────────────────────┐
    │ #  │ Scenario Description    │ Backend State    │ UI Label               │
    ├────┼─────────────────────────┼──────────────────┼────────────────────────┤
    │ 1  │ Empty environment       │ UNKNOWN          │ "Empty" (via helper)   │
    │ 2  │ Git only (nothing dep.) │ DEPLOY_MISSING   │ "Deploy needed"        │
    │ 3  │ n8n only (unmanaged)    │ UNMANAGED        │ "Unmanaged"            │
    │ 4  │ Git + n8n (in sync)     │ IN_SYNC          │ "Matches baseline/app" │
    │ 5  │ Git + n8n (drifted)     │ DRIFT_DETECTED   │ "Drift detected"       │
    │ 6  │ Git missing (prev. mgd) │ GIT_UNAVAILABLE  │ "Git unavailable"      │
    │ 7  │ Git exists, n8n empty   │ DEPLOY_MISSING   │ "Deploy needed"        │
    │ 8  │ Mixed managed+unmanaged │ (flag) is_partial│ "{N} unmanaged" badge  │
    │ 9  │ DEV managed             │ IN_SYNC/DRIFT    │ secondary variant      │
    │ 10 │ STAGING/PROD managed    │ IN_SYNC/DRIFT    │ destructive variant    │
    └────┴─────────────────────────┴──────────────────┴────────────────────────┘

    DESIGN DECISIONS:
    - GIT_UNAVAILABLE covers ALL repo access failures (401/403/404)
      User action is the same: check repository URL and credentials.
    - Scenario #8 (PARTIAL_MANAGEMENT) is a summary flag, not a distinct state.
      Drift status reflects LINKED workflows only; unmanaged_count shown separately.
    - Scenarios #9/#10 share states with #4/#5; differentiation is UI-only via
      environmentClass (DEV vs non-DEV).
    """
    # Scenario #1: Empty environment (no Git, no workflows)
    UNKNOWN = "UNKNOWN"

    # Scenarios #4, #9, #10: Managed environment, runtime matches baseline
    IN_SYNC = "IN_SYNC"

    # Scenarios #5, #9, #10: Managed environment, runtime differs from baseline
    DRIFT_DETECTED = "DRIFT_DETECTED"

    # Environment-level only: no baseline exists (Git configured but not onboarded)
    NEW = "NEW"

    # Scenario #6: Git repo inaccessible (401/403/404) - previously managed, now broken
    GIT_UNAVAILABLE = "GIT_UNAVAILABLE"

    # System error during drift detection
    ERROR = "ERROR"

    # Scenarios #2, #7: Git has workflows, n8n runtime is empty - needs deployment
    DEPLOY_MISSING = "DEPLOY_MISSING"

    # Scenario #3: Git not configured, but workflows exist in n8n
    UNMANAGED = "UNMANAGED"


@dataclass
class WorkflowDriftInfo:
    """Drift info for a single workflow"""
    workflow_id: str
    workflow_name: str
    active: bool
    has_drift: bool
    not_in_git: bool
    drift_type: str  # 'none', 'modified', 'added_in_runtime', 'missing_from_runtime'
    nodes_added: int = 0
    nodes_removed: int = 0
    nodes_modified: int = 0
    connections_changed: bool = False
    settings_changed: bool = False


@dataclass
class EnvironmentDriftSummary:
    """Complete drift summary for an environment"""
    total_workflows: int
    in_sync: int
    with_drift: int
    not_in_git: int
    git_configured: bool
    last_detected_at: str
    affected_workflows: List[Dict[str, Any]]
    missing_from_runtime: int = 0  # Workflows in Git but not in n8n
    error: Optional[str] = None
    # P0 FIX: Flag for environments with both LINKED and UNMAPPED workflows
    is_partially_managed: bool = False
    unmanaged_count: int = 0  # Count of UNMAPPED workflows (for UI display)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "totalWorkflows": self.total_workflows,
            "inSync": self.in_sync,
            "withDrift": self.with_drift,
            "notInGit": self.not_in_git,
            "missingFromRuntime": self.missing_from_runtime,
            "gitConfigured": self.git_configured,
            "lastDetectedAt": self.last_detected_at,
            "affectedWorkflows": self.affected_workflows,
            "error": self.error,
            "isPartiallyManaged": self.is_partially_managed,
            "unmanagedCount": self.unmanaged_count
        }


class DriftDetectionService:
    """Service for detecting and managing drift between environments and GitHub"""

    async def detect_drift(
        self,
        tenant_id: str,
        environment_id: str,
        update_status: bool = True
    ) -> EnvironmentDriftSummary:
        """
        Detect drift for all workflows in an environment.

        Args:
            tenant_id: The tenant ID
            environment_id: The environment to check
            update_status: Whether to update the environment's drift_status in DB

        Returns:
            EnvironmentDriftSummary with detailed drift information
        """
        try:
            # Get environment details
            environment = await db_service.get_environment(environment_id, tenant_id)
            if not environment:
                return EnvironmentDriftSummary(
                    total_workflows=0,
                    in_sync=0,
                    with_drift=0,
                    not_in_git=0,
                    git_configured=False,
                    last_detected_at=datetime.utcnow().isoformat(),
                    affected_workflows=[],
                    error="Environment not found"
                )

            # Check if GitHub is configured
            if not environment.get("git_repo_url") or not environment.get("git_pat"):
                workflow_count = environment.get("workflow_count", 0)

                # P1 DELTA FIX: Distinguish EMPTY from UNMANAGED
                # EMPTY = no Git, no workflows
                # UNMANAGED = no Git, but workflows exist
                if workflow_count > 0:
                    drift_status = DriftStatus.UNMANAGED
                    error_msg = None  # Not an error - just unmanaged state
                else:
                    drift_status = DriftStatus.UNKNOWN
                    error_msg = "GitHub is not configured for this environment"

                summary = EnvironmentDriftSummary(
                    total_workflows=workflow_count,
                    in_sync=0,
                    with_drift=0,
                    not_in_git=0,
                    git_configured=False,
                    last_detected_at=datetime.utcnow().isoformat(),
                    affected_workflows=[],
                    error=error_msg
                )

                if update_status:
                    await self._update_environment_drift_status(
                        tenant_id, environment_id, drift_status, summary
                    )

                return summary

            # CRITICAL: Environment state gate - must execute BEFORE any drift logic
            # Check if environment is onboarded (has valid baseline)
            from app.services.git_snapshot_service import git_snapshot_service
            is_onboarded, onboard_reason = await git_snapshot_service.is_env_onboarded(tenant_id, environment_id)

            if not is_onboarded:
                # Determine status based on reason:
                # - "new" / "no_git_config" → DriftStatus.NEW
                # - "git_unavailable" → DriftStatus.GIT_UNAVAILABLE
                # - "invalid_pointer" → DriftStatus.ERROR
                if onboard_reason == "git_unavailable":
                    drift_status = DriftStatus.GIT_UNAVAILABLE
                    error_msg = "Git repository is unavailable"
                elif onboard_reason == "invalid_pointer":
                    drift_status = DriftStatus.ERROR
                    error_msg = "Baseline pointer references missing snapshot"
                else:
                    # "new", "no_git_config", "env_not_found" → NEW
                    drift_status = DriftStatus.NEW
                    error_msg = None

                summary = EnvironmentDriftSummary(
                    total_workflows=environment.get("workflow_count", 0),
                    in_sync=0,
                    with_drift=0,
                    not_in_git=0,
                    git_configured=True,
                    last_detected_at=datetime.utcnow().isoformat(),
                    affected_workflows=[],  # Empty - no comparison possible
                    error=error_msg
                )
                if update_status:
                    await self._update_environment_drift_status(
                        tenant_id, environment_id, drift_status, summary
                    )
                return summary

            # Create provider adapter
            adapter = ProviderRegistry.get_adapter_for_environment(environment)

            # Create GitHub service
            repo_url = environment.get("git_repo_url", "").rstrip('/').replace('.git', '')
            repo_parts = repo_url.split("/")
            github_service = GitHubService(
                token=environment.get("git_pat"),
                repo_owner=repo_parts[-2] if len(repo_parts) >= 2 else "",
                repo_name=repo_parts[-1] if len(repo_parts) >= 1 else "",
                branch=environment.get("git_branch", "main")
            )

            if not github_service.is_configured():
                summary = EnvironmentDriftSummary(
                    total_workflows=environment.get("workflow_count", 0),
                    in_sync=0,
                    with_drift=0,
                    not_in_git=0,
                    git_configured=False,
                    last_detected_at=datetime.utcnow().isoformat(),
                    affected_workflows=[],
                    error="GitHub is not properly configured"
                )

                if update_status:
                    await self._update_environment_drift_status(
                        tenant_id, environment_id, DriftStatus.UNKNOWN, summary
                    )

                return summary

            # Fetch all workflows from provider
            try:
                runtime_workflows = await adapter.get_workflows()
            except Exception as e:
                logger.error(f"Failed to fetch workflows from provider: {e}")
                summary = EnvironmentDriftSummary(
                    total_workflows=0,
                    in_sync=0,
                    with_drift=0,
                    not_in_git=0,
                    git_configured=True,
                    last_detected_at=datetime.utcnow().isoformat(),
                    affected_workflows=[],
                    error=f"Failed to fetch workflows from provider: {str(e)}"
                )

                if update_status:
                    await self._update_environment_drift_status(
                        tenant_id, environment_id, DriftStatus.ERROR, summary
                    )

                return summary

            # Fetch all workflows from GitHub
            env_type = environment.get("n8n_type")
            if not env_type:
                summary = EnvironmentDriftSummary(
                    total_workflows=len(runtime_workflows),
                    in_sync=0,
                    with_drift=0,
                    not_in_git=0,
                    git_configured=True,
                    last_detected_at=datetime.utcnow().isoformat(),
                    affected_workflows=[],
                    error="Environment type is required for drift detection"
                )

                if update_status:
                    await self._update_environment_drift_status(
                        tenant_id, environment_id, DriftStatus.ERROR, summary
                    )

                return summary

            try:
                git_workflows_map = await github_service.get_all_workflows_from_github(environment_type=env_type)
            except GithubException as e:
                # P1 FIX: Distinguish GIT_UNAVAILABLE from generic ERROR
                is_unavailable = e.status in (403, 404, 401)
                error_status = DriftStatus.GIT_UNAVAILABLE if is_unavailable else DriftStatus.ERROR
                error_msg = (
                    f"Git repository unavailable (HTTP {e.status}): {e.data.get('message', str(e))}"
                    if is_unavailable
                    else f"GitHub error: {str(e)}"
                )
                logger.error(f"GitHub error for environment {environment_id}: {error_msg}")
                summary = EnvironmentDriftSummary(
                    total_workflows=len(runtime_workflows),
                    in_sync=0,
                    with_drift=0,
                    not_in_git=0,
                    git_configured=True,
                    last_detected_at=datetime.utcnow().isoformat(),
                    affected_workflows=[],
                    error=error_msg
                )

                if update_status:
                    await self._update_environment_drift_status(
                        tenant_id, environment_id, error_status, summary
                    )

                return summary
            except Exception as e:
                logger.error(f"Failed to fetch workflows from GitHub: {e}")
                summary = EnvironmentDriftSummary(
                    total_workflows=len(runtime_workflows),
                    in_sync=0,
                    with_drift=0,
                    not_in_git=0,
                    git_configured=True,
                    last_detected_at=datetime.utcnow().isoformat(),
                    affected_workflows=[],
                    error=f"Failed to fetch workflows from GitHub: {str(e)}"
                )

                if update_status:
                    await self._update_environment_drift_status(
                        tenant_id, environment_id, DriftStatus.ERROR, summary
                    )

                return summary

            # Create map of git workflows by name
            git_by_name = {}
            for wf_id, gw in git_workflows_map.items():
                name = gw.get("name", "")
                if name:
                    git_by_name[name] = gw

            # P0 DELTA FIX: Get LINKED workflow mappings for this environment
            # Only LINKED workflows participate in drift detection
            linked_workflow_ids = await self._get_linked_workflow_ids(
                tenant_id, environment_id
            )
            # If no mappings exist yet, treat all runtime workflows as candidates
            # (backward compatibility for environments without mapping data)
            has_mapping_data = linked_workflow_ids is not None
            linked_set = set(linked_workflow_ids) if linked_workflow_ids else None

            # Compare each runtime workflow
            affected_workflows = []
            unmanaged_workflows = []  # Track separately, don't influence drift
            in_sync_count = 0
            with_drift_count = 0
            not_in_git_count = 0  # Only counts LINKED workflows not in Git

            for runtime_wf in runtime_workflows:
                wf_name = runtime_wf.get("name", "")
                wf_id = runtime_wf.get("id", "")
                active = runtime_wf.get("active", False)

                # P0 DELTA FIX: Check if workflow is LINKED (managed)
                # If has_mapping_data is True but workflow not in linked_set, it's UNMAPPED
                is_linked = (not has_mapping_data) or (wf_id in linked_set)

                git_entry = git_by_name.get(wf_name)

                if not is_linked:
                    # UNMAPPED workflow - track separately, does NOT influence drift
                    unmanaged_workflows.append({
                        "id": wf_id,
                        "name": wf_name,
                        "active": active,
                        "hasDrift": False,
                        "notInGit": git_entry is None,
                        "driftType": "unmapped",
                        "mappingStatus": "unmapped"
                    })
                    continue  # Skip drift calculation for unmapped workflows

                # LINKED workflow - participates in drift detection
                if git_entry is None:
                    # LINKED but not in Git - this is drift (added locally)
                    not_in_git_count += 1
                    affected_workflows.append({
                        "id": wf_id,
                        "name": wf_name,
                        "active": active,
                        "hasDrift": False,
                        "notInGit": True,
                        "driftType": "added_in_runtime",
                        "mappingStatus": "linked"
                    })
                else:
                    # Compare workflows
                    drift_result = compare_workflows(
                        git_workflow=git_entry,
                        runtime_workflow=runtime_wf
                    )

                    if drift_result.has_drift:
                        with_drift_count += 1
                        affected_workflows.append({
                            "id": wf_id,
                            "name": wf_name,
                            "active": active,
                            "hasDrift": True,
                            "notInGit": False,
                            "driftType": "modified",
                            "mappingStatus": "linked",
                            "summary": {
                                "nodesAdded": drift_result.summary.nodes_added,
                                "nodesRemoved": drift_result.summary.nodes_removed,
                                "nodesModified": drift_result.summary.nodes_modified,
                                "connectionsChanged": drift_result.summary.connections_changed,
                                "settingsChanged": drift_result.summary.settings_changed
                            },
                            "differenceCount": len(drift_result.differences)
                        })
                    else:
                        in_sync_count += 1

            # P0 FIX: Detect LINKED workflows in Git but missing from n8n runtime
            # This catches workflows that were deployed but later deleted from n8n
            runtime_names = {wf.get("name", "") for wf in runtime_workflows}
            missing_from_runtime_count = 0
            for git_name, git_wf in git_by_name.items():
                if git_name and git_name not in runtime_names:
                    # Workflow exists in Git baseline but not in n8n runtime
                    missing_from_runtime_count += 1
                    affected_workflows.append({
                        "id": f"git-{git_name}",  # Synthetic ID for Git-only workflows
                        "name": git_name,
                        "active": False,
                        "hasDrift": True,
                        "notInGit": False,
                        "driftType": "missing_from_runtime",
                        "mappingStatus": "linked",  # If in Git baseline, it was managed
                        "gitPath": git_wf.get("path", "")
                    })

            # Determine overall status based on drift detection
            # (NEW environments are already short-circuited above)

            # P1 DELTA FIX: Check for DEPLOY_MISSING scenario
            # DEPLOY_MISSING = Git has workflows, but n8n runtime is empty
            # This is NOT drift - it's a deployment-needed state (no incidents, deploy action)
            if len(runtime_workflows) == 0 and missing_from_runtime_count > 0:
                drift_status = DriftStatus.DEPLOY_MISSING
            else:
                has_drift = with_drift_count > 0 or not_in_git_count > 0 or missing_from_runtime_count > 0
                drift_status = DriftStatus.DRIFT_DETECTED if has_drift else DriftStatus.IN_SYNC

            # Sort affected workflows: drift first, then missing_from_runtime, then not_in_git
            affected_workflows.sort(key=lambda x: (
                0 if x.get("hasDrift") and x.get("driftType") == "modified" else (
                    1 if x.get("driftType") == "missing_from_runtime" else (
                        2 if x.get("notInGit") else 3
                    )
                ),
                x.get("name", "").lower()
            ))

            # Total workflows includes both runtime and Git-only workflows
            total_workflow_count = len(runtime_workflows) + missing_from_runtime_count

            # P0 FIX: Determine if environment is partially managed
            # An environment is partially managed when it has:
            # - At least one LINKED workflow (or uses backward compat mode)
            # - AND at least one UNMAPPED workflow
            unmanaged_count = len(unmanaged_workflows)
            has_managed_workflows = in_sync_count > 0 or with_drift_count > 0 or not_in_git_count > 0 or missing_from_runtime_count > 0
            is_partially_managed = has_managed_workflows and unmanaged_count > 0

            summary = EnvironmentDriftSummary(
                total_workflows=total_workflow_count,
                in_sync=in_sync_count,
                with_drift=with_drift_count,
                not_in_git=not_in_git_count,
                git_configured=True,
                last_detected_at=datetime.utcnow().isoformat(),
                affected_workflows=affected_workflows,
                missing_from_runtime=missing_from_runtime_count,
                is_partially_managed=is_partially_managed,
                unmanaged_count=unmanaged_count
            )

            if update_status:
                await self._update_environment_drift_status(
                    tenant_id, environment_id, drift_status, summary
                )

            return summary

        except Exception as e:
            logger.error(f"Failed to detect drift for environment {environment_id}: {e}")
            summary = EnvironmentDriftSummary(
                total_workflows=0,
                in_sync=0,
                with_drift=0,
                not_in_git=0,
                git_configured=False,
                last_detected_at=datetime.utcnow().isoformat(),
                affected_workflows=[],
                error=str(e)
            )

            if update_status:
                await self._update_environment_drift_status(
                    tenant_id, environment_id, DriftStatus.ERROR, summary
                )

            return summary

    async def get_cached_drift_status(
        self,
        tenant_id: str,
        environment_id: str
    ) -> Dict[str, Any]:
        """
        Get the cached drift status for an environment without running detection.

        Returns the last known drift status from the database.
        """
        environment = await db_service.get_environment(environment_id, tenant_id)
        if not environment:
            return {
                "driftStatus": DriftStatus.UNKNOWN,
                "lastDriftDetectedAt": None,
                "summary": None
            }

        return {
            "driftStatus": environment.get("drift_status", DriftStatus.UNKNOWN),
            "lastDriftDetectedAt": environment.get("last_drift_detected_at"),
            "activeDriftIncidentId": environment.get("active_drift_incident_id"),
            "summary": None  # Summary not cached in environment table for now
        }

    async def _get_linked_workflow_ids(
        self,
        tenant_id: str,
        environment_id: str,
    ) -> Optional[List[str]]:
        """
        Get list of LINKED workflow IDs for an environment.

        P0 DELTA FIX: Only LINKED workflows participate in drift detection.
        UNMAPPED workflows do not influence drift status or trigger incidents.

        Returns:
            List of workflow IDs with status='linked', or None if no mapping data exists
        """
        try:
            result = db_service.client.table("workflow_env_map").select(
                "workflow_id"
            ).eq("tenant_id", tenant_id).eq(
                "environment_id", environment_id
            ).eq("status", "linked").execute()

            if result.data:
                return [r["workflow_id"] for r in result.data]

            # Check if ANY mappings exist (to distinguish "no data" from "all unmapped")
            any_result = db_service.client.table("workflow_env_map").select(
                "id", count="exact"
            ).eq("tenant_id", tenant_id).eq(
                "environment_id", environment_id
            ).limit(1).execute()

            if any_result.count and any_result.count > 0:
                # Mappings exist but none are linked
                return []
            else:
                # No mapping data at all - return None for backward compatibility
                return None

        except Exception as e:
            logger.warning(f"Failed to get linked workflows for {environment_id}: {e}")
            # On error, return None to allow drift detection to proceed
            return None

    async def _update_environment_drift_status(
        self,
        tenant_id: str,
        environment_id: str,
        drift_status: str,
        summary: EnvironmentDriftSummary
    ) -> None:
        """Update the environment's drift status in the database"""
        try:
            now = datetime.utcnow().isoformat()
            update_data = {
                "drift_status": drift_status,
                "last_drift_check_at": now
            }
            
            # Only update last_drift_detected_at if drift was actually detected
            if drift_status == DriftStatus.DRIFT_DETECTED:
                update_data["last_drift_detected_at"] = now

            await db_service.update_environment(environment_id, tenant_id, update_data)

            logger.info(
                f"Updated drift status for environment {environment_id}: "
                f"{drift_status} ({summary.with_drift} drifted, {summary.not_in_git} not in git)"
            )
        except Exception as e:
            logger.error(f"Failed to update drift status for environment {environment_id}: {e}")


# Singleton instance
drift_detection_service = DriftDetectionService()
