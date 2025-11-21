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
    get_flows_schema, get_flow_collections_schema, get_flow_object_references_schema,
    get_flows_projections, get_flow_collections_projections, get_flow_object_references_projections
)
from ...sources.schemas import (
    get_sources_schema, get_source_collections_schema,
    get_sources_projections, get_source_collections_projections
)
from ...segments.schemas import get_segments_schema, get_segments_projections
from ...objects.schemas import (
    get_objects_schema, get_object_instances_schema,
    get_objects_projections, get_object_instances_projections
)
from ...vast.schemas import (
    get_object_vector_schema, get_object_vector_projections
)
from ...service.schemas import (
    get_deletion_requests_schema, get_deletion_requests_projections
)
from ...webhooks.schemas import get_webhooks_schema, get_webhooks_projections
from ...auth.schemas import (
    get_users_schema, get_api_tokens_schema, get_refresh_tokens_schema, 
    get_auth_logs_schema, get_auth_provider_configs_schema,
    get_users_projections, get_api_tokens_projections, get_refresh_tokens_projections,
    get_auth_logs_projections, get_auth_provider_configs_projections
)
from ..tags.schemas import get_tags_schema, get_tags_projections
from ...storagebackends.schemas import get_storage_backends_schema, get_storage_backends_projections

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
        "object_vector": get_object_vector_schema(),
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
        "tags": get_tags_schema(),
        "storage_backends": get_storage_backends_schema(),
    }


def get_table_projections() -> Dict[str, List[List[str]]]:
    """
    Get table projection definitions from resource modules.
    
    Returns:
        Dict[str, List[List[str]]]: Dictionary mapping table names to projection column lists
    """
    return {
        "sources": get_sources_projections(),
        "flows": get_flows_projections(),
        "segments": get_segments_projections(),
        "objects": get_objects_projections(),
        "object_vector": get_object_vector_projections(),
        "flow_object_references": get_flow_object_references_projections(),
        "flow_collections": get_flow_collections_projections(),
        "source_collections": get_source_collections_projections(),
        "webhooks": get_webhooks_projections(),
        "deletion_requests": get_deletion_requests_projections(),
        "users": get_users_projections(),
        "api_tokens": get_api_tokens_projections(),
        "refresh_tokens": get_refresh_tokens_projections(),
        "auth_logs": get_auth_logs_projections(),
        "auth_provider_configs": get_auth_provider_configs_projections(),
        "tags": get_tags_projections(),
        "storage_backends": get_storage_backends_projections(),
    }


