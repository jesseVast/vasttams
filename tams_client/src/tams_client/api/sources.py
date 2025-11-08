"""
Source API methods.

Low-level API calls for source operations.
"""

from typing import Dict, Any, List, Optional
import aiohttp
from ..exceptions import TAMSAPIError, TAMSConnectionError


async def create_source(client, source_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a source."""
    url = f"{client.server_url}/sources"
    headers = await client._get_headers()
    async with client._session.post(url, json=source_data, headers=headers) as response:
        if response.status == 201:
            return await response.json()
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to create source: {error_text}", response.status, error_text)


async def get_source(client, source_id: str) -> Optional[Dict[str, Any]]:
    """Get a source by ID."""
    url = f"{client.server_url}/sources/{source_id}"
    headers = await client._get_headers()
    async with client._session.get(url, headers=headers) as response:
        if response.status == 200:
            return await response.json()
        elif response.status == 404:
            return None
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to get source: {error_text}", response.status, error_text)


async def update_source(client, source_id: str, source_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update a source."""
    url = f"{client.server_url}/sources/{source_id}"
    headers = await client._get_headers()
    async with client._session.put(url, json=source_data, headers=headers) as response:
        if response.status == 200:
            return await response.json()
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to update source: {error_text}", response.status, error_text)


async def delete_source(client, source_id: str) -> None:
    """Delete a source."""
    url = f"{client.server_url}/sources/{source_id}"
    headers = await client._get_headers()
    async with client._session.delete(url, headers=headers) as response:
        if response.status not in (200, 204):
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to delete source: {error_text}", response.status, error_text)


async def list_sources(client, query_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """List sources."""
    url = f"{client.server_url}/sources"
    headers = await client._get_headers()
    async with client._session.get(url, params=query_params or {}, headers=headers) as response:
        if response.status == 200:
            data = await response.json()
            return data.get("data", [])
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to list sources: {error_text}", response.status, error_text)

