from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import Dict, Any, Set

from app.schemas.support import (
    SupportRequestCreate,
    SupportRequestResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.services.support_service import support_service
from app.services.support_attachments_service import create_attachment_record, upload_attachment_bytes, link_attachments_to_request
from app.core.entitlements_gate import require_entitlement
from app.services.auth_service import get_current_user
from app.services.database import db_service

router = APIRouter()

# Security constants for file uploads
MAX_UPLOAD_SIZE_MB = 10
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024  # 10MB

# Allowed MIME types for attachments (security: prevent executable uploads)
ALLOWED_CONTENT_TYPES: Set[str] = {
    # Images
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    # Documents
    "application/pdf",
    "text/plain",
    "text/csv",
    "text/markdown",
    # Data formats
    "application/json",
    "application/xml",
    "text/xml",
    # Archives (for log bundles)
    "application/zip",
    "application/gzip",
    # Fallback for unknown but safe binary
    "application/octet-stream",
}


def _tenant_id(user_info: dict) -> str:
    tenant = user_info.get("tenant") or {}
    tid = tenant.get("id")
    if not tid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return tid


def _actor(user_info: dict) -> tuple[str, str | None]:
    user = user_info.get("user") or {}
    return (user.get("email") or "", user.get("id"))


@router.post("/requests", response_model=SupportRequestResponse)
async def create_support_request(
    data: SupportRequestCreate,
    user_info: dict = Depends(get_current_user),
    # _: dict = Depends(require_entitlement("support_enabled"))
) -> SupportRequestResponse:
    """
    Create a support request (bug report, feature request, or help request).

    The request is forwarded to n8n which creates the JSM ticket.
    Returns the JSM request key immediately.
    """
    try:
        tenant_id = _tenant_id(user_info)
        user_email, user_id = _actor(user_info)
        # Build Issue Contract from request data
        contract = await support_service.build_issue_contract(
            request=data,
            user_email=user_email,
            user_id=user_id,
            tenant_id=tenant_id,
            diagnostics=data.diagnostics
        )

        # Forward to n8n and get JSM key
        response = await support_service.forward_to_n8n(contract, tenant_id)

        # Persist request + link attachments for admin viewing
        try:
            req_row = db_service.client.table("support_requests").insert(
                {
                    "tenant_id": tenant_id,
                    "created_by_user_id": user_id,
                    "created_by_email": user_email,
                    "intent_kind": data.intent_kind.value if hasattr(data.intent_kind, "value") else str(data.intent_kind),
                    "jsm_request_key": response.jsm_request_key,
                    "payload_json": data.model_dump(),
                }
            ).execute()
            created = (req_row.data or [None])[0]
            if created:
                attachment_ids = []
                if data.bug_report and data.bug_report.attachment_ids:
                    attachment_ids += data.bug_report.attachment_ids
                if data.help_request and data.help_request.attachment_ids:
                    attachment_ids += data.help_request.attachment_ids
                attachment_ids = [a for a in attachment_ids if a]
                if attachment_ids:
                    await link_attachments_to_request(tenant_id, created["id"], attachment_ids)
        except Exception:
            pass

        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create support request: {str(e)}"
        )


@router.post("/upload-url", response_model=UploadUrlResponse)
async def get_upload_url(
    data: UploadUrlRequest,
    user_info: dict = Depends(get_current_user),
    # _: dict = Depends(require_entitlement("support_enabled"))
) -> UploadUrlResponse:
    """
    Get a signed upload URL for file attachments.

    The frontend uses this URL to upload files directly to storage.
    """
    try:
        tenant_id = _tenant_id(user_info)
        user_email, user_id = _actor(user_info)
        row = await create_attachment_record(
            tenant_id=tenant_id,
            uploader_user_id=user_id,
            uploader_email=user_email,
            filename=data.filename,
            content_type=data.content_type,
        )
        return UploadUrlResponse(
            attachment_id=row["id"],
            upload_url=f"support/attachments/{row['id']}/upload",
            public_url=f"support://attachment/{row['id']}",
            method="PUT",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate upload URL: {str(e)}"
        )


@router.put("/attachments/{attachment_id}/upload")
async def upload_attachment(
    attachment_id: str,
    request: Request,
    user_info: dict = Depends(get_current_user),
):
    """
    Upload attachment bytes to private Supabase Storage (server-side upload).
    Client should PUT raw bytes with Content-Type set.

    Security measures:
    - File size limit: 10MB max
    - Content-Type validation against allowlist
    """
    try:
        tenant_id = _tenant_id(user_info)

        # Security: Validate Content-Length header before reading body
        content_length_header = request.headers.get("content-length")
        if content_length_header:
            try:
                content_length = int(content_length_header)
                if content_length > MAX_UPLOAD_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE_MB}MB"
                    )
            except ValueError:
                pass  # Invalid content-length header, will validate after reading

        # Security: Validate Content-Type against allowlist
        content_type = request.headers.get("content-type") or "application/octet-stream"
        # Extract base content type (ignore charset and other parameters)
        base_content_type = content_type.split(";")[0].strip().lower()

        if base_content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"File type '{base_content_type}' is not allowed. Allowed types: images, PDFs, text files, JSON, XML, and archives."
            )

        # Read body with size limit enforcement
        body = await request.body()

        if not body:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty upload")

        # Security: Validate actual body size (defense in depth)
        if len(body) > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE_MB}MB"
            )

        await upload_attachment_bytes(
            tenant_id=tenant_id,
            attachment_id=attachment_id,
            content_type=base_content_type,
            data=body
        )
        return {"success": True, "attachment_id": attachment_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload attachment"  # Generic message to avoid info disclosure
        )
