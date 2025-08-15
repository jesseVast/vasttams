"""
Timerange utilities for TAMS API

This module provides flexible timerange generation and validation functions
to replace hardcoded timeranges throughout the codebase.
"""

import re
from typing import Optional, Tuple
from datetime import datetime, timedelta


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
