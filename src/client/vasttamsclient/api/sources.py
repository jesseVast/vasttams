"""
Source API methods.

Low-level API calls for source operations.
"""

from typing import TYPE_CHECKING, Dict, Any, List, Optional
from ..exceptions import TAMSAPIError, TAMSConnectionError

if TYPE_CHECKING:
    from ..client import TAMSClient


async def create_source(client: "TAMSClient", source_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a source."""
    url = f"{client.server_url}{client.api_prefix}/sources"
    headers = await client._get_headers()
    response = await client._request("POST", url, json=source_data, headers=headers)
    if response.status_code == 201:
        return response.json()
    else:
        error_text = response.text
        raise TAMSAPIError(f"Failed to create source: {error_text}", response.status_code, error_text)


async def get_source(client: "TAMSClient", source_id: str) -> Optional[Dict[str, Any]]:
    """Get a source by ID."""
    url = f"{client.server_url}{client.api_prefix}/sources/{source_id}"
    headers = await client._get_headers()
    response = await client._request("GET", url, headers=headers)
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        return None
    else:
        error_text = response.text
        raise TAMSAPIError(f"Failed to get source: {error_text}", response.status_code, error_text)


async def update_source_label(client: "TAMSClient", source_id: str, label: str) -> None:
    """Update a source label."""
    url = f"{client.server_url}{client.api_prefix}/sources/{source_id}/label"
    headers = await client._get_headers()
    headers["Content-Type"] = "text/plain"
    response = await client._request("PUT", url, data=label, headers=headers)
    if response.status_code not in (200, 204):
        error_text = response.text
        raise TAMSAPIError(f"Failed to update source label: {error_text}", response.status_code, error_text)


async def update_source_description(client: "TAMSClient", source_id: str, description: str) -> None:
    """Update a source description."""
    url = f"{client.server_url}{client.api_prefix}/sources/{source_id}/description"
    headers = await client._get_headers()
    headers["Content-Type"] = "text/plain"
    response = await client._request("PUT", url, data=description, headers=headers)
    if response.status_code not in (200, 204):
        error_text = response.text
        raise TAMSAPIError(f"Failed to update source description: {error_text}", response.status_code, error_text)


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
    response = await client._request("DELETE", url, params=params, headers=headers)
    # Accept 200, 202 (Accepted for async operations), or 204 (No Content)
    if response.status_code not in (200, 202, 204):
        error_text = response.text
        raise TAMSAPIError(f"Failed to delete source: {error_text}", response.status_code, error_text)


async def list_sources(client: "TAMSClient", query_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """List sources."""
    url = f"{client.server_url}{client.api_prefix}/sources"
    headers = await client._get_headers()
    response = await client._request("GET", url, params=query_params or {}, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get("data", []) if isinstance(data, dict) else data
    else:
        error_text = response.text
        raise TAMSAPIError(f"Failed to list sources: {error_text}", response.status_code, error_text)

