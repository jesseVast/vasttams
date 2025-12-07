"""
Object API methods.

Low-level API calls for object operations.
"""

from typing import TYPE_CHECKING, Dict, Any, List, Optional
from ..exceptions import TAMSAPIError

if TYPE_CHECKING:
    from ..client import TAMSClient


async def get_object(client: "TAMSClient", object_id: str) -> Optional[Dict[str, Any]]:
    """Get an object by ID."""
    url = f"{client.server_url}{client.api_prefix}/objects/{object_id}"
    response = await client._request("GET", url, headers=await client._get_headers())
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        return None
    else:
        error_text = response.text
        raise TAMSAPIError(f"Failed to get object: {error_text}", response.status_code, error_text)


async def list_objects(client: "TAMSClient", query_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """List objects."""
    url = f"{client.server_url}{client.api_prefix}/objects"
    response = await client._request("GET", url, params=query_params or {}, headers=await client._get_headers())
    if response.status_code == 200:
        data = response.json()
        return data.get("data", []) if isinstance(data, dict) else data
    else:
        error_text = response.text
        raise TAMSAPIError(f"Failed to list objects: {error_text}", response.status_code, error_text)

