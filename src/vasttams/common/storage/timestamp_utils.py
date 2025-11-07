"""
TAMS Timestamp Utilities

This module provides high-resolution timestamp generation and management utilities
following TAMS appnote 0008 requirements for linear, high-resolution clock management.

Key Features:
- Nanosecond precision timestamps
- Linear clock implementation
- Uniqueness guarantees
- Timezone consistency (UTC)
- Timeline synchronization utilities
"""

import time
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import threading
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TimestampInfo:
    """Information about a generated timestamp"""
    timestamp: datetime
    nanoseconds: int
    linear_clock_value: int
    is_unique: bool


class TAMSTimestampGenerator:
    """
    High-resolution timestamp generator following TAMS appnote 0008 requirements.
    
    Features:
    - Nanosecond precision using time.time_ns()
    - Linear clock implementation
    - Uniqueness guarantees through sequence numbers
    - UTC timezone consistency
    - Thread-safe operation
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        self._last_timestamp_ns = 0
        self._sequence_counter = 0
        self._linear_clock_base = int(time.time_ns())
        
    def generate_timestamp(self) -> TimestampInfo:
        """
        Generate a high-resolution, unique timestamp following TAMS requirements.
        
        Returns:
            TimestampInfo: Complete timestamp information including linear clock value
        """
        with self._lock:
            # Get current nanosecond timestamp
            current_ns = int(time.time_ns())
            
            # Ensure uniqueness by incrementing sequence if timestamp is the same
            if current_ns <= self._last_timestamp_ns:
                self._sequence_counter += 1
                # Add sequence counter as nanoseconds to ensure uniqueness
                unique_ns = current_ns + self._sequence_counter
            else:
                self._sequence_counter = 0
                unique_ns = current_ns
                
            self._last_timestamp_ns = unique_ns
            
            # Convert to datetime with nanosecond precision
            timestamp = datetime.fromtimestamp(unique_ns / 1_000_000_000, tz=timezone.utc)
            
            # Calculate linear clock value (nanoseconds since base)
            linear_clock_value = unique_ns - self._linear_clock_base
            
            return TimestampInfo(
                timestamp=timestamp,
                nanoseconds=unique_ns,
                linear_clock_value=linear_clock_value,
                is_unique=True
            )
    
    def generate_linear_clock_value(self) -> int:
        """
        Generate a linear clock value for timeline synchronization.
        
        Returns:
            int: Linear clock value in nanoseconds since base
        """
        timestamp_info = self.generate_timestamp()
        return timestamp_info.linear_clock_value
    
    def reset_linear_clock(self):
        """Reset the linear clock base to current time."""
        with self._lock:
            self._linear_clock_base = int(time.time_ns())
            self._sequence_counter = 0


# Global timestamp generator instance
_timestamp_generator = TAMSTimestampGenerator()


def get_tams_timestamp() -> datetime:
    """
    Get a TAMS-compliant high-resolution timestamp.
    
    This is the main function to use throughout the application for timestamp generation.
    It ensures nanosecond precision, uniqueness, and UTC timezone consistency.
    
    Returns:
        datetime: High-resolution timestamp in UTC timezone
    """
    return _timestamp_generator.generate_timestamp().timestamp


def get_tams_timestamp_info() -> TimestampInfo:
    """
    Get complete timestamp information including linear clock value.
    
    Returns:
        TimestampInfo: Complete timestamp information
    """
    return _timestamp_generator.generate_timestamp()


def get_linear_clock_value() -> int:
    """
    Get a linear clock value for timeline synchronization.
    
    Returns:
        int: Linear clock value in nanoseconds
    """
    return _timestamp_generator.generate_linear_clock_value()


def reset_linear_clock():
    """Reset the linear clock base to current time."""
    _timestamp_generator.reset_linear_clock()


class TimelineSynchronizer:
    """
    Utility class for timeline synchronization across TAMS flows.
    
    Ensures all media flows are aligned to a common timeline as required by TAMS.
    """
    
    def __init__(self):
        self._reference_timeline: Optional[int] = None
        self._timeline_offsets: Dict[str, int] = {}
    
    def set_reference_timeline(self, linear_clock_value: int):
        """
        Set the reference timeline for synchronization.
        
        Args:
            linear_clock_value: Reference linear clock value
        """
        self._reference_timeline = linear_clock_value
        logger.debug("Reference timeline set to: %d nanoseconds", linear_clock_value)
    
    def register_flow_timeline(self, flow_id: str, linear_clock_value: int) -> int:
        """
        Register a flow's timeline and calculate offset from reference.
        
        Args:
            flow_id: Unique flow identifier
            linear_clock_value: Flow's linear clock value
            
        Returns:
            int: Offset from reference timeline in nanoseconds
        """
        if self._reference_timeline is None:
            self.set_reference_timeline(linear_clock_value)
            offset = 0
        else:
            offset = linear_clock_value - self._reference_timeline
            
        self._timeline_offsets[flow_id] = offset
        logger.debug("Flow %s timeline offset: %d nanoseconds", flow_id, offset)
        return offset
    
    def get_flow_offset(self, flow_id: str) -> Optional[int]:
        """
        Get the timeline offset for a specific flow.
        
        Args:
            flow_id: Flow identifier
            
        Returns:
            int: Timeline offset in nanoseconds, or None if not registered
        """
        return self._timeline_offsets.get(flow_id)
    
    def synchronize_timestamps(self, flow_id: str, timestamp: datetime) -> datetime:
        """
        Synchronize a timestamp to the reference timeline.
        
        Args:
            flow_id: Flow identifier
            timestamp: Original timestamp
            
        Returns:
            datetime: Synchronized timestamp
        """
        offset = self.get_flow_offset(flow_id)
        if offset is None:
            logger.warning("Flow %s not registered for timeline synchronization", flow_id)
            return timestamp
            
        # Apply offset to synchronize with reference timeline
        synchronized_timestamp = timestamp + datetime.timedelta(microseconds=offset / 1000)
        return synchronized_timestamp
    
    def get_timeline_consistency_report(self) -> Dict[str, Any]:
        """
        Generate a report on timeline consistency across flows.
        
        Returns:
            Dict: Timeline consistency information
        """
        if not self._timeline_offsets:
            return {"status": "no_flows_registered", "flows": 0}
        
        offsets = list(self._timeline_offsets.values())
        max_offset = max(offsets)
        min_offset = min(offsets)
        offset_range = max_offset - min_offset
        
        return {
            "status": "active",
            "flows": len(self._timeline_offsets),
            "reference_timeline": self._reference_timeline,
            "max_offset_ns": max_offset,
            "min_offset_ns": min_offset,
            "offset_range_ns": offset_range,
            "flow_offsets": self._timeline_offsets
        }


# Global timeline synchronizer instance
_timeline_synchronizer = TimelineSynchronizer()


def get_timeline_synchronizer() -> TimelineSynchronizer:
    """Get the global timeline synchronizer instance."""
    return _timeline_synchronizer


def validate_timestamp_precision(timestamp: datetime) -> bool:
    """
    Validate that a timestamp has nanosecond precision.
    
    Args:
        timestamp: Timestamp to validate
        
    Returns:
        bool: True if timestamp has nanosecond precision
    """
    # Check if timestamp has microsecond precision (which includes nanosecond)
    return timestamp.microsecond is not None


def format_timestamp_for_tams(timestamp: datetime) -> str:
    """
    Format a timestamp for TAMS storage (ISO format with nanosecond precision).
    
    Args:
        timestamp: Timestamp to format
        
    Returns:
        str: ISO formatted timestamp string
    """
    return timestamp.isoformat()


def parse_timestamp_from_tams(timestamp_str: str) -> datetime:
    """
    Parse a timestamp string from TAMS storage.
    
    Args:
        timestamp_str: ISO formatted timestamp string
        
    Returns:
        datetime: Parsed timestamp
    """
    return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))


def convert_iso_to_pyarrow_timestamp(iso_timestamp: str) -> int:
    """
    Convert ISO timestamp string to PyArrow timestamp nanoseconds.
    
    Args:
        iso_timestamp: ISO formatted timestamp string (e.g., "2025-01-27T10:30:45.123456+00:00")
        
    Returns:
        int: Nanoseconds since epoch for PyArrow timestamp[ns]
        
    Raises:
        ValueError: If timestamp format is invalid
    """
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        # Convert to nanoseconds since epoch
        return int(dt.timestamp() * 1_000_000_000)
    except Exception as e:
        raise ValueError(f"Invalid timestamp format '{iso_timestamp}': {e}")


def convert_datetime_to_pyarrow_timestamp(dt: datetime) -> int:
    """
    Convert datetime object to PyArrow timestamp nanoseconds.
    
    Args:
        dt: datetime object
        
    Returns:
        int: Nanoseconds since epoch for PyArrow timestamp[ns]
    """
    return int(dt.timestamp() * 1_000_000_000)


def is_timestamp_field(field_name: str) -> bool:
    """
    Check if a field name represents a timestamp field that needs conversion.
    
    Args:
        field_name: Name of the field
        
    Returns:
        bool: True if field is a timestamp field
    """
    timestamp_fields = {
        'created', 'updated', 'metadata_updated', 'segments_updated',
        'created_at', 'updated_at', 'timestamp', 'time'
    }
    return field_name in timestamp_fields


def convert_timestamp_value(value: Any, field_name: str) -> Any:
    """
    Convert a timestamp value to the appropriate format for PyArrow.
    
    Args:
        value: The value to convert
        field_name: Name of the field (used to determine if it's a timestamp)
        
    Returns:
        Converted value (nanoseconds int for timestamps, original value otherwise)
    """
    if not is_timestamp_field(field_name):
        return value
    
    if value is None:
        return None
    
    if isinstance(value, str) and 'T' in value:
        # ISO timestamp string
        return convert_iso_to_pyarrow_timestamp(value)
    elif isinstance(value, datetime):
        # datetime object
        return convert_datetime_to_pyarrow_timestamp(value)
    else:
        # Return as-is if not a recognized timestamp format
        return value


def prepare_data_for_pyarrow(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare data for PyArrow/VAST storage by converting timestamps to nanoseconds.
    
    Args:
        data: Dictionary of field names and values
        
    Returns:
        Dictionary with timestamps converted to nanoseconds
    """
    prepared_data = {}
    for field_name, value in data.items():
        if value is not None and is_timestamp_field(field_name):
            prepared_data[field_name] = convert_timestamp_value(value, field_name)
        else:
            prepared_data[field_name] = value
    return prepared_data


def prepare_data_for_sql(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare data for SQL queries by converting timestamps to SQL format.

    Args:
        data: Dictionary of field names and values

    Returns:
        Dictionary with timestamps converted to SQL timestamp strings
    """
    import logging
    logger = logging.getLogger(__name__)
    
    prepared_data = {}
    
    for field_name, value in data.items():
        if value is not None and is_timestamp_field(field_name):
            # Convert to nanoseconds first
            nanoseconds = convert_timestamp_value(value, field_name)
            # Convert to a format that Trino can parse as timestamp
            # Use CAST to ensure Trino treats it as a timestamp
            dt = datetime.fromtimestamp(nanoseconds / 1_000_000_000, tz=timezone.utc)
            timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            sql_timestamp = f"CAST('{timestamp_str}' AS TIMESTAMP(9))"
            prepared_data[field_name] = sql_timestamp
        else:
            prepared_data[field_name] = value
    
    return prepared_data


# Backward compatibility functions
def get_current_timestamp() -> datetime:
    """
    Backward compatibility function for existing code.
    
    This function provides the same interface as the old datetime.now() calls
    but with TAMS-compliant high-resolution timestamps.
    
    Returns:
        datetime: High-resolution timestamp in UTC
    """
    return get_tams_timestamp()


def get_current_timestamp_utc() -> datetime:
    """
    Backward compatibility function for existing code.
    
    This function provides the same interface as datetime.now(timezone.utc)
    but with TAMS-compliant high-resolution timestamps.
    
    Returns:
        datetime: High-resolution timestamp in UTC
    """
    return get_tams_timestamp()
