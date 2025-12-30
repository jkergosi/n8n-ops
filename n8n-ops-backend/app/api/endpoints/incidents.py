from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional

from app.core.entitlements_gate import require_entitlement
from app.services.database import db_service
from app.schemas.drift_incident import DriftIncidentResponse


router = APIRouter()

# TODO: Replace with actual tenant ID from authenticated user (align with environments.py)
MOCK_TENANT_ID = "00000000-0000-0000-0000-000000000000"


@router.get("/", response_model=List[DriftIncidentResponse], response_model_exclude_none=False)
async def list_incidents(
    environment_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    _: dict = Depends(require_entitlement("environment_basic")),
):
    try:
        incidents = await db_service.get_drift_incidents(
            tenant_id=MOCK_TENANT_ID,
            environment_id=environment_id,
            status=status_filter,
            limit=limit,
        )
        return incidents
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch incidents: {str(e)}",
        )


@router.get("/{incident_id}", response_model=DriftIncidentResponse, response_model_exclude_none=False)
async def get_incident(
    incident_id: str,
    _: dict = Depends(require_entitlement("environment_basic")),
):
    try:
        incident = await db_service.get_drift_incident(tenant_id=MOCK_TENANT_ID, incident_id=incident_id)
        if not incident:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
        return incident
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch incident: {str(e)}",
        )


