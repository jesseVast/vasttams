"""
Vector API methods.

Low-level API calls for vector operations.
"""

from typing import TYPE_CHECKING, Dict, Any, List, Optional, Union
from ..exceptions import TAMSAPIError

if TYPE_CHECKING:
    from ..client import TAMSClient


async def search_vectors(
    client: "TAMSClient", 
    vector: List[float], 
    limit: int = 10, 
    distance_metric: str = "L2",
    distance_threshold: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Search for objects by vector similarity.
    
    Args:
        client: TAMSClient instance
        vector: Query vector (list of floats)
        limit: Maximum number of results
        distance_metric: Distance metric ("L2", "COSINE", "IP")
        distance_threshold: Optional threshold for distance
        
    Returns:
        List of search results with object_id, distance, and metadata
    """
    # Note: Vector endpoints are under /api/vast/, not /api/tams/v8.0/
    # We need to construct the URL correctly.
    # client.server_url is like "http://localhost:8000"
    # client.api_prefix is like "/api/tams/v8.0" or "/api/tams/latest"
    # We need "/api/vast/objects/vector/search"
    
    # Construct base URL for VAST extensions
    # Assuming standard deployment, /api/vast is a sibling of /api/tams
    vast_prefix = "/api/vast"
    url = f"{client.server_url}{vast_prefix}/objects/vector/search"
    
    payload: Dict[str, Any] = {
        "vector": vector,
        "limit": limit,
        "distance_metric": distance_metric
    }
    
    if distance_threshold is not None:
        payload["distance_threshold"] = distance_threshold
        
    # Ensure session is available
    await client._ensure_session()
    if client._session is None:
        raise TAMSAPIError("Client session not available", 500, "Internal Client Error")

    async with client._session.post(url, json=payload, headers=await client._get_headers()) as response:
        if response.status == 200:
            return await response.json()
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Vector search failed: {error_text}", response.status, error_text)


async def update_object_vector(
    client: "TAMSClient", 
    object_id: str, 
    vector: List[float],
    summary: Optional[str] = None,
    embedding_model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update or set vector for an object.
    
    Args:
        client: TAMSClient instance
        object_id: Object ID
        vector: Vector embedding (list of floats)
        summary: Optional text summary
        embedding_model: Optional model name
        
    Returns:
        Response dictionary
    """
    vast_prefix = "/api/vast"
    url = f"{client.server_url}{vast_prefix}/objects/{object_id}/vector"
    
    payload: Dict[str, Any] = {
        "vector": vector
    }
    
    if summary:
        payload["summary"] = summary
    
    if embedding_model:
        payload["embedding_model"] = embedding_model
    
    # Ensure session is available
    await client._ensure_session()
    if client._session is None:
        raise TAMSAPIError("Client session not available", 500, "Internal Client Error")
        
    async with client._session.put(url, json=payload, headers=await client._get_headers()) as response:
        if response.status in (200, 201):
            return await response.json()
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to update object vector: {error_text}", response.status, error_text)


async def get_object_vector(client: "TAMSClient", object_id: str) -> Optional[Dict[str, Any]]:
    """
    Get vector data for an object.
    
    Args:
        client: TAMSClient instance
        object_id: Object ID
        
    Returns:
        Vector data dict or None if not found
    """
    vast_prefix = "/api/vast"
    url = f"{client.server_url}{vast_prefix}/objects/{object_id}/vector"
    
    # Ensure session is available
    await client._ensure_session()
    if client._session is None:
        raise TAMSAPIError("Client session not available", 500, "Internal Client Error")

    async with client._session.get(url, headers=await client._get_headers()) as response:
        if response.status == 200:
            return await response.json()
        elif response.status == 404:
            return None
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to get object vector: {error_text}", response.status, error_text)


async def delete_object_vector(client: "TAMSClient", object_id: str) -> bool:
    """
    Delete vector data for an object.
    
    Args:
        client: TAMSClient instance
        object_id: Object ID
        
    Returns:
        True if deleted, False if not found
    """
    vast_prefix = "/api/vast"
    url = f"{client.server_url}{vast_prefix}/objects/{object_id}/vector"
    
    # Ensure session is available
    await client._ensure_session()
    if client._session is None:
        raise TAMSAPIError("Client session not available", 500, "Internal Client Error")

    async with client._session.delete(url, headers=await client._get_headers()) as response:
        if response.status in (200, 204):
            return True
        elif response.status == 404:
            return False
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to delete object vector: {error_text}", response.status, error_text)

