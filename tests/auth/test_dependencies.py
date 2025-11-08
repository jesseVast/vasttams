#!/usr/bin/env python3
"""
Tests for Authentication Dependencies

Tests auth dependency functions.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.auth.dependencies import (
    get_auth_manager,
    get_jwt_provider,
    get_basic_provider,
    get_url_token_provider
)
from vasttamsserver.auth.core import AuthManager
from vasttamsserver.auth.providers.jwt import JWTProvider
from vasttamsserver.auth.providers.basic import BasicAuthProvider
from vasttamsserver.auth.providers.url_token import URLTokenProvider


class TestAuthDependencies:
    """Test authentication dependency functions"""
    
    def test_get_jwt_provider(self):
        """Test get_jwt_provider"""
        provider = get_jwt_provider()
        
        assert isinstance(provider, JWTProvider)
        assert provider.get_method().value == "bearer"
    
    def test_get_basic_provider(self):
        """Test get_basic_provider"""
        mock_store = Mock()
        provider = get_basic_provider(mock_store)
        
        assert isinstance(provider, BasicAuthProvider)
        assert provider.get_method().value == "basic"
        assert provider.vast_store == mock_store
    
    def test_get_url_token_provider(self):
        """Test get_url_token_provider"""
        mock_store = Mock()
        provider = get_url_token_provider(mock_store)
        
        assert isinstance(provider, URLTokenProvider)
        assert provider.get_method().value == "url_token"
        assert provider.vast_store == mock_store
    
    def test_get_auth_manager_singleton(self):
        """Test get_auth_manager returns singleton"""
        # Clear global instance
        import vasttamsserver.auth.dependencies
        vasttamsserver.auth.dependencies._auth_manager = None
        
        mock_store = Mock()
        manager1 = get_auth_manager(mock_store)
        manager2 = get_auth_manager(mock_store)
        
        assert manager1 is manager2
        assert isinstance(manager1, AuthManager)
    
    def test_get_auth_manager_initializes_providers(self):
        """Test get_auth_manager initializes providers"""
        # Clear global instance
        import vasttamsserver.auth.dependencies
        vasttamsserver.auth.dependencies._auth_manager = None
        
        mock_store = Mock()
        manager = get_auth_manager(mock_store)
        
        assert len(manager.providers) > 0
        # Should have JWT, Basic, and URL Token providers
        provider_methods = [p.get_method().value for p in manager.providers]
        assert "bearer" in provider_methods
        assert "basic" in provider_methods
        assert "url_token" in provider_methods
    
    def test_get_auth_manager_reuses_instance(self):
        """Test get_auth_manager reuses same instance on subsequent calls"""
        import vasttamsserver.auth.dependencies
        vasttamsserver.auth.dependencies._auth_manager = None
        
        mock_store1 = Mock()
        mock_store2 = Mock()
        
        manager1 = get_auth_manager(mock_store1)
        manager2 = get_auth_manager(mock_store2)
        
        # Should be same instance
        assert manager1 is manager2
    
    def test_get_jwt_provider_creates_new(self):
        """Test get_jwt_provider creates new instance each time"""
        provider1 = get_jwt_provider()
        provider2 = get_jwt_provider()
        
        # Should be different instances
        assert provider1 is not provider2
        assert isinstance(provider1, JWTProvider)
        assert isinstance(provider2, JWTProvider)
    
    def test_get_basic_provider_with_store(self):
        """Test get_basic_provider with vast_store"""
        mock_store = Mock()
        provider = get_basic_provider(mock_store)
        
        assert isinstance(provider, BasicAuthProvider)
        assert provider.vast_store == mock_store
        assert provider.user_service is not None
    
    def test_get_url_token_provider_with_store(self):
        """Test get_url_token_provider with vast_store"""
        mock_store = Mock()
        provider = get_url_token_provider(mock_store)
        
        assert isinstance(provider, URLTokenProvider)
        assert provider.vast_store == mock_store

