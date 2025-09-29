"""
TAMS Table Schemas

This module defines PyArrow schemas for all TAMS database tables based on the Pydantic models.
These schemas are used for table creation and ensure consistency between the API models and database structure.
"""

import pyarrow as pa
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def get_tams_table_schemas() -> Dict[str, pa.Schema]:
    """
    Get all TAMS table schemas based on Pydantic models.
    
    Returns:
        Dict[str, pa.Schema]: Dictionary mapping table names to PyArrow schemas
    """
    return {
        "sources": _get_sources_schema(),
        "flows": _get_flows_schema(),
        "segments": _get_segments_schema(),
        "objects": _get_objects_schema(),
        "flow_object_references": _get_flow_object_references_schema(),
        "flow_collections": _get_flow_collections_schema(),
        "source_collections": _get_source_collections_schema(),
        "webhooks": _get_webhooks_schema(),
        "deletion_requests": _get_deletion_requests_schema(),
        "users": _get_users_schema(),
        "api_tokens": _get_api_tokens_schema(),
        "refresh_tokens": _get_refresh_tokens_schema(),
        "auth_logs": _get_auth_logs_schema(),
    }


def get_table_projections() -> Dict[str, List[List[str]]]:
    """
    Get table projection definitions for performance optimization.
    
    Returns:
        Dict[str, List[List[str]]]: Dictionary mapping table names to projection column lists
    """
    return {
        "sources": [
            ["id"],
            ["id", "format"],
            ["id", "created"],
            ["format", "created"]
        ],
        "flows": [
            ["id"],
            ["id", "source_id"],
            ["id", "format"],
            ["source_id", "format"]
        ],
        "segments": [
            ["id"],
            ["id", "flow_id"],
            ["flow_id", "timerange_start"],
            ["flow_id", "timerange_end"]
        ],
        "objects": [
            ["id"],
            ["id", "first_referenced_by_flow"],
            ["created"]
        ],
        "flow_object_references": [
            ["flow_id"],
            ["object_id"],
            ["flow_id", "object_id"]
        ],
        "flow_collections": [
            ["id"],
            ["id", "flow_id"],
            ["flow_id"]
        ],
        "source_collections": [
            ["id"],
            ["id", "source_id"],
            ["source_id"]
        ],
        "webhooks": [
            ["id"],
            ["id", "enabled"],
            ["enabled"]
        ],
        "deletion_requests": [
            ["id"],
            ["id", "status"],
            ["status", "created"]
        ],
        "users": [
            ["id"],
            ["username"],
            ["email"]
        ],
        "api_tokens": [
            ["id"],
            ["user_id"],
            ["token_hash"]
        ],
        "refresh_tokens": [
            ["id"],
            ["user_id"],
            ["token_hash"]
        ],
        "auth_logs": [
            ["id"],
            ["user_id"],
            ["event_type"],
            ["created"]
        ]
    }


# ============================================================================
# Individual Table Schemas
# ============================================================================

def _get_sources_schema() -> pa.Schema:
    """Get sources table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("format", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("label", pa.string(), nullable=True),
        pa.field("description", pa.string(), nullable=True),
        pa.field("created_by", pa.string(), nullable=True),
        pa.field("updated_by", pa.string(), nullable=True),
        pa.field("created", pa.timestamp("us"), nullable=True),
        pa.field("updated", pa.timestamp("us"), nullable=True),
        pa.field("tags", pa.string(), nullable=True)  # JSON string
    ])


def _get_flows_schema() -> pa.Schema:
    """Get flows table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("source_id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("format", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("label", pa.string(), nullable=True),
        pa.field("description", pa.string(), nullable=True),
        pa.field("created_by", pa.string(), nullable=True),
        pa.field("updated_by", pa.string(), nullable=True),
        pa.field("tags", pa.string(), nullable=True),  # JSON string
        pa.field("metadata_version", pa.string(), nullable=True),
        pa.field("generation", pa.int64(), nullable=True),
        pa.field("created", pa.timestamp("us"), nullable=True),
        pa.field("metadata_updated", pa.timestamp("us"), nullable=True),
        pa.field("segments_updated", pa.timestamp("us"), nullable=True),
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
        pa.field("essence_parameters", pa.string(), nullable=True)  # JSON string
    ])


def _get_segments_schema() -> pa.Schema:
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
        pa.field("created", pa.timestamp("us"), nullable=True)
    ])


def _get_objects_schema() -> pa.Schema:
    """Get objects table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("referenced_by_flows", pa.string(), nullable=True),  # JSON array string
        pa.field("first_referenced_by_flow", pa.string(), nullable=True),
        pa.field("size", pa.int64(), nullable=True),
        pa.field("created", pa.timestamp("us"), nullable=True)
    ])


def _get_flow_object_references_schema() -> pa.Schema:
    """Get flow_object_references table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("flow_id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("object_id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("created", pa.timestamp("us"), nullable=True)
    ])


def _get_flow_collections_schema() -> pa.Schema:
    """Get flow_collections table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("flow_id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("collection_name", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("created", pa.timestamp("us"), nullable=True)
    ])


def _get_source_collections_schema() -> pa.Schema:
    """Get source_collections table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("source_id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("collection_name", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("created", pa.timestamp("us"), nullable=True)
    ])


def _get_webhooks_schema() -> pa.Schema:
    """Get webhooks table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("url", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("enabled", pa.bool_(), nullable=True),
        pa.field("events", pa.string(), nullable=True),  # JSON array string
        pa.field("filters", pa.string(), nullable=True),  # JSON string
        pa.field("created", pa.timestamp("us"), nullable=True),
        pa.field("updated", pa.timestamp("us"), nullable=True)
    ])


def _get_deletion_requests_schema() -> pa.Schema:
    """Get deletion_requests table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("status", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("requested_by", pa.string(), nullable=True),
        pa.field("reason", pa.string(), nullable=True),
        pa.field("created", pa.timestamp("us"), nullable=True),
        pa.field("completed", pa.timestamp("us"), nullable=True)
    ])


def _get_users_schema() -> pa.Schema:
    """Get users table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("username", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("email", pa.string(), nullable=True),
        pa.field("password_hash", pa.string(), nullable=True),
        pa.field("is_active", pa.bool_(), nullable=True),
        pa.field("is_admin", pa.bool_(), nullable=True),
        pa.field("created", pa.timestamp("us"), nullable=True),
        pa.field("updated", pa.timestamp("us"), nullable=True),
        pa.field("last_login", pa.timestamp("us"), nullable=True)
    ])


def _get_api_tokens_schema() -> pa.Schema:
    """Get api_tokens table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("user_id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("token_hash", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("name", pa.string(), nullable=True),
        pa.field("expires_at", pa.timestamp("us"), nullable=True),
        pa.field("created", pa.timestamp("us"), nullable=True),
        pa.field("last_used", pa.timestamp("us"), nullable=True)
    ])


def _get_refresh_tokens_schema() -> pa.Schema:
    """Get refresh_tokens table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("user_id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("token_hash", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("expires_at", pa.timestamp("us"), nullable=True),
        pa.field("created", pa.timestamp("us"), nullable=True)
    ])


def _get_auth_logs_schema() -> pa.Schema:
    """Get auth_logs table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("user_id", pa.string(), nullable=True),
        pa.field("event_type", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("ip_address", pa.string(), nullable=True),
        pa.field("user_agent", pa.string(), nullable=True),
        pa.field("details", pa.string(), nullable=True),  # JSON string
        pa.field("created", pa.timestamp("us"), nullable=True)
    ])
