"""
Deletion Request API methods.

Low-level API calls for deletion request operations.
"""

from typing import TYPE_CHECKING, Dict, Any, List, Optional
from ..exceptions import TAMSAPIError

if TYPE_CHECKING:
    from ..client import TAMSClient


async def get_deletion_requests(client: "TAMSClient") -> List[Dict[str, Any]]:
    """Get all deletion requests."""
    url = f"{client.server_url}{client.api_prefix}/flow-delete-requests"
    response = await client._request("GET", url, headers=await client._get_headers())
    if response.status_code == 200:
        return response.json()
    else:
        error_text = response.text
        raise TAMSAPIError(f"Failed to get deletion requests: {error_text}", response.status_code, error_text)


async def get_deletion_request(client: "TAMSClient", request_id: str) -> Optional[Dict[str, Any]]:
    """Get a deletion request by ID."""
    url = f"{client.server_url}/flow-delete-requests/{request_id}"
    response = await client._request("GET", url, headers=await client._get_headers())
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        return None
    else:
        error_text = response.text
        raise TAMSAPIError(f"Failed to get deletion request: {error_text}", response.status_code, error_text)

