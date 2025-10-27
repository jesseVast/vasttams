"""
Source table schemas for TAMS.

This module defines the PyArrow schemas for source-related tables.
"""

import pyarrow as pa


def get_sources_schema() -> pa.Schema:
    """Get sources table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("format", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("label", pa.string(), nullable=True),
        pa.field("description", pa.string(), nullable=True),
        pa.field("created_by", pa.string(), nullable=True),
        pa.field("updated_by", pa.string(), nullable=True),
        pa.field("created", pa.timestamp("ns"), nullable=True),
        pa.field("updated", pa.timestamp("ns"), nullable=True)
    ])


def get_source_collections_schema() -> pa.Schema:
    """Get source_collections table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("source_id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("collection_name", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("created", pa.timestamp("ns"), nullable=True),
    ])

