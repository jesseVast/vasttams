#!/usr/bin/env python3
"""
Tests for Timerange Utilities

Tests the timerange generation and parsing functions in src/vasttams/core/timerange_utils.py
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.core.timerange_utils import (
    TimerangeGenerator,
    get_default_timerange,
    get_long_timerange,
    parse_tams_timerange
)


class TestTimerangeGenerator:
    """Test TimerangeGenerator class"""
    
    def test_generate_default_timerange(self):
        """Test generating default timerange"""
        result = TimerangeGenerator.generate_default_timerange(300)
        # Format is [00:00:00.000,MM:SS.mmm) - note the hours in start
        assert result == "[00:00:00.000,05:00.000)"
        assert result.startswith("[00:00:00.000,")
        assert result.endswith(")")
    
    def test_generate_default_timerange_60_seconds(self):
        """Test generating timerange for 60 seconds"""
        result = TimerangeGenerator.generate_default_timerange(60)
        assert result == "[00:00:00.000,01:00.000)"
    
    def test_generate_default_timerange_invalid_duration(self):
        """Test that invalid duration raises ValueError"""
        with pytest.raises(ValueError, match="Duration must be positive"):
            TimerangeGenerator.generate_default_timerange(0)
        with pytest.raises(ValueError, match="Duration must be positive"):
            TimerangeGenerator.generate_default_timerange(-1)
    
    def test_generate_tams_timerange(self):
        """Test generating TAMS format timerange"""
        result = TimerangeGenerator.generate_tams_timerange(300)
        assert result == "[0:0_5:0]"
        assert result.startswith("[0:0_")
        assert result.endswith("]")
    
    def test_generate_timerange_from_duration(self):
        """Test generating timerange from start and duration"""
        result = TimerangeGenerator.generate_timerange_from_duration(0, 300)
        # Format is [MM:SS.mmm,MM:SS.mmm) - no hours
        assert result == "[00:00.000,05:00.000)"
        
        result = TimerangeGenerator.generate_timerange_from_duration(300, 300)
        assert result == "[05:00.000,10:00.000)"
    
    def test_generate_timerange_from_duration_invalid(self):
        """Test that invalid parameters raise ValueError"""
        with pytest.raises(ValueError, match="Start time cannot be negative"):
            TimerangeGenerator.generate_timerange_from_duration(-1, 300)
        with pytest.raises(ValueError, match="Duration must be positive"):
            TimerangeGenerator.generate_timerange_from_duration(0, 0)
    
    def test_generate_timerange_from_timestamps(self):
        """Test generating timerange from datetime objects"""
        start = datetime(2024, 1, 1, 10, 0, 0)
        end = datetime(2024, 1, 1, 10, 5, 0)
        result = TimerangeGenerator.generate_timerange_from_timestamps(start, end)
        # Result format is [MM:SS.mmm,MM:SS.mmm) - converts hours*3600 + minutes*60 + seconds
        # 10:00 = 10*3600 + 0*60 + 0 = 36000 seconds = 600 minutes = 10:00.000
        assert result.startswith("[")
        assert result.endswith(")")
        # Should contain time information
        assert ":" in result
    
    def test_generate_timerange_from_timestamps_invalid(self):
        """Test that start >= end raises ValueError"""
        start = datetime(2024, 1, 1, 10, 5, 0)
        end = datetime(2024, 1, 1, 10, 0, 0)
        with pytest.raises(ValueError, match="Start time must be before end time"):
            TimerangeGenerator.generate_timerange_from_timestamps(start, end)
    
    def test_parse_timerange(self):
        """Test parsing timerange string - format is [MM:SS.mmm,MM:SS.mmm)"""
        # The parse_timerange expects format [MM:SS.mmm,MM:SS.mmm) where MM is 2 digits
        start, end = TimerangeGenerator.parse_timerange("[00:00.000,05:00.000)")
        assert start == 0
        assert end == 300
        
        start, end = TimerangeGenerator.parse_timerange("[05:00.000,10:00.000)")
        assert start == 300
        assert end == 600
    
    def test_parse_timerange_invalid(self):
        """Test that invalid timerange raises ValueError"""
        with pytest.raises(ValueError, match="Invalid timerange format"):
            TimerangeGenerator.parse_timerange("invalid")
        with pytest.raises(ValueError):
            TimerangeGenerator.parse_timerange("[00:00:00)")
    
    def test_get_duration_seconds(self):
        """Test getting duration from timerange"""
        duration = TimerangeGenerator.get_duration_seconds("[00:00.000,05:00.000)")
        assert duration == 300
        
        duration = TimerangeGenerator.get_duration_seconds("[05:00.000,10:00.000)")
        assert duration == 300
    
    def test_is_valid_timerange(self):
        """Test validating timerange strings"""
        assert TimerangeGenerator.is_valid_timerange("[00:00.000,05:00.000)") is True
        assert TimerangeGenerator.is_valid_timerange("[05:00.000,10:00.000)") is True
        assert TimerangeGenerator.is_valid_timerange("invalid") is False
        assert TimerangeGenerator.is_valid_timerange("") is False


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_get_default_timerange(self):
        """Test get_default_timerange function"""
        result = get_default_timerange(300)
        assert result == "[00:00:00.000,05:00.000)"
    
    def test_get_tams_timerange(self):
        """Test get_tams_timerange via TimerangeGenerator"""
        result = TimerangeGenerator.generate_tams_timerange(300)
        assert result == "[0:0_5:0]"
    
    def test_get_long_timerange(self):
        """Test get_long_timerange function"""
        result = get_long_timerange()
        assert result == "[00:00:00.000,15:00.000)"  # 900 seconds = 15 minutes
    
    def test_parse_tams_timerange_standard_format(self):
        """Test parsing standard timerange format"""
        # parse_tams_timerange can handle various formats
        start, end = parse_tams_timerange("[00:00:00.000,05:00.000)")
        assert start == 0.0
        assert end == 300.0
    
    def test_parse_tams_timerange_tams_format(self):
        """Test parsing TAMS format timerange"""
        start, end = parse_tams_timerange("[0:0_10:0)")
        assert start == 0.0
        assert end == 10.0
    
    def test_parse_tams_timerange_invalid(self):
        """Test parsing invalid timerange returns default"""
        start, end = parse_tams_timerange("invalid")
        assert start == 0.0
        assert end == 0.0

