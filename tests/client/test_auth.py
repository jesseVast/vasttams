"""
Tests for TokenManager authentication.
"""

import pytest
import aiohttp
from unittest.mock import AsyncMock, MagicMock, patch
from vasttamsclient.auth import TokenManager
from vasttamsclient.exceptions import TAMSAuthenticationError, TAMSConnectionError


class TestTokenManager:
    """Tests for TokenManager."""
    
    @pytest.fixture
    def token_manager(self):
        """Create a TokenManager instance."""
        return TokenManager(
            server_url="http://localhost:8000",
            username="testuser",
            password="testpass"
        )
    
    def test_init(self, token_manager):
        """Test TokenManager initialization."""
        assert token_manager.server_url == "http://localhost:8000"
        assert token_manager.username == "testuser"
        assert token_manager.password == "testpass"
        assert token_manager._token is None
    
    def test_init_strips_trailing_slash(self):
        """Test that server_url trailing slash is stripped."""
        manager = TokenManager("http://localhost:8000/", "user", "pass")
        assert manager.server_url == "http://localhost:8000"
    
    @pytest.mark.asyncio
    async def test_login_success(self, token_manager):
        """Test successful login."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"access_token": "test-token-123"})
        
        mock_session = AsyncMock()
        mock_session.post = AsyncMock()
        mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            token = await token_manager.login()
            assert token == "test-token-123"
            assert token_manager._token == "test-token-123"
    
    @pytest.mark.asyncio
    async def test_login_401_error(self, token_manager):
        """Test login with 401 error."""
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Invalid credentials")
        
        mock_session = AsyncMock()
        mock_session.post = AsyncMock()
        mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with pytest.raises(TAMSAuthenticationError) as exc_info:
                await token_manager.login()
            assert "Authentication failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_login_no_token_in_response(self, token_manager):
        """Test login when response doesn't contain access_token."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={})  # No access_token
        
        mock_session = AsyncMock()
        mock_session.post = AsyncMock()
        mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with pytest.raises(TAMSAuthenticationError) as exc_info:
                await token_manager.login()
            assert "No access token" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_login_connection_error(self, token_manager):
        """Test login with connection error."""
        mock_session = AsyncMock()
        mock_session.post = AsyncMock(side_effect=aiohttp.ClientError("Connection failed"))
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with pytest.raises(TAMSConnectionError) as exc_info:
                await token_manager.login()
            assert "Connection error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_token_caches_token(self, token_manager):
        """Test that get_token caches the token."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"access_token": "cached-token"})
        
        mock_session = AsyncMock()
        mock_session.post = AsyncMock()
        mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # First call should login
            token1 = await token_manager.get_token()
            assert token1 == "cached-token"
            
            # Second call should use cached token (no new login)
            token2 = await token_manager.get_token()
            assert token2 == "cached-token"
            # Verify login was only called once
            assert mock_session.post.call_count == 1
    
    @pytest.mark.asyncio
    async def test_refresh_token(self, token_manager):
        """Test token refresh."""
        # Set initial token
        token_manager._token = "old-token"
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"access_token": "new-token"})
        
        mock_session = AsyncMock()
        mock_session.post = AsyncMock()
        mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            token = await token_manager.refresh_token()
            assert token == "new-token"
            assert token_manager._token == "new-token"
    
    def test_clear_token(self, token_manager):
        """Test clearing token."""
        token_manager._token = "some-token"
        token_manager.clear_token()
        assert token_manager._token is None

