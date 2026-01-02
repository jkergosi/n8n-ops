"""Support attachments service.

# Migration: 947a226f2ac2 - add_support_storage_and_attachments
# See: alembic/versions/947a226f2ac2_add_support_storage_and_attachments.py
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import re

import httpx

from app.core.config import settings
from app.services.database import db_service
from app.services.support_service import support_service


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_filename(name: str) -> str:
    name = name.strip().replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name or "attachment"


def _join_path(*parts: str) -> str:
    cleaned = []
    for p in parts:
        if p is None:
            continue
        s = str(p).strip().strip("/")
        if s:
            cleaned.append(s)
    return "/".join(cleaned)


async def _get_storage_config(tenant_id: str) -> tuple[str, str]:
    cfg = await support_service.get_config(tenant_id)
    bucket = (cfg.storage_bucket if cfg else None) or "support-attachments"
    base_prefix = (cfg.storage_prefix if cfg else None) or "support"
    prefix = _join_path(base_prefix, tenant_id)
    return bucket, prefix


async def create_attachment_record(
    tenant_id: str,
    uploader_user_id: Optional[str],
    uploader_email: Optional[str],
    filename: str,
    content_type: str,
) -> Dict[str, Any]:
    bucket, prefix = await _get_storage_config(tenant_id)
    safe_name = _sanitize_filename(filename)
    created_at = _now_iso()

    # Create row first so we can use the generated id in the object path.
    insert_resp = db_service.client.table("support_attachments").insert(
        {
            "tenant_id": tenant_id,
            "uploader_user_id": uploader_user_id,
            "uploader_email": uploader_email,
            "filename": safe_name,
            "content_type": content_type,
            "object_path": "pending",
            "created_at": created_at,
        }
    ).execute()

    row = (insert_resp.data or [None])[0]
    if not row:
        raise ValueError("Failed to create attachment record")

    object_path = _join_path(prefix, row["id"], safe_name)
    db_service.client.table("support_attachments").update(
        {"object_path": object_path}
    ).eq("tenant_id", tenant_id).eq("id", row["id"]).execute()

    row["object_path"] = object_path
    row["storage_bucket"] = bucket
    return row


async def upload_attachment_bytes(
    tenant_id: str,
    attachment_id: str,
    content_type: str,
    data: bytes,
) -> None:
    # Load attachment row
    resp = (
        db_service.client.table("support_attachments")
        .select("id, tenant_id, object_path")
        .eq("tenant_id", tenant_id)
        .eq("id", attachment_id)
        .single()
        .execute()
    )
    row = resp.data
    if not row:
        raise ValueError("Attachment not found")

    bucket, _ = await _get_storage_config(tenant_id)
    object_path = row["object_path"]
    if not object_path or object_path == "pending":
        raise ValueError("Attachment object path not ready")

    url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/{bucket}/{object_path}"
    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
        "apikey": settings.SUPABASE_SERVICE_KEY,
        "Content-Type": content_type,
        "x-upsert": "false",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(url, headers=headers, content=data)
        if r.status_code >= 300:
            raise ValueError(f"Storage upload failed ({r.status_code}): {r.text}")

    db_service.client.table("support_attachments").update(
        {"size_bytes": len(data)}
    ).eq("tenant_id", tenant_id).eq("id", attachment_id).execute()


async def create_signed_download_url(tenant_id: str, attachment_id: str, expires_seconds: int = 3600) -> str:
    resp = (
        db_service.client.table("support_attachments")
        .select("id, tenant_id, object_path")
        .eq("tenant_id", tenant_id)
        .eq("id", attachment_id)
        .single()
        .execute()
    )
    row = resp.data
    if not row:
        raise ValueError("Attachment not found")

    bucket, _ = await _get_storage_config(tenant_id)
    object_path = row["object_path"]

    url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/sign/{bucket}/{object_path}"
    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
        "apikey": settings.SUPABASE_SERVICE_KEY,
        "Content-Type": "application/json",
    }
    payload = {"expiresIn": int(expires_seconds)}

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, headers=headers, json=payload)
        if r.status_code >= 300:
            raise ValueError(f"Storage signed URL failed ({r.status_code}): {r.text}")
        data = r.json() if r.text else {}

    signed = data.get("signedURL") or data.get("signedUrl") or data.get("signed_url")
    if not signed:
        raise ValueError("Storage did not return signed URL")

    if signed.startswith("http"):
        return signed
    return f"{settings.SUPABASE_URL.rstrip('/')}{signed}"


async def link_attachments_to_request(tenant_id: str, support_request_id: str, attachment_ids: List[str]) -> None:
    if not attachment_ids:
        return
    db_service.client.table("support_attachments").update(
        {"support_request_id": support_request_id}
    ).eq("tenant_id", tenant_id).in_("id", attachment_ids).execute()


