"""
TAMS Table Schemas Registry

This module aggregates PyArrow schemas from resource modules.
Schemas are now defined in their respective resource modules for better organization.
"""

import pyarrow as pa
from typing import Dict, List, Optional
import logging

# Import schemas from resource modules
from ...flows.schemas import (
    get_flows_schema, get_flow_collections_schema, get_flow_object_references_schema
)
from ...sources.schemas import (
    get_sources_schema, get_source_collections_schema
)
from ...segments.schemas import get_segments_schema
from ...objects.schemas import (
    get_objects_schema, get_object_instances_schema
)
from ...service.schemas import (
    get_webhooks_schema, get_deletion_requests_schema
)
from ...auth.schemas import (
    get_users_schema, get_api_tokens_schema, get_refresh_tokens_schema, 
    get_auth_logs_schema, get_auth_provider_configs_schema
)

logger = logging.getLogger(__name__)


def get_tams_table_schemas() -> Dict[str, pa.Schema]:
    """
    Get all TAMS table schemas from resource modules.
    
    Returns:
        Dict[str, pa.Schema]: Dictionary mapping table names to PyArrow schemas
    """
    return {
        "sources": get_sources_schema(),
        "flows": get_flows_schema(),
        "segments": get_segments_schema(),
        "objects": get_objects_schema(),
        "object_instances": get_object_instances_schema(),
        "flow_object_references": get_flow_object_references_schema(),
        "flow_collections": get_flow_collections_schema(),
        "source_collections": get_source_collections_schema(),
        "webhooks": get_webhooks_schema(),
        "deletion_requests": get_deletion_requests_schema(),
        "users": get_users_schema(),
        "api_tokens": get_api_tokens_schema(),
        "refresh_tokens": get_refresh_tokens_schema(),
        "auth_logs": get_auth_logs_schema(),
        "auth_provider_configs": get_auth_provider_configs_schema(),
        "tags": _get_tags_schema(),  # Tags stay here as shared
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
        ],
        "tags": [
            ["id"],
            ["entity_type", "entity_id"],
            ["entity_type", "tag_name"],
            ["entity_id", "tag_name"],
            ["created_at"],
            ["updated_at"],
            ["deleted_date"]
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
        pa.field("created", pa.timestamp("ns"), nullable=True),
        pa.field("updated", pa.timestamp("ns"), nullable=True)
    ])


def _get_flows_schema() -> pa.Schema:
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
        pa.field("created", pa.timestamp("ns"), nullable=True),
    ])


def _get_objects_schema() -> pa.Schema:
    """Get objects table schema - TAMS 8.0 with timerange support"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("referenced_by_flows", pa.string(), nullable=True),  # JSON array string
        pa.field("first_referenced_by_flow", pa.string(), nullable=True),
        pa.field("timerange", pa.string(), nullable=True),  # TAMS 8.0: Required timerange field
        pa.field("size", pa.int64(), nullable=True),
        pa.field("created", pa.timestamp("ns"), nullable=True),
    ])


def _get_object_instances_schema() -> pa.Schema:
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


def _get_flow_object_references_schema() -> pa.Schema:
    """Get flow_object_references table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("flow_id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("object_id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("created", pa.timestamp("ns"), nullable=True),
    ])


def _get_flow_collections_schema() -> pa.Schema:
    """Get flow_collections table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("flow_id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("collection_name", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("created", pa.timestamp("ns"), nullable=True),
    ])


def _get_source_collections_schema() -> pa.Schema:
    """Get source_collections table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("source_id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("collection_name", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("created", pa.timestamp("ns"), nullable=True),
    ])


def _get_webhooks_schema() -> pa.Schema:
    """Get webhooks table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("url", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("enabled", pa.bool_(), nullable=True),
        pa.field("events", pa.string(), nullable=True),  # JSON array string
        pa.field("filters", pa.string(), nullable=True),  # JSON string
        pa.field("created", pa.timestamp("ns"), nullable=True),
        pa.field("updated", pa.timestamp("ns"), nullable=True)
    ])


def _get_deletion_requests_schema() -> pa.Schema:
    """Get deletion_requests table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("status", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("requested_by", pa.string(), nullable=True),
        pa.field("reason", pa.string(), nullable=True),
        pa.field("created", pa.timestamp("ns"), nullable=True),
        pa.field("completed", pa.timestamp("ns"), nullable=True),
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
        pa.field("created", pa.timestamp("ns"), nullable=True),
        pa.field("updated", pa.timestamp("ns"), nullable=True),
        pa.field("last_login", pa.timestamp("ns"), nullable=True),
    ])


def _get_api_tokens_schema() -> pa.Schema:
    """Get api_tokens table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("user_id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("token_hash", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("name", pa.string(), nullable=True),
        pa.field("expires_at", pa.timestamp("ns"), nullable=True),
        pa.field("created", pa.timestamp("ns"), nullable=True),
        pa.field("last_used", pa.timestamp("ns"), nullable=True),
    ])


def _get_refresh_tokens_schema() -> pa.Schema:
    """Get refresh_tokens table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("user_id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("token_hash", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("expires_at", pa.timestamp("ns"), nullable=True),
        pa.field("created", pa.timestamp("ns"), nullable=True),
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
        pa.field("created", pa.timestamp("ns"), nullable=True),
    ])


def _get_tags_schema() -> pa.Schema:
    """Get tags table schema"""
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
