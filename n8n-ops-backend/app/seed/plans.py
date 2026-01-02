"""
Billing plans and entitlements seeding.

Creates subscription plans and tenant plan associations.
"""
from datetime import datetime
from typing import Dict, Any
from decimal import Decimal

from supabase import Client

from .tenants import get_seed_tenant_ids, deterministic_uuid


# Subscription plans (should match what's in billing tables)
SUBSCRIPTION_PLANS = [
    {
        "id": deterministic_uuid("plan-free"),
        "name": "free",
        "display_name": "Free",
        "description": "Get started with basic workflow management",
        "price_monthly": Decimal("0"),
        "price_yearly": Decimal("0"),
        "max_environments": 1,
        "max_team_members": 1,
        "max_workflows": 10,
        "features": {
            "workflow_management": True,
            "basic_executions": True,
            "community_support": True,
            "git_backup": False,
            "environment_promotion": False,
            "advanced_analytics": False,
            "priority_support": False,
            "custom_integrations": False,
            "sso": False,
            "audit_logs": False,
        },
        "is_active": True,
    },
    {
        "id": deterministic_uuid("plan-pro"),
        "name": "pro",
        "display_name": "Pro",
        "description": "For teams that need more power",
        "price_monthly": Decimal("49"),
        "price_yearly": Decimal("490"),
        "max_environments": 5,
        "max_team_members": 10,
        "max_workflows": 100,
        "features": {
            "workflow_management": True,
            "basic_executions": True,
            "community_support": True,
            "git_backup": True,
            "environment_promotion": True,
            "advanced_analytics": True,
            "priority_support": False,
            "custom_integrations": False,
            "sso": False,
            "audit_logs": True,
        },
        "is_active": True,
    },
    {
        "id": deterministic_uuid("plan-agency"),
        "name": "agency",
        "display_name": "Agency",
        "description": "For agencies managing multiple clients",
        "price_monthly": Decimal("199"),
        "price_yearly": Decimal("1990"),
        "max_environments": 25,
        "max_team_members": 50,
        "max_workflows": 500,
        "features": {
            "workflow_management": True,
            "basic_executions": True,
            "community_support": True,
            "git_backup": True,
            "environment_promotion": True,
            "advanced_analytics": True,
            "priority_support": True,
            "custom_integrations": True,
            "sso": False,
            "audit_logs": True,
            "white_label": True,
            "client_management": True,
        },
        "is_active": True,
    },
    {
        "id": deterministic_uuid("plan-enterprise"),
        "name": "enterprise",
        "display_name": "Enterprise",
        "description": "For large organizations with advanced needs",
        "price_monthly": Decimal("499"),
        "price_yearly": Decimal("4990"),
        "max_environments": None,  # Unlimited
        "max_team_members": None,  # Unlimited
        "max_workflows": None,  # Unlimited
        "features": {
            "workflow_management": True,
            "basic_executions": True,
            "community_support": True,
            "git_backup": True,
            "environment_promotion": True,
            "advanced_analytics": True,
            "priority_support": True,
            "custom_integrations": True,
            "sso": True,
            "audit_logs": True,
            "dedicated_support": True,
            "custom_contracts": True,
            "sla_guarantee": True,
        },
        "is_active": True,
    },
]


async def seed_plans(client: Client, clean: bool = False) -> Dict[str, Any]:
    """
    Seed subscription plans.

    Args:
        client: Supabase client
        clean: If True, delete existing seed plans first

    Returns:
        Dict with counts
    """
    results = {
        "plans_created": 0,
        "plans_skipped": 0,
        "plans_updated": 0,
        "tenant_plans_created": 0,
    }

    now = datetime.utcnow().isoformat()

    # Seed subscription_plans table
    for plan_data in SUBSCRIPTION_PLANS:
        try:
            # Check if exists
            existing = client.table("subscription_plans").select("id").eq("name", plan_data["name"]).execute()

            if existing.data:
                # Update existing plan
                plan_id = existing.data[0]["id"]
                update_data = {
                    **plan_data,
                    "id": plan_id,  # Keep existing ID
                    "updated_at": now,
                }
                # Convert Decimal to float for JSON
                update_data["price_monthly"] = float(update_data["price_monthly"])
                if update_data["price_yearly"]:
                    update_data["price_yearly"] = float(update_data["price_yearly"])

                client.table("subscription_plans").update(update_data).eq("id", plan_id).execute()
                results["plans_updated"] += 1
                print(f"    Updated plan: {plan_data['display_name']}")
                continue

            # Create new plan
            full_plan = {
                **plan_data,
                "created_at": now,
                "updated_at": now,
            }
            # Convert Decimal to float for JSON
            full_plan["price_monthly"] = float(full_plan["price_monthly"])
            if full_plan["price_yearly"]:
                full_plan["price_yearly"] = float(full_plan["price_yearly"])

            client.table("subscription_plans").insert(full_plan).execute()
            results["plans_created"] += 1
            print(f"    Created plan: {plan_data['display_name']}")

        except Exception as e:
            print(f"    Failed to seed plan {plan_data['name']}: {e}")

    # Create tenant_plans associations for seed tenants
    tenant_ids = get_seed_tenant_ids()
    tenant_plan_mapping = {
        "acme": "pro",
        "startup": "free",
        "enterprise": "enterprise",
        "agency": "agency",
        "trial": "free",
    }

    for tenant_key, plan_name in tenant_plan_mapping.items():
        tenant_id = tenant_ids.get(tenant_key)
        if not tenant_id:
            continue

        try:
            # Get plan ID
            plan_response = client.table("subscription_plans").select("id").eq("name", plan_name).execute()
            if not plan_response.data:
                continue
            plan_id = plan_response.data[0]["id"]

            # Check if tenant_plan exists
            existing = client.table("tenant_plans").select("id").eq("tenant_id", tenant_id).execute()

            if existing.data:
                continue  # Skip if already exists

            # Create tenant_plan
            tenant_plan = {
                "id": deterministic_uuid(f"tenant-plan-{tenant_key}"),
                "tenant_id": tenant_id,
                "plan_id": plan_id,
                "status": "active",
                "billing_cycle": "monthly",
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }

            client.table("tenant_plans").insert(tenant_plan).execute()
            results["tenant_plans_created"] += 1
            print(f"    Created tenant_plan: {tenant_key} -> {plan_name}")

        except Exception as e:
            print(f"    Failed to create tenant_plan for {tenant_key}: {e}")

    return results


def get_plan_id(plan_name: str) -> str:
    """Get deterministic plan ID by name."""
    return deterministic_uuid(f"plan-{plan_name}")
