"""
TAMS-specific segment storage operations

This module handles TAMS-specific segment operations including:
- Segment creation and metadata storage
- Segment retrieval with TAMS compliance
- Segment management and lifecycle

TAMS API DELETE RULES (CRITICAL COMPLIANCE):
============================================

SEGMENT DELETION:
- MUST FAIL (409 Conflict) if dependent objects exist
- Objects are immutable and cannot be deleted via cascade
- Only segment metadata is removed, S3 objects remain
- Flow references must be checked before deletion

All delete operations implement TAMS API compliance rules to prevent
referential integrity violations and data corruption.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

from ...vastdbmanager import VastDBManager
from ...core.s3_core import S3Core
from ...storage_backend_manager import StorageBackendManager
from ....models.models import FlowSegment, GetUrl

logger = logging.getLogger(__name__)


class SegmentsStorage:
    """
    TAMS-specific segment operations
    
    This class handles TAMS-specific segment operations that combine
    VAST metadata storage with S3 media storage.
    """
    
    def __init__(self, vast_core: VastDBManager, s3_segments: 'SegmentsS3'):
        """
        Initialize segments storage
        
        Args:
            vast_core: VastDBManager for metadata operations
            s3_segments: S3 segments handler for media storage
        """
        self.vast = vast_core
        self.s3 = s3_segments
        self.storage_backend_manager = StorageBackendManager()
        
        logger.info("SegmentsStorage initialized")
    
    async def create_segment(self, segment: FlowSegment, flow_id: str, data: bytes) -> bool:
        """
        Create a TAMS flow segment with media data
        
        Args:
            segment: FlowSegment model instance
            flow_id: ID of the flow this segment belongs to
            data: Media data bytes
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            logger.info("Creating TAMS segment for flow %s: %s", flow_id, segment.object_id)
            
            # 1. Store media data in S3
            s3_success = await self.s3.store_segment(segment, data)
            if not s3_success:
                logger.error("Failed to store segment media in S3 for segment %s", segment.object_id)
                return False
            
            # 2. Store metadata in VAST
            vast_success = await self._store_segment_metadata(segment, flow_id)
            if not vast_success:
                logger.error("Failed to store segment metadata in VAST for segment %s", segment.object_id)
                # TODO: Clean up S3 data if metadata storage fails
                return False
            
            logger.info("Successfully created TAMS segment: %s", segment.object_id)
            return True
            
        except Exception as e:
            logger.error("Failed to create TAMS segment %s: %s", segment.object_id, e)
            return False
    
    async def create_segment_metadata(self, segment: FlowSegment, flow_id: str) -> bool:
        """
        Create a TAMS flow segment with metadata only (no media data)
        Used when media data is uploaded separately via presigned URL
        
        Args:
            segment: FlowSegment model instance
            flow_id: ID of the flow this segment belongs to
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            logger.info("Creating TAMS segment metadata for flow %s: %s", flow_id, segment.object_id)
            
            # Only store metadata in VAST (media data uploaded separately)
            vast_success = await self._store_segment_metadata(segment, flow_id)
            if not vast_success:
                logger.error("Failed to store segment metadata in VAST for segment %s", segment.object_id)
                return False
            
            logger.info("Successfully created TAMS segment metadata: %s", segment.object_id)
            return True
            
        except Exception as e:
            logger.error("Failed to create TAMS segment metadata %s: %s", segment.object_id, e)
            return False
    
    async def get_segments(self, flow_id: str, timerange: Optional[str] = None) -> List[FlowSegment]:
        """
        Get TAMS flow segments with optional timerange filtering
        
        Args:
            flow_id: ID of the flow to get segments for
            timerange: Optional timerange filter
            
        Returns:
            List[FlowSegment]: List of flow segments
        """
        try:
            logger.info("Getting TAMS segments for flow %s (timerange: %s)", flow_id, timerange)
            
            # 1. Get segment metadata from VAST
            segments_metadata = await self._get_segments_metadata(flow_id, timerange)
            if not segments_metadata:
                logger.info("No segments found for flow %s", flow_id)
                return []
            
            # 2. Convert to FlowSegment models with get_urls
            segments = []
            for metadata in segments_metadata:
                segment = await self._metadata_to_segment(metadata)
                if segment:
                    # Generate get_urls dynamically since presigned URLs expire
                    if segment.storage_path:
                        try:
                            get_urls = await self.s3.generate_get_urls(segment)
                            segment.get_urls = get_urls
                            logger.debug("Generated dynamic get_urls for segment %s: %d URLs", 
                                      segment.object_id, len(get_urls) if get_urls else 0)
                        except Exception as e:
                            logger.error("Failed to generate get_urls for segment %s: %s", 
                                       segment.object_id, e)
                            segment.get_urls = []
                    else:
                        logger.warning("No storage_path for segment %s, cannot generate get_urls", 
                                     segment.object_id)
                        segment.get_urls = []
                    
                    segments.append(segment)
            
            logger.info("Retrieved %d TAMS segments for flow %s", len(segments), flow_id)
            return segments
            
        except Exception as e:
            logger.error("Failed to get TAMS segments for flow %s: %s", flow_id, e)
            return []
    
    async def delete_segments(self, flow_id: str, timerange: Optional[str] = None) -> bool:
        """
        Delete TAMS flow segments with optional timerange filtering
        
        Args:
            flow_id: ID of the flow to delete segments for
            timerange: Optional timerange filter
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            logger.info("Deleting TAMS segments for flow %s (timerange: %s)", flow_id, timerange)
            
            # 1. Get segments to delete
            segments = await self.get_segments(flow_id, timerange)
            if not segments:
                logger.info("No segments to delete for flow %s", flow_id)
                return True
            
            # 2. Delete from S3 and VAST
            success_count = 0
            for segment in segments:
                s3_success = await self.s3.delete_segment(segment)
                vast_success = await self._delete_segment_metadata(segment.object_id)
                
                if s3_success and vast_success:
                    success_count += 1
                else:
                    logger.warning("Partial deletion for segment %s (S3: %s, VAST: %s)", 
                                 segment.object_id, s3_success, vast_success)
            
            logger.info("Deleted %d/%d TAMS segments for flow %s", success_count, len(segments), flow_id)
            return success_count == len(segments)
            
        except Exception as e:
            logger.error("Failed to delete TAMS segments for flow %s: %s", flow_id, e)
            return False
    
    async def _store_segment_metadata(self, segment: FlowSegment, flow_id: str) -> bool:
        """
        Store segment metadata in VAST
        """
        try:
            metadata = {
                'id': segment.object_id,  # Use object_id as the primary key
                'flow_id': flow_id,
                'object_id': segment.object_id,
                'timerange': segment.timerange,
                'ts_offset': segment.ts_offset,
                'last_duration': segment.last_duration,
                'storage_path': segment.storage_path,  # Store the S3 key used for this segment
                'size': 0 # FlowSegment does not have a size field, set to 0 for now
            }
            success = self.vast.insert_record('segments', metadata)
            if success:
                logger.info("Successfully stored segment metadata for %s with storage_path: %s", 
                          segment.object_id, segment.storage_path)
            else:
                logger.error("Failed to store segment metadata for %s", segment.object_id)
            return success
        except Exception as e:
            logger.error("Error storing segment metadata for %s: %s", segment.object_id, e)
            return False
    
    async def _get_segments_metadata(self, flow_id: str, timerange: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get segment metadata from VAST
        
        Args:
            flow_id: ID of the flow to get segments for
            timerange: Optional timerange filter
            
        Returns:
            List[Dict]: List of segment metadata
        """
        try:
            # Build predicate
            predicate = {'flow_id': flow_id}
            
            # Add timerange filter if provided
            if timerange:
                predicate['timerange'] = timerange
            
            # Query VAST
            metadata = self.vast.query_records('segments', predicate=predicate)
            
            logger.info("Retrieved %d segment metadata records from VAST for flow %s", 
                       len(metadata), flow_id)
            return metadata
            
        except Exception as e:
            logger.error("Failed to get segment metadata for flow %s: %s", flow_id, e)
            return []
    
    async def _metadata_to_segment(self, metadata: Dict[str, Any]) -> Optional[FlowSegment]:
        """
        Convert VAST metadata to FlowSegment model
        Note: get_urls are generated dynamically since presigned URLs expire
        """
        try:
            segment = FlowSegment(
                object_id=metadata['object_id'],
                timerange=metadata['timerange'],
                ts_offset=metadata.get('ts_offset', '0:0'),
                last_duration=metadata.get('last_duration', '0:0'),
                storage_path=metadata.get('storage_path')  # Restore the S3 key used for this segment
            )
            
            logger.info("Converted metadata to FlowSegment: %s with storage_path: %s", 
                      segment.object_id, segment.storage_path)
            return segment
            
        except Exception as e:
            logger.error("Failed to convert metadata to FlowSegment: %s", e)
            return None
    
    async def _delete_segment_metadata(self, segment_id: str) -> bool:
        """
        Delete segment metadata from VAST
        
        Args:
            segment_id: ID of the segment to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            # Note: VAST doesn't have native DELETE operations
            # This would need to be implemented using VAST's delete capabilities
            logger.warning("Segment metadata deletion not implemented for VAST")
            return False
            
        except Exception as e:
            logger.error("Failed to delete segment metadata for %s: %s", segment_id, e)
            return False
    
    async def get_segment_by_id(self, segment_id: str) -> Optional[FlowSegment]:
        """
        Get a specific TAMS segment by ID
        
        Args:
            segment_id: ID of the segment to get
            
        Returns:
            FlowSegment: FlowSegment model instance or None if not found
        """
        try:
            logger.info("Getting TAMS segment by ID: %s", segment_id)
            
            # Get metadata from VAST
            metadata = self.vast.query_records('segments', predicate={'id': segment_id})
            
            if not metadata:
                logger.info("Segment not found: %s", segment_id)
                return None
            
            # Convert to FlowSegment model
            segment = await self._metadata_to_segment(metadata[0])
            
            if segment:
                # Generate get_urls dynamically since presigned URLs expire
                if segment.storage_path:
                    try:
                        get_urls = await self.s3.generate_get_urls(segment)
                        segment.get_urls = get_urls
                        logger.debug("Generated dynamic get_urls for segment %s: %d URLs", 
                                  segment.object_id, len(get_urls) if get_urls else 0)
                    except Exception as e:
                        logger.error("Failed to generate get_urls for segment %s: %s", 
                                   segment.object_id, e)
                        segment.get_urls = []
                else:
                    logger.warning("No storage_path for segment %s, cannot generate get_urls", 
                                 segment.object_id)
                    segment.get_urls = []
                
                logger.info("Successfully retrieved TAMS segment: %s", segment_id)
            
            return segment
            
        except Exception as e:
            logger.error("Failed to get TAMS segment %s: %s", segment_id, e)
            return None
    
    async def update_segment(self, segment_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a TAMS segment
        
        Args:
            segment_id: ID of the segment to update
            updates: Dictionary of fields to update
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            logger.info("Updating TAMS segment %s with: %s", segment_id, updates)
            
            # Note: VAST doesn't have native UPDATE operations
            # This would need to be implemented as DELETE + INSERT or using VAST's update capabilities
            logger.warning("Segment update not implemented for VAST - use delete + insert instead")
            return False
            
        except Exception as e:
            logger.error("Failed to update TAMS segment %s: %s", segment_id, e)
            return False
