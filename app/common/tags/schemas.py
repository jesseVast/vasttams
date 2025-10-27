"""
Tag table schema for TAMS.

This module defines the PyArrow schema for the tags table.
Tags are used across multiple resources (flows, sources, objects, webhooks).
"""

import pyarrow as pa


def get_tags_schema() -> pa.Schema:
    """Get tags table schema
    
    Tags are used across multiple resources, so the schema lives in common/tags.
    """
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # UUID4 for the tag record
        pa.field("entity_type", pa.string(), nullable=True),  # 'source' or 'flow'
        pa.field("entity_id", pa.string(), nullable=True),  # ID of the source or flow
        pa.field("tag_name", pa.string(), nullable=True),  # Name of the tag
        pa.field("tag_value", pa.string(), nullable=True),  # Value of the tag (can be NULL)
        pa.field("created_at", pa.timestamp("ns"), nullable=True),  # When the tag was created
        pa.field("updated_at", pa.timestamp("ns"), nullable=True),  # When the tag was last updated
        pa.field("created_date", pa.timestamp("ns"), nullable=True),  # Metadata: creation date
        pa.field("updated_date", pa.timestamp("ns"), nullable=True),  # Metadata: last update date
        pa.field("deleted_date", pa.timestamp("ns"), nullable=True),  # Metadata: soft delete date (NULL if not deleted)
    ])


def get_tags_projections() -> list:
    """Get tag table projection definitions for performance optimization"""
    return [
        ["id"],
        ["entity_type", "entity_id"],
        ["entity_type", "tag_name"],
        ["entity_id", "tag_name"],
        ["created_at"],
        ["updated_at"],
        ["deleted_date"]
    ]

