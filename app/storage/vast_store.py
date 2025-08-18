"""
VAST Database Store for TAMS (Time-addressable Media Store)

This module provides a high-level interface to VAST Database for TAMS operations,
combining VAST database management with S3 storage for efficient media handling.

The VASTStore class integrates:
- VAST Database for metadata storage and analytics
- S3-compatible storage for media segment data
- Comprehensive TAMS API compliance
- Time-series optimized data structures
- Efficient querying and analytics capabilities

Key Features:
- Source, Flow, and FlowSegment management
- Time-range based queries and analytics
- Hybrid storage (metadata in VAST, media in S3)
- Presigned URL generation for secure access
- Comprehensive error handling and logging

Example Usage:
    store = VASTStore(
        endpoint="http://vast.example.com",
        access_key="your_key",
        secret_key="your_secret",
        bucket="tams-bucket"
    )
    
    # Create a source
    source = Source(id=UUID4("..."), format="urn:x-nmos:format:video")
    await store.create_source(source)
    
    # Create a flow
    flow = VideoFlow(id=UUID4("..."), source_id=source.id, ...)
    await store.create_flow(flow)
    
    # Store media segment
    segment = FlowSegment(object_id="...", timerange="[0:0_10:0)")
    await store.create_flow_segment(segment, flow.id, media_data)
"""

import logging
import json
import uuid
import time
from ibis import _ as ibis_
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, Union, Tuple
import pandas as pd
import pyarrow as pa
from pydantic import UUID4
from pyarrow import Table, Schema, RecordBatch

from .vastdbmanager import VastDBManager
from ..core.telemetry import telemetry_manager, trace_operation
from ..models.models import (
    Source, Flow, FlowSegment, Object, DeletionRequest, 
    TimeRange, Tags, VideoFlow, AudioFlow, DataFlow, ImageFlow, MultiFlow,
    CollectionItem, GetUrl, Webhook, WebhookPost, User, ApiToken, AuthLog
)
from .s3_store import S3Store
from .storage_backend_manager import StorageBackendManager
from ..core.config import get_settings

logger = logging.getLogger(__name__)

# Configuration Constants - Easy to adjust for troubleshooting
DEFAULT_QUERY_TIMEOUT = 30  # Default query timeout in seconds
DEFAULT_CACHE_TTL_MINUTES = 30  # Default cache time-to-live in minutes
DEFAULT_MAX_RETRIES = 3  # Default maximum retry attempts
DEFAULT_BATCH_SIZE = 1000  # Default batch size for operations
DEFAULT_MAX_WORKERS = 4  # Default maximum parallel workers
DEFAULT_ANALYTICS_TIMEOUT = 60  # Default analytics query timeout
DEFAULT_STORAGE_CALCULATION_BASE = 0  # Base value for storage calculations
DEFAULT_ACCESS_COUNT_BASE = 0  # Base value for access count calculations

EXPECTED_PARTS_LENGTH = 2  # Expected number of parts for parsing
EXPECTED_CONDITIONS_LENGTH = 2  # Expected number of conditions for predicate building
SINGLE_CONDITION_LENGTH = 1  # Length indicating single condition


