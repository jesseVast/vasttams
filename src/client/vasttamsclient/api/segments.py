"""
Segment API methods.

Low-level API calls for segment operations.
"""

import json
import os
import logging
import asyncio
import threading
from typing import TYPE_CHECKING, Dict, Any, List, Optional
import requests
import aiohttp
from pathlib import Path
from ..exceptions import TAMSAPIError

if TYPE_CHECKING:
    from ..client import TAMSClient

logger = logging.getLogger(__name__)

# Default chunk size for multipart uploads (8MB)
DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024  # 8MB

# Shared requests session pool for presigned URL uploads
# Using thread-local storage to ensure thread safety
_thread_local = threading.local()

def _get_requests_session():
    """Get or create a thread-local requests session for connection pooling."""
    if not hasattr(_thread_local, 'session'):
        _thread_local.session = requests.Session()
        # Configure connection pooling
        # Increased pool sizes to handle concurrent parallel uploads and URL generation
        # pool_connections: number of connection pools (one per host)
        # pool_maxsize: max connections per pool (increased for parallel operations)
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=50,  # Number of connection pools to cache (increased from 10)
            pool_maxsize=100,  # Maximum number of connections to save in the pool (increased from 20)
            max_retries=3
        )
        _thread_local.session.mount('http://', adapter)
        _thread_local.session.mount('https://', adapter)
    return _thread_local.session


async def create_segment(client: "TAMSClient", flow_id: str, segment_data: Dict[str, Any], file_path: Optional[str] = None, chunk_size: int = DEFAULT_CHUNK_SIZE) -> Dict[str, Any]:
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


