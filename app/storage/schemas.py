"""
TAMS Table Schemas for VAST Database

This module contains all the PyArrow schemas for TAMS tables.
These schemas define the structure of data stored in VAST Database.
"""

import pyarrow as pa

# Source table schema
source_schema = pa.schema([
    ('id', pa.string()),
    ('format', pa.string()),
    ('label', pa.string()),
    ('description', pa.string()),
    ('created_by', pa.string()),
    ('updated_by', pa.string()),
    ('created', pa.timestamp('us')),
    ('updated', pa.timestamp('us')),  # TAMS spec requires 'updated' field name
    ('source_collection', pa.string()),  # JSON string
    ('collected_by', pa.string()),  # JSON string
    # Note: tags field removed - now stored in separate tags table
])

# Flow table schema
flow_schema = pa.schema([
    ('id', pa.string()),
    ('source_id', pa.string()),
    ('format', pa.string()),
    ('codec', pa.string()),
    ('label', pa.string()),
    ('description', pa.string()),
    ('created_by', pa.string()),
    ('updated_by', pa.string()),
    ('created', pa.timestamp('us')),
    ('metadata_updated', pa.timestamp('us')),
    ('segments_updated', pa.timestamp('us')),  # TAMS required field
    ('container', pa.string()),
    ('read_only', pa.bool_()),
    # TAMS required fields
    ('metadata_version', pa.string()),  # TAMS required field
    ('generation', pa.int32()),  # TAMS required field
    ('segment_duration', pa.string()),  # JSON string with numerator/denominator
    # Video specific
    ('frame_width', pa.int32()),
    ('frame_height', pa.int32()),
    ('frame_rate', pa.string()),  # TAMS timestamp format
    ('interlace_mode', pa.string()),
    ('color_sampling', pa.string()),
    ('color_space', pa.string()),
    ('transfer_characteristics', pa.string()),
    ('color_primaries', pa.string()),
    # Audio specific
    ('sample_rate', pa.string()),  # Changed to string for TAMS timestamp format
    ('bits_per_sample', pa.int32()),
    ('channels', pa.int32()),
    # Bit rate fields
    ('max_bit_rate', pa.int32()),  # Maximum bit rate in 1000 bits/second
    ('avg_bit_rate', pa.int32()),  # Average bit rate in 1000 bits/second
    # Multi flow specific
    ('flow_collection', pa.string()),  # JSON string
    # Note: tags field removed - now stored in separate tags table
])

# Flow segment table schema (time-series optimized)
segment_schema = pa.schema([
    ('id', pa.string()),
    ('flow_id', pa.string()),
    ('object_id', pa.string()),
    ('timerange', pa.string()),
    ('ts_offset', pa.string()),
    ('last_duration', pa.string()),
    ('sample_offset', pa.int64()),
    ('sample_count', pa.int64()),
    ('get_urls', pa.string()),  # JSON string
    ('key_frame_count', pa.int32()),
    ('created', pa.timestamp('us')),
    # NEW: Storage path field for hierarchical S3 structure
    ('storage_path', pa.string()),  # The actual S3 object key where data is stored
    # Time-series optimization fields
    ('start_time', pa.timestamp('us')),
    ('end_time', pa.timestamp('us')),
    ('duration_seconds', pa.float64()),
])

# Object table schema - TAMS compliant
# Note: referenced_by_flows and first_referenced_by_flow are computed dynamically
# from the flow_object_references table, not stored as columns
object_schema = pa.schema([
    ('id', pa.string()),  # TAMS spec requires 'id' field
    ('size', pa.int64()),
    ('created', pa.timestamp('us')),
    # Additional fields for performance and monitoring
    ('last_accessed', pa.timestamp('us')),
    ('access_count', pa.int32()),
])

# Flow-Object references table schema
flow_object_references_schema = pa.schema([
    ('object_id', pa.string()),
    ('flow_id', pa.string()),
    ('created', pa.timestamp('us')),
])

# Flow collections table - TAMS compliant (dynamic collection management)
flow_collections_schema = pa.schema([
    ('collection_id', pa.string()),  # Unique collection identifier
    ('flow_id', pa.string()),        # References flows.id
    ('label', pa.string()),          # Collection label
    ('description', pa.string()),    # Collection description
    ('created', pa.timestamp('us')), # When flow was added to collection
    ('created_by', pa.string()),     # Who added the flow to collection
])

