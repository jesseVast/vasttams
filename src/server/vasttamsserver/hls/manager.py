"""
HLS Manager

Generates HLS playlists from TAMS flows and segments.
"""

import logging
from typing import List, Optional, TYPE_CHECKING
import re

from .models import HLSPlaylist, HLSSegment

if TYPE_CHECKING:
    from ..segments.models import FlowSegment

logger = logging.getLogger(__name__)


class HLSManager:
    """Manages HLS playlist generation"""
    
    def __init__(self, vast_db, s3_client=None, settings=None):
        """Initialize HLS Manager"""
        self.vast_db = vast_db
        self.s3_client = s3_client
        self.settings = settings or self._get_settings()
        
        # Initialize segment service (lazy)
        self._segment_service = None
    
    def _get_settings(self):
        """Get application settings"""
        from ..core.config import get_settings
        return get_settings()
    
    def _get_segment_service(self):
        """Get or create segment service"""
        if self._segment_service is None:
            from ..segments.service import SegmentStorageService
            s3_client = self.s3_client if self.s3_client else None
            self._segment_service = SegmentStorageService(
                self.vast_db, 
                s3_client, 
                self.settings
            )
        return self._segment_service
    
    async def generate_playlist(self, flow_id: str) -> Optional[HLSPlaylist]:
        """
        Generate HLS master playlist for a flow
        
        Args:
            flow_id: Flow identifier
            
        Returns:
            HLSPlaylist or None if flow not found
        """
        try:
            # Get segments
            segment_service = self._get_segment_service()
            segments = await segment_service.get_flow_segments(flow_id)
            
            if not segments:
                logger.warning(f"No segments found for flow {flow_id}")
                return None
            
            # Generate HLS playlist
            return self._generate_playlist(segments)
            
        except Exception as e:
            logger.error(f"Failed to generate HLS playlist for flow {flow_id}: {e}", exc_info=True)
            return None
    
    def _generate_playlist(self, segments: List['FlowSegment']) -> HLSPlaylist:
        """Generate HLS playlist from segments"""
        hls_segments = []
        
        for i, segment in enumerate(segments):
            # Get segment URL
            url = self._get_segment_url(segment)
            if not url:
                continue
            
            # Calculate duration
            duration = self._calculate_segment_duration(segment)
            
            # Create HLS segment
            hls_segment = HLSSegment(
                url=url,
                duration=duration,
                sequence=i,
                discontinuity=False
            )
            hls_segments.append(hls_segment)
        
        if not hls_segments:
            logger.warning("No HLS segments generated")
            return HLSPlaylist(
                version=3,
                target_duration=1.0,
                media_sequence=0,
                segments=[],
                endlist=True
            )
        
        # Get target duration (longest segment)
        target_duration = max(
            (s.duration for s in hls_segments), 
            default=1.0
        )
        
        return HLSPlaylist(
            version=3,
            target_duration=target_duration,
            media_sequence=0,
            segments=hls_segments,
            endlist=True  # For now, always closed
        )
    
    def _get_segment_url(self, segment: 'FlowSegment') -> Optional[str]:
        """Get HLS-compatible URL from segment"""
        if not segment.get_urls or len(segment.get_urls) == 0:
            return None
        
        # Try to get HLS-specific URL first (by label)
        for get_url in segment.get_urls:
            label = getattr(get_url, 'label', '') or ''
            if label and 'hls' in label.lower():
                return get_url.url
        
        # Fallback to first URL
        return segment.get_urls[0].url
    
    def _calculate_segment_duration(self, segment: 'FlowSegment') -> float:
        """Calculate segment duration in seconds"""
        if segment.timerange:
            duration = self._parse_timerange_duration(segment.timerange)
            if duration:
                return duration
        
        # Fallback: estimate from sample_count
        if segment.sample_count:
            # Rough estimate: 30 samples per second (adjust as needed)
            return segment.sample_count / 30.0
        
        # Default: 1 second
        logger.debug(f"No duration info for segment {segment.object_id}, using 1.0s default")
        return 1.0
    
    def _parse_timerange_duration(self, timerange) -> Optional[float]:
        """Parse timerange to get duration in seconds"""
        if not timerange:
            return None
        
        try:
            timerange_str = str(timerange.value) if hasattr(timerange, 'value') else str(timerange)
            
            # Parse: [start_sec:start_nano_end_sec:end_nano)
            # Example: [1234567890:0_1234567891:0)
            pattern = r'\[(\d+):(\d+)_(\d+):(\d+)\)'
            match = re.search(pattern, timerange_str)
            
            if match:
                start_sec = int(match.group(1))
                start_nano = int(match.group(2))
                end_sec = int(match.group(3))
                end_nano = int(match.group(4))
                
                start_total = start_sec + (start_nano / 1e9)
                end_total = end_sec + (end_nano / 1e9)
                
                duration = end_total - start_total
                return max(0, duration)  # Ensure non-negative
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not parse timerange {timerange}: {e}")
            return None
    
    def playlist_to_m3u8(self, playlist: HLSPlaylist) -> str:
        """Convert HLSPlaylist model to M3U8 format"""
        lines = [
            "#EXTM3U",
            f"#EXT-X-VERSION:{playlist.version}",
            f"#EXT-X-TARGETDURATION:{int(playlist.target_duration)}",
            f"#EXT-X-MEDIA-SEQUENCE:{playlist.media_sequence}"
        ]
        
        for segment in playlist.segments:
            if segment.discontinuity:
                lines.append("#EXT-X-DISCONTINUITY")
            
            lines.append(f"#EXTINF:{segment.duration:.3f},")
            lines.append(segment.url)
        
        if playlist.endlist:
            lines.append("#EXT-X-ENDLIST")
        
        return "\n".join(lines) + "\n"

