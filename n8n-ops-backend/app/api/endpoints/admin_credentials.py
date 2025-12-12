from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, List
import logging

from app.services.database import db_service
from app.services.provider_registry import ProviderRegistry
from app.schemas.credential import (
    LogicalCredentialCreate,
    LogicalCredentialResponse,
    CredentialMappingCreate,
    CredentialMappingUpdate,
    CredentialMappingResponse,
    CredentialPreflightRequest,
    CredentialPreflightResult,
    CredentialIssue,
    ResolvedMapping,
    CredentialDetail,
    WorkflowCredentialDependencyResponse,
)
from app.api.endpoints.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


def get_current_tenant_id(user_info: dict) -> str:
    tenant = user_info.get("tenant") if user_info else None
    if tenant and tenant.get("id"):
        return tenant.get("id")
    return "00000000-0000-0000-0000-000000000000"


@router.get("/logical", response_model=list[LogicalCredentialResponse])
async def list_logical_credentials(user_info: dict = Depends(get_current_user)):
    tenant_id = get_current_tenant_id(user_info)
    return await db_service.list_logical_credentials(tenant_id)


@router.post("/logical", response_model=LogicalCredentialResponse, status_code=status.HTTP_201_CREATED)
async def create_logical_credential(body: LogicalCredentialCreate, user_info: dict = Depends(get_current_user)):
    tenant_id = get_current_tenant_id(user_info)
    data = body.model_dump()
    data["tenant_id"] = tenant_id
    created = await db_service.create_logical_credential(data)
    return created


