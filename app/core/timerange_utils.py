"""
Timerange utilities for TAMS API

This module provides flexible timerange generation and validation functions
to replace hardcoded timeranges throughout the codebase.
"""

import re
import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TimerangeGenerator:
    """Generate flexible timeranges for TAMS operations"""
    
    @staticmethod
    def generate_default_timerange(duration_seconds: int = 300) -> str:
        """
        Generate a default timerange starting from 00:00:00.000
        
        Args:
            duration_seconds: Duration in seconds (default: 300 = 5 minutes)
            
        Returns:
            Timerange string in format [00:00:00.000,MM:SS.mmm)
            
        Examples:
            >>> TimerangeGenerator.generate_default_timerange(300)
            '[00:00:00.000,05:00.000)'
            >>> TimerangeGenerator.generate_default_timerange(60)
            '[00:00:00.000,01:00.000)'
        """
        if duration_seconds <= 0:
            raise ValueError("Duration must be positive")
        
        # Calculate minutes and seconds
        minutes = duration_seconds // 60
        seconds = duration_seconds % 60
        
        # Format end time
        end_time = f"{minutes:02d}:{seconds:02d}.000"
        
        return f"[00:00:00.000,{end_time})"
    
    @staticmethod
    def generate_timerange_from_duration(start_seconds: int = 0, duration_seconds: int = 300) -> str:
        """
        Generate timerange from start time and duration
        
        Args:
            start_seconds: Start time in seconds (default: 0)
            duration_seconds: Duration in seconds (default: 300)
            
        Returns:
            Timerange string in format [MM:SS.mmm,MM:SS.mmm)
            
        Examples:
            >>> TimerangeGenerator.generate_timerange_from_duration(0, 300)
            '[00:00:00.000,05:00.000)'
            >>> TimerangeGenerator.generate_timerange_from_duration(300, 300)
            '[05:00.000,10:00.000)'
        """
        if start_seconds < 0:
            raise ValueError("Start time cannot be negative")
        if duration_seconds <= 0:
            raise ValueError("Duration must be positive")
        
        # Calculate start time
        start_minutes = start_seconds // 60
        start_secs = start_seconds % 60
        start_time = f"{start_minutes:02d}:{start_secs:02d}.000"
        
        # Calculate end time
        end_seconds = start_seconds + duration_seconds
        end_minutes = end_seconds // 60
        end_secs = end_seconds % 60
        end_time = f"{end_minutes:02d}:{end_secs:02d}.000"
        
        return f"[{start_time},{end_time})"
    
    @staticmethod
    def generate_timerange_from_timestamps(start_time: datetime, end_time: datetime) -> str:
        """
        Generate timerange from datetime objects
        
        Args:
            start_time: Start datetime
            end_time: End datetime
            
        Returns:
            Timerange string in format [MM:SS.mmm,MM:SS.mmm)
        """
        if start_time >= end_time:
            raise ValueError("Start time must be before end time")
        
        # Convert to seconds since midnight
        start_seconds = start_time.hour * 3600 + start_time.minute * 60 + start_time.second
        end_seconds = end_time.hour * 3600 + end_time.minute * 60 + end_time.second
        
        return TimerangeGenerator.generate_timerange_from_duration(start_seconds, end_seconds - start_seconds)
    
    @staticmethod
    def parse_timerange(timerange: str) -> Tuple[int, int]:
        """
        Parse timerange string to extract start and end times in seconds
        
        Args:
            timerange: Timerange string in format [MM:SS.mmm,MM:SS.mmm)
            
        Returns:
            Tuple of (start_seconds, end_seconds)
            
        Examples:
            >>> TimerangeGenerator.parse_timerange("[00:00:00.000,05:00.000)")
            (0, 300)
        """
        # Extract times using regex
        pattern = r'\[(\d{2}):(\d{2})\.(\d{3}),(\d{2}):(\d{2})\.(\d{3})\)'
        match = re.match(pattern, timerange)
        
        if not match:
            raise ValueError(f"Invalid timerange format: {timerange}")
        
        # Parse start time
        start_min, start_sec, start_ms = map(int, match.groups()[:3])
        start_seconds = start_min * 60 + start_sec
        
        # Parse end time
        end_min, end_sec, end_ms = map(int, match.groups()[3:])
        end_seconds = end_min * 60 + end_sec
        
        return start_seconds, end_seconds
    
    @staticmethod
    def get_duration_seconds(timerange: str) -> int:
        """
        Get duration in seconds from timerange string
        
        Args:
            timerange: Timerange string
            
        Returns:
            Duration in seconds
        """
        start_seconds, end_seconds = TimerangeGenerator.parse_timerange(timerange)
        return end_seconds - start_seconds
    
    @staticmethod
    def is_valid_timerange(timerange: str) -> bool:
        """
        Check if timerange string is valid
        
        Args:
            timerange: Timerange string to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            TimerangeGenerator.parse_timerange(timerange)
            return True
        except (ValueError, AttributeError):
            return False


# Convenience functions for common use cases
def get_default_timerange(duration_seconds: int = 300) -> str:
    """Get default timerange for storage allocation"""
    return TimerangeGenerator.generate_default_timerange(duration_seconds)


def get_storage_timerange(duration_seconds: int = 300) -> str:
    """Get timerange for storage operations (alias for get_default_timerange)"""
    return get_default_timerange(duration_seconds)


def get_short_timerange() -> str:
    """Get short timerange (1 minute) for quick operations"""
    return TimerangeGenerator.generate_default_timerange(60)


def get_medium_timerange() -> str:
    """Get medium timerange (5 minutes) for standard operations"""
    return TimerangeGenerator.generate_default_timerange(300)


def get_long_timerange() -> str:
    """Get long timerange (15 minutes) for extended operations"""
    return TimerangeGenerator.generate_default_timerange(900)


def parse_tams_timerange(timerange: str) -> Tuple[float, float]:
    """
    Parse TAMS timerange format to extract start and end times in seconds
    
    Args:
        timerange: TAMS timerange string (e.g., "[0:0_10:0)", "[00:00:00.000,05:00.000)")
        
    Returns:
        Tuple of (start_seconds, end_seconds)
        
    Examples:
        >>> parse_tams_timerange("[0:0_10:0)")
        (0.0, 10.0)
        >>> parse_tams_timerange("[00:00:00.000,05:00.000)")
        (0.0, 300.0)
    """
    try:
        # Remove brackets/parentheses
        clean_range = timerange.strip('[]()')
        
        if '_' in clean_range:
            # TAMS format: [start_end)
            start_str, end_str = clean_range.split('_', 1)
            
            # Parse start time
            start_seconds = _parse_tams_timestamp(start_str) if start_str else 0.0
            
            # Parse end time
            end_seconds = _parse_tams_timestamp(end_str) if end_str else float('inf')
            
        elif ',' in clean_range:
            # Standard format: [start,end)
            start_str, end_str = clean_range.split(',', 1)
            
            # Parse start time
            start_seconds = _parse_standard_timestamp(start_str) if start_str else 0.0
            
            # Parse end time
            end_seconds = _parse_standard_timestamp(end_str) if end_str else float('inf')
            
        else:
            # Single timestamp
            start_seconds = _parse_tams_timestamp(clean_range)
            end_seconds = start_seconds
            
        return start_seconds, end_seconds
        
    except Exception as e:
        logger.warning("Failed to parse TAMS timerange '%s': %s", timerange, e)
        # Return default values
        return 0.0, 0.0


def _parse_tams_timestamp(timestamp_str: str) -> float:
    """
    Parse TAMS timestamp format to seconds
    
    Args:
        timestamp_str: TAMS timestamp string (e.g., "0:0", "10:5")
        
    Returns:
        Seconds as float
    """
    if not timestamp_str:
        return 0.0
        
    if ':' in timestamp_str:
        parts = timestamp_str.split(':')
        if len(parts) == 2:
            try:
                seconds = int(parts[0])
                subseconds = int(parts[1]) if parts[1] else 0
                return seconds + (subseconds / 1000000000)  # Assuming nanoseconds
            except ValueError:
                return 0.0
    return 0.0


def _parse_standard_timestamp(timestamp_str: str) -> float:
    """
    Parse standard timestamp format to seconds
    
    Args:
        timestamp_str: Standard timestamp string (e.g., "00:00:00.000", "05:00:00.000")
        
    Returns:
        Seconds as float
    """
    if not timestamp_str:
        return 0.0
        
    try:
        # Handle format: MM:SS.mmm
        if timestamp_str.count(':') == 1:
            parts = timestamp_str.split(':')
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
                
        # Handle format: HH:MM:SS.mmm
        elif timestamp_str.count(':') == 2:
            parts = timestamp_str.split(':')
            if len(parts) == 3:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
                
    except ValueError:
        pass
        
    return 0.0


def timeranges_overlap(timerange1: str, timerange2: str) -> bool:
    """
    Check if two TAMS timeranges overlap
    
    Args:
        timerange1: First timerange string
        timerange2: Second timerange string
        
    Returns:
        True if timeranges overlap, False otherwise
        
    Examples:
        >>> timeranges_overlap("[0:0_5:0)", "[3:0_8:0)")
        True
        >>> timeranges_overlap("[0:0_5:0)", "[6:0_10:0)")
        False
    """
    try:
        start1, end1 = parse_tams_timerange(timerange1)
        start2, end2 = parse_tams_timerange(timerange2)
        
        # Check for overlap: (start1 < end2) and (end1 > start2)
        return start1 < end2 and end1 > start2
        
    except Exception as e:
        logger.warning("Failed to check timerange overlap: %s", e)
        return False


def timerange_contains(timerange1: str, timerange2: str) -> bool:
    """
    Check if timerange1 contains timerange2 (timerange2 is subset of timerange1)
    
    Args:
        timerange1: Outer timerange string
        timerange2: Inner timerange string
        
    Returns:
        True if timerange1 contains timerange2, False otherwise
    """
    try:
        start1, end1 = parse_tams_timerange(timerange1)
        start2, end2 = parse_tams_timerange(timerange2)
        
        # Check if timerange2 is contained within timerange1
        return start1 <= start2 and end1 >= end2
        
    except Exception as e:
        logger.warning("Failed to check timerange containment: %s", e)
        return False
