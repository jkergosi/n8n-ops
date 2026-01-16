"""
API endpoint for workflow × environment matrix (read-only).

This endpoint provides a single read-only API that returns the full workflow × environment
matrix with backend-computed status for each cell. The UI must not infer or compute status logic.

Status Computation:
------------------
Cell status is computed using a two-tier approach:

1. Persisted Status (from workflow_env_map.status) - Follows precedence rules:
   - DELETED: Takes precedence over all (not shown in matrix)
   - IGNORED: User explicitly ignored (not shown in matrix)
   - MISSING: Workflow disappeared from n8n (not shown in matrix)
   - UNMAPPED: Exists in n8n but no canonical_id
   - LINKED: Normal operational state

2. Display Status (computed for matrix cells):
   - LINKED: Mapped and in sync (env_content_hash == git_content_hash)
   - UNMAPPED: Exists in n8n but no canonical mapping
   - DRIFT: Linked but env has local changes not in git (env updated after git sync)
   - OUT_OF_DATE: Linked but git is ahead of env (git updated after env sync)

The UI must not compute or override these statuses - all logic is server-side.
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
from app.services.canonical_workflow_service import compute_workflow_mapping_status
from app.schemas.canonical_workflow import WorkflowMappingStatus

logger = logging.getLogger(__name__)

router = APIRouter()


# Response Models

class WorkflowEnvironmentStatus(str, Enum):
    """
    Display status of a canonical workflow in a specific environment.

    These statuses are computed for the workflow matrix UI based on:
    1. The persisted mapping status (from WorkflowMappingStatus with precedence rules)
    2. Content hash comparisons to detect drift/out-of-date conditions

    Display Statuses:
    - LINKED: Workflow is canonically mapped and in sync (env hash == git hash)
    - UNMAPPED: Workflow exists in n8n but has no canonical mapping
    - DRIFT: Workflow is linked but has local changes not yet pushed to git
    - OUT_OF_DATE: Workflow is linked but git has newer version not deployed to env

    Note: Workflows with DELETED, IGNORED, or MISSING status are not shown in the matrix.
    """
    LINKED = "linked"
    UNMAPPED = "unmapped"
    DRIFT = "drift"
    OUT_OF_DATE = "out_of_date"


class WorkflowMatrixCell(BaseModel):
    """Represents a single cell in the workflow × environment matrix."""
    status: WorkflowEnvironmentStatus
    can_sync: bool = Field(alias="canSync", serialization_alias="canSync")
    n8n_workflow_id: Optional[str] = Field(default=None, alias="n8nWorkflowId", serialization_alias="n8nWorkflowId")
    content_hash: Optional[str] = Field(default=None, alias="contentHash", serialization_alias="contentHash")
    collision_warning: Optional[str] = Field(
        default=None,
        alias="collisionWarning",
        serialization_alias="collisionWarning",
        description="Hash collision warning if detected for this workflow in this environment"
    )

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


class PageMetadata(BaseModel):
    """Pagination metadata"""
    page: int
    page_size: int = Field(alias="pageSize", serialization_alias="pageSize")
    total_workflows: int = Field(alias="totalWorkflows", serialization_alias="totalWorkflows")
    total_pages: int = Field(alias="totalPages", serialization_alias="totalPages")
    has_more: bool = Field(alias="hasMore", serialization_alias="hasMore")

    model_config = {"populate_by_name": True}


class WorkflowMatrixResponse(BaseModel):
    """Complete matrix response from the backend."""
    workflows: List[WorkflowMatrixRow]
    environments: List[WorkflowMatrixEnvironment]
    matrix: Dict[str, Dict[str, Optional[WorkflowMatrixCell]]]
    page_metadata: PageMetadata = Field(alias="pageMetadata", serialization_alias="pageMetadata")

    model_config = {"populate_by_name": True}


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
    Compute the display status for a workflow in an environment.

    Returns tuple of (status, can_sync).

    This function computes display statuses for the workflow matrix UI based on:
    1. The persisted mapping status (using precedence rules from compute_workflow_mapping_status)
    2. Content hash comparisons to determine DRIFT or OUT_OF_DATE display states

    Status Precedence (from WorkflowMappingStatus):
    1. DELETED - Workflow/mapping is soft-deleted (not shown in matrix)
    2. IGNORED - User explicitly ignored (not shown in matrix)
    3. MISSING - Was mapped but disappeared from n8n (not shown in matrix)
    4. UNMAPPED - Exists in n8n but no canonical_id (shown as "unmapped")
    5. LINKED - Normal operational state (shown as "linked", "drift", or "out_of_date")

    Display Status Logic:
    - UNMAPPED: Workflow exists but no canonical mapping (mapping status = "unmapped")
    - LINKED: Mapping status is "linked" and env_content_hash == git_content_hash
    - DRIFT: Mapping status is "linked" but env has changes not in git
    - OUT_OF_DATE: Mapping status is "linked" but git is ahead of env

    Args:
        mapping: The workflow_env_map record for this workflow in this environment
        git_state: The canonical_workflow_git_state record (if exists)

    Returns:
        Tuple of (WorkflowEnvironmentStatus | None, can_sync: bool)
        Returns (None, False) if workflow should not be displayed in matrix
    """
    if not mapping:
        # No mapping means the workflow doesn't exist in this environment
        return None, False

    # Get the persisted mapping status
    mapping_status = mapping.get("status")

    # Apply status precedence rules: DELETED, IGNORED, and MISSING are not shown in matrix
    # These statuses indicate the workflow should not be displayed as an active cell
    if mapping_status in ("deleted", "ignored", "missing"):
        return None, False

    # UNMAPPED: workflow exists in n8n but has no canonical mapping
    if mapping_status == "unmapped":
        return WorkflowEnvironmentStatus.UNMAPPED, False

    # LINKED: workflow has canonical mapping - now check for drift/out-of-date
    if mapping_status == "linked":
        env_content_hash = mapping.get("env_content_hash")
        git_content_hash = git_state.get("git_content_hash") if git_state else None

        # If no git state exists yet, the workflow is linked but not synced to git
        if not git_content_hash:
            return WorkflowEnvironmentStatus.LINKED, False

        # Compare content hashes to determine if in sync, drifted, or out-of-date
        if env_content_hash and git_content_hash:
            if env_content_hash == git_content_hash:
                # Fully in sync
                return WorkflowEnvironmentStatus.LINKED, False
            else:
                # Hashes differ - determine if drift or out-of-date
                # DRIFT: Environment has local changes not yet pushed to git
                # OUT_OF_DATE: Git has newer version not yet deployed to environment
                #
                # For MVP, we use a simplified heuristic:
                # - Compare timestamps: if env was updated after git sync, it's DRIFT
                # - Otherwise, if git is different, it's OUT_OF_DATE
                #
                # Future enhancement: Track bidirectional sync timestamps for precise detection
                env_updated_at = mapping.get("n8n_updated_at")
                git_synced_at = git_state.get("last_repo_sync_at")

                if env_updated_at and git_synced_at:
                    # Parse timestamps for comparison
                    try:
                        from dateutil import parser
                        env_dt = parser.parse(env_updated_at) if isinstance(env_updated_at, str) else env_updated_at
                        git_dt = parser.parse(git_synced_at) if isinstance(git_synced_at, str) else git_synced_at

                        if env_dt > git_dt:
                            # Environment was updated after git sync - local changes (DRIFT)
                            return WorkflowEnvironmentStatus.DRIFT, True
                    except Exception as e:
                        logger.warning(f"Error comparing timestamps: {e}")

                # Default: git is ahead of environment (OUT_OF_DATE)
                return WorkflowEnvironmentStatus.OUT_OF_DATE, True
        else:
            # Missing hash - treat as out of date
            return WorkflowEnvironmentStatus.OUT_OF_DATE, True

    # Fallback for unknown status - should not happen with proper data
    logger.warning(f"Unexpected mapping status in matrix: {mapping_status}")
    return None, False


