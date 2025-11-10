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
    url = f"{client.server_url}/objects/{object_id}"
    async with client._session.get(url, headers=await client._get_headers()) as response:
        if response.status == 200:
            return await response.json()
        elif response.status == 404:
            return None
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to get object: {error_text}", response.status, error_text)


async def list_objects(client: "TAMSClient", query_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """List objects."""
    url = f"{client.server_url}/objects"
    async with client._session.get(url, params=query_params or {}, headers=await client._get_headers()) as response:
        if response.status == 200:
            data = await response.json()
            return data.get("data", [])
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to list objects: {error_text}", response.status, error_text)

