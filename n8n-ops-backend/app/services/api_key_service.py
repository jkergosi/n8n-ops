"""Tenant API key service.

# Migration: 7c76f55a6ef6 - create_tenant_api_keys
# See: alembic/versions/7c76f55a6ef6_create_tenant_api_keys.py
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.services.database import db_service


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_key(key: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{key}".encode("utf-8")).hexdigest()


def _new_api_key() -> str:
    # Format: n8nops_<url-safe random>
    return f"n8nops_{secrets.token_urlsafe(32)}"


def _key_prefix(key: str) -> str:
    # Prefix safe to display, used for lookups.
    return key[:12]


async def list_keys(tenant_id: str) -> List[Dict[str, Any]]:
    resp = (
        db_service.client.table("tenant_api_keys")
        .select("id, name, key_prefix, scopes, created_at, last_used_at, revoked_at, is_active")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .execute()
    )
    return resp.data or []


async def create_key(tenant_id: str, name: str, scopes: List[str]) -> Dict[str, Any]:
    api_key = _new_api_key()
    prefix = _key_prefix(api_key)
    salt = secrets.token_hex(16)
    key_hash = _hash_key(api_key, salt)
    now = _now_iso()

    insert_resp = db_service.client.table("tenant_api_keys").insert(
        {
            "tenant_id": tenant_id,
            "name": name,
            "key_prefix": prefix,
            "key_hash": key_hash,
            "key_salt": salt,
            "scopes": scopes,
            "created_at": now,
            "is_active": True,
        }
    ).execute()

    row = (insert_resp.data or [None])[0]
    return {"api_key": api_key, "row": row}


async def revoke_key(tenant_id: str, key_id: str) -> Optional[Dict[str, Any]]:
    now = _now_iso()
    resp = (
        db_service.client.table("tenant_api_keys")
        .update({"is_active": False, "revoked_at": now})
        .eq("tenant_id", tenant_id)
        .eq("id", key_id)
        .execute()
    )
    if resp.data:
        return resp.data[0]
    return None


