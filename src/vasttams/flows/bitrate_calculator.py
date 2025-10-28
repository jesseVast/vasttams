"""
Bit Rate Calculator for TAMS Flows

Implements auto-calculation of flow bit rates from segments per TAMS App Note 0013.
"""

import logging
from typing import List, Optional
import asyncio
import httpx
import json

from ..segments.models import FlowSegment

logger = logging.getLogger(__name__)


class BitRateCalculator:
    """Calculate flow bit rates from segment metadata"""
    
    @staticmethod
    async def calculate_avg_bit_rate(segments: List[FlowSegment], get_segment_size_fn=None) -> Optional[int]:
        """
        Calculate average bit rate from segments per App Note 0013
        
        Formula: avg_bit_rate = int(total_segment_bit_size / (total_segment_duration_sec * 1000)) kbit/sec
        
        Args:
            segments: List of flow segments
            get_segment_size_fn: Async function to get segment size in bytes
            
        Returns:
            Average bit rate in kbit/sec, or None if calculation fails
        """
        if not segments:
            return None
        
        total_bit_size = 0
        total_duration_sec = 0
        
        for segment in segments:
            try:
                # Get segment size if available
                segment_size_bytes = await _get_segment_size(segment, get_segment_size_fn)
                if segment_size_bytes:
                    total_bit_size += segment_size_bytes * 8  # Convert bytes to bits
                
                # Calculate duration from timerange
                duration_sec = _calculate_segment_duration(segment)
                if duration_sec:
                    total_duration_sec += duration_sec
                    
            except Exception as e:
                logger.warning(f"Failed to process segment for bit rate calculation: {e}")
                continue
        
        if total_duration_sec == 0:
            return None
        
        # Calculate average bit rate in kbit/sec
        avg_bit_rate = int(total_bit_size / (total_duration_sec * 1000))
        return avg_bit_rate
    
    @staticmethod
    async def calculate_max_bit_rate(segments: List[FlowSegment], target_segment_duration: float, get_segment_size_fn=None) -> Optional[int]:
        """
        Calculate maximum bit rate from segments per App Note 0013
        
        Formula: max_bit_rate = int(peak_segment_bit_rate / 1000) kbit/sec
        Peak is the maximum bit rate for a contiguous sequence of segments with duration between 0.5 and 1.5 target duration
        
        Args:
            segments: List of flow segments
            target_segment_duration: Target segment duration in seconds
            get_segment_size_fn: Async function to get segment size in bytes
            
        Returns:
            Maximum bit rate in kbit/sec, or None if calculation fails
        """
        if not segments:
            return None
        
        max_bit_rate = 0
        
        # Process segments in sliding windows
        for i in range(len(segments)):
            sequence_duration = 0
            sequence_bits = 0
            
            # Build sequence starting from segment i
            for j in range(i, len(segments)):
                segment = segments[j]
                segment_duration = _calculate_segment_duration(segment)
                
                if segment_duration:
                    sequence_duration += segment_duration
                    
                    # Check if sequence duration is between 0.5 and 1.5 target duration
                    if sequence_duration > target_segment_duration * 1.5:
                        break
                    
                    # Get segment size
                    segment_size_bytes = await _get_segment_size(segment, get_segment_size_fn)
                    if segment_size_bytes:
                        sequence_bits += segment_size_bytes * 8
                    
                    # Calculate bit rate for this sequence
                    if sequence_duration >= target_segment_duration * 0.5:
                        sequence_bit_rate = int(sequence_bits / sequence_duration)
                        max_bit_rate = max(max_bit_rate, sequence_bit_rate)
        
        # Also check single segments above 1.5 target duration (per HLS extension in app note)
        for segment in segments:
            segment_duration = _calculate_segment_duration(segment)
            if segment_duration and segment_duration > target_segment_duration * 1.5:
                segment_size_bytes = await _get_segment_size(segment, get_segment_size_fn)
                if segment_size_bytes:
                    segment_bits = segment_size_bytes * 8
                    segment_bit_rate = int(segment_bits / segment_duration)
                    max_bit_rate = max(max_bit_rate, segment_bit_rate)
        
        return int(max_bit_rate / 1000) if max_bit_rate > 0 else None


async def _get_segment_size(segment: FlowSegment, get_segment_size_fn=None) -> Optional[int]:
    """
    Get segment size in bytes
    
    Args:
        segment: Flow segment
        get_segment_size_fn: Optional async function to fetch actual size from storage
        
    Returns:
        Size in bytes, or None if unavailable
    """
    # If custom function provided, use it
    if get_segment_size_fn:
        try:
            return await get_segment_size_fn(segment)
        except Exception as e:
            logger.warning(f"Failed to get segment size: {e}")
    
    # Try to estimate from sample_count if available
    if segment.sample_count:
        # Rough estimate: 4 bytes per sample (very rough, depends on codec)
        return segment.sample_count * 4
    
    # Could also try to fetch from get_urls
    if segment.get_urls:
        try:
            # Try first URL
            first_url = segment.get_urls[0]
            async with httpx.AsyncClient() as client:
                response = await client.head(first_url.url, timeout=5)
                if response.status_code == 200:
                    content_length = response.headers.get('content-length')
                    if content_length:
                        return int(content_length)
        except Exception as e:
            logger.debug(f"Could not get segment size from URL: {e}")
    
    return None


def _calculate_segment_duration(segment: FlowSegment) -> Optional[float]:
    """
    Calculate segment duration in seconds from timerange
    
    Args:
        segment: Flow segment
        
    Returns:
        Duration in seconds, or None if unavailable
    """
    if not segment.timerange:
        return None
    
    try:
        # Parse timerange value
        timerange_value = segment.timerange.value if hasattr(segment.timerange, 'value') else str(segment.timerange)
        
        # Parse TAMS timerange format: [start_end)
        import re
        pattern = r'^(\[|\()?(-?\d+):(\d+)(_(-?\d+):(\d+))?(\]|\))?$'
        match = re.match(pattern, timerange_value)
        
        if not match:
            return None
        
        # Extract start and end timestamps
        start_seconds = int(match.group(2)) if match.group(2) else 0
        start_nanos = int(match.group(3)) if match.group(3) else 0
        end_seconds = int(match.group(5)) if match.group(5) and match.group(5) != '_' else start_seconds
        end_nanos = int(match.group(6)) if match.group(6) else start_nanos
        
        # Calculate duration in seconds
        start_total = start_seconds + (start_nanos / 1e9)
        end_total = end_seconds + (end_nanos / 1e9)
        duration = end_total - start_total
        
        return max(0, duration)
        
    except Exception as e:
        logger.warning(f"Failed to calculate segment duration: {e}")
        return None

