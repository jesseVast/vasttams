"""
Storage Backend API methods.

Low-level API calls for storage backend operations.
"""

from typing import Dict, Any, List, Optional
from ..exceptions import TAMSAPIError


async def list_storage_backends(client) -> List[Dict[str, Any]]:
    """List storage backends."""
    url = f"{client.server_url}/service/storage-backends"
    async with client._session.get(url, headers=await client._get_headers()) as response:
        if response.status == 200:
            data = await response.json()
            # Handle both list and dict with 'data' key
            if isinstance(data, list):
                return data
            return data.get("data", [])
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to list storage backends: {error_text}", response.status, error_text)


async def get_storage_backend(client, backend_id: str) -> Optional[Dict[str, Any]]:
    """Get a storage backend by ID."""
    url = f"{client.server_url}/service/storage-backends/{backend_id}"
    async with client._session.get(url, headers=await client._get_headers()) as response:
        if response.status == 200:
            return await response.json()
        elif response.status == 404:
            return None
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to get storage backend: {error_text}", response.status, error_text)


async def create_storage_backend(client, backend_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a storage backend."""
    url = f"{client.server_url}/service/storage-backends"
    async with client._session.post(url, json=backend_data, headers=await client._get_headers()) as response:
        if response.status == 201:
            return await response.json()
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to create storage backend: {error_text}", response.status, error_text)


async def update_storage_backend(client, backend_id: str, backend_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update a storage backend."""
    url = f"{client.server_url}/service/storage-backends/{backend_id}"
    async with client._session.put(url, json=backend_data, headers=await client._get_headers()) as response:
        if response.status == 200:
            return await response.json()
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to update storage backend: {error_text}", response.status, error_text)


async def delete_storage_backend(client, backend_id: str) -> None:
    """Delete a storage backend."""
    url = f"{client.server_url}/service/storage-backends/{backend_id}"
    async with client._session.delete(url, headers=await client._get_headers()) as response:
        if response.status not in (200, 204):
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to delete storage backend: {error_text}", response.status, error_text)

