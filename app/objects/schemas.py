"""
Object table schemas for TAMS.

This module defines the PyArrow schemas for object-related tables.
"""

import pyarrow as pa


def get_objects_schema() -> pa.Schema:
    """Get objects table schema - TAMS 8.0 with timerange support"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("referenced_by_flows", pa.string(), nullable=True),  # JSON array string
        pa.field("first_referenced_by_flow", pa.string(), nullable=True),
        pa.field("timerange", pa.string(), nullable=True),  # TAMS 8.0: Required timerange field
        pa.field("size", pa.int64(), nullable=True),
        pa.field("created", pa.timestamp("ns"), nullable=True),
    ])


def get_object_instances_schema() -> pa.Schema:
    """Get object instances table schema - TAMS 8.0"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # Instance ID
        pa.field("object_id", pa.string(), nullable=True),  # Foreign key to objects
        pa.field("label", pa.string(), nullable=True),  # Human-readable label (required for uncontrolled)
        pa.field("storage_id", pa.string(), nullable=True),  # Storage backend identifier
        pa.field("url", pa.string(), nullable=True),  # URL for accessing this instance
        pa.field("controlled", pa.bool_(), nullable=True),  # Whether TAMS controls this instance
        pa.field("metadata", pa.string(), nullable=True),  # Additional metadata as JSON
        pa.field("created", pa.timestamp("ns"), nullable=True),
    ])

