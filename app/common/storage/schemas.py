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
# Shared Tags Schema
# ============================================================================

def _get_tags_schema() -> pa.Schema:
    """Get tags table schema
    
    Tags are used across multiple resources, so the schema stays in common.
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
