"""
Simplified S3 Store Orchestrator for TAMS Application

This module is now a simplified orchestrator that delegates S3 operations
to specialized modules. It maintains backward compatibility while using
the new modular architecture.
"""

import logging
from typing import Optional, Dict, Any, List, BinaryIO, Union
from datetime import datetime, timedelta, timezone

from ..models.models import FlowSegment, GetUrl
from ..core.config import get_settings
from .storage_backend_manager import StorageBackendManager
from .core.s3_core import S3Core
from .endpoints.segments.segments_s3 import SegmentsS3

logger = logging.getLogger(__name__)


class S3Store:
    """
    Simplified S3 Store Orchestrator for TAMS Flow Segments
    
    This class now acts as an orchestrator that delegates operations to
    specialized modules. It maintains backward compatibility while using
    the new modular architecture.
    """
    
    def __init__(self, endpoint_url=None, access_key_id=None, secret_access_key=None, 
                 bucket_name=None, use_ssl=None, storage_backend_manager=None):
        """Initialize S3 Store using provided config or config.py"""
        # Initialize storage backend manager
        self.storage_backend_manager = storage_backend_manager or StorageBackendManager()
        
        # Get configuration
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
            self.use_ssl = getattr(settings, 's3_use_ssl', True)
        
        # Initialize core S3 component
        self.s3_core = S3Core(
            endpoint_url=self.endpoint_url,
            access_key_id=self.access_key_id,
            secret_access_key=self.secret_access_key,
            bucket_name=self.bucket_name,
            use_ssl=self.use_ssl
        )
        
        # Initialize specialized endpoint modules
        self.segments_s3 = SegmentsS3(self.s3_core, self.storage_backend_manager)
        
        logger.info("S3Store orchestrator initialized - Endpoint: %s, Bucket: %s", 
                   self.endpoint_url, self.bucket_name)
    
    def _ensure_bucket_exists(self):
        """Ensure the S3 bucket exists - delegated to S3Core"""
        # This is now handled by S3Core during initialization
        pass
    
    def _generate_segment_key(self, flow_id: str, segment_id: str, timerange: str) -> str:
        """
        Generate segment key - delegated to SegmentsS3
        
        Args:
            flow_id: Flow ID
            segment_id: Segment ID
            timerange: Timerange string
            
        Returns:
            str: Generated S3 key
        """
        # Create a temporary segment object for key generation
        temp_segment = FlowSegment(
            id=segment_id,
            object_id=f"temp_{segment_id}",
            timerange=timerange
        )
        
        # Delegate to SegmentsS3 for key generation
        return self.segments_s3._generate_segment_key(temp_segment)
    
    def generate_segment_key(self, flow_id: str, segment_id: str, timerange: str) -> str:
        """
        Generate segment key - delegated to SegmentsS3
        
        Args:
            flow_id: Flow ID
            segment_id: Segment ID
            timerange: Timerange string
            
        Returns:
            str: Generated S3 key
        """
        return self._generate_segment_key(flow_id, segment_id, timerange)
    
    def delete_object(self, storage_path: str) -> bool:
        """
        Delete object from S3 - delegated to S3Core
        
        Args:
            storage_path: S3 object key
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        return self.s3_core.delete_object(storage_path)
    
    def generate_presigned_url(self, storage_path: str, operation: str = "get_object", 
                              expires: int = 3600) -> Optional[str]:
        """
        Generate presigned URL - delegated to S3Core
        
        Args:
            storage_path: S3 object key
            operation: S3 operation
            expires: URL expiration time
            
        Returns:
            str: Presigned URL or None if failed
        """
        return self.s3_core.generate_presigned_url(storage_path, operation, expires)
    
    def generate_object_presigned_url(self, storage_path: str, operation: str = "get_object", 
                                    expires: int = 3600) -> Optional[str]:
        """
        Generate object presigned URL - delegated to S3Core
        
        Args:
            storage_path: S3 object key
            operation: S3 operation
            expires: URL expiration time
            
        Returns:
            str: Presigned URL or None if failed
        """
        return self.s3_core.generate_presigned_url(storage_path, operation, expires)
    
    # Legacy methods for backward compatibility
    def create_get_urls(self, segment: FlowSegment) -> List[GetUrl]:
        """
        Create get_urls for segment - delegated to SegmentsS3
        
        Args:
            segment: FlowSegment model instance
            
        Returns:
            List[GetUrl]: List of get_urls
        """
        # This is now async, but we maintain sync interface for backward compatibility
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, we can't use run_until_complete
                # Return empty list for now - this should be updated to use async interface
                logger.warning("create_get_urls called in async context - returning empty list")
                return []
            else:
                return loop.run_until_complete(self.segments_s3.generate_get_urls(segment))
        except RuntimeError:
            # No event loop available
            logger.warning("No event loop available for create_get_urls - returning empty list")
            return []
    
    def create_tams_compliant_get_urls(self, segment: FlowSegment) -> List[GetUrl]:
        """
        Create TAMS-compliant get_urls for segment - delegated to SegmentsS3
        
        Args:
            segment: FlowSegment model instance
            
        Returns:
            List[GetUrl]: List of TAMS-compliant get_urls
        """
        return self.create_get_urls(segment)
    
    # Health check and diagnostic methods
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on S3 storage
        
        Returns:
            Dict: Health check results
        """
        try:
            bucket_info = self.s3_core.get_bucket_info()
            return {
                'status': 'healthy' if bucket_info.get('exists') else 'unhealthy',
                'bucket_info': bucket_info,
                'endpoint': self.endpoint_url,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'endpoint': self.endpoint_url,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get storage information
        
        Returns:
            Dict: Storage information
        """
        try:
            bucket_info = self.s3_core.get_bucket_info()
            return {
                'type': 's3',
                'endpoint': self.endpoint_url,
                'bucket': self.bucket_name,
                'bucket_info': bucket_info,
                'storage_backend_manager': self.storage_backend_manager.get_default_backend()
            }
        except Exception as e:
            return {
                'type': 's3',
                'endpoint': self.endpoint_url,
                'bucket': self.bucket_name,
                'error': str(e)
            } 