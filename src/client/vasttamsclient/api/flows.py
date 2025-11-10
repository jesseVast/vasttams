"""
Flow API methods.

Low-level API calls for flow operations.
"""

from typing import TYPE_CHECKING, Dict, Any, List, Optional
import aiohttp
from ..exceptions import TAMSAPIError

if TYPE_CHECKING:
    from ..client import TAMSClient


async def create_flow(client: "TAMSClient", flow_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a flow."""
    url = f"{client.server_url}/flows"
    async with client._session.post(url, json=flow_data, headers=await client._get_headers()) as response:
        if response.status == 201:
            return await response.json()
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to create flow: {error_text}", response.status, error_text)


async def get_flow(client: "TAMSClient", flow_id: str) -> Optional[Dict[str, Any]]:
    """Get a flow by ID."""
    url = f"{client.server_url}/flows/{flow_id}"
    async with client._session.get(url, headers=await client._get_headers()) as response:
        if response.status == 200:
            return await response.json()
        elif response.status == 404:
            return None
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to get flow: {error_text}", response.status, error_text)


async def update_flow(client: "TAMSClient", flow_id: str, flow_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update a flow."""
    url = f"{client.server_url}/flows/{flow_id}"
    async with client._session.put(url, json=flow_data, headers=await client._get_headers()) as response:
        if response.status == 200:
            return await response.json()
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to update flow: {error_text}", response.status, error_text)


async def delete_flow(client: "TAMSClient", flow_id: str) -> None:
    """Delete a flow."""
    url = f"{client.server_url}/flows/{flow_id}"
    async with client._session.delete(url, headers=await client._get_headers()) as response:
        if response.status not in (200, 204):
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to delete flow: {error_text}", response.status, error_text)


async def list_flows(client: "TAMSClient", query_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """List flows."""
    url = f"{client.server_url}/flows"
    async with client._session.get(url, params=query_params or {}, headers=await client._get_headers()) as response:
        if response.status == 200:
            data = await response.json()
            return data.get("data", [])
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to list flows: {error_text}", response.status, error_text)

