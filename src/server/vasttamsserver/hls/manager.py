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
    
    async def generate_playlist(self, flow_id: str, flow_container: Optional[str] = None, 
                               use_proxy_urls: bool = True, base_url: Optional[str] = None) -> Optional[HLSPlaylist]:
        """
        Generate HLS master playlist for a flow
        
        Args:
            flow_id: Flow identifier
            flow_container: Optional flow container type (e.g., 'video/mp2t') for validation
            use_proxy_urls: If True, use proxy URLs through TAMS API (for CORS support)
            base_url: Base URL for generating absolute proxy URLs (e.g., 'http://localhost:8000')
            
        Returns:
            HLSPlaylist or None if flow not found
        """
        try:
            # Get segments WITH get_urls generation - HLS playlists need presigned URLs to work
            # This is expected to be slower for large flows, but necessary for HLS functionality
            segment_service = self._get_segment_service()
            segments = await segment_service.get_flow_segments(flow_id, skip_get_urls_generation=False)
            
            if not segments:
                logger.warning(f"No segments found for flow {flow_id}")
                return None
            
            # Generate HLS playlist with flow container for validation
            return self._generate_playlist(
                segments, 
                flow_container=flow_container, 
                flow_id=flow_id, 
                use_proxy_urls=use_proxy_urls,
                base_url=base_url
            )
            
        except Exception as e:
            logger.error(f"Failed to generate HLS playlist for flow {flow_id}: {e}", exc_info=True)
            return None
    
    def _generate_playlist(self, segments: List['FlowSegment'], flow_container: Optional[str] = None, 
                          flow_id: Optional[str] = None, use_proxy_urls: bool = True, 
                          base_url: Optional[str] = None) -> HLSPlaylist:
        """Generate HLS playlist from segments
        
        Only includes segments with HLS-compatible URLs (.ts files).
        
        Args:
            segments: List of flow segments
            flow_container: Optional flow container type for validation (e.g., 'video/mp2t')
            flow_id: Flow ID for generating proxy URLs
            use_proxy_urls: If True, convert storage URLs to proxy URLs (for CORS support)
            base_url: Base URL for generating absolute proxy URLs
        """
        hls_segments = []
        skipped_count = 0
        
        # Check if flow container indicates HLS-compatible content
        is_hls_container = False
        if flow_container:
            flow_container_lower = flow_container.lower()
            is_hls_container = (
                'mp2t' in flow_container_lower or 
                'mpeg2ts' in flow_container_lower or
                'video/mp2t' in flow_container_lower
            )
        
        for i, segment in enumerate(segments):
            # Get segment URL (validates .ts extension or uses flow container)
            original_url = self._get_segment_url(segment, is_hls_container=is_hls_container)
            if not original_url:
                skipped_count += 1
                logger.debug(f"Skipping segment {segment.object_id} - no HLS-compatible URL (.ts file)")
                continue
            
            # Convert to proxy URL if requested (for CORS support)
            if use_proxy_urls and flow_id:
                from urllib.parse import quote
                proxy_path = f"/api/tams/v8.0/hls/flows/{flow_id}/segments/{segment.object_id}?url={quote(original_url, safe='')}"
                # Use absolute URL if base_url provided, otherwise use relative
                if base_url:
                    url = f"{base_url}{proxy_path}"
                else:
                    url = proxy_path
            else:
                url = original_url
            
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
            logger.warning(f"No HLS segments generated from {len(segments)} segments (skipped {skipped_count} non-.ts segments)")
            return HLSPlaylist(
                version=3,
                target_duration=1.0,
                media_sequence=0,
                segments=[],
                endlist=True
            )
        
        if skipped_count > 0:
            logger.info(f"Generated HLS playlist with {len(hls_segments)} segments (skipped {skipped_count} non-.ts segments)")
        
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
    
    def _get_segment_url(self, segment: 'FlowSegment', is_hls_container: bool = False) -> Optional[str]:
        """Get HLS-compatible URL from segment
        
        HLS requires .ts (Transport Stream) files. This method validates that
        the URL points to a .ts file or has an HLS-compatible label.
        
        Args:
            segment: Flow segment
            is_hls_container: If True, accept URLs even without .ts extension (for video/mp2t flows)
        """
        if not segment.get_urls or len(segment.get_urls) == 0:
            return None
        
        # Try to get HLS-specific URL first (by label)
        for get_url in segment.get_urls:
            label = getattr(get_url, 'label', '') or ''
            if label and 'hls' in label.lower():
                url = get_url.url
                # Validate it's a .ts file or flow container indicates HLS
                if self._is_hls_compatible_url(url, is_hls_container=is_hls_container):
                    return url
        
        # Fallback to first URL, but validate it's .ts or flow is HLS-compatible
        for get_url in segment.get_urls:
            url = get_url.url
            if self._is_hls_compatible_url(url, is_hls_container=is_hls_container):
                return url
        
        # No HLS-compatible URL found
        logger.warning(f"Segment {segment.object_id} has no HLS-compatible URLs (.ts files)")
        return None
    
    def _is_hls_compatible_url(self, url: str, is_hls_container: bool = False) -> bool:
        """Check if URL points to an HLS-compatible file (.ts extension)
        
        HLS requires Transport Stream (.ts) files. This validates the URL
        has a .ts extension or is explicitly marked as HLS-compatible.
        
        Args:
            url: URL to validate
            is_hls_container: If True, accept URLs even without .ts extension (for video/mp2t flows)
        """
        if not url:
            return False
        
        # Check for .ts extension (case-insensitive)
        url_lower = url.lower()
        if url_lower.endswith('.ts'):
            return True
        
        # Check for .ts in query parameters (some CDNs use this)
        if '.ts' in url_lower:
            return True
        
        # If flow container indicates HLS-compatible content (video/mp2t), accept URLs without extension
        # This handles cases where segments are stored by object_id without file extensions
        if is_hls_container:
            logger.debug(f"URL {url} accepted for HLS (flow container indicates Transport Stream)")
            return True
        
        # If URL doesn't have extension, we can't validate - log warning
        # In practice, HLS segments should always have .ts extension
        logger.debug(f"URL {url} does not have .ts extension - may not be HLS-compatible")
        return False
    
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

