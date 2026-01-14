"""
Workflow and execution seeding.

Creates representative workflows, environments, and execution history.
"""
import json
from datetime import datetime, timedelta
import random
from typing import Dict, Any, List

from supabase import Client

from .tenants import get_seed_tenant_ids, deterministic_uuid


# Sample workflow definitions
SAMPLE_WORKFLOWS = [
    {
        "name": "Daily Data Sync",
        "description": "Synchronizes customer data from CRM to data warehouse",
        "tags": ["sync", "production", "critical"],
        "active": True,
        "complexity": "medium",
    },
    {
        "name": "Email Notification Handler",
        "description": "Sends automated email notifications based on triggers",
        "tags": ["notifications", "email"],
        "active": True,
        "complexity": "simple",
    },
    {
        "name": "Invoice Generator",
        "description": "Generates and sends monthly invoices to customers",
        "tags": ["billing", "production"],
        "active": True,
        "complexity": "complex",
    },
    {
        "name": "API Health Monitor",
        "description": "Monitors external API endpoints and alerts on failures",
        "tags": ["monitoring", "alerts"],
        "active": True,
        "complexity": "simple",
    },
    {
        "name": "Data Transformation Pipeline",
        "description": "ETL pipeline for analytics data",
        "tags": ["etl", "analytics"],
        "active": False,
        "complexity": "complex",
    },
    {
        "name": "Slack Bot Handler",
        "description": "Handles slash commands and interactions from Slack",
        "tags": ["slack", "integrations"],
        "active": True,
        "complexity": "medium",
    },
    {
        "name": "Backup Automation",
        "description": "Automated backup of critical data to cloud storage",
        "tags": ["backup", "maintenance"],
        "active": True,
        "complexity": "simple",
    },
    {
        "name": "Lead Scoring Engine",
        "description": "Scores and routes leads based on engagement data",
        "tags": ["sales", "automation"],
        "active": True,
        "complexity": "complex",
    },
]

# Environment types to create for each tenant
ENVIRONMENT_CONFIGS = [
    {
        "name": "Development",
        "n8n_type": "development",
        "environment_class": "development",
        "color": "#22c55e",
    },
    {
        "name": "Staging",
        "n8n_type": "staging",
        "environment_class": "staging",
        "color": "#f59e0b",
    },
    {
        "name": "Production",
        "n8n_type": "production",
        "environment_class": "production",
        "color": "#ef4444",
    },
]


