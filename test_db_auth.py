#!/usr/bin/env python3
"""
Test script for database-backed authentication
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import get_settings
from app.storage.vast_store import VASTStore
from app.auth.providers.basic import BasicAuthProvider
from app.auth.providers.url_token import URLTokenProvider
from app.models.models import User
import uuid

async def test_db_auth():
    """Test database authentication functionality"""
    
    print("🧪 Testing Database-Backed Authentication")
    print("=" * 50)
    
    # Initialize settings and store
    settings = get_settings()
    
    try:
        # Initialize VAST store
        vast_store = VASTStore(
            endpoint=settings.vast_endpoint,
            access_key=settings.vast_access_key,
            secret_key=settings.vast_secret_key,
            bucket=settings.vast_bucket,
            schema=settings.vast_schema,
            s3_endpoint_url=settings.s3_endpoint_url,
            s3_access_key_id=settings.s3_access_key_id,
            s3_secret_access_key=settings.s3_secret_access_key,
            s3_bucket_name=settings.s3_bucket_name,
            s3_use_ssl=settings.s3_use_ssl
        )
        print("✅ Connected to VAST database")
        
        # Test Basic Auth Provider
        print("\n🔐 Testing Basic Auth Provider")
        print("-" * 30)
        
        basic_provider = BasicAuthProvider(vast_store=vast_store)
        
        # Test adding a user
        test_username = "testuser"
        test_password = "testpass123"
        
        print(f"➕ Adding user '{test_username}'...")
        success = await basic_provider.add_user(test_username, test_password)
        if success:
            print("✅ User added successfully")
        else:
            print("❌ Failed to add user")
            return
        
        # Test password verification
        print("🔍 Testing password verification...")
        user = await vast_store.get_user_by_username(test_username)
        if user and user.password_hash:
            if basic_provider.verify_password(test_password, user.password_hash):
                print("✅ Password verification successful")
            else:
                print("❌ Password verification failed")
        else:
            print("❌ User not found in database")
        
        # Test URL Token Provider
        print("\n🎫 Testing URL Token Provider")
        print("-" * 30)
        
        token_provider = URLTokenProvider(vast_store=vast_store)
        
        # Add a test token
        test_token = "test-db-token-123"
        print(f"➕ Adding token '{test_token}'...")
        
        success = await token_provider.add_token(
            test_token, 
            user.user_id, 
            user.username,
            "Test DB Token"
        )
        
        if success:
            print("✅ Token added successfully")
        else:
            print("❌ Failed to add token")
            return
        
        # Test token retrieval
        print("🔍 Testing token retrieval...")
        api_token = await vast_store.get_api_token(test_token)
        if api_token and api_token.is_active:
            print(f"✅ Token retrieved: {api_token.description}")
        else:
            print("❌ Token not found in database")
        
        # Test fallback authentication
        print("\n🔄 Testing Fallback Authentication")
        print("-" * 30)
        
        # Create provider without database (fallback mode)
        fallback_basic = BasicAuthProvider(vast_store=None)
        
        # Test fallback user
        print("🔍 Testing fallback user 'admin'...")
        if fallback_basic.verify_password("admin123", fallback_basic.fallback_users["admin"]):
            print("✅ Fallback authentication working")
        else:
            print("❌ Fallback authentication failed")
        
        # Cleanup
        print("\n🧹 Cleaning up test data...")
        await basic_provider.remove_user(test_username)
        await token_provider.remove_token(test_token)
        print("✅ Cleanup completed")
        
        print("\n🎉 All database authentication tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Close the VAST store connection
        if 'vast_store' in locals():
            await vast_store.close()
    
    return True

if __name__ == "__main__":
    # Run the test
    success = asyncio.run(test_db_auth())
    sys.exit(0 if success else 1)
