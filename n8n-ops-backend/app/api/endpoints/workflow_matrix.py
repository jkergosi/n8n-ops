"""
API endpoint for workflow × environment matrix (read-only).

This endpoint provides a single read-only API that returns the full workflow × environment
matrix with backend-computed status for each cell. The UI must not infer or compute status logic.

Status Semantics (MVP):
- Linked: Canonical workflow is mapped to the environment and in sync
- Untracked: Workflow exists in the environment but has no canonical mapping
- Drift: Canonical mapping exists, but the environment version differs from canonical
- Out-of-date: Canonical version is newer than the version deployed to the environment
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import logging

from app.services.database import db_service
from app.core.entitlements_gate import require_entitlement
from app.services.auth_service import get_current_user
from app.schemas.environment import EnvironmentClass

logger = logging.getLogger(__name__)

router = APIRouter()


# Response Models

class WorkflowEnvironmentStatus(str, Enum):
    """Status of a canonical workflow in a specific environment."""
    LINKED = "linked"
    UNTRACKED = "untracked"
    DRIFT = "drift"
    OUT_OF_DATE = "out_of_date"


class WorkflowMatrixCell(BaseModel):
    """Represents a single cell in the workflow × environment matrix."""
    status: WorkflowEnvironmentStatus
    can_sync: bool = Field(alias="canSync", serialization_alias="canSync")
    n8n_workflow_id: Optional[str] = Field(default=None, alias="n8nWorkflowId", serialization_alias="n8nWorkflowId")
    content_hash: Optional[str] = Field(default=None, alias="contentHash", serialization_alias="contentHash")

    model_config = {"populate_by_name": True}


class WorkflowMatrixEnvironment(BaseModel):
    """Environment metadata for matrix columns."""
    id: str
    name: str
    type: Optional[str] = None
    environment_class: EnvironmentClass = Field(alias="environmentClass", serialization_alias="environmentClass")

    model_config = {"populate_by_name": True}


class WorkflowMatrixRow(BaseModel):
    """Canonical workflow metadata for matrix rows."""
    canonical_id: str = Field(alias="canonicalId", serialization_alias="canonicalId")
    display_name: str = Field(alias="displayName", serialization_alias="displayName")
    created_at: datetime = Field(alias="createdAt", serialization_alias="createdAt")

    model_config = {"populate_by_name": True}


class WorkflowMatrixResponse(BaseModel):
    """Complete matrix response from the backend."""
    workflows: List[WorkflowMatrixRow]
    environments: List[WorkflowMatrixEnvironment]
    matrix: Dict[str, Dict[str, Optional[WorkflowMatrixCell]]]


def get_tenant_id(user_info: dict) -> str:
    """Extract tenant_id from user_info with proper error handling."""
    tenant = user_info.get("tenant") or {}
    tenant_id = tenant.get("id")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return tenant_id


async def _compute_cell_status(
    mapping: Optional[Dict[str, Any]],
    git_state: Optional[Dict[str, Any]]
) -> tuple[WorkflowEnvironmentStatus, bool]:
    """
    Compute the status for a workflow in an environment.

    Returns tuple of (status, can_sync).

    Status logic:
    - linked: Mapping exists, status is "linked", and hashes match
    - untracked: Mapping status is "untracked" (workflow exists but not canonically mapped)
    - drift: Mapping exists but env_content_hash differs from git_content_hash
    - out_of_date: Like drift, but specifically when we know git has a newer version
    """
    if not mapping:
        # No mapping means the workflow doesn't exist in this environment
        return None, False

    mapping_status = mapping.get("status")
    env_content_hash = mapping.get("env_content_hash")
    git_content_hash = git_state.get("git_content_hash") if git_state else None

    # Untracked: workflow exists but no canonical mapping
    if mapping_status == "untracked":
        return WorkflowEnvironmentStatus.UNTRACKED, False

    # For linked workflows, check if in sync
    if mapping_status == "linked":
        if git_content_hash and env_content_hash:
            if env_content_hash == git_content_hash:
                # Fully in sync
                return WorkflowEnvironmentStatus.LINKED, False
            else:
                # Hashes differ - this is either drift or out-of-date
                # Drift: local n8n changes not pushed to git
                # Out-of-date: git has newer version not pulled to n8n
                #
                # For MVP, we can determine this based on timestamps or context.
                # If env was modified after git sync, it's drift.
                # If git was updated after env sync, it's out-of-date.
                #
                # Simplified approach for now: if git_content_hash exists and differs,
                # we consider it out_of_date (canonical is ahead).
                # True drift detection would require more sophisticated comparison.
                return WorkflowEnvironmentStatus.OUT_OF_DATE, True
        elif not git_content_hash:
            # No git state yet - consider it linked (just not synced to git)
            return WorkflowEnvironmentStatus.LINKED, False
        else:
            # Has git state but env_content_hash is missing/different
            return WorkflowEnvironmentStatus.OUT_OF_DATE, True

    # For other mapping statuses (ignored, deleted, missing), treat as not present
    # These shouldn't typically appear in the matrix view
    return None, False


@router.get("/matrix", response_model=WorkflowMatrixResponse)
async def get_workflow_matrix(
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("workflow_read"))
):
    """
    Get the workflow × environment matrix with status badges.

    Returns a complete matrix showing:
    - Rows: All canonical workflows for the tenant
    - Columns: All active environments for the tenant
    - Cells: Status badge (linked, untracked, drift, out_of_date) for each combination

    All status logic is computed server-side. The UI must not infer or compute status logic.
    """
    tenant_id = get_tenant_id(user_info)

    try:
        # Fetch all data in parallel
        canonical_workflows = await db_service.get_canonical_workflows(
            tenant_id=tenant_id,
            include_deleted=False
        )

        environments = await db_service.get_environments(tenant_id)
        # Filter to only active environments
        active_environments = [env for env in environments if env.get("is_active", True)]

        # Get all workflow mappings for this tenant
        all_mappings = await db_service.get_workflow_mappings(tenant_id=tenant_id)

        # Build lookup structures for efficient access
        # mappings_by_canonical_env[canonical_id][environment_id] = mapping
        mappings_by_canonical_env: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for mapping in all_mappings:
            canonical_id = mapping.get("canonical_id")
            env_id = mapping.get("environment_id")
            if canonical_id and env_id:
                if canonical_id not in mappings_by_canonical_env:
                    mappings_by_canonical_env[canonical_id] = {}
                mappings_by_canonical_env[canonical_id][env_id] = mapping

        # Fetch all git states for the tenant
        # We need to query the canonical_workflow_git_state table
        git_states_response = db_service.client.table("canonical_workflow_git_state").select("*").eq("tenant_id", tenant_id).execute()
        git_states = git_states_response.data or []

        # Build lookup for git states
        # git_states_by_canonical_env[canonical_id][environment_id] = git_state
        git_states_by_canonical_env: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for gs in git_states:
            canonical_id = gs.get("canonical_id")
            env_id = gs.get("environment_id")
            if canonical_id and env_id:
                if canonical_id not in git_states_by_canonical_env:
                    git_states_by_canonical_env[canonical_id] = {}
                git_states_by_canonical_env[canonical_id][env_id] = gs

        # Build the response
        workflow_rows: List[WorkflowMatrixRow] = []
        environment_cols: List[WorkflowMatrixEnvironment] = []
        matrix: Dict[str, Dict[str, Optional[WorkflowMatrixCell]]] = {}

        # Build environment columns
        for env in active_environments:
            env_class = env.get("environment_class", "dev")
            # Handle string or enum values
            if isinstance(env_class, str):
                try:
                    env_class = EnvironmentClass(env_class)
                except ValueError:
                    env_class = EnvironmentClass.DEV

            environment_cols.append(WorkflowMatrixEnvironment(
                id=env["id"],
                name=env.get("n8n_name", env.get("name", "Unknown")),
                type=env.get("n8n_type"),
                environment_class=env_class
            ))

        # Build workflow rows and matrix data
        for workflow in canonical_workflows:
            canonical_id = workflow.get("canonical_id")
            if not canonical_id:
                continue

            # Add workflow row
            workflow_rows.append(WorkflowMatrixRow(
                canonical_id=canonical_id,
                display_name=workflow.get("display_name") or canonical_id,
                created_at=workflow.get("created_at")
            ))

            # Initialize matrix row
            matrix[canonical_id] = {}

            # Compute status for each environment
            for env in active_environments:
                env_id = env["id"]

                # Get mapping and git state for this workflow in this environment
                mapping = mappings_by_canonical_env.get(canonical_id, {}).get(env_id)
                git_state = git_states_by_canonical_env.get(canonical_id, {}).get(env_id)

                # Compute status
                status_result = await _compute_cell_status(mapping, git_state)
                computed_status, can_sync = status_result

                if computed_status is None:
                    # Workflow doesn't exist in this environment
                    matrix[canonical_id][env_id] = None
                else:
                    matrix[canonical_id][env_id] = WorkflowMatrixCell(
                        status=computed_status,
                        can_sync=can_sync,
                        n8n_workflow_id=mapping.get("n8n_workflow_id") if mapping else None,
                        content_hash=mapping.get("env_content_hash") if mapping else None
                    )

        return WorkflowMatrixResponse(
            workflows=workflow_rows,
            environments=environment_cols,
            matrix=matrix
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching workflow matrix: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch workflow matrix: {str(e)}"
        )
