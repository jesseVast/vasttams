"""
Flow table schema for TAMS.

This module defines the PyArrow schema for the flows table.
"""

import pyarrow as pa
from typing import List


def get_flows_schema() -> pa.Schema:
    """Get flows table schema - TAMS 8.0 with VFR support"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("source_id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("format", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("label", pa.string(), nullable=True),
        pa.field("description", pa.string(), nullable=True),
        pa.field("created_by", pa.string(), nullable=True),
        pa.field("updated_by", pa.string(), nullable=True),
        pa.field("metadata_version", pa.string(), nullable=True),
        pa.field("generation", pa.int64(), nullable=True),
        pa.field("created", pa.timestamp("ns"), nullable=True),
        pa.field("metadata_updated", pa.timestamp("ns"), nullable=True),
        pa.field("segments_updated", pa.timestamp("ns"), nullable=True),
        pa.field("read_only", pa.bool_(), nullable=True),
        pa.field("codec", pa.string(), nullable=True),
        pa.field("container", pa.string(), nullable=True),
        pa.field("avg_bit_rate", pa.int64(), nullable=True),
        pa.field("max_bit_rate", pa.int64(), nullable=True),
        pa.field("segment_duration", pa.string(), nullable=True),  # JSON string
        pa.field("timerange", pa.string(), nullable=True),  # JSON string
        pa.field("flow_collection", pa.string(), nullable=True),  # JSON string
        pa.field("collected_by", pa.string(), nullable=True),  # JSON string
        pa.field("container_mapping", pa.string(), nullable=True),  # JSON string
        pa.field("essence_parameters", pa.string(), nullable=True),  # JSON string with VFR support
        pa.field("vfr", pa.bool_(), nullable=True)  # TAMS 8.0: Variable frame rate flag
    ])


def get_flow_collections_schema() -> pa.Schema:
    """Get flow_collections table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("flow_id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("collection_name", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("created", pa.timestamp("ns"), nullable=True),
    ])


def get_flow_object_references_schema() -> pa.Schema:
    """Get flow_object_references table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("flow_id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("object_id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("created", pa.timestamp("ns"), nullable=True),
    ])


def get_flows_projections() -> List[List[str]]:
    """Get flows table projection definitions for performance optimization"""
    return [
        ["id"],
        ["id", "source_id"],
        ["id", "format"],
        ["source_id", "format"]
    ]


def get_flow_collections_projections() -> List[List[str]]:
    """Get flow_collections table projection definitions"""
    return [
        ["id"],
        ["id", "flow_id"],
        ["flow_id"]
    ]


def get_flow_object_references_projections() -> List[List[str]]:
    """Get flow_object_references table projection definitions"""
    return [
        ["flow_id"],
        ["object_id"],
        ["flow_id", "object_id"]
    ]

