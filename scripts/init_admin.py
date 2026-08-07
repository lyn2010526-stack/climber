#!/usr/bin/env python3
"""Initialize the first admin user and API key."""

import sys
sys.path.insert(0, '/workspace/agent-engine')

from app.middleware.auth import get_user_store

def init_admin():
    """Create admin user and API key."""
    store = get_user_store()
    
    # Create admin user's API key with full permissions
    raw_key, key_id = store.create_key(
        owner="admin",
        scopes=["read", "write", "admin"],
        ttl_days=None  # Never expires
    )
    
    print("=" * 60)
    print("ADMIN USER INITIALIZED")
    print("=" * 60)
    print(f"Owner: admin")
    print(f"API Key ID: {key_id}")
    print(f"API Key: {raw_key}")
    print(f"Scopes: read, write, admin")
    print("=" * 60)
    print("\n⚠️  IMPORTANT: Save this API Key securely!")
    print("   The raw key is only returned once at creation.")
    print("   You cannot retrieve it later.")
    print("=" * 60)
    
    return raw_key

if __name__ == "__main__":
    try:
        init_admin()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
