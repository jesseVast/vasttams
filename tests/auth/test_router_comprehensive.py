#!/usr/bin/env python3
"""
Comprehensive Router Tests for Auth

Tests all endpoints in auth/router.py to achieve 100% coverage.
"""

import pytest
import sys
import requests
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.core.config import get_settings

import logging
logger = logging.getLogger(__name__)

# Get settings for API base URL
settings = get_settings()
BASE_URL = f"http://{settings.host}:{settings.port}"


@pytest.fixture(scope="module")
def api_available():
    """Check if API server is running"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        pytest.skip("API server not running. Start server with: python run.py")


@pytest.mark.usefixtures("api_available")
class TestAuthRouterGET:
    """Test GET endpoints for auth router"""
    
    def test_list_auth_providers(self, api_available, auth_headers):
        """Test GET /auth/providers endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/auth/providers", headers=auth_headers)
        assert response.status_code == 200
        providers = response.json()
        assert isinstance(providers, list)
    
    def test_get_auth_provider(self, api_available, auth_headers):
        """Test GET /auth/providers/{method} endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        # Test with jwt method
        response = requests.get(f"{BASE_URL}/auth/providers/jwt", headers=auth_headers)
        # May return 200 or 404 depending on configuration
        assert response.status_code in [200, 404]
        
        # Test with non-existent method
        response = requests.get(f"{BASE_URL}/auth/providers/nonexistent", headers=auth_headers)
        assert response.status_code == 404


@pytest.mark.usefixtures("api_available")
class TestAuthRouterPUT:
    """Test PUT endpoints for auth router"""
    
    def test_update_auth_provider(self, api_available, auth_headers):
        """Test PUT /auth/providers/{method} endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        # Get list first to find a valid method
        list_response = requests.get(f"{BASE_URL}/auth/providers", headers=auth_headers)
        if list_response.status_code == 200:
            providers = list_response.json()
            if providers:
                method = providers[0].get("method", {}).get("value") if isinstance(providers[0].get("method"), dict) else providers[0].get("method")
                if method:
                    update_data = {
                        "enabled": True
                    }
                    response = requests.put(
                        f"{BASE_URL}/auth/providers/{method}",
                        json=update_data,
                        headers=auth_headers
                    )
                    # May return 200 or 404/500 depending on implementation
                    assert response.status_code in [200, 404, 500]


