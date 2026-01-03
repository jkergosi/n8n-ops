#!/usr/bin/env python3
"""
Script to check if a platform admin exists and verify the data
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.database import db_service

def check_platform_admin(user_id: str):
    """Check if user exists and is a platform admin"""
    print(f"Checking user ID: {user_id}")
    print("=" * 60)
    
    # Check if user exists
    try:
        user_resp = db_service.client.table("users").select("id, email, name").eq("id", user_id).maybe_single().execute()
        user = user_resp.data
        
        if not user:
            print(f"[ERROR] User {user_id} does NOT exist in users table")
            return False
        
        print(f"[OK] User exists:")
        print(f"   ID: {user.get('id')}")
        print(f"   Email: {user.get('email')}")
        print(f"   Name: {user.get('name')}")
    except Exception as e:
        print(f"[ERROR] Error checking user: {e}")
        return False
    
    # Check if user is a platform admin
    try:
        pa_resp = db_service.client.table("platform_admins").select("*").eq("user_id", user_id).maybe_single().execute()
        pa = pa_resp.data
        
        if not pa:
            print(f"[ERROR] User {user_id} is NOT a platform admin")
            return False
        
        print(f"[OK] User IS a platform admin:")
        print(f"   Granted at: {pa.get('granted_at')}")
        print(f"   Granted by: {pa.get('granted_by')}")
    except Exception as e:
        print(f"[ERROR] Error checking platform admin: {e}")
        return False
    
    # List all platform admins
    print("\n" + "=" * 60)
    print("All Platform Admins:")
    print("=" * 60)
    try:
        all_pa_resp = db_service.client.table("platform_admins").select("user_id, granted_at, granted_by").execute()
        all_pa = all_pa_resp.data or []
        
        if not all_pa:
            print("[ERROR] No platform admins found in database")
            return False
        
        print(f"Found {len(all_pa)} platform admin(s):")
        for pa in all_pa:
            print(f"  - User ID: {pa.get('user_id')}")
            print(f"    Granted at: {pa.get('granted_at')}")
            print(f"    Granted by: {pa.get('granted_by')}")
    except Exception as e:
        print(f"[ERROR] Error listing platform admins: {e}")
        return False
    
    return True

if __name__ == "__main__":
    user_id = "f39b83c8-2c92-489d-8896-8d3f30e05e8e"
    check_platform_admin(user_id)

