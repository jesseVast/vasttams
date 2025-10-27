"""
Segment table schemas for TAMS.

This module defines the PyArrow schemas for segment-related tables.
"""

import pyarrow as pa
from typing import List


def get_segments_schema() -> pa.Schema:
    """Get segments table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("flow_id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("object_id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("timerange_start", pa.string(), nullable=True),  # TAMS timerange format
        pa.field("timerange_end", pa.string(), nullable=True),   # TAMS timerange format
        pa.field("ts_offset", pa.string(), nullable=True),       # TAMS timestamp format
        pa.field("last_duration", pa.string(), nullable=True),   # TAMS timestamp format
        pa.field("sample_offset", pa.int64(), nullable=True),
        pa.field("sample_count", pa.int64(), nullable=True),
        pa.field("get_urls", pa.string(), nullable=True),        # JSON string
        pa.field("key_frame_count", pa.int32(), nullable=True),
        pa.field("created", pa.timestamp("ns"), nullable=True),
    ])


def get_segments_projections() -> List[List[str]]:
    """Get segments table projection definitions"""
    return [
        ["id"],
        ["id", "flow_id"],
        ["flow_id", "timerange_start"],
        ["flow_id", "timerange_end"]
    ]