class VASTStore:
    """
    VAST Database Store for TAMS (Time-addressable Media Store) operations.
    
    This class provides a high-level interface to VAST Database for TAMS operations,
    combining VAST database management with S3 storage for efficient media handling.
    It implements the TAMS API specification with optimized time-series storage
    and analytics capabilities.
    
    The store uses a hybrid approach:
    - Metadata (sources, flows, segments) stored in VAST Database
    - Media segment data stored in S3-compatible storage
    - Time-range optimized queries for efficient retrieval
    
    Attributes:
        endpoint (str): VAST Database endpoint URL
        access_key (str): VAST access key for authentication
        secret_key (str): VAST secret key for authentication
        bucket (str): VAST bucket name for TAMS data
        schema (str): VAST schema name for TAMS tables
        db_manager (VastDBManager): VAST database manager instance
        s3_store (S3Store): S3 storage manager for media segments
        
    Example:
        >>> store = VASTStore(
        ...     endpoint="http://vast.example.com",
        ...     access_key="your_key",
        ...     secret_key="your_vast_secret",
        ...     bucket="tams-data",
        ...     schema="tams-schema",
        ...     s3_endpoint_url="http://s3.example.com",
        ...     s3_access_key_id="your_s3_key",
        ...     s3_secret_access_key="your_s3_secret",
        ...     s3_bucket_name="tams-media",
        ...     s3_use_ssl=True
        ... )
        >>> 
        >>> # Create a video source
        >>> source = Source(
        ...     id=UUID4("550e8400-e29b-41d4-a716-446655440000"),
        ...     format="urn:x-nmos:format:video",
        ...     label="Camera 1"
        ... )
        >>> await store.create_source(source)
        >>> 
        >>> # Create a video flow
        >>> flow = VideoFlow(
        ...     id=UUID4("550e8400-e29b-41d4-a716-446655440001"),
        ...     source_id=source.id,
        ...     format="urn:x-nmos:format:video",
        ...     codec="urn:x-nmos:codec:prores",
        ...     frame_width=1920,
        ...     frame_height=1080,
        ...     frame_rate="25/1"
        ... )
        >>> await store.create_flow(flow)
        >>> 
        >>> # Store a media segment
        >>> segment = FlowSegment(
        ...     object_id="seg_001",
        ...     timerange="[0:0_10:0)",
        ...     sample_offset=0,
        ...     sample_count=250
        ... )
        >>> await store.create_flow_segment(segment, flow.id, media_bytes)
    """
    
    def __init__(self, 
                 endpoint: Optional[str] = None, 
                 access_key: Optional[str] = None, 
                 secret_key: Optional[str] = None, 
                 bucket: Optional[str] = None,
                 schema: Optional[str] = None):
        """
        Initialize VAST Store
        
        Args:
            endpoint: VAST Database endpoint URL
            access_key: VAST access key for authentication
            secret_key: VAST secret key for authentication
            bucket: VAST bucket name for TAMS data
            schema: VAST schema name for TAMS tables
        """
        # Use provided parameters or load from config
        if endpoint is None or access_key is None or secret_key is None or bucket is None:
            settings = get_settings()
            self.endpoint = endpoint or settings.vast_endpoint
            self.access_key = access_key or settings.vast_access_key
            self.secret_key = secret_key or settings.vast_secret_key
            self.bucket = bucket or settings.vast_bucket
            self.schema = schema or settings.vast_schema
        else:
            self.endpoint = endpoint
            self.access_key = access_key
            self.secret_key = secret_key
            self.bucket = bucket
            self.schema = schema or "tams7"
        
        # Initialize storage backend manager
        self.storage_backend_manager = StorageBackendManager()
        
        # Initialize S3 store with storage backend manager
        self.s3_store = S3Store(storage_backend_manager=self.storage_backend_manager)
        
        # Initialize VAST database manager
        self.db_manager = VastDBManager(
            endpoints=self.endpoint
        )
        
        # Create TAMS tables if they don't exist
        self._setup_tams_tables()
        
        logger.info(f"VAST Store initialized with endpoint: {self.endpoint}, bucket: {self.bucket}, schema: {self.schema}")
    
    def _setup_tams_tables(self):
        """Setup TAMS tables with their schemas"""
        
        # Source table schema
        source_schema = pa.schema([
            ('id', pa.string()),
            ('format', pa.string()),
            ('label', pa.string()),
            ('description', pa.string()),
            ('created_by', pa.string()),
            ('updated_by', pa.string()),
            ('created', pa.timestamp('us')),
            ('metadata_updated', pa.timestamp('us')),
            ('tags', pa.string()),  # JSON string
            ('source_collection', pa.string()),  # JSON string
            ('collected_by', pa.string()),  # JSON string
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
            ('tags', pa.string()),  # JSON string
            ('container', pa.string()),
            ('read_only', pa.bool_()),
            # Video specific
            ('frame_width', pa.int32()),
            ('frame_height', pa.int32()),
            ('frame_rate', pa.string()),
            ('interlace_mode', pa.string()),
            ('color_sampling', pa.string()),
            ('color_space', pa.string()),
            ('transfer_characteristics', pa.string()),
            ('color_primaries', pa.string()),
            # Audio specific
            ('sample_rate', pa.int32()),
            ('bits_per_sample', pa.int32()),
            ('channels', pa.int32()),
            # Multi flow specific
            ('flow_collection', pa.string()),  # JSON string
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
        object_schema = pa.schema([
            ('id', pa.string()),  # Changed from object_id to id
            ('size', pa.int64()),
            ('created', pa.timestamp('us')),
            ('last_accessed', pa.timestamp('us')),
            ('access_count', pa.int32()),
        ])
        
        # Flow-Object references table schema
        flow_object_references_schema = pa.schema([
            ('object_id', pa.string()),
            ('flow_id', pa.string()),
            ('created', pa.timestamp('us')),
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
            
            # Security fields
            ('revoked_at', pa.timestamp('us')),
            ('revoked_by', pa.string()),
            ('revocation_reason', pa.string()),
            
            # Metadata
            ('created_by', pa.string()),
            ('metadata', pa.string()),
            
        ])
        
        refresh_tokens_schema = pa.schema([
            # Core token fields
            ('refresh_token_id', pa.string()),
            ('user_id', pa.string()),
            ('jwt_id', pa.string()),
            ('refresh_token_hash', pa.string()),
            
            # Token lifecycle
            ('is_active', pa.bool_()),
            ('created_at', pa.timestamp('us')),
            ('expires_at', pa.timestamp('us')),
            ('used_at', pa.timestamp('us')),
            
            # Security fields
            ('revoked_at', pa.timestamp('us')),
            ('revoked_by', pa.string()),
            ('revocation_reason', pa.string()),
            
            # Device/context information
            ('device_id', pa.string()),
            ('user_agent', pa.string()),
            ('ip_address', pa.string()),
            
            # Metadata
            ('created_by', pa.string()),
            ('metadata', pa.string()),
            
        ])
        
        auth_logs_schema = pa.schema([
            # Core log fields
            ('log_id', pa.string()),
            ('user_id', pa.string()),
            ('session_id', pa.string()),
            
            # Event details
            ('event_type', pa.string()),
            ('auth_method', pa.string()),
            ('success', pa.bool_()),
            
            # Request details
            ('ip_address', pa.string()),
            ('user_agent', pa.string()),
            ('request_path', pa.string()),
            
            # Error details
            ('error_code', pa.string()),
            ('error_message', pa.string()),
            
            # Timestamps
            ('timestamp', pa.timestamp('us')),
            
            # Metadata
            ('metadata', pa.string()),
            
        ])
        
        # Create tables
        tables_config = {
            'sources': source_schema,
            'flows': flow_schema,
            'segments': segment_schema,
            'objects': object_schema,
            'flow_object_references': flow_object_references_schema,
            'webhooks': webhook_schema,
            'deletion_requests': deletion_request_schema,
            'users': users_schema,
            'api_tokens': api_tokens_schema,
            'refresh_tokens': refresh_tokens_schema,
            'auth_logs': auth_logs_schema
        }
        
        settings = get_settings()
        
        # Define desired projections per table. Only columns present in the schema will be used.
        desired_table_projections = VASTStore._get_desired_table_projections()
        
        def _projection_name(table: str, cols: tuple) -> str:
            return f"{table}_{'_'.join(cols)}_proj"
        
        for table_name, schema in tables_config.items():
            try:
                projections_arg = None
                
                if settings.enable_table_projections:
                    # Filter projection columns to only those present in the schema
                    schema_columns = {field.name for field in schema}
                    desired_specs = desired_table_projections.get(table_name, [])
                    projections_map = {}
                    for cols in desired_specs:
                        filtered_cols = [c for c in cols if c in schema_columns]
                        if not filtered_cols:
                            continue
                        proj_name = _projection_name(table_name, tuple(filtered_cols))
                        projections_map[proj_name] = filtered_cols
                    if projections_map:
                        projections_arg = projections_map
                
                # Create table with projections (if any)
                self.db_manager.create_table(table_name, schema, projections=projections_arg)
                if projections_arg:
                    logger.info("Table '%s' setup complete with projections: %s", table_name, list(projections_arg.keys()))
                else:
                    logger.info("Table '%s' setup complete", table_name)
            except Exception as e:
                logger.error("Failed to setup table '%s': %s", table_name, e)
                raise
    
    @staticmethod
    def _get_desired_table_projections():
        """Get the desired table projections configuration"""
        return {
            'sources': [
                ('id',),  # Primary key projection
            ],
            'flows': [
                ('id',),  # Primary key projection
                ('id', 'source_id'),  # Composite key for source-based queries
                ('id', 'start_time', 'end_time'),  # Time range projection
            ],
            'segments': [
                ('id',),  # Primary key projection
                ('id', 'flow_id'),  # Composite projection for flow-based queries
                ('id', 'flow_id', 'object_id'),  # Composite key for segment queries
                ('id', 'object_id'),  # Composite projection for object-based queries
                ('id', 'start_time', 'end_time'),  # Time range projection
            ],
            'objects': [
                ('id',),  # Primary key projection
            ],
            'flow_object_references': [
                ('object_id',),  # Primary key projection
                ('object_id', 'flow_id'),  # Composite key for object-flow queries
                ('flow_id', 'object_id'),  # Composite key for flow-object queries
            ]
        }
    
    def _parse_timerange(self, timerange: str) -> Tuple[datetime, datetime, float]:
        """
        Parse TAMS timerange format to extract start, end, and duration
        
        Args:
            timerange: TAMS timerange string (e.g., "[0:0_10:0)")
            
        Returns:
            Tuple of (start_time, end_time, duration_seconds)
        """
        try:
            # Remove brackets/parentheses
            clean_range = timerange.strip('[]()')
            
            if '_' in clean_range:
                start_str, end_str = clean_range.split('_', 1)
                
                # Parse start time
                if start_str:
                    start_seconds = self._parse_timestamp(start_str)
                else:
                    start_seconds = DEFAULT_STORAGE_CALCULATION_BASE
                
                # Parse end time
                if end_str:
                    end_seconds = self._parse_timestamp(end_str)
                else:
                    end_seconds = float('inf')
                
                duration = end_seconds - start_seconds if end_seconds != float('inf') else 0
                
                # Convert to datetime (using epoch as base)
                start_time = datetime.fromtimestamp(start_seconds, timezone.utc)
                end_time = datetime.fromtimestamp(end_seconds, timezone.utc) if end_seconds != float('inf') else start_time + timedelta(seconds=duration)
                
            else:
                # Single timestamp
                start_seconds = self._parse_timestamp(clean_range)
                start_time = datetime.fromtimestamp(start_seconds, timezone.utc)
                end_time = start_time
                duration = DEFAULT_STORAGE_CALCULATION_BASE
            
            return start_time, end_time, duration
            
        except Exception as e:
            logger.warning(f"Failed to parse timerange '{timerange}': {e}")
            # Return default values
            now = datetime.now(timezone.utc)
            return now, now, 0
    
    def _parse_timestamp(self, timestamp_str: str) -> float:
        """
        Parse TAMS timestamp format to seconds
        
        Args:
            timestamp_str: TAMS timestamp string (e.g., "0:0", "10:5")
            
        Returns:
            Seconds as float
        """
        if ':' in timestamp_str:
            parts = timestamp_str.split(':')
            if len(parts) == EXPECTED_PARTS_LENGTH:
                seconds = int(parts[0])
                subseconds = int(parts[1]) if parts[1] else 0
                return seconds + (subseconds / 1000000000)  # Assuming nanoseconds
        return 0.0
    
    def _timerange_matches(self, stored_timerange: str, query_timerange: str) -> bool:
        """
        Check if stored timerange matches query timerange using TAMS overlap logic
        
        Args:
            stored_timerange: Timerange stored in database (e.g., "[0:0_5:0)")
            query_timerange: Timerange from query parameter (e.g., "[1:0_3:0)")
            
        Returns:
            True if timeranges overlap, False otherwise
        """
        try:
            from ..core.timerange_utils import timeranges_overlap
            return timeranges_overlap(stored_timerange, query_timerange)
        except ImportError:
            # Fallback to basic string comparison if timerange_utils not available
            logger.warning("timerange_utils not available, using fallback comparison")
            return stored_timerange == query_timerange
    
    def _dict_to_json(self, data: Union[Dict[str, Any], List[Any]]) -> str:
        """Convert dictionary or list to JSON string"""
        if not data:
            return ""
        
        # Custom JSON encoder to handle UUIDs, datetime objects, and other non-serializable types
        class UUIDEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, uuid.UUID):
                    return str(obj)
                elif isinstance(obj, datetime):
                    return obj.isoformat()
                elif hasattr(obj, 'isoformat'):  # Handle any object with isoformat method
                    return obj.isoformat()
                return super().default(obj)
        
        return json.dumps(data, cls=UUIDEncoder)
    
    def _json_to_dict(self, json_str: Union[str, List[Any], Any]) -> Dict[str, Any]:
        """Convert JSON string, list, or any data to dictionary"""
        if isinstance(json_str, str):
            try:
                return json.loads(json_str) if json_str else {}
            except json.JSONDecodeError:
                return {}
        elif isinstance(json_str, list):
            return {"items": json_str}
        elif isinstance(json_str, dict):
            return json_str
        else:
            return {}
    
    def _json_to_list(self, json_str: Union[str, List[Any], Any]) -> List[Any]:
        """Convert JSON string or any data to list"""
        if isinstance(json_str, str):
            try:
                parsed = json.loads(json_str) if json_str else []
                return parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                return []
        elif isinstance(json_str, list):
            return json_str
        elif isinstance(json_str, dict):
            return []  # Empty list for dict
        else:
            return []
    
    async def create_source(self, source: Source) -> bool:
        """Create a new source in VAST store"""
        try:
            # Convert source to dictionary
            source_data = {
                'id': str(source.id),
                'format': str(source.format),
                'label': source.label or "",
                'description': source.description or "",
                'created_by': source.created_by or "",
                'updated_by': source.updated_by or "",
                'created': source.created or datetime.now(timezone.utc),
                'metadata_updated': source.metadata_updated or datetime.now(timezone.utc),
                'tags': self._dict_to_json(source.tags.root if source.tags else {}),
                'source_collection': self._dict_to_json([item.model_dump() for item in source.source_collection] if source.source_collection else []),
                'collected_by': self._dict_to_json([str(uuid) for uuid in source.collected_by] if source.collected_by else []),
            }
            # Insert into VAST database as dict of lists
            self.db_manager.insert('sources', {k: [v] for k, v in source_data.items()})
            logger.info(f"Created source {source.id} in VAST store")
            return True
        except Exception as e:
            logger.error(f"Failed to create source {source.id}: {e}")
            return False
    
    async def get_source(self, source_id: str) -> Optional[Source]:
        """Get source by ID"""
        try:
            # Query for specific source
            predicate = (ibis_.id == source_id)
            results = self.db_manager.select('sources', predicate=predicate, output_by_row=True)
            
            if not results:
                return None
            
            # Convert first result back to Source model
            if isinstance(results, list) and results:
                row = results[0]
            elif isinstance(results, dict):
                row = results
            else:
                return None
            
            source_data = {
                'id': row['id'],
                'format': row['format'],
                'label': row['label'] if row['label'] else None,
                'description': row['description'] if row['description'] else None,
                'created_by': row['created_by'] if row['created_by'] else None,
                'updated_by': row['updated_by'] if row['updated_by'] else None,
                'created': row['created'],
                'metadata_updated': row['metadata_updated'],
                'tags': Tags(self._json_to_dict(row['tags'])),
                'source_collection': [CollectionItem(id=item.get('id', str(uuid.uuid4())), label=item.get('label', '')) if isinstance(item, dict) else CollectionItem(id=str(uuid.uuid4()), label=str(item)) for item in self._json_to_dict(row['source_collection'])],
                'collected_by': [uuid for uuid in self._json_to_dict(row['collected_by'])],
            }
            
            return Source(**source_data)
            
        except Exception as e:
            logger.error(f"Failed to get source {source_id}: {e}")
            return None
    
    async def list_sources(self, filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> List[Source]:
        """List sources with optional filtering"""
        try:
            # Build predicate from filters
            predicate = None
            if filters:
                conditions = []
                if 'label' in filters:
                    conditions.append((ibis_.label == filters['label']))
                if 'format' in filters:
                    conditions.append((ibis_.format == filters['format']))
                if conditions:
                    predicate = conditions[0] if len(conditions) == SINGLE_CONDITION_LENGTH else conditions[0] & conditions[1]
            
            # Query sources
            results = self.db_manager.select('sources', predicate=predicate, output_by_row=True)
            
            # Apply limit
            if limit and isinstance(results, list):
                results = results[:limit]
            elif limit and isinstance(results, dict):
                # For column-oriented results, limit each column
                limited_results = {}
                for key, values in results.items():
                    limited_results[key] = values[:limit]
                results = limited_results
            
            # Convert to Source models
            sources = []
            if isinstance(results, list):
                for row in results:
                    source_data = {
                        'id': row['id'],
                        'format': row['format'],
                        'label': row['label'] if row['label'] else None,
                        'description': row['description'] if row['description'] else None,
                        'created_by': row['created_by'] if row['created_by'] else None,
                        'updated_by': row['updated_by'] if row['updated_by'] else None,
                        'created': row['created'],
                        'metadata_updated': row['metadata_updated'],
                        'tags': Tags(self._json_to_dict(row['tags'])),
                        'source_collection': [CollectionItem(id=item.get('id', str(uuid.uuid4())), label=item.get('label', '')) if isinstance(item, dict) else CollectionItem(id=str(uuid.uuid4()), label=str(item)) for item in self._json_to_dict(row['source_collection'])],
                        'collected_by': [uuid for uuid in self._json_to_dict(row['collected_by'])],
                    }
                    sources.append(Source(**source_data))
            
            return sources
            
        except Exception as e:
            logger.error(f"Failed to list sources: {e}")
            return []
    
    async def create_flow(self, flow: Flow) -> bool:
        """Create a new flow in VAST store"""
        try:
            # Convert flow to dictionary
            flow_data = {
                'id': str(flow.id),
                'source_id': str(flow.source_id),
                'format': str(flow.format),
                'codec': str(flow.codec),
                'label': flow.label or "",
                'description': flow.description or "",
                'created_by': flow.created_by or "",
                'updated_by': flow.updated_by or "",
                'created': flow.created or datetime.now(timezone.utc),
                'metadata_updated': flow.metadata_updated or datetime.now(timezone.utc),
                'tags': self._dict_to_json(flow.tags.root if flow.tags else {}),
                'container': flow.container or "",
                'read_only': flow.read_only or False,
                'frame_width': getattr(flow, 'frame_width', 0),
                'frame_height': getattr(flow, 'frame_height', 0),
                'frame_rate': getattr(flow, 'frame_rate', ""),
                'interlace_mode': getattr(flow, 'interlace_mode', ""),
                'color_sampling': getattr(flow, 'color_sampling', ""),
                'color_space': getattr(flow, 'color_space', ""),
                'transfer_characteristics': getattr(flow, 'transfer_characteristics', ""),
                'color_primaries': getattr(flow, 'color_primaries', ""),
                'sample_rate': getattr(flow, 'sample_rate', 0),
                'bits_per_sample': getattr(flow, 'bits_per_sample', 0),
                'channels': getattr(flow, 'channels', 0),
                'flow_collection': self._dict_to_json([str(uuid) for uuid in getattr(flow, 'flow_collection', [])]),
            }
            # Insert into VAST database as dict of lists
            self.db_manager.insert('flows', {k: [v] for k, v in flow_data.items()})
            logger.info(f"Created flow {flow.id} in VAST store")
            return True
        except Exception as e:
            logger.error(f"Failed to create flow {flow.id}: {e}")
            return False
    
    async def get_flow(self, flow_id: str) -> Optional[Flow]:
        """Get flow by ID"""
        try:
            # Query for specific flow
            predicate = (ibis_.id == flow_id)
            results = self.db_manager.select('flows', predicate=predicate, output_by_row=True)
            
            if not results:
                return None
            
            # Convert first result back to Flow model
            if isinstance(results, list) and results:
                row = results[0]
            elif isinstance(results, dict):
                row = results
            else:
                return None
            
            flow_data = {
                'id': row['id'],
                'source_id': row['source_id'],
                'format': row['format'],
                'codec': row['codec'],
                'label': row['label'] if row['label'] else None,
                'description': row['description'] if row['description'] else None,
                'created_by': row['created_by'] if row['created_by'] else None,
                'updated_by': row['updated_by'] if row['updated_by'] else None,
                'created': row['created'],
                'metadata_updated': row['metadata_updated'],
                'tags': Tags(self._json_to_dict(row['tags'])),
                'container': row['container'] if row['container'] else None,
                'read_only': row['read_only'],
            }
            
            # Add format-specific fields
            format_type = row['format']
            if format_type == "urn:x-nmos:format:video":
                flow_data.update({
                    'frame_width': row['frame_width'],
                    'frame_height': row['frame_height'],
                    'frame_rate': row['frame_rate'],
                    'interlace_mode': row['interlace_mode'] if row['interlace_mode'] else None,
                    'color_sampling': row['color_sampling'] if row['color_sampling'] else None,
                    'color_space': row['color_space'] if row['color_space'] else None,
                    'transfer_characteristics': row['transfer_characteristics'] if row['transfer_characteristics'] else None,
                    'color_primaries': row['color_primaries'] if row['color_primaries'] else None,
                })
                return VideoFlow(**flow_data)
            elif format_type == "urn:x-nmos:format:audio":
                flow_data.update({
                    'sample_rate': row['sample_rate'],
                    'bits_per_sample': row['bits_per_sample'],
                    'channels': row['channels'],
                })
                return AudioFlow(**flow_data)
            elif format_type == "urn:x-tam:format:image":
                flow_data.update({
                    'frame_width': row['frame_width'],
                    'frame_height': row['frame_height'],
                })
                return ImageFlow(**flow_data)
            elif format_type == "urn:x-nmos:format:multi":
                flow_data.update({
                    'flow_collection': [uuid for uuid in self._json_to_dict(row['flow_collection'])],
                })
                return MultiFlow(**flow_data)
            else:
                return DataFlow(**flow_data)
            
        except Exception as e:
            logger.error(f"Failed to get flow {flow_id}: {e}")
            return None
    
    async def create_flow_segment(self, segment: FlowSegment, flow_id: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
        """Create a new flow segment: store data in S3 and metadata in VAST DB"""
        try:
            # Store segment data in S3 only if data is not empty
            if data:
                s3_success = await self.s3_store.store_flow_segment(flow_id, segment, data, content_type)
                if not s3_success:
                    logger.error(f"Failed to store flow segment data in S3 for flow {flow_id}")
                    return False
            else:
                logger.info(f"Skipping S3 storage for empty segment data in flow {flow_id}")
            # Store only segment metadata in VAST DB
            start_time, end_time, duration = self._parse_timerange(segment.timerange)
            
            # Generate storage_path if not provided to ensure consistency
            if not segment.storage_path:
                # Generate the same hierarchical path that would be used in storage allocation
                storage_path = self.s3_store.generate_segment_key(flow_id, segment.id, segment.timerange)  # Changed from object_id to id
                logger.info(f"Generated storage_path for segment {segment.id}: {storage_path}")  # Changed from object_id to id
            else:
                storage_path = segment.storage_path
                logger.info(f"Using provided storage_path for segment {segment.id}: {storage_path}")  # Changed from object_id to id
            
            # Generate TAMS-compliant get_urls using the new method
            get_urls_objs = await self.s3_store.create_tams_compliant_get_urls(
                flow_id=flow_id,
                segment_id=segment.id,  # Changed from object_id to id
                timerange=segment.timerange,
                storage_path=storage_path
            )
            get_urls_json = self._dict_to_json([url.model_dump() for url in get_urls_objs])
            segment_data = {
                'id': str(uuid.uuid4()),
                'flow_id': flow_id,
                'object_id': segment.id,  # Changed from object_id to id
                'timerange': segment.timerange,
                'ts_offset': segment.ts_offset or "",
                'last_duration': segment.last_duration or "",
                'sample_offset': segment.sample_offset or 0,
                'sample_count': segment.sample_count or 0,
                'get_urls': get_urls_json,
                'key_frame_count': segment.key_frame_count or 0,
                'created': datetime.now(timezone.utc),
                'start_time': start_time,
                'end_time': end_time,
                'duration_seconds': duration,
                'storage_path': storage_path  # Store the generated or provided storage path
            }
            self.db_manager.insert('segments', {k: [v] for k, v in segment_data.items()})
            logger.info(f"Created flow segment metadata for flow {flow_id} in VAST DB")
            return True
        except Exception as e:
            logger.error(f"Failed to create flow segment for flow {flow_id}: {e}")
            return False

    async def get_flow_segments(self, flow_id: str, timerange: Optional[str] = None) -> List[FlowSegment]:
        """Get flow segment metadata from VAST DB and data from S3"""
        try:
            # First get all segments for the flow (no timerange filtering at DB level)
            predicate = (ibis_.flow_id == flow_id)
            
            
            results = self.db_manager.select('segments', predicate=predicate, output_by_row=True)
            segments = []
            
            if isinstance(results, list):
                for row in results:
                    # Apply timerange filtering in Python using TAMS timerange overlap logic
                    if timerange and not self._timerange_matches(row['timerange'], timerange):
                        continue
                    
                    # get_urls is generated from S3 using stored storage_path
                    get_urls = await self.s3_store.create_tams_compliant_get_urls(
                        flow_id=flow_id, 
                        segment_id=row['object_id'], 
                        timerange=row['timerange'], 
                        storage_path=row.get('storage_path')
                    )
                    segment = FlowSegment(
                        object_id=row['object_id'],
                        timerange=row['timerange'],
                        ts_offset=row['ts_offset'] if row['ts_offset'] else None,
                        last_duration=row['last_duration'] if row['last_duration'] else None,
                        sample_offset=row['sample_offset'],
                        sample_count=row['sample_count'],
                        get_urls=get_urls,
                        key_frame_count=row['key_frame_count'],
                        storage_path=row.get('storage_path')  # Retrieve the stored storage path
                    )
                    segments.append(segment)
            return segments
        except Exception as e:
            logger.error(f"Failed to get flow segments for flow {flow_id}: {e}")
            return []
    
    async def create_object(self, obj: Object) -> bool:
        """Create a new media object in VAST store - TAMS compliant"""
        try:
            # Convert object to dictionary for objects table
            object_data = {
                'id': obj.id,  # Changed from object_id to id
                'size': obj.size or 0,
                'created': obj.created or datetime.now(timezone.utc),
                'last_accessed': datetime.now(timezone.utc),
                'access_count': 0,
            }
            
            # Insert into VAST database as dict of lists
            self.db_manager.insert('objects', {k: [v] for k, v in object_data.items()})
            
            # If there are flow references, insert them into the flow_object_references table
            if obj.referenced_by_flows:
                for flow_id in obj.referenced_by_flows:
                    ref_data = {
                        'object_id': obj.id,
                        'flow_id': flow_id,
                        'created': obj.created or datetime.now(timezone.utc),
                    }
                    self.db_manager.insert('flow_object_references', {k: [v] for k, v in ref_data.items()})
            
            logger.info(f"Created object {obj.id} in VAST store")
            return True
        except Exception as e:
            logger.error(f"Failed to create object {obj.id}: {e}")
            return False
    
    async def get_object(self, object_id: str) -> Optional[Object]:
        """Get media object by ID - TAMS compliant"""
        try:
            # Query for specific object
            predicate = (ibis_.id == object_id)  # Changed from object_id to id
            results = self.db_manager.select('objects', predicate=predicate, output_by_row=True)
            
            if not results:
                return None
            
            # Convert first result back to Object model
            if isinstance(results, list) and results:
                row = results[0]
            elif isinstance(results, dict):
                row = results
            else:
                return None
            
            # Update access count and last accessed time
            access_count = row['access_count'][0] if isinstance(row['access_count'], list) else row['access_count']
            # Safely handle None values for access_count
            if access_count is None:
                access_count = DEFAULT_ACCESS_COUNT_BASE
            update_data = {
                'access_count': access_count + 1,
                'last_accessed': datetime.now(timezone.utc)
            }
            self.db_manager.update('objects', update_data, predicate)
            
            # Get flow references from the flow_object_references table
            ref_predicate = (ibis_.object_id == object_id)
            ref_results = self.db_manager.select('flow_object_references', predicate=ref_predicate, output_by_row=True)
            
            referenced_by_flows = []
            first_referenced_by_flow = None
            
            if ref_results:
                if isinstance(ref_results, list):
                    for ref_row in ref_results:
                        flow_id = ref_row['flow_id'][0] if isinstance(ref_row['flow_id'], list) else ref_row['flow_id']
                        if flow_id:
                            referenced_by_flows.append(str(flow_id))
                            # Set first_referenced_by_flow to the first one we encounter
                            if first_referenced_by_flow is None:
                                first_referenced_by_flow = str(flow_id)
                elif isinstance(ref_results, dict):
                    flow_id = ref_results['flow_id'][0] if isinstance(ref_results['flow_id'], list) else ref_results['flow_id']
                    if flow_id:
                        referenced_by_flows.append(str(flow_id))
                        first_referenced_by_flow = str(flow_id)
            
            # Convert back to Object model
            obj = Object(
                id=str(row['id']),  # Changed from object_id to id
                referenced_by_flows=referenced_by_flows,
                first_referenced_by_flow=first_referenced_by_flow,
                size=int(row['size']) if row['size'] is not None and not isinstance(row['size'], list) else (row['size'][0] if isinstance(row['size'], list) and row['size'] else None),
                created=row['created'] if isinstance(row['created'], (datetime, type(None))) else datetime.fromisoformat(str(row['created'])) if row['created'] else None
            )
            
            return obj
            
        except Exception as e:
            logger.error(f"Failed to get object {object_id}: {e}")
            return None
    
    @trace_operation("analytics_query")
    async def analytics_query(self, query_type: str, **kwargs) -> Dict[str, Any]:
        """
        Perform analytics queries on VAST data
        
        Args:
            query_type: Type of analytics query
            **kwargs: Query-specific parameters
            
        Returns:
            Analytics results
        """
        try:
            start_time = time.time()
            
            if query_type == "flow_usage":
                result = await self._flow_usage_analytics(**kwargs)
            elif query_type == "storage_usage":
                result = await self._storage_usage_analytics(**kwargs)
            elif query_type == "time_range_analysis":
                result = await self._time_range_analysis(**kwargs)
            elif query_type == "catalog_summary":
                result = await self._catalog_summary(**kwargs)
            else:
                raise ValueError(f"Unknown analytics query type: {query_type}")
            
            # Record performance metrics
            duration = time.time() - start_time
            telemetry_manager.record_performance_metrics(
                f"analytics_{query_type}", duration, "vast"
            )
            
            return result
                
        except Exception as e:
            logger.error(f"Analytics query failed: {e}")
            telemetry_manager.record_error("vast_query_error", f"analytics_{query_type}", str(e))
            return {"error": str(e)}
    
    async def _flow_usage_analytics(self, **kwargs) -> Dict[str, Any]:
        """Analyze flow usage patterns using VAST table queries"""
        try:
            # Get all flows
            results = self.db_manager.select('flows')
            
            if not results:
                return {"total_flows": 0, "format_distribution": {}, "estimated_storage_bytes": 0}
            
            # Convert to pandas for analysis
            df = pd.DataFrame(results)
            
            # Group by format and convert numpy types
            format_counts = df['format'].value_counts().to_dict()
            # Convert numpy types to native Python types
            format_counts = {str(k): int(v) if hasattr(v, 'item') else v for k, v in format_counts.items()}
            
            # Calculate storage estimates
            total_storage = DEFAULT_STORAGE_CALCULATION_BASE
            for _, row in df.iterrows():
                try:
                    if row['format'] == "urn:x-nmos:format:video":
                        # Convert numpy types to native Python types and handle None values
                        frame_width = int(row['frame_width']) if hasattr(row['frame_width'], 'item') else row['frame_width']
                        frame_height = int(row['frame_height']) if hasattr(row['frame_height'], 'item') else row['frame_height']
                        if frame_width is not None and frame_height is not None:
                            pixels = frame_width * frame_height
                            total_storage += pixels
                    elif row['format'] == "urn:x-nmos:format:audio":
                        # Convert numpy types to native Python types and handle None values
                        sample_rate = int(row['sample_rate']) if hasattr(row['sample_rate'], 'item') else row['sample_rate']
                        channels = int(row['channels']) if hasattr(row['channels'], 'item') else row['channels']
                        if sample_rate is not None and channels is not None:
                            total_storage += sample_rate * channels * 2
                except (KeyError, TypeError) as e:
                    logger.warning(f"Could not calculate storage for flow: {e}")
                    continue
            
            return {
                "total_flows": len(df),
                "format_distribution": format_counts,
                "estimated_storage_bytes": total_storage,
                "average_flow_size": total_storage / len(df) if len(df) > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Flow usage analytics failed: {e}")
            return {"error": str(e)}
    
    async def _storage_usage_analytics(self, **kwargs) -> Dict[str, Any]:
        """Analyze storage usage patterns"""
        try:
            # Get all objects from database (not S3)
            results = self.db_manager.select('objects')
            
            if not results:
                logger.info("No objects found in storage usage analytics")
                return {
                    "total_objects": 0, 
                    "total_size_bytes": 0, 
                    "average_size_bytes": 0,
                    "most_accessed": 0,
                    "least_accessed": 0,
                    "average_access_count": 0
                }
            
            # Handle different result formats
            if isinstance(results, dict):
                # Column-oriented results
                if 'size' not in results or 'access_count' not in results:
                    logger.warning("Objects table missing required columns for storage analytics")
                    return {
                        "total_objects": len(results.get('object_id', [])), 
                        "total_size_bytes": 0, 
                        "average_size_bytes": 0,
                        "most_accessed": 0,
                        "least_accessed": 0,
                        "average_access_count": 0
                    }
                
                # Convert numpy types to native Python types and filter out None values
                sizes = [int(x) if hasattr(x, 'item') else x for x in results['size'] if x is not None] if results['size'] else []
                access_counts = [int(x) if hasattr(x, 'item') else x for x in results['access_count'] if x is not None] if results['access_count'] else []
                total_size = sum(sizes) if sizes else 0
                total_objects = len(sizes) if sizes else 0
            else:
                # Row-oriented results
                try:
                    df = pd.DataFrame(results)
                    if 'size' not in df.columns or 'access_count' not in df.columns:
                        logger.warning("Objects table missing required columns for storage analytics")
                        return {
                            "total_objects": len(df), 
                            "total_size_bytes": 0, 
                            "average_size_bytes": 0,
                            "most_accessed": 0,
                            "least_accessed": 0,
                            "average_access_count": 0
                        }
                    
                    # Convert numpy types to native Python types and filter out None values
                    sizes = [int(x) if hasattr(x, 'item') else x for x in df['size'].tolist() if x is not None]
                    access_counts = [int(x) if hasattr(x, 'item') else x for x in df['access_count'].tolist() if x is not None]
                    total_size = sum(sizes) if sizes else 0
                    total_objects = len(df)
                except Exception as e:
                    logger.error(f"Failed to process objects data: {e}")
                    return {
                        "total_objects": 0, 
                        "total_size_bytes": 0, 
                        "average_size_bytes": 0,
                        "most_accessed": 0,
                        "least_accessed": 0,
                        "average_access_count": 0
                    }
            
            if total_objects == DEFAULT_STORAGE_CALCULATION_BASE:
                return {
                    "total_objects": 0, 
                    "total_size_bytes": 0, 
                    "average_size_bytes": 0,
                    "most_accessed": 0,
                    "least_accessed": 0,
                    "average_access_count": 0
                }
            
            average_size = total_size / total_objects if total_objects > 0 else 0
            
            # Handle access counts safely
            if isinstance(access_counts, list) and access_counts:
                most_accessed = max(access_counts)
                least_accessed = min(access_counts)
                average_access_count = sum(access_counts) / len(access_counts)
            else:
                most_accessed = DEFAULT_ACCESS_COUNT_BASE
                least_accessed = DEFAULT_ACCESS_COUNT_BASE
                average_access_count = DEFAULT_ACCESS_COUNT_BASE
            
            return {
                "total_objects": total_objects,
                "total_size_bytes": total_size,
                "average_size_bytes": average_size,
                "most_accessed": most_accessed,
                "least_accessed": least_accessed,
                "average_access_count": average_access_count
            }
            
        except Exception as e:
            logger.error(f"Storage usage analytics failed: {e}")
            # Return a safe default response instead of an error
            return {
                "total_objects": 0, 
                "total_size_bytes": 0, 
                "average_size_bytes": 0,
                "most_accessed": 0,
                "least_accessed": 0,
                "average_access_count": 0,
                "note": "Analytics based on database metadata only"
            }
    
    async def _time_range_analysis(self, **kwargs) -> Dict[str, Any]:
        """Analyze time range patterns in flow segments"""
        try:
            # Get all segments
            results = self.db_manager.select('segments')
            
            if not results:
                return {"total_segments": 0, "average_duration": 0}
            
            df = pd.DataFrame(results)
            # Convert numpy types to native Python types and filter out None values
            durations = [float(x) if hasattr(x, 'item') else x for x in df['duration_seconds'].tolist() if x is not None]
            
            if not durations:
                return {"total_segments": len(df), "average_duration": 0}
            
            return {
                "total_segments": len(df),
                "average_duration_seconds": sum(durations) / len(durations),
                "min_duration_seconds": min(durations),
                "max_duration_seconds": max(durations),
                "total_duration_seconds": sum(durations)
            }
            
        except Exception as e:
            logger.error(f"Time range analysis failed: {e}")
            return {"error": str(e)}
    
    async def _catalog_summary(self, **kwargs) -> Dict[str, Any]:
        """Get catalog summary using VAST catalog"""
        try:
            # Get table statistics for all tables
            table_stats = {}
            for table_name in self.db_manager.tables:
                try:
                    stats = self.db_manager.get_table_stats(table_name)
                    table_stats[table_name] = stats
                except Exception as e:
                    logger.warning(f"Could not get stats for table {table_name}: {e}")
            
            return {
                "total_tables": len(self.db_manager.tables),
                "table_names": self.db_manager.tables,
                "table_stats": table_stats
            }
            
        except Exception as e:
            logger.error(f"Catalog summary failed: {e}")
            return {"error": str(e)}
    
    async def list_flows(self, filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> List[Flow]:
        """List flows with optional filtering"""
        try:
            # Build predicate from filters
            predicate = None
            if filters:
                conditions = []
                if 'source_id' in filters:
                    conditions.append((ibis_.source_id == filters['source_id']))
                if 'format' in filters:
                    conditions.append((ibis_.format == filters['format']))
                if 'codec' in filters:
                    conditions.append((ibis_.codec == filters['codec']))
                if 'label' in filters:
                    conditions.append((ibis_.label == filters['label']))
                if 'frame_width' in filters:
                    conditions.append((ibis_.frame_width == filters['frame_width']))
                if 'frame_height' in filters:
                    conditions.append((ibis_.frame_height == filters['frame_height']))
                if conditions:
                    predicate = conditions[0] if len(conditions) == 1 else (conditions[0] & conditions[1])
            
            
            # Query flows
            results = self.db_manager.select('flows', predicate=predicate, output_by_row=True)
            
            # Apply limit
            if limit and isinstance(results, list):
                results = results[:limit]
            elif limit and isinstance(results, dict):
                # For column-oriented results, limit each column
                limited_results = {}
                for key, values in results.items():
                    limited_results[key] = values[:limit]
                results = limited_results
            
            # Convert to Flow models
            flows = []
            if isinstance(results, list):
                for row in results:
                    flow_data = {
                        'id': row['id'],
                        'source_id': row['source_id'],
                        'format': row['format'],
                        'codec': row['codec'],
                        'label': row['label'] if row['label'] else None,
                        'description': row['description'] if row['description'] else None,
                        'created_by': row['created_by'] if row['created_by'] else None,
                        'updated_by': row['updated_by'] if row['updated_by'] else None,
                        'created': row['created'],
                        'metadata_updated': row['metadata_updated'],
                        'tags': Tags(self._json_to_dict(row['tags'])),
                        'container': row['container'] if row['container'] else None,
                        'read_only': row['read_only']
                    }
                    
                    # Add format-specific fields
                    format_type = row['format']
                    if format_type == "urn:x-nmos:format:video":
                        flow_data.update({
                            'frame_width': row['frame_width'],
                            'frame_height': row['frame_height'],
                            'frame_rate': row['frame_rate'],
                        })
                        flow = VideoFlow(**flow_data)
                    elif format_type == "urn:x-nmos:format:audio":
                        flow_data.update({
                            'sample_rate': row['sample_rate'],
                            'bits_per_sample': row['bits_per_sample'],
                            'channels': row['channels'],
                        })
                        flow = AudioFlow(**flow_data)
                    else:
                        flow = DataFlow(**flow_data)
                    
                    flows.append(flow)
            
            return flows
            
        except Exception as e:
            logger.error(f"Failed to list flows: {e}")
            return []
    
    def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """Get statistics for a specific table"""
        try:
            stats = self.db_manager.get_table_stats(table_name)
            return {"table_name": table_name, "stats": stats}
        except Exception as e:
            logger.error(f"Failed to get stats for table {table_name}: {e}")
            return {"error": str(e)}
    
    def list_tables(self) -> List[str]:
        """List all tables in the schema"""
        return self.db_manager.list_tables()
    
    def list_schemas(self) -> List[str]:
        """List all schemas in the bucket"""
        return self.db_manager.list_schemas()
    
    async def delete_source(self, source_id: str, cascade: bool = True) -> bool:
        """
        Delete a source from the VAST store by its unique identifier.
        
        NOTE: According to TAMS API rules, sources CANNOT be deleted - they are immutable.
        This method will always throw an error.
        
        Args:
            source_id (str): The unique identifier of the source to delete.
            cascade (bool): Ignored - sources cannot be deleted.
            
        Returns:
            bool: Never returns - always raises exception.
            
        Raises:
            ValueError: Sources cannot be deleted according to TAMS API rules.
        """
        raise ValueError(
            f"Source {source_id} cannot be deleted. Sources are immutable by design according to TAMS API rules. "
            "Use flow and segment management instead."
        )
    
    async def delete_flow(self, flow_id: str, cascade: bool = True) -> bool:
        """
        Delete a flow from the VAST store by its unique identifier.
        
        According to TAMS API rules:
        - cascade=True: Delete flow + all segments (objects remain immutable)
        - cascade=False: Delete flow ONLY if no segments exist
        
        Args:
            flow_id (str): The unique identifier of the flow to delete.
            cascade (bool): If True, also delete associated segments.
            
        Returns:
            bool: True if the flow was deleted, False if not found or deletion failed.
            
        Raises:
            ValueError: If cascade=False and segments exist
        """
        try:
            from ibis import _ as ibis_
            
            # First check if flow exists
            predicate = (ibis_.id == flow_id)
            results = self.db_manager.select('flows', predicate=predicate, output_by_row=True)
            
            if not results:
                logger.warning(f"Flow {flow_id} not found for deletion")
                return False
            
            # Check for dependent segments
            deps = await self.check_flow_dependencies(flow_id)
            
            if not cascade and deps['has_dependencies']:
                # Cannot delete flow if cascade=False and segments exist
                raise ValueError(
                    f"Cannot delete flow {flow_id}: {deps['segment_count']} dependent segments exist. "
                    "Use cascade=true to delete all dependencies, or delete segments first."
                )
            
            if cascade and deps['has_dependencies']:
                # Check if this is a large deletion that needs async handling
                from ..core.config import get_settings
                settings = get_settings()
                threshold = settings.async_deletion_threshold
                
                if deps['segment_count'] > threshold:
                    logger.warning(f"Large flow deletion detected: {deps['segment_count']} segments (threshold: {threshold}). Consider using async deletion via /flow-delete-requests endpoint for better performance.")
                
                # Delete associated segments first (objects remain immutable)
                await self.delete_flow_segments(flow_id)
            
            # Delete the flow
            deleted_count = self.db_manager.delete('flows', predicate)
            
            if deleted_count > 0:
                logger.info(f"Hard deleted flow {flow_id}")
                return True
            else:
                logger.warning(f"Flow {flow_id} not found for deletion")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete flow {flow_id}: {e}")
            raise  # Re-raise to let caller handle the error
    
    async def delete_flow_segments(self, flow_id: str, timerange: Optional[str] = None) -> bool:
        """
        Delete flow segments for a specific flow.
        
        According to TAMS API rules:
        - Segments can be deleted
        - Objects remain immutable and are NOT deleted
        - Only the segment metadata is removed
        
        Args:
            flow_id (str): The unique identifier of the flow.
            timerange (Optional[str]): Optional timerange filter for segments to delete.
            
        Returns:
            bool: True if segments were deleted, False if deletion failed.
        """
        try:
            from ibis import _ as ibis_
            
            # Get segments to delete
            segments = await self.get_flow_segments(flow_id, timerange)
            
            if not segments:
                logger.info(f"No segments found for flow {flow_id}")
                return True
            
            # Note: According to TAMS API rules, objects are immutable and should NOT be deleted
            # Only segment metadata is removed from the database
            # S3 objects remain available for potential reuse by other flows
            
            # Delete segments from VAST database
            predicate = (ibis_.flow_id == flow_id)
            if timerange:
                predicate = predicate & (ibis_.timerange == timerange)
            
            deleted_count = self.db_manager.delete('segments', predicate)
            
            if deleted_count > 0:
                logger.info(f"Hard deleted {deleted_count} segments for flow {flow_id}")
                return True
            else:
                logger.warning(f"No segments found for flow {flow_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete flow segments for flow {flow_id}: {e}")
            return False
    
    async def delete_object(self, object_id: str) -> bool:
        """
        Delete an object from the VAST store by its unique identifier.
        
        NOTE: According to TAMS API rules, objects can ONLY be deleted via this method.
        They are immutable by design and cannot be deleted via cascade operations.
        
        Args:
            object_id (str): The unique identifier of the object to delete.
            
        Returns:
            bool: True if the object was deleted, False if not found or deletion failed.
        """
        try:
            from ibis import _ as ibis_
            
            # First check if object exists
            predicate = (ibis_.id == object_id)  # Changed from object_id to id
            results = self.db_manager.select('objects', predicate=predicate, output_by_row=True)
            
            if not results:
                logger.warning(f"Object {object_id} not found for deletion")
                return False
            
            # Check if object has any flow references in the flow_object_references table
            # According to TAMS API rules, objects are immutable and cannot be deleted if they have flow references
            ref_predicate = (ibis_.object_id == object_id)
            ref_results = self.db_manager.select('flow_object_references', predicate=ref_predicate, output_by_row=True)
            
            if ref_results:
                ref_count = len(ref_results) if isinstance(ref_results, list) else 1
                logger.error(f"Object {object_id} has {ref_count} flow references. Objects are immutable by design and cannot be deleted while referenced by flows.")
                return False
            
            # Delete the object (only if no flow references exist)
            deleted_count = self.db_manager.delete('objects', predicate)
            
            if deleted_count > 0:
                logger.info(f"Hard deleted object {object_id}")
                return True
            else:
                logger.warning(f"Object {object_id} not found for deletion")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete object {object_id}: {e}")
            return False
    
    async def close(self):
        """Close VAST store and cleanup resources"""
        logger.info("Closing VAST store")
        # The vastdbmanager handles its own connection cleanup 


    
    def column_exists(self, table_name: str, column_name: str) -> bool:
        """
        Check if a column exists in a table.
        
        Args:
            table_name: Name of the table to check
            column_name: Name of the column to check for
            
        Returns:
            True if column exists, False otherwise
        """
        try:
            return self.db_manager.column_exists(table_name, column_name)
        except Exception as e:
            logger.error(f"Failed to check column existence for {table_name}.{column_name}: {e}")
            return False
    
    def add_columns(self, table_name: str, new_columns: pa.Schema) -> bool:
        """
        Add new columns to an existing table.
        
        This is a transactional metadata operation that does not result in any data updates
        or allocations in main storage. Since VAST-DB is a columnar data store, there is
        no impact on subsequent inserts or updates but there is also no provision for
        default values during column addition.
        
        Args:
            table_name: Name of the table to add columns to
            new_columns: PyArrow schema containing the new columns to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.db_manager.add_columns(table_name, new_columns)
            if success:
                logger.info(f"Added columns to table {table_name}: {[field.name for field in new_columns]}")
            return success
        except Exception as e:
            logger.error(f"Failed to add columns to table {table_name}: {e}")
            return False
    
    def rename_column(self, table_name: str, current_column_name: str, new_column_name: str) -> bool:
        """
        Rename a column in a table.
        
        Args:
            table_name: Name of the table containing the column
            current_column_name: Current name of the column to rename
            new_column_name: New name for the column
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.db_manager.rename_column(table_name, current_column_name, new_column_name)
            if success:
                logger.info(f"Renamed column {current_column_name} to {new_column_name} in table {table_name}")
            return success
        except Exception as e:
            logger.error(f"Failed to rename column {current_column_name} in table {table_name}: {e}")
            return False
    
    def drop_column(self, table_name: str, column_to_drop: pa.Schema) -> bool:
        """
        Remove columns from a table.
        
        Column removals are transactional and will operate similarly to data delete operations.
        The column is tombstoned and becomes immediately inaccessible. Async tasks then take
        over and rewrite/unlink data chunks as necessary in main storage. A column removal
        can imply a lot of background activity, similar to a large delete, relative to the
        amount of data in that column (sparsity, data size, etc).
        
        Args:
            table_name: Name of the table to remove columns from
            column_to_drop: PyArrow schema containing the columns to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.db_manager.drop_column(table_name, column_to_drop)
            if success:
                logger.info(f"Dropped columns from table {table_name}: {[field.name for field in column_to_drop]}")
            return success
        except Exception as e:
            logger.error(f"Failed to drop columns from table {table_name}: {e}")
            return False
    
    def list_table_columns(self, table_name: str) -> List[str]:
        """
        Get a list of column names for a table.
        
        Args:
            table_name: Name of the table to list columns for
            
        Returns:
            List of column names
        """
        try:
            schema = self.get_table_columns(table_name)
            return [field.name for field in schema]
        except Exception as e:
            logger.error(f"Failed to list columns for table {table_name}: {e}")
            return []
    
    def get_column_info(self, table_name: str, column_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific column.
        
        Args:
            table_name: Name of the table containing the column
            column_name: Name of the column to get info for
            
        Returns:
            Dictionary containing column information or None if not found
        """
        try:
            schema = self.get_table_columns(table_name)
            for field in schema:
                if field.name == column_name:
                    return {
                        'name': field.name,
                        'type': str(field.type),
                        'nullable': field.nullable,
                        'metadata': field.metadata
                    }
            return None
        except Exception as e:
            logger.error(f"Failed to get column info for {table_name}.{column_name}: {e}")
            return None

    async def update_source_tags(self, source_id: str, tags: Tags) -> bool:
        """
        Update tags for a source.
        
        Args:
            source_id (str): The source ID to update tags for
            tags (Tags): The new tags to set
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert tags to JSON string
            tags_json = self._dict_to_json(tags.root if tags else {})
            
            # Update the tags column in the sources table
            update_data = {'tags': [tags_json]}  # Wrap in list as expected by VastDBManager
            result = self.db_manager.update('sources', update_data, predicate={'id': source_id})
            
            if result and result > 0:
                logger.info(f"Successfully updated tags for source {source_id}")
                return True
            else:
                logger.error(f"Failed to update tags for source {source_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating tags for source {source_id}: {e}")
            return False

    async def list_webhooks(self) -> List[Webhook]:
        """
        List all webhooks.
        
        Returns:
            List of webhook configurations
        """
        try:
            # Get all webhooks from the database - use output_by_row=True to get row-oriented data
            results = self.db_manager.select('webhooks', output_by_row=True)
            
            if not results:
                return []
            
            webhooks = []
            for row in results:
                try:
                    webhook = Webhook(
                        url=row['url'],
                        api_key_name=row['api_key_name'],
                        api_key_value=row.get('api_key_value'),
                        events=self._json_to_list(row['events']),
                        flow_ids=self._json_to_list(row.get('flow_ids')),
                        source_ids=self._json_to_list(row.get('source_ids')),
                        flow_collected_by_ids=self._json_to_list(row.get('flow_collected_by_ids')),
                        source_collected_by_ids=self._json_to_list(row.get('source_collected_by_ids')),
                        accept_get_urls=self._json_to_list(row.get('accept_get_urls')),
                        accept_storage_ids=self._json_to_list(row.get('accept_storage_ids')),
                        presigned=row.get('presigned'),
                        verbose_storage=row.get('verbose_storage'),
                        owner_id=row.get('owner_id'),
                        created_by=row.get('created_by'),
                        created=row['created'] if 'created' in row else None
                    )
                    webhooks.append(webhook)
                except Exception as row_e:
                    logger.error(f"Error processing webhook row: {row_e}")
                    logger.error(f"Row data: {row}")
                    continue
            
            return webhooks
            
        except Exception as e:
            logger.error(f"Failed to list webhooks: {e}")
            return []

    async def create_webhook(self, webhook: WebhookPost) -> bool:
        """
        Create a new webhook.
        
        Args:
            webhook: Webhook configuration to create
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Generate a unique ID for the webhook
            webhook_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            # Prepare webhook data
            webhook_data = {
                'id': [webhook_id],
                'url': [webhook.url],
                'api_key_name': [webhook.api_key_name],
                'api_key_value': [webhook.api_key_value],
                'events': [self._dict_to_json(webhook.events)],
                'flow_ids': [self._dict_to_json(webhook.flow_ids) if webhook.flow_ids else None],
                'source_ids': [self._dict_to_json(webhook.source_ids) if webhook.source_ids else None],
                'flow_collected_by_ids': [self._dict_to_json(webhook.flow_collected_by_ids) if webhook.flow_collected_by_ids else None],
                'source_collected_by_ids': [self._dict_to_json(webhook.source_collected_by_ids) if webhook.source_collected_by_ids else None],
                'accept_get_urls': [self._dict_to_json(webhook.accept_get_urls) if webhook.accept_get_urls else None],
                'accept_storage_ids': [self._dict_to_json(webhook.accept_storage_ids) if webhook.accept_storage_ids else None],
                'presigned': [webhook.presigned if webhook.presigned is not None else True],
                'verbose_storage': [webhook.verbose_storage if webhook.verbose_storage is not None else False],
                'owner_id': [webhook.owner_id],
                'created_by': [webhook.created_by],
                'created': [now],
                'updated': [now]
            }
            
            # Insert the webhook
            result = self.db_manager.insert('webhooks', webhook_data)
            
            if result:
                logger.info(f"Successfully created webhook {webhook_id} for {webhook.url}")
                return True
            else:
                logger.error(f"Failed to create webhook for {webhook.url}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating webhook: {e}")
            return False

    async def update_source_property(self, source_id: str, property_name: str, property_value: Any) -> bool:
        """
        Update a specific property of a source.
        
        Args:
            source_id (str): The source ID to update
            property_name (str): The property name to update
            property_value (Any): The new property value
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Update the specific property in the sources table
            update_data = {property_name: [property_value], 'metadata_updated': [datetime.now(timezone.utc)]}
            result = self.db_manager.update('sources', update_data, predicate={'id': source_id})
            
            if result and result > 0:
                logger.info(f"Successfully updated {property_name} for source {source_id}")
                return True
            else:
                logger.error(f"Failed to update {property_name} for source {source_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating {property_name} for source {source_id}: {e}")
            return False

    async def update_source(self, source_id: str, source: Source) -> bool:
        """
        Update a source with new data.
        
        Args:
            source_id (str): The source ID to update
            source (Source): The updated source data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Prepare update data
            update_data = {
                'label': [source.label],
                'description': [source.description],
                'tags': [self._dict_to_json(source.tags.root if source.tags else {})],
                'source_collection': [self._dict_to_json([item.model_dump() for item in source.source_collection] if source.source_collection else [])],
                'collected_by': [self._dict_to_json([str(uuid) for uuid in source.collected_by] if source.collected_by else [])],
                'metadata_updated': [datetime.now(timezone.utc)]
            }
            
            # Update the source in the database
            result = self.db_manager.update('sources', update_data, predicate={'id': source_id})
            
            if result and result > 0:
                logger.info(f"Successfully updated source {source_id}")
                return True
            else:
                logger.error(f"Failed to update source {source_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating source {source_id}: {e}")
            return False

    async def check_source_dependencies(self, source_id: str) -> Dict[str, Any]:
        """
        Check for dependencies on a source using direct DB queries.
        
        NOTE: According to TAMS API rules, sources CANNOT be deleted - they are immutable.
        This method is provided for informational purposes only.
        
        Args:
            source_id (str): The source ID to check dependencies for
            
        Returns:
            Dict containing dependency information:
            {
                'has_dependencies': bool,
                'flow_count': int,
                'segment_count': int,
                'object_count': int,
                'deletable': False  # Sources are never deletable
            }
        """
        try:
            from ibis import _ as ibis_
            
            # Check for dependent flows (most direct dependency)
            flow_predicate = (ibis_.source_id == source_id)
            flow_results = self.db_manager.select('flows', predicate=flow_predicate, columns=['id'], output_by_row=True)
            
            flow_count = 0
            if isinstance(flow_results, list):
                flow_count = len(flow_results)
            elif isinstance(flow_results, dict) and 'id' in flow_results:
                flow_count = len(flow_results['id']) if isinstance(flow_results['id'], list) else 1
            
            # If no flows, no need to check deeper dependencies
            if flow_count == 0:
                return {
                    'has_dependencies': False,
                    'flow_count': 0,
                    'segment_count': 0,
                    'object_count': 0
                }
            
            # Check for dependent segments (through flows)
            segment_count = 0
            if flow_count > 0:
                # Get flow IDs for segment query
                flow_ids = []
                if isinstance(flow_results, list):
                    flow_ids = [str(row['id']) for row in flow_results]
                elif isinstance(flow_results, dict) and 'id' in flow_results:
                    flow_ids = [str(id_val) for id_val in (flow_results['id'] if isinstance(flow_results['id'], list) else [flow_results['id']])]
                
                # Query segments for these flows
                if flow_ids:
                    # Note: This assumes segments table has flow_id column
                    # If not, we'll need to adjust the query structure
                    segment_predicate = ibis_.flow_id.isin(flow_ids)
                    segment_results = self.db_manager.select('segments', predicate=segment_predicate, columns=['id'], output_by_row=True)
                    
                    if isinstance(segment_results, list):
                        segment_count = len(segment_results)
                    elif isinstance(segment_results, dict) and 'id' in segment_results:
                        segment_count = len(segment_results['id']) if isinstance(segment_results['id'], list) else 1
            
            # Check for dependent objects (through segments)
            object_count = 0
            if segment_count > 0:
                # Query objects that reference these segments
                # Note: Objects have flow_references, not direct segment_id
                # We'll check if any objects reference the flows that contain these segments
                if flow_ids:
                    # Check objects that reference any of the flows
                    object_predicate = ibis_.flow_id.isin(flow_ids)
                    object_results = self.db_manager.select('objects', predicate=object_predicate, columns=['object_id'], output_by_row=True)
                    
                    if isinstance(object_results, list):
                        object_count = len(object_results)
                    elif isinstance(object_results, dict) and 'object_id' in object_results:
                        object_count = len(object_results['object_id']) if isinstance(object_results['object_id'], list) else 1
            
            return {
                'has_dependencies': flow_count > 0 or segment_count > 0 or object_count > 0,
                'flow_count': flow_count,
                'segment_count': segment_count,
                'object_count': object_count
            }
            
        except Exception as e:
            logger.error(f"Failed to check source dependencies for {source_id}: {e}")
            return {
                'has_dependencies': True,  # Assume dependencies exist on error (safer)
                'flow_count': -1,
                'segment_count': -1,
                'object_count': -1
            }
    
    async def update_flow_tags(self, flow_id: str, tags: Tags) -> bool:
        """
        Update tags for a flow.
        
        Args:
            flow_id (str): The flow ID to update tags for
            tags (Tags): The new tags to set
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert tags to JSON string
            tags_json = self._dict_to_json(tags.root if tags else {})
            
            # Update the tags column in the flows table
            update_data = {'tags': [tags_json]}  # Wrap in list as expected by VastDBManager
            result = self.db_manager.update('flows', update_data, predicate={'id': flow_id})
            
            if result and result > 0:
                logger.info(f"Successfully updated tags for flow {flow_id}")
                return True
            else:
                logger.error(f"Failed to update tags for flow {flow_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating tags for flow {flow_id}: {e}")
            return False

    async def update_flow_property(self, flow_id: str, property_name: str, property_value: Any) -> bool:
        """
        Update a specific property of a flow.
        
        Args:
            flow_id (str): The flow ID to update
            property_name (str): The property name to update
            property_value (Any): The new property value
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the actual table schema to know which columns exist
            table_schema = self.db_manager.cache_manager.get_table_columns('flows')
            if table_schema is None:
                logger.error(f"Could not get schema for flows table")
                return False
            
            available_columns = [f.name for f in table_schema]
            
            # Check if the property exists in the schema
            if property_name not in available_columns:
                logger.error(f"Property {property_name} does not exist in flows table schema")
                return False
            
            # Update the specific property in the flows table
            update_data = {property_name: [property_value], 'metadata_updated': [datetime.now(timezone.utc)]}
            result = self.db_manager.update('flows', update_data, predicate={'id': flow_id})
            
            if result and result > 0:
                logger.info(f"Successfully updated {property_name} for flow {flow_id}")
                return True
            else:
                logger.error(f"Failed to update {property_name} for flow {flow_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating {property_name} for flow {flow_id}: {e}")
            return False

    async def update_flow(self, flow_id: str, flow: Flow) -> bool:
        """
        Update a flow with new data.
        
        Args:
            flow_id (str): The flow ID to update
            flow (Flow): The updated flow data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the actual table schema to know which columns exist
            table_schema = self.db_manager.cache_manager.get_table_columns('flows')
            if table_schema is None:
                logger.error(f"Could not get schema for flows table")
                return False
            
            available_columns = [f.name for f in table_schema]
            
            # Prepare update data based on flow type - only include existing columns
            update_data = {}
            
            # Basic fields that should always exist
            if 'label' in available_columns and flow.label is not None:
                update_data['label'] = [flow.label]
            if 'description' in available_columns and flow.description is not None:
                update_data['description'] = [flow.description]
            if 'tags' in available_columns:
                update_data['tags'] = [self._dict_to_json(flow.tags.root if flow.tags else {})]
            if 'metadata_updated' in available_columns:
                update_data['metadata_updated'] = [datetime.now(timezone.utc)]
            
            # Add type-specific fields only if they exist in the schema
            if 'frame_width' in available_columns and hasattr(flow, 'frame_width') and flow.frame_width is not None:
                update_data['frame_width'] = [flow.frame_width]
            if 'frame_height' in available_columns and hasattr(flow, 'frame_height') and flow.frame_height is not None:
                update_data['frame_height'] = [flow.frame_height]
            if 'frame_rate' in available_columns and hasattr(flow, 'frame_rate') and flow.frame_rate is not None:
                update_data['frame_rate'] = [flow.frame_rate]
            if 'read_only' in available_columns and hasattr(flow, 'read_only') and flow.read_only is not None:
                update_data['read_only'] = [flow.read_only]
            if 'flow_collection' in available_columns and hasattr(flow, 'flow_collection') and flow.flow_collection is not None:
                update_data['flow_collection'] = [self._dict_to_json([item.model_dump() for item in flow.flow_collection] if flow.flow_collection else [])]
            
            # Don't include max_bit_rate and avg_bit_rate as they don't exist in the schema
            
            if not update_data:
                logger.warning(f"No valid fields to update for flow {flow_id}")
                return False
            
            # Update the flow in the database
            result = self.db_manager.update('flows', update_data, predicate={'id': flow_id})
            
            if result and result > 0:
                logger.info(f"Successfully updated flow {flow_id}")
                return True
            else:
                logger.error(f"Failed to update flow {flow_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating flow {flow_id}: {e}")
            return False

    async def check_flow_dependencies(self, flow_id: str) -> Dict[str, Any]:
        """
        Efficiently check for dependencies on a flow using direct DB queries.
        
        Args:
            flow_id (str): The flow ID to check dependencies for
            
        Returns:
            Dict containing dependency information:
            {
                'has_dependencies': bool,
                'segment_count': int,
                'object_count': int
            }
        """
        try:
            from ibis import _ as ibis_
            
            # Check for dependent segments
            segment_predicate = (ibis_.flow_id == flow_id)
            segment_results = self.db_manager.select('segments', predicate=segment_predicate, columns=['id'], output_by_row=True)
            
            segment_count = 0
            if isinstance(segment_results, list):
                segment_count = len(segment_results)
            elif isinstance(segment_results, dict) and 'id' in segment_results:
                segment_count = len(segment_results['id']) if isinstance(segment_results['id'], list) else 1
            
            # If no segments, no need to check deeper dependencies
            if segment_count == 0:
                return {
                    'has_dependencies': False,
                    'segment_count': 0,
                    'object_count': 0
                }
            
            # Check for dependent objects (through segments in this flow)
            object_count = 0
            if segment_count > 0:
                # Objects are linked to flows through segments, so we count segments as object references
                # Each segment represents one object reference
                object_count = segment_count
            
            return {
                'has_dependencies': segment_count > 0 or object_count > 0,
                'segment_count': segment_count,
                'object_count': object_count
            }
            
        except Exception as e:
            logger.error(f"Failed to check flow dependencies for {flow_id}: {e}")
            return {
                'has_dependencies': True,  # Assume dependencies exist on error (safer)
                'segment_count': -1,
                'object_count': -1
            }
    
    async def check_segment_dependencies(self, segment_id: str, flow_id: str) -> Dict[str, Any]:
        """
        Efficiently check for dependencies on a segment using direct DB queries.
        
        Args:
            segment_id (str): The segment ID to check dependencies for
            flow_id (str): The flow ID that contains this segment
            
        Returns:
            Dict containing dependency information:
            {
                'has_dependencies': bool,
                'object_count': int
            }
        """
        try:
            from ibis import _ as ibis_
            
            # Check for dependent objects that reference the flow containing this segment
            # Since objects are immutable and linked through segments, we check if this segment
            # is referenced by any other flows (indicating dependency)
            segment_predicate = (ibis_.object_id == segment_id)
            segment_results = self.db_manager.select('segments', predicate=segment_predicate, columns=['id'], output_by_row=True)
            
            dependency_count = 0
            if isinstance(segment_results, list):
                dependency_count = len(segment_results)
            elif isinstance(segment_results, dict) and 'id' in segment_results:
                dependency_count = len(segment_results['id']) if isinstance(segment_results['id'], list) else 1
            
            # A segment has dependencies if it's referenced by multiple flows
            has_dependencies = dependency_count > 1  # More than just the current flow
            
            return {
                'has_dependencies': has_dependencies,
                'object_count': dependency_count
            }
            
        except Exception as e:
            logger.error(f"Failed to check segment dependencies for {segment_id}: {e}")
            return {
                'has_dependencies': True,  # Assume dependencies exist on error (safer)
                'object_count': -1
            }
    
    async def get_dependency_summary(self, entity_type: str, entity_id: str) -> Dict[str, Any]:
        """
        Get a comprehensive dependency summary for any entity type.
        
        Args:
            entity_type (str): Type of entity ('source', 'flow', 'segment')
            entity_id (str): ID of the entity
            
        Returns:
            Dict containing dependency summary
        """
        try:
            if entity_type == 'source':
                return await self.check_source_dependencies(entity_id)
            elif entity_type == 'flow':
                return await self.check_flow_dependencies(entity_id)
            elif entity_type == 'segment':
                # For segments, we need both segment_id and flow_id
                # This is a limitation - we'll need to pass flow_id separately
                logger.warning("Segment dependency check requires flow_id - use check_segment_dependencies(segment_id, flow_id) directly")
                return {'has_dependencies': True, 'error': 'flow_id required for segment dependency check'}
            else:
                logger.error(f"Unknown entity type: {entity_type}")
                return {'has_dependencies': True, 'error': f"Unknown entity type: {entity_type}"}
                
        except Exception as e:
            logger.error(f"Failed to get dependency summary for {entity_type} {entity_id}: {e}")
            return {'has_dependencies': True, 'error': str(e)}
    
    async def create_async_deletion_request(self, flow_id: str, timerange: Optional[str] = None) -> str:
        """
        Create an async deletion request for a flow with many segments.
        
        According to TAMS API rules, flows with >{threshold} segments should use async deletion
        via the /flow-delete-requests endpoint for better performance.
        
        Args:
            flow_id (str): The flow ID to delete
            timerange (Optional[str]): Optional timerange filter for segments
            
        Returns:
            str: The deletion request ID for tracking status
            
        Raises:
            ValueError: If flow has <={threshold} segments (should use sync deletion)
        """
        try:
            # Check flow dependencies first
            deps = await self.check_flow_dependencies(flow_id)
            
            if not deps['has_dependencies']:
                raise ValueError(f"Flow {flow_id} has no segments to delete")
            
            # Get configurable threshold
            from ..core.config import get_settings
            settings = get_settings()
            threshold = settings.async_deletion_threshold
            
            if deps['segment_count'] <= threshold:
                raise ValueError(
                    f"Flow {flow_id} has only {deps['segment_count']} segments (threshold: {threshold}). "
                    "Use sync deletion (cascade=true) for flows with <={threshold} segments."
                )
            
            # Generate unique request ID
            request_id = f"del-{flow_id}-{int(datetime.now().timestamp())}"
            
            # Create deletion request record
            deletion_request = {
                'request_id': request_id,
                'flow_id': flow_id,
                'timerange': timerange or "0:0_999999:0",  # Default to full range
                'status': 'pending',
                'created': datetime.now(timezone.utc),
                'updated': datetime.now(timezone.utc)
            }
            
            # Store the deletion request
            success = await self.create_deletion_request(deletion_request)
            if not success:
                raise RuntimeError(f"Failed to create deletion request for flow {flow_id}")
            
            logger.info(f"Created async deletion request {request_id} for flow {flow_id} with {deps['segment_count']} segments")
            return request_id
            
        except Exception as e:
            logger.error(f"Failed to create async deletion request for flow {flow_id}: {e}")
            raise
    
    async def create_deletion_request(self, deletion_request: Dict[str, Any]) -> bool:
        """
        Create a deletion request record in the database.
        
        Args:
            deletion_request (Dict[str, Any]): Deletion request data
            
        Returns:
            bool: True if created successfully, False otherwise
        """
        try:
            from ibis import _ as ibis_
            
            # Insert deletion request
            rows_inserted = self.db_manager.insert_batch_efficient(
                table_name='deletion_requests',
                data=deletion_request,
                batch_size=1
            )
            
            return rows_inserted > 0
            
        except Exception as e:
            logger.error(f"Failed to create deletion request: {e}")
            return False
    
    async def get_deletion_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a deletion request by ID.
        
        Args:
            request_id (str): The deletion request ID
            
        Returns:
            Optional[Dict[str, Any]]: Deletion request data or None if not found
        """
        try:
            from ibis import _ as ibis_
            
            predicate = (ibis_.id == request_id)
            results = self.db_manager.select('deletion_requests', predicate=predicate, output_by_row=True)
            
            if not results:
                return None
            
            # Convert to dict format
            if isinstance(results, list) and results:
                return dict(results[0])
            elif isinstance(results, dict):
                return results
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get deletion request {request_id}: {e}")
            return None
    
    async def list_deletion_requests(self) -> List[Dict[str, Any]]:
        """
        List all deletion requests.
        
        Returns:
            List[Dict[str, Any]]: List of deletion requests
        """
        try:
            results = self.db_manager.select('deletion_requests', output_by_row=True)
            
            if not results:
                return []
            
            # Convert to list of dicts
            if isinstance(results, list):
                return [dict(row) for row in results]
            elif isinstance(results, dict):
                # Handle column-oriented format
                keys = list(results.keys())
                if keys:
                    return [dict(zip(keys, values)) for values in zip(*results.values())]
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to list deletion requests: {e}")
            return []
    
    async def update_deletion_request_status(self, request_id: str, status: str) -> bool:
        """
        Update the status of a deletion request.
        
        Args:
            request_id (str): The deletion request ID
            status (str): New status ('pending', 'in_progress', 'completed', 'failed')
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        try:
            from ibis import _ as ibis_
            
            # Update status and timestamp
            update_data = {
                'status': status,
                'updated': datetime.now(timezone.utc)
            }
            
            # Note: This assumes the db_manager has an update method
            # If not, we'll need to implement it differently
            success = self.db_manager.update(
                table_name='deletion_requests',
                predicate=(ibis_.id == request_id),
                data=update_data
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update deletion request {request_id} status: {e}")
            return False

    # Flow-Object Reference Management Methods
    
    async def add_flow_object_reference(self, object_id: str, flow_id: str) -> bool:
        """
        Add a flow-object reference relationship.
        
        Args:
            object_id (str): The object ID
            flow_id (str): The flow ID
            
        Returns:
            bool: True if reference was added successfully, False otherwise
        """
        try:
            ref_data = {
                'object_id': object_id,
                'flow_id': flow_id,
                'created': datetime.now(timezone.utc),
            }
            
            # Insert into flow_object_references table
            self.db_manager.insert('flow_object_references', {k: [v] for k, v in ref_data.items()})
            logger.info(f"Added flow-object reference: {flow_id} -> {object_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add flow-object reference {flow_id} -> {object_id}: {e}")
            return False
    
    async def remove_flow_object_reference(self, object_id: str, flow_id: str) -> bool:
        """
        Remove a flow-object reference relationship.
        
        Args:
            object_id (str): The object ID
            flow_id (str): The flow ID
            
        Returns:
            bool: True if reference was removed successfully, False otherwise
        """
        try:
            from ibis import _ as ibis_
            
            predicate = (ibis_.object_id == object_id) & (ibis_.flow_id == flow_id)
            deleted_count = self.db_manager.delete('flow_object_references', predicate)
            
            if deleted_count > 0:
                logger.info(f"Removed flow-object reference: {flow_id} -> {object_id}")
                return True
            else:
                logger.warning(f"Flow-object reference not found: {flow_id} -> {object_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to remove flow-object reference {flow_id} -> {object_id}: {e}")
            return False
    
    async def get_object_flow_references(self, object_id: str) -> List[str]:
        """
        Get all flow IDs that reference a specific object.
        
        Args:
            object_id (str): The object ID
            
        Returns:
            List[str]: List of flow IDs that reference this object
        """
        try:
            from ibis import _ as ibis_
            
            predicate = (ibis_.object_id == object_id)
            results = self.db_manager.select('flow_object_references', predicate=predicate, output_by_row=True)
            
            flow_ids = []
            if results:
                if isinstance(results, list):
                    for row in results:
                        flow_id = row['flow_id'][0] if isinstance(row['flow_id'], list) else row['flow_id']
                        if flow_id:
                            flow_ids.append(str(flow_id))
                elif isinstance(results, dict):
                    flow_id = results['flow_id'][0] if isinstance(results['flow_id'], list) else results['flow_id']
                    if flow_id:
                        flow_ids.append(str(flow_id))
            
            return flow_ids
            
        except Exception as e:
            logger.error(f"Failed to get flow references for object {object_id}: {e}")
            return []
    
    async def get_flow_object_references(self, flow_id: str) -> List[str]:
        """
        Get all object IDs that are referenced by a specific flow.
        
        Args:
            flow_id (str): The flow ID
            
        Returns:
            List[str]: List of object IDs referenced by this flow
        """
        try:
            from ibis import _ as ibis_
            
            predicate = (ibis_.flow_id == flow_id)
            results = self.db_manager.select('flow_object_references', predicate=predicate, output_by_row=True)
            
            object_ids = []
            if results:
                if isinstance(results, list):
                    for row in results:
                        obj_id = row['object_id'][0] if isinstance(row['object_id'], list) else row['object_id']
                        if obj_id:
                            object_ids.append(str(obj_id))
                elif isinstance(results, dict):
                    obj_id = results['object_id'][0] if isinstance(results['object_id'], list) else results['object_id']
                    if obj_id:
                        object_ids.append(str(obj_id))
            
            return object_ids
            
        except Exception as e:
            logger.error(f"Failed to get object references for flow {flow_id}: {e}")
            return []