@router.patch("/logical/{logical_id}", response_model=LogicalCredentialResponse)
async def update_logical_credential(logical_id: str, body: LogicalCredentialCreate, user_info: dict = Depends(get_current_user)):
    tenant_id = get_current_tenant_id(user_info)
    updated = await db_service.update_logical_credential(tenant_id, logical_id, body.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logical credential not found")
    return updated


@router.delete("/logical/{logical_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_logical_credential(logical_id: str, user_info: dict = Depends(get_current_user)):
    tenant_id = get_current_tenant_id(user_info)
    await db_service.delete_logical_credential(tenant_id, logical_id)
    return {}


@router.get("/mappings", response_model=list[CredentialMappingResponse])
async def list_mappings(environment_id: Optional[str] = None, provider: Optional[str] = None, user_info: dict = Depends(get_current_user)):
    tenant_id = get_current_tenant_id(user_info)
    return await db_service.list_credential_mappings(tenant_id, environment_id=environment_id, provider=provider)


@router.post("/mappings", response_model=CredentialMappingResponse, status_code=status.HTTP_201_CREATED)
async def create_mapping(body: CredentialMappingCreate, user_info: dict = Depends(get_current_user)):
    tenant_id = get_current_tenant_id(user_info)
    data = body.model_dump()
    data["tenant_id"] = tenant_id
    created = await db_service.create_credential_mapping(data)
    return created


@router.patch("/mappings/{mapping_id}", response_model=CredentialMappingResponse)
async def update_mapping(mapping_id: str, body: CredentialMappingUpdate, user_info: dict = Depends(get_current_user)):
    tenant_id = get_current_tenant_id(user_info)
    updated = await db_service.update_credential_mapping(tenant_id, mapping_id, body.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    return updated


@router.delete("/mappings/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(mapping_id: str, user_info: dict = Depends(get_current_user)):
    tenant_id = get_current_tenant_id(user_info)
    await db_service.delete_credential_mapping(tenant_id, mapping_id)
    return {}


@router.post("/preflight", response_model=CredentialPreflightResult)
async def credential_preflight_check(
    body: CredentialPreflightRequest,
    user_info: dict = Depends(get_current_user)
):
    """
    Validate credential mappings for workflows before promotion.
    Returns blocking issues and resolved mappings.
    """
    tenant_id = get_current_tenant_id(user_info)

    blocking_issues: List[CredentialIssue] = []
    warnings: List[CredentialIssue] = []
    resolved_mappings: List[ResolvedMapping] = []

    # Get environment configs
    source_env = await db_service.get_environment(body.source_environment_id, tenant_id)
    target_env = await db_service.get_environment(body.target_environment_id, tenant_id)

    if not source_env:
        raise HTTPException(status_code=404, detail="Source environment not found")
    if not target_env:
        raise HTTPException(status_code=404, detail="Target environment not found")

    # Get target environment credentials
    try:
        target_adapter = ProviderRegistry.get_adapter_for_environment(target_env)
        target_credentials = await target_adapter.get_credentials()
        target_cred_map = {(c.get("type"), c.get("name")): c for c in target_credentials}
    except Exception as e:
        logger.error(f"Failed to fetch target credentials: {e}")
        target_cred_map = {}

    # Process each workflow
    for workflow_id in body.workflow_ids:
        # Get workflow data from cache
        workflow_record = await db_service.get_workflow(tenant_id, body.source_environment_id, workflow_id)
        if not workflow_record:
            blocking_issues.append(CredentialIssue(
                workflow_id=workflow_id,
                workflow_name="Unknown",
                logical_credential_key="",
                issue_type="workflow_not_found",
                message=f"Workflow {workflow_id} not found in source environment",
                is_blocking=True
            ))
            continue

        workflow_name = workflow_record.get("name", "Unknown")
        workflow_data = workflow_record.get("workflow_data", {})

        # Extract logical credentials using provider-specific adapter
        adapter_class = ProviderRegistry.get_adapter_class(body.provider)
        logical_keys = adapter_class.extract_logical_credentials(workflow_data)

        # Check each credential
        nodes = workflow_data.get("nodes", [])
        for node in nodes:
            node_credentials = node.get("credentials", {})
            for cred_type, cred_info in node_credentials.items():
                if isinstance(cred_info, dict):
                    cred_name = cred_info.get("name", "Unknown")
                else:
                    cred_name = str(cred_info) if cred_info else "Unknown"

                logical_key = f"{cred_type}:{cred_name}"

                # Try provider-aware logical mapping first
                logical = await db_service.find_logical_credential_by_name(tenant_id, logical_key)
                if logical:
                    mapping = await db_service.get_mapping_for_logical(
                        tenant_id,
                        body.target_environment_id,
                        body.provider,
                        logical.get("id"),
                    )
                    if not mapping:
                        blocking_issues.append(CredentialIssue(
                            workflow_id=workflow_id,
                            workflow_name=workflow_name,
                            logical_credential_key=logical_key,
                            issue_type="missing_mapping",
                            message=f"No mapping for '{logical_key}' in target environment",
                            is_blocking=True
                        ))
                        continue

                    # Check if mapped physical credential exists
                    mapped_key = (
                        mapping.get("physical_type") or cred_type,
                        mapping.get("physical_name") or cred_name,
                    )
                    if mapped_key not in target_cred_map:
                        blocking_issues.append(CredentialIssue(
                            workflow_id=workflow_id,
                            workflow_name=workflow_name,
                            logical_credential_key=logical_key,
                            issue_type="mapped_missing_in_target",
                            message=f"Mapped credential '{mapping.get('physical_name')}' not found in target",
                            is_blocking=True
                        ))
                        continue

                    # Successfully resolved
                    resolved_mappings.append(ResolvedMapping(
                        logical_key=logical_key,
                        source_physical_name=cred_name,
                        target_physical_name=mapping.get("physical_name") or cred_name,
                        target_physical_id=mapping.get("physical_credential_id") or ""
                    ))
                else:
                    # No logical credential defined - check direct match
                    cred_key = (cred_type, cred_name)
                    if cred_key not in target_cred_map:
                        # Warning: no logical credential and not in target
                        warnings.append(CredentialIssue(
                            workflow_id=workflow_id,
                            workflow_name=workflow_name,
                            logical_credential_key=logical_key,
                            issue_type="no_logical_credential",
                            message=f"'{logical_key}' not defined as logical credential and not found in target",
                            is_blocking=False
                        ))
                    else:
                        # Direct match found
                        target_cred = target_cred_map[cred_key]
                        resolved_mappings.append(ResolvedMapping(
                            logical_key=logical_key,
                            source_physical_name=cred_name,
                            target_physical_name=cred_name,
                            target_physical_id=target_cred.get("id", "")
                        ))

    # Deduplicate resolved mappings
    seen_keys = set()
    unique_resolved = []
    for mapping in resolved_mappings:
        if mapping.logical_key not in seen_keys:
            seen_keys.add(mapping.logical_key)
            unique_resolved.append(mapping)

    return CredentialPreflightResult(
        valid=len(blocking_issues) == 0,
        blocking_issues=blocking_issues,
        warnings=warnings,
        resolved_mappings=unique_resolved
    )


@router.get("/workflows/{workflow_id}/dependencies", response_model=WorkflowCredentialDependencyResponse)
async def get_workflow_dependencies(
    workflow_id: str,
    provider: str = "n8n",
    user_info: dict = Depends(get_current_user)
):
    """Get credential dependencies for a specific workflow."""
    tenant_id = get_current_tenant_id(user_info)

    # Get stored dependencies
    deps = await db_service.get_workflow_dependencies(workflow_id, provider)

    if not deps:
        return WorkflowCredentialDependencyResponse(
            workflow_id=workflow_id,
            provider=provider,
            logical_credential_ids=[],
            credentials=[]
        )

    logical_ids = deps.get("logical_credential_ids", [])

    # Enrich with mapping status
    credentials: List[CredentialDetail] = []
    all_mappings = await db_service.list_credential_mappings(tenant_id, provider=provider)

    for logical_key in logical_ids:
        parts = logical_key.split(":", 1)
        cred_type = parts[0] if len(parts) > 0 else ""
        cred_name = parts[1] if len(parts) > 1 else logical_key

        # Find logical credential
        logical = await db_service.find_logical_credential_by_name(tenant_id, logical_key)

        # Find environments with mappings
        target_envs = []
        mapping_status = "missing"

        if logical:
            for m in all_mappings:
                if m.get("logical_credential_id") == logical.get("id"):
                    target_envs.append(m.get("environment_id"))
                    if m.get("status") == "valid":
                        mapping_status = "valid"
            if target_envs and mapping_status != "valid":
                mapping_status = "invalid"

        credentials.append(CredentialDetail(
            logical_key=logical_key,
            credential_type=cred_type,
            credential_name=cred_name,
            is_mapped=len(target_envs) > 0,
            mapping_status=mapping_status if logical else None,
            target_environments=target_envs
        ))

    return WorkflowCredentialDependencyResponse(
        workflow_id=workflow_id,
        provider=provider,
        logical_credential_ids=logical_ids,
        credentials=credentials,
        updated_at=deps.get("updated_at")
    )


@router.post("/workflows/{workflow_id}/dependencies/refresh")
async def refresh_workflow_dependencies(
    workflow_id: str,
    environment_id: str,
    provider: str = "n8n",
    user_info: dict = Depends(get_current_user)
):
    """Re-extract credential dependencies from workflow data."""
    tenant_id = get_current_tenant_id(user_info)

    # Get workflow from cache
    workflow_record = await db_service.get_workflow(tenant_id, environment_id, workflow_id)
    if not workflow_record:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow_data = workflow_record.get("workflow_data", {})

    # Extract logical credentials using provider-specific adapter
    adapter_class = ProviderRegistry.get_adapter_class(provider)
    logical_keys = adapter_class.extract_logical_credentials(workflow_data)

    # Upsert dependencies
    await db_service.upsert_workflow_dependencies(
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        provider=provider,
        logical_credential_ids=logical_keys,
    )

    return {"success": True, "logical_credential_ids": logical_keys}

