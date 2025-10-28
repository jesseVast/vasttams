"""
Loop Recorder Manager

Manages automatic deletion of old segments when flows exceed their loop_recorder_duration.
"""

import logging
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
            s3_client = self.s3_client or (lambda: None)  # Default to None
            self._flow_service = FlowStorageService(self.vast_db, s3_client)
        return self._flow_service
    
    def _get_segment_service(self):
        """Get or create segment service"""
        if self._segment_service is None:
            from ..segments.service import SegmentStorageService
            s3_client = self.s3_client or (lambda: None)  # Default to None
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
            
            # Check if flow has loop_recorder_duration tag
            if not flow.tags or not flow.tags.root:
                return False
            
            duration_limit_sec = self._get_duration_limit(flow.tags.root)
            if not duration_limit_sec:
                return False
            
            logger.debug(f"Loop recorder: Processing flow {flow_id} with limit {duration_limit_sec}s")
            
            # Get all segments
            segment_service = self._get_segment_service()
            segments = await segment_service.get_flow_segments(flow_id)
            
            if not segments or len(segments) == 0:
                logger.debug(f"No segments found for flow {flow_id}")
                return False
            
            # Calculate current duration
            current_duration = self._calculate_flow_duration(segments)
            
            logger.debug(f"Loop recorder: Flow {flow_id} duration {current_duration}s / {duration_limit_sec}s limit")
            
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
            
            logger.info(
                f"Loop recorder: Deleted {deleted_count} segments from flow {flow_id} "
                f"(current: {current_duration:.1f}s, limit: {duration_limit_sec}s)"
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
    
    def _calculate_flow_duration(self, segments: List[FlowSegment]) -> float:
        """Calculate total duration of flow in seconds"""
        if not segments or len(segments) == 0:
            return 0
        
        # Sort segments by timerange
        sorted_segments = sorted(segments, key=lambda s: self._get_timerange_start(s.timerange))
        
        # Get first and last segment
        first_segment = sorted_segments[0]
        last_segment = sorted_segments[-1]
        
        # Try to parse timeranges
        start = self._parse_timerange(first_segment.timerange)
        end = self._parse_timerange(last_segment.timerange)
        
        if start and end:
            return (end - start).total_seconds()
        
        # Fallback: estimate from sample_count if available
        total_samples = sum(
            (s.sample_count or 0) for s in segments if s.sample_count
        )
        if total_samples > 0:
            # Rough estimate: 30 samples per second for video
            # Adjust based on actual frame rate
            return total_samples / 30.0
        
        logger.warning("Could not calculate flow duration - no timerange or sample_count")
        return 0
    
    def _parse_timerange(self, timerange) -> Optional[datetime]:
        """Parse TAMS timerange to datetime"""
        if not timerange:
            return None
        
        try:
            # TAMS timerange format: [start_seconds:start_nanos_end_seconds:end_nanos)
            # Example: [1234567890:0_1234567891:0)
            
            timerange_str = str(timerange.value) if hasattr(timerange, 'value') else str(timerange)
            
            # Parse the start timestamp
            # Format: [sec:nanosec...]
            pattern = r'\[(\d+):(\d+)'
            match = re.search(pattern, timerange_str)
            
            if match:
                seconds = int(match.group(1))
                nanos = int(match.group(2))
                
                # Convert to datetime
                return datetime.fromtimestamp(seconds + (nanos / 1e9), tz=datetime.timezone.utc)
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not parse timerange {timerange}: {e}")
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
        """Delete a specific segment"""
        try:
            segment_service = self._get_segment_service()
            
            # Delete by creating a timerange that matches this segment
            # Then calling delete_flow_segments
            if segment.timerange:
                timerange_str = str(segment.timerange.value) if hasattr(segment.timerange, 'value') else str(segment.timerange)
                
                # Delete segment by timerange and object_id
                success = await segment_service.delete_flow_segments(
                    flow_id,
                    timerange=timerange_str
                )
                
                return success
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete segment from flow {flow_id}: {e}")
            return False

