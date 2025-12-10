"""
Service for computing workflow sync status between N8N runtime and GitHub
"""
from typing import Dict, Any, Optional
import json
from datetime import datetime
from enum import Enum


class SyncStatus(str, Enum):
    IN_SYNC = "in_sync"
    LOCAL_CHANGES = "local_changes"
    UPDATE_AVAILABLE = "update_available"
    CONFLICT = "conflict"


def compute_sync_status(
    n8n_workflow: Dict[str, Any],
    github_workflow: Optional[Dict[str, Any]],
    last_synced_at: Optional[str] = None,
    n8n_updated_at: Optional[str] = None,
    github_updated_at: Optional[str] = None
) -> str:
    """
    Compute sync status for a workflow by comparing N8N runtime with GitHub.
    
    Args:
        n8n_workflow: Workflow data from N8N runtime
        github_workflow: Workflow data from GitHub (None if not in GitHub)
        last_synced_at: ISO timestamp of last successful sync (optional)
        n8n_updated_at: ISO timestamp when N8N workflow was last updated (optional)
        github_updated_at: ISO timestamp when GitHub workflow was last updated (optional)
    
    Returns:
        Sync status: 'in_sync', 'local_changes', 'update_available', or 'conflict'
    """
    # Normalize workflow JSON for comparison (remove metadata that doesn't affect functionality)
    n8n_json = _normalize_workflow_json(n8n_workflow)
    
    # If workflow doesn't exist in GitHub
    if github_workflow is None:
        # If it was never synced, treat as local changes
        if not last_synced_at:
            return SyncStatus.LOCAL_CHANGES.value
        # If it was synced before but no longer in GitHub, treat as local changes
        return SyncStatus.LOCAL_CHANGES.value
    
    github_json = _normalize_workflow_json(github_workflow)
    
    # Compare normalized JSON
    n8n_json_str = json.dumps(n8n_json, sort_keys=True)
    github_json_str = json.dumps(github_json, sort_keys=True)
    
    # If JSON is identical
    if n8n_json_str == github_json_str:
        return SyncStatus.IN_SYNC.value
    
    # If JSON differs, determine the cause using timestamps if available
    if last_synced_at and n8n_updated_at and github_updated_at:
        try:
            last_sync = datetime.fromisoformat(last_synced_at.replace('Z', '+00:00'))
            n8n_updated = datetime.fromisoformat(n8n_updated_at.replace('Z', '+00:00'))
            github_updated = datetime.fromisoformat(github_updated_at.replace('Z', '+00:00'))
            
            # Check if N8N changed since last sync
            n8n_changed = n8n_updated > last_sync
            # Check if GitHub changed since last sync
            github_changed = github_updated > last_sync
            
            if n8n_changed and not github_changed:
                return SyncStatus.LOCAL_CHANGES.value
            elif github_changed and not n8n_changed:
                return SyncStatus.UPDATE_AVAILABLE.value
            elif n8n_changed and github_changed:
                return SyncStatus.CONFLICT.value
        except (ValueError, AttributeError):
            # If timestamp parsing fails, fall through to conflict
            pass
    
    # If we can't determine from timestamps, check if both have different updated times
    # This is a heuristic: if both were updated, it's likely a conflict
    if n8n_updated_at and github_updated_at:
        try:
            n8n_updated = datetime.fromisoformat(n8n_updated_at.replace('Z', '+00:00'))
            github_updated = datetime.fromisoformat(github_updated_at.replace('Z', '+00:00'))
            
            # If both have recent updates, likely conflict
            # Otherwise, if only one is recent, use that to determine status
            if abs((n8n_updated - github_updated).total_seconds()) < 60:
                # Updated within same minute - likely conflict
                return SyncStatus.CONFLICT.value
            elif n8n_updated > github_updated:
                return SyncStatus.LOCAL_CHANGES.value
            else:
                return SyncStatus.UPDATE_AVAILABLE.value
        except (ValueError, AttributeError):
            pass
    
    # Default to conflict if we can't determine
    return SyncStatus.CONFLICT.value


def _normalize_workflow_json(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize workflow JSON for comparison by removing metadata fields
    that don't affect functionality.
    """
    # Create a copy to avoid modifying the original
    normalized = json.loads(json.dumps(workflow))
    
    # Remove metadata fields that don't affect workflow functionality
    metadata_fields = [
        'id',  # ID might differ but workflow is the same
        'updatedAt',  # Timestamp doesn't affect functionality
        'createdAt',  # Timestamp doesn't affect functionality
        'versionId',  # Version ID is metadata
    ]
    
    for field in metadata_fields:
        normalized.pop(field, None)
    
    # Also normalize nodes - remove position and other UI metadata
    if 'nodes' in normalized and isinstance(normalized['nodes'], list):
        for node in normalized['nodes']:
            # Remove position and other UI-specific fields
            ui_fields = ['position', 'positionAbsolute', 'selected', 'selectedNodes']
            for field in ui_fields:
                node.pop(field, None)
    
    return normalized

