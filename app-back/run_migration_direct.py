"""
Script to run database migrations directly via psycopg2
"""
import psycopg2
from app.core.config import settings

def run_migration():
    """Run the workflow_count migration"""

    # Read the migration file
    with open("migrations/add_workflow_count_to_environments.sql", "r") as f:
        migration_sql = f.read()

    print("Running migration: add_workflow_count_to_environments.sql")
    print("-" * 60)

    # Connect to database
    try:
        conn = psycopg2.connect(settings.DATABASE_URL)
        cursor = conn.cursor()

        print("Connected to database successfully!")

        # Execute the migration
        print("\nExecuting migration SQL...")
        cursor.execute(migration_sql)

        # Commit the changes
        conn.commit()
        print("Migration executed successfully!")

        # Verify the column was added
        cursor.execute("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'environments' AND column_name = 'workflow_count'
        """)
        result = cursor.fetchone()

        if result:
            print("\nVerification: workflow_count column added successfully!")
            print(f"  Column: {result[0]}")
            print(f"  Type: {result[1]}")
            print(f"  Default: {result[2]}")
        else:
            print("\nWarning: Could not verify column was added")

        # Check current environments
        cursor.execute("SELECT id, name, workflow_count FROM environments")
        environments = cursor.fetchall()
        print(f"\nCurrent environments ({len(environments)}):")
        for env in environments:
            print(f"  - {env[1]}: workflow_count = {env[2]}")

        cursor.close()
        conn.close()

        print("\n" + "=" * 60)
        print("MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError running migration: {str(e)}")
        print("\nAlternative: Run the migration manually in Supabase Dashboard")
        print("1. Go to https://supabase.com/dashboard")
        print("2. Navigate to your project > SQL Editor")
        print("3. Copy and paste the SQL from migrations/add_workflow_count_to_environments.sql")
        print("4. Click 'Run'")
        raise

if __name__ == "__main__":
    run_migration()
