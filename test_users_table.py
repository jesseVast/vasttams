#!/usr/bin/env python3
"""
Simple script to test the users table directly
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.storage.vast_store import VASTStore
from app.core.config import get_settings

async def test_users_table():
    """Test the users table directly"""
    try:
        print("🔍 Testing users table directly...")
        
        # Initialize VAST store
        settings = get_settings()
        vast_store = VASTStore(
            endpoint=settings.vast_endpoint,
            access_key=settings.vast_access_key,
            secret_key=settings.vast_secret_key,
            bucket=settings.vast_bucket,
            schema=settings.vast_schema
        )
        
        print("✅ VAST store initialized")
        
        # Check if users table exists
        if 'users' in vast_store.db_manager.tables:
            print("✅ Users table exists")
            
            # Try to get admin user
            admin_user = await vast_store.get_user_by_username('admin')
            if admin_user:
                print(f"✅ Admin user found: {admin_user.username}")
                print(f"   User ID: {admin_user.user_id}")
                print(f"   Is Admin: {admin_user.is_admin}")
                print(f"   Is Active: {admin_user.is_active}")
                print(f"   Has Password Hash: {bool(admin_user.password_hash)}")
            else:
                print("❌ Admin user not found")
                
                # Let's see what's in the users table
                print("\n🔍 Checking what's in the users table...")
                try:
                    # Query all users
                    all_users = vast_store.db_manager.select('users', {}, columns=['user_id', 'username', 'is_admin'])
                    print(f"Users table contents: {all_users}")
                except Exception as e:
                    print(f"❌ Error querying users table: {e}")
        else:
            print("❌ Users table does not exist")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_users_table())
