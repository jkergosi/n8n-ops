from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Optional

from app.schemas.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantStats
)
from app.schemas.entitlements import (
    TenantFeatureOverrideCreate,
    TenantFeatureOverrideUpdate,
    TenantFeatureOverrideResponse,
    TenantFeatureOverrideListResponse,
    FeatureConfigAuditListResponse,
    FeatureAccessLogListResponse,
    AuditEntityType,
    AccessResult,
    AuditAction,
)
from app.services.database import db_service
from app.services.audit_service import audit_service
from app.services.entitlements_service import entitlements_service

router = APIRouter()


@router.get("/", response_model=List[TenantResponse])
async def get_tenants():
    """Get all tenants (admin only)"""
    try:
        # Get all tenants
        response = db_service.client.table("tenants").select("*").order("created_at", desc=True).execute()
        tenants = response.data or []

        # Enrich with counts
        enriched_tenants = []
        for tenant in tenants:
            tenant_id = tenant["id"]

            # Get workflow count
            workflow_response = db_service.client.table("workflows").select(
                "id", count="exact"
            ).eq("tenant_id", tenant_id).eq("is_deleted", False).execute()
            workflow_count = workflow_response.count or 0

            # Get environment count
            env_response = db_service.client.table("environments").select(
                "id", count="exact"
            ).eq("tenant_id", tenant_id).execute()
            environment_count = env_response.count or 0

            # Get user count
            user_response = db_service.client.table("users").select(
                "id", count="exact"
            ).eq("tenant_id", tenant_id).execute()
            user_count = user_response.count or 0

            enriched_tenants.append({
                **tenant,
                # Map subscription_tier to subscription_plan for API response
                "subscription_plan": tenant.get("subscription_tier") or tenant.get("subscription_plan", "free"),
                "workflow_count": workflow_count,
                "environment_count": environment_count,
                "user_count": user_count,
                "status": tenant.get("status", "active"),
            })

        return enriched_tenants

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch tenants: {str(e)}"
        )