# Source collections table - TAMS compliant (dynamic collection management)
source_collections_schema = pa.schema([
    ('collection_id', pa.string()),  # Unique collection identifier
    ('source_id', pa.string()),      # References sources.id
    ('label', pa.string()),          # Collection label
    ('description', pa.string()),    # Collection description
    ('created', pa.timestamp('us')), # When source was added to collection
    ('created_by', pa.string()),     # Who added the source to collection
])

# Tags table schema - NEW: Dynamic tags for sources and flows
tags_schema = pa.schema([
    ('id', pa.string()),  # Unique tag identifier
    ('entity_type', pa.string()),  # 'source' or 'flow'
    ('entity_id', pa.string()),  # ID of the source or flow
    ('tag_name', pa.string()),  # Tag name/key
    ('tag_value', pa.string()),  # Tag value
    ('created', pa.timestamp('us')),  # When tag was created
    ('updated', pa.timestamp('us')),  # When tag was last updated
    ('created_by', pa.string()),  # Who created the tag
    ('updated_by', pa.string()),  # Who last updated the tag
])

# Webhook table schema
webhook_schema = pa.schema([
    ('id', pa.string()),
    ('url', pa.string()),
    ('api_key_name', pa.string()),
    ('api_key_value', pa.string()),
    ('events', pa.string()),  # JSON string
    # TAMS-specific filtering fields
    ('flow_ids', pa.string()),  # JSON string
    ('source_ids', pa.string()),  # JSON string
    ('flow_collected_by_ids', pa.string()),  # JSON string
    ('source_collected_by_ids', pa.string()),  # JSON string
    ('accept_get_urls', pa.string()),  # JSON string
    ('accept_storage_ids', pa.string()),  # JSON string
    ('presigned', pa.bool_()),
    ('verbose_storage', pa.bool_()),
    # Ownership fields for TAMS API v7.0 compliance
    ('owner_id', pa.string()),
    ('created_by', pa.string()),
    ('created', pa.timestamp('us')),
    ('updated', pa.timestamp('us'))
])

# Deletion request table schema
deletion_request_schema = pa.schema([
    ('id', pa.string()),
    ('flow_id', pa.string()),
    ('timerange', pa.string()),
    ('status', pa.string()),
    ('created', pa.timestamp('us')),
    ('updated', pa.timestamp('us'))
])

# Authentication table schemas
users_schema = pa.schema([
    # Core user fields
    ('user_id', pa.string()),
    ('username', pa.string()),
    ('email', pa.string()),
    ('full_name', pa.string()),
    ('is_active', pa.bool_()),
    ('is_admin', pa.bool_()),
    
    # Authentication fields
    ('password_hash', pa.string()),
    ('password_salt', pa.string()),
    ('password_changed_at', pa.timestamp('us')),
    
    # Security fields
    ('failed_login_attempts', pa.int32()),
    ('locked_until', pa.timestamp('us')),
    ('last_login_at', pa.timestamp('us')),
    ('last_login_ip', pa.string()),
    
    # Metadata fields
    ('created_by', pa.string()),
    ('updated_by', pa.string()),
    ('created', pa.timestamp('us')),
    ('updated', pa.timestamp('us')),
    ('metadata', pa.string()),
])

api_tokens_schema = pa.schema([
    # Core token fields
    ('token_id', pa.string()),
    ('user_id', pa.string()),
    ('token_hash', pa.string()),
    ('token_name', pa.string()),
    ('token_type', pa.string()),
    
    # Permissions and scope
    ('permissions', pa.string()),
    ('scopes', pa.string()),
    ('allowed_ips', pa.string()),
    
    # Token lifecycle
    ('is_active', pa.bool_()),
    ('created_at', pa.timestamp('us')),
    ('expires_at', pa.timestamp('us')),
    ('last_used_at', pa.timestamp('us')),
    ('last_used_ip', pa.string()),
    ('usage_count', pa.int64()),
    
    # Metadata fields
    ('created_by', pa.string()),
    ('updated_by', pa.string()),
    ('updated', pa.timestamp('us')),
])