@router.get("/matrix", response_model=WorkflowMatrixResponse)
async def get_workflow_matrix(
    page: int = 1,
    page_size: int = 50,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("workflow_read"))
):
    """
    Get the workflow × environment matrix with status badges.

    Returns a paginated matrix showing:
    - Rows: Canonical workflows for the tenant (paginated)
    - Columns: All active environments for the tenant
    - Cells: Status badge (linked, unmapped, drift, out_of_date) for each combination

    Pagination:
    - page: Page number (1-indexed, default: 1)
    - page_size: Items per page (default: 50, max: 100)

    All status logic is computed server-side. The UI must not infer or compute status logic.
    """
    tenant_id = get_tenant_id(user_info)

    # Validate and cap page_size
    page_size = min(max(1, page_size), 100)  # Cap at 100
    page = max(1, page)  # Ensure page is at least 1

    try:
        # Get total count for pagination metadata (run in parallel with data fetch)
        import asyncio
        total_workflows_task = asyncio.create_task(
            db_service.count_canonical_workflows(
                tenant_id=tenant_id,
                include_deleted=False
            )
        )

        # Fetch paginated workflows and environments in parallel
        canonical_workflows = await db_service.get_canonical_workflows(
            tenant_id=tenant_id,
            include_deleted=False,
            page=page,
            page_size=page_size
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

        # Build hash collision detection map per environment
        # Map of environment_id -> content_hash -> list of canonical_ids
        hash_to_canonical_map: Dict[str, Dict[str, List[str]]] = {}
        for mapping in all_mappings:
            env_id = mapping.get("environment_id")
            content_hash = mapping.get("env_content_hash")
            canonical_id = mapping.get("canonical_id")

            if env_id and content_hash and canonical_id:
                if env_id not in hash_to_canonical_map:
                    hash_to_canonical_map[env_id] = {}
                if content_hash not in hash_to_canonical_map[env_id]:
                    hash_to_canonical_map[env_id][content_hash] = []
                hash_to_canonical_map[env_id][content_hash].append(canonical_id)

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
                    # Check for hash collision in this environment
                    collision_warning = None
                    if mapping:
                        content_hash = mapping.get("env_content_hash")
                        if content_hash and env_id in hash_to_canonical_map:
                            canonical_ids_with_hash = hash_to_canonical_map[env_id].get(content_hash, [])
                            if len(canonical_ids_with_hash) > 1:
                                # Collision detected: multiple canonical workflows share the same hash
                                other_workflows = [cid for cid in canonical_ids_with_hash if cid != canonical_id]
                                collision_warning = (
                                    f"Hash collision detected: Content hash '{content_hash[:12]}...' "
                                    f"is shared with {len(other_workflows)} other workflow(s). "
                                    f"This may indicate identical workflow content or a hash collision."
                                )

                    matrix[canonical_id][env_id] = WorkflowMatrixCell(
                        status=computed_status,
                        can_sync=can_sync,
                        n8n_workflow_id=mapping.get("n8n_workflow_id") if mapping else None,
                        content_hash=mapping.get("env_content_hash") if mapping else None,
                        collision_warning=collision_warning
                    )

        # Await the total count
        total_workflows = await total_workflows_task

        # Calculate pagination metadata
        import math
        total_pages = math.ceil(total_workflows / page_size) if page_size > 0 else 0
        has_more = page < total_pages

        return WorkflowMatrixResponse(
            workflows=workflow_rows,
            environments=environment_cols,
            matrix=matrix,
            page_metadata=PageMetadata(
                page=page,
                page_size=page_size,
                total_workflows=total_workflows,
                total_pages=total_pages,
                has_more=has_more
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching workflow matrix: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch workflow matrix: {str(e)}"
        )
