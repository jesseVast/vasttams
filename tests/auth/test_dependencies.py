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

from vasttams.auth.dependencies import (
    get_auth_manager,
    get_jwt_provider,
    get_basic_provider,
    get_url_token_provider
)
from vasttams.auth.core import AuthManager
from vasttams.auth.providers.jwt import JWTProvider
from vasttams.auth.providers.basic import BasicAuthProvider
from vasttams.auth.providers.url_token import URLTokenProvider


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
        import vasttams.auth.dependencies
        vasttams.auth.dependencies._auth_manager = None
        
        mock_store = Mock()
        manager1 = get_auth_manager(mock_store)
        manager2 = get_auth_manager(mock_store)
        
        assert manager1 is manager2
        assert isinstance(manager1, AuthManager)
    
    def test_get_auth_manager_initializes_providers(self):
        """Test get_auth_manager initializes providers"""
        # Clear global instance
        import vasttams.auth.dependencies
        vasttams.auth.dependencies._auth_manager = None
        
        mock_store = Mock()
        manager = get_auth_manager(mock_store)
        
        assert len(manager.providers) > 0
        # Should have JWT, Basic, and URL Token providers
        provider_methods = [p.get_method().value for p in manager.providers]
        assert "bearer" in provider_methods
        assert "basic" in provider_methods
        assert "url_token" in provider_methods

