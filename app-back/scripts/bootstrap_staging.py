"""
Bootstrap staging database from production.

This script:
1. Dumps the schema (not data) from production Supabase
2. Applies it to staging Supabase
3. Verifies critical tables exist
4. Stamps Alembic version to establish baseline

Usage:
    python scripts/bootstrap_staging.py --prod-url "postgresql://..." --staging-url "postgresql://..."

    Or use environment variables:
    PROD_DATABASE_URL=... STAGING_DATABASE_URL=... python scripts/bootstrap_staging.py

Prerequisites:
    - pg_dump and psql must be installed and in PATH
    - Both database URLs must be accessible
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from datetime import datetime

# Current migration head - update this when migrations change
CURRENT_MIGRATION_HEAD = "947a226f2ac2"

# Critical tables that must exist after bootstrap
CRITICAL_TABLES = [
    "tenants",
    "users",
    "environments",
    "workflows",
    "executions",
    "pipelines",
    "promotions",
    "deployments",
    "snapshots",
    "drift_incidents",
    "drift_policies",
]

# Schemas to exclude from dump (Supabase internal)
EXCLUDE_SCHEMAS = [
    "auth",
    "storage",
    "supabase_functions",
    "supabase_migrations",
    "graphql",
    "graphql_public",
    "realtime",
    "pgsodium",
    "pgsodium_masks",
    "vault",
    "extensions",
]


def run_command(cmd: list[str], description: str, capture_output: bool = True) -> subprocess.CompletedProcess:
    """Run a command and handle errors."""
    print(f"  {description}...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            print(f"    FAILED!")
            if result.stderr:
                print(f"    Error: {result.stderr[:500]}")
            return result

        print(f"    Done")
        return result

    except subprocess.TimeoutExpired:
        print(f"    TIMEOUT after 5 minutes")
        raise
    except FileNotFoundError as e:
        print(f"    Command not found: {e}")
        raise


def check_prerequisites():
    """Check that required tools are installed."""
    print("\n[1/6] Checking prerequisites...")

    # Check pg_dump
    try:
        result = subprocess.run(["pg_dump", "--version"], capture_output=True, text=True)
        print(f"  pg_dump: {result.stdout.strip().split()[2] if result.returncode == 0 else 'NOT FOUND'}")
    except FileNotFoundError:
        print("  ERROR: pg_dump not found. Install PostgreSQL client tools.")
        return False

    # Check psql
    try:
        result = subprocess.run(["psql", "--version"], capture_output=True, text=True)
        print(f"  psql: {result.stdout.strip().split()[2] if result.returncode == 0 else 'NOT FOUND'}")
    except FileNotFoundError:
        print("  ERROR: psql not found. Install PostgreSQL client tools.")
        return False

    # Check alembic
    try:
        result = subprocess.run(["alembic", "--version"], capture_output=True, text=True)
        print(f"  alembic: found")
    except FileNotFoundError:
        print("  ERROR: alembic not found. Run: pip install alembic")
        return False

    return True


def test_connection(url: str, name: str) -> bool:
    """Test database connection."""
    result = subprocess.run(
        ["psql", url, "-c", "SELECT 1;"],
        capture_output=True,
        text=True,
        timeout=30
    )

    if result.returncode != 0:
        print(f"    FAILED to connect to {name}")
        print(f"    Error: {result.stderr[:200]}")
        return False

    print(f"    {name}: connected")
    return True


def dump_schema(prod_url: str, output_file: str) -> bool:
    """Dump schema-only from production."""
    print("\n[2/6] Dumping schema from production...")

    # Build pg_dump command with schema exclusions
    cmd = [
        "pg_dump",
        prod_url,
        "--schema-only",
        "--no-owner",
        "--no-privileges",
        "--no-comments",
        "-f", output_file,
    ]

    # Exclude Supabase internal schemas
    for schema in EXCLUDE_SCHEMAS:
        cmd.extend(["--exclude-schema", schema])

    result = run_command(cmd, "Dumping schema")

    if result.returncode != 0:
        return False

    # Check file size
    size = os.path.getsize(output_file)
    print(f"    Schema dump size: {size:,} bytes")

    if size < 1000:
        print("    WARNING: Schema dump seems too small, may be empty")
        return False

    return True


def apply_schema(staging_url: str, schema_file: str) -> bool:
    """Apply schema to staging database."""
    print("\n[3/6] Applying schema to staging...")

    # Drop and recreate public schema to start fresh
    print("  Resetting public schema...")
    reset_result = subprocess.run(
        ["psql", staging_url, "-c", "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO postgres; GRANT ALL ON SCHEMA public TO public;"],
        capture_output=True,
        text=True,
        timeout=60
    )

    if reset_result.returncode != 0:
        print(f"    WARNING: Schema reset had issues: {reset_result.stderr[:200]}")

    # Apply the schema dump
    result = run_command(
        ["psql", staging_url, "-f", schema_file],
        "Applying schema"
    )

    # psql may return warnings but still succeed
    if result.returncode != 0:
        print(f"    Schema apply had errors")
        return False

    return True


def verify_tables(staging_url: str) -> bool:
    """Verify critical tables exist in staging."""
    print("\n[4/6] Verifying critical tables...")

    missing = []
    for table in CRITICAL_TABLES:
        result = subprocess.run(
            ["psql", staging_url, "-t", "-c", f"SELECT to_regclass('public.{table}');"],
            capture_output=True,
            text=True,
            timeout=10
        )

        exists = result.stdout.strip() and result.stdout.strip() != "-"
        status = "OK" if exists else "MISSING"
        print(f"    {table}: {status}")

        if not exists:
            missing.append(table)

    if missing:
        print(f"\n    ERROR: Missing tables: {', '.join(missing)}")
        return False

    print(f"\n    All {len(CRITICAL_TABLES)} critical tables verified")
    return True


def verify_extensions(staging_url: str) -> bool:
    """Verify required extensions exist."""
    print("\n[5/6] Verifying extensions...")

    # Check for common required extensions
    extensions = ["uuid-ossp", "pgcrypto"]

    for ext in extensions:
        result = subprocess.run(
            ["psql", staging_url, "-t", "-c", f"SELECT 1 FROM pg_extension WHERE extname = '{ext}';"],
            capture_output=True,
            text=True,
            timeout=10
        )

        exists = result.stdout.strip() == "1"
        status = "OK" if exists else "NOT FOUND (may be ok)"
        print(f"    {ext}: {status}")

    return True


def stamp_alembic(staging_url: str) -> bool:
    """Stamp Alembic version to establish baseline."""
    print("\n[6/6] Stamping Alembic baseline...")

    backend_dir = Path(__file__).parent.parent
    original_dir = os.getcwd()
    original_env = os.environ.get("DATABASE_URL")

    try:
        os.chdir(backend_dir)
        os.environ["DATABASE_URL"] = staging_url

        # First, check if alembic_version table exists
        result = subprocess.run(
            ["psql", staging_url, "-t", "-c", "SELECT version_num FROM alembic_version;"],
            capture_output=True,
            text=True,
            timeout=10
        )

        current_version = result.stdout.strip() if result.returncode == 0 else None

        if current_version:
            print(f"    Existing version: {current_version}")
            if current_version == CURRENT_MIGRATION_HEAD:
                print(f"    Already at correct version, skipping stamp")
                return True

        # Stamp with current head
        result = subprocess.run(
            ["alembic", "stamp", CURRENT_MIGRATION_HEAD],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            print(f"    FAILED to stamp: {result.stderr}")
            return False

        print(f"    Stamped with version: {CURRENT_MIGRATION_HEAD}")
        return True

    finally:
        os.chdir(original_dir)
        if original_env:
            os.environ["DATABASE_URL"] = original_env
        elif "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap staging database from production schema"
    )
    parser.add_argument(
        "--prod-url",
        default=os.environ.get("PROD_DATABASE_URL"),
        help="Production database URL (or set PROD_DATABASE_URL env var)"
    )
    parser.add_argument(
        "--staging-url",
        default=os.environ.get("STAGING_DATABASE_URL"),
        help="Staging database URL (or set STAGING_DATABASE_URL env var)"
    )
    parser.add_argument(
        "--keep-dump",
        action="store_true",
        help="Keep the schema dump file after completion"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dump schema only, don't apply to staging"
    )

    args = parser.parse_args()

    if not args.prod_url:
        print("ERROR: Production database URL required.")
        print("  Use --prod-url or set PROD_DATABASE_URL environment variable")
        sys.exit(1)

    if not args.staging_url and not args.dry_run:
        print("ERROR: Staging database URL required.")
        print("  Use --staging-url or set STAGING_DATABASE_URL environment variable")
        sys.exit(1)

    print("=" * 60)
    print("STAGING DATABASE BOOTSTRAP")
    print("=" * 60)
    print(f"  Time: {datetime.now().isoformat()}")
    print(f"  Migration head: {CURRENT_MIGRATION_HEAD}")
    print(f"  Dry run: {args.dry_run}")

    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)

    # Test connections
    print("\n  Testing connections...")
    if not test_connection(args.prod_url, "Production"):
        sys.exit(1)

    if not args.dry_run:
        if not test_connection(args.staging_url, "Staging"):
            sys.exit(1)

    # Create temp file for schema dump
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_file = f"schema_dump_{timestamp}.sql"

    if args.keep_dump:
        dump_path = str(Path(__file__).parent / dump_file)
    else:
        dump_path = os.path.join(tempfile.gettempdir(), dump_file)

    try:
        # Dump schema from production
        if not dump_schema(args.prod_url, dump_path):
            sys.exit(1)

        if args.dry_run:
            print(f"\n  Dry run complete. Schema dump: {dump_path}")
            sys.exit(0)

        # Apply to staging
        if not apply_schema(args.staging_url, dump_path):
            sys.exit(1)

        # Verify tables
        if not verify_tables(args.staging_url):
            sys.exit(1)

        # Verify extensions
        verify_extensions(args.staging_url)

        # Stamp Alembic
        if not stamp_alembic(args.staging_url):
            sys.exit(1)

        print("\n" + "=" * 60)
        print("BOOTSTRAP COMPLETE")
        print("=" * 60)
        print(f"\nStaging database is now a schema copy of production.")
        print(f"Alembic is stamped at: {CURRENT_MIGRATION_HEAD}")
        print(f"\nNext steps:")
        print(f"  1. Run seed script: python -m app.seed --env staging")
        print(f"  2. Create test users in Supabase Auth")
        print(f"  3. Configure staging Auth settings (site_url, SMTP)")

    finally:
        # Clean up temp file
        if not args.keep_dump and os.path.exists(dump_path):
            os.remove(dump_path)


if __name__ == "__main__":
    main()
