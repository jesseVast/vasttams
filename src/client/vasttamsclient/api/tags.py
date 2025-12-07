"""
Tags API methods.

Low-level API calls for tag operations.
"""

import json
from typing import TYPE_CHECKING, Dict, Any, Optional, Union, List
from ..exceptions import TAMSAPIError

if TYPE_CHECKING:
    from ..client import TAMSClient


async def get_tags(client: "TAMSClient", entity_type: str, entity_id: str) -> Dict[str, Union[str, List[str]]]:
    """
    Get all tags for an entity.
    
    Returns:
        Dict mapping tag names to values (string or list of strings)
    """
    if entity_type == "source":
        url = f"{client.server_url}{client.api_prefix}/sources/{entity_id}/tags"
    elif entity_type == "flow":
        url = f"{client.server_url}{client.api_prefix}/flows/{entity_id}/tags"
    else:
        raise ValueError(f"Unsupported entity type: {entity_type}")
    
    response = await client._request("GET", url, headers=await client._get_headers())
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        return {}
    else:
        error_text = response.text
        raise TAMSAPIError(f"Failed to get tags: {error_text}", response.status_code, error_text)


async def get_tag(client: "TAMSClient", entity_type: str, entity_id: str, tag_name: str) -> Optional[Union[str, List[str]]]:
    """
    Get a specific tag value.
    
    Returns:
        Tag value as string or list of strings, or None if not found
    """
    if entity_type == "source":
        url = f"{client.server_url}{client.api_prefix}/sources/{entity_id}/tags/{tag_name}"
    elif entity_type == "flow":
        url = f"{client.server_url}{client.api_prefix}/flows/{entity_id}/tags/{tag_name}"
    else:
        raise ValueError(f"Unsupported entity type: {entity_type}")
    
    response = await client._request("GET", url, headers=await client._get_headers())
    if response.status_code == 200:
        # Try to parse as JSON (handles both strings and arrays)
        try:
            return response.json()
        except Exception:
            return response.text
    elif response.status_code == 404:
        return None
    else:
        error_text = response.text
        raise TAMSAPIError(f"Failed to get tag: {error_text}", response.status_code, error_text)


async def set_tag(client: "TAMSClient", entity_type: str, entity_id: str, tag_name: str, 
                  tag_value: Union[str, List[str]]) -> None:
    """
    Set or update a tag.
    
    Args:
        client: TAMSClient instance
        entity_type: Entity type ("source" or "flow")
        entity_id: Entity ID
        tag_name: Tag name
        tag_value: Tag value (string or list of strings)
    """
    if entity_type == "source":
        url = f"{client.server_url}{client.api_prefix}/sources/{entity_id}/tags/{tag_name}"
    elif entity_type == "flow":
        url = f"{client.server_url}{client.api_prefix}/flows/{entity_id}/tags/{tag_name}"
    else:
        raise ValueError(f"Unsupported entity type: {entity_type}")
    
    headers = await client._get_headers()
    
    # Handle list values - send as JSON
    if isinstance(tag_value, list):
        headers["Content-Type"] = "application/json"
        data = json.dumps(tag_value)
    else:
        # String value - send as text/plain
        headers["Content-Type"] = "text/plain"
        data = tag_value
    
    response = await client._request("PUT", url, data=data, headers=headers)
    if response.status_code not in (200, 204):
        error_text = response.text
        raise TAMSAPIError(f"Failed to set tag: {error_text}", response.status_code, error_text)


async def delete_tag(client: "TAMSClient", entity_type: str, entity_id: str, tag_name: str) -> None:
    """Delete a tag."""
    if entity_type == "source":
        url = f"{client.server_url}{client.api_prefix}/sources/{entity_id}/tags/{tag_name}"
    elif entity_type == "flow":
        url = f"{client.server_url}{client.api_prefix}/flows/{entity_id}/tags/{tag_name}"
    else:
        raise ValueError(f"Unsupported entity type: {entity_type}")
    
    response = await client._request("DELETE", url, headers=await client._get_headers())
    if response.status_code not in (200, 204):
        error_text = response.text
        raise TAMSAPIError(f"Failed to delete tag: {error_text}", response.status_code, error_text)

