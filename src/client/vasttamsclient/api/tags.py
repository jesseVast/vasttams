"""
Tags API methods.

Low-level API calls for tag operations.
"""

from typing import Dict, Any, Optional
from ..exceptions import TAMSAPIError


async def get_tags(client, entity_type: str, entity_id: str) -> Dict[str, str]:
    """Get all tags for an entity."""
    if entity_type == "source":
        url = f"{client.server_url}/sources/{entity_id}/tags"
    elif entity_type == "flow":
        url = f"{client.server_url}/flows/{entity_id}/tags"
    else:
        raise ValueError(f"Unsupported entity type: {entity_type}")
    
    async with client._session.get(url, headers=await client._get_headers()) as response:
        if response.status == 200:
            return await response.json()
        elif response.status == 404:
            return {}
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to get tags: {error_text}", response.status, error_text)


async def get_tag(client, entity_type: str, entity_id: str, tag_name: str) -> Optional[str]:
    """Get a specific tag value."""
    if entity_type == "source":
        url = f"{client.server_url}/sources/{entity_id}/tags/{tag_name}"
    elif entity_type == "flow":
        url = f"{client.server_url}/flows/{entity_id}/tags/{tag_name}"
    else:
        raise ValueError(f"Unsupported entity type: {entity_type}")
    
    async with client._session.get(url, headers=await client._get_headers()) as response:
        if response.status == 200:
            text = await response.text()
            # Try to parse as JSON if it looks like JSON (starts with quote)
            if text.startswith('"') and text.endswith('"'):
                import json
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    pass
            return text
        elif response.status == 404:
            return None
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to get tag: {error_text}", response.status, error_text)


async def set_tag(client, entity_type: str, entity_id: str, tag_name: str, tag_value: str) -> None:
    """Set or update a tag."""
    if entity_type == "source":
        url = f"{client.server_url}/sources/{entity_id}/tags/{tag_name}"
    elif entity_type == "flow":
        url = f"{client.server_url}/flows/{entity_id}/tags/{tag_name}"
    else:
        raise ValueError(f"Unsupported entity type: {entity_type}")
    
    headers = await client._get_headers()
    headers["Content-Type"] = "text/plain"
    async with client._session.put(url, data=tag_value, headers=headers) as response:
        if response.status not in (200, 204):
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to set tag: {error_text}", response.status, error_text)


async def delete_tag(client, entity_type: str, entity_id: str, tag_name: str) -> None:
    """Delete a tag."""
    if entity_type == "source":
        url = f"{client.server_url}/sources/{entity_id}/tags/{tag_name}"
    elif entity_type == "flow":
        url = f"{client.server_url}/flows/{entity_id}/tags/{tag_name}"
    else:
        raise ValueError(f"Unsupported entity type: {entity_type}")
    
    async with client._session.delete(url, headers=await client._get_headers()) as response:
        if response.status not in (200, 204):
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to delete tag: {error_text}", response.status, error_text)

