#!/usr/bin/env python3
"""
Simple test script for TAMS API 7.0 authentication
"""

import asyncio
from fastapi import Request
from fastapi.testclient import TestClient

# Import our authentication system
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.auth.core import AuthManager
from app.auth.providers.jwt import JWTProvider
from app.auth.providers.basic import BasicAuthProvider
from app.auth.providers.url_token import URLTokenProvider
from app.auth.models import AuthResult

async def test_auth_providers():
    """Test all authentication providers"""
    print("🧪 Testing TAMS API 7.0 Authentication System")
    print("=" * 50)
    
    # Initialize auth manager
    auth_manager = AuthManager()
    
    # Add providers
    jwt_provider = JWTProvider(jwt_secret="test-secret")
    basic_provider = BasicAuthProvider()
    url_token_provider = URLTokenProvider()
    
    auth_manager.add_provider(jwt_provider)
    auth_manager.add_provider(basic_provider)
    auth_manager.add_provider(url_token_provider)
    
    print(f"✅ Added {len(auth_manager.providers)} providers to auth manager")
    
    # Test JWT Provider
    print("\n🔐 Testing JWT Provider:")
    print(f"  Enabled: {jwt_provider.is_enabled()}")
    print(f"  Method: {jwt_provider.get_method()}")
    
    # Create a test token
    token = jwt_provider.create_token("test-user", "test-username")
    print(f"  Created token: {token[:20]}...")
    
    # Test Basic Auth Provider
    print("\n🔑 Testing Basic Auth Provider:")
    print(f"  Enabled: {basic_provider.is_enabled()}")
    print(f"  Method: {basic_provider.get_method()}")
    print(f"  Users: {list(basic_provider.users.keys())}")
    
    # Test URL Token Provider
    print("\n🔗 Testing URL Token Provider:")
    print(f"  Enabled: {url_token_provider.is_enabled()}")
    print(f"  Method: {url_token_provider.get_method()}")
    print(f"  Tokens: {list(url_token_provider.valid_tokens.keys())}")
    
    # Test provider management
    print("\n⚙️ Testing Provider Management:")
    print(f"  Total providers: {len(auth_manager.providers)}")
    
    for i, provider in enumerate(auth_manager.providers):
        print(f"  Provider {i+1}: {provider.get_method()} - {'Enabled' if provider.is_enabled() else 'Disabled'}")
    
    print("\n✅ All authentication providers initialized successfully!")
    return auth_manager

def test_auth_manager():
    """Test auth manager functionality"""
    print("\n🧪 Testing Auth Manager:")
    
    # This would require a mock request object
    # For now, just test the structure
    auth_manager = AuthManager()
    
    jwt_provider = JWTProvider(jwt_secret="test-secret")
    basic_provider = BasicAuthProvider()
    url_token_provider = URLTokenProvider()
    
    auth_manager.add_provider(jwt_provider)
    auth_manager.add_provider(basic_provider)
    auth_manager.add_provider(url_token_provider)
    
    print(f"  Providers added: {len(auth_manager.providers)}")
    print("  ✅ Auth manager ready for testing")
    
    return auth_manager

if __name__ == "__main__":
    print("🚀 Starting TAMS Authentication Tests")
    print("=" * 50)
    
    # Run async tests
    auth_manager = asyncio.run(test_auth_providers())
    
    # Run sync tests
    test_auth_manager()
    
    print("\n" + "=" * 50)
    print("✅ Authentication system test completed!")
    print("\n📋 Next steps:")
    print("  1. Run 'python test_auth.py' to start the test server")
    print("  2. Test endpoints with curl or browser")
    print("  3. Verify all authentication methods work")
    print("  4. Integrate with main TAMS API when ready") 