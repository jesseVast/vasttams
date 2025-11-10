"""
Deletion Request API methods.

Low-level API calls for deletion request operations.
"""

from typing import TYPE_CHECKING, Dict, Any, List, Optional
import aiohttp
from ..exceptions import TAMSAPIError

if TYPE_CHECKING:
    from ..client import TAMSClient


async def get_deletion_requests(client: "TAMSClient") -> List[Dict[str, Any]]:
    """Get all deletion requests."""
    url = f"{client.server_url}/flow-delete-requests"
    async with client._session.get(url, headers=await client._get_headers()) as response:
        if response.status == 200:
            return await response.json()
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to get deletion requests: {error_text}", response.status, error_text)


async def get_deletion_request(client: "TAMSClient", request_id: str) -> Optional[Dict[str, Any]]:
    """Get a deletion request by ID."""
    url = f"{client.server_url}/flow-delete-requests/{request_id}"
    async with client._session.get(url, headers=await client._get_headers()) as response:
        if response.status == 200:
            return await response.json()
        elif response.status == 404:
            return None
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to get deletion request: {error_text}", response.status, error_text)

