"""
TAMS API Client

Client for interacting with TAMS API for source, flow, and segment management.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
import aiohttp
import json
import uuid

from .models import Source, VideoFlow, TAMSSegment
from .constants import TAMS_ENDPOINTS, TAMS_HEADERS, TAMS_ERRORS

logger = logging.getLogger(__name__)


class TAMSError(Exception):
    """Exception raised for TAMS API errors."""
    pass


class TAMSClient:
    """
    Client for interacting with TAMS API.
    
    Provides methods for:
    - Creating and managing sources
    - Creating and managing flows
    - Uploading flow segments
    - Searching sources and flows
    - Handling API errors and retries
    
    COMPATIBILITY: This client is ONLY compatible with TAMS API version 6.0.
    It will fail gracefully if used with later versions.
    """
    
    def __init__(self, base_url: str, api_key: Optional[str] = None, 
                 timeout: int = 30, retry_attempts: int = 3, verify_ssl: bool = False):
        """
        Initialize TAMS client.
        
        Args:
            base_url: TAMS API base URL
            api_key: Optional API key
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts
            verify_ssl: Verify SSL certificates
            
        Raises:
            TAMSError: If TAMS API version is not 6.0
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.verify_ssl = verify_ssl
        self._version_checked = False
        
        logger.info(f"TAMS client initialized - Base URL: {self.base_url}")
    
    async def _check_api_version(self) -> None:
        """
        Check TAMS API version compatibility.
        
        Raises:
            TAMSError: If API version is not 6.0
        """
        if self._version_checked:
            return
            
        try:
            url = f"{self.base_url}{TAMS_ENDPOINTS['service']}"
            headers = self._get_headers()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ssl=self.verify_ssl
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        api_version = data.get('api_version', 'unknown')
                        
                        if api_version != '6.0':
                            error_msg = (
                                f"TAMS API version {api_version} is not supported. "
                                f"This client only supports TAMS API version 6.0. "
                                f"Please use a compatible TAMS server or update the client."
                            )
                            logger.error(error_msg)
                            raise TAMSError(error_msg)
                        
                        logger.info(f"TAMS API version {api_version} is compatible")
                        self._version_checked = True
                    else:
                        error_text = await response.text()
                        raise TAMSError(f"Failed to check API version: {response.status} - {error_text}")
                        
        except TAMSError:
            raise
        except Exception as e:
            logger.error(f"TAMS API version check error: {e}")
            raise TAMSError(f"API version check failed: {e}")

    async def health_check(self) -> bool:
        """
        Check if TAMS API is healthy and version-compatible.
        
        Returns:
            bool: True if API is healthy and compatible with version 6.0
        """
        try:
            # First check API version compatibility
            await self._check_api_version()
            
            # Then check health
            url = f"{self.base_url}{TAMS_ENDPOINTS['health']}"
            headers = self._get_headers()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5),
                    ssl=self.verify_ssl
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        status = data.get('status', '')
                        if status == 'healthy':
                            logger.info("TAMS API health check passed and version is compatible")
                            return True
                        else:
                            logger.warning(f"TAMS API health check failed: {status}")
                            return False
                    else:
                        logger.warning(f"TAMS API health check failed: {response.status}")
                        return False
                        
        except TAMSError as e:
            logger.error(f"TAMS API compatibility error: {e}")
            return False
        except Exception as e:
            logger.error(f"TAMS API health check error: {e}")
            return False
    
    async def create_source(self, source_data: Dict[str, Any]) -> str:
        """
        Create a new source in TAMS.
        
        Args:
            source_data: Source data including format, label, description, tags
            
        Returns:
            str: Created source ID
            
        Raises:
            TAMSError: If source creation fails or API version is incompatible
        """
        try:
            # Check API version compatibility
            await self._check_api_version()
            
            # Generate UUID for source if not provided
            if 'id' not in source_data:
                source_data['id'] = str(uuid.uuid4())
            
            url = f"{self.base_url}{TAMS_ENDPOINTS['sources']}"
            headers = self._get_headers()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, 
                    json=source_data, 
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ssl=self.verify_ssl
                ) as response:
                    if response.status == 201:
                        result = await response.json()
                        source_id = result.get('id')
                        logger.info(f"Created TAMS source: {source_id}")
                        return source_id
                    else:
                        error_text = await response.text()
                        raise TAMSError(f"Failed to create source: {response.status} - {error_text}")
                        
        except Exception as e:
            logger.error(f"Error creating TAMS source: {e}")
            raise TAMSError(f"Source creation failed: {e}")
    
    async def create_flow(self, flow_data: Dict[str, Any]) -> str:
        """
        Create a new flow in TAMS.
        
        Args:
            flow_data: Flow data including source_id, format, codec, label, description, tags
            
        Returns:
            str: Created flow ID
            
        Raises:
            TAMSError: If flow creation fails or API version is incompatible
        """
        try:
            # Check API version compatibility
            await self._check_api_version()
            
            # Generate UUID for flow if not provided
            if 'id' not in flow_data:
                flow_data['id'] = str(uuid.uuid4())
            
            url = f"{self.base_url}{TAMS_ENDPOINTS['flows']}"
            headers = self._get_headers()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, 
                    json=flow_data, 
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ssl=self.verify_ssl
                ) as response:
                    if response.status == 201:
                        result = await response.json()
                        flow_id = result.get('id')
                        logger.info(f"Created TAMS flow: {flow_id}")
                        return flow_id
                    else:
                        error_text = await response.text()
                        raise TAMSError(f"Failed to create flow: {response.status} - {error_text}")
                        
        except Exception as e:
            logger.error(f"Error creating TAMS flow: {e}")
            raise TAMSError(f"Flow creation failed: {e}")
    
    async def create_flow_segment(self, flow_id: str, segment_data: Dict[str, Any], 
                                 file_path: Optional[str] = None) -> str:
        """
        Create a flow segment in TAMS.
        
        Args:
            flow_id: Flow ID to create segment for
            segment_data: FlowSegment data including object_id, timerange, etc.
            file_path: Optional file path for media file
            
        Returns:
            str: Created segment object_id
            
        Raises:
            TAMSError: If segment creation fails or API version is incompatible
        """
        try:
            # Check API version compatibility
            await self._check_api_version()
            
            url = f"{self.base_url}{TAMS_ENDPOINTS['flow_segments'].format(flow_id=flow_id)}"
            headers = self._get_headers()
            
            # Prepare multipart form data as required by TAMS API
            data = aiohttp.FormData()
            
            # Add segment data as JSON string (TAMS API expects segment_data field)
            data.add_field('segment_data', json.dumps(segment_data), content_type='application/json')
            
            # Add file if provided
            if file_path and Path(file_path).exists():
                data.add_field('file', open(file_path, 'rb'), filename=Path(file_path).name)
            
            # Remove Content-Type header for multipart form data
            multipart_headers = {k: v for k, v in headers.items() if k.lower() != 'content-type'}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    data=data,
                    headers=multipart_headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ssl=self.verify_ssl
                ) as response:
                    if response.status == 201:
                        result = await response.json()
                        object_id = result.get('object_id')
                        logger.info(f"Created TAMS flow segment: {object_id}")
                        return object_id
                    else:
                        error_text = await response.text()
                        raise TAMSError(f"Failed to create flow segment: {response.status} - {error_text}")
                        
        except Exception as e:
            logger.error(f"Error creating TAMS flow segment: {e}")
            raise TAMSError(f"Flow segment creation failed: {e}")
    
    async def upload_segment(self, flow_id: str, segment_data: Dict[str, Any], 
                           file_path: str) -> str:
        """
        Upload a flow segment with file to TAMS.
        
        Args:
            flow_id: Flow ID to upload segment to
            segment_data: Segment data including object_id, timerange, get_urls
            file_path: Path to media file to upload
            
        Returns:
            str: Uploaded segment object_id
            
        Raises:
            TAMSError: If segment upload fails
        """
        try:
            url = f"{self.base_url}{TAMS_ENDPOINTS['flow_segments'].format(flow_id=flow_id)}"
            headers = self._get_headers()
            
            # Prepare multipart form data
            data = aiohttp.FormData()
            data.add_field('segment', json.dumps(segment_data), content_type='application/json')
            
            with open(file_path, 'rb') as f:
                data.add_field('file', f, filename=Path(file_path).name)
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        data=data,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=self.timeout * 2),  # Longer timeout for uploads
                        ssl=self.verify_ssl
                    ) as response:
                        if response.status == 201:
                            result = await response.json()
                            object_id = result.get('object_id')
                            logger.info(f"Uploaded TAMS segment with file: {object_id}")
                            return object_id
                        else:
                            error_text = await response.text()
                            raise TAMSError(f"Failed to upload segment: {response.status} - {error_text}")
                            
        except Exception as e:
            logger.error(f"Error uploading TAMS segment: {e}")
            raise TAMSError(f"Segment upload failed: {e}")
    
    async def get_source(self, source_id: str) -> Optional[Source]:
        """
        Retrieve a source from TAMS.
        
        Args:
            source_id: Source ID to retrieve
            
        Returns:
            Source or None if not found
            
        Raises:
            TAMSError: If source retrieval fails
        """
        try:
            url = f"{self.base_url}{TAMS_ENDPOINTS['sources']}/{source_id}"
            headers = self._get_headers()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ssl=self.verify_ssl
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return Source(**data)
                    elif response.status == 404:
                        logger.warning(f"Source not found: {source_id}")
                        return None
                    else:
                        error_text = await response.text()
                        raise TAMSError(f"Failed to get source: {response.status} - {error_text}")
                        
        except Exception as e:
            logger.error(f"Error retrieving TAMS source {source_id}: {e}")
            raise TAMSError(f"Source retrieval failed: {e}")
    
    async def get_flow(self, flow_id: str) -> Optional[VideoFlow]:
        """
        Retrieve a flow from TAMS.
        
        Args:
            flow_id: Flow ID to retrieve
            
        Returns:
            VideoFlow or None if not found
            
        Raises:
            TAMSError: If flow retrieval fails
        """
        try:
            url = f"{self.base_url}{TAMS_ENDPOINTS['flows']}/{flow_id}"
            headers = self._get_headers()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ssl=self.verify_ssl
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return VideoFlow(**data)
                    elif response.status == 404:
                        logger.warning(f"Flow not found: {flow_id}")
                        return None
                    else:
                        error_text = await response.text()
                        raise TAMSError(f"Failed to get flow: {response.status} - {error_text}")
                        
        except Exception as e:
            logger.error(f"Error retrieving TAMS flow {flow_id}: {e}")
            raise TAMSError(f"Flow retrieval failed: {e}")
    
    async def list_sources(self, query_params: Optional[Dict[str, Any]] = None) -> List[Source]:
        """
        List sources from TAMS.
        
        Args:
            query_params: Optional query parameters for filtering
            
        Returns:
            List of Source objects
            
        Raises:
            TAMSError: If listing fails
        """
        try:
            url = f"{self.base_url}{TAMS_ENDPOINTS['sources']}"
            headers = self._get_headers()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=query_params or {},
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ssl=self.verify_ssl
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        sources_data = data.get('data', [])
                        sources = [Source(**source) for source in sources_data]
                        logger.info(f"Found {len(sources)} sources")
                        return sources
                    else:
                        error_text = await response.text()
                        raise TAMSError(f"Failed to list sources: {response.status} - {error_text}")
                        
        except Exception as e:
            logger.error(f"Error listing TAMS sources: {e}")
            raise TAMSError(f"Source listing failed: {e}")
    
    async def list_flows(self, query_params: Optional[Dict[str, Any]] = None) -> List[VideoFlow]:
        """
        List flows from TAMS.
        
        Args:
            query_params: Optional query parameters for filtering
            
        Returns:
            List of VideoFlow objects
            
        Raises:
            TAMSError: If listing fails
        """
        try:
            url = f"{self.base_url}{TAMS_ENDPOINTS['flows']}"
            headers = self._get_headers()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=query_params or {},
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ssl=self.verify_ssl
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        flows_data = data.get('data', [])
                        flows = [VideoFlow(**flow) for flow in flows_data]
                        logger.info(f"Found {len(flows)} flows")
                        return flows
                    else:
                        error_text = await response.text()
                        raise TAMSError(f"Failed to list flows: {response.status} - {error_text}")
                        
        except Exception as e:
            logger.error(f"Error listing TAMS flows: {e}")
            raise TAMSError(f"Flow listing failed: {e}")
    
    async def get_flow_segments(self, flow_id: str, query_params: Optional[Dict[str, Any]] = None) -> List[TAMSSegment]:
        """
        Get segments for a flow from TAMS.
        
        Args:
            flow_id: Flow ID to get segments for
            query_params: Optional query parameters for filtering
            
        Returns:
            List of TAMSSegment objects
            
        Raises:
            TAMSError: If segment retrieval fails
        """
        try:
            url = f"{self.base_url}{TAMS_ENDPOINTS['flow_segments'].format(flow_id=flow_id)}"
            headers = self._get_headers()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=query_params or {},
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ssl=self.verify_ssl
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        segments_data = data.get('data', [])
                        segments = [TAMSSegment(**segment) for segment in segments_data]
                        logger.info(f"Found {len(segments)} segments for flow {flow_id}")
                        return segments
                    else:
                        error_text = await response.text()
                        raise TAMSError(f"Failed to get flow segments: {response.status} - {error_text}")
                        
        except Exception as e:
            logger.error(f"Error getting TAMS flow segments: {e}")
            raise TAMSError(f"Flow segment retrieval failed: {e}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests."""
        headers = TAMS_HEADERS.copy()
        
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        return headers
