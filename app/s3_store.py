"""
S3 Store for TAMS Flow Segments

This module handles S3 operations for storing and retrieving flow segment data.
Flow segments contain the actual media data and are stored in S3 buckets,
while metadata is stored in the VAST database.
"""

import logging
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, Union, BinaryIO
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import urllib.parse

from .models import FlowSegment, GetUrl, TimeRange

logger = logging.getLogger(__name__)


class S3Store:
    """
    S3 Store for TAMS Flow Segments
    
    This class provides a high-level interface to S3 for storing and retrieving
    flow segment data. Flow segments contain the actual media content and are
    stored as objects in S3 buckets.
    """
    
    def __init__(self,
                 endpoint_url: str = "http://localhost:9000",
                 access_key_id: str = "minioadmin",
                 secret_access_key: str = "minioadmin",
                 bucket_name: str = "tams-segments",
                 use_ssl: bool = False):
        """
        Initialize S3 Store with connection parameters
        
        Args:
            endpoint_url: S3-compatible endpoint URL (e.g., MinIO, AWS S3)
            access_key_id: S3 access key for authentication
            secret_access_key: S3 secret key for authentication
            bucket_name: S3 bucket name for flow segments
            use_ssl: Whether to use SSL/TLS for connections
        """
        self.endpoint_url = endpoint_url
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.bucket_name = bucket_name
        self.use_ssl = use_ssl
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                use_ssl=use_ssl,
                verify=False  # For self-signed certificates in development
            )
            
            # Ensure bucket exists
            self._ensure_bucket_exists()
            
            logger.info(f"S3 Store initialized with endpoint: {endpoint_url}, bucket: {bucket_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize S3 Store: {e}")
            raise
    
    def _ensure_bucket_exists(self):
        """Ensure the S3 bucket exists, create if it doesn't"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket '{self.bucket_name}' already exists")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket doesn't exist, create it
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                    logger.info(f"Created bucket '{self.bucket_name}'")
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket '{self.bucket_name}': {create_error}")
                    raise
            else:
                logger.error(f"Error checking bucket '{self.bucket_name}': {e}")
                raise
    
    def _generate_segment_key(self, flow_id: str, segment_id: str, timerange: str) -> str:
        """
        Generate S3 object key for flow segment
        
        Args:
            flow_id: Flow identifier
            segment_id: Segment identifier
            timerange: Time range string
            
        Returns:
            S3 object key
        """
        # Parse timerange to extract time information for path structure
        # Format: [start_time:end_time) or [start_time:)
        clean_range = timerange.strip('[]()')
        
        if '_' in clean_range:
            start_str, _ = clean_range.split('_', 1)
        else:
            start_str = clean_range
        
        # Convert to datetime for path structure
        try:
            if ':' in start_str:
                parts = start_str.split(':')
                if len(parts) == 2:
                    seconds = int(parts[0])
                    subseconds = int(parts[1]) if parts[1] else 0
                    start_time = datetime.fromtimestamp(seconds + (subseconds / 1000000000), timezone.utc)
                else:
                    start_time = datetime.now(timezone.utc)
            else:
                start_time = datetime.now(timezone.utc)
        except (ValueError, TypeError):
            start_time = datetime.now(timezone.utc)
        
        # Create hierarchical path structure
        year = start_time.year
        month = start_time.month
        day = start_time.day
        
        # Key format: flow_id/year/month/day/segment_id
        key = f"{flow_id}/{year:04d}/{month:02d}/{day:02d}/{segment_id}"
        
        return key
    
    async def store_flow_segment(self, 
                                flow_id: str, 
                                segment: FlowSegment, 
                                data: Union[bytes, BinaryIO, str],
                                content_type: str = "application/octet-stream") -> bool:
        """
        Store flow segment data in S3
        
        Args:
            flow_id: Flow identifier
            segment: Flow segment object
            data: Segment data (bytes, file-like object, or file path)
            content_type: MIME type of the data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate unique segment ID if not provided
            import uuid as _uuid
            segment_id = segment.object_id if segment.object_id else str(_uuid.uuid4())
            
            # Generate S3 object key
            object_key = self._generate_segment_key(flow_id, segment_id, segment.timerange)
            
            # Prepare metadata
            metadata = {
                'flow_id': flow_id,
                'segment_id': segment_id,
                'timerange': segment.timerange,
                'ts_offset': segment.ts_offset or '',
                'last_duration': segment.last_duration or '',
                'sample_offset': str(segment.sample_offset or 0),
                'sample_count': str(segment.sample_count or 0),
                'key_frame_count': str(segment.key_frame_count or 0),
                'created': datetime.now(timezone.utc).isoformat(),
                'content_type': content_type
            }
            
            # Handle different data types
            if isinstance(data, bytes):
                # Data is already bytes
                data_bytes = data
            elif isinstance(data, str):
                # Data is file path
                with open(data, 'rb') as f:
                    data_bytes = f.read()
            elif hasattr(data, 'read'):
                # Data is file-like object
                data_bytes = data.read()
            else:
                raise ValueError("Data must be bytes, file path, or file-like object")
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=data_bytes,
                ContentType=content_type,
                Metadata=metadata
            )
            
            logger.info(f"Stored flow segment {segment_id} for flow {flow_id} in S3")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store flow segment for flow {flow_id}: {e}")
            return False
    
    async def get_flow_segment_data(self, 
                                   flow_id: str, 
                                   segment_id: str, 
                                   timerange: str) -> Optional[bytes]:
        """
        Retrieve flow segment data from S3
        
        Args:
            flow_id: Flow identifier
            segment_id: Segment identifier
            timerange: Time range string
            
        Returns:
            Segment data as bytes, or None if not found
        """
        try:
            # Generate S3 object key
            object_key = self._generate_segment_key(flow_id, segment_id, timerange)
            
            # Get object from S3
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            # Read data
            data = response['Body'].read()
            
            logger.info(f"Retrieved flow segment {segment_id} for flow {flow_id} from S3")
            return data
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.warning(f"Flow segment {segment_id} for flow {flow_id} not found in S3")
                return None
            else:
                logger.error(f"Failed to retrieve flow segment {segment_id} for flow {flow_id}: {e}")
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve flow segment {segment_id} for flow {flow_id}: {e}")
            return None
    
    async def get_flow_segment_metadata(self, 
                                       flow_id: str, 
                                       segment_id: str, 
                                       timerange: str) -> Optional[Dict[str, Any]]:
        """
        Get flow segment metadata from S3
        
        Args:
            flow_id: Flow identifier
            segment_id: Segment identifier
            timerange: Time range string
            
        Returns:
            Segment metadata dictionary, or None if not found
        """
        try:
            # Generate S3 object key
            object_key = self._generate_segment_key(flow_id, segment_id, timerange)
            
            # Get object metadata from S3
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            # Extract metadata
            metadata = response.get('Metadata', {})
            metadata.update({
                'size': response.get('ContentLength', 0),
                'last_modified': response.get('LastModified'),
                'content_type': response.get('ContentType'),
                'etag': response.get('ETag', '').strip('"')
            })
            
            return metadata
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.warning(f"Flow segment {segment_id} for flow {flow_id} not found in S3")
                return None
            else:
                logger.error(f"Failed to get metadata for flow segment {segment_id}: {e}")
                return None
        except Exception as e:
            logger.error(f"Failed to get metadata for flow segment {segment_id}: {e}")
            return None
    
    async def delete_flow_segment(self, 
                                 flow_id: str, 
                                 segment_id: str, 
                                 timerange: str) -> bool:
        """
        Delete flow segment data from S3
        
        Args:
            flow_id: Flow identifier
            segment_id: Segment identifier
            timerange: Time range string
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate S3 object key
            object_key = self._generate_segment_key(flow_id, segment_id, timerange)
            
            # Delete object from S3
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            logger.info(f"Deleted flow segment {segment_id} for flow {flow_id} from S3")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.warning(f"Flow segment {segment_id} for flow {flow_id} not found in S3")
                return True  # Consider it successful if it doesn't exist
            else:
                logger.error(f"Failed to delete flow segment {segment_id} for flow {flow_id}: {e}")
                return False
        except Exception as e:
            logger.error(f"Failed to delete flow segment {segment_id} for flow {flow_id}: {e}")
            return False
    
    async def list_flow_segments(self, 
                                flow_id: str, 
                                timerange: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List flow segments for a given flow
        
        Args:
            flow_id: Flow identifier
            timerange: Optional time range filter
            
        Returns:
            List of segment metadata dictionaries
        """
        try:
            # List objects with flow_id prefix
            prefix = f"{flow_id}/"
            
            segments = []
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        # Extract segment information from key
                        key = obj['Key']
                        segment_info = self._parse_segment_key(key)
                        
                        if segment_info:
                            # Apply time range filter if specified
                            if timerange and not self._timerange_overlaps(
                                segment_info['timerange'], timerange):
                                continue
                            
                            # Get full metadata
                            metadata = await self.get_flow_segment_metadata(
                                flow_id, 
                                segment_info['segment_id'], 
                                segment_info['timerange']
                            )
                            
                            if metadata:
                                segments.append({
                                    'segment_id': segment_info['segment_id'],
                                    'timerange': segment_info['timerange'],
                                    'key': key,
                                    'size': obj['Size'],
                                    'last_modified': obj['LastModified'],
                                    'metadata': metadata
                                })
            
            return segments
            
        except Exception as e:
            logger.error(f"Failed to list flow segments for flow {flow_id}: {e}")
            return []
    
    def _parse_segment_key(self, key: str) -> Optional[Dict[str, str]]:
        """
        Parse S3 object key to extract segment information
        
        Args:
            key: S3 object key
            
        Returns:
            Dictionary with segment_id and timerange, or None if invalid
        """
        try:
            # Key format: flow_id/year/month/day/segment_id
            parts = key.split('/')
            if len(parts) >= 5:
                segment_id = parts[-1]  # Last part is segment_id
                
                # Try to reconstruct timerange from metadata or use default
                # This is a simplified approach - in practice, timerange would be stored in metadata
                timerange = "[0:0)"  # Default timerange
                
                return {
                    'segment_id': segment_id,
                    'timerange': timerange
                }
        except Exception as e:
            logger.warning(f"Failed to parse segment key {key}: {e}")
        
        return None
    
    def _timerange_overlaps(self, range1: str, range2: str) -> bool:
        """
        Check if two time ranges overlap
        
        Args:
            range1: First time range
            range2: Second time range
            
        Returns:
            True if ranges overlap, False otherwise
        """
        # Simplified overlap check - in practice, this would parse and compare time ranges
        # For now, assume they overlap if they're not empty
        return bool(range1.strip('[]()') and range2.strip('[]()'))
    
    async def generate_presigned_url(self, 
                                    flow_id: str, 
                                    segment_id: str, 
                                    timerange: str,
                                    operation: str = 'get_object',
                                    expires_in: int = 3600) -> Optional[str]:
        """
        Generate presigned URL for S3 operations
        
        Args:
            flow_id: Flow identifier
            segment_id: Segment identifier
            timerange: Time range string
            operation: S3 operation ('get_object', 'put_object', 'delete_object')
            expires_in: URL expiration time in seconds
            
        Returns:
            Presigned URL, or None if failed
        """
        try:
            # Generate S3 object key
            object_key = self._generate_segment_key(flow_id, segment_id, timerange)
            
            # Generate presigned URL
            url = self.s3_client.generate_presigned_url(
                operation,
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key
                },
                ExpiresIn=expires_in
            )
            
            logger.info(f"Generated presigned URL for {operation} on segment {segment_id}")
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for segment {segment_id}: {e}")
            return None
    
    async def create_get_urls(self, 
                             flow_id: str, 
                             segment_id: str, 
                             timerange: str) -> List[GetUrl]:
        """
        Create GetUrl objects for flow segment access
        
        Args:
            flow_id: Flow identifier
            segment_id: Segment identifier
            timerange: Time range string
            
        Returns:
            List of GetUrl objects
        """
        try:
            # Generate presigned URL for direct access
            presigned_url = await self.generate_presigned_url(
                flow_id, segment_id, timerange, 'get_object'
            )
            
            if presigned_url:
                return [
                    GetUrl(
                        url=presigned_url,
                        method="GET",
                        headers={},
                        expires=datetime.now(timezone.utc) + timedelta(hours=1)
                    )
                ]
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to create GetUrls for segment {segment_id}: {e}")
            return []
    
    async def get_bucket_stats(self) -> Dict[str, Any]:
        """
        Get S3 bucket statistics
        
        Returns:
            Dictionary with bucket statistics
        """
        try:
            # Get bucket size and object count
            total_size = 0
            object_count = 0
            
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self.bucket_name):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        total_size += obj['Size']
                        object_count += 1
            
            return {
                'bucket_name': self.bucket_name,
                'total_size_bytes': total_size,
                'object_count': object_count,
                'average_object_size': total_size / object_count if object_count > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get bucket stats: {e}")
            return {'error': str(e)}
    
    async def close(self):
        """Close S3 store and cleanup resources"""
        logger.info("Closing S3 store")
        # S3 client doesn't require explicit cleanup 