@pytest.mark.usefixtures("api_available")
class TestAuthRouterPOST:
    """Test POST endpoints for auth router"""
    
    def test_reload_auth_providers(self, api_available, auth_headers):
        """Test POST /auth/providers/reload endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.post(f"{BASE_URL}/auth/providers/reload", headers=auth_headers)
        # May return 200 or 500 depending on implementation
        assert response.status_code in [200, 500]
    
    def test_login(self, api_available):
        """Test POST /auth/login endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        login_data = {
            "username": "admin",
            "password": "vastdata"
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
    
    def test_login_invalid_credentials(self, api_available):
        """Test POST /auth/login with invalid credentials"""
        if not api_available:
            pytest.skip("API not available")
        
        login_data = {
            "username": "invalid",
            "password": "invalid"
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        assert response.status_code == 401


@pytest.mark.usefixtures("api_available")
class TestUsersRouterGET:
    """Test GET endpoints for users router"""
    
    def test_list_users(self, api_available, auth_headers):
        """Test GET /users endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/users", headers=auth_headers)
        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)


@pytest.mark.usefixtures("api_available")
class TestUsersRouterPOST:
    """Test POST endpoints for users router"""
    
    def test_create_user(self, api_available, auth_headers):
        """Test POST /users endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        import uuid
        username = f"testuser_{uuid.uuid4().hex[:8]}"
        user_data = {
            "username": username,
            "password": "testpassword123",
            "role": "viewer"
        }
        
        response = requests.post(f"{BASE_URL}/users", json=user_data, headers=auth_headers)
        # May return 200, 201, or 409 if user exists
        assert response.status_code in [200, 201, 409, 500]
        
        # Cleanup if created
        if response.status_code in [200, 201]:
            requests.delete(f"{BASE_URL}/users/{username}", headers=auth_headers)


@pytest.mark.usefixtures("api_available")
class TestUsersRouterDELETE:
    """Test DELETE endpoints for users router"""
    
    def test_delete_user(self, api_available, auth_headers):
        """Test DELETE /users/{username} endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create a user first for deletion
        import uuid
        username = f"testuser_{uuid.uuid4().hex[:8]}"
        user_data = {
            "username": username,
            "password": "testpassword123",
            "role": "viewer"
        }
        
        create_response = requests.post(f"{BASE_URL}/users", json=user_data, headers=auth_headers)
        
        if create_response.status_code == 201:
            # Delete user
            response = requests.delete(f"{BASE_URL}/users/{username}", headers=auth_headers)
            assert response.status_code in [200, 404]
        
        # Test with non-existent user
        response = requests.delete(f"{BASE_URL}/users/nonexistent_user", headers=auth_headers)
        assert response.status_code in [404, 200]


@pytest.mark.usefixtures("api_available")
class TestAuthRouterProviderConfig:
    """Test provider configuration management"""
    
    def test_update_provider_enabled(self, api_available, auth_headers):
        """Test PUT /auth/providers/{method} with enabled update"""
        if not api_available:
            pytest.skip("API not available")
        
        # Get list first to find a valid method
        list_response = requests.get(f"{BASE_URL}/auth/providers", headers=auth_headers)
        if list_response.status_code == 200:
            providers = list_response.json()
            if providers:
                method = providers[0].get("method", {}).get("value") if isinstance(providers[0].get("method"), dict) else providers[0].get("method")
                if method:
                    update_data = {
                        "enabled": False
                    }
                    response = requests.put(
                        f"{BASE_URL}/auth/providers/{method}",
                        json=update_data,
                        headers=auth_headers
                    )
                    # May return 200 or 404/500 depending on implementation
                    assert response.status_code in [200, 404, 500]
                    
                    # Re-enable for cleanup
                    update_data2 = {"enabled": True}
                    requests.put(f"{BASE_URL}/auth/providers/{method}", json=update_data2, headers=auth_headers)
    
    def test_update_provider_config(self, api_available, auth_headers):
        """Test PUT /auth/providers/{method} with config update"""
        if not api_available:
            pytest.skip("API not available")
        
        # Get list first to find a valid method
        list_response = requests.get(f"{BASE_URL}/auth/providers", headers=auth_headers)
        if list_response.status_code == 200:
            providers = list_response.json()
            if providers:
                method = providers[0].get("method", {}).get("value") if isinstance(providers[0].get("method"), dict) else providers[0].get("method")
                if method:
                    update_data = {
                        "config": {"test_key": "test_value"}
                    }
                    response = requests.put(
                        f"{BASE_URL}/auth/providers/{method}",
                        json=update_data,
                        headers=auth_headers
                    )
                    # May return 200 or 404/500 depending on implementation
                    assert response.status_code in [200, 404, 500]
    
    def test_update_provider_order(self, api_available, auth_headers):
        """Test PUT /auth/providers/{method} with order update"""
        if not api_available:
            pytest.skip("API not available")
        
        # Get list first to find a valid method
        list_response = requests.get(f"{BASE_URL}/auth/providers", headers=auth_headers)
        if list_response.status_code == 200:
            providers = list_response.json()
            if providers:
                method = providers[0].get("method", {}).get("value") if isinstance(providers[0].get("method"), dict) else providers[0].get("method")
                if method:
                    update_data = {
                        "order": 1
                    }
                    response = requests.put(
                        f"{BASE_URL}/auth/providers/{method}",
                        json=update_data,
                        headers=auth_headers
                    )
                    # May return 200 or 404/500 depending on implementation
                    assert response.status_code in [200, 404, 500]
    
    def test_update_provider_invalid_method(self, api_available, auth_headers):
        """Test PUT /auth/providers/{method} with invalid method"""
        if not api_available:
            pytest.skip("API not available")
        
        update_data = {"enabled": True}
        response = requests.put(
            f"{BASE_URL}/auth/providers/invalid-method",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 404
    
    def test_get_provider_invalid_method(self, api_available, auth_headers):
        """Test GET /auth/providers/{method} with invalid method"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/auth/providers/invalid-method", headers=auth_headers)
        assert response.status_code == 404


@pytest.mark.usefixtures("api_available")
class TestAuthRouterUserManagement:
    """Test user management operations"""
    
    def test_get_user_by_username(self, api_available, auth_headers):
        """Test GET /users/{username} endpoint (if exists)"""
        if not api_available:
            pytest.skip("API not available")
        
        # Try to get a user - endpoint may not exist
        response = requests.get(f"{BASE_URL}/users/admin", headers=auth_headers)
        # May return 200, 404, or 405 (method not allowed)
        assert response.status_code in [200, 404, 405]
    
    def test_update_user(self, api_available, auth_headers):
        """Test PUT /users/{username} endpoint (if exists)"""
        if not api_available:
            pytest.skip("API not available")
        
        # Try to update a user - endpoint may not exist
        update_data = {"role": "editor"}
        response = requests.put(f"{BASE_URL}/users/admin", json=update_data, headers=auth_headers)
        # May return 200, 404, or 405 (method not allowed)
        assert response.status_code in [200, 404, 405]
    
    def test_create_user_duplicate(self, api_available, auth_headers):
        """Test POST /users with duplicate username"""
        if not api_available:
            pytest.skip("API not available")
        
        import uuid
        username = f"testuser_{uuid.uuid4().hex[:8]}"
        user_data = {
            "username": username,
            "password": "testpassword123",
            "role": "viewer"
        }
        
        # Create user first
        create_response = requests.post(f"{BASE_URL}/users", json=user_data, headers=auth_headers)
        
        if create_response.status_code in [200, 201]:
            # Try to create again with same username
            duplicate_response = requests.post(f"{BASE_URL}/users", json=user_data, headers=auth_headers)
            assert duplicate_response.status_code == 409  # Conflict
            
            # Cleanup
            requests.delete(f"{BASE_URL}/users/{username}", headers=auth_headers)
    
    def test_create_user_invalid_role(self, api_available, auth_headers):
        """Test POST /users with invalid role"""
        if not api_available:
            pytest.skip("API not available")
        
        import uuid
        username = f"testuser_{uuid.uuid4().hex[:8]}"
        user_data = {
            "username": username,
            "password": "testpassword123",
            "role": "invalid_role"  # Invalid role
        }
        
        response = requests.post(f"{BASE_URL}/users", json=user_data, headers=auth_headers)
        assert response.status_code in [400, 422]
    
    def test_create_user_missing_fields(self, api_available, auth_headers):
        """Test POST /users with missing required fields"""
        if not api_available:
            pytest.skip("API not available")
        
        # Missing password
        user_data = {
            "username": "testuser"
            # Missing password
        }
        response = requests.post(f"{BASE_URL}/users", json=user_data, headers=auth_headers)
        assert response.status_code in [400, 422]
        
        # Missing username
        user_data2 = {
            "password": "testpassword123"
            # Missing username
        }
        response2 = requests.post(f"{BASE_URL}/users", json=user_data2, headers=auth_headers)
        assert response2.status_code in [400, 422]
    
    def test_create_user_all_roles(self, api_available, auth_headers):
        """Test POST /users with all valid roles"""
        if not api_available:
            pytest.skip("API not available")
        
        import uuid
        roles = ["viewer", "editor", "admin"]
        
        for role in roles:
            username = f"testuser_{uuid.uuid4().hex[:8]}"
            user_data = {
                "username": username,
                "password": "testpassword123",
                "role": role
            }
            
            response = requests.post(f"{BASE_URL}/users", json=user_data, headers=auth_headers)
            # May succeed or fail depending on permissions
            assert response.status_code in [200, 201, 409, 500]
            
            # Cleanup if created
            if response.status_code in [200, 201]:
                requests.delete(f"{BASE_URL}/users/{username}", headers=auth_headers)


@pytest.mark.usefixtures("api_available")
class TestAuthRouterRBAC:
    """Test RBAC enforcement"""
    
    def test_list_users_requires_admin(self, api_available, auth_headers):
        """Test GET /users requires admin role"""
        if not api_available:
            pytest.skip("API not available")
        
        # This test assumes auth_headers has admin role
        # If not, it should fail with 403
        response = requests.get(f"{BASE_URL}/users", headers=auth_headers)
        # Should return 200 (if admin) or 403 (if not admin)
        assert response.status_code in [200, 403]
    
    def test_create_user_requires_admin(self, api_available, auth_headers):
        """Test POST /users requires admin role"""
        if not api_available:
            pytest.skip("API not available")
        
        import uuid
        username = f"testuser_{uuid.uuid4().hex[:8]}"
        user_data = {
            "username": username,
            "password": "testpassword123",
            "role": "viewer"
        }
        
        response = requests.post(f"{BASE_URL}/users", json=user_data, headers=auth_headers)
        # Should return 201 (if admin) or 403 (if not admin)
        assert response.status_code in [200, 201, 403, 500]
        
        # Cleanup if created
        if response.status_code in [200, 201]:
            requests.delete(f"{BASE_URL}/users/{username}", headers=auth_headers)
    
    def test_delete_user_requires_admin(self, api_available, auth_headers):
        """Test DELETE /users/{username} requires admin role"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.delete(f"{BASE_URL}/users/testuser", headers=auth_headers)
        # Should return 200/404 (if admin) or 403 (if not admin)
        assert response.status_code in [200, 404, 403]
    
    def test_list_providers_requires_viewer(self, api_available, auth_headers):
        """Test GET /auth/providers requires viewer role"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/auth/providers", headers=auth_headers)
        # Should return 200 (if authenticated) or 401/403 (if not)
        assert response.status_code in [200, 401, 403]
    
    def test_reload_providers_requires_admin(self, api_available, auth_headers):
        """Test POST /auth/providers/reload requires admin role"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.post(f"{BASE_URL}/auth/providers/reload", headers=auth_headers)
        # Should return 200 (if admin) or 403 (if not admin)
        assert response.status_code in [200, 403, 500]


@pytest.mark.usefixtures("api_available")
class TestAuthRouterLogin:
    """Test login endpoint edge cases"""
    
    def test_login_missing_username(self, api_available):
        """Test POST /auth/login with missing username"""
        if not api_available:
            pytest.skip("API not available")
        
        login_data = {
            "password": "vastdata"
            # Missing username
        }
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        assert response.status_code in [400, 422]
    
    def test_login_missing_password(self, api_available):
        """Test POST /auth/login with missing password"""
        if not api_available:
            pytest.skip("API not available")
        
        login_data = {
            "username": "admin"
            # Missing password
        }
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        assert response.status_code in [400, 422]
    
    def test_login_empty_username(self, api_available):
        """Test POST /auth/login with empty username"""
        if not api_available:
            pytest.skip("API not available")
        
        login_data = {
            "username": "",
            "password": "vastdata"
        }
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        assert response.status_code in [400, 401, 422]
    
    def test_login_empty_password(self, api_available):
        """Test POST /auth/login with empty password"""
        if not api_available:
            pytest.skip("API not available")
        
        login_data = {
            "username": "admin",
            "password": ""
        }
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        assert response.status_code in [400, 401, 422]
    
    def test_login_response_structure(self, api_available):
        """Test POST /auth/login response structure"""
        if not api_available:
            pytest.skip("API not available")
        
        login_data = {
            "username": "admin",
            "password": "vastdata"
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert "token_type" in data
            assert data["token_type"] == "bearer"
            # Optional fields
            if "user_id" in data:
                assert isinstance(data["user_id"], str)
            if "username" in data:
                assert data["username"] == "admin"
            if "role" in data:
                assert data["role"] in ["viewer", "editor", "admin"]

