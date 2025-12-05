"""
Script to run database migrations via Supabase
"""
import requests
from app.core.config import settings

def run_migration():
    """Run the workflow_count migration via Supabase Management API"""

    print("=" * 60)
    print("MIGRATION: add_workflow_count_to_environments")
    print("=" * 60)

    # Read the migration file
    with open("migrations/add_workflow_count_to_environments.sql", "r") as f:
        migration_sql = f.read()

    print("\nMigration SQL:")
    print("-" * 60)
    print(migration_sql)
    print("-" * 60)

    print("\n" + "=" * 60)
    print("INSTRUCTIONS TO RUN THE MIGRATION:")
    print("=" * 60)
    print("\nOption 1: Supabase Dashboard (RECOMMENDED)")
    print("  1. Go to: https://supabase.com/dashboard")
    print("  2. Select your project: xjunfyugpbyjslqkzlwn")
    print("  3. Click 'SQL Editor' in the left sidebar")
    print("  4. Click 'New Query'")
    print("  5. Copy and paste the SQL from above")
    print("  6. Click 'Run' (or press Ctrl+Enter)")
    print("\nOption 2: Command Line (if you have psql installed)")
    print("  Get the connection string from Supabase Dashboard:")
    print("  Settings > Database > Connection String > Direct Connection")
    print("  Then run:")
    print("  psql '<connection-string>' -f migrations/add_workflow_count_to_environments.sql")

    print("\n" + "=" * 60)
    print("AFTER RUNNING THE MIGRATION:")
    print("=" * 60)
    print("\nVerify the migration worked by running this Python command:")
    print("  cd n8n-ops-backend")
    print("  python -c \"from app.services.database import db_service; print(db_service.client.table('environments').select('id, name, workflow_count').execute())\"")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    run_migration()
