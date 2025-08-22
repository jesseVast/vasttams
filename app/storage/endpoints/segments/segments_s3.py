"""
TAMS-specific S3 operations for segments

This module handles TAMS-specific S3 operations for flow segments including:
- Segment media storage and retrieval
- TAMS-compliant get_urls generation
- Segment-specific S3 key management
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid

from ...core.s3_core import S3Core
from ...storage_backend_manager import StorageBackendManager
from ....models.models import FlowSegment, GetUrl

logger = logging.getLogger(__name__)


class SegmentsS3:
    """
    TAMS-specific S3 operations for segments
    
    This class handles TAMS-specific S3 operations for flow segments,
    including media storage and TAMS-compliant get_urls generation.
    """
    
    def __init__(self, s3_core: S3Core, storage_backend_manager: StorageBackendManager):
        """
        Initialize segments S3 handler
        
        Args:
            s3_core: Core S3 operations
            storage_backend_manager: Storage backend manager for TAMS compliance
        """
        self.s3 = s3_core
        self.storage_backend_manager = storage_backend_manager
        
        logger.info("SegmentsS3 initialized")
    
    async def store_segment(self, segment: FlowSegment, data: bytes) -> bool:
        """
        Store segment media data in S3
        
        Args:
            segment: FlowSegment model instance
            data: Media data bytes
            
        Returns:
            bool: True if storage successful, False otherwise
        """
        try:
            logger.info("Storing segment media in S3: %s (%d bytes)", segment.object_id, len(data))
            
            # Generate S3 key for segment
            key = self._generate_segment_key(segment)
            
            # Store media data
            success = self.s3.upload_object(
                key=key,
                data=data,
                content_type="application/octet-stream"
            )
            
            if success:
                logger.info("Successfully stored segment media in S3: %s", segment.object_id)
            else:
                logger.error("Failed to store segment media in S3: %s", segment.object_id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to store segment media for %s: %s", segment.object_id, e)
            return False
    
    async def retrieve_segment(self, segment: FlowSegment) -> Optional[bytes]:
        """
        Retrieve segment media data from S3
        
        Args:
            segment: FlowSegment model instance
            
        Returns:
            bytes: Media data or None if failed
        """
        try:
            logger.info("Retrieving segment media from S3: %s", segment.object_id)
            
            # Generate S3 key for segment
            key = self._generate_segment_key(segment)
            
            # Retrieve media data
            data = self.s3.download_object(key)
            
            if data is not None:
                logger.info("Successfully retrieved segment media from S3: %s (%d bytes)", 
                           segment.object_id, len(data))
            else:
                logger.error("Failed to retrieve segment media from S3: %s", segment.object_id)
            
            return data
            
        except Exception as e:
            logger.error("Failed to retrieve segment media for %s: %s", segment.object_id, e)
            return None
    
    async def delete_segment(self, segment: FlowSegment) -> bool:
        """
        Delete segment media data from S3
        
        Args:
            segment: FlowSegment model instance
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            logger.info("Deleting segment media from S3: %s", segment.object_id)
            
            # Generate S3 key for segment
            key = self._generate_segment_key(segment)
            
            # Delete media data
            success = self.s3.delete_object(key)
            
            if success:
                logger.info("Successfully deleted segment media from S3: %s", segment.object_id)
            else:
                logger.error("Failed to delete segment media from S3: %s", segment.object_id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to delete segment media for %s: %s", segment.object_id, e)
            return False
    
    async def generate_get_urls(self, segment: FlowSegment) -> List[GetUrl]:
        """
        Generate TAMS-compliant get_urls for a segment
        Since presigned URLs expire, we generate them dynamically on each request
        """
        try:
            logger.info("Generating TAMS-compliant get_urls for segment: %s", segment.object_id)
            
            # Use stored storage_path if available, otherwise generate key
            key = segment.storage_path if segment.storage_path else self._generate_segment_key(segment)
            logger.info("Using S3 key for segment %s: %s", segment.object_id, key)
            
            # Get storage backend information for TAMS compliance
            storage_backend = self.storage_backend_manager.get_storage_backend_info("default")
            logger.info("Storage backend info: %s", storage_backend)
            
            # Generate dynamic presigned URL for download (expires in 1 hour)
            logger.info("Generating presigned URL for key: %s", key)
            presigned_url = self.s3.generate_presigned_url(
                key=key,
                operation="get_object",
                expires=3600  # 1 hour expiration
            )
            logger.info("Presigned URL result: %s", presigned_url)
            
            if not presigned_url:
                logger.error("Failed to generate presigned URL for segment %s", segment.object_id)
                return []
            
            # Create TAMS-compliant GetUrl object
            get_url = GetUrl(
                store_type="http_object_store",
                provider=storage_backend.get("provider", "unknown"),
                region=storage_backend.get("region", "unknown"),
                availability_zone=storage_backend.get("availability_zone"),
                store_product=storage_backend.get("store_product", "unknown"),
                url=presigned_url,
                storage_id=storage_backend.get("id", "default"),
                presigned=True,
                label="default",
                controlled=True
            )
            
            logger.info("Generated get_url for segment %s: %s", segment.object_id, presigned_url)
            return [get_url]
            
        except Exception as e:
            logger.error("Error generating get_urls for segment %s: %s", segment.object_id, e)
            import traceback
            logger.error("Traceback: %s", traceback.format_exc())
            return []
    
    def _generate_segment_key(self, segment: FlowSegment) -> str:
        """
        Generate S3 key for segment storage using TAMS path format
        Format: {tams_storage_path}/{year}/{month}/{date}/{object_id}
        """
        from datetime import datetime
        from app.core.config import get_settings
        
        # Get current date for TAMS path organization
        now = datetime.now()
        year = str(now.year)
        month = f"{now.month:02d}"
        date = f"{now.day:02d}"
        
        # Generate TAMS-compliant storage path
        settings = get_settings()
        tams_path = f"{settings.tams_storage_path}/{year}/{month}/{date}/{segment.object_id}"
        
        logger.info("Generated TAMS storage path: %s for segment: %s", tams_path, segment.object_id)
        return tams_path
    
    def segment_exists(self, segment: FlowSegment) -> bool:
        """
        Check if segment media exists in S3
        
        Args:
            segment: FlowSegment model instance
            
        Returns:
            bool: True if segment exists, False otherwise
        """
        try:
            key = self._generate_segment_key(segment)
            return self.s3.object_exists(key)
            
        except Exception as e:
            logger.error("Failed to check segment existence for %s: %s", segment.object_id, e)
            return False
    
    def get_segment_metadata(self, segment: FlowSegment) -> Optional[Dict[str, Any]]:
        """
        Get segment media metadata from S3
        
        Args:
            segment: FlowSegment model instance
            
        Returns:
            Dict: Segment metadata or None if failed
        """
        try:
            key = self._generate_segment_key(segment)
            return self.s3.get_object_metadata(key)
            
        except Exception as e:
            logger.error("Failed to get segment metadata for %s: %s", segment.object_id, e)
            return None
    
    def copy_segment(self, source_segment: FlowSegment, destination_segment: FlowSegment) -> bool:
        """
        Copy segment media data within S3
        
        Args:
            source_segment: Source FlowSegment model instance
            destination_segment: Destination FlowSegment model instance
            
        Returns:
            bool: True if copy successful, False otherwise
        """
        try:
            logger.info("Copying segment media from %s to %s", source_segment.object_id, destination_segment.object_id)
            
            source_key = self._generate_segment_key(source_segment)
            destination_key = self._generate_segment_key(destination_segment)
            
            success = self.s3.copy_object(source_key, destination_key)
            
            if success:
                logger.info("Successfully copied segment media from %s to %s", 
                           source_segment.object_id, destination_segment.object_id)
            else:
                logger.error("Failed to copy segment media from %s to %s", 
                           source_segment.object_id, destination_segment.object_id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to copy segment media from %s to %s: %s", 
                       source_segment.object_id, destination_segment.object_id, e)
            return False
    
    def list_segments_by_prefix(self, prefix: str = "segments/") -> List[str]:
        """
        List segment keys by prefix
        
        Args:
            prefix: Key prefix to filter by
            
        Returns:
            List[str]: List of segment keys
        """
        try:
            return self.s3.list_objects(prefix=prefix)
            
        except Exception as e:
            logger.error("Failed to list segments by prefix '%s': %s", prefix, e)
            return []
    
    def get_segment_size(self, segment: FlowSegment) -> Optional[int]:
        """
        Get segment media size from S3
        
        Args:
            segment: FlowSegment model instance
            
        Returns:
            int: Segment size in bytes or None if failed
        """
        try:
            metadata = self.get_segment_metadata(segment)
            if metadata:
                return metadata.get('content_length')
            return None
            
        except Exception as e:
            logger.error("Failed to get segment size for %s: %s", segment.object_id, e)
            return None
