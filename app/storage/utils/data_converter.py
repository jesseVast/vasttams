"""
Data conversion utilities for storage operations

This module provides utilities for converting data between different formats
used in storage operations.
"""

import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone
import json

logger = logging.getLogger(__name__)


class DataConverter:
    """
    Utility class for converting data between different formats
    """
    
    @staticmethod
    def datetime_to_iso(dt: datetime) -> str:
        """
        Convert datetime to ISO format string
        
        Args:
            dt: Datetime object to convert
            
        Returns:
            str: ISO format string
        """
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    
    @staticmethod
    def iso_to_datetime(iso_str: str) -> Optional[datetime]:
        """
        Convert ISO format string to datetime
        
        Args:
            iso_str: ISO format string
            
        Returns:
            datetime: Datetime object or None if parsing failed
        """
        try:
            return datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        except Exception as e:
            logger.warning("Failed to parse ISO string '%s': %s", iso_str, e)
            return None
    
    @staticmethod
    def dict_to_json(data: Dict[str, Any]) -> str:
        """
        Convert dictionary to JSON string
        
        Args:
            data: Dictionary to convert
            
        Returns:
            str: JSON string
        """
        try:
            return json.dumps(data, default=str)
        except Exception as e:
            logger.error("Failed to convert dict to JSON: %s", e)
            return "{}"
    
    @staticmethod
    def json_to_dict(json_str: str) -> Optional[Dict[str, Any]]:
        """
        Convert JSON string to dictionary
        
        Args:
            json_str: JSON string to convert
            
        Returns:
            Dict: Dictionary or None if parsing failed
        """
        try:
            return json.loads(json_str)
        except Exception as e:
            logger.warning("Failed to parse JSON string: %s", e)
            return None
    
    @staticmethod
    def bytes_to_size_human(bytes_value: int) -> str:
        """
        Convert bytes to human readable size
        
        Args:
            bytes_value: Size in bytes
            
        Returns:
            str: Human readable size string
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    
    @staticmethod
    def size_human_to_bytes(size_str: str) -> Optional[int]:
        """
        Convert human readable size to bytes
        
        Args:
            size_str: Human readable size string (e.g., "1.5 MB")
            
        Returns:
            int: Size in bytes or None if parsing failed
        """
        try:
            size_str = size_str.strip().upper()
            if size_str.endswith('B'):
                size_str = size_str[:-1].strip()
            
            # Extract number and unit
            import re
            match = re.match(r'^([\d.]+)\s*([KMGT]?)$', size_str)
            if not match:
                return None
            
            number = float(match.group(1))
            unit = match.group(2)
            
            multipliers = {'': 1, 'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}
            multiplier = multipliers.get(unit, 1)
            
            return int(number * multiplier)
            
        except Exception as e:
            logger.warning("Failed to parse size string '%s': %s", size_str, e)
            return None
    
    @staticmethod
    def timerange_to_seconds(timerange: str) -> Optional[float]:
        """
        Convert timerange string to seconds
        
        Args:
            timerange: Timerange string (e.g., "[0:0_10:0)")
            
        Returns:
            float: Duration in seconds or None if parsing failed
        """
        try:
            if not timerange or '_' not in timerange:
                return None
            
            # Extract start and end times
            parts = timerange.split('_')
            if len(parts) != 2:
                return None
            
            start_part = parts[0].strip('[]()')
            end_part = parts[1].strip('[]()')
            
            # Parse times (simplified - assumes format like "0:0")
            start_seconds = DataConverter._parse_time_to_seconds(start_part)
            end_seconds = DataConverter._parse_time_to_seconds(end_part)
            
            if start_seconds is not None and end_seconds is not None:
                return end_seconds - start_seconds
            
            return None
            
        except Exception as e:
            logger.debug("Failed to parse timerange '%s': %s", timerange, e)
            return None
    
    @staticmethod
    def _parse_time_to_seconds(time_str: str) -> Optional[float]:
        """
        Parse time string to seconds
        
        Args:
            time_str: Time string (e.g., "0:0")
            
        Returns:
            float: Time in seconds or None if parsing failed
        """
        try:
            if ':' not in time_str:
                return None
            
            parts = time_str.split(':')
            if len(parts) != 2:
                return None
            
            seconds = int(parts[0])
            subseconds = int(parts[1]) if parts[1] else 0
            
            return seconds + (subseconds / 1000000000)  # Convert nanoseconds to seconds
            
        except Exception as e:
            logger.debug("Failed to parse time '%s': %s", time_str, e)
            return None
    
    @staticmethod
    def format_timestamp(timestamp: Union[datetime, str, float], 
                        format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """
        Format timestamp to string
        
        Args:
            timestamp: Timestamp to format
            format_str: Format string
            
        Returns:
            str: Formatted timestamp string
        """
        try:
            if isinstance(timestamp, str):
                dt = DataConverter.iso_to_datetime(timestamp)
                if dt is None:
                    return timestamp
                timestamp = dt
            
            if isinstance(timestamp, (int, float)):
                timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            
            if isinstance(timestamp, datetime):
                return timestamp.strftime(format_str)
            
            return str(timestamp)
            
        except Exception as e:
            logger.warning("Failed to format timestamp: %s", e)
            return str(timestamp)
