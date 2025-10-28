#!/usr/bin/env python3
"""
Tests for HLS Manager

Tests HLS playlist generation logic.
"""

import pytest
import sys
from pathlib import Path
import uuid

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.hls.manager import HLSManager
from vasttams.hls.models import HLSPlaylist, HLSSegment

import logging
logger = logging.getLogger(__name__)


class TestHLSManager:
    """Test HLS Manager functionality"""
    
    def test_parse_timerange_duration(self):
        """Test timerange duration parsing"""
        manager = HLSManager(None)  # vast_db not needed for this test
        
        # Test standard timerange - use string directly
        from vasttams.common.models import TimeRange
        timerange = TimeRange(value="[1234567890:0_1234567891:0)")
        duration = manager._parse_timerange_duration(timerange)
        assert duration == 1.0
        
        # Test with nanoseconds
        timerange = TimeRange(value="[1234567890:500000000_1234567891:0)")
        duration = manager._parse_timerange_duration(timerange)
        assert duration == 0.5
        
        # Test invalid timerange
        result = manager._parse_timerange_duration(None)
        assert result is None
    
    def test_calculate_segment_duration_from_timerange(self):
        """Test duration calculation from timerange"""
        manager = HLSManager(None)
        
        from vasttams.segments.models import FlowSegment, GetUrl
        from vasttams.common.models import TimeRange
        
        segment = FlowSegment(
            object_id=str(uuid.uuid4()),
            timerange=TimeRange(value="[0:0_2:0)"),  # 2 seconds
            get_urls=[
                GetUrl(
                    url="https://example.com/segment.ts",
                    storage_id=str(uuid.uuid4()),
                    provider="aws",
                    store_product="s3"
                )
            ]
        )
        
        duration = manager._calculate_segment_duration(segment)
        assert duration == 2.0
    
    def test_calculate_segment_duration_from_sample_count(self):
        """Test duration calculation from sample_count"""
        manager = HLSManager(None)
        
        from vasttams.segments.models import FlowSegment, GetUrl
        from vasttams.common.models import TimeRange
        
        # Use Optional for timerange
        segment = FlowSegment(
            object_id=str(uuid.uuid4()),
            timerange=TimeRange(value="[0:0_0:0)"),  # Zero-duration timerange, will use sample_count
            sample_count=30,  # 30 samples at 30 fps = 1 second
            get_urls=[
                GetUrl(
                    url="https://example.com/segment.ts",
                    storage_id=str(uuid.uuid4()),
                    provider="aws",
                    store_product="s3"
                )
            ]
        )
        
        duration = manager._calculate_segment_duration(segment)
        assert duration == 1.0
    
    def test_get_segment_url_prefers_hls_label(self):
        """Test that URLs with 'hls' in label are preferred"""
        manager = HLSManager(None)
        
        from vasttams.segments.models import FlowSegment, GetUrl
        from vasttams.common.models import TimeRange
        
        segment = FlowSegment(
            object_id=str(uuid.uuid4()),
            timerange=TimeRange(value="[0:0_1:0)"),
            get_urls=[
                GetUrl(
                    url="https://example.com/regular.mp4",
                    storage_id=str(uuid.uuid4()),
                    provider="aws",
                    store_product="s3",
                    label="original"
                ),
                GetUrl(
                    url="https://example.com/segment.ts",
                    storage_id=str(uuid.uuid4()),
                    provider="aws",
                    store_product="s3",
                    label="hls"
                )
            ]
        )
        
        url = manager._get_segment_url(segment)
        assert url == "https://example.com/segment.ts"
    
    def test_get_segment_url_fallback_to_first(self):
        """Test URL selection falls back to first URL if no HLS label"""
        manager = HLSManager(None)
        
        from vasttams.segments.models import FlowSegment, GetUrl
        from vasttams.common.models import TimeRange
        
        segment = FlowSegment(
            object_id=str(uuid.uuid4()),
            timerange=TimeRange(value="[0:0_1:0)"),
            get_urls=[
                GetUrl(
                    url="https://example.com/segment.mp4",
                    storage_id=str(uuid.uuid4()),
                    provider="aws",
                    store_product="s3",
                    label="original"
                )
            ]
        )
        
        url = manager._get_segment_url(segment)
        assert url == "https://example.com/segment.mp4"
    
    def test_get_segment_url_no_urls(self):
        """Test URL selection with no URLs"""
        manager = HLSManager(None)
        
        from vasttams.segments.models import FlowSegment
        from vasttams.common.models import TimeRange
        
        segment = FlowSegment(
            object_id=str(uuid.uuid4()),
            timerange=TimeRange(value="[0:0_1:0)"),
            get_urls=[]
        )
        
        url = manager._get_segment_url(segment)
        assert url is None
    
    def test_playlist_to_m3u8_format(self):
        """Test M3U8 format generation"""
        manager = HLSManager(None)
        
        playlist = HLSPlaylist(
            version=3,
            target_duration=1.0,
            media_sequence=0,
            segments=[
                HLSSegment(
                    url="https://example.com/seg1.ts",
                    duration=1.0,
                    sequence=0,
                    discontinuity=False
                ),
                HLSSegment(
                    url="https://example.com/seg2.ts",
                    duration=1.5,
                    sequence=1,
                    discontinuity=False
                )
            ],
            endlist=True
        )
        
        m3u8 = manager.playlist_to_m3u8(playlist)
        
        # Check format
        assert "#EXTM3U" in m3u8
        assert "#EXT-X-VERSION:3" in m3u8
        assert "#EXT-X-TARGETDURATION:1" in m3u8
        assert "#EXT-X-MEDIA-SEQUENCE:0" in m3u8
        assert "#EXT-X-ENDLIST" in m3u8
        
        # Check segments
        assert "#EXTINF:1.000," in m3u8
        assert "#EXTINF:1.500," in m3u8
        assert "https://example.com/seg1.ts" in m3u8
        assert "https://example.com/seg2.ts" in m3u8
    
    def test_playlist_to_m3u8_with_discontinuity(self):
        """Test M3U8 format with discontinuity"""
        manager = HLSManager(None)
        
        playlist = HLSPlaylist(
            version=3,
            target_duration=1.0,
            media_sequence=0,
            segments=[
                HLSSegment(
                    url="https://example.com/seg1.ts",
                    duration=1.0,
                    sequence=0,
                    discontinuity=False
                ),
                HLSSegment(
                    url="https://example.com/seg2.ts",
                    duration=1.0,
                    sequence=1,
                    discontinuity=True  # Mark discontinuity
                )
            ],
            endlist=True
        )
        
        m3u8 = manager.playlist_to_m3u8(playlist)
        
        # Check for discontinuity marker
        assert "#EXT-X-DISCONTINUITY" in m3u8

