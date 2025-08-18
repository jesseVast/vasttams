"""S3 storage backend for TAMS application"""

import boto3
import logging
from typing import Optional, Dict, Any, List, BinaryIO, Union
from botocore.exceptions import ClientError, NoCredentialsError
import json
import uuid
from datetime import datetime, timedelta, timezone

# Configuration Constants - Easy to adjust for troubleshooting
DEFAULT_S3_TIMEOUT = 30  # Default S3 operation timeout in seconds
DEFAULT_PRESIGNED_URL_TIMEOUT = 3600  # Default presigned URL expiration time in seconds (matches config.py)
DEFAULT_MAX_RETRIES = 3  # Default maximum retry attempts for S3 operations
DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024  # Default chunk size for multipart uploads (8MB)
DEFAULT_MAX_CONCURRENT_PARTS = 10  # Default maximum concurrent parts for multipart uploads
EXPECTED_PARTS_LENGTH = 2  # Expected number of parts for key parsing

from ..models.models import FlowSegment, GetUrl
from ..core.config import get_settings
from .storage_backend_manager import StorageBackendManager

logger = logging.getLogger(__name__)


class S3Store:
    """
    S3 Store for TAMS Flow Segments
    
    This class provides a high-level interface to S3 for storing and retrieving
    flow segment data. Flow segments contain the actual media content and are
    stored as objects in S3 buckets.
    """
    
    def __init__(self, endpoint_url=None, access_key_id=None, secret_access_key=None, bucket_name=None, use_ssl=None, storage_backend_manager=None):
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
        
        # Initialize storage backend manager
        self.storage_backend_manager = storage_backend_manager or StorageBackendManager()
        
        logger.info("S3Store initialization - Endpoint: %s, Bucket: %s, Access Key: %s", 
                   self.endpoint_url, self.bucket_name, self.access_key_id)
        
        # Initialize S3 client using VastS3 approach
        try:
            session = boto3.session.Session()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Created boto3 session: %s", session)
            
            self.s3_client = session.client(
                service_name='s3',
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                endpoint_url=self.endpoint_url
            )
            logger.info(f"Created S3 client: {self.s3_client}")
            
            self._ensure_bucket_exists()
            logger.info(f"S3 Store initialized with endpoint: {self.endpoint_url}, bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize S3 Store: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
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
                if len(parts) == EXPECTED_PARTS_LENGTH:
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
    
    def generate_segment_key(self, flow_id: str, segment_id: str, timerange: str) -> str:
        """
        Public method to generate S3 object key for flow segment
        
        Args:
            flow_id: Flow identifier
            segment_id: Segment identifier
            timerange: Time range string
            
        Returns:
            S3 object key string
        """
        return self._generate_segment_key(flow_id, segment_id, timerange)
    
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
            
            # Upload to S3 with absolute minimal headers for MinIO compatibility
            put_kwargs = {
                'Bucket': self.bucket_name,
                'Key': object_key,
                'Body': data_bytes
            }
            
            # Only add content type if it's not the default
            if content_type != "application/octet-stream":
                put_kwargs['ContentType'] = content_type
            
            # Only add metadata if it's not empty
            if metadata:
                put_kwargs['Metadata'] = metadata
            
            self.s3_client.put_object(**put_kwargs)
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
    
    def delete_object(self, storage_path: str) -> bool:
        """
        Delete an object from S3 by its storage path
        
        Args:
            storage_path: The storage path/key of the object to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete object from S3 using the storage path directly as the key
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=storage_path
            )
            
            logger.info(f"Deleted S3 object: {storage_path}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.warning(f"S3 object not found: {storage_path}")
                return True  # Consider it successful if it doesn't exist
            else:
                logger.error(f"Failed to delete S3 object {storage_path}: {e}")
                return False
        except Exception as e:
            logger.error(f"Failed to delete S3 object {storage_path}: {e}")
            return False
    
    def generate_presigned_url(self, 
                              flow_id: str,
                              segment_id: str,
                              timerange: str,
                              operation: str = 'get_object',
                              expires_in: int = None) -> Optional[str]:
        """
        Generate presigned URL for S3 operations
        
        Args:
            flow_id: Flow identifier
            segment_id: Segment identifier
            timerange: Time range string
            operation: S3 operation ('get_object', 'put_object', 'delete_object')
            expires_in: URL expiration time in seconds (uses config if None)
            
        Returns:
            Presigned URL, or None if failed
        """
        # Use configurable timeout from settings, fallback to configured default
        if expires_in is None:
            try:
                settings = get_settings()
                expires_in = settings.s3_presigned_url_timeout
            except Exception:
                expires_in = DEFAULT_PRESIGNED_URL_TIMEOUT  # Fallback to configured default
        
        logger.info(f"generate_presigned_url called with flow_id={flow_id}, segment_id={segment_id}, timerange={timerange}, operation={operation}, expires_in={expires_in}")
        logger.info(f"S3Store state - endpoint_url: {self.endpoint_url}, bucket_name: {self.bucket_name}, s3_client: {self.s3_client}")
        
        try:
            # Generate S3 object key for the flow segment
            object_key = self._generate_segment_key(flow_id, segment_id, timerange)
            logger.info(f"Generated object key: {object_key}")
            
            # Generate presigned URL for the object
            url = self.s3_client.generate_presigned_url(
                operation,
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key
                },
                ExpiresIn=expires_in
            )
            
            logger.info(f"Generated presigned URL: {url}")
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for flow {flow_id}, segment {segment_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def generate_object_presigned_url(self, 
                                    object_id: str, 
                                    operation: str, 
                                    expires_in: Optional[int] = None,
                                    custom_key: Optional[str] = None) -> Optional[str]:
        """
        Generate a presigned URL for S3 object operations
        
        Args:
            object_id: Object identifier
            operation: S3 operation ('get_object', 'put_object', 'delete_object')
            expires_in: URL expiration time in seconds (uses config if None)
            custom_key: Optional custom S3 object key to use instead of object_id
            
        Returns:
            Presigned URL, or None if failed
        """
        # Use configurable timeout from settings, fallback to configured default
        if expires_in is None:
            try:
                settings = get_settings()
                # Use appropriate timeout based on operation
                if operation == 'put_object':
                    expires_in = settings.s3_presigned_url_upload_timeout
                else:
                    expires_in = settings.s3_presigned_url_download_timeout
            except Exception:
                # Fallback to appropriate default based on operation
                if operation == 'put_object':
                    expires_in = 3600  # 1 hour for uploads
                else:
                    expires_in = 3600  # 1 hour for downloads
        
        logger.info(f"generate_object_presigned_url called with object_id={object_id}, operation={operation}, expires_in={expires_in}, custom_key={custom_key}")
        logger.info(f"S3Store state - endpoint_url: {self.endpoint_url}, bucket_name: {self.bucket_name}, s3_client: {self.s3_client}")
        
        try:
            # Use custom_key if provided, otherwise use object_id
            s3_key = custom_key if custom_key else object_id
            logger.info(f"Using S3 key: {s3_key}")
            
            # Generate presigned URL for the S3 key
            url = self.s3_client.generate_presigned_url(
                operation,
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expires_in
            )
            
            logger.info(f"Generated presigned URL: {url}")
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for object {object_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    async def create_get_urls(self, 
                             flow_id: str, 
                             segment_id: str, 
                             timerange: str,
                             storage_path: Optional[str] = None) -> List[GetUrl]:
        """
        Create GetUrl objects for flow segment access (Legacy method - kept for backward compatibility)
        
        Args:
            flow_id: Flow identifier
            segment_id: Segment identifier
            timerange: Time range string
            storage_path: Optional storage path to use instead of regenerating
            
        Returns:
            List of GetUrl objects
        """
        try:
            # Use provided storage_path if available, otherwise generate from parameters
            if storage_path:
                object_key = storage_path
                logger.info(f"Using provided storage path: {object_key}")
            else:
                # Fallback to generating path (for backward compatibility)
                object_key = self._generate_segment_key(flow_id, segment_id, timerange)
                logger.info(f"Generated fallback path: {object_key}")
            
            # Generate presigned URL for the object key
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key
                },
                ExpiresIn=DEFAULT_PRESIGNED_URL_TIMEOUT
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

    async def create_tams_compliant_get_urls(
        self, 
        flow_id: str, 
        segment_id: str, 
        timerange: str,
        storage_path: Optional[str] = None,
        storage_backend_id: str = None
    ) -> List[GetUrl]:
        """
        Create TAMS-compliant GetUrl objects with dynamic URL generation
        
        Args:
            flow_id: Flow identifier
            segment_id: Segment identifier
            timerange: Time range string
            storage_path: Optional storage path to use instead of regenerating
            storage_backend_id: Storage backend ID to use (defaults to config default)
            
        Returns:
            List of TAMS-compliant GetUrl objects
        """
        try:
            # Get storage backend metadata
            if storage_backend_id is None:
                settings = get_settings()
                storage_backend_id = settings.default_storage_backend_id
            
            backend_info = self.storage_backend_manager.get_storage_backend_info(storage_backend_id)
            
            # Use provided storage_path if available, otherwise generate from parameters
            if storage_path:
                object_key = storage_path
                logger.info(f"Using provided storage path: {object_key}")
            else:
                # Generate path from parameters
                object_key = self._generate_segment_key(flow_id, segment_id, timerange)
                logger.info(f"Generated storage path: {object_key}")
            
            # Generate presigned URL for the object key using download timeout
            settings = get_settings()
            expires_in = settings.s3_presigned_url_download_timeout
            
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key
                },
                ExpiresIn=expires_in
            )
            
            if presigned_url:
                # Create TAMS-compliant GetUrl object
                get_url = GetUrl(
                    # Storage backend fields from storage-backend.json
                    store_type=backend_info.get("store_type", "http_object_store"),
                    provider=backend_info.get("provider", "S3-Compatible"),
                    region=backend_info.get("region", "default"),
                    availability_zone=backend_info.get("availability_zone"),
                    store_product=backend_info.get("store_product", "S3-Compatible Storage"),
                    
                    # Dynamic fields
                    url=presigned_url,
                    storage_id=storage_backend_id,
                    presigned=True,
                    label=f"Direct access for segment {segment_id}",
                    controlled=True
                )
                
                logger.info(f"Created TAMS-compliant GetUrl for segment {segment_id}")
                return [get_url]
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to create TAMS-compliant GetUrls for segment {segment_id}: {e}")
            return []
    
    async def close(self):
        """Close S3 store and cleanup resources"""
        logger.info("Closing S3 store")
        # S3 client doesn't require explicit cleanup 