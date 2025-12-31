"""Drift Incident Service with full lifecycle management."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from app.services.database import db_service
from app.services.feature_service import feature_service
from app.schemas.drift_incident import (
    DriftIncidentStatus,
    DriftSeverity,
    ResolutionType,
    AffectedWorkflow,
)


# Valid status transitions
VALID_TRANSITIONS = {
    DriftIncidentStatus.detected: [DriftIncidentStatus.acknowledged, DriftIncidentStatus.closed],
    DriftIncidentStatus.acknowledged: [DriftIncidentStatus.stabilized, DriftIncidentStatus.reconciled, DriftIncidentStatus.closed],
    DriftIncidentStatus.stabilized: [DriftIncidentStatus.reconciled, DriftIncidentStatus.closed],
    DriftIncidentStatus.reconciled: [DriftIncidentStatus.closed],
    DriftIncidentStatus.closed: [],  # Terminal state
}


class DriftIncidentService:
    """Service for managing drift incident lifecycle."""

    async def get_incidents(
        self,
        tenant_id: str,
        environment_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Get drift incidents with pagination."""
        try:
            query = db_service.client.table("drift_incidents").select(
                "*", count="exact"
            ).eq("tenant_id", tenant_id)

            if environment_id:
                query = query.eq("environment_id", environment_id)
            if status_filter:
                query = query.eq("status", status_filter)

            response = query.order(
                "detected_at", desc=True
            ).range(offset, offset + limit - 1).execute()

            return {
                "items": response.data or [],
                "total": response.count or 0,
                "has_more": (response.count or 0) > offset + limit,
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch incidents: {str(e)}",
            )

    async def get_incident(
        self, tenant_id: str, incident_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a single drift incident."""
        try:
            response = db_service.client.table("drift_incidents").select(
                "*"
            ).eq("tenant_id", tenant_id).eq("id", incident_id).single().execute()
            return response.data
        except Exception:
            return None

    async def get_active_incident_for_environment(
        self, tenant_id: str, environment_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get the active (non-closed) drift incident for an environment."""
        try:
            response = db_service.client.table("drift_incidents").select(
                "*"
            ).eq("tenant_id", tenant_id).eq(
                "environment_id", environment_id
            ).neq("status", "closed").order(
                "detected_at", desc=True
            ).limit(1).execute()

            return response.data[0] if response.data else None
        except Exception:
            return None

    async def create_incident(
        self,
        tenant_id: str,
        environment_id: str,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        affected_workflows: Optional[List[AffectedWorkflow]] = None,
        drift_snapshot: Optional[Dict[str, Any]] = None,
        severity: Optional[DriftSeverity] = None,
    ) -> Dict[str, Any]:
        """Create a new drift incident."""
        # Check if there's already an active incident
        existing = await self.get_active_incident_for_environment(tenant_id, environment_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "active_incident_exists",
                    "incident_id": existing["id"],
                    "message": "An active drift incident already exists for this environment",
                },
            )

        now = datetime.utcnow().isoformat()

        payload = {
            "tenant_id": tenant_id,
            "environment_id": environment_id,
            "status": DriftIncidentStatus.detected.value,
            "detected_at": now,
            "created_by": user_id,
            "affected_workflows": [w.model_dump() for w in affected_workflows] if affected_workflows else [],
            "drift_snapshot": drift_snapshot,
        }

        if title:
            payload["title"] = title
        if severity:
            payload["severity"] = severity.value

        try:
            response = db_service.client.table("drift_incidents").insert(
                payload
            ).execute()
            incident = response.data[0] if response.data else None

            if not incident:
                raise Exception("Failed to insert incident")

            # Update environment to point to this incident
            db_service.client.table("environments").update({
                "drift_status": "DRIFT_DETECTED",
                "active_drift_incident_id": incident["id"],
                "last_drift_detected_at": now,
            }).eq("id", environment_id).eq("tenant_id", tenant_id).execute()

            return incident
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create incident: {str(e)}",
            )

    async def update_incident(
        self,
        tenant_id: str,
        incident_id: str,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        owner_user_id: Optional[str] = None,
        reason: Optional[str] = None,
        ticket_ref: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        severity: Optional[DriftSeverity] = None,
    ) -> Dict[str, Any]:
        """Update incident fields (not status transitions)."""
        incident = await self.get_incident(tenant_id, incident_id)
        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Incident not found",
            )

        update_data = {"updated_at": datetime.utcnow().isoformat()}

        if title is not None:
            update_data["title"] = title
        if owner_user_id is not None:
            update_data["owner_user_id"] = owner_user_id
        if reason is not None:
            update_data["reason"] = reason
        if ticket_ref is not None:
            update_data["ticket_ref"] = ticket_ref
        if expires_at is not None:
            # Check if tenant has TTL feature
            features = await feature_service.get_tenant_features(tenant_id)
            if features.get("drift_ttl_sla"):
                update_data["expires_at"] = expires_at.isoformat()
        if severity is not None:
            update_data["severity"] = severity.value

        try:
            response = db_service.client.table("drift_incidents").update(
                update_data
            ).eq("id", incident_id).eq("tenant_id", tenant_id).execute()

            return response.data[0] if response.data else incident
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update incident: {str(e)}",
            )

    def _validate_transition(
        self, current_status: str, new_status: DriftIncidentStatus
    ) -> bool:
        """Check if a status transition is valid."""
        current = DriftIncidentStatus(current_status)
        return new_status in VALID_TRANSITIONS.get(current, [])

    async def acknowledge_incident(
        self,
        tenant_id: str,
        incident_id: str,
        user_id: str,
        reason: Optional[str] = None,
        owner_user_id: Optional[str] = None,
        ticket_ref: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Acknowledge a drift incident."""
        incident = await self.get_incident(tenant_id, incident_id)
        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Incident not found",
            )

        if not self._validate_transition(
            incident["status"], DriftIncidentStatus.acknowledged
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot acknowledge incident in '{incident['status']}' status",
            )

        now = datetime.utcnow().isoformat()
        update_data = {
            "status": DriftIncidentStatus.acknowledged.value,
            "acknowledged_at": now,
            "acknowledged_by": user_id,
            "updated_at": now,
        }

        if reason:
            update_data["reason"] = reason
        if owner_user_id:
            update_data["owner_user_id"] = owner_user_id
        if ticket_ref:
            update_data["ticket_ref"] = ticket_ref
        if expires_at:
            features = await feature_service.get_tenant_features(tenant_id)
            if features.get("drift_ttl_sla"):
                update_data["expires_at"] = expires_at.isoformat()

        try:
            response = db_service.client.table("drift_incidents").update(
                update_data
            ).eq("id", incident_id).eq("tenant_id", tenant_id).execute()

            return response.data[0] if response.data else incident
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to acknowledge incident: {str(e)}",
            )

    async def stabilize_incident(
        self,
        tenant_id: str,
        incident_id: str,
        user_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mark incident as stabilized (no new drift changes)."""
        incident = await self.get_incident(tenant_id, incident_id)
        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Incident not found",
            )

        if not self._validate_transition(
            incident["status"], DriftIncidentStatus.stabilized
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot stabilize incident in '{incident['status']}' status",
            )

        now = datetime.utcnow().isoformat()
        update_data = {
            "status": DriftIncidentStatus.stabilized.value,
            "stabilized_at": now,
            "stabilized_by": user_id,
            "updated_at": now,
        }

        if reason:
            update_data["reason"] = reason

        try:
            response = db_service.client.table("drift_incidents").update(
                update_data
            ).eq("id", incident_id).eq("tenant_id", tenant_id).execute()

            return response.data[0] if response.data else incident
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to stabilize incident: {str(e)}",
            )

    async def reconcile_incident(
        self,
        tenant_id: str,
        incident_id: str,
        user_id: str,
        resolution_type: ResolutionType,
        reason: Optional[str] = None,
        resolution_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Mark incident as reconciled with resolution tracking."""
        incident = await self.get_incident(tenant_id, incident_id)
        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Incident not found",
            )

        if not self._validate_transition(
            incident["status"], DriftIncidentStatus.reconciled
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reconcile incident in '{incident['status']}' status",
            )

        now = datetime.utcnow().isoformat()
        update_data = {
            "status": DriftIncidentStatus.reconciled.value,
            "reconciled_at": now,
            "reconciled_by": user_id,
            "resolution_type": resolution_type.value,
            "updated_at": now,
        }

        if reason:
            update_data["reason"] = reason
        if resolution_details:
            update_data["resolution_details"] = resolution_details

        try:
            response = db_service.client.table("drift_incidents").update(
                update_data
            ).eq("id", incident_id).eq("tenant_id", tenant_id).execute()

            return response.data[0] if response.data else incident
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to reconcile incident: {str(e)}",
            )

    async def close_incident(
        self,
        tenant_id: str,
        incident_id: str,
        user_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Close a drift incident."""
        incident = await self.get_incident(tenant_id, incident_id)
        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Incident not found",
            )

        if not self._validate_transition(
            incident["status"], DriftIncidentStatus.closed
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot close incident in '{incident['status']}' status",
            )

        now = datetime.utcnow().isoformat()
        update_data = {
            "status": DriftIncidentStatus.closed.value,
            "closed_at": now,
            "closed_by": user_id,
            "updated_at": now,
        }

        if reason:
            update_data["reason"] = reason

        try:
            response = db_service.client.table("drift_incidents").update(
                update_data
            ).eq("id", incident_id).eq("tenant_id", tenant_id).execute()

            # Clear environment's active incident reference
            db_service.client.table("environments").update({
                "active_drift_incident_id": None,
                "drift_status": "IN_SYNC",
            }).eq(
                "id", incident["environment_id"]
            ).eq("tenant_id", tenant_id).execute()

            return response.data[0] if response.data else incident
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to close incident: {str(e)}",
            )

    async def refresh_incident_drift(
        self,
        tenant_id: str,
        incident_id: str,
        affected_workflows: List[AffectedWorkflow],
        drift_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update incident with latest drift data."""
        incident = await self.get_incident(tenant_id, incident_id)
        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Incident not found",
            )

        if incident["status"] == DriftIncidentStatus.closed.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update closed incident",
            )

        update_data = {
            "affected_workflows": [w.model_dump() for w in affected_workflows],
            "updated_at": datetime.utcnow().isoformat(),
        }

        if drift_snapshot:
            update_data["drift_snapshot"] = drift_snapshot

        try:
            response = db_service.client.table("drift_incidents").update(
                update_data
            ).eq("id", incident_id).eq("tenant_id", tenant_id).execute()

            return response.data[0] if response.data else incident
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to refresh incident drift: {str(e)}",
            )

    async def get_incident_stats(
        self, tenant_id: str, environment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get incident statistics."""
        try:
            base_query = db_service.client.table("drift_incidents").select(
                "status", count="exact"
            ).eq("tenant_id", tenant_id)

            if environment_id:
                base_query = base_query.eq("environment_id", environment_id)

            # Get counts by status
            stats = {"total": 0, "by_status": {}}

            for status_val in DriftIncidentStatus:
                response = base_query.eq(
                    "status", status_val.value
                ).execute()
                count = response.count or 0
                stats["by_status"][status_val.value] = count
                stats["total"] += count

            # Get open incidents count
            stats["open"] = (
                stats["by_status"].get("detected", 0) +
                stats["by_status"].get("acknowledged", 0) +
                stats["by_status"].get("stabilized", 0)
            )

            return stats
        except Exception:
            return {"total": 0, "open": 0, "by_status": {}}


# Singleton instance
drift_incident_service = DriftIncidentService()
