"""
Configuration and feature flag seeding.

Creates drift policies, environment types, and other config.
"""
from datetime import datetime
from typing import Dict, Any

from supabase import Client

from .tenants import get_seed_tenant_ids, deterministic_uuid


# Default environment types (system-wide ordering)
DEFAULT_ENVIRONMENT_TYPES = [
    {"name": "development", "display_name": "Development", "sort_order": 0, "color": "#22c55e"},
    {"name": "staging", "display_name": "Staging", "sort_order": 10, "color": "#f59e0b"},
    {"name": "production", "display_name": "Production", "sort_order": 20, "color": "#ef4444"},
    {"name": "sandbox", "display_name": "Sandbox", "sort_order": 30, "color": "#8b5cf6"},
]


# Default drift policies per tenant
DEFAULT_DRIFT_POLICIES = {
    "acme": {
        "enabled": True,
        "check_interval_minutes": 60,
        "alert_on_drift": True,
        "auto_reconcile": False,
        "ttl_hours": 24,
        "sla_hours": 48,
        "severity_threshold": "medium",
    },
    "enterprise": {
        "enabled": True,
        "check_interval_minutes": 30,
        "alert_on_drift": True,
        "auto_reconcile": True,
        "ttl_hours": 12,
        "sla_hours": 24,
        "severity_threshold": "low",
    },
    "startup": {
        "enabled": False,
        "check_interval_minutes": 1440,  # Daily
        "alert_on_drift": False,
        "auto_reconcile": False,
        "ttl_hours": 168,  # 1 week
        "sla_hours": 336,  # 2 weeks
        "severity_threshold": "high",
    },
}


async def seed_config(client: Client, clean: bool = False) -> Dict[str, Any]:
    """
    Seed configuration data: environment types, drift policies, etc.

    Args:
        client: Supabase client
        clean: If True, delete existing seed config first

    Returns:
        Dict with counts
    """
    results = {
        "environment_types_created": 0,
        "environment_types_skipped": 0,
        "drift_policies_created": 0,
        "drift_policies_skipped": 0,
    }

    now = datetime.utcnow().isoformat()
    tenant_ids = get_seed_tenant_ids()

    # Seed environment types for each tenant
    for tenant_key, tenant_id in tenant_ids.items():
        for env_type in DEFAULT_ENVIRONMENT_TYPES:
            type_id = deterministic_uuid(f"{tenant_key}-envtype-{env_type['name']}")

            try:
                # Check if exists
                existing = client.table("environment_types").select("id").eq("id", type_id).execute()

                if existing.data:
                    results["environment_types_skipped"] += 1
                    continue

                type_data = {
                    "id": type_id,
                    "tenant_id": tenant_id,
                    "name": env_type["name"],
                    "display_name": env_type["display_name"],
                    "sort_order": env_type["sort_order"],
                    "color": env_type["color"],
                    "created_at": now,
                    "updated_at": now,
                }

                client.table("environment_types").insert(type_data).execute()
                results["environment_types_created"] += 1

            except Exception as e:
                # Table might not exist, skip
                if "environment_types" in str(e):
                    break
                print(f"    Failed to create environment type: {e}")

    # Seed drift policies
    for tenant_key, policy_config in DEFAULT_DRIFT_POLICIES.items():
        tenant_id = tenant_ids.get(tenant_key)
        if not tenant_id:
            continue

        policy_id = deterministic_uuid(f"{tenant_key}-drift-policy")

        try:
            # Check if exists
            existing = client.table("drift_policies").select("id").eq("tenant_id", tenant_id).execute()

            if existing.data:
                results["drift_policies_skipped"] += 1
                continue

            policy_data = {
                "id": policy_id,
                "tenant_id": tenant_id,
                **policy_config,
                "created_at": now,
                "updated_at": now,
            }

            client.table("drift_policies").insert(policy_data).execute()
            results["drift_policies_created"] += 1
            print(f"    Created drift policy for: {tenant_key}")

        except Exception as e:
            # Table might not exist, skip
            if "drift_policies" in str(e):
                break
            print(f"    Failed to create drift policy: {e}")

    return results


async def seed_notifications_config(client: Client) -> Dict[str, Any]:
    """
    Seed sample notifications for testing.

    Creates a few sample notifications for test users.
    """
    results = {"notifications_created": 0}

    now = datetime.utcnow().isoformat()
    tenant_ids = get_seed_tenant_ids()

    # Sample notifications
    notifications = [
        {
            "type": "info",
            "title": "Welcome to Staging",
            "message": "This is a test environment with synthetic data.",
            "read": False,
        },
        {
            "type": "success",
            "title": "Sync Complete",
            "message": "All workflows have been synchronized successfully.",
            "read": True,
        },
        {
            "type": "warning",
            "title": "Drift Detected",
            "message": "Workflow 'Daily Data Sync' has drifted from Git.",
            "read": False,
        },
    ]

    # Only create for Acme tenant
    acme_id = tenant_ids.get("acme")
    if not acme_id:
        return results

    for i, notif in enumerate(notifications):
        notif_id = deterministic_uuid(f"acme-notification-{i}")

        try:
            existing = client.table("notifications").select("id").eq("id", notif_id).execute()
            if existing.data:
                continue

            notif_data = {
                "id": notif_id,
                "tenant_id": acme_id,
                **notif,
                "created_at": now,
                "updated_at": now,
            }

            client.table("notifications").insert(notif_data).execute()
            results["notifications_created"] += 1

        except Exception:
            pass  # Table might not exist

    return results
