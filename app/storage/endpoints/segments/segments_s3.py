"""
TAMS-specific S3 operations for segments

This module handles TAMS-specific S3 operations for flow segments including:
- Segment media storage and retrieval
- TAMS-compliant get_urls generation
- Segment-specific S3 key management
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
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
            logger.info("Storing segment media in S3: %s (%d bytes)", segment.id, len(data))
            
            # Generate S3 key for segment
            key = self._generate_segment_key(segment)
            
            # Store media data
            success = self.s3.upload_object(
                key=key,
                data=data,
                content_type="application/octet-stream"
            )
            
            if success:
                logger.info("Successfully stored segment media in S3: %s", segment.id)
            else:
                logger.error("Failed to store segment media in S3: %s", segment.id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to store segment media for %s: %s", segment.id, e)
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
            logger.info("Retrieving segment media from S3: %s", segment.id)
            
            # Generate S3 key for segment
            key = self._generate_segment_key(segment)
            
            # Retrieve media data
            data = self.s3.download_object(key)
            
            if data is not None:
                logger.info("Successfully retrieved segment media from S3: %s (%d bytes)", 
                           segment.id, len(data))
            else:
                logger.error("Failed to retrieve segment media from S3: %s", segment.id)
            
            return data
            
        except Exception as e:
            logger.error("Failed to retrieve segment media for %s: %s", segment.id, e)
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
            logger.info("Deleting segment media from S3: %s", segment.id)
            
            # Generate S3 key for segment
            key = self._generate_segment_key(segment)
            
            # Delete media data
            success = self.s3.delete_object(key)
            
            if success:
                logger.info("Successfully deleted segment media from S3: %s", segment.id)
            else:
                logger.error("Failed to delete segment media from S3: %s", segment.id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to delete segment media for %s: %s", segment.id, e)
            return False
    
    async def generate_get_urls(self, segment: FlowSegment) -> List[GetUrl]:
        """
        Generate TAMS-compliant get_urls for a segment
        
        Args:
            segment: FlowSegment model instance
            
        Returns:
            List[GetUrl]: List of TAMS-compliant get_urls
        """
        try:
            logger.info("Generating TAMS-compliant get_urls for segment: %s", segment.id)
            
            # Generate S3 key for segment
            key = self._generate_segment_key(segment)
            
            # Get storage backend information for TAMS compliance
            storage_backend = self.storage_backend_manager.get_default_backend()
            
            # Generate presigned URL for download
            presigned_url = self.s3.generate_presigned_url(
                key=key,
                operation="get_object",
                expires=3600  # 1 hour expiration
            )
            
            if not presigned_url:
                logger.error("Failed to generate presigned URL for segment: %s", segment.id)
                return []
            
            # Create TAMS-compliant GetUrl
            get_url = GetUrl(
                store_type="http_object_store",
                provider=storage_backend.get('provider', 'unknown'),
                region=storage_backend.get('region', 'unknown'),
                availability_zone=storage_backend.get('availability_zone'),
                store_product=storage_backend.get('store_product', 'unknown'),
                url=presigned_url,
                storage_id=storage_backend.get('id', 'default'),
                presigned=True,
                label="default",
                controlled=True
            )
            
            logger.info("Generated TAMS-compliant get_urls for segment: %s", segment.id)
            return [get_url]
            
        except Exception as e:
            logger.error("Failed to generate get_urls for segment %s: %s", segment.id, e)
            return []
    
    def _generate_segment_key(self, segment: FlowSegment) -> str:
        """
        Generate S3 key for segment storage
        
        Args:
            segment: FlowSegment model instance
            
        Returns:
            str: S3 key for segment storage
        """
        try:
            # Extract flow_id from segment context
            # This assumes the segment has flow_id context available
            # In practice, you might need to pass this separately
            
            # For now, use a simple key format
            # TODO: Implement proper key generation based on TAMS requirements
            key = f"segments/{segment.id}/{segment.object_id}"
            
            logger.debug("Generated S3 key for segment %s: %s", segment.id, key)
            return key
            
        except Exception as e:
            logger.error("Failed to generate S3 key for segment %s: %s", segment.id, e)
            # Fallback key
            return f"segments/{segment.id}/fallback"
    
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
            logger.error("Failed to check segment existence for %s: %s", segment.id, e)
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
            logger.error("Failed to get segment metadata for %s: %s", segment.id, e)
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
            logger.info("Copying segment media from %s to %s", source_segment.id, destination_segment.id)
            
            source_key = self._generate_segment_key(source_segment)
            destination_key = self._generate_segment_key(destination_segment)
            
            success = self.s3.copy_object(source_key, destination_key)
            
            if success:
                logger.info("Successfully copied segment media from %s to %s", 
                           source_segment.id, destination_segment.id)
            else:
                logger.error("Failed to copy segment media from %s to %s", 
                            source_segment.id, destination_segment.id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to copy segment media from %s to %s: %s", 
                        source_segment.id, destination_segment.id, e)
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
            logger.error("Failed to get segment size for %s: %s", segment.id, e)
            return None
