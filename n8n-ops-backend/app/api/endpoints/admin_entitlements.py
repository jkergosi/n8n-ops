"""Admin endpoints for entitlements management (Phase 4)."""
from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime

from app.schemas.entitlements import (
    FeatureType,
    FeatureStatus,
    PlanResponse,
    FeatureMatrixEntry,
    FeatureMatrixResponse,
    PlanFeatureUpdate,
    PlanFeatureValueResponse,
    AdminFeatureResponse,
    AdminFeatureListResponse,
    AdminPlanResponse,
    AdminPlanListResponse,
    AuditAction,
    AuditEntityType,
)
from app.services.database import db_service
from app.services.audit_service import audit_service
from app.services.entitlements_service import entitlements_service

router = APIRouter()


# =============================================================================
# Feature Management
# =============================================================================

@router.get("/features", response_model=AdminFeatureListResponse)
async def get_all_features(
    status_filter: Optional[str] = Query(None, description="Filter by status (active, deprecated, hidden)"),
    type_filter: Optional[str] = Query(None, description="Filter by type (flag, limit)"),
):
    """Get all features (admin only)."""
    try:
        query = db_service.client.table("features").select("*")

        if status_filter:
            query = query.eq("status", status_filter)
        if type_filter:
            query = query.eq("type", type_filter)

        response = query.order("name").execute()

        features = []
        for row in response.data or []:
            features.append(AdminFeatureResponse(
                id=row["id"],
                key=row["name"],
                display_name=row["display_name"],
                description=row.get("description"),
                type=row["type"],
                default_value=row.get("default_value", {}),
                status=row.get("status", "active"),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            ))

        return AdminFeatureListResponse(
            features=features,
            total=len(features)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch features: {str(e)}"
        )