def generate_workflow_data(workflow_def: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Generate a mock n8n workflow data structure."""
    return {
        "id": str(1000 + index),
        "name": workflow_def["name"],
        "active": workflow_def["active"],
        "nodes": [
            {"type": "n8n-nodes-base.start", "name": "Start"},
            {"type": "n8n-nodes-base.httpRequest", "name": "HTTP Request"},
            {"type": "n8n-nodes-base.set", "name": "Set"},
        ],
        "connections": {},
        "settings": {"saveExecutionProgress": True},
        "tags": [{"name": tag} for tag in workflow_def.get("tags", [])],
        "createdAt": datetime.utcnow().isoformat(),
        "updatedAt": datetime.utcnow().isoformat(),
    }


def generate_execution_data(
    workflow_id: str,
    workflow_name: str,
    index: int,
    days_ago: int = 0,
) -> Dict[str, Any]:
    """Generate a mock execution record."""
    started_at = datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23))
    execution_time_ms = random.randint(100, 30000)
    finished_at = started_at + timedelta(milliseconds=execution_time_ms)

    # 90% success rate
    status = "success" if random.random() < 0.9 else "error"

    return {
        "execution_id": str(10000 + index),
        "workflow_id": workflow_id,
        "workflow_name": workflow_name,
        "status": status,
        "mode": random.choice(["trigger", "manual", "webhook"]),
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "execution_time": execution_time_ms,
        "retry_of": None,
        "retry_success_id": None,
    }


async def seed_workflows(client: Client, clean: bool = False) -> Dict[str, Any]:
    """
    Seed environments, workflows, and executions.

    Args:
        client: Supabase client
        clean: If True, delete existing seed data first

    Returns:
        Dict with counts
    """
    results = {
        "environments_created": 0,
        "environments_skipped": 0,
        "workflows_created": 0,
        "workflows_skipped": 0,
        "executions_created": 0,
        "tags_created": 0,
    }

    now = datetime.utcnow().isoformat()
    tenant_ids = get_seed_tenant_ids()

    # Only seed for Acme (pro) and Enterprise tenants
    tenants_to_seed = ["acme", "enterprise"]

    for tenant_key in tenants_to_seed:
        tenant_id = tenant_ids.get(tenant_key)
        if not tenant_id:
            continue

        print(f"  Seeding for tenant: {tenant_key}")

        # Create environments
        env_ids = {}
        for env_config in ENVIRONMENT_CONFIGS:
            env_id = deterministic_uuid(f"{tenant_key}-env-{env_config['n8n_type']}")
            env_ids[env_config["n8n_type"]] = env_id

            try:
                # Check if exists
                existing = client.table("environments").select("id").eq("id", env_id).execute()

                if existing.data:
                    results["environments_skipped"] += 1
                    continue

                env_data = {
                    "id": env_id,
                    "tenant_id": tenant_id,
                    "name": env_config["name"],
                    "n8n_type": env_config["n8n_type"],
                    "environment_class": env_config["environment_class"],
                    "base_url": f"https://{tenant_key}-{env_config['n8n_type']}.n8n-test.local",
                    "api_key": f"test-api-key-{tenant_key}-{env_config['n8n_type']}",
                    "color": env_config["color"],
                    "is_active": True,
                    "workflow_count": 0,
                    "last_sync": None,
                    "created_at": now,
                    "updated_at": now,
                }

                client.table("environments").insert(env_data).execute()
                results["environments_created"] += 1
                print(f"    Created environment: {env_config['name']}")

            except Exception as e:
                print(f"    Failed to create environment {env_config['name']}: {e}")

        # Create workflows in development environment
        dev_env_id = env_ids.get("development")
        if not dev_env_id:
            continue

        workflow_count = len(SAMPLE_WORKFLOWS) if tenant_key == "enterprise" else 4

        for i, workflow_def in enumerate(SAMPLE_WORKFLOWS[:workflow_count]):
            workflow_id = deterministic_uuid(f"{tenant_key}-workflow-{i}")
            n8n_workflow_id = str(1000 + i)

            try:
                # Check if exists
                existing = client.table("workflows").select("id").eq("id", workflow_id).execute()

                if existing.data:
                    results["workflows_skipped"] += 1
                    continue

                workflow_data = generate_workflow_data(workflow_def, i)

                workflow_record = {
                    "id": workflow_id,
                    "tenant_id": tenant_id,
                    "environment_id": dev_env_id,
                    "n8n_workflow_id": n8n_workflow_id,
                    "name": workflow_def["name"],
                    "description": workflow_def["description"],
                    "active": workflow_def["active"],
                    "tags": workflow_def["tags"],
                    "workflow_data": workflow_data,
                    "is_deleted": False,
                    "is_archived": False,
                    "created_at": now,
                    "updated_at": now,
                    "last_synced_at": now,
                }

                client.table("workflows").insert(workflow_record).execute()
                results["workflows_created"] += 1
                print(f"    Created workflow: {workflow_def['name']}")

                # Create some executions for this workflow
                for j in range(random.randint(3, 10)):
                    try:
                        exec_id = deterministic_uuid(f"{tenant_key}-exec-{i}-{j}")
                        exec_data = generate_execution_data(
                            workflow_id=n8n_workflow_id,
                            workflow_name=workflow_def["name"],
                            index=i * 100 + j,
                            days_ago=random.randint(0, 7),
                        )

                        exec_record = {
                            "id": exec_id,
                            "tenant_id": tenant_id,
                            "environment_id": dev_env_id,
                            **exec_data,
                            "created_at": now,
                            "updated_at": now,
                        }

                        client.table("executions").insert(exec_record).execute()
                        results["executions_created"] += 1

                    except Exception:
                        pass  # Ignore execution insert errors

            except Exception as e:
                print(f"    Failed to create workflow {workflow_def['name']}: {e}")

        # Update environment workflow count
        try:
            client.table("environments").update({
                "workflow_count": workflow_count,
                "updated_at": now,
            }).eq("id", dev_env_id).execute()
        except Exception:
            pass

        # Create tags
        all_tags = set()
        for wf in SAMPLE_WORKFLOWS[:workflow_count]:
            all_tags.update(wf.get("tags", []))

        for tag_name in all_tags:
            tag_id = deterministic_uuid(f"{tenant_key}-tag-{tag_name}")
            try:
                existing = client.table("tags").select("id").eq("id", tag_id).execute()
                if existing.data:
                    continue

                tag_record = {
                    "id": tag_id,
                    "tenant_id": tenant_id,
                    "environment_id": dev_env_id,
                    "tag_id": tag_name,  # Using name as n8n tag ID
                    "name": tag_name,
                    "created_at": now,
                    "updated_at": now,
                }

                client.table("tags").insert(tag_record).execute()
                results["tags_created"] += 1

            except Exception:
                pass

    return results
