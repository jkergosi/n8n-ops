"""
Canonical Workflow Service - Core service for canonical workflow identity management
"""
import hashlib
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import uuid4

from app.services.database import db_service
from app.services.promotion_service import normalize_workflow_for_comparison
from app.schemas.canonical_workflow import WorkflowMappingStatus

logger = logging.getLogger(__name__)


# Hash collision registry - tracks hash->payload mappings for collision detection
# Key: content_hash (str), Value: normalized workflow payload (Dict[str, Any])
_hash_collision_registry: Dict[str, Dict[str, Any]] = {}


def register_workflow_hash(content_hash: str, normalized_payload: Dict[str, Any]) -> None:
    """
    Register a workflow hash and its normalized payload in the collision registry.

    This registry is used for collision detection during hash computation.
    When a hash collision is detected (same hash, different payload),
    the system can apply a deterministic fallback strategy.

    Args:
        content_hash: The SHA256 hash of the normalized workflow
        normalized_payload: The normalized workflow payload that produced this hash
    """
    _hash_collision_registry[content_hash] = normalized_payload


def get_registered_payload(content_hash: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve the registered payload for a given hash.

    Returns None if the hash hasn't been registered yet.

    Args:
        content_hash: The SHA256 hash to lookup

    Returns:
        The normalized workflow payload if registered, None otherwise
    """
    return _hash_collision_registry.get(content_hash)


def clear_hash_registry() -> None:
    """
    Clear the hash collision registry.

    Useful for testing or when starting a fresh batch operation.
    """
    global _hash_collision_registry
    _hash_collision_registry = {}


def get_registry_stats() -> Dict[str, int]:
    """
    Get statistics about the current hash registry.

    Returns:
        Dictionary with registry statistics (total_entries)
    """
    return {
        "total_entries": len(_hash_collision_registry)
    }


def compute_workflow_hash(workflow: Dict[str, Any], canonical_id: Optional[str] = None) -> str:
    """
    Compute SHA256 hash of normalized workflow content with collision detection.

    Uses normalize_workflow_for_comparison() as the single source of truth
    for normalization, then hashes the sorted JSON representation.

    Implements collision detection with deterministic fallback strategy:
    - If a hash collision is detected (same hash, different payload),
      applies a deterministic fallback by appending the canonical_id to the
      normalized content and rehashing.
    - This ensures that workflows with identical content but different
      canonical_ids receive unique, deterministic hashes.
    - If no canonical_id is provided during a collision, a warning is logged
      and the original colliding hash is returned (collision unresolved).

    Args:
        workflow: The workflow payload to hash
        canonical_id: Optional canonical workflow ID (required for deterministic
                     fallback in case of hash collision)

    Returns:
        SHA256 hex digest (no prefix). If collision detected and canonical_id
        is provided, returns a deterministic fallback hash. If collision detected
        without canonical_id, returns the original colliding hash.
    """
    normalized = normalize_workflow_for_comparison(workflow)
    json_str = json.dumps(normalized, sort_keys=True)
    content_hash = hashlib.sha256(json_str.encode()).hexdigest()

    # Check for hash collision
    registered_payload = get_registered_payload(content_hash)

    if registered_payload is not None:
        # Hash already exists - check if payloads are identical
        if registered_payload != normalized:
            # COLLISION DETECTED: Same hash, different payload
            logger.warning(
                f"Hash collision detected! Hash '{content_hash}' maps to different payloads. "
                f"Canonical ID: {canonical_id or 'unknown'}. "
                f"Applying deterministic fallback strategy."
            )

            # Apply deterministic fallback strategy
            if canonical_id:
                # Append canonical_id to normalized content and rehash
                # This creates a deterministic, unique hash for this workflow
                fallback_content = {
                    **normalized,
                    "__canonical_id__": canonical_id
                }
                fallback_json_str = json.dumps(fallback_content, sort_keys=True)
                fallback_hash = hashlib.sha256(fallback_json_str.encode()).hexdigest()

                logger.info(
                    f"Applied fallback hash strategy for collision. "
                    f"Original hash: '{content_hash}', "
                    f"Fallback hash: '{fallback_hash}', "
                    f"Canonical ID: {canonical_id}"
                )

                # Register the fallback hash to prevent future collisions
                register_workflow_hash(fallback_hash, fallback_content)

                return fallback_hash
            else:
                # No canonical_id provided - cannot apply fallback strategy
                logger.error(
                    f"Hash collision detected but no canonical_id provided for fallback. "
                    f"Hash: '{content_hash}'. Returning colliding hash (unresolved collision)."
                )
                # Return the colliding hash - collision remains unresolved
                return content_hash
        else:
            # Same hash, same payload - this is expected (duplicate workflow)
            logger.debug(f"Hash '{content_hash}' matches existing payload (duplicate workflow)")
    else:
        # First time seeing this hash - register it
        register_workflow_hash(content_hash, normalized)
        logger.debug(f"Registered new hash '{content_hash}' in collision registry")

    return content_hash


def compute_workflow_mapping_status(
    canonical_id: Optional[str],
    n8n_workflow_id: Optional[str],
    is_present_in_n8n: bool,
    is_deleted: bool = False,
    is_ignored: bool = False
) -> WorkflowMappingStatus:
    """
    Compute the correct workflow mapping status based on precedence rules.

    Implements the status precedence rules defined in WorkflowMappingStatus:
    1. DELETED - Takes precedence over all other states
    2. IGNORED - Takes precedence over operational states
    3. MISSING - Workflow was mapped but disappeared from n8n
    4. UNMAPPED - Workflow exists in n8n but has no canonical_id
    5. LINKED - Normal operational state with both IDs

    Args:
        canonical_id: The canonical workflow ID (None if not linked)
        n8n_workflow_id: The n8n workflow ID (None if not synced)
        is_present_in_n8n: Whether workflow currently exists in n8n environment
        is_deleted: Whether the mapping/workflow is soft-deleted
        is_ignored: Whether the workflow is explicitly marked as ignored

    Returns:
        The computed WorkflowMappingStatus based on precedence rules

    Examples:
        # Deleted workflow (highest precedence)
        >>> compute_workflow_mapping_status("c1", "w1", True, is_deleted=True)
        WorkflowMappingStatus.DELETED

        # Ignored workflow
        >>> compute_workflow_mapping_status("c1", "w1", True, is_ignored=True)
        WorkflowMappingStatus.IGNORED

        # Missing workflow (was linked, disappeared from n8n)
        >>> compute_workflow_mapping_status("c1", "w1", False)
        WorkflowMappingStatus.MISSING

        # Unmapped workflow (exists in n8n, no canonical_id)
        >>> compute_workflow_mapping_status(None, "w1", True)
        WorkflowMappingStatus.UNMAPPED

        # Linked workflow (normal state)
        >>> compute_workflow_mapping_status("c1", "w1", True)
        WorkflowMappingStatus.LINKED
    """
    # Precedence 1: DELETED overrides everything
    if is_deleted:
        return WorkflowMappingStatus.DELETED

    # Precedence 2: IGNORED overrides operational states
    if is_ignored:
        return WorkflowMappingStatus.IGNORED

    # Precedence 3: MISSING if workflow was mapped but disappeared from n8n
    # A workflow is considered "was mapped" if it has n8n_workflow_id
    if not is_present_in_n8n and n8n_workflow_id:
        return WorkflowMappingStatus.MISSING

    # Precedence 4: UNMAPPED if no canonical_id but exists in n8n
    if not canonical_id and is_present_in_n8n:
        return WorkflowMappingStatus.UNMAPPED

    # Precedence 5: LINKED as default operational state
    # This requires both canonical_id and is_present_in_n8n
    if canonical_id and is_present_in_n8n:
        return WorkflowMappingStatus.LINKED

    # Edge case: if we get here, the mapping is in an inconsistent state
    # This could happen during onboarding or partial sync operations
    # Default to UNMAPPED as the safest fallback
    logger.warning(
        f"Inconsistent workflow mapping state: canonical_id={canonical_id}, "
        f"n8n_workflow_id={n8n_workflow_id}, is_present_in_n8n={is_present_in_n8n}, "
        f"is_deleted={is_deleted}, is_ignored={is_ignored}. Defaulting to UNMAPPED."
    )
    return WorkflowMappingStatus.UNMAPPED


class CanonicalWorkflowService:
    """Service for managing canonical workflow identity"""
    
    @staticmethod
    async def create_canonical_workflow(
        tenant_id: str,
        canonical_id: Optional[str] = None,
        created_by_user_id: Optional[str] = None,
        display_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new canonical workflow.
        
        Args:
            tenant_id: Tenant ID
            canonical_id: Optional canonical ID (generates UUID if not provided)
            created_by_user_id: User who created the workflow
            display_name: Optional display name cache
            
        Returns:
            Created canonical workflow record
        """
        if not canonical_id:
            canonical_id = str(uuid4())
        
        workflow_data = {
            "tenant_id": tenant_id,
            "canonical_id": canonical_id,
            "created_at": datetime.utcnow().isoformat(),
            "created_by_user_id": created_by_user_id,
            "display_name": display_name
        }
        
        try:
            response = db_service.client.table("canonical_workflows").insert(workflow_data).execute()
            if response and response.data:
                logger.info(f"Created canonical workflow {canonical_id} for tenant {tenant_id}")
                return response.data[0]
            raise Exception("Failed to create canonical workflow")
        except Exception as e:
            logger.error(f"Error creating canonical workflow: {str(e)}")
            raise
    
    @staticmethod
    async def get_canonical_workflow(
        tenant_id: str,
        canonical_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a canonical workflow by ID"""
        try:
            response = (
                db_service.client.table("canonical_workflows")
                .select("*")
                .eq("tenant_id", tenant_id)
                .eq("canonical_id", canonical_id)
                .is_("deleted_at", "null")
                .maybe_single()
                .execute()
            )
            return response.data if response and response.data else None
        except Exception as e:
            logger.error(f"Error fetching canonical workflow {canonical_id}: {str(e)}")
            return None
    
    @staticmethod
    async def list_canonical_workflows(
        tenant_id: str,
        include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """List all canonical workflows for a tenant"""
        try:
            query = (
                db_service.client.table("canonical_workflows")
                .select("*")
                .eq("tenant_id", tenant_id)
            )
            
            if not include_deleted:
                query = query.is_("deleted_at", "null")

            response = query.order("created_at", desc=True).execute()
            return (response.data or []) if response else []
        except Exception as e:
            logger.error(f"Error listing canonical workflows: {str(e)}")
            return []
    
    @staticmethod
    async def update_canonical_workflow(
        tenant_id: str,
        canonical_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a canonical workflow"""
        try:
            response = (
                db_service.client.table("canonical_workflows")
                .update(updates)
                .eq("tenant_id", tenant_id)
                .eq("canonical_id", canonical_id)
                .execute()
            )
            return response.data[0] if response and response.data else None
        except Exception as e:
            logger.error(f"Error updating canonical workflow {canonical_id}: {str(e)}")
            return None
    
    @staticmethod
    async def mark_canonical_workflow_deleted(
        tenant_id: str,
        canonical_id: str
    ) -> bool:
        """
        Mark a canonical workflow as deleted (soft delete).
        
        Does not actually delete the row - sets deleted_at timestamp.
        """
        try:
            await CanonicalWorkflowService.update_canonical_workflow(
                tenant_id,
                canonical_id,
                {"deleted_at": datetime.utcnow().isoformat()}
            )
            logger.info(f"Marked canonical workflow {canonical_id} as deleted")
            return True
        except Exception as e:
            logger.error(f"Error marking canonical workflow as deleted: {str(e)}")
            return False
    
    @staticmethod
    async def get_canonical_workflow_git_state(
        tenant_id: str,
        environment_id: str,
        canonical_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get Git state for a canonical workflow in a specific environment.

        Returns None if no Git state exists for this workflow in the environment.
        This is expected for workflows that haven't been synced to Git yet.
        """
        try:
            response = (
                db_service.client.table("canonical_workflow_git_state")
                .select("*")
                .eq("tenant_id", tenant_id)
                .eq("environment_id", environment_id)
                .eq("canonical_id", canonical_id)
                .maybe_single()
                .execute()
            )
            return response.data if response and response.data else None
        except Exception as e:
            logger.error(f"Error fetching Git state: {str(e)}")
            return None
    
    @staticmethod
    async def upsert_canonical_workflow_git_state(
        tenant_id: str,
        environment_id: str,
        canonical_id: str,
        git_path: str,
        git_content_hash: str,
        git_commit_sha: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create or update Git state for a canonical workflow"""
        git_state_data = {
            "tenant_id": tenant_id,
            "environment_id": environment_id,
            "canonical_id": canonical_id,
            "git_path": git_path,
            "git_content_hash": git_content_hash,
            "git_commit_sha": git_commit_sha,
            "last_repo_sync_at": datetime.utcnow().isoformat()
        }
        
        try:
            response = (
                db_service.client.table("canonical_workflow_git_state")
                .upsert(git_state_data, on_conflict="tenant_id,environment_id,canonical_id")
                .execute()
            )
            return response.data[0] if response and response.data else git_state_data
        except Exception as e:
            logger.error(f"Error upserting Git state: {str(e)}")
            raise