refresh_tokens_schema = pa.schema([
    # Core token fields
    ('token_id', pa.string()),
    ('user_id', pa.string()),
    ('token_hash', pa.string()),
    ('token_name', pa.string()),
    
    # Token lifecycle
    ('is_active', pa.bool_()),
    ('created_at', pa.timestamp('us')),
    ('expires_at', pa.timestamp('us')),
    ('last_used_at', pa.timestamp('us')),
    ('last_used_ip', pa.string()),
    
    # Metadata fields
    ('created_by', pa.string()),
    ('updated_by', pa.string()),
    ('updated', pa.timestamp('us')),
])

auth_logs_schema = pa.schema([
    # Core log fields
    ('log_id', pa.string()),
    ('user_id', pa.string()),
    ('event_type', pa.string()),
    ('event_details', pa.string()),
    ('ip_address', pa.string()),
    ('user_agent', pa.string()),
    
    # Timestamp fields
    ('created_at', pa.timestamp('us')),
    
    # Additional context
    ('session_id', pa.string()),
    ('request_id', pa.string()),
])

# Complete table configuration
tables_config = {
    'sources': source_schema,
    'flows': flow_schema,
    'segments': segment_schema,
    'objects': object_schema,
    'flow_object_references': flow_object_references_schema,
    'flow_collections': flow_collections_schema,
    'source_collections': source_collections_schema,
    'tags': tags_schema,  # NEW: Tags table
    'webhooks': webhook_schema,
    'deletion_requests': deletion_request_schema,
    'users': users_schema,
    'api_tokens': api_tokens_schema,
    'refresh_tokens': refresh_tokens_schema,
    'auth_logs': auth_logs_schema
}

def get_desired_table_projections():
    """Get the desired table projections configuration"""
    return {
        'sources': [
            ('id',),  # Primary key projection
        ],
        'flows': [
            ('id',),  # Primary key projection
            ('id', 'source_id'),  # Composite key for source-based queries
            ('source_id', 'created'),  # Source-based creation time queries
            ('source_id', 'updated'),  # Source-based update time queries (TAMS spec field name)
        ],
        'segments': [
            ('id',),  # Primary key projection
            ('id', 'flow_id'),  # Composite projection for flow-based queries
            ('id', 'flow_id', 'object_id'),  # Composite key for segment queries
            ('id', 'object_id'),  # Composite projection for object-based queries
            ('id', 'start_time', 'end_time'),  # Time range projection
            ('source_id', 'start_time', 'end_time'),  # Source-based time range queries
            ('flow_id', 'start_time', 'end_time'),  # Flow-based time range queries
            ('object_id', 'start_time', 'end_time'),  # Object-based time range queries
            ('source_id', 'flow_id', 'start_time', 'end_time'),  # Composite source+flow time range queries
        ],
        'objects': [
            ('id',),  # Primary key projection
        ],
        'flow_object_references': [
            ('object_id',),  # Primary key projection
            ('object_id', 'flow_id'),  # Composite key for object-flow queries
            ('flow_id', 'object_id'),  # Composite key for flow-object queries
        ],
        'flow_collections': [
            ('collection_id',),  # Primary key projection
            ('collection_id', 'flow_id'),  # Composite key for collection-flow queries
            ('flow_id', 'collection_id'),  # Composite key for flow-collection queries
            ('collection_id', 'label'),  # Collection label queries
            ('collection_id', 'created'),  # Collection creation time queries
            ('collection_id', 'created_by'),  # Collection creator queries
            ('flow_id', 'created'),  # Flow collection membership time queries
            ('label', 'created'),  # Label-based creation time queries
            ('collection_id', 'flow_id', 'created'),  # Full collection membership queries
        ],
        'source_collections': [
            ('collection_id',),  # Primary key projection
            ('collection_id', 'source_id'),  # Composite key for collection-source queries
            ('source_id', 'collection_id'),  # Composite key for source-collection queries
            ('collection_id', 'label'),  # Collection label queries
            ('collection_id', 'created'),  # Collection creation time queries
            ('collection_id', 'created_by'),  # Collection creator queries
            ('source_id', 'created'),  # Source collection membership time queries
            ('label', 'created'),  # Label-based creation time queries
            ('collection_id', 'source_id', 'created'),  # Full collection membership queries
        ],
        'tags': [  # NEW: Tags table projections
            ('id',),  # Primary key projection
            ('entity_type', 'entity_id'),  # Entity-based queries
            ('entity_id', 'tag_name'),  # Tag name queries
            ('tag_name', 'tag_value'),  # Tag value queries
            ('entity_type', 'tag_name'),  # Entity type + tag name queries
        ]
    }
