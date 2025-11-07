#!/usr/bin/env python3
"""
Tests for Authentication Providers

Tests JWT, Basic, and URL Token providers to achieve coverage.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import jwt
from datetime import datetime, timedelta, timezone

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.auth.providers.jwt import JWTProvider
from vasttams.auth.providers.basic import BasicAuthProvider
from vasttams.auth.providers.url_token import URLTokenProvider
from vasttams.auth.models import AuthMethod, UserRole, AuthResult


class TestJWTProvider:
    """Test JWT authentication provider"""
    
    def test_init(self):
        """Test JWTProvider initialization"""
        provider = JWTProvider()
        assert provider.jwt_secret == "your-secret-key"
        assert provider.jwt_algorithm == "HS256"
        assert provider.jwt_expire_minutes == 30
        assert provider.is_enabled() is True
    
    def test_init_custom_config(self):
        """Test JWTProvider with custom configuration"""
        provider = JWTProvider(
            jwt_secret="custom-secret",
            jwt_algorithm="HS512",
            jwt_expire_minutes=60
        )
        assert provider.jwt_secret == "custom-secret"
        assert provider.jwt_algorithm == "HS512"
        assert provider.jwt_expire_minutes == 60
    
    def test_get_method(self):
        """Test get_method returns BEARER"""
        provider = JWTProvider()
        assert provider.get_method() == AuthMethod.BEARER
    
    def test_is_enabled(self):
        """Test is_enabled"""
        provider = JWTProvider()
        assert provider.is_enabled() is True
        
        provider.set_enabled(False)
        assert provider.is_enabled() is False
        
        provider.set_enabled(True)
        assert provider.is_enabled() is True
    
    def test_set_enabled(self):
        """Test set_enabled"""
        provider = JWTProvider()
        provider.set_enabled(False)
        assert provider._enabled is False
        
        provider.set_enabled(True)
        assert provider._enabled is True
    
    def test_create_token(self):
        """Test create_token"""
        provider = JWTProvider(jwt_secret="test-secret")
        token = provider.create_token("user1", "testuser", UserRole.VIEWER)
        
        assert token is not None
        assert isinstance(token, str)
        
        # Decode to verify
        payload = jwt.decode(token, "test-secret", algorithms=["HS256"])
        assert payload["sub"] == "user1"
        assert payload["username"] == "testuser"
        assert payload["role"] == "viewer"
    
    def test_create_token_with_expiration(self):
        """Test create_token with custom expiration"""
        provider = JWTProvider(jwt_secret="test-secret", jwt_expire_minutes=60)
        token = provider.create_token("user1", "testuser", UserRole.ADMIN)
        
        payload = jwt.decode(token, "test-secret", algorithms=["HS256"])
        assert payload["role"] == "admin"
        
        # Check expiration is set
        assert "exp" in payload
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self):
        """Test authenticate with valid token"""
        provider = JWTProvider(jwt_secret="test-secret")
        token = provider.create_token("user1", "testuser", UserRole.VIEWER)
        
        # Create mock request with Bearer token
        mock_request = Mock()
        mock_credentials = Mock()
        mock_credentials.credentials = token
        provider.security = AsyncMock(return_value=mock_credentials)
        
        result = await provider.authenticate(mock_request)
        
        assert result.success is True
        assert result.user_id == "user1"
        assert result.username == "testuser"
        assert result.role == UserRole.VIEWER
    
    @pytest.mark.asyncio
    async def test_authenticate_no_token(self):
        """Test authenticate with no token"""
        provider = JWTProvider()
        
        mock_request = Mock()
        provider.security = AsyncMock(return_value=None)
        
        result = await provider.authenticate(mock_request)
        
        assert result.success is False
        assert "No Bearer token" in result.error
    
    @pytest.mark.asyncio
    async def test_authenticate_expired_token(self):
        """Test authenticate with expired token"""
        provider = JWTProvider(jwt_secret="test-secret")
        
        # Create expired token
        expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {
            "sub": "user1",
            "username": "testuser",
            "exp": int(expired_time.timestamp())
        }
        expired_token = jwt.encode(payload, "test-secret", algorithm="HS256")
        
        mock_request = Mock()
        mock_credentials = Mock()
        mock_credentials.credentials = expired_token
        provider.security = AsyncMock(return_value=mock_credentials)
        
        result = await provider.authenticate(mock_request)
        
        assert result.success is False
        assert "expired" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_authenticate_invalid_token(self):
        """Test authenticate with invalid token"""
        provider = JWTProvider(jwt_secret="test-secret")
        
        mock_request = Mock()
        mock_credentials = Mock()
        mock_credentials.credentials = "invalid-token"
        provider.security = AsyncMock(return_value=mock_credentials)
        
        result = await provider.authenticate(mock_request)
        
        assert result.success is False
        assert "Invalid" in result.error or "error" in result.error.lower()
    
    def test_is_enabled_no_secret(self):
        """Test is_enabled returns False when secret is None"""
        provider = JWTProvider(jwt_secret=None)
        assert provider.is_enabled() is False


class TestBasicAuthProvider:
    """Test Basic authentication provider"""
    
    def test_init(self):
        """Test BasicAuthProvider initialization"""
        provider = BasicAuthProvider()
        assert provider.get_method() == AuthMethod.BASIC
        assert provider.is_enabled() is True
        assert len(provider.fallback_users) > 0
    
    def test_init_with_vast_store(self):
        """Test BasicAuthProvider with vast_store"""
        mock_store = Mock()
        provider = BasicAuthProvider(vast_store=mock_store)
        assert provider.vast_store == mock_store
        assert provider.user_service is not None
    
    def test_get_method(self):
        """Test get_method returns BASIC"""
        provider = BasicAuthProvider()
        assert provider.get_method() == AuthMethod.BASIC
    
    def test_is_enabled(self):
        """Test is_enabled"""
        provider = BasicAuthProvider()
        assert provider.is_enabled() is True
        
        provider.set_enabled(False)
        assert provider.is_enabled() is False
    
    def test_hash_password(self):
        """Test hash_password"""
        provider = BasicAuthProvider()
        password = "testpassword"
        hashed = provider.hash_password(password)
        
        assert hashed is not None
        assert hashed != password
        assert hashed.startswith("$2b$")
    
    def test_verify_password(self):
        """Test verify_password"""
        provider = BasicAuthProvider()
        password = "testpassword"
        hashed = provider.hash_password(password)
        
        assert provider.verify_password(password, hashed) is True
        assert provider.verify_password("wrongpassword", hashed) is False
    
    @pytest.mark.asyncio
    async def test_authenticate_success_fallback(self):
        """Test authenticate with valid fallback credentials"""
        provider = BasicAuthProvider()
        
        # Create mock request with Basic auth
        mock_request = Mock()
        mock_credentials = Mock()
        mock_credentials.username = "admin"
        mock_credentials.password = "admin123"
        provider.security = AsyncMock(return_value=mock_credentials)
        
        result = await provider.authenticate(mock_request)
        
        assert result.success is True
        assert result.username == "admin"
    
    @pytest.mark.asyncio
    async def test_authenticate_invalid_credentials(self):
        """Test authenticate with invalid credentials"""
        provider = BasicAuthProvider()
        
        mock_request = Mock()
        mock_credentials = Mock()
        mock_credentials.username = "invalid"
        mock_credentials.password = "invalid"
        provider.security = AsyncMock(return_value=mock_credentials)
        
        result = await provider.authenticate(mock_request)
        
        assert result.success is False
    
    @pytest.mark.asyncio
    async def test_authenticate_no_credentials(self):
        """Test authenticate with no credentials"""
        provider = BasicAuthProvider()
        
        mock_request = Mock()
        provider.security = AsyncMock(return_value=None)
        
        result = await provider.authenticate(mock_request)
        
        assert result.success is False
    
    @pytest.mark.asyncio
    async def test_add_user_fallback(self):
        """Test add_user with fallback storage"""
        provider = BasicAuthProvider()
        
        result = await provider.add_user("newuser", "newpassword")
        
        assert result is True
        assert "newuser" in provider.fallback_users
    
    @pytest.mark.asyncio
    async def test_add_user_database(self):
        """Test add_user with database storage"""
        mock_store = Mock()
        provider = BasicAuthProvider(vast_store=mock_store)
        provider.user_service = AsyncMock()
        provider.user_service.create_user = AsyncMock(return_value=Mock())
        
        result = await provider.add_user("newuser", "newpassword")
        
        assert result is True
        provider.user_service.create_user.assert_called_once()


class TestURLTokenProvider:
    """Test URL token authentication provider"""
    
    def test_init(self):
        """Test URLTokenProvider initialization"""
        provider = URLTokenProvider()
        assert provider.get_method() == AuthMethod.URL_TOKEN
        assert provider.is_enabled() is True
        assert len(provider.fallback_tokens) > 0
    
    def test_init_with_vast_store(self):
        """Test URLTokenProvider with vast_store"""
        mock_store = Mock()
        provider = URLTokenProvider(vast_store=mock_store)
        assert provider.vast_store == mock_store
    
    def test_get_method(self):
        """Test get_method returns URL_TOKEN"""
        provider = URLTokenProvider()
        assert provider.get_method() == AuthMethod.URL_TOKEN
    
    def test_is_enabled(self):
        """Test is_enabled"""
        provider = URLTokenProvider()
        assert provider.is_enabled() is True
        
        provider.set_enabled(False)
        assert provider.is_enabled() is False
    
    @pytest.mark.asyncio
    async def test_authenticate_success_fallback(self):
        """Test authenticate with valid fallback token"""
        provider = URLTokenProvider()
        
        mock_request = Mock()
        mock_request.query_params = {"access_token": "test-token"}
        
        result = await provider.authenticate(mock_request)
        
        assert result.success is True
        assert result.username == "test"
        assert result.user_id == "test-user"
    
    @pytest.mark.asyncio
    async def test_authenticate_no_token(self):
        """Test authenticate with no token"""
        provider = URLTokenProvider()
        
        mock_request = Mock()
        mock_request.query_params = {}
        
        result = await provider.authenticate(mock_request)
        
        assert result.success is False
        assert "No access_token" in result.error
    
    @pytest.mark.asyncio
    async def test_authenticate_invalid_token(self):
        """Test authenticate with invalid token"""
        provider = URLTokenProvider()
        
        mock_request = Mock()
        mock_request.query_params = {"access_token": "invalid-token"}
        
        result = await provider.authenticate(mock_request)
        
        assert result.success is False
    
    @pytest.mark.asyncio
    async def test_add_token_fallback(self):
        """Test add_token with fallback storage"""
        provider = URLTokenProvider()
        
        result = await provider.add_token("new-token", "user1", "testuser", "Test token")
        
        assert result is True
        assert "new-token" in provider.fallback_tokens
    
    @pytest.mark.asyncio
    async def test_remove_token_fallback(self):
        """Test remove_token with fallback storage"""
        provider = URLTokenProvider()
        
        # Add token first
        await provider.add_token("temp-token", "user1", "testuser")
        
        # Remove token
        result = await provider.remove_token("temp-token")
        
        assert result is True
        assert "temp-token" not in provider.fallback_tokens
    
    @pytest.mark.asyncio
    async def test_remove_token_not_found(self):
        """Test remove_token with non-existent token"""
        provider = URLTokenProvider()
        
        result = await provider.remove_token("nonexistent-token")
        
        assert result is False

