#!/usr/bin/env python3
"""
Tests for Authentication Core (AuthManager)

Tests AuthManager functionality.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from fastapi import Request

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.auth.core import AuthManager, AuthProvider
from vasttamsserver.auth.models import AuthResult, AuthMethod, UserRole
from vasttamsserver.auth.providers.jwt import JWTProvider
from vasttamsserver.auth.providers.basic import BasicAuthProvider
from vasttamsserver.auth.providers.url_token import URLTokenProvider


class TestAuthManager:
    """Test AuthManager"""
    
    def test_init(self):
        """Test AuthManager initialization"""
        manager = AuthManager()
        
        assert manager.providers == []
        assert isinstance(manager.providers, list)
    
    def test_add_provider(self):
        """Test add_provider"""
        manager = AuthManager()
        provider = JWTProvider()
        
        manager.add_provider(provider)
        
        assert len(manager.providers) == 1
        assert manager.providers[0] == provider
    
    def test_add_multiple_providers(self):
        """Test adding multiple providers"""
        manager = AuthManager()
        
        jwt_provider = JWTProvider()
        basic_provider = BasicAuthProvider()
        url_token_provider = URLTokenProvider()
        
        manager.add_provider(jwt_provider)
        manager.add_provider(basic_provider)
        manager.add_provider(url_token_provider)
        
        assert len(manager.providers) == 3
        assert jwt_provider in manager.providers
        assert basic_provider in manager.providers
        assert url_token_provider in manager.providers
    
    @pytest.mark.asyncio
    async def test_authenticate_success_first_provider(self):
        """Test authenticate succeeds with first provider"""
        manager = AuthManager()
        
        # Create mock providers
        mock_provider1 = Mock(spec=AuthProvider)
        mock_provider1.is_enabled = Mock(return_value=True)
        mock_provider1.get_method = Mock(return_value=AuthMethod.BEARER)
        mock_provider1.authenticate = AsyncMock(return_value=AuthResult(
            success=True,
            user_id="user1",
            username="testuser",
            role=UserRole.VIEWER
        ))
        
        mock_provider2 = Mock(spec=AuthProvider)
        mock_provider2.is_enabled = Mock(return_value=True)
        mock_provider2.authenticate = AsyncMock()
        
        manager.add_provider(mock_provider1)
        manager.add_provider(mock_provider2)
        
        mock_request = Mock()
        result = await manager.authenticate(mock_request)
        
        assert result.success is True
        assert result.user_id == "user1"
        assert result.username == "testuser"
        assert result.auth_method == AuthMethod.BEARER
        
        # Second provider should not be called
        mock_provider2.authenticate.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_authenticate_success_second_provider(self):
        """Test authenticate succeeds with second provider when first fails"""
        manager = AuthManager()
        
        # Create mock providers
        mock_provider1 = Mock(spec=AuthProvider)
        mock_provider1.is_enabled = Mock(return_value=True)
        mock_provider1.authenticate = AsyncMock(return_value=AuthResult(
            success=False,
            error="First provider failed"
        ))
        
        mock_provider2 = Mock(spec=AuthProvider)
        mock_provider2.is_enabled = Mock(return_value=True)
        mock_provider2.get_method = Mock(return_value=AuthMethod.BASIC)
        mock_provider2.authenticate = AsyncMock(return_value=AuthResult(
            success=True,
            user_id="user2",
            username="testuser2",
            role=UserRole.EDITOR
        ))
        
        manager.add_provider(mock_provider1)
        manager.add_provider(mock_provider2)
        
        mock_request = Mock()
        result = await manager.authenticate(mock_request)
        
        assert result.success is True
        assert result.user_id == "user2"
        assert result.username == "testuser2"
        assert result.auth_method == AuthMethod.BASIC
        
        # Both providers should be called
        mock_provider1.authenticate.assert_called_once()
        mock_provider2.authenticate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_all_providers_fail(self):
        """Test authenticate when all providers fail"""
        manager = AuthManager()
        
        # Create mock providers that all fail
        mock_provider1 = Mock(spec=AuthProvider)
        mock_provider1.is_enabled = Mock(return_value=True)
        mock_provider1.authenticate = AsyncMock(return_value=AuthResult(
            success=False,
            error="Provider 1 failed"
        ))
        
        mock_provider2 = Mock(spec=AuthProvider)
        mock_provider2.is_enabled = Mock(return_value=True)
        mock_provider2.authenticate = AsyncMock(return_value=AuthResult(
            success=False,
            error="Provider 2 failed"
        ))
        
        manager.add_provider(mock_provider1)
        manager.add_provider(mock_provider2)
        
        mock_request = Mock()
        result = await manager.authenticate(mock_request)
        
        assert result.success is False
        assert "Authentication failed" in result.error
        
        # Both providers should be called
        mock_provider1.authenticate.assert_called_once()
        mock_provider2.authenticate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_skips_disabled_provider(self):
        """Test authenticate skips disabled providers"""
        manager = AuthManager()
        
        # Create disabled provider
        mock_provider1 = Mock(spec=AuthProvider)
        mock_provider1.is_enabled = Mock(return_value=False)
        mock_provider1.authenticate = AsyncMock()
        
        # Create enabled provider
        mock_provider2 = Mock(spec=AuthProvider)
        mock_provider2.is_enabled = Mock(return_value=True)
        mock_provider2.get_method = Mock(return_value=AuthMethod.BASIC)
        mock_provider2.authenticate = AsyncMock(return_value=AuthResult(
            success=True,
            user_id="user1",
            username="testuser",
            role=UserRole.VIEWER
        ))
        
        manager.add_provider(mock_provider1)
        manager.add_provider(mock_provider2)
        
        mock_request = Mock()
        result = await manager.authenticate(mock_request)
        
        assert result.success is True
        
        # Disabled provider should not be called
        mock_provider1.authenticate.assert_not_called()
        # Enabled provider should be called
        mock_provider2.authenticate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_provider_exception(self):
        """Test authenticate handles provider exceptions gracefully"""
        manager = AuthManager()
        
        # Create provider that raises exception
        mock_provider1 = Mock(spec=AuthProvider)
        mock_provider1.is_enabled = Mock(return_value=True)
        mock_provider1.authenticate = AsyncMock(side_effect=Exception("Provider error"))
        
        # Create working provider
        mock_provider2 = Mock(spec=AuthProvider)
        mock_provider2.is_enabled = Mock(return_value=True)
        mock_provider2.get_method = Mock(return_value=AuthMethod.BASIC)
        mock_provider2.authenticate = AsyncMock(return_value=AuthResult(
            success=True,
            user_id="user1",
            username="testuser",
            role=UserRole.VIEWER
        ))
        
        manager.add_provider(mock_provider1)
        manager.add_provider(mock_provider2)
        
        mock_request = Mock()
        result = await manager.authenticate(mock_request)
        
        # Should continue to next provider despite exception
        assert result.success is True
        assert result.user_id == "user1"
    
    @pytest.mark.asyncio
    async def test_authenticate_no_providers(self):
        """Test authenticate with no providers"""
        manager = AuthManager()
        
        mock_request = Mock()
        result = await manager.authenticate(mock_request)
        
        assert result.success is False
        assert "Authentication failed" in result.error
    
    @pytest.mark.asyncio
    async def test_authenticate_all_providers_disabled(self):
        """Test authenticate when all providers are disabled"""
        manager = AuthManager()
        
        mock_provider = Mock(spec=AuthProvider)
        mock_provider.is_enabled = Mock(return_value=False)
        mock_provider.authenticate = AsyncMock()
        
        manager.add_provider(mock_provider)
        
        mock_request = Mock()
        result = await manager.authenticate(mock_request)
        
        assert result.success is False
        # Provider should not be called
        mock_provider.authenticate.assert_not_called()

