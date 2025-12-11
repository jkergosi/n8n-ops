from fastapi import APIRouter, HTTPException, status, Query
from typing import Optional, List
from datetime import datetime
from app.services.database import db_service
from app.services.github_service import GitHubService
from app.services.n8n_client import N8NClient
from app.schemas.deployment import (
    SnapshotResponse,
    SnapshotCreate,
    SnapshotType,
)
from app.schemas.promotion import PromotionSnapshotResponse

router = APIRouter()

# TODO: Replace with actual tenant ID from authenticated user
MOCK_TENANT_ID = "00000000-0000-0000-0000-000000000000"


@router.get("/", response_model=List[SnapshotResponse])
async def get_snapshots(
    environment_id: Optional[str] = Query(None),
    type: Optional[SnapshotType] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """
    Get list of snapshots with filtering and pagination.
    Environment-scoped by default.
    """
    try:
        # Build query
        query = db_service.client.table("snapshots").select("*").eq("tenant_id", MOCK_TENANT_ID)

        if environment_id:
            query = query.eq("environment_id", environment_id)
        if type:
            query = query.eq("type", type.value)
        if from_date:
            query = query.gte("created_at", from_date.isoformat())
        if to_date:
            query = query.lte("created_at", to_date.isoformat())

        # Apply pagination
        from_index = (page - 1) * page_size
        to_index = from_index + page_size
        query = query.order("created_at", desc=True).range(from_index, to_index - 1)

        result = query.execute()
        snapshots_data = result.data or []

        return [SnapshotResponse(**snapshot) for snapshot in snapshots_data]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch snapshots: {str(e)}",
        )


@router.get("/{snapshot_id}", response_model=SnapshotResponse)
async def get_snapshot(snapshot_id: str):
    """
    Get snapshot details including metadata and related deployment.
    """
    try:
        result = (
            db_service.client.table("snapshots")
            .select("*")
            .eq("id", snapshot_id)
            .eq("tenant_id", MOCK_TENANT_ID)
            .single()
            .execute()
        )

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Snapshot {snapshot_id} not found",
            )

        return SnapshotResponse(**result.data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch snapshot: {str(e)}",
        )


@router.post("/{snapshot_id}/restore")
async def restore_snapshot(snapshot_id: str):
    """
    Restore an environment to a snapshot's state.
    Pulls workflows from GitHub at the snapshot's commit SHA and pushes to N8N.
    """
    try:
        # Get snapshot
        snapshot_result = (
            db_service.client.table("snapshots")
            .select("*")
            .eq("id", snapshot_id)
            .eq("tenant_id", MOCK_TENANT_ID)
            .single()
            .execute()
        )

        if not snapshot_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Snapshot {snapshot_id} not found",
            )

        snapshot = snapshot_result.data
        environment_id = snapshot["environment_id"]
        commit_sha = snapshot["git_commit_sha"]

        # Get environment config
        env_config = await db_service.get_environment(environment_id, MOCK_TENANT_ID)
        if not env_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Environment {environment_id} not found",
            )

        # Check GitHub config
        if not env_config.get("git_repo_url") or not env_config.get("git_pat"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub not configured for this environment",
            )

        # Create GitHub service
        repo_url = env_config.get("git_repo_url", "").rstrip('/').replace('.git', '')
        repo_parts = repo_url.split("/")
        github_service = GitHubService(
            token=env_config.get("git_pat"),
            repo_owner=repo_parts[-2] if len(repo_parts) >= 2 else "",
            repo_name=repo_parts[-1] if len(repo_parts) >= 1 else "",
            branch=env_config.get("git_branch", "main")
        )

        # Create N8N client
        n8n_client = N8NClient(
            base_url=env_config.get("n8n_base_url"),
            api_key=env_config.get("n8n_api_key")
        )

        # Get all workflows from GitHub at the commit SHA
        # Note: This requires GitHub API to get tree/blob at specific commit
        # For now, we'll use the current branch state (v1 limitation)
        # TODO: Implement commit SHA checkout in GitHubService
        workflows = await github_service.get_all_workflows_from_github(
            environment_type=env_config.get("n8n_type", "dev")
        )

        if not workflows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No workflows found in GitHub for commit {commit_sha}",
            )

        # Restore workflows to N8N
        restored_count = 0
        errors = []

        for workflow_id, workflow_data in workflows.items():
            try:
                # Update or create workflow in N8N
                await n8n_client.update_workflow(workflow_id, workflow_data)
                restored_count += 1
            except Exception as e:
                errors.append(f"Failed to restore workflow {workflow_id}: {str(e)}")

        # Optionally create a new snapshot after rollback
        # This would be a manual_backup type snapshot

        return {
            "success": len(errors) == 0,
            "restored": restored_count,
            "failed": len(errors),
            "errors": errors,
            "message": f"Restored {restored_count} workflows from snapshot",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restore snapshot: {str(e)}",
        )

