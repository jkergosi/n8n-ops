"""
Test script to debug observability environment filtering.

Run this from the backend directory:
    python test_observability.py
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app-back'))

from app.services.database import db_service
from app.services.observability_service import observability_service
from app.schemas.observability import TimeRange

MOCK_TENANT_ID = "00000000-0000-0000-0000-000000000001"

async def test_observability():
    print("=" * 60)
    print("Testing Observability Environment Filtering")
    print("=" * 60)
    
    # 1. Get all environments
    print("\n1. Fetching environments...")
    environments = await db_service.get_environments(MOCK_TENANT_ID)
    print(f"   Found {len(environments)} environments:")
    for env in environments:
        print(f"   - {env.get('n8n_name')} (ID: {env.get('id')}, Type: {env.get('n8n_type')})")
    
    if not environments:
        print("   ERROR: No environments found!")
        return
    
    # 2. Get all executions (no filter)
    print("\n2. Checking executions in database...")
    all_executions = await db_service.get_executions(MOCK_TENANT_ID)
    print(f"   Total executions: {len(all_executions)}")
    
    if all_executions:
        # Show environment distribution
        env_counts = {}
        for exec in all_executions:
            env_id = exec.get('environment_id')
            if env_id:
                env_counts[env_id] = env_counts.get(env_id, 0) + 1
        
        print(f"   Executions by environment:")
        for env_id, count in env_counts.items():
            env_name = next((e.get('n8n_name') for e in environments if e.get('id') == env_id), 'Unknown')
            print(f"     - {env_name} ({env_id}): {count} executions")
    
    # 3. Test observability without environment filter
    print("\n3. Testing observability overview (no environment filter)...")
    overview_all = await observability_service.get_observability_overview(
        MOCK_TENANT_ID,
        TimeRange.THIRTY_DAYS
    )
    print(f"   Total Executions: {overview_all.kpi_metrics.total_executions}")
    print(f"   Success Count: {overview_all.kpi_metrics.success_count}")
    print(f"   Failure Count: {overview_all.kpi_metrics.failure_count}")
    print(f"   Workflow Performance Count: {len(overview_all.workflow_performance)}")
    
    # 4. Test with each environment
    for env in environments:
        env_id = env.get('id')
        env_name = env.get('n8n_name')
        env_type = env.get('n8n_type')
        
        print(f"\n4. Testing observability for {env_name} (ID: {env_id}, Type: {env_type})...")
        
        # Check executions for this environment
        env_executions = await db_service.get_executions(MOCK_TENANT_ID, environment_id=env_id)
        print(f"   Executions in database for this environment: {len(env_executions)}")
        
        # Test observability with environment filter
        overview_filtered = await observability_service.get_observability_overview(
            MOCK_TENANT_ID,
            TimeRange.THIRTY_DAYS,
            environment_id=env_id
        )
        print(f"   Observability Results:")
        print(f"     - Total Executions: {overview_filtered.kpi_metrics.total_executions}")
        print(f"     - Success Count: {overview_filtered.kpi_metrics.success_count}")
        print(f"     - Failure Count: {overview_filtered.kpi_metrics.failure_count}")
        print(f"     - Workflow Performance Count: {len(overview_filtered.workflow_performance)}")
        
        if overview_filtered.kpi_metrics.total_executions == 0 and len(env_executions) > 0:
            print(f"   ⚠️  WARNING: Database has {len(env_executions)} executions but observability shows 0!")
            print(f"      This suggests a filtering issue.")
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_observability())
