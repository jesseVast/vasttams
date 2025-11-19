"""
Object table schemas for TAMS.

This module defines the PyArrow schemas for object-related tables.
"""

import pyarrow as pa
from typing import List


def get_objects_schema() -> pa.Schema:
    """Get objects table schema - TAMS 8.0 with timerange support
    
    Note: referenced_by_flows is computed dynamically from segments table via JOINs,
    so it's not stored in the database schema. It's required by TAMS spec in API responses
    but computed on-the-fly for data consistency.
    """
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("first_referenced_by_flow", pa.string(), nullable=True),  # Computed dynamically, kept for caching/performance
        pa.field("timerange", pa.string(), nullable=True),  # TAMS 8.0: Required timerange field
        pa.field("size", pa.int64(), nullable=True),
        pa.field("metadata", pa.string(), nullable=True),  # JSON metadata (storage_id, storage_path, etc.)
        pa.field("created", pa.timestamp("ns"), nullable=True),
        pa.field("vector", pa.fixed_size_list(pa.float32(), 768), nullable=True),  # 768-dim vector embedding
        pa.field("summary", pa.string(), nullable=True),  # Text summary
        pa.field("embedding_date", pa.timestamp("ns"), nullable=True),  # Date of embedding
        pa.field("embedding_model", pa.string(), nullable=True),  # Embedding model name
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


def get_objects_projections() -> List[List[str]]:
    """Get objects table projection definitions"""
    return [
        ["id"],
        ["id", "first_referenced_by_flow"],
        ["created"]
    ]


def get_object_instances_projections() -> List[List[str]]:
    """Get object_instances table projection definitions"""
    return [
        ["object_id"],
        ["object_id", "storage_id"],
        ["id"]
    ]

