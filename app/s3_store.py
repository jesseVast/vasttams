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
from botocore.exceptions import ClientError

from .models import FlowSegment, GetUrl
from .config import get_settings

logger = logging.getLogger(__name__)


class S3Store:
    """
    S3 Store for TAMS Flow Segments
    
    This class provides a high-level interface to S3 for storing and retrieving
    flow segment data. Flow segments contain the actual media content and are
    stored as objects in S3 buckets.
    """
    
    def __init__(self, endpoint_url=None, access_key_id=None, secret_access_key=None, bucket_name=None, use_ssl=None):
        """Initialize S3 Store using provided config or config.py"""
        if any(param is not None for param in [endpoint_url, access_key_id, secret_access_key, bucket_name, use_ssl]):
            self.endpoint_url = endpoint_url
            self.access_key_id = access_key_id
            self.secret_access_key = secret_access_key
            self.bucket_name = bucket_name
            self.use_ssl = use_ssl
        else:
            settings = get_settings()
            self.endpoint_url = settings.s3_endpoint_url
            self.access_key_id = settings.s3_access_key_id
            self.secret_access_key = settings.s3_secret_access_key
            self.bucket_name = settings.s3_bucket_name
            self.use_ssl = settings.s3_use_ssl
        # Initialize S3 client
        try:
            self.s3_client = boto3.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                use_ssl=self.use_ssl,
                verify=False
            )
            self._ensure_bucket_exists()
            logger.info(f"S3 Store initialized with endpoint: {self.endpoint_url}, bucket: {self.bucket_name}")
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
            segment_id = segment.object_id if segment.object_id else str(uuid.uuid4())
            
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
                        label=f"Direct access for segment {segment_id}"
                    )
                ]
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to create GetUrls for segment {segment_id}: {e}")
            return []
    
    async def close(self):
        """Close S3 store and cleanup resources"""
        logger.info("Closing S3 store")
        # S3 client doesn't require explicit cleanup 