"""Reconciliation Service for executing drift resolution actions."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from app.services.database import db_service
from app.services.github_service import github_service
from app.services.feature_service import feature_service
from app.schemas.drift_incident import (
    ResolutionType,
    ReconciliationStatus,
)


class ReconciliationService:
    """Service for executing drift reconciliation actions."""

    async def create_artifact(
        self,
        tenant_id: str,
        incident_id: str,
        resolution_type: ResolutionType,
        user_id: str,
        affected_workflows: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a reconciliation artifact and start the process."""
        # Verify incident exists and is in valid state
        incident = await self._get_incident(tenant_id, incident_id)
        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Incident not found",
            )

        # Check incident status allows reconciliation
        if incident["status"] not in ["detected", "acknowledged", "stabilized"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot start reconciliation for incident in '{incident['status']}' status",
            )

        now = datetime.utcnow().isoformat()

        artifact_data = {
            "tenant_id": tenant_id,
            "incident_id": incident_id,
            "type": resolution_type.value,
            "status": ReconciliationStatus.pending.value,
            "started_by": user_id,
            "affected_workflows": affected_workflows or [],
            "external_refs": {},
            "created_at": now,
            "updated_at": now,
        }

        try:
            response = db_service.client.table(
                "drift_reconciliation_artifacts"
            ).insert(artifact_data).execute()

            artifact = response.data[0] if response.data else None
            if not artifact:
                raise Exception("Failed to create artifact")

            return artifact
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create reconciliation artifact: {str(e)}",
            )

    async def start_reconciliation(
        self,
        tenant_id: str,
        artifact_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Start the reconciliation execution."""
        artifact = await self._get_artifact(tenant_id, artifact_id)
        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reconciliation artifact not found",
            )

        if artifact["status"] != ReconciliationStatus.pending.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot start reconciliation in '{artifact['status']}' status",
            )

        now = datetime.utcnow().isoformat()

        # Update to in_progress
        update_data = {
            "status": ReconciliationStatus.in_progress.value,
            "started_at": now,
            "updated_at": now,
        }

        try:
            response = db_service.client.table(
                "drift_reconciliation_artifacts"
            ).update(update_data).eq("id", artifact_id).eq(
                "tenant_id", tenant_id
            ).execute()

            return response.data[0] if response.data else artifact
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start reconciliation: {str(e)}",
            )

    async def execute_promote(
        self,
        tenant_id: str,
        artifact_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Execute promote reconciliation.
        Pushes runtime workflow state to Git.
        """
        artifact = await self._get_artifact(tenant_id, artifact_id)
        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reconciliation artifact not found",
            )

        if artifact["type"] != ResolutionType.promote.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Artifact is not a promote type",
            )

        # Get incident and environment
        incident = await self._get_incident(tenant_id, artifact["incident_id"])
        if not incident:
            return await self._fail_artifact(
                tenant_id, artifact_id, "Incident not found"
            )

        environment_id = incident["environment_id"]

        # Get environment details for Git config
        env_response = db_service.client.table("environments").select(
            "*"
        ).eq("id", environment_id).eq("tenant_id", tenant_id).single().execute()

        if not env_response.data:
            return await self._fail_artifact(
                tenant_id, artifact_id, "Environment not found"
            )

        env = env_response.data

        # Check Git is configured
        if not env.get("git_repo_url") or not env.get("git_pat"):
            return await self._fail_artifact(
                tenant_id, artifact_id, "Git not configured for environment"
            )

        try:
            # Get affected workflows from incident
            affected = incident.get("affected_workflows", [])

            # Call GitHub service to sync workflows to Git
            # This creates a commit with the current runtime state
            result = await github_service.sync_workflows_to_git(
                tenant_id=tenant_id,
                environment_id=environment_id,
                workflow_ids=[w.get("workflow_id") for w in affected if w.get("workflow_id")],
            )

            # Update artifact with success
            external_refs = {
                "commit_sha": result.get("commit_sha"),
                "branch": result.get("branch"),
                "pr_url": result.get("pr_url"),
            }

            return await self._complete_artifact(
                tenant_id, artifact_id, external_refs
            )

        except Exception as e:
            return await self._fail_artifact(
                tenant_id, artifact_id, str(e)
            )

    async def execute_revert(
        self,
        tenant_id: str,
        artifact_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Execute revert reconciliation.
        Deploys Git state back to runtime.
        """
        artifact = await self._get_artifact(tenant_id, artifact_id)
        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reconciliation artifact not found",
            )

        if artifact["type"] != ResolutionType.revert.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Artifact is not a revert type",
            )

        # Get incident and environment
        incident = await self._get_incident(tenant_id, artifact["incident_id"])
        if not incident:
            return await self._fail_artifact(
                tenant_id, artifact_id, "Incident not found"
            )

        environment_id = incident["environment_id"]

        try:
            # Import from Git to runtime
            result = await github_service.sync_workflows_from_git(
                tenant_id=tenant_id,
                environment_id=environment_id,
            )

            # Update artifact with success
            external_refs = {
                "restored_from_sha": result.get("commit_sha"),
                "workflows_restored": result.get("workflow_count", 0),
            }

            return await self._complete_artifact(
                tenant_id, artifact_id, external_refs
            )

        except Exception as e:
            return await self._fail_artifact(
                tenant_id, artifact_id, str(e)
            )

    async def mark_replaced(
        self,
        tenant_id: str,
        artifact_id: str,
        user_id: str,
        external_refs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Mark a replace-type artifact as complete.
        Used when Git was updated via external process (e.g., manual commit).
        """
        artifact = await self._get_artifact(tenant_id, artifact_id)
        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reconciliation artifact not found",
            )

        if artifact["type"] != ResolutionType.replace.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Artifact is not a replace type",
            )

        return await self._complete_artifact(
            tenant_id, artifact_id, external_refs or {}
        )

    async def get_artifacts_for_incident(
        self,
        tenant_id: str,
        incident_id: str,
    ) -> List[Dict[str, Any]]:
        """Get all reconciliation artifacts for an incident."""
        try:
            response = db_service.client.table(
                "drift_reconciliation_artifacts"
            ).select("*").eq("tenant_id", tenant_id).eq(
                "incident_id", incident_id
            ).order("created_at", desc=True).execute()

            return response.data or []
        except Exception:
            return []

    async def _get_incident(
        self, tenant_id: str, incident_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a drift incident."""
        try:
            response = db_service.client.table("drift_incidents").select(
                "*"
            ).eq("tenant_id", tenant_id).eq("id", incident_id).single().execute()
            return response.data
        except Exception:
            return None

    async def _get_artifact(
        self, tenant_id: str, artifact_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a reconciliation artifact."""
        try:
            response = db_service.client.table(
                "drift_reconciliation_artifacts"
            ).select("*").eq("tenant_id", tenant_id).eq(
                "id", artifact_id
            ).single().execute()
            return response.data
        except Exception:
            return None

    async def _complete_artifact(
        self,
        tenant_id: str,
        artifact_id: str,
        external_refs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Mark an artifact as successfully completed."""
        now = datetime.utcnow().isoformat()

        update_data = {
            "status": ReconciliationStatus.success.value,
            "finished_at": now,
            "external_refs": external_refs,
            "updated_at": now,
        }

        response = db_service.client.table(
            "drift_reconciliation_artifacts"
        ).update(update_data).eq("id", artifact_id).eq(
            "tenant_id", tenant_id
        ).execute()

        return response.data[0] if response.data else {}

    async def _fail_artifact(
        self,
        tenant_id: str,
        artifact_id: str,
        error_message: str,
    ) -> Dict[str, Any]:
        """Mark an artifact as failed."""
        now = datetime.utcnow().isoformat()

        update_data = {
            "status": ReconciliationStatus.failed.value,
            "finished_at": now,
            "error_message": error_message,
            "updated_at": now,
        }

        response = db_service.client.table(
            "drift_reconciliation_artifacts"
        ).update(update_data).eq("id", artifact_id).eq(
            "tenant_id", tenant_id
        ).execute()

        return response.data[0] if response.data else {}


# Singleton instance
reconciliation_service = ReconciliationService()
