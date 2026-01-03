"""
TAMS Client

Main client class for interacting with TAMS servers.
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any, List, Union, Coroutine, cast
from pathlib import Path
import httpx
from .auth import TokenManager
from .exceptions import TAMSAuthenticationError, TAMSAPIError, TAMSConnectionError
from .domain.source import TAMSSource
from .domain.flow import TAMSFlow
from .domain.deletion_request import TAMSDeletionRequest
from .transport import HttpxTransport

logger = logging.getLogger(__name__)


class TAMSClient:
    """Main TAMS client class."""
    
    def __init__(self, server_url: str, username: str, password: str, 
                 timeout: int = 60, verify_ssl: bool = True,
                 limit: int = 100, limit_per_host: int = 30,
                 keepalive_timeout: int = 60, api_version: Optional[str] = None,
                 transport: Optional[HttpxTransport] = None):
        """
        Initialize TAMS client.
        
        Args:
            server_url: TAMS server base URL (e.g., "http://localhost:8000")
            username: Username for authentication
            password: Password for authentication
            timeout: Request timeout in seconds (default: 60)
            verify_ssl: Verify SSL certificates
            limit: Total connection pool size (default: 100)
            limit_per_host: Max connections per host (default: 30)
            keepalive_timeout: Keep-alive timeout in seconds (default: 60)
            api_version: API version to use (e.g., "v8.0", "v7.0"). 
                        If None, uses "/api/tams/latest" (default: None)
            transport: Optional HttpxTransport to inject (default creates one)
        """
        # Normalize server URL: add http:// if no protocol is specified
        server_url = server_url.strip()
        if not server_url.startswith(('http://', 'https://')):
            server_url = f"http://{server_url}"
            logger.debug(f"Added http:// protocol to server URL: {server_url}")
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
        
        self._transport = transport or HttpxTransport(
            timeout=timeout,
            verify_ssl=verify_ssl,
            limit=limit,
            limit_per_host=limit_per_host,
            keepalive_timeout=keepalive_timeout,
        )
        self._token_manager = TokenManager(
            server_url,
            username,
            password,
            api_prefix=self.api_prefix,
            requester=self._transport.request,
        )
        self._closed = False
        
        # Domain object cache: {type: {id: object}}
        self._cache: Dict[str, Dict[str, Any]] = {
            "source": {},
            "flow": {}
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication token."""
        token = await self._token_manager.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    
    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """
        Make HTTP request with automatic token refresh on 401.
        
        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request arguments
            
        Returns:
            ClientResponse: Response object
        """
        headers = await self._get_headers()
        headers.update(kwargs.pop("headers", {}))
        
        try:
            response = await self._transport.request(method, url, headers=headers, **kwargs)
            if response.status_code == 401:
                # Token expired, refresh and retry once
                logger.debug("Token expired, refreshing...")
                await self._token_manager.refresh_token()
                headers = await self._get_headers()
                headers.update(kwargs.pop("headers", {}))
                response = await self._transport.request(method, url, headers=headers, **kwargs)
                if response.status_code == 401:
                    raise TAMSAuthenticationError("Authentication failed after token refresh")
            return response
        except httpx.HTTPError as e:
            # Safely format httpx errors to avoid type concatenation issues
            try:
                error_msg = str(e)
            except Exception:
                error_msg = f"<unprintable httpx error of type {type(e).__name__}>"
            raise TAMSConnectionError(f"Connection error: {error_msg}") from e
    
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
    
    async def close(self, wait_timeout: float = 10.0):
        """
        Close HTTP transport, waiting briefly for pending operations.
        """
        try:
            await asyncio.wait_for(self._transport.close(), timeout=wait_timeout)
        except asyncio.TimeoutError:
            logger.warning(
                f"Timeout ({wait_timeout}s) closing transport."
            )
        except Exception as e:
            logger.warning(f"Error during transport close: {e}", exc_info=True)
        
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

    def _execute_coroutine_sync(self, coroutine):
        """
        Execute a coroutine synchronously and return the result.
        Handles both cases: existing event loop and no event loop.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Can't run synchronously in async context - this should be handled by caller
                raise RuntimeError("Cannot execute coroutine synchronously in running event loop")
            else:
                # In sync context with event loop, run synchronously
                logger.debug("Running coroutine synchronously in existing loop")
                return loop.run_until_complete(coroutine)
        except RuntimeError:
            # No event loop or event loop is closed, create new one
            # Use new_event_loop() instead of asyncio.run() to avoid conflicts with pytest-asyncio
            logger.debug("Creating new event loop for synchronous execution")
            new_loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(new_loop)
                return new_loop.run_until_complete(coroutine)
            finally:
                new_loop.close()
                # Restore previous loop if it existed
                try:
                    asyncio.set_event_loop(None)
                except RuntimeError:
                    pass

    def _run_in_proper_context(self, coroutine):
        """
        Run a coroutine in the appropriate context.
        Returns either the result or the coroutine based on context.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In async context, return coroutine to be awaited by caller
                logger.debug("Returning coroutine for async context")
                return coroutine
            else:
                # In sync context, execute synchronously
                return self._execute_coroutine_sync(coroutine)
        except RuntimeError:
            # No event loop, execute synchronously
            return self._execute_coroutine_sync(coroutine)

    def _run_synchronously(self, coroutine):
        """
        Always run a coroutine synchronously and return the result.
        Works in both sync and async contexts.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In async context, we can't run synchronously in the same thread,
                # so we run it in a separate thread with its own event loop.
                import threading

                result = [None]
                exception: List[Optional[Exception]] = [None]

                def run_in_thread():
                    try:
                        # Create new event loop in this thread
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        result[0] = new_loop.run_until_complete(coroutine)
                    except Exception as e:
                        exception[0] = cast(Exception, e)
                    finally:
                        new_loop.close()

                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join()

                if exception[0]:
                    raise exception[0]
                return result[0]
            else:
                # In sync context, execute synchronously
                return self._execute_coroutine_sync(coroutine)
        except RuntimeError:
            # No event loop, execute synchronously
            return self._execute_coroutine_sync(coroutine)
    
    # Query methods for retrieving existing objects
    async def get_source_async(self, source_id: str, use_cache: bool = True) -> Optional["TAMSSource"]:
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
    
    async def get_flow_async(self, flow_id: str, use_cache: bool = True) -> Optional["TAMSFlow"]:
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
    
    async def list_sources_async(self, **query_params) -> List["TAMSSource"]:
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
    
    async def list_flows_async(self, **query_params) -> List["TAMSFlow"]:
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
    
    async def get_deletion_request_async(self, request_id: str) -> Optional["TAMSDeletionRequest"]:
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
    
    async def list_deletion_requests_async(self) -> List[TAMSDeletionRequest]:
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
    async def list_sources_by_tag_async(self, tag_name: str, tag_value: Optional[str] = None,
                                  tag_exists: bool = False) -> List["TAMSSource"]:
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
        return await self.list_sources_async(**query_params)
    
    async def list_flows_by_tag_async(self, tag_name: str, tag_value: Optional[str] = None,
                               tag_exists: bool = False) -> List["TAMSFlow"]:
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
        return await self.list_flows_async(**query_params)
    
    # Sync wrappers
    def get_source(self, source_id: str) -> Union[Coroutine[Any, Any, Optional["TAMSSource"]], Optional["TAMSSource"]]:
        """Synchronous wrapper for get_source_async."""
        return self._run_in_proper_context(self.get_source_async(source_id))

    def get_flow(self, flow_id: str) -> Union[Coroutine[Any, Any, Optional["TAMSFlow"]], Optional["TAMSFlow"]]:
        """Synchronous wrapper for get_flow_async."""
        return self._run_in_proper_context(self.get_flow_async(flow_id))
    
    def list_sources(self, **query_params) -> Union[Coroutine[Any, Any, List["TAMSSource"]], List["TAMSSource"]]:
        """Synchronous wrapper for list_sources_async."""
        return self._run_in_proper_context(self.list_sources_async(**query_params))
    
    def list_flows(self, **query_params) -> Union[Coroutine[Any, Any, List["TAMSFlow"]], List["TAMSFlow"]]:
        """Synchronous wrapper for list_flows_async."""
        return self._run_in_proper_context(self.list_flows_async(**query_params))
    
    async def export_source_tree_async(self, source: Union[str, "TAMSSource"],
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
            source_obj = await self.get_source_async(source)
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
    
    def export_source_tree(self, source: Union[str, "TAMSSource"],
                                output_file: Optional[str] = None,
                                indent: int = 2) -> Union[Coroutine[Any, Any, Dict[str, Any]], Dict[str, Any]]:
        """Synchronous wrapper for export_source_tree_async."""
        return self._run_in_proper_context(self.export_source_tree_async(source, output_file, indent))

    # Vector operations (VAST extensions)
    async def search_vectors_async(self, vector: List[float], limit: int = 10,
                            distance_metric: str = "L2",
                            distance_threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Search for objects by vector similarity.
        
        Args:
            vector: Query vector (list of floats)
            limit: Maximum number of results
            distance_metric: Distance metric ("L2", "COSINE", "IP")
            distance_threshold: Optional threshold for distance
            
        Returns:
            List of search results with object_id, distance, and metadata
        """
        from .api import vectors as vector_api
        return await vector_api.search_vectors(self, vector, limit, distance_metric, distance_threshold)

    async def update_object_vector_async(self, object_id: str, vector: List[float],
                                  summary: Optional[str] = None,
                                  embedding_model: Optional[str] = None) -> Dict[str, Any]:
        """
        Update or set vector for an object.
        
        Args:
            object_id: Object ID
            vector: Vector embedding (list of floats)
            summary: Optional text summary
            embedding_model: Optional model name
            
        Returns:
            Response dictionary
        """
        from .api import vectors as vector_api
        return await vector_api.update_object_vector(self, object_id, vector, summary, embedding_model)

    async def get_object_vector_async(self, object_id: str) -> Optional[Dict[str, Any]]:
        """
        Get vector data for an object.
        
        Args:
            object_id: Object ID
            
        Returns:
            Vector data dict or None if not found
        """
        from .api import vectors as vector_api
        return await vector_api.get_object_vector(self, object_id)

    async def delete_object_vector_async(self, object_id: str) -> bool:
        """
        Delete vector data for an object.
        
        Args:
            object_id: Object ID
            
        Returns:
            True if deleted, False if not found
        """
        from .api import vectors as vector_api
        return await vector_api.delete_object_vector(self, object_id)

    # Sync wrappers for vector operations
    def search_vectors(self, vector: List[float], limit: int = 10,
                           distance_metric: str = "L2",
                           distance_threshold: Optional[float] = None) -> Union[Coroutine[Any, Any, List[Dict[str, Any]]], List[Dict[str, Any]]]:
        """Synchronous wrapper for search_vectors_async."""
        return self._run_in_proper_context(self.search_vectors_async(vector, limit, distance_metric, distance_threshold))
    
    def update_object_vector(self, object_id: str, vector: List[float],
                                  summary: Optional[str] = None,
                                  embedding_model: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for update_object_vector_async."""
        result = self._run_synchronously(self.update_object_vector_async(object_id, vector, summary, embedding_model))
        if result is None or not isinstance(result, dict):
            return None
        return result

    def get_object_vector(self, object_id: str) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for get_object_vector_async."""
        result = self._run_synchronously(self.get_object_vector_async(object_id))
        if result is None or not isinstance(result, dict):
            return None
        return result
    
    def delete_object_vector(self, object_id: str) -> bool:
        """Synchronous wrapper for delete_object_vector_async."""
        result= self._run_synchronously(self.delete_object_vector_async(object_id))
        if result is None or not isinstance(result, bool):
            return False
        return result
