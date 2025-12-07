"""
Storage Backend API methods.

Low-level API calls for storage backend operations.
"""

from typing import TYPE_CHECKING, Dict, Any, List, Optional
from ..exceptions import TAMSAPIError

if TYPE_CHECKING:
    from ..client import TAMSClient


async def list_storage_backends(client: "TAMSClient") -> List[Dict[str, Any]]:
    """List storage backends."""
    url = f"{client.server_url}{client.api_prefix}/service/storage-backends"
    response = await client._request("GET", url, headers=await client._get_headers())
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, list):
            return data
        return data.get("data", [])
    else:
        error_text = response.text
        raise TAMSAPIError(f"Failed to list storage backends: {error_text}", response.status_code, error_text)


async def get_storage_backend(client: "TAMSClient", backend_id: str) -> Optional[Dict[str, Any]]:
    """Get a storage backend by ID."""
    url = f"{client.server_url}{client.api_prefix}/service/storage-backends/{backend_id}"
    response = await client._request("GET", url, headers=await client._get_headers())
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        return None
    else:
        error_text = response.text
        raise TAMSAPIError(f"Failed to get storage backend: {error_text}", response.status_code, error_text)


async def create_storage_backend(client: "TAMSClient", backend_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a storage backend."""
    url = f"{client.server_url}{client.api_prefix}/service/storage-backends"
    response = await client._request("POST", url, json=backend_data, headers=await client._get_headers())
    if response.status_code == 201:
        return response.json()
    else:
        error_text = response.text
        raise TAMSAPIError(f"Failed to create storage backend: {error_text}", response.status_code, error_text)


async def update_storage_backend(client: "TAMSClient", backend_id: str, backend_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update a storage backend."""
    url = f"{client.server_url}{client.api_prefix}/service/storage-backends/{backend_id}"
    response = await client._request("PUT", url, json=backend_data, headers=await client._get_headers())
    if response.status_code == 200:
        return response.json()
    else:
        error_text = response.text
        raise TAMSAPIError(f"Failed to update storage backend: {error_text}", response.status_code, error_text)


async def delete_storage_backend(client: "TAMSClient", backend_id: str) -> None:
    """Delete a storage backend."""
    url = f"{client.server_url}{client.api_prefix}/service/storage-backends/{backend_id}"
    response = await client._request("DELETE", url, headers=await client._get_headers())
    if response.status_code not in (200, 204):
        error_text = response.text
        raise TAMSAPIError(f"Failed to delete storage backend: {error_text}", response.status_code, error_text)

