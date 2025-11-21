"""
Loop Recorder Manager

Manages automatic deletion of old segments when flows exceed their loop_recorder_duration.
"""

import logging
import asyncio
from typing import Optional, List
from datetime import datetime, timedelta
import re

from ..flows.models import Flow
from ..segments.models import FlowSegment

logger = logging.getLogger(__name__)


class LoopRecorderManager:
    """Manages loop recording for flows"""
    
    def __init__(self, vast_db, s3_client=None, settings=None):
        """
        Initialize Loop Recorder Manager
        
        Args:
            vast_db: VAST database connection
            s3_client: S3 client (optional)
            settings: Application settings (optional)
        """
        self.vast_db = vast_db
        self.s3_client = s3_client
        self.settings = settings
        
        if settings is None:
            from ..core.config import get_settings
            self.settings = get_settings()
        
        # Service instances (lazy initialization)
        self._flow_service = None
        self._segment_service = None
    
    def _get_flow_service(self):
        """Get or create flow service"""
        if self._flow_service is None:
            from ..flows.service import FlowStorageService
            # Use s3_client if available, otherwise None
            s3_client = self.s3_client if self.s3_client is not None else None
            self._flow_service = FlowStorageService(self.vast_db, s3_client)
        return self._flow_service
    
    def _get_segment_service(self):
        """Get or create segment service"""
        if self._segment_service is None:
            from ..segments.service import SegmentStorageService
            # Use s3_client if available, otherwise None
            s3_client = self.s3_client if self.s3_client is not None else None
            self._segment_service = SegmentStorageService(self.vast_db, s3_client, self.settings)
        return self._segment_service
    
    async def process_flow(self, flow_id: str) -> bool:
        """
        Process a flow for loop recorder
        
        Args:
            flow_id: Flow identifier
            
        Returns:
            True if segments were deleted, False otherwise
        """
        try:
            # Get flow
            flow_service = self._get_flow_service()
            flow = await flow_service.get_flow(flow_id)
            if not flow:
                logger.debug(f"Flow {flow_id} not found for loop recorder")
                return False
            
            # Get tags from tag service (tags are stored separately, not in flow.tags JSON)
            from ..common.tags.service import TagStorageService
            # Use s3_client if available, otherwise None (TagStorageService requires it but can be None)
            s3_client = self.s3_client if self.s3_client is not None else None
            tag_service = TagStorageService(self.vast_db, s3_client)
            tags = await tag_service.get_flow_tags(flow_id)
            
            if not tags:
                logger.debug(f"Flow {flow_id} has no tags")
                return False
            
            # Get tags dict - handle both Tags model and dict
            tags_dict = None
            if hasattr(tags, 'root'):
                tags_dict = tags.root
            elif isinstance(tags, dict):
                tags_dict = tags
            else:
                logger.debug(f"Flow {flow_id} tags format not recognized: {type(tags)}")
                return False
            
            if not tags_dict:
                logger.debug(f"Flow {flow_id} tags.root is empty")
                return False
            
            logger.debug(f"Flow {flow_id} tags: {tags_dict}")
            
            duration_limit_sec = self._get_duration_limit(tags_dict)
            if not duration_limit_sec:
                logger.debug(f"Flow {flow_id} has no valid loop_recorder_duration tag")
                return False
            
            logger.info(f"Loop recorder: Processing flow {flow_id} with limit {duration_limit_sec}s")
            
            # Get all segments (skip URL generation since we don't need it for loop recorder)
            segment_service = self._get_segment_service()
            segments = await segment_service.get_flow_segments(flow_id, skip_get_urls_generation=True)
            
            if not segments or len(segments) == 0:
                logger.debug(f"No segments found for flow {flow_id}")
                return False
            
            logger.info(f"Loop recorder: Found {len(segments)} segments for flow {flow_id}")
            
            # Calculate current duration (pass flow_id for chunk_duration fallback)
            current_duration = await self._calculate_flow_duration(segments, flow_id)
            
            logger.info(f"Loop recorder: Flow {flow_id} duration {current_duration:.1f}s / {duration_limit_sec}s limit")
            
            # If within limit, no action needed
            if current_duration <= duration_limit_sec:
                return False
            
            # Calculate segments to delete
            segments_to_delete = self._get_segments_to_delete(
                segments,
                current_duration,
                duration_limit_sec
            )
            
            if not segments_to_delete:
                logger.debug(f"No segments to delete for flow {flow_id}")
                return False
            
            # Delete old segments
            deleted_count = 0
            for segment in segments_to_delete:
                success = await self._delete_segment(flow_id, segment)
                if success:
                    deleted_count += 1
            
            # After deleting segments, cleanup unreferenced objects (TAMS 8.0 spec requirement)
            # This ensures S3 objects are deleted when no longer referenced by any segments
            if deleted_count > 0:
                try:
                    from ..objects.service import ObjectStorageService
                    object_service = ObjectStorageService(self.vast_db, self.s3_client)
                    unreferenced = await object_service.get_unreferenced_objects()
                    if unreferenced:
                        cleanup_count = await object_service.delete_unreferenced_objects(unreferenced)
                        if cleanup_count > 0:
                            logger.info(f"Loop recorder: Cleaned up {cleanup_count} unreferenced objects after deleting {deleted_count} segments")
                except Exception as e:
                    logger.warning(f"Loop recorder: Failed to cleanup unreferenced objects: {e}")
                    # Don't fail the deletion if cleanup fails
            
            logger.info(
                "Loop recorder: Deleted %d segments from flow %s (current: %.1fs, limit: %.1fs)",
                deleted_count, flow_id, current_duration, duration_limit_sec
            )
            
            return deleted_count > 0
            
        except Exception as e:
            logger.error(f"Loop recorder error for flow {flow_id}: {e}", exc_info=True)
            return False
    
    def _get_duration_limit(self, tags: dict) -> Optional[int]:
        """Get loop_recorder_duration from tags in seconds"""
        duration = tags.get('loop_recorder_duration')
        if duration:
            try:
                return int(duration)
            except (ValueError, TypeError):
                logger.warning(f"Invalid loop_recorder_duration tag: {duration}")
        return None
    
    async def _calculate_flow_duration(self, segments: List[FlowSegment], flow_id: Optional[str] = None) -> float:
        """Calculate total duration of flow in seconds"""
        if not segments or len(segments) == 0:
            return 0
        
        # Sort segments by timerange
        sorted_segments = sorted(segments, key=lambda s: self._get_timerange_start(s.timerange))
        
        # Get first and last segment
        first_segment = sorted_segments[0]
        last_segment = sorted_segments[-1]
        
        # Try to parse timeranges - need to get END time from last segment
        start = self._parse_timerange(first_segment.timerange)
        # For end time, we need to parse the END of the timerange, not the start
        end = self._parse_timerange_end(last_segment.timerange)
        
        if start and end:
            duration = (end - start).total_seconds()
            logger.debug(f"Calculated duration from timeranges: {duration}s (start: {start}, end: {end})")
            return duration
        
        # Fallback 1: estimate from sample_count if available
        total_samples = sum(
            (s.sample_count or 0) for s in segments if s.sample_count
        )
        if total_samples > 0:
            # Rough estimate: 30 samples per second for video
            # Adjust based on actual frame rate
            estimated_duration = total_samples / 30.0
            logger.debug(f"Estimated duration from sample_count: {estimated_duration}s ({total_samples} samples)")
            return estimated_duration
        
        # Fallback 2: Use chunk_duration tag from flow if available
        # This is a common pattern for stream_ingestor where chunks have fixed duration
        if flow_id:
            try:
                from ..common.tags.service import TagStorageService
                s3_client = self.s3_client if self.s3_client is not None else None
                tag_service = TagStorageService(self.vast_db, s3_client)
                tags = await tag_service.get_flow_tags(flow_id)
                if tags and hasattr(tags, 'root') and tags.root:
                    chunk_duration_str = tags.root.get('chunk_duration')
                    if chunk_duration_str:
                        try:
                            chunk_duration = int(chunk_duration_str)
                            estimated_duration = len(segments) * chunk_duration
                            logger.debug(f"Estimated duration from chunk_duration tag: {estimated_duration}s ({len(segments)} segments × {chunk_duration}s)")
                            return estimated_duration
                        except (ValueError, TypeError):
                            pass
            except Exception as e:
                logger.debug(f"Could not use chunk_duration fallback: {e}")
        
        logger.warning("Could not calculate flow duration - no timerange, sample_count, or chunk_duration")
        return 0
    
    def _parse_timerange(self, timerange) -> Optional[datetime]:
        """Parse TAMS timerange to datetime - returns the START time"""
        if not timerange:
            return None
        
        try:
            # TAMS timerange format: [start_seconds:start_nanos_end_seconds:end_nanos)
            # Example: [1234567890:0_1234567891:0) or [0:0_5:0) for relative time
            
            timerange_str = str(timerange.value) if hasattr(timerange, 'value') else str(timerange)
            
            # Parse the start timestamp
            # Format: [sec:nanosec...]
            pattern = r'\[(\d+):(\d+)'
            match = re.search(pattern, timerange_str)
            
            if match:
                seconds = int(match.group(1))
                nanos = int(match.group(2))
                
                # For relative timestamps (starting from 0), we can still use them
                # The duration calculation uses (end - start), so relative times work fine
                # Convert to datetime (using epoch + offset for relative times)
                # For absolute timestamps, this is correct
                # For relative timestamps starting at 0, we use epoch + offset
                timestamp = seconds + (nanos / 1e9)
                
                # If timestamp is very small (< 1000), it's likely a relative timestamp
                # We'll treat it as seconds since epoch start (1970-01-01)
                # This allows duration calculation: (end_time - start_time) to work correctly
                return datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not parse timerange {timerange}: {e}")
            return None
    
    def _parse_timerange_end(self, timerange) -> Optional[datetime]:
        """Parse TAMS timerange to datetime - returns the END time"""
        if not timerange:
            return None
        
        try:
            # TAMS timerange format: [start_seconds:start_nanos_end_seconds:end_nanos)
            # Example: [1234567890:0_1234567891:0) or [0:0_5:0)
            
            timerange_str = str(timerange.value) if hasattr(timerange, 'value') else str(timerange)
            
            # Parse the END timestamp
            # Format: ..._end_sec:end_nanos)
            pattern = r'_(\d+):(\d+)\)'
            match = re.search(pattern, timerange_str)
            
            if match:
                seconds = int(match.group(1))
                nanos = int(match.group(2))
                
                timestamp = seconds + (nanos / 1e9)
                return datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not parse timerange end {timerange}: {e}")
            return None
    
    def _get_timerange_start(self, timerange) -> float:
        """Get start time of timerange as float for sorting"""
        parsed = self._parse_timerange(timerange)
        if parsed:
            return parsed.timestamp()
        return 0.0
    
    def _get_segments_to_delete(self, segments: List[FlowSegment], current_duration: float, limit_duration: float) -> List[FlowSegment]:
        """Get segments to delete to bring duration within limit"""
        if not segments:
            return []
        
        excess_duration = current_duration - limit_duration
        if excess_duration <= 0:
            return []
        
        # Sort segments by timerange (oldest first)
        sorted_segments = sorted(segments, key=lambda s: self._get_timerange_start(s.timerange))
        
        # Calculate approximate duration per segment
        duration_per_segment = current_duration / len(segments) if len(segments) > 0 else 0
        
        if duration_per_segment == 0:
            return []
        
        # Estimate how many segments to delete
        # Add 1 extra to ensure we're under the limit
        segments_to_delete_count = int(excess_duration / duration_per_segment) + 1
        
        # Don't delete all segments
        if segments_to_delete_count >= len(sorted_segments):
            segments_to_delete_count = len(sorted_segments) - 1
        
        # Return oldest segments
        return sorted_segments[:segments_to_delete_count]
    
    async def _delete_segment(self, flow_id: str, segment: FlowSegment) -> bool:
        """Delete a specific segment by object_id and timerange"""
        try:
            if not segment.object_id:
                logger.warning(f"Cannot delete segment from flow {flow_id}: no object_id")
                return False
            
            if not segment.timerange:
                logger.warning(f"Cannot delete segment from flow {flow_id}: no timerange")
                return False
            
            # Use segment service to delete - this ensures proper cleanup
            # Note: We use SegmentStorageService directly (not TAMSStorageService) to avoid
            # triggering object cleanup for each individual segment deletion.
            # Object cleanup should happen in batch after all segments are deleted.
            segment_service = self._get_segment_service()
            
            # Parse timerange to get timerange string for deletion
            timerange_str = str(segment.timerange.value) if hasattr(segment.timerange, 'value') else str(segment.timerange)
            
            # Delete segment using service method (which handles database deletion)
            # This deletes the segment record from the database
            success = await segment_service.delete_flow_segments(
                flow_id,
                timerange=timerange_str
            )
            
            if success:
                logger.debug(f"Deleted segment {segment.object_id} (timerange: {timerange_str}) from flow {flow_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete segment from flow {flow_id}: {e}", exc_info=True)
            return False