@router.get("/stats", response_model=TenantStats)
async def get_tenant_stats():
    """Get tenant statistics"""
    try:
        # Get all tenants for stats (subscription_tier is the actual db column)
        # Note: status column may not exist in db, so we just get id and subscription_tier
        response = db_service.client.table("tenants").select("id, subscription_tier").execute()
        tenants = response.data or []

        total = len(tenants)
        # Since status column doesn't exist, all tenants are considered active
        active = total
        suspended = 0
        pending = 0

        # Use subscription_tier from db
        by_plan = {
            "free": sum(1 for t in tenants if t.get("subscription_tier") == "free"),
            "pro": sum(1 for t in tenants if t.get("subscription_tier") == "pro"),
            "enterprise": sum(1 for t in tenants if t.get("subscription_tier") == "enterprise"),
        }

        return {
            "total": total,
            "active": active,
            "suspended": suspended,
            "pending": pending,
            "by_plan": by_plan
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch tenant stats: {str(e)}"
        )


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: str):
    """Get a specific tenant"""
    try:
        response = db_service.client.table("tenants").select("*").eq(
            "id", tenant_id
        ).single().execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )

        tenant = response.data

        # Get counts
        workflow_response = db_service.client.table("workflows").select(
            "id", count="exact"
        ).eq("tenant_id", tenant_id).eq("is_deleted", False).execute()

        env_response = db_service.client.table("environments").select(
            "id", count="exact"
        ).eq("tenant_id", tenant_id).execute()

        user_response = db_service.client.table("users").select(
            "id", count="exact"
        ).eq("tenant_id", tenant_id).execute()

        return {
            **tenant,
            # Map subscription_tier to subscription_plan for API response
            "subscription_plan": tenant.get("subscription_tier") or tenant.get("subscription_plan", "free"),
            "workflow_count": workflow_response.count or 0,
            "environment_count": env_response.count or 0,
            "user_count": user_response.count or 0,
            "status": tenant.get("status", "active"),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch tenant: {str(e)}"
        )


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(tenant: TenantCreate):
    """Create a new tenant"""
    try:
        # Check if email already exists
        existing = db_service.client.table("tenants").select("id").eq(
            "email", tenant.email
        ).execute()

        if existing.data and len(existing.data) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A tenant with this email already exists"
            )

        # Create tenant (use subscription_tier for db column)
        tenant_data = {
            "name": tenant.name,
            "email": tenant.email,
            "subscription_tier": tenant.subscription_plan.value,
            "status": "active"
        }

        response = db_service.client.table("tenants").insert(tenant_data).execute()

        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create tenant"
            )

        created_tenant = response.data[0]
        return {
            **created_tenant,
            # Map subscription_tier to subscription_plan for API response
            "subscription_plan": created_tenant.get("subscription_tier", "free"),
            "workflow_count": 0,
            "environment_count": 0,
            "user_count": 0,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tenant: {str(e)}"
        )


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(tenant_id: str, tenant: TenantUpdate):
    """Update a tenant"""
    try:
        # Check if tenant exists
        existing = db_service.client.table("tenants").select("*").eq(
            "id", tenant_id
        ).single().execute()

        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )

        # Build update data (use subscription_tier for db column)
        update_data = {}
        if tenant.name is not None:
            update_data["name"] = tenant.name
        if tenant.email is not None:
            update_data["email"] = tenant.email
        if tenant.subscription_plan is not None:
            update_data["subscription_tier"] = tenant.subscription_plan.value
        if tenant.status is not None:
            update_data["status"] = tenant.status.value

        if not update_data:
            # No changes, return existing tenant with counts
            return await get_tenant(tenant_id)

        # Update tenant
        response = db_service.client.table("tenants").update(update_data).eq(
            "id", tenant_id
        ).execute()

        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )

        # Return updated tenant with counts
        return await get_tenant(tenant_id)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tenant: {str(e)}"
        )


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(tenant_id: str):
    """Delete a tenant and all associated data"""
    try:
        # Check if tenant exists
        existing = db_service.client.table("tenants").select("*").eq(
            "id", tenant_id
        ).single().execute()

        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )

        # Delete associated data in order (respecting foreign keys)
        # Delete executions
        db_service.client.table("executions").delete().eq("tenant_id", tenant_id).execute()

        # Delete workflows
        db_service.client.table("workflows").delete().eq("tenant_id", tenant_id).execute()

        # Delete workflow snapshots
        db_service.client.table("workflow_snapshots").delete().eq("tenant_id", tenant_id).execute()

        # Delete credentials
        db_service.client.table("credentials").delete().eq("tenant_id", tenant_id).execute()

        # Delete tags
        db_service.client.table("tags").delete().eq("tenant_id", tenant_id).execute()

        # Delete n8n_users
        db_service.client.table("n8n_users").delete().eq("tenant_id", tenant_id).execute()

        # Delete environments
        db_service.client.table("environments").delete().eq("tenant_id", tenant_id).execute()

        # Delete users (team members)
        db_service.client.table("users").delete().eq("tenant_id", tenant_id).execute()

        # Delete deployments
        db_service.client.table("deployments").delete().eq("tenant_id", tenant_id).execute()

        # Finally delete the tenant
        db_service.client.table("tenants").delete().eq("id", tenant_id).execute()

        return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tenant: {str(e)}"
        )


# =============================================================================
# Phase 3: Tenant Feature Overrides
# =============================================================================

@router.get("/{tenant_id}/overrides", response_model=TenantFeatureOverrideListResponse)
async def get_tenant_overrides(tenant_id: str):
    """Get all feature overrides for a tenant (admin only)"""
    try:
        # Verify tenant exists
        tenant_response = db_service.client.table("tenants").select("id").eq(
            "id", tenant_id
        ).single().execute()
        if not tenant_response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

        # Get overrides with feature details
        response = db_service.client.table("tenant_feature_overrides").select(
            "*, feature:feature_id(id, name, display_name), created_by_user:created_by(email)"
        ).eq("tenant_id", tenant_id).order("created_at", desc=True).execute()

        overrides = []
        for row in response.data or []:
            feature = row.get("feature", {}) or {}
            created_by_user = row.get("created_by_user", {}) or {}
            overrides.append(TenantFeatureOverrideResponse(
                id=row["id"],
                tenant_id=row["tenant_id"],
                feature_id=row["feature_id"],
                feature_key=feature.get("name", ""),
                feature_display_name=feature.get("display_name", ""),
                value=row["value"],
                reason=row.get("reason"),
                created_by=row.get("created_by"),
                created_by_email=created_by_user.get("email"),
                expires_at=row.get("expires_at"),
                is_active=row.get("is_active", True),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            ))

        return TenantFeatureOverrideListResponse(
            overrides=overrides,
            total=len(overrides)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch overrides: {str(e)}"
        )


