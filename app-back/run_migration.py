"""
Script to run database migrations
"""
import sys
import asyncio
from pathlib import Path
from app.core.config import settings

# Try importing psycopg2, fall back to instructions if not available
try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

async def run_migration(migration_file: str):
    """Run a SQL migration file"""

    migration_path = Path("migrations") / migration_file

    if not migration_path.exists():
        print(f"[-] Migration file not found: {migration_path}")
        return False

    # Read the migration file
    with open(migration_path, "r") as f:
        migration_sql = f.read()

    print(f"[*] Running migration: {migration_file}")
    print("-" * 60)

    if not HAS_PSYCOPG2:
        print("\n[!] psycopg2 not installed. Showing manual migration instructions...")
        print("\n" + "=" * 60)
        print("MIGRATION INSTRUCTIONS:")
        print("=" * 60)
        print(f"\nThe migration file is at: migrations/{migration_file}")
        print("\nTo run this migration, you have two options:")
        print("\n1. Use Supabase Dashboard:")
        print("   - Go to https://supabase.com/dashboard")
        print("   - Navigate to your project > SQL Editor")
        print("   - Copy and paste the SQL from the migration file")
        print("   - Click 'Run'")
        print("\n2. Use psql command line:")
        print("   - psql <your-database-url>")
        print(f"   - \\i migrations/{migration_file}")
        print("\n" + "=" * 60)
        return False

    # Execute migration using psycopg2
    try:
        conn = psycopg2.connect(settings.DATABASE_URL)
        cursor = conn.cursor()

        print("[+] Connected to database")
        print(f"\nExecuting SQL from {migration_file}...")

        cursor.execute(migration_sql)
        conn.commit()

        print("[+] Migration executed successfully!")

        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"[-] Migration failed: {e}")
        return False

if __name__ == "__main__":
    migration_file = "add_git_fields_to_environments.sql"

    if len(sys.argv) > 1:
        migration_file = sys.argv[1]

    success = asyncio.run(run_migration(migration_file))
    sys.exit(0 if success else 1)
