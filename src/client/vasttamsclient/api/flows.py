"""
Flow API methods.

Low-level API calls for flow operations.
"""

from typing import TYPE_CHECKING, Dict, Any, List, Optional
from ..exceptions import TAMSAPIError

if TYPE_CHECKING:
    from ..client import TAMSClient


async def create_flow(client: "TAMSClient", flow_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a flow."""
    import logging
    logger = logging.getLogger(__name__)
    
    # Debug logging for codec validation issues
    if "codec" in flow_data:
        codec_value = flow_data["codec"]
        logger.debug(f"Creating flow with codec: {repr(codec_value)} (type: {type(codec_value)})")
        if not isinstance(codec_value, str) or "/" not in str(codec_value):
            logger.error(f"INVALID CODEC DETECTED: {repr(codec_value)} (type: {type(codec_value)})")
    
    url = f"{client.server_url}{client.api_prefix}/flows"
    response = await client._request("POST", url, json=flow_data, headers=await client._get_headers())
    if response.status_code == 201:
        return response.json()
    else:
        error_text = response.text
        raise TAMSAPIError(f"Failed to create flow: {error_text}", response.status_code, error_text)


async def get_flow(client: "TAMSClient", flow_id: str) -> Optional[Dict[str, Any]]:
    """Get a flow by ID."""
    url = f"{client.server_url}{client.api_prefix}/flows/{flow_id}"
    response = await client._request("GET", url, headers=await client._get_headers())
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        return None
    else:
        error_text = response.text
        raise TAMSAPIError(f"Failed to get flow: {error_text}", response.status_code, error_text)


async def update_flow(client: "TAMSClient", flow_id: str, flow_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update a flow."""
    url = f"{client.server_url}{client.api_prefix}/flows/{flow_id}"
    response = await client._request("PUT", url, json=flow_data, headers=await client._get_headers())
    if response.status_code == 200:
        return response.json()
    else:
        error_text = response.text
        raise TAMSAPIError(f"Failed to update flow: {error_text}", response.status_code, error_text)


async def delete_flow(client: "TAMSClient", flow_id: str, cascade: bool = True) -> None:
    """Delete a flow.
    
    Args:
        client: TAMSClient instance
        flow_id: Flow ID to delete
        cascade: If True, cascade delete to associated segments (default: True)
    """
    url = f"{client.server_url}{client.api_prefix}/flows/{flow_id}"
    params = {"cascade": str(cascade).lower()}
    response = await client._request("DELETE", url, params=params, headers=await client._get_headers())
    # Accept 200, 202 (Accepted for async operations), or 204 (No Content)
    if response.status_code not in (200, 202, 204):
        error_text = response.text
        raise TAMSAPIError(f"Failed to delete flow: {error_text}", response.status_code, error_text)


async def list_flows(client: "TAMSClient", query_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """List flows."""
    url = f"{client.server_url}{client.api_prefix}/flows"
    response = await client._request("GET", url, params=query_params or {}, headers=await client._get_headers())
    if response.status_code == 200:
        data = response.json()
        return data.get("data", []) if isinstance(data, dict) else data
    else:
        error_text = response.text
        raise TAMSAPIError(f"Failed to list flows: {error_text}", response.status_code, error_text)

