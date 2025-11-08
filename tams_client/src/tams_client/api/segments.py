"""
Segment API methods.

Low-level API calls for segment operations.
"""

import json
from typing import Dict, Any, List, Optional
import aiohttp
from pathlib import Path
from ..exceptions import TAMSAPIError


async def create_segment(client, flow_id: str, segment_data: Dict[str, Any], file_path: Optional[str] = None) -> Dict[str, Any]:
    """Create a segment."""
    url = f"{client.server_url}/flows/{flow_id}/segments"
    
    if file_path:
        # Multipart form data upload
        data = aiohttp.FormData()
        data.add_field('segment_data', json.dumps(segment_data), content_type='application/json')
        
        file_path_obj = Path(file_path)
        if file_path_obj.exists():
            # Read file data first
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            data.add_field('file', file_data, filename=file_path_obj.name)
            headers = await client._get_headers()
            # Remove Content-Type for multipart
            headers.pop('Content-Type', None)
            async with client._session.post(url, data=data, headers=headers) as response:
                if response.status == 201:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise TAMSAPIError(f"Failed to create segment: {error_text}", response.status, error_text)
        else:
            raise TAMSAPIError(f"File not found: {file_path}")
    else:
        # JSON only
        async with client._session.post(url, json=segment_data, headers=await client._get_headers()) as response:
            if response.status == 201:
                return await response.json()
            else:
                error_text = await response.text()
                raise TAMSAPIError(f"Failed to create segment: {error_text}", response.status, error_text)


async def list_segments(client, flow_id: str, query_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """List segments for a flow."""
    url = f"{client.server_url}/flows/{flow_id}/segments"
    async with client._session.get(url, params=query_params or {}, headers=await client._get_headers()) as response:
        if response.status == 200:
            data = await response.json()
            return data.get("data", [])
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to list segments: {error_text}", response.status, error_text)


async def delete_segments(client, flow_id: str, query_params: Optional[Dict[str, Any]] = None) -> None:
    """Delete segments."""
    url = f"{client.server_url}/flows/{flow_id}/segments"
    async with client._session.delete(url, params=query_params or {}, headers=await client._get_headers()) as response:
        if response.status not in (200, 204):
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to delete segments: {error_text}", response.status, error_text)


async def allocate_storage(client, flow_id: str, label: Optional[str] = None, limit: int = 1, storage_id: Optional[str] = None) -> Dict[str, Any]:
    """Allocate storage for flow segments."""
    url = f"{client.server_url}/flows/{flow_id}/storage"
    data = {"limit": limit}
    if label:
        data["label"] = label
    if storage_id:
        data["storage_id"] = storage_id
    
    async with client._session.post(url, json=data, headers=await client._get_headers()) as response:
        if response.status == 201:
            return await response.json()
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to allocate storage: {error_text}", response.status, error_text)


async def upload_to_storage(client, presigned_url: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
    """Upload data to storage using presigned URL."""
    headers = {"Content-Type": content_type}
    async with client._session.put(presigned_url, data=data, headers=headers) as response:
        if response.status in (200, 201, 204):
            return True
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to upload to storage: {error_text}", response.status, error_text)

