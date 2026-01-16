"""
Snapshot Manifest Schema - Git-based snapshot structure

This module defines the schema for snapshot manifests stored in Git.
Snapshots are owned by the TARGET environment and are immutable once created.

Git Structure:
    <env>/
        current.json                    # Pointer to current snapshot
        snapshots/
            <snapshot_id>/
                manifest.json           # This schema
                workflows/
                    <workflow_key>.json # Individual workflow files
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class SnapshotKind(str, Enum):
    """Type of snapshot operation that created this snapshot."""
    ONBOARDING = "onboarding"   # Initial environment setup
    PROMOTION = "promotion"     # Workflow promotion from another env
    BACKUP = "backup"           # Manual or scheduled backup
    ROLLBACK = "rollback"       # Rollback operation (creates new snapshot)


class WorkflowFileEntry(BaseModel):
    """Entry for a single workflow file in the manifest."""
    workflow_key: str = Field(..., description="Workflow identifier (used as filename)")
    workflow_name: str = Field(..., description="Human-readable workflow name")
    file_path: str = Field(..., description="Relative path within snapshot (e.g., 'workflows/abc123.json')")
    content_hash: str = Field(..., description="SHA256 hash of normalized workflow content")
    active: bool = Field(default=False, description="Whether workflow was active at snapshot time")

    class Config:
        json_schema_extra = {
            "example": {
                "workflow_key": "abc123",
                "workflow_name": "Customer Onboarding",
                "file_path": "workflows/abc123.json",
                "content_hash": "sha256:a1b2c3d4e5f6...",
                "active": True
            }
        }


class SnapshotManifest(BaseModel):
    """
    Manifest for a Git-based snapshot.

    This is stored as manifest.json within each snapshot folder.
    The manifest contains metadata about the snapshot and a list of all
    workflow files with their content hashes.
    """
    snapshot_id: str = Field(..., description="Unique snapshot identifier (UUID)")
    kind: SnapshotKind = Field(..., description="Type of operation that created this snapshot")
    target_env: str = Field(..., description="Environment that owns this snapshot")
    source_env: Optional[str] = Field(None, description="Source environment (for promotions)")
    source_snapshot_id: Optional[str] = Field(None, description="Source snapshot ID (for promotions from staging to prod)")

    created_at: datetime = Field(default_factory=_utc_now, description="Snapshot creation timestamp")
    created_by: Optional[str] = Field(None, description="User ID who created the snapshot")

    workflows: List[WorkflowFileEntry] = Field(default_factory=list, description="List of workflow files in snapshot")
    workflows_count: int = Field(default=0, description="Total number of workflows")

    overall_hash: str = Field(..., description="Combined hash of all workflow hashes (deterministic)")

    # Optional metadata
    reason: Optional[str] = Field(None, description="Human-readable reason for snapshot")
    promotion_id: Optional[str] = Field(None, description="Associated promotion ID (if applicable)")
    deployment_id: Optional[str] = Field(None, description="Associated deployment ID (if applicable)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "snapshot_id": "550e8400-e29b-41d4-a716-446655440000",
                "kind": "promotion",
                "target_env": "staging",
                "source_env": "dev",
                "created_at": "2024-01-15T10:30:00Z",
                "workflows": [],
                "workflows_count": 5,
                "overall_hash": "sha256:combined..."
            }
        }


class EnvironmentPointer(BaseModel):
    """
    Environment pointer stored as <env>/current.json in Git.

    Points to the currently deployed snapshot for this environment.
    Only updated AFTER successful deploy + verify.
    """
    env: str = Field(..., description="Environment identifier")
    current_snapshot_id: str = Field(..., description="Currently deployed snapshot ID")
    current_snapshot_commit: Optional[str] = Field(None, description="Git commit SHA of the snapshot")
    updated_at: datetime = Field(default_factory=_utc_now, description="When pointer was last updated")
    updated_by: Optional[str] = Field(None, description="User who updated the pointer")

    class Config:
        json_schema_extra = {
            "example": {
                "env": "staging",
                "current_snapshot_id": "550e8400-e29b-41d4-a716-446655440000",
                "current_snapshot_commit": "abc123def456",
                "updated_at": "2024-01-15T10:35:00Z"
            }
        }


def generate_snapshot_id() -> str:
    """Generate a new unique snapshot ID."""
    return str(uuid4())
