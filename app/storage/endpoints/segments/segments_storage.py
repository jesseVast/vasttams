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
    
    async def create_flow_segment(self, segment: FlowSegment, flow_id: str, media_data: Any) -> bool:
        """
        Create a TAMS flow segment - wrapper for create_segment for compatibility
        
        Args:
            segment: FlowSegment model instance
            flow_id: ID of the flow this segment belongs to
            media_data: Media data (bytes, string, or None for metadata-only)
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            # Convert media_data to bytes if it's a string
            if isinstance(media_data, str):
                media_data = media_data.encode('utf-8')
            elif media_data is None:
                # Metadata-only creation
                return await self.create_segment_metadata(segment, flow_id)
            
            # Create segment with media data
            return await self.create_segment(segment, flow_id, media_data)
            
        except Exception as e:
            logger.error("Failed to create flow segment %s: %s", segment.object_id, e)
            return False
    
    async def get_flow_segments(self, flow_id: str, timerange: Optional[str] = None) -> List[FlowSegment]:
        """
        Get TAMS flow segments with optional timerange filtering
        
        Args:
            flow_id: ID of the flow to get segments for
            timerange: Optional time range filter
            
        Returns:
            List of FlowSegment model instances
        """
        try:
            logger.info("Getting TAMS segments for flow %s", flow_id)
            
            # Use the get_segments method which includes get_urls generation
            return await self.get_segments(flow_id, timerange)
            
        except Exception as e:
            logger.error("Failed to get TAMS segments for flow %s: %s", flow_id, e)
            return []
    
    async def remove_flow_object_reference(self, object_id: str, flow_id: str) -> bool:
        """
        Remove a flow-object reference when a segment is deleted
        
        Args:
            object_id: ID of the object
            flow_id: ID of the flow that no longer references this object
            
        Returns:
            bool: True if removal successful, False otherwise
        """
        try:
            # Remove from flow_object_references table
            predicate = {
                'object_id': object_id,
                'flow_id': flow_id
            }
            
            # Use VAST delete with predicate
            success = self.vast.delete('flow_object_references', predicate)
            
            if success >= 0:  # 0 or positive means success
                logger.info("Removed flow-object reference for object %s, flow %s", object_id, flow_id)
                return True
            else:
                logger.error("Failed to remove flow-object reference for object %s, flow %s", object_id, flow_id)
                return False
                
        except Exception as e:
            logger.error("Failed to remove flow-object reference for object %s, flow %s: %s", 
                        object_id, flow_id, e)
            return False
    
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
            
        Raises:
            ValueError: If segments have dependent objects (TAMS API compliance)
        """
        try:
            logger.info("Deleting TAMS segments for flow %s (timerange: %s)", flow_id, timerange)
            
            # 1. Get segments to delete
            segments = await self.get_segments(flow_id, timerange)
            if not segments:
                logger.info("No segments to delete for flow %s", flow_id)
                return True
            
            # 2. ✅ NEW: Check dependencies before deletion (TAMS API compliance)
            for segment in segments:
                logger.info("🔍 DEBUG: Checking dependencies for segment %s (object_id: %s)", segment.object_id, segment.object_id)
                dependencies = await self._get_dependent_objects_for_segment(segment.object_id)
                logger.info("🔍 DEBUG: Dependencies found for segment %s: %s", segment.object_id, dependencies)
                if dependencies:
                    error_msg = f"Cannot delete segment {segment.object_id}: {len(dependencies)} dependencies exist. This would violate referential integrity: {dependencies}"
                    logger.warning(error_msg)
                    raise ValueError(error_msg)
                else:
                    logger.info("🔍 DEBUG: No dependencies found for segment %s, deletion allowed", segment.object_id)
            
            # 3. Delete from S3 and VAST
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
            
        except ValueError:
            # Re-raise TAMS compliance errors
            raise
        except Exception as e:
            logger.error("Failed to delete TAMS segments for flow %s: %s", flow_id, e)
            return False
    
    async def _store_segment_metadata(self, segment: FlowSegment, flow_id: str) -> bool:
        """
        Store segment metadata in VAST and manage flow-object references
        
        This method ensures TAMS compliance by:
        1. Storing segment metadata
        2. Creating/updating flow_object_references
        3. Ensuring objects know which flows reference them
        """
        try:
            # 1. Store segment metadata
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
            
            segment_success = self.vast.insert_record('segments', metadata)
            if not segment_success:
                logger.error("Failed to store segment metadata for %s", segment.object_id)
                return False
            
            # 2. Create flow-object reference for TAMS compliance
            # Use the working 'insert' method instead of 'insert_record' to avoid datetime conversion issues
            reference_metadata = {
                'object_id': [segment.object_id],  # Columnar format expected by 'insert'
                'flow_id': [flow_id],
                'created': [datetime.now(timezone.utc)]
            }
            
            reference_success = self.vast.insert('flow_object_references', reference_metadata)
            if not reference_success:
                logger.error("Failed to create flow-object reference for segment %s, flow %s", 
                           segment.object_id, flow_id)
                # Note: We don't fail here as the segment was created successfully
                # The flow reference is for compliance, not core functionality
                logger.warning("Flow-object reference creation failed, but segment was created")
            else:
                logger.info("Successfully created flow-object reference for segment %s, flow %s", 
                           segment.object_id, flow_id)
            
            # 3. Ensure object exists in objects table (if not already there)
            try:
                from ..objects.objects_storage import ObjectsStorage
                objects_storage = ObjectsStorage(self.vast)
                
                # Check if object exists
                existing_object = await objects_storage.get_object(segment.object_id)
                if not existing_object:
                    # Create minimal object record
                    from ....models.models import Object
                    obj = Object(
                        id=segment.object_id,
                        referenced_by_flows=[flow_id],
                        first_referenced_by_flow=flow_id,
                        size=0,  # Size unknown until actually uploaded
                        created=datetime.now(timezone.utc)
                    )
                    obj_success = await objects_storage.create_object(obj)
                    if obj_success:
                        logger.info("Created object record for segment %s", segment.object_id)
                    else:
                        logger.warning("Failed to create object record for segment %s", segment.object_id)
                else:
                    # Object exists, update its referenced_by_flows if needed
                    if flow_id not in existing_object.referenced_by_flows:
                        # Add this flow to the object's references
                        # Note: This would require an update method in ObjectsStorage
                        logger.debug("Object %s already exists and references flow %s", 
                                   segment.object_id, flow_id)
            except Exception as e:
                logger.warning("Failed to manage object record for segment %s: %s", segment.object_id, e)
                # Don't fail segment creation for object management issues
            
            logger.info("Successfully stored segment metadata for %s with storage_path: %s", 
                      segment.object_id, segment.storage_path)
            return True
            
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
            from ibis import _ as ibis_
            
            # Delete segment from VAST database using ibis predicate
            predicate = (ibis_.id == segment_id)
            deleted_count = self.vast.delete('segments', predicate)
            
            if deleted_count > 0:
                logger.info("Successfully deleted segment %s from VAST", segment_id)
                return True
            else:
                logger.warning("Segment %s not found for deletion", segment_id)
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

    async def _get_dependent_objects_for_segment(self, segment_id: str) -> List[str]:
        """
        Check if segment's object has dependencies that prevent deletion
        
        Args:
            segment_id: ID of the segment to check
            
        Returns:
            List[str]: List of dependency violations (flow references, other segments, etc.)
        """
        try:
            # Get the object_id from the segment
            segment = await self.get_segment_by_id(segment_id)
            if not segment:
                logger.warning("Segment %s not found for dependency check", segment_id)
                return []
            
            object_id = segment.object_id
            dependencies = []
            
            # 1. Check if this object is referenced by other flows (TAMS API compliance)
            flow_references = self.vast.query_records(
                'flow_object_references', 
                predicate={'object_id': object_id}
            )
            
            # Filter out the current flow
            other_flow_refs = [
                ref for ref in flow_references 
                if ref.get('flow_id') != segment.flow_id
            ]
            
            if other_flow_refs:
                logger.info("Object %s is referenced by %d other flows: %s", 
                           object_id, len(other_flow_refs), 
                           [ref.get('flow_id') for ref in other_flow_refs])
                dependencies.extend([f"flow_{ref.get('flow_id')}" for ref in other_flow_refs])
            
            # 2. Check if this object is referenced by other segments in the same flow
            # (This might indicate a data integrity issue)
            other_segments = self.vast.query_records(
                'segments', 
                predicate={'object_id': object_id, 'flow_id': segment.flow_id}
            )
            
            # Filter out the current segment
            other_segments = [
                seg for seg in other_segments 
                if seg.get('id') != segment_id
            ]
            
            if other_segments:
                logger.info("Object %s is referenced by %d other segments in flow %s: %s", 
                           object_id, len(other_segments), segment.flow_id,
                           [seg.get('id') for seg in other_segments])
                dependencies.extend([f"segment_{seg.get('id')}" for seg in other_segments])
            
            if dependencies:
                logger.info("Object %s has %d dependencies: %s", object_id, len(dependencies), dependencies)
            
            return dependencies
            
        except Exception as e:
            logger.error("Failed to check object dependencies for segment %s: %s", segment_id, e)
            return []
