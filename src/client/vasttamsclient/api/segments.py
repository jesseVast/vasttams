"""
Segment API methods.

Low-level API calls for segment operations.
"""

import json
import os
import logging
from typing import Dict, Any, List, Optional
import aiohttp
from pathlib import Path
from ..exceptions import TAMSAPIError

logger = logging.getLogger(__name__)

# Default chunk size for multipart uploads (8MB)
DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024  # 8MB


async def create_segment(client, flow_id: str, segment_data: Dict[str, Any], file_path: Optional[str] = None, chunk_size: int = DEFAULT_CHUNK_SIZE) -> Dict[str, Any]:
    """
    Create a segment with optional file upload.
    
    Args:
        client: TAMSClient instance
        flow_id: Flow ID
        segment_data: Segment data dictionary
        file_path: Optional path to file to upload
        chunk_size: Chunk size for multipart uploads (default: 8MB)
    """
    url = f"{client.server_url}/flows/{flow_id}/segments"
    
    if file_path:
        # Multipart form data upload with chunked file reading
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise TAMSAPIError(f"File not found: {file_path}")
        
        file_size = file_path_obj.stat().st_size
        logger.debug(f"Uploading file {file_path} ({file_size} bytes) using multipart form data")
        
        # Use aiohttp's FormData for multipart upload
        # For large files, aiohttp will stream the file in chunks automatically
        data = aiohttp.FormData()
        data.add_field('segment_data', json.dumps(segment_data), content_type='application/json')
        
        # Add file field - aiohttp will handle streaming for large files
        # When file is large, aiohttp streams it in chunks during multipart encoding
        with open(file_path, 'rb') as f:
            data.add_field('file', f, filename=file_path_obj.name, content_type='application/octet-stream')
            
            headers = await client._get_headers()
            # Remove Content-Type for multipart (aiohttp will set it correctly with boundary)
            headers.pop('Content-Type', None)
            
            async with client._session.post(url, data=data, headers=headers) as response:
                if response.status == 201:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise TAMSAPIError(f"Failed to create segment: {error_text}", response.status, error_text)
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


async def upload_to_storage(client, presigned_url: str, data: bytes = None, file_path: Optional[str] = None, 
                           content_type: str = "application/octet-stream", chunk_size: int = DEFAULT_CHUNK_SIZE) -> bool:
    """
    Upload data to storage using presigned URL with multipart support.
    
    Args:
        client: TAMSClient instance
        presigned_url: Presigned URL for upload
        data: Bytes data to upload (if file_path not provided)
        file_path: Path to file to upload (alternative to data)
        content_type: Content type for upload
        chunk_size: Chunk size for streaming uploads (default: 8MB)
    
    Returns:
        bool: True if upload successful
    """
    headers = {"Content-Type": content_type}
    
    if file_path:
        # Stream file in chunks for large files
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise TAMSAPIError(f"File not found: {file_path}")
        
        file_size = file_path_obj.stat().st_size
        logger.debug(f"Uploading file {file_path} ({file_size} bytes) to presigned URL using chunked upload")
        
        # Use aiohttp's streaming upload
        async def file_reader():
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        
        async with client._session.put(presigned_url, data=file_reader(), headers=headers) as response:
            if response.status in (200, 201, 204):
                return True
            else:
                error_text = await response.text()
                raise TAMSAPIError(f"Failed to upload to storage: {error_text}", response.status, error_text)
    elif data:
        # For small data, upload directly
        # For large data, still use chunked approach
        if len(data) > chunk_size:
            logger.debug(f"Uploading {len(data)} bytes in chunks to presigned URL")
            # Create a generator for chunked upload
            async def data_reader():
                offset = 0
                while offset < len(data):
                    chunk = data[offset:offset + chunk_size]
                    yield chunk
                    offset += chunk_size
            
            async with client._session.put(presigned_url, data=data_reader(), headers=headers) as response:
                if response.status in (200, 201, 204):
                    return True
                else:
                    error_text = await response.text()
                    raise TAMSAPIError(f"Failed to upload to storage: {error_text}", response.status, error_text)
        else:
            # Small data, upload directly
            async with client._session.put(presigned_url, data=data, headers=headers) as response:
                if response.status in (200, 201, 204):
                    return True
                else:
                    error_text = await response.text()
                    raise TAMSAPIError(f"Failed to upload to storage: {error_text}", response.status, error_text)
    else:
        raise ValueError("Either data or file_path must be provided")

