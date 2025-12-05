import asyncio
import asyncpg
from app.core.config import settings

async def run_migration():
    conn = await asyncpg.connect(settings.DATABASE_URL)

    migration_sql = """
    ALTER TABLE environments ADD COLUMN IF NOT EXISTS last_backup TIMESTAMP WITH TIME ZONE;
    CREATE INDEX IF NOT EXISTS idx_environments_last_backup ON environments(last_backup) WHERE last_backup IS NOT NULL;
    """

    try:
        await conn.execute(migration_sql)
        print("✓ Migration completed successfully")
        print("✓ Added last_backup column to environments table")
    except Exception as e:
        print(f"✗ Migration failed: {str(e)}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migration())
