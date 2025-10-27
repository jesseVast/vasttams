"""
Segment table schemas for TAMS.

This module defines the PyArrow schemas for segment-related tables.
"""

import pyarrow as pa


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
        pa.field("created", pa.timestamp("ns"), nullable=True),
    ])