@router.post("/{tenant_id}/overrides", response_model=TenantFeatureOverrideResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant_override(tenant_id: str, override: TenantFeatureOverrideCreate):
    """Create a feature override for a tenant (admin only)"""
    try:
        # Verify tenant exists
        tenant_response = db_service.client.table("tenants").select("id").eq(
            "id", tenant_id
        ).single().execute()
        if not tenant_response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

        # Find feature by key
        feature_response = db_service.client.table("features").select(
            "id, name, display_name, type"
        ).eq("name", override.feature_key).single().execute()
        if not feature_response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Feature '{override.feature_key}' not found"
            )
        feature = feature_response.data

        # Check if override already exists for this tenant+feature
        existing = db_service.client.table("tenant_feature_overrides").select("id").eq(
            "tenant_id", tenant_id
        ).eq("feature_id", feature["id"]).execute()
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Override for feature '{override.feature_key}' already exists. Use PATCH to update."
            )

        # Create override
        override_data = {
            "tenant_id": tenant_id,
            "feature_id": feature["id"],
            "value": override.value,
            "reason": override.reason,
            "expires_at": override.expires_at.isoformat() if override.expires_at else None,
            "is_active": True,
        }

        response = db_service.client.table("tenant_feature_overrides").insert(override_data).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create override"
            )

        created = response.data[0]

        # Clear entitlements cache for this tenant
        entitlements_service.clear_cache(tenant_id)

        return TenantFeatureOverrideResponse(
            id=created["id"],
            tenant_id=created["tenant_id"],
            feature_id=created["feature_id"],
            feature_key=feature["name"],
            feature_display_name=feature["display_name"],
            value=created["value"],
            reason=created.get("reason"),
            created_by=created.get("created_by"),
            created_by_email=None,
            expires_at=created.get("expires_at"),
            is_active=created.get("is_active", True),
            created_at=created["created_at"],
            updated_at=created["updated_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create override: {str(e)}"
        )


@router.patch("/{tenant_id}/overrides/{override_id}", response_model=TenantFeatureOverrideResponse)
async def update_tenant_override(
    tenant_id: str,
    override_id: str,
    override: TenantFeatureOverrideUpdate
):
    """Update a feature override for a tenant (admin only)"""
    try:
        # Get existing override
        existing = db_service.client.table("tenant_feature_overrides").select(
            "*, feature:feature_id(id, name, display_name)"
        ).eq("id", override_id).eq("tenant_id", tenant_id).single().execute()

        if not existing.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Override not found")

        # Build update data
        update_data = {}
        if override.value is not None:
            update_data["value"] = override.value
        if override.reason is not None:
            update_data["reason"] = override.reason
        if override.expires_at is not None:
            update_data["expires_at"] = override.expires_at.isoformat()
        if override.is_active is not None:
            update_data["is_active"] = override.is_active

        if not update_data:
            # No changes
            feature = existing.data.get("feature", {}) or {}
            return TenantFeatureOverrideResponse(
                id=existing.data["id"],
                tenant_id=existing.data["tenant_id"],
                feature_id=existing.data["feature_id"],
                feature_key=feature.get("name", ""),
                feature_display_name=feature.get("display_name", ""),
                value=existing.data["value"],
                reason=existing.data.get("reason"),
                created_by=existing.data.get("created_by"),
                created_by_email=None,
                expires_at=existing.data.get("expires_at"),
                is_active=existing.data.get("is_active", True),
                created_at=existing.data["created_at"],
                updated_at=existing.data["updated_at"],
            )

        response = db_service.client.table("tenant_feature_overrides").update(
            update_data
        ).eq("id", override_id).execute()

        if not response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Override not found")

        # Clear entitlements cache for this tenant
        entitlements_service.clear_cache(tenant_id)

        # Fetch updated record with feature details
        updated = db_service.client.table("tenant_feature_overrides").select(
            "*, feature:feature_id(id, name, display_name)"
        ).eq("id", override_id).single().execute()

        feature = updated.data.get("feature", {}) or {}
        return TenantFeatureOverrideResponse(
            id=updated.data["id"],
            tenant_id=updated.data["tenant_id"],
            feature_id=updated.data["feature_id"],
            feature_key=feature.get("name", ""),
            feature_display_name=feature.get("display_name", ""),
            value=updated.data["value"],
            reason=updated.data.get("reason"),
            created_by=updated.data.get("created_by"),
            created_by_email=None,
            expires_at=updated.data.get("expires_at"),
            is_active=updated.data.get("is_active", True),
            created_at=updated.data["created_at"],
            updated_at=updated.data["updated_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update override: {str(e)}"
        )


@router.delete("/{tenant_id}/overrides/{override_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant_override(tenant_id: str, override_id: str):
    """Delete a feature override for a tenant (admin only)"""
    try:
        # Check if override exists
        existing = db_service.client.table("tenant_feature_overrides").select("id").eq(
            "id", override_id
        ).eq("tenant_id", tenant_id).execute()

        if not existing.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Override not found")

        # Delete override
        db_service.client.table("tenant_feature_overrides").delete().eq(
            "id", override_id
        ).execute()

        # Clear entitlements cache for this tenant
        entitlements_service.clear_cache(tenant_id)

        return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete override: {str(e)}"
        )


# =============================================================================
# Phase 3: Audit Logs
# =============================================================================

@router.get("/{tenant_id}/audit-logs", response_model=FeatureConfigAuditListResponse)
async def get_tenant_config_audit_logs(
    tenant_id: str,
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    feature_key: Optional[str] = Query(None, description="Filter by feature key"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """Get configuration audit logs for a tenant (admin only)"""
    try:
        # Verify tenant exists
        tenant_response = db_service.client.table("tenants").select("id").eq(
            "id", tenant_id
        ).single().execute()
        if not tenant_response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

        # Convert entity_type string to enum if provided
        entity_type_enum = None
        if entity_type:
            try:
                entity_type_enum = AuditEntityType(entity_type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid entity_type. Must be one of: {[e.value for e in AuditEntityType]}"
                )

        logs, total = await audit_service.get_config_audit_logs(
            tenant_id=tenant_id,
            entity_type=entity_type_enum,
            feature_key=feature_key,
            page=page,
            page_size=page_size,
        )

        return FeatureConfigAuditListResponse(
            audits=logs,
            total=total,
            page=page,
            page_size=page_size,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch audit logs: {str(e)}"
        )


@router.get("/{tenant_id}/access-logs", response_model=FeatureAccessLogListResponse)
async def get_tenant_access_logs(
    tenant_id: str,
    feature_key: Optional[str] = Query(None, description="Filter by feature key"),
    result: Optional[str] = Query(None, description="Filter by result (allowed, denied, limit_exceeded)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """Get feature access logs for a tenant (admin only)"""
    try:
        # Verify tenant exists
        tenant_response = db_service.client.table("tenants").select("id").eq(
            "id", tenant_id
        ).single().execute()
        if not tenant_response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

        # Convert result string to enum if provided
        result_enum = None
        if result:
            try:
                result_enum = AccessResult(result)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid result. Must be one of: {[e.value for e in AccessResult]}"
                )

        logs, total = await audit_service.get_access_logs(
            tenant_id=tenant_id,
            feature_key=feature_key,
            result=result_enum,
            page=page,
            page_size=page_size,
        )

        return FeatureAccessLogListResponse(
            logs=logs,
            total=total,
            page=page,
            page_size=page_size,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch access logs: {str(e)}"
        )
