#!/usr/bin/env python3
"""
Diagnostic script to assess tenant plan configuration and identify why
a tenant with a pro plan subscription is receiving free plan limits.

Usage:
    python scripts/diagnose_tenant_plan.py <tenant_id>
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.database import db_service
from app.services.plan_resolver import resolve_effective_plan
from app.services.entitlements_service import entitlements_service


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_field(label: str, value: Any, indent: int = 0):
    """Print a formatted field."""
    prefix = "  " * indent
    if value is None:
        value_str = "[NULL]"
    elif isinstance(value, bool):
        value_str = "[YES]" if value else "[NO]"
    elif isinstance(value, dict):
        value_str = str(value)
    else:
        value_str = str(value)
    print(f"{prefix}{label}: {value_str}")


async def diagnose_tenant_plan(tenant_id: str):
    """Run comprehensive diagnostic on tenant plan configuration."""
    
    print_section(f"Tenant Plan Diagnostic - {tenant_id}")
    
    # 1. Check tenant exists
    print_section("1. Tenant Verification")
    try:
        tenant_resp = db_service.client.table("tenants").select(
            "id, name, subscription_tier"
        ).eq("id", tenant_id).maybe_single().execute()
        
        tenant = tenant_resp.data
        if not tenant:
            print(f"[ERROR] Tenant {tenant_id} not found in database")
            return False
        
        print_field("Tenant ID", tenant.get("id"))
        print_field("Tenant Name", tenant.get("name"))
        print_field("Legacy subscription_tier", tenant.get("subscription_tier"))
        print("\n[NOTE] subscription_tier is legacy - not used for gating")
    except Exception as e:
        print(f"[ERROR] Failed to query tenant: {e}")
        return False
    
    # 2. Check provider subscriptions
    print_section("2. Provider Subscriptions (tenant_provider_subscriptions)")
    try:
        subs_resp = db_service.client.table("tenant_provider_subscriptions").select(
            "id, tenant_id, provider_id, plan_id, status, "
            "billing_cycle, current_period_start, current_period_end, "
            "cancel_at_period_end, created_at, updated_at, "
            "provider:provider_id(id, name, display_name), "
            "plan:plan_id(id, name, display_name, max_environments, max_workflows, features)"
        ).eq("tenant_id", tenant_id).execute()
        
        subscriptions = subs_resp.data or []
        
        if not subscriptions:
            print("[WARNING] No provider subscriptions found for this tenant")
            print("[INFO] Tenant will default to 'free' plan")
        else:
            print(f"[INFO] Found {len(subscriptions)} subscription(s)")
            
            for i, sub in enumerate(subscriptions, 1):
                print(f"\n  Subscription #{i}:")
                print_field("Subscription ID", sub.get("id"), indent=1)
                print_field("Provider", f"{sub.get('provider', {}).get('name')} ({sub.get('provider_id')})", indent=1)
                print_field("Plan ID", sub.get("plan_id"), indent=1)
                
                plan = sub.get("plan", {})
                print_field("Plan Name", plan.get("name"), indent=1)
                print_field("Plan Display Name", plan.get("display_name"), indent=1)
                print_field("Status", sub.get("status"), indent=1)
                print_field("Billing Cycle", sub.get("billing_cycle"), indent=1)
                print_field("Current Period Start", sub.get("current_period_start"), indent=1)
                print_field("Current Period End", sub.get("current_period_end"), indent=1)
                print_field("Cancel at Period End", sub.get("cancel_at_period_end"), indent=1)
                
                # Check if subscription is active
                now = datetime.now(timezone.utc)
                status = (sub.get("status") or "").lower()
                is_active_status = status in ("active", "trialing")
                
                current_period_end = sub.get("current_period_end")
                is_not_expired = True
                if current_period_end:
                    try:
                        if isinstance(current_period_end, str):
                            end_dt = datetime.fromisoformat(current_period_end.replace("Z", "+00:00"))
                        else:
                            end_dt = current_period_end
                        is_not_expired = end_dt > now
                    except Exception:
                        pass
                
                is_active = is_active_status and is_not_expired
                print_field("Is Active", is_active, indent=1)
                
                if not is_active:
                    print(f"\n    [ISSUE] Subscription is NOT active:", indent=1)
                    if not is_active_status:
                        print(f"      - Status '{status}' is not in ('active', 'trialing')")
                    if not is_not_expired:
                        print(f"      - Current period ended: {current_period_end}")
                
                # Show plan limits from provider_plans
                if plan:
                    print_field("Plan max_environments", plan.get("max_environments"), indent=1)
                    print_field("Plan max_workflows", plan.get("max_workflows"), indent=1)
                    features = plan.get("features") or {}
                    if features:
                        print_field("Plan features (JSONB)", f"{len(features)} features", indent=1)
    except Exception as e:
        print(f"[ERROR] Failed to query subscriptions: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 3. Check plan resolver
    print_section("3. Plan Resolver (resolve_effective_plan)")
    try:
        resolved = await resolve_effective_plan(tenant_id)
        
        print_field("Resolved Plan Name", resolved.get("plan_name"))
        print_field("Source", resolved.get("source"))
        print_field("Plan Rank", resolved.get("plan_rank"))
        print_field("Highest Subscription ID", resolved.get("highest_subscription_id"))
        
        active_subs = resolved.get("active_subscriptions", [])
        print_field("Active Subscriptions Count", len(active_subs))
        
        if active_subs:
            print("\n  Active Subscriptions:")
            for sub in active_subs:
                print(f"    - ID: {sub.get('id')}, Plan: {sub.get('plan_name')}, Rank: {sub.get('plan_rank')}")
        
        contributing = resolved.get("contributing_subscriptions", [])
        print_field("Contributing Subscription IDs", contributing if contributing else "None")
        
        if resolved.get("plan_name") == "free" and not resolved.get("highest_subscription_id"):
            print("\n  [ISSUE] No active subscription found - defaulting to 'free'")
    except Exception as e:
        print(f"[ERROR] Failed to resolve plan: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. Check plans table (used by entitlements_service)
    print_section("4. Plans Table (plans)")
    try:
        resolved_plan_name = resolved.get("plan_name", "free")
        
        plan_resp = db_service.client.table("plans").select(
            "id, name, display_name"
        ).eq("name", resolved_plan_name).maybe_single().execute()
        
        plan_record = plan_resp.data
        if not plan_record:
            print(f"[WARNING] Plan '{resolved_plan_name}' not found in plans table")
            print("[INFO] This will cause entitlements_service to fail")
        else:
            print_field("Plan ID", plan_record.get("id"))
            print_field("Plan Name", plan_record.get("name"))
            print_field("Plan Display Name", plan_record.get("display_name"))
            
            plan_id = plan_record.get("id")
            
            # 5. Check plan_features
            print_section("5. Plan Features (plan_features)")
            if plan_id:
                features_resp = db_service.client.table("plan_features").select(
                    "value, feature:feature_id(id, name, type, display_name)"
                ).eq("plan_id", plan_id).execute()
                
                features = features_resp.data or []
                
                if not features:
                    print(f"[WARNING] No features found for plan_id {plan_id}")
                else:
                    print(f"[INFO] Found {len(features)} feature(s)")
                    
                    # Look for critical limits
                    workflow_limits = None
                    environment_limits = None
                    
                    for pf in features:
                        feature = pf.get("feature", {})
                        feature_name = feature.get("name")
                        feature_type = feature.get("type")
                        value = pf.get("value", {})
                        
                        if feature_name == "workflow_limits":
                            workflow_limits = value.get("value") if feature_type == "limit" else None
                        elif feature_name == "environment_limits":
                            environment_limits = value.get("value") if feature_type == "limit" else None
                    
                    print("\n  Critical Limits:")
                    print_field("workflow_limits", workflow_limits, indent=1)
                    print_field("environment_limits", environment_limits, indent=1)
                    
                    # Expected values
                    expected_limits = {
                        "free": {"workflow_limits": 10, "environment_limits": 1},
                        "pro": {"workflow_limits": 200, "environment_limits": 3},
                        "agency": {"workflow_limits": 500, "environment_limits": 9999},
                        "enterprise": {"workflow_limits": -1, "environment_limits": 9999},
                    }
                    
                    expected = expected_limits.get(resolved_plan_name, {})
                    if expected:
                        print("\n  Expected Limits (for comparison):")
                        print_field("Expected workflow_limits", expected.get("workflow_limits"), indent=1)
                        print_field("Expected environment_limits", expected.get("environment_limits"), indent=1)
                        
                        if workflow_limits != expected.get("workflow_limits"):
                            print(f"\n    [ISSUE] workflow_limits mismatch: got {workflow_limits}, expected {expected.get('workflow_limits')}")
                        if environment_limits != expected.get("environment_limits"):
                            print(f"\n    [ISSUE] environment_limits mismatch: got {environment_limits}, expected {expected.get('environment_limits')}")
                    
                    print("\n  All Features:")
                    for pf in features:
                        feature = pf.get("feature", {})
                        feature_name = feature.get("name")
                        feature_type = feature.get("type")
                        value = pf.get("value", {})
                        
                        if feature_type == "flag":
                            display_value = value.get("enabled", False)
                        elif feature_type == "limit":
                            display_value = value.get("value", 0)
                        else:
                            display_value = value
                        
                        print(f"    - {feature_name} ({feature_type}): {display_value}")
    except Exception as e:
        print(f"[ERROR] Failed to query plans/features: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 6. Check entitlements_service output
    print_section("6. Entitlements Service (get_tenant_entitlements)")
    try:
        # Clear cache first
        entitlements_service.clear_cache(tenant_id)
        
        entitlements = await entitlements_service.get_tenant_entitlements(tenant_id)
        
        print_field("Plan ID", entitlements.get("plan_id"))
        print_field("Plan Name", entitlements.get("plan_name"))
        print_field("Entitlements Version", entitlements.get("entitlements_version"))
        
        features = entitlements.get("features", {})
        print_field("Total Features", len(features))
        
        # Show critical limits
        print("\n  Effective Limits (from entitlements_service):")
        workflow_limit = features.get("workflow_limits")
        environment_limit = features.get("environment_limits")
        print_field("workflow_limits", workflow_limit, indent=1)
        print_field("environment_limits", environment_limit, indent=1)
        
        # Compare with expected
        expected_limits = {
            "free": {"workflow_limits": 10, "environment_limits": 1},
            "pro": {"workflow_limits": 200, "environment_limits": 3},
        }
        
        plan_name = entitlements.get("plan_name", "free")
        expected = expected_limits.get(plan_name, {})
        
        if expected:
            print("\n  Comparison:")
            if workflow_limit != expected.get("workflow_limits"):
                print(f"    [ISSUE] workflow_limits: got {workflow_limit}, expected {expected.get('workflow_limits')} for {plan_name} plan")
            else:
                print(f"    [OK] workflow_limits matches expected ({workflow_limit})")
            
            if environment_limit != expected.get("environment_limits"):
                print(f"    [ISSUE] environment_limits: got {environment_limit}, expected {expected.get('environment_limits')} for {plan_name} plan")
            else:
                print(f"    [OK] environment_limits matches expected ({environment_limit})")
        
        overrides = entitlements.get("overrides_applied", [])
        if overrides:
            print(f"\n  [INFO] {len(overrides)} override(s) applied: {overrides}")
    except Exception as e:
        print(f"[ERROR] Failed to get entitlements: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 7. Check FeatureService (uses different data source)
    print_section("7. FeatureService (get_tenant_features)")
    try:
        from app.services.feature_service import feature_service
        
        # Check old subscriptions table
        try:
            old_sub_resp = db_service.client.table("subscriptions").select(
                "*, plan:plan_id(name, display_name, features, max_environments, max_workflows)"
            ).eq("tenant_id", tenant_id).maybe_single().execute()
            
            old_sub = old_sub_resp.data if old_sub_resp else None
        except Exception:
            old_sub = None
        if old_sub:
            print("[WARNING] Found subscription in OLD 'subscriptions' table")
            print_field("Plan Name", old_sub.get("plan", {}).get("name"))
            print_field("Status", old_sub.get("status"))
        else:
            print("[INFO] No subscription in OLD 'subscriptions' table")
            print("[ISSUE] FeatureService.get_tenant_features() will return free plan defaults!")
        
        # Check what FeatureService returns
        features = await feature_service.get_tenant_features(tenant_id)
        print("\n  FeatureService.get_tenant_features() returns:")
        print_field("plan_name", features.get("plan_name"), indent=1)
        print_field("max_environments", features.get("max_environments"), indent=1)
        print_field("max_team_members", features.get("max_team_members"), indent=1)
        
        # Check get_effective_entitlements (uses tenant_provider_subscriptions)
        effective = await feature_service.get_effective_entitlements(tenant_id, "n8n")
        print("\n  FeatureService.get_effective_entitlements() returns:")
        print_field("plan_name", effective.get("plan_name"), indent=1)
        print_field("max_environments", effective.get("max_environments"), indent=1)
        print_field("max_workflows", effective.get("max_workflows"), indent=1)
        print_field("has_subscription", effective.get("has_subscription"), indent=1)
        
        if features.get("max_environments") == 1 and effective.get("max_environments") > 1:
            print("\n  [ISSUE] FeatureService.get_tenant_features() returns free limits!")
            print("         But get_effective_entitlements() returns correct pro limits")
            print("         → FeatureService.get_tenant_features() needs to be updated")
    except Exception as e:
        print(f"[ERROR] Failed to check FeatureService: {e}")
        import traceback
        traceback.print_exc()
    
    # 8. Summary
    print_section("8. Summary & Recommendations")
    
    resolved_plan = resolved.get("plan_name", "free")
    entitlements_plan = entitlements.get("plan_name", "free")
    workflow_limit = features.get("workflow_limits")
    environment_limit = features.get("environment_limits")
    
    issues = []
    
    if resolved_plan == "free" and subscriptions:
        issues.append("Plan resolver returns 'free' despite existing subscriptions")
        issues.append("  → Check subscription status and dates")
    
    if resolved_plan != entitlements_plan:
        issues.append(f"Plan mismatch: resolver={resolved_plan}, entitlements={entitlements_plan}")
    
    if resolved_plan == "pro" and workflow_limit == 10:
        issues.append("Pro plan but workflow_limits=10 (should be 200)")
        issues.append("  → Check plan_features table for pro plan")
    
    if resolved_plan == "pro" and environment_limit == 1:
        issues.append("Pro plan but environment_limits=1 (should be 3)")
        issues.append("  → Check plan_features table or PLAN_ENVIRONMENT_LIMITS constant")
    
    if not issues:
        print("[OK] No issues detected - tenant plan configuration looks correct")
    else:
        print("[ISSUES FOUND]:")
        for issue in issues:
            print(f"  - {issue}")
    
    return len(issues) == 0


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/diagnose_tenant_plan.py <tenant_id>")
        sys.exit(1)
    
    tenant_id = sys.argv[1]
    success = await diagnose_tenant_plan(tenant_id)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