async def list_segments(client: "TAMSClient", flow_id: str, query_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """List segments for a flow."""
    url = f"{client.server_url}/flows/{flow_id}/segments"
    async with client._session.get(url, params=query_params or {}, headers=await client._get_headers()) as response:
        if response.status == 200:
            data = await response.json()
            # Server returns a list directly, not a dict with "data" key
            if isinstance(data, list):
                return data
            # Handle pagination case if server returns dict with "data" key
            return data.get("data", [])
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to list segments: {error_text}", response.status, error_text)


async def delete_segments(client: "TAMSClient", flow_id: str, query_params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Delete segments.
    
    Returns:
        None if deletion completed synchronously (200/204)
        Dict with deletion request info if async deletion was created (202)
        The dict contains:
            - id: Deletion request ID
            - status: Request status ("created")
            - location: URL to check deletion request status
    """
    url = f"{client.server_url}/flows/{flow_id}/segments"
    async with client._session.delete(url, params=query_params or {}, headers=await client._get_headers()) as response:
        if response.status == 202:
            # Async deletion request created
            location = response.headers.get("Location", "")
            try:
                response_data = await response.json()
                response_data["location"] = location
                return response_data
            except:
                # If JSON parsing fails, extract ID from Location header
                request_id = location.split("/")[-1] if "/" in location else None
                return {
                    "id": request_id,
                    "status": "created",
                    "location": location,
                    "message": "Deletion request created"
                }
        elif response.status in (200, 204):
            # Synchronous deletion completed
            return None
        else:
            error_text = await response.text()
            raise TAMSAPIError(f"Failed to delete segments: {error_text}", response.status, error_text)


async def allocate_storage(client: "TAMSClient", flow_id: str, label: Optional[str] = None, limit: int = 1, storage_id: Optional[str] = None) -> Dict[str, Any]:
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


async def upload_to_storage(client: "TAMSClient", presigned_url: str, data: bytes = None, file_path: Optional[str] = None, 
                           content_type: str = "application/octet-stream", chunk_size: int = DEFAULT_CHUNK_SIZE) -> bool:
    """
    Upload data to storage using presigned URL.
    
    When the server generates a presigned URL with content_type, the signature
    includes it, so we MUST include a matching Content-Type header in the request.
    The server provides content-type in the put_url response.
    
    Args:
        client: TAMSClient instance
        presigned_url: Presigned URL for upload
        data: Bytes data to upload (if file_path not provided)
        file_path: Path to file to upload (alternative to data)
        content_type: Content-Type header value (must match what was used to sign the URL)
        chunk_size: Threshold for chunked uploads (default: 8MB)
    
    Returns:
        bool: True if upload successful
    """
    # If content_type is provided, check if presigned URL already has it in query string
    # If it's in the query string, we may not need to add it as a header (depends on S3 implementation)
    # Some S3 implementations require it in both places, others only in query string
    headers = {}
    
    # Check if presigned URL has content-type in query string
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(presigned_url)
    query_params = parse_qs(parsed.query)
    has_content_type_in_query = 'content-type' in query_params or 'Content-Type' in query_params
    
    # Include Content-Type header if provided
    # Note: Some S3 implementations require it even if in query string, others don't
    # The server's ingest_test_data_real.py always includes it, so we do too
    if content_type:
        headers["Content-Type"] = content_type
        if has_content_type_in_query:
            logger.debug(f"Presigned URL has content-type in query string, also adding as header")
    
    if file_path:
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise TAMSAPIError(f"File not found: {file_path}")
        
        file_size = file_path_obj.stat().st_size
        logger.debug(f"Uploading file {file_path} ({file_size} bytes) to presigned URL")
        logger.debug(f"Presigned URL: {presigned_url[:100]}...")  # Truncate for logging
        logger.debug(f"Content-Type header: {content_type}")
        logger.debug(f"Headers to send: {headers}")
        
        # Use requests library (synchronous) to match server's ingest_test_data_real.py implementation
        # Run in thread pool to avoid blocking the event loop
        # Use thread-local session for connection pooling
        def _upload_file():
            session = _get_requests_session()
            if file_size < chunk_size:
                # Small file: read into memory (matches server script behavior)
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                logger.debug(f"Uploading {len(file_data)} bytes as data (small file)")
                response = session.put(presigned_url, data=file_data, headers=headers, timeout=300)
                logger.debug(f"Response status: {response.status_code}")
                if response.status_code in (200, 201, 204):
                    return True
                else:
                    error_text = response.text
                    logger.error(f"Upload failed. Response body: {error_text}")
                    raise TAMSAPIError(f"Failed to upload to storage: {error_text}", response.status_code, error_text)
            else:
                # Large file: use file handle for streaming (matches server script behavior)
                logger.debug(f"Uploading as file handle (large file, streaming)")
                with open(file_path, 'rb') as f:
                    response = session.put(presigned_url, data=f, headers=headers, timeout=300)
                    logger.debug(f"Response status: {response.status_code}")
                    if response.status_code in (200, 201, 204):
                        return True
                    else:
                        error_text = response.text
                        logger.error(f"Upload failed. Response body: {error_text}")
                        raise TAMSAPIError(f"Failed to upload to storage: {error_text}", response.status_code, error_text)
        
        # Run synchronous requests.put in thread pool and ensure it completes
        result = await asyncio.to_thread(_upload_file)
        return result
    elif data:
        # Presigned URLs should be used with a plain session (no auth headers)
        logger.debug(f"Uploading {len(data)} bytes of data to presigned URL")
        logger.debug(f"Presigned URL: {presigned_url}")
        
        # Use requests library (synchronous) to match server's ingest_test_data_real.py implementation
        # Run in thread pool to avoid blocking the event loop
        # Use thread-local session for connection pooling
        def _upload_data():
            session = _get_requests_session()
            if len(data) < chunk_size:
                # Small data: upload directly
                logger.debug(f"Uploading {len(data)} bytes directly (small data)")
                response = session.put(presigned_url, data=data, headers=headers, timeout=300)
                logger.debug(f"Response status: {response.status_code}")
                if response.status_code in (200, 201, 204):
                    return True
                else:
                    error_text = response.text
                    logger.error(f"Upload failed. Response body: {error_text}")
                    raise TAMSAPIError(f"Failed to upload to storage: {error_text}", response.status_code, error_text)
            else:
                # Large data: requests will handle chunking automatically when streaming
                logger.debug(f"Uploading {len(data)} bytes (large data, requests will handle chunking)")
                # Create a file-like object from bytes for streaming
                import io
                data_stream = io.BytesIO(data)
                response = session.put(presigned_url, data=data_stream, headers=headers, timeout=300)
                logger.debug(f"Response status: {response.status_code}")
                if response.status_code in (200, 201, 204):
                    return True
                else:
                    error_text = response.text
                    logger.error(f"Upload failed. Response body: {error_text}")
                    raise TAMSAPIError(f"Failed to upload to storage: {error_text}", response.status_code, error_text)
        
        # Run synchronous requests.put in thread pool and ensure it completes
        result = await asyncio.to_thread(_upload_data)
        return result
    else:
        raise ValueError("Either data or file_path must be provided")