@router.get("/features/{feature_id}", response_model=AdminFeatureResponse)
async def get_feature(feature_id: str):
    """Get a specific feature (admin only)."""
    try:
        response = db_service.client.table("features").select("*").eq(
            "id", feature_id
        ).single().execute()

        if not response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature not found")

        row = response.data
        return AdminFeatureResponse(
            id=row["id"],
            key=row["name"],
            display_name=row["display_name"],
            description=row.get("description"),
            type=row["type"],
            default_value=row.get("default_value", {}),
            status=row.get("status", "active"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch feature: {str(e)}"
        )


# =============================================================================
# Plan Management
# =============================================================================

@router.get("/plans", response_model=AdminPlanListResponse)
async def get_all_plans():
    """Get all plans with tenant counts (admin only)."""
    try:
        response = db_service.client.table("plans").select("*").order("sort_order").execute()

        plans = []
        for row in response.data or []:
            # Get tenant count for this plan
            tenant_count_response = db_service.client.table("tenant_plans").select(
                "id", count="exact"
            ).eq("plan_id", row["id"]).eq("is_active", True).execute()
            tenant_count = tenant_count_response.count or 0

            plans.append(AdminPlanResponse(
                id=row["id"],
                name=row["name"],
                display_name=row["display_name"],
                description=row.get("description"),
                sort_order=row.get("sort_order", 0),
                is_active=row.get("is_active", True),
                tenant_count=tenant_count,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            ))

        return AdminPlanListResponse(
            plans=plans,
            total=len(plans)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch plans: {str(e)}"
        )


@router.get("/plans/{plan_id}", response_model=AdminPlanResponse)
async def get_plan(plan_id: str):
    """Get a specific plan (admin only)."""
    try:
        response = db_service.client.table("plans").select("*").eq(
            "id", plan_id
        ).single().execute()

        if not response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

        row = response.data

        # Get tenant count
        tenant_count_response = db_service.client.table("tenant_plans").select(
            "id", count="exact"
        ).eq("plan_id", plan_id).eq("is_active", True).execute()
        tenant_count = tenant_count_response.count or 0

        return AdminPlanResponse(
            id=row["id"],
            name=row["name"],
            display_name=row["display_name"],
            description=row.get("description"),
            sort_order=row.get("sort_order", 0),
            is_active=row.get("is_active", True),
            tenant_count=tenant_count,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch plan: {str(e)}"
        )


# =============================================================================
# Feature Matrix
# =============================================================================

@router.get("/features/matrix", response_model=FeatureMatrixResponse)
async def get_feature_matrix():
    """
    Get the full feature matrix showing all features and their values across all plans.
    This is the main admin view for managing entitlements.
    """
    try:
        # Get all plans
        plans_response = db_service.client.table("plans").select("*").order("sort_order").execute()
        plans = plans_response.data or []

        # Get all features
        features_response = db_service.client.table("features").select("*").order("name").execute()
        features = features_response.data or []

        # Get all plan-feature mappings
        plan_features_response = db_service.client.table("plan_features").select(
            "plan_id, feature_id, value"
        ).execute()
        plan_features = plan_features_response.data or []

        # Build lookup: {feature_id: {plan_id: value}}
        feature_plan_values = {}
        for pf in plan_features:
            feature_id = pf["feature_id"]
            plan_id = pf["plan_id"]
            if feature_id not in feature_plan_values:
                feature_plan_values[feature_id] = {}
            feature_plan_values[feature_id][plan_id] = pf["value"]

        # Build plan_id to plan_name lookup
        plan_id_to_name = {p["id"]: p["name"] for p in plans}

        # Build matrix entries
        matrix_entries = []
        for feature in features:
            feature_id = feature["id"]
            feature_type = feature["type"]

            # Build plan_values dict with plan names as keys
            plan_values = {}
            for plan in plans:
                plan_id = plan["id"]
                plan_name = plan["name"]
                if feature_id in feature_plan_values and plan_id in feature_plan_values[feature_id]:
                    raw_value = feature_plan_values[feature_id][plan_id]
                    # Extract the actual value based on feature type
                    if feature_type == "flag":
                        plan_values[plan_name] = raw_value.get("enabled", False)
                    else:  # limit
                        plan_values[plan_name] = raw_value.get("value", 0)
                else:
                    # Default value if no mapping exists
                    if feature_type == "flag":
                        plan_values[plan_name] = False
                    else:
                        plan_values[plan_name] = 0

            matrix_entries.append(FeatureMatrixEntry(
                feature_id=feature_id,
                feature_key=feature["name"],
                feature_display_name=feature["display_name"],
                feature_type=feature_type,
                description=feature.get("description"),
                status=feature.get("status", "active"),
                plan_values=plan_values,
            ))

        # Build plan responses
        plan_responses = [
            PlanResponse(
                id=p["id"],
                name=p["name"],
                display_name=p["display_name"],
                description=p.get("description"),
                sort_order=p.get("sort_order", 0),
                is_active=p.get("is_active", True),
            )
            for p in plans
        ]

        return FeatureMatrixResponse(
            features=matrix_entries,
            plans=plan_responses,
            total_features=len(matrix_entries),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch feature matrix: {str(e)}"
        )


# =============================================================================
# Plan-Feature Value Editing
# =============================================================================

@router.patch("/plans/{plan_id}/features/{feature_key}", response_model=PlanFeatureValueResponse)
async def update_plan_feature_value(
    plan_id: str,
    feature_key: str,
    update: PlanFeatureUpdate,
):
    """
    Update a plan-feature value (admin only).
    This changes the base entitlement for all tenants on this plan.
    """
    try:
        # Verify plan exists
        plan_response = db_service.client.table("plans").select("id, name").eq(
            "id", plan_id
        ).single().execute()
        if not plan_response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
        plan = plan_response.data

        # Find feature by key
        feature_response = db_service.client.table("features").select("id, name, type").eq(
            "name", feature_key
        ).single().execute()
        if not feature_response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Feature '{feature_key}' not found"
            )
        feature = feature_response.data

        # Validate value format based on feature type
        feature_type = feature["type"]
        if feature_type == "flag":
            if "enabled" not in update.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Flag features require {'enabled': true/false}"
                )
        elif feature_type == "limit":
            if "value" not in update.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Limit features require {'value': number}"
                )

        # Check if plan_feature mapping exists
        existing = db_service.client.table("plan_features").select("id, value").eq(
            "plan_id", plan_id
        ).eq("feature_id", feature["id"]).execute()

        old_value = None
        if existing.data:
            # Update existing mapping
            old_value = existing.data[0]["value"]
            db_service.client.table("plan_features").update({
                "value": update.value
            }).eq("id", existing.data[0]["id"]).execute()
        else:
            # Create new mapping
            db_service.client.table("plan_features").insert({
                "plan_id": plan_id,
                "feature_id": feature["id"],
                "value": update.value,
            }).execute()

        # Log the change to audit
        await audit_service.log_config_change(
            tenant_id=None,  # System-wide change
            entity_type=AuditEntityType.PLAN_FEATURE,
            entity_id=f"{plan_id}:{feature['id']}",
            action=AuditAction.UPDATE if old_value else AuditAction.CREATE,
            old_value=old_value,
            new_value=update.value,
            feature_key=feature_key,
            reason=update.reason,
        )

        # Clear all caches since this affects all tenants on this plan
        entitlements_service.clear_cache()

        return PlanFeatureValueResponse(
            plan_id=plan_id,
            plan_name=plan["name"],
            feature_id=feature["id"],
            feature_key=feature_key,
            value=update.value,
            updated_at=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update plan feature: {str(e)}"
        )


@router.get("/plans/{plan_id}/features", response_model=List[PlanFeatureValueResponse])
async def get_plan_features(plan_id: str):
    """Get all feature values for a specific plan (admin only)."""
    try:
        # Verify plan exists
        plan_response = db_service.client.table("plans").select("id, name").eq(
            "id", plan_id
        ).single().execute()
        if not plan_response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
        plan = plan_response.data

        # Get all plan-feature mappings with feature details
        response = db_service.client.table("plan_features").select(
            "*, feature:feature_id(id, name)"
        ).eq("plan_id", plan_id).execute()

        features = []
        for row in response.data or []:
            feature = row.get("feature", {}) or {}
            features.append(PlanFeatureValueResponse(
                plan_id=plan_id,
                plan_name=plan["name"],
                feature_id=feature.get("id", row["feature_id"]),
                feature_key=feature.get("name", ""),
                value=row["value"],
                updated_at=row.get("updated_at", datetime.utcnow()),
            ))

        return features

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch plan features: {str(e)}"
        )


# =============================================================================
# Bulk Operations
# =============================================================================

@router.post("/cache/clear")
async def clear_entitlements_cache():
    """Clear all entitlements caches (admin only). Use after bulk updates."""
    try:
        entitlements_service.clear_cache()
        return {"message": "Entitlements cache cleared successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )
