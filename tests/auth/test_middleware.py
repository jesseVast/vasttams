#!/usr/bin/env python3
"""
Tests for Authentication Middleware

Tests auth middleware functionality.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request, HTTPException

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.auth.middleware import AuthMiddleware, get_current_user_session, require_authentication
from vasttams.auth.core import AuthManager
from vasttams.auth.models import AuthResult, UserSession, UserRole, AuthMethod
from datetime import datetime, timezone


class TestAuthMiddleware:
    """Test AuthMiddleware"""
    
    def test_init(self):
        """Test AuthMiddleware initialization"""
        mock_manager = Mock(spec=AuthManager)
        middleware = AuthMiddleware(mock_manager, require_auth=False)
        
        assert middleware.auth_manager == mock_manager
        assert middleware.require_auth is False
    
    def test_init_require_auth(self):
        """Test AuthMiddleware with require_auth=True"""
        mock_manager = Mock(spec=AuthManager)
        middleware = AuthMiddleware(mock_manager, require_auth=True)
        
        assert middleware.require_auth is True
    
    def test_should_skip_auth(self):
        """Test _should_skip_auth"""
        mock_manager = Mock(spec=AuthManager)
        middleware = AuthMiddleware(mock_manager)
        
        assert middleware._should_skip_auth("/docs") is True
        assert middleware._should_skip_auth("/redoc") is True
        assert middleware._should_skip_auth("/openapi.json") is True
        assert middleware._should_skip_auth("/health") is True
        assert middleware._should_skip_auth("/metrics") is True
        assert middleware._should_skip_auth("/auth/test") is True
        assert middleware._should_skip_auth("/sources") is False
    
    @pytest.mark.asyncio
    async def test_call_skip_auth_path(self):
        """Test middleware skips auth for certain paths"""
        mock_manager = Mock(spec=AuthManager)
        middleware = AuthMiddleware(mock_manager, require_auth=True)
        
        mock_request = Mock()
        mock_request.url.path = "/health"
        mock_request.state = Mock()
        
        mock_response = Mock()
        mock_call_next = AsyncMock(return_value=mock_response)
        
        result = await middleware(mock_request, mock_call_next)
        
        assert result == mock_response
        mock_call_next.assert_called_once()
        # Should not have called authenticate
        assert not hasattr(mock_manager, 'authenticate') or not mock_manager.authenticate.called
    
    @pytest.mark.asyncio
    async def test_call_auth_success(self):
        """Test middleware with successful authentication"""
        mock_manager = Mock(spec=AuthManager)
        mock_manager.authenticate = AsyncMock(return_value=AuthResult(
            success=True,
            user_id="user1",
            username="testuser",
            role=UserRole.VIEWER,
            auth_method=AuthMethod.BEARER
        ))
        
        middleware = AuthMiddleware(mock_manager, require_auth=False)
        
        mock_request = Mock()
        mock_request.url.path = "/sources"
        mock_request.state = Mock()
        
        mock_response = Mock()
        mock_call_next = AsyncMock(return_value=mock_response)
        
        result = await middleware(mock_request, mock_call_next)
        
        assert result == mock_response
        assert mock_request.state.user_session is not None
        assert mock_request.state.user_session.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_call_auth_failure_require_auth(self):
        """Test middleware raises exception when auth fails and require_auth=True"""
        mock_manager = Mock(spec=AuthManager)
        mock_manager.authenticate = AsyncMock(return_value=AuthResult(
            success=False,
            error="Authentication failed"
        ))
        
        middleware = AuthMiddleware(mock_manager, require_auth=True)
        
        mock_request = Mock()
        mock_request.url.path = "/sources"
        mock_request.state = Mock()
        
        mock_call_next = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await middleware(mock_request, mock_call_next)
        
        assert exc_info.value.status_code == 401
        assert "Authentication failed" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_call_auth_failure_no_require_auth(self):
        """Test middleware continues without auth when require_auth=False"""
        mock_manager = Mock(spec=AuthManager)
        mock_manager.authenticate = AsyncMock(return_value=AuthResult(
            success=False,
            error="Authentication failed"
        ))
        
        middleware = AuthMiddleware(mock_manager, require_auth=False)
        
        mock_request = Mock()
        mock_request.url.path = "/sources"
        mock_request.state = Mock()
        
        mock_response = Mock()
        mock_call_next = AsyncMock(return_value=mock_response)
        
        result = await middleware(mock_request, mock_call_next)
        
        assert result == mock_response
        assert mock_request.state.user_session is None


class TestMiddlewareFunctions:
    """Test middleware helper functions"""
    
    @pytest.mark.asyncio
    async def test_get_current_user_session_with_session(self):
        """Test get_current_user_session when session exists"""
        mock_request = Mock()
        user_session = UserSession(
            user_id="user1",
            username="testuser",
            role=UserRole.VIEWER,
            auth_method=AuthMethod.BEARER,
            created_at=datetime.now(timezone.utc)
        )
        mock_request.state.user_session = user_session
        
        result = await get_current_user_session(mock_request)
        
        assert result == user_session
    
    @pytest.mark.asyncio
    async def test_get_current_user_session_no_session(self):
        """Test get_current_user_session when no session exists"""
        mock_request = Mock()
        mock_request.state = Mock()
        mock_request.state.user_session = None
        
        result = await get_current_user_session(mock_request)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_require_authentication_success(self):
        """Test require_authentication with valid session"""
        user_session = UserSession(
            user_id="user1",
            username="testuser",
            role=UserRole.VIEWER,
            auth_method=AuthMethod.BEARER,
            created_at=datetime.now(timezone.utc)
        )
        
        result = await require_authentication(user_session)
        
        assert result == user_session
    
    @pytest.mark.asyncio
    async def test_require_authentication_no_session(self):
        """Test require_authentication raises exception when no session"""
        with pytest.raises(HTTPException) as exc_info:
            await require_authentication(None)
        
        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail

