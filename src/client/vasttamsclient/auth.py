"""
TAMS Authentication Module

Handles authentication and token management with automatic renewal.
"""

import asyncio
import logging
from typing import Optional, Callable, Awaitable
import httpx
from .exceptions import TAMSAuthenticationError, TAMSConnectionError

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages authentication tokens with automatic renewal."""
    
    def __init__(self, server_url: str, username: str, password: str, 
                 api_prefix: str = "/api/tams/latest",
                 requester: Optional[Callable[..., Awaitable[httpx.Response]]] = None):
        """
        Initialize token manager.
        
        Args:
            server_url: TAMS server base URL
            username: Username for authentication
            password: Password for authentication
            api_prefix: API path prefix (default: "/api/tams/latest")
            requester: Async callable used to perform HTTP requests (method, url, **kwargs) -> httpx.Response
        """
        # Normalize server URL: add http:// if no protocol is specified
        server_url = server_url.strip()
        if not server_url.startswith(('http://', 'https://')):
            # Default to http:// if no protocol specified
            server_url = f"http://{server_url}"
            logger.debug(f"Added http:// protocol to server URL: {server_url}")
        self.server_url = server_url.rstrip('/')
        self.username = username
        self.password = password
        self.api_prefix = api_prefix
        self._token: Optional[str] = None
        self._lock = asyncio.Lock()
        self._requester = requester
        
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
            if self._requester:
                response = await self._requester(
                    "POST",
                    url,
                    json={"username": self.username, "password": self.password},
                )
            else:
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.post(
                        url,
                        json={"username": self.username, "password": self.password},
                    )

            if response.status_code == 200:
                data = response.json()
                self._token = data.get("access_token")
                if not self._token:
                    raise TAMSAuthenticationError("No access token in login response")
                logger.debug("Successfully authenticated")
                return self._token
            elif response.status_code == 401:
                error_text = response.text
                raise TAMSAuthenticationError(f"Authentication failed: {error_text}")
            else:
                error_text = response.text
                raise TAMSAuthenticationError(f"Login failed with status {response.status_code}: {error_text}")
        except httpx.HTTPError as e:
            raise TAMSConnectionError(f"Connection error during login: {e}")
        except Exception as e:
            if isinstance(e, (TAMSAuthenticationError, TAMSConnectionError)):
                raise
            raise TAMSAuthenticationError(f"Unexpected error during login: {e}")
    
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

