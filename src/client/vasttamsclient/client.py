"""
TAMS Client

Main client class for interacting with TAMS servers.
"""

import asyncio
import json
import logging
import aiohttp
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
from .auth import TokenManager
from .exceptions import TAMSAuthenticationError, TAMSAPIError, TAMSConnectionError
from .domain.source import TAMSSource
from .domain.flow import TAMSFlow
from .domain.deletion_request import TAMSDeletionRequest

logger = logging.getLogger(__name__)


class TAMSClient:
    """Main TAMS client class."""
    
    def __init__(self, server_url: str, username: str, password: str, 
                 timeout: int = 30, verify_ssl: bool = True,
                 limit: int = 100, limit_per_host: int = 30,
                 keepalive_timeout: int = 30, api_version: Optional[str] = None):
        """
        Initialize TAMS client.
        
        Args:
            server_url: TAMS server base URL (e.g., "http://localhost:8000")
            username: Username for authentication
            password: Password for authentication
            timeout: Request timeout in seconds
            verify_ssl: Verify SSL certificates
            limit: Total connection pool size (default: 100)
            limit_per_host: Max connections per host (default: 30)
            keepalive_timeout: Keep-alive timeout in seconds (default: 30)
            api_version: API version to use (e.g., "v8.0", "v7.0"). 
                        If None, uses "/api/tams/latest" (default: None)
        """
        self.server_url = server_url.rstrip('/')
        self.username = username
        self.password = password
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.limit = limit
        self.limit_per_host = limit_per_host
        self.keepalive_timeout = keepalive_timeout
        
        # Set API path prefix based on version
        if api_version:
            self.api_prefix = f"/api/tams/{api_version}"
        else:
            self.api_prefix = "/api/tams/latest"
        
        self._token_manager = TokenManager(server_url, username, password, api_prefix=self.api_prefix)
        self._session: Optional[aiohttp.ClientSession] = None
        self._closed = False
        
        # Domain object cache: {type: {id: object}}
        self._cache: Dict[str, Dict[str, Any]] = {
            "source": {},
            "flow": {}
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure HTTP session is created with connection pooling."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            # Configure connection pooling for parallel uploads
            connector = aiohttp.TCPConnector(
                ssl=self.verify_ssl,
                limit=self.limit,  # Total connection pool size
                limit_per_host=self.limit_per_host,  # Max connections per host
                keepalive_timeout=self.keepalive_timeout,  # Keep connections alive
                ttl_dns_cache=300,  # DNS cache TTL (5 minutes)
                use_dns_cache=True,  # Enable DNS caching
                force_close=False  # Reuse connections
            )
            self._session = aiohttp.ClientSession(timeout=timeout, connector=connector)
            # Update token manager to use shared session for connection reuse
            self._token_manager.set_session(self._session)
    
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
    
    def clear_cache(self, object_type: Optional[str] = None, object_id: Optional[str] = None):
        """
        Clear domain object cache.
        
        Args:
            object_type: Type of object to clear ("source", "flow", or None for all)
            object_id: Specific object ID to clear (or None for all of type)
        """
        if object_type is None:
            # Clear all caches
            self._cache["source"].clear()
            self._cache["flow"].clear()
        elif object_type in self._cache:
            if object_id is None:
                # Clear all of this type
                self._cache[object_type].clear()
            else:
                # Clear specific object
                self._cache[object_type].pop(object_id, None)
    
    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            # Wait a brief moment to ensure any pending operations complete
            # This helps avoid "Unclosed client session" warnings
            await asyncio.sleep(0.1)
            await self._session.close()
            # Wait for connector to close all connections
            if self._session.connector:
                await self._session.connector.close()
        # Clear cache on close
        self.clear_cache()
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
    async def get_source(self, source_id: str, use_cache: bool = True) -> Optional[TAMSSource]:
        """
        Get a source by ID.
        
        Args:
            source_id: Source ID
            use_cache: If True, return cached object if available
            
        Returns:
            TAMSSource or None if not found
        """
        # Check cache first
        if use_cache and source_id in self._cache["source"]:
            return self._cache["source"][source_id]
        
        from .api import sources as source_api
        source_data = await source_api.get_source(self, source_id)
        if source_data:
            source = TAMSSource(self, **source_data)
            # Cache the object
            self._cache["source"][source_id] = source
            return source
        return None
    
    async def get_flow(self, flow_id: str, use_cache: bool = True) -> Optional[TAMSFlow]:
        """
        Get a flow by ID.
        
        Args:
            flow_id: Flow ID
            use_cache: If True, return cached object if available
            
        Returns:
            TAMSFlow or None if not found
        """
        # Check cache first
        if use_cache and flow_id in self._cache["flow"]:
            return self._cache["flow"][flow_id]
        
        from .api import flows as flow_api
        flow_data = await flow_api.get_flow(self, flow_id)
        if flow_data:
            # Remove id from flow_data since TAMSFlow expects it as a keyword argument when id is provided
            flow_data_copy = {k: v for k, v in flow_data.items() if k != "id"}
            flow = TAMSFlow(self, id=flow_id, **flow_data_copy)
            # Cache the object
            self._cache["flow"][flow_id] = flow
            return flow
        return None
    
    async def list_sources(self, **query_params) -> List[TAMSSource]:
        """
        List sources.
        
        Args:
            **query_params: Query parameters (e.g., tag.quality="hd", tag_exists.quality=True)
            
        Returns:
            List of TAMSSource objects
        """
        from .api import sources as source_api
        sources_data = await source_api.list_sources(self, query_params)
        result = []
        for s in sources_data:
            source_id = s.get("id")
            if source_id:
                # Use cached object if available, otherwise create new
                if source_id in self._cache["source"]:
                    result.append(self._cache["source"][source_id])
                else:
                    source = TAMSSource(self, **s)
                    self._cache["source"][source_id] = source
                    result.append(source)
        return result
    
    async def list_flows(self, **query_params) -> List[TAMSFlow]:
        """
        List flows.
        
        Args:
            **query_params: Query parameters (e.g., tag.quality="hd", tag_exists.quality=True)
            
        Returns:
            List of TAMSFlow objects
        """
        from .api import flows as flow_api
        flows_data = await flow_api.list_flows(self, query_params)
        result = []
        for f in flows_data:
            # Remove id from flow_data since TAMSFlow expects it as a keyword argument when id is provided
            flow_id = f.get("id")
            if flow_id:
                # Use cached object if available, otherwise create new
                if flow_id in self._cache["flow"]:
                    result.append(self._cache["flow"][flow_id])
                else:
                    flow_data_copy = {k: v for k, v in f.items() if k != "id"}
                    flow = TAMSFlow(self, id=flow_id, **flow_data_copy)
                    self._cache["flow"][flow_id] = flow
                    result.append(flow)
        return result
    
    async def get_deletion_request(self, request_id: str) -> Optional[TAMSDeletionRequest]:
        """
        Get a deletion request by ID.
        
        Args:
            request_id: Deletion request ID
            
        Returns:
            TAMSDeletionRequest or None if not found
        """
        from .api import deletion_requests as deletion_request_api
        deletion_request_data = await deletion_request_api.get_deletion_request(self, request_id)
        if deletion_request_data:
            return TAMSDeletionRequest(self, request_id, deletion_request_data)
        return None
    
    async def list_deletion_requests(self) -> List[TAMSDeletionRequest]:
        """
        List all active deletion requests.
        
        Returns:
            List of TAMSDeletionRequest objects
        """
        from .api import deletion_requests as deletion_request_api
        deletion_requests_data = await deletion_request_api.get_deletion_requests(self)
        result = []
        for dr in deletion_requests_data:
            request_id = dr.get("id")
            if request_id:
                result.append(TAMSDeletionRequest(self, request_id, dr))
        return result
    
    # Tag-based query helpers
    async def list_sources_by_tag(self, tag_name: str, tag_value: Optional[str] = None, 
                                  tag_exists: bool = False) -> List[TAMSSource]:
        """
        List sources filtered by tag.
        
        Args:
            tag_name: Tag name to filter on
            tag_value: Tag value(s) to match (comma-separated string for multiple values)
            tag_exists: If True, only check if tag exists (ignore value)
            
        Returns:
            List of TAMSSource objects matching the tag criteria
        """
        query_params = {}
        if tag_exists:
            query_params[f"tag_exists.{tag_name}"] = True
        elif tag_value:
            query_params[f"tag.{tag_name}"] = tag_value
        else:
            query_params[f"tag_exists.{tag_name}"] = True
        return await self.list_sources(**query_params)
    
    async def list_flows_by_tag(self, tag_name: str, tag_value: Optional[str] = None,
                               tag_exists: bool = False) -> List[TAMSFlow]:
        """
        List flows filtered by tag.
        
        Args:
            tag_name: Tag name to filter on
            tag_value: Tag value(s) to match (comma-separated string for multiple values)
            tag_exists: If True, only check if tag exists (ignore value)
            
        Returns:
            List of TAMSFlow objects matching the tag criteria
        """
        query_params = {}
        if tag_exists:
            query_params[f"tag_exists.{tag_name}"] = True
        elif tag_value:
            query_params[f"tag.{tag_name}"] = tag_value
        else:
            query_params[f"tag_exists.{tag_name}"] = True
        return await self.list_flows(**query_params)
    
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
    
    async def export_source_tree(self, source: Union[str, TAMSSource], 
                                 output_file: Optional[str] = None,
                                 indent: int = 2) -> Dict[str, Any]:
        """
        Export the complete tree structure of a source to JSON.
        
        Creates a JSON representation of:
        - Source and its properties (including tags)
        - All flows under the source (with properties and tags)
        - All segments under each flow
        - All objects referenced by each segment
        
        Args:
            source: Source ID string or TAMSSource instance
            output_file: Optional file path to save JSON. If None, prints to stdout.
            indent: JSON indentation level (default: 2)
            
        Returns:
            Dict containing the complete tree structure
            
        Example:
            # Save to file
            tree = await client.export_source_tree("source-id", "output.json")
            
            # Print to stdout
            tree = await client.export_source_tree("source-id")
        """
        from .api import objects as object_api
        
        # Get source if source_id provided
        if isinstance(source, str):
            source_obj = await self.get_source(source)
            if source_obj is None:
                raise ValueError(f"Source not found: {source}")
        else:
            source_obj = source
        
        # Build source data with tags
        source_data = source_obj._data.copy()
        try:
            source_tags = await source_obj.get_tags()
            if source_tags:
                source_data["tags"] = source_tags
        except Exception as e:
            logger.warning(f"Failed to get tags for source {source_obj.id}: {e}")
            source_data["tags"] = {}
        
        # Get all flows for this source
        flows = await source_obj.list_flows()
        flows_data = []
        
        for flow in flows:
            # Build flow data with tags
            flow_data = flow._data.copy()
            try:
                flow_tags = await flow.get_tags()
                if flow_tags:
                    flow_data["tags"] = flow_tags
            except Exception as e:
                logger.warning(f"Failed to get tags for flow {flow.id}: {e}")
                flow_data["tags"] = {}
            
            # Get all segments for this flow
            segments = await flow.list_segments()
            segments_data = []
            
            for segment in segments:
                # Build segment data
                segment_data = segment._data.copy()
                
                # Get object for this segment
                object_id = segment.object_id
                try:
                    object_data = await object_api.get_object(self, object_id)
                    if object_data:
                        segment_data["object"] = object_data
                    else:
                        segment_data["object"] = None
                        logger.warning(f"Object not found: {object_id}")
                except Exception as e:
                    logger.warning(f"Failed to get object {object_id}: {e}")
                    segment_data["object"] = None
                
                segments_data.append(segment_data)
            
            flow_data["segments"] = segments_data
            flows_data.append(flow_data)
        
        # Build complete tree structure
        tree = {
            "source": source_data,
            "flows": flows_data
        }
        
        # Output JSON
        json_str = json.dumps(tree, indent=indent, default=str)
        
        if output_file:
            # Save to file
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json_str, encoding='utf-8')
            logger.info(f"Source tree exported to {output_file}")
        else:
            # Print to stdout
            print(json_str)
        
        return tree
    
    def export_source_tree_sync(self, source: Union[str, TAMSSource],
                                output_file: Optional[str] = None,
                                indent: int = 2) -> Dict[str, Any]:
        """Synchronous wrapper for export_source_tree."""
        return asyncio.run(self.export_source_tree(source, output_file, indent))

