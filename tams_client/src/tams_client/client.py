"""
TAMS Client

Main client class for interacting with TAMS servers.
"""

import asyncio
import logging
import aiohttp
from typing import Optional, Dict, Any, List
from .auth import TokenManager
from .exceptions import TAMSAuthenticationError, TAMSAPIError, TAMSConnectionError
from .domain.source import TAMSSource
from .domain.flow import TAMSFlow

logger = logging.getLogger(__name__)


class TAMSClient:
    """Main TAMS client class."""
    
    def __init__(self, server_url: str, username: str, password: str, 
                 timeout: int = 30, verify_ssl: bool = True):
        """
        Initialize TAMS client.
        
        Args:
            server_url: TAMS server base URL (e.g., "http://localhost:8000")
            username: Username for authentication
            password: Password for authentication
            timeout: Request timeout in seconds
            verify_ssl: Verify SSL certificates
        """
        self.server_url = server_url.rstrip('/')
        self.username = username
        self.password = password
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        
        self._token_manager = TokenManager(server_url, username, password)
        self._session: Optional[aiohttp.ClientSession] = None
        self._closed = False
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure HTTP session is created."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            connector = aiohttp.TCPConnector(ssl=self.verify_ssl)
            self._session = aiohttp.ClientSession(timeout=timeout, connector=connector)
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication token."""
        await self._ensure_session()
        token = await self._token_manager.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    async def _request(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        """
        Make HTTP request with automatic token refresh on 401.
        
        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request arguments
            
        Returns:
            ClientResponse: Response object
        """
        await self._ensure_session()
        headers = await self._get_headers()
        headers.update(kwargs.pop("headers", {}))
        
        try:
            async with self._session.request(method, url, headers=headers, **kwargs) as response:
                if response.status == 401:
                    # Token expired, refresh and retry once
                    logger.debug("Token expired, refreshing...")
                    await self._token_manager.refresh_token()
                    headers = await self._get_headers()
                    headers.update(kwargs.pop("headers", {}))
                    async with self._session.request(method, url, headers=headers, **kwargs) as response:
                        if response.status == 401:
                            raise TAMSAuthenticationError("Authentication failed after token refresh")
                        return response
                return response
        except aiohttp.ClientError as e:
            raise TAMSConnectionError(f"Connection error: {e}")
    
    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
        self._closed = True
    
    # Factory methods for creating new objects
    def TAMSSource(self, format: str, label: Optional[str] = None, **source_data) -> TAMSSource:
        """
        Create a new source.
        
        Args:
            format: Source format URN
            label: Optional source label
            **source_data: Additional source data
            
        Returns:
            TAMSSource: New source instance
        """
        source_data.update({"format": format, "label": label})
        return TAMSSource(self, **source_data)
    
    def TAMSFlow(self, source_id: str, format: str, codec: str, 
                 label: Optional[str] = None, **flow_data) -> TAMSFlow:
        """
        Create a new flow.
        
        Args:
            source_id: Source ID
            format: Flow format URN
            codec: Flow codec MIME type
            label: Optional flow label
            **flow_data: Additional flow data
            
        Returns:
            TAMSFlow: New flow instance
        """
        flow_data.update({
            "source_id": source_id,
            "format": format,
            "codec": codec,
            "label": label
        })
        return TAMSFlow(self, **flow_data)
    
    # Query methods for retrieving existing objects
    async def get_source(self, source_id: str) -> Optional[TAMSSource]:
        """Get a source by ID."""
        from .api import sources as source_api
        source_data = await source_api.get_source(self, source_id)
        if source_data:
            return TAMSSource(self, id=source_id, **source_data)
        return None
    
    async def get_flow(self, flow_id: str) -> Optional[TAMSFlow]:
        """Get a flow by ID."""
        from .api import flows as flow_api
        flow_data = await flow_api.get_flow(self, flow_id)
        if flow_data:
            return TAMSFlow(self, id=flow_id, **flow_data)
        return None
    
    async def list_sources(self, **query_params) -> List[TAMSSource]:
        """List sources."""
        from .api import sources as source_api
        sources_data = await source_api.list_sources(self, query_params)
        return [TAMSSource(self, id=s["id"], **s) for s in sources_data]
    
    async def list_flows(self, **query_params) -> List[TAMSFlow]:
        """List flows."""
        from .api import flows as flow_api
        flows_data = await flow_api.list_flows(self, query_params)
        return [TAMSFlow(self, id=f["id"], **f) for f in flows_data]
    
    # Sync wrappers
    def get_source_sync(self, source_id: str) -> Optional[TAMSSource]:
        """Synchronous wrapper for get_source."""
        return asyncio.run(self.get_source(source_id))
    
    def get_flow_sync(self, flow_id: str) -> Optional[TAMSFlow]:
        """Synchronous wrapper for get_flow."""
        return asyncio.run(self.get_flow(flow_id))
    
    def list_sources_sync(self, **query_params) -> List[TAMSSource]:
        """Synchronous wrapper for list_sources."""
        return asyncio.run(self.list_sources(**query_params))
    
    def list_flows_sync(self, **query_params) -> List[TAMSFlow]:
        """Synchronous wrapper for list_flows."""
        return asyncio.run(self.list_flows(**query_params))

