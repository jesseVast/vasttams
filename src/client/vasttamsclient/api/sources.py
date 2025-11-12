"""
Source API methods.

Low-level API calls for source operations.
"""

from typing import TYPE_CHECKING, Dict, Any, List, Optional
import aiohttp
from ..exceptions import TAMSAPIError, TAMSConnectionError

if TYPE_CHECKING:
    from ..client import TAMSClient


async def create_source(client: "TAMSClient", source_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a source."""
    url = f"{client.server_url}{client.api_prefix}/sources"
    headers = await client._get_headers()
    async with client._session.post(url, json=source_data, headers=headers) as response:
        if response.status == 201:
            return await response.json()
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to create source: {error_text}", response.status, error_text)


async def get_source(client: "TAMSClient", source_id: str) -> Optional[Dict[str, Any]]:
    """Get a source by ID."""
    url = f"{client.server_url}{client.api_prefix}/sources/{source_id}"
    headers = await client._get_headers()
    async with client._session.get(url, headers=headers) as response:
        if response.status == 200:
            return await response.json()
        elif response.status == 404:
            return None
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to get source: {error_text}", response.status, error_text)


async def update_source_label(client: "TAMSClient", source_id: str, label: str) -> None:
    """Update a source label."""
    url = f"{client.server_url}{client.api_prefix}/sources/{source_id}/label"
    headers = await client._get_headers()
    headers["Content-Type"] = "text/plain"
    async with client._session.put(url, data=label, headers=headers) as response:
        if response.status not in (200, 204):
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to update source label: {error_text}", response.status, error_text)


async def update_source_description(client: "TAMSClient", source_id: str, description: str) -> None:
    """Update a source description."""
    url = f"{client.server_url}{client.api_prefix}/sources/{source_id}/description"
    headers = await client._get_headers()
    headers["Content-Type"] = "text/plain"
    async with client._session.put(url, data=description, headers=headers) as response:
        if response.status not in (200, 204):
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to update source description: {error_text}", response.status, error_text)


async def delete_source(client: "TAMSClient", source_id: str, cascade: bool = True) -> None:
    """Delete a source.
    
    Args:
        client: TAMSClient instance
        source_id: Source ID to delete
        cascade: If True, cascade delete to associated flows and segments (default: True)
    """
    url = f"{client.server_url}{client.api_prefix}/sources/{source_id}"
    params = {"cascade": str(cascade).lower()}
    headers = await client._get_headers()
    async with client._session.delete(url, params=params, headers=headers) as response:
        if response.status not in (200, 204):
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to delete source: {error_text}", response.status, error_text)


async def list_sources(client: "TAMSClient", query_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """List sources."""
    url = f"{client.server_url}{client.api_prefix}/sources"
    headers = await client._get_headers()
    async with client._session.get(url, params=query_params or {}, headers=headers) as response:
        if response.status == 200:
            data = await response.json()
            return data.get("data", [])
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to list sources: {error_text}", response.status, error_text)

