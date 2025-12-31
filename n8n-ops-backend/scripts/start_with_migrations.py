"""
Start script that runs database migrations before starting the application.

This ensures the database schema is up-to-date before the FastAPI app starts.
If migrations fail, the application will not start.

Usage:
    python scripts/start_with_migrations.py
    python scripts/start_with_migrations.py --port 4000
    python scripts/start_with_migrations.py --host 0.0.0.0 --port 4000 --reload
"""
import subprocess
import sys
import os
import argparse
from pathlib import Path


def run_migrations():
    """Run Alembic migrations before starting the app."""
    backend_dir = Path(__file__).parent.parent
    original_dir = os.getcwd()
    
    try:
        os.chdir(backend_dir)
        
        print("=" * 60)
        print("Running database migrations...")
        print("=" * 60)
        
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print("❌ Migration failed!")
            print("\nSTDOUT:")
            print(result.stdout)
            print("\nSTDERR:")
            print(result.stderr)
            return False
        
        print("✅ Migrations completed successfully")
        print("=" * 60)
        return True
        
    except FileNotFoundError:
        print("❌ Error: 'alembic' command not found.")
        print("   Make sure Alembic is installed: pip install alembic")
        return False
    except Exception as e:
        print(f"❌ Error running migrations: {str(e)}")
        return False
    finally:
        os.chdir(original_dir)


def start_application(host="0.0.0.0", port=4000, reload=True):
    """Start the FastAPI application using uvicorn."""
    backend_dir = Path(__file__).parent.parent
    os.chdir(backend_dir)
    
    print("\n" + "=" * 60)
    print("Starting application...")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Reload: {reload}")
    print("=" * 60 + "\n")
    
    # Build uvicorn command
    cmd = [
        "uvicorn",
        "app.main:app",
        "--host", host,
        "--port", str(port)
    ]
    
    if reload:
        cmd.append("--reload")
    
    # Replace current process with uvicorn
    os.execvp("uvicorn", cmd)


def main():
    parser = argparse.ArgumentParser(
        description="Run database migrations and start the application"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=4000,
        help="Port to bind to (default: 4000)"
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable auto-reload (useful for production)"
    )
    parser.add_argument(
        "--skip-migrations",
        action="store_true",
        help="Skip running migrations (not recommended)"
    )
    
    args = parser.parse_args()
    
    # Run migrations unless skipped
    if not args.skip_migrations:
        if not run_migrations():
            print("\n❌ Failed to run migrations. Application will not start.")
            print("   To skip migrations (not recommended), use --skip-migrations")
            sys.exit(1)
    else:
        print("⚠️  Skipping migrations (--skip-migrations flag used)")
    
    # Start the application
    start_application(
        host=args.host,
        port=args.port,
        reload=not args.no_reload
    )


if __name__ == "__main__":
    main()

