"""
TAMS Authentication Module

Handles authentication and token management with automatic renewal.
"""

import asyncio
import logging
from typing import Optional
import aiohttp
from .exceptions import TAMSAuthenticationError, TAMSConnectionError

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages authentication tokens with automatic renewal."""
    
    def __init__(self, server_url: str, username: str, password: str, 
                 api_prefix: str = "/api/tams/latest", session: Optional[aiohttp.ClientSession] = None):
        """
        Initialize token manager.
        
        Args:
            server_url: TAMS server base URL
            username: Username for authentication
            password: Password for authentication
            api_prefix: API path prefix (default: "/api/tams/latest")
            session: Optional shared aiohttp session to reuse connections
        """
        self.server_url = server_url.rstrip('/')
        self.username = username
        self.password = password
        self.api_prefix = api_prefix
        self._token: Optional[str] = None
        self._lock = asyncio.Lock()
        self._session = session  # Use shared session if provided
        
    async def _do_login(self) -> str:
        """
        Internal login method without lock (assumes lock is already held).
        
        Returns:
            str: Authentication token
            
        Raises:
            TAMSAuthenticationError: If login fails
            TAMSConnectionError: If connection fails
        """
        try:
            url = f"{self.server_url}{self.api_prefix}/auth/login"
            # Use shared session if available, otherwise create temporary one
            if self._session and not self._session.closed:
                # Use shared session to reuse connections
                async with self._session.post(
                    url,
                    json={"username": self.username, "password": self.password}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self._token = data.get("access_token")
                        if not self._token:
                            raise TAMSAuthenticationError("No access token in login response")
                        logger.debug("Successfully authenticated")
                        return self._token
                    elif response.status == 401:
                        error_text = await response.text()
                        raise TAMSAuthenticationError(f"Authentication failed: {error_text}")
                    else:
                        error_text = await response.text()
                        raise TAMSAuthenticationError(f"Login failed with status {response.status}: {error_text}")
            else:
                # Fallback: create temporary session only if shared session not available
                timeout = aiohttp.ClientTimeout(total=30)
                async with aiohttp.ClientSession(timeout=timeout) as temp_session:
                    async with temp_session.post(
                        url,
                        json={"username": self.username, "password": self.password}
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            self._token = data.get("access_token")
                            if not self._token:
                                raise TAMSAuthenticationError("No access token in login response")
                            logger.debug("Successfully authenticated")
                            return self._token
                        elif response.status == 401:
                            error_text = await response.text()
                            raise TAMSAuthenticationError(f"Authentication failed: {error_text}")
                        else:
                            error_text = await response.text()
                            raise TAMSAuthenticationError(f"Login failed with status {response.status}: {error_text}")
        except aiohttp.ClientError as e:
            raise TAMSConnectionError(f"Connection error during login: {e}")
        except Exception as e:
            if isinstance(e, (TAMSAuthenticationError, TAMSConnectionError)):
                raise
            raise TAMSAuthenticationError(f"Unexpected error during login: {e}")
    
    def set_session(self, session: aiohttp.ClientSession):
        """Update the shared session (called after client session is created)."""
        self._session = session
    
    async def login(self) -> str:
        """
        Login and get authentication token.
        
        Returns:
            str: Authentication token
            
        Raises:
            TAMSAuthenticationError: If login fails
            TAMSConnectionError: If connection fails
        """
        async with self._lock:
            if self._token:
                return self._token
            return await self._do_login()
    
    async def refresh_token(self) -> str:
        """
        Refresh authentication token (re-login).
        
        Returns:
            str: New authentication token
        """
        async with self._lock:
            self._token = None
            return await self._do_login()
    
    async def get_token(self) -> str:
        """
        Get current token, logging in if necessary.
        
        Returns:
            str: Authentication token
        """
        if not self._token:
            await self.login()
        return self._token
    
    def clear_token(self):
        """Clear stored token (force re-authentication on next request)."""
        self._token = None

