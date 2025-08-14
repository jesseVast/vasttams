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

logger = logging.getLogger(__name__)


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
                 endpoints: Union[str, List[str]] = "http://main.vast.acme.com",
                 access_key: str = "test-access-key",
                 secret_key: str = "test-secret-key", 
                 bucket: str = "tams-bucket",
                 schema: str = "tams-schema",
                 s3_endpoint_url: str = "http://s3.vast.acme.com",
                 s3_access_key_id: str = "minioadmin",
                 s3_secret_access_key: str = "minioadmin",
                 s3_bucket_name: str = "tams-bucket",
                 s3_use_ssl: bool = False):
        """
        Initialize VAST Store with connection parameters.
        
        Sets up both VAST Database and S3 storage connections, creates necessary
        schemas and tables, and prepares the store for TAMS operations.
        
        Args:
            endpoints: VAST Database endpoint URL(s) - can be single string or list
                     (default: "http://main.vast.acme.com")
            access_key: VAST access key for authentication (default: "test-access-key")
            secret_key: VAST secret key for authentication (default: "test-secret-key")
            bucket: VAST bucket name for TAMS data (default: "tams-bucket")
            schema: VAST schema name for TAMS tables (default: "tams-schema")
            s3_endpoint_url: S3-compatible endpoint URL for media storage
                           (default: "http://s3.vast.acme.com")
            s3_access_key_id: S3 access key ID for media storage (default: "minioadmin")
            s3_secret_access_key: S3 secret access key for media storage (default: "minioadmin")
            s3_bucket_name: S3 bucket name for media segments (default: "tams-bucket")
            s3_use_ssl: Whether to use SSL for S3 communication (default: False)
            
        Raises:
            Exception: If connection setup fails or required tables cannot be created
            
        Note:
            The initialization process:
            1. Establishes VAST Database connection with multiple endpoints
            2. Creates schema if it doesn't exist
            3. Sets up TAMS tables with optimized schemas
            4. Initializes S3 storage connection
            5. Validates all connections are ready
            
        Example:
            >>> store = VASTStore(
            ...     endpoints=["http://vast1.example.com", "http://vast2.example.com"],
            ...     access_key="your_vast_key",
            ...     secret_key="your_vast_secret",
            ...     bucket="tams-data",
            ...     schema="tams-schema",
            ...     s3_endpoint_url="http://s3.example.com",
            ...     s3_access_key_id="your_s3_key",
            ...     s3_secret_access_key="your_s3_secret",
            ...     s3_bucket_name="tams-media",
            ...     s3_use_ssl=True
            ... )
        """
        # Handle both single endpoint and list of endpoints
        if isinstance(endpoints, str):
            self.endpoints = [endpoints]
            self.endpoint = endpoints  # Keep for backward compatibility
        else:
            self.endpoints = endpoints
            self.endpoint = endpoints[0]  # Use first endpoint as primary
            
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self.schema = schema
        
        # Initialize VAST database manager with multiple endpoints
        try:
            self.db_manager = VastDBManager(
                endpoints=self.endpoints  # Pass the full endpoints list
            )
            logger.info(f"VAST Store initialized with {len(self.endpoints)} endpoint(s): {self.endpoints}, bucket: {bucket}, schema: {schema}")
            
            # Setup TAMS tables with schemas
            self._setup_tams_tables()
            
            self.s3_store = S3Store()
            
        except Exception as e:
            logger.error(f"Failed to initialize VAST Store: {e}")
            raise
    
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
            ('updated', pa.timestamp('us')),
            ('tags', pa.string()),  # JSON string
            ('source_collection', pa.string()),  # JSON string
            ('collected_by', pa.string()),  # JSON string
            # Soft delete fields
            ('deleted', pa.bool_()),
            ('deleted_at', pa.timestamp('us')),
            ('deleted_by', pa.string())
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
            ('updated', pa.timestamp('us')),
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
            # Soft delete fields
            ('deleted', pa.bool_()),
            ('deleted_at', pa.timestamp('us')),
            ('deleted_by', pa.string())
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
            # Time-series optimization fields
            ('start_time', pa.timestamp('us')),
            ('end_time', pa.timestamp('us')),
            ('duration_seconds', pa.float64()),
            # Soft delete fields
            ('deleted', pa.bool_()),
            ('deleted_at', pa.timestamp('us')),
            ('deleted_by', pa.string())
        ])
        
        # Object table schema
        object_schema = pa.schema([
            ('object_id', pa.string()),
            ('flow_references', pa.string()),  # JSON string
            ('size', pa.int64()),
            ('created', pa.timestamp('us')),
            ('last_accessed', pa.timestamp('us')),
            ('access_count', pa.int32()),
            # Soft delete fields with default values
            ('deleted', pa.bool_()),
            ('deleted_at', pa.timestamp('us')),
            ('deleted_by', pa.string())
        ])
        
        # Webhook table schema
        webhook_schema = pa.schema([
            ('id', pa.string()),
            ('url', pa.string()),
            ('api_key_name', pa.string()),
            ('api_key_value', pa.string()),
            ('events', pa.string()),  # JSON string
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
            
            # Soft delete fields
            ('deleted', pa.bool_()),
            ('deleted_at', pa.timestamp('us')),
            ('deleted_by', pa.string())
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
            
            # Soft delete fields
            ('deleted', pa.bool_()),
            ('deleted_at', pa.timestamp('us')),
            ('deleted_by', pa.string())
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
            
            # Soft delete fields
            ('deleted', pa.bool_()),
            ('deleted_at', pa.timestamp('us')),
            ('deleted_by', pa.string())
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
            
            # Soft delete fields
            ('deleted', pa.bool_()),
            ('deleted_at', pa.timestamp('us')),
            ('deleted_by', pa.string())
        ])
        
        # Create tables
        tables_config = {
            'sources': source_schema,
            'flows': flow_schema,
            'segments': segment_schema,
            'objects': object_schema,
            'webhooks': webhook_schema,
            'deletion_requests': deletion_request_schema,
            'users': users_schema,
            'api_tokens': api_tokens_schema,
            'refresh_tokens': refresh_tokens_schema,
            'auth_logs': auth_logs_schema
        }
        
        for table_name, schema in tables_config.items():
            try:
                self.db_manager.create_table(table_name, schema)
                logger.info(f"Table '{table_name}' setup complete")
            except Exception as e:
                logger.error(f"Failed to setup table '{table_name}': {e}")
                raise
    
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
                    start_seconds = 0
                
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
                duration = 0
            
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
            if len(parts) == 2:
                seconds = int(parts[0])
                subseconds = int(parts[1]) if parts[1] else 0
                return seconds + (subseconds / 1000000000)  # Assuming nanoseconds
        return 0.0
    
    def _dict_to_json(self, data: Union[Dict[str, Any], List[Any]]) -> str:
        """Convert dictionary or list to JSON string"""
        if not data:
            return ""
        
        # Custom JSON encoder to handle UUIDs and other non-serializable types
        class UUIDEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, uuid.UUID):
                    return str(obj)
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
                'updated': source.updated or datetime.now(timezone.utc),
                'tags': self._dict_to_json(source.tags.root if source.tags else {}),
                'source_collection': self._dict_to_json([item.model_dump() for item in source.source_collection] if source.source_collection else []),
                'collected_by': self._dict_to_json([str(uuid) for uuid in source.collected_by] if source.collected_by else []),
                # Soft delete fields with default values
                'deleted': False,
                'deleted_at': None,
                'deleted_by': None
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
            # Add soft delete filtering
            predicate = self._add_soft_delete_predicate(predicate)
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
                'updated': row['updated'],
                'tags': Tags(self._json_to_dict(row['tags'])),
                'source_collection': [CollectionItem(id=item.get('id', str(uuid.uuid4())), label=item.get('label', '')) if isinstance(item, dict) else CollectionItem(id=str(uuid.uuid4()), label=str(item)) for item in self._json_to_dict(row['source_collection'])],
                'collected_by': [uuid for uuid in self._json_to_dict(row['collected_by'])],
                'deleted': row.get('deleted', False),
                'deleted_at': row.get('deleted_at'),
                'deleted_by': row.get('deleted_by')
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
                    predicate = conditions[0] if len(conditions) == 1 else conditions[0] & conditions[1]
            
            # Add soft delete filtering
            predicate = self._add_soft_delete_predicate(predicate)
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
                        'updated': row['updated'],
                        'tags': Tags(self._json_to_dict(row['tags'])),
                        'source_collection': [CollectionItem(id=item.get('id', str(uuid.uuid4())), label=item.get('label', '')) if isinstance(item, dict) else CollectionItem(id=str(uuid.uuid4()), label=str(item)) for item in self._json_to_dict(row['source_collection'])],
                        'collected_by': [uuid for uuid in self._json_to_dict(row['collected_by'])],
                        'deleted': row.get('deleted', False),
                        'deleted_at': row.get('deleted_at'),
                        'deleted_by': row.get('deleted_by')
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
                'updated': flow.updated or datetime.now(timezone.utc),
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
                # Soft delete fields with default values
                'deleted': False,
                'deleted_at': None,
                'deleted_by': None
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
            # Add soft delete filtering
            predicate = self._add_soft_delete_predicate(predicate)
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
                'updated': row['updated'],
                'tags': Tags(self._json_to_dict(row['tags'])),
                'container': row['container'] if row['container'] else None,
                'read_only': row['read_only'],
                'deleted': row.get('deleted', False),
                'deleted_at': row.get('deleted_at'),
                'deleted_by': row.get('deleted_by')
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
            get_urls_objs = await self.s3_store.create_get_urls(flow_id, segment.object_id, segment.timerange)
            get_urls_json = self._dict_to_json([url.model_dump() for url in get_urls_objs])
            segment_data = {
                'id': str(uuid.uuid4()),
                'flow_id': flow_id,
                'object_id': segment.object_id,
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
                'duration_seconds': duration
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
            predicate = (ibis_.flow_id == flow_id)
            if timerange:
                target_start, target_end, _ = self._parse_timerange(timerange)
                predicate = predicate & (ibis_.start_time <= target_end) & (ibis_.end_time >= target_start)
            
            # Add soft delete filtering
            predicate = self._add_soft_delete_predicate(predicate)
            
            results = self.db_manager.select('segments', predicate=predicate, output_by_row=True)
            segments = []
            if isinstance(results, list):
                for row in results:
                    # get_urls is generated from S3
                    get_urls = await self.s3_store.create_get_urls(flow_id, row['object_id'], row['timerange'])
                    segment = FlowSegment(
                        object_id=row['object_id'],
                        timerange=row['timerange'],
                        ts_offset=row['ts_offset'] if row['ts_offset'] else None,
                        last_duration=row['last_duration'] if row['last_duration'] else None,
                        sample_offset=row['sample_offset'],
                        sample_count=row['sample_count'],
                        get_urls=get_urls,
                        key_frame_count=row['key_frame_count']
                    )
                    segments.append(segment)
            return segments
        except Exception as e:
            logger.error(f"Failed to get flow segments for flow {flow_id}: {e}")
            return []
    
    async def create_object(self, obj: Object) -> bool:
        """Create a new media object in VAST store"""
        try:
            # Convert object to dictionary
            object_data = {
                'object_id': obj.object_id,
                'flow_references': self._dict_to_json(obj.flow_references),
                'size': obj.size or 0,
                'created': obj.created or datetime.now(timezone.utc),
                'last_accessed': datetime.now(timezone.utc),
                'access_count': 0,
                # Soft delete fields with default values
                'deleted': False,
                'deleted_at': None,
                'deleted_by': None
            }
            # Insert into VAST database as dict of lists
            self.db_manager.insert('objects', {k: [v] for k, v in object_data.items()})
            logger.info(f"Created object {obj.object_id} in VAST store")
            return True
        except Exception as e:
            logger.error(f"Failed to create object {obj.object_id}: {e}")
            return False
    
    async def get_object(self, object_id: str) -> Optional[Object]:
        """Get media object by ID"""
        try:
            # Query for specific object
            predicate = (ibis_.object_id == object_id)
            # Add soft delete filtering
            predicate = self._add_soft_delete_predicate(predicate)
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
            update_data = {
                'access_count': access_count + 1,
                'last_accessed': datetime.now(timezone.utc)
            }
            self.db_manager.update('objects', update_data, predicate)
            
            # Convert back to Object model
            flow_refs = self._json_to_dict(row['flow_references'])
            if isinstance(flow_refs, dict):
                flow_refs = [flow_refs]
            elif not isinstance(flow_refs, list):
                flow_refs = []
            obj = Object(
                object_id=str(row['object_id']),
                flow_references=flow_refs,
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
            total_storage = 0
            for _, row in df.iterrows():
                try:
                    if row['format'] == "urn:x-nmos:format:video":
                        # Convert numpy types to native Python types
                        frame_width = int(row['frame_width']) if hasattr(row['frame_width'], 'item') else row['frame_width']
                        frame_height = int(row['frame_height']) if hasattr(row['frame_height'], 'item') else row['frame_height']
                        pixels = frame_width * frame_height
                        total_storage += pixels
                    elif row['format'] == "urn:x-nmos:format:audio":
                        # Convert numpy types to native Python types
                        sample_rate = int(row['sample_rate']) if hasattr(row['sample_rate'], 'item') else row['sample_rate']
                        channels = int(row['channels']) if hasattr(row['channels'], 'item') else row['channels']
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
                
                # Convert numpy types to native Python types
                sizes = [int(x) if hasattr(x, 'item') else x for x in results['size']] if results['size'] else []
                access_counts = [int(x) if hasattr(x, 'item') else x for x in results['access_count']] if results['access_count'] else []
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
                    
                    # Convert numpy types to native Python types
                    sizes = [int(x) if hasattr(x, 'item') else x for x in df['size'].tolist()]
                    access_counts = [int(x) if hasattr(x, 'item') else x for x in df['access_count'].tolist()]
                    total_size = sum(sizes)
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
            
            if total_objects == 0:
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
                most_accessed = 0
                least_accessed = 0
                average_access_count = 0
            
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
            # Convert numpy types to native Python types
            durations = [float(x) if hasattr(x, 'item') else x for x in df['duration_seconds'].tolist()]
            
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
            
            # Add soft delete filtering
            predicate = self._add_soft_delete_predicate(predicate)
            
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
                        'updated': row['updated'],
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
    
    async def close(self):
        """Close VAST store and cleanup resources"""
        logger.info("Closing VAST store")
        # The vastdbmanager handles its own connection cleanup 

    def _add_soft_delete_predicate(self, predicate=None):
        """Add soft delete predicate to exclude deleted records from queries."""
        # Import ibis here to avoid circular imports
        from ibis import _ as ibis_
        
        # Create soft delete predicate using proper Ibis syntax
        soft_delete_predicate = (ibis_.deleted.isnull() | (ibis_.deleted == False))
        
        if predicate is None:
            return soft_delete_predicate
        else:
            # Combine the existing predicate with soft delete using AND
            return predicate & soft_delete_predicate
    
    async def soft_delete_record(self, table_name: str, record_id: str, deleted_by: str) -> bool:
        """Soft delete a record by marking it as deleted."""
        try:
            from datetime import datetime, timezone
            
            # Update the record to mark it as soft deleted
            update_data = {
                'deleted': True,
                'deleted_at': datetime.now(timezone.utc),
                'deleted_by': deleted_by
            }
            
            # Create predicate to find the record
            from ibis import _ as ibis_
            if table_name == 'objects':
                predicate = (ibis_.object_id == record_id)
            elif table_name == 'users':
                predicate = (ibis_.user_id == record_id)
            elif table_name == 'api_tokens':
                predicate = (ibis_.token_id == record_id)
            elif table_name == 'sources':
                predicate = (ibis_.source_id == record_id)
            elif table_name == 'flows':
                predicate = (ibis_.flow_id == record_id)
            elif table_name == 'segments':
                predicate = (ibis_.segment_id == record_id)
            elif table_name == 'webhooks':
                predicate = (ibis_.webhook_id == record_id)
            elif table_name == 'deletion_requests':
                predicate = (ibis_.request_id == record_id)
            else:
                # Default fallback for other tables
                predicate = (ibis_.id == record_id)
            
            # Update the record
            updated_count = self.db_manager.update(table_name, update_data, predicate)
            
            if updated_count > 0:
                logger.info(f"Soft deleted record {record_id} from table {table_name}")
                return True
            else:
                logger.warning(f"Record {record_id} not found in table {table_name} for soft delete")
                return False
                
        except Exception as e:
            logger.error(f"Failed to soft delete record {record_id} from table {table_name}: {e}")
            return False
    
    async def hard_delete_record(self, table_name: str, record_id: str) -> bool:
        """Hard delete a record by removing it from the database."""
        try:
            # Create predicate to find the record
            from ibis import _ as ibis_
            if table_name == 'objects':
                predicate = (ibis_.object_id == record_id)
            elif table_name == 'users':
                predicate = (ibis_.user_id == record_id)
            elif table_name == 'api_tokens':
                predicate = (ibis_.token_id == record_id)
            elif table_name == 'sources':
                predicate = (ibis_.source_id == record_id)
            elif table_name == 'flows':
                predicate = (ibis_.flow_id == record_id)
            elif table_name == 'segments':
                predicate = (ibis_.segment_id == record_id)
            elif table_name == 'webhooks':
                predicate = (ibis_.webhook_id == record_id)
            elif table_name == 'deletion_requests':
                predicate = (ibis_.request_id == record_id)
            else:
                # Default fallback for other tables
                predicate = (ibis_.id == record_id)
            
            # Delete the record
            deleted_count = self.db_manager.delete(table_name, predicate)
            
            if deleted_count > 0:
                logger.info(f"Hard deleted record {record_id} from table {table_name}")
                return True
            else:
                logger.warning(f"Record {record_id} not found in table {table_name} for hard delete")
                return False
                
        except Exception as e:
            logger.error(f"Failed to hard delete record {record_id} from table {table_name}: {e}")
            return False
    
    async def restore_record(self, table_name: str, record_id: str) -> bool:
        """Restore a soft-deleted record by unmarking it as deleted."""
        try:
            # Update the record to unmark it as soft deleted
            update_data = {
                'deleted': False,
                'deleted_at': None,
                'deleted_by': None
            }
            
            # Create predicate to find the record
            from ibis import _ as ibis_
            if table_name == 'objects':
                predicate = (ibis_.object_id == record_id)
            elif table_name == 'users':
                predicate = (ibis_.user_id == record_id)
            elif table_name == 'api_tokens':
                predicate = (ibis_.token_id == record_id)
            elif table_name == 'sources':
                predicate = (ibis_.source_id == record_id)
            elif table_name == 'flows':
                predicate = (ibis_.flow_id == record_id)
            elif table_name == 'segments':
                predicate = (ibis_.segment_id == record_id)
            elif table_name == 'webhooks':
                predicate = (ibis_.webhook_id == record_id)
            elif table_name == 'deletion_requests':
                predicate = (ibis_.request_id == record_id)
            else:
                # Default fallback for other tables
                predicate = (ibis_.id == record_id)
            
            # Update the record
            updated_count = self.db_manager.update(table_name, update_data, predicate)
            
            if updated_count > 0:
                logger.info(f"Restored record {record_id} from table {table_name}")
                return True
            else:
                logger.warning(f"Record {record_id} not found in table {table_name} for restore")
                return False
                
        except Exception as e:
            logger.error(f"Failed to restore record {record_id} from table {table_name}: {e}")
            return False

    async def update_source(self, source_id: str, source: Source) -> bool:
        """Update an existing source in VAST store"""
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
                'updated': source.updated or datetime.now(timezone.utc),
                'tags': self._dict_to_json(source.tags.root if source.tags else {}),
                'source_collection': self._dict_to_json([item.model_dump() for item in source.source_collection] if source.source_collection else []),
                'collected_by': self._dict_to_json([str(uuid) for uuid in source.collected_by] if source.collected_by else [])
            }
            
            # Update in VAST database
            predicate = (ibis_.id == source_id)
            self.db_manager.update('sources', source_data, predicate)
            
            logger.info(f"Updated source {source_id} in VAST store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update source {source_id}: {e}")
            return False

    async def update_source_tags(self, source_id: str, tags) -> bool:
        """Update source tags"""
        try:
            from ibis import _ as ibis_
            predicate = (ibis_.id == source_id)
            predicate = self._add_soft_delete_predicate(predicate)
            
            update_data = {
                'tags': self._dict_to_json(tags.root if tags else {}),
                'updated': datetime.now(timezone.utc)
            }
            
            updated_count = self.db_manager.update('sources', update_data, predicate)
            
            if updated_count > 0:
                logger.info(f"Updated source {source_id} tags")
                return True
            else:
                logger.warning(f"Source {source_id} not found for tags update")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update source {source_id} tags: {e}")
            return False

    async def update_flow_read_only(self, flow_id: str, read_only: bool) -> bool:
        """Update flow read-only status"""
        try:
            from ibis import _ as ibis_
            predicate = (ibis_.id == flow_id)
            predicate = self._add_soft_delete_predicate(predicate)
            
            update_data = {
                'read_only': read_only,
                'updated': datetime.now(timezone.utc)
            }
            
            updated_count = self.db_manager.update('flows', update_data, predicate)
            
            if updated_count > 0:
                logger.info(f"Updated flow {flow_id} read_only to {read_only}")
                return True
            else:
                logger.warning(f"Flow {flow_id} not found for read_only update")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update flow {flow_id} read_only: {e}")
            return False

    async def update_flow(self, flow_id: str, flow: Flow) -> bool:
        """Update an existing flow in VAST store"""
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
                'updated': flow.updated or datetime.now(timezone.utc),
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
                'max_bit_rate': getattr(flow, 'max_bit_rate', None),
                'avg_bit_rate': getattr(flow, 'avg_bit_rate', None),
                'flow_collection': self._dict_to_json([str(uuid) for uuid in getattr(flow, 'flow_collection', [])])
            }
            
            # Update in VAST database
            predicate = (ibis_.id == flow_id)
            self.db_manager.update('flows', flow_data, predicate)
            
            logger.info(f"Updated flow {flow_id} in VAST store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update flow {flow_id}: {e}")
            return False

    async def delete_flow(self, flow_id: str, soft_delete: bool = True, cascade: bool = True, deleted_by: str = "system") -> bool:
        """Delete a flow from VAST store"""
        try:
            if soft_delete:
                # Soft delete - mark as deleted
                success = await self.soft_delete_record('flows', flow_id, deleted_by)
                if success and cascade:
                    # Also soft delete associated segments
                    await self.delete_flow_segments(flow_id, soft_delete=True, deleted_by=deleted_by)
                return success
            else:
                # Hard delete - physically remove
                if cascade:
                    # Also hard delete associated segments
                    await self.delete_flow_segments(flow_id, soft_delete=False, deleted_by=deleted_by)
                
                # Delete from VAST database
                predicate = (ibis_.id == flow_id)
                deleted_count = self.db_manager.delete('flows', predicate)
                
                if deleted_count > 0:
                    logger.info(f"Hard deleted flow {flow_id} from VAST store")
                    return True
                else:
                    logger.warning(f"Flow {flow_id} not found for deletion")
                    return False
            
        except Exception as e:
            logger.error(f"Failed to delete flow {flow_id}: {e}")
            return False

    async def delete_flow_segments(self, flow_id: str, timerange: Optional[str] = None, soft_delete: bool = True, deleted_by: str = "system") -> bool:
        """Delete flow segments from VAST store and S3"""
        try:
            # Get segments to delete
            segments = await self.get_flow_segments(flow_id, timerange=timerange)
            
            if soft_delete:
                # Soft delete - mark segments as deleted
                for segment in segments:
                    await self.soft_delete_record('segments', segment.object_id, deleted_by)
                
                logger.info(f"Soft deleted {len(segments)} flow segments for flow {flow_id}")
                return True
            else:
                # Hard delete - physically remove segments and S3 data
                for segment in segments:
                    # Delete from S3
                    await self.s3_store.delete_flow_segment(flow_id, segment.object_id, segment.timerange)
                
                # Delete from VAST database
                predicate = (ibis_.flow_id == flow_id)
                if timerange:
                    target_start, target_end, _ = self._parse_timerange(timerange)
                    predicate = predicate & (ibis_.start_time <= target_end) & (ibis_.end_time >= target_start)
                
                deleted_count = self.db_manager.delete('segments', predicate)
                
                logger.info(f"Hard deleted {deleted_count} flow segments for flow {flow_id}")
                return True
            
        except Exception as e:
            logger.error(f"Failed to delete flow segments for flow {flow_id}: {e}")
            return False

    async def list_webhooks(self) -> List[Webhook]:
        """List webhooks from VAST store"""
        try:
            results = self.db_manager.select('webhooks', output_by_row=True)
            webhooks = []
            
            if isinstance(results, list):
                for row in results:
                    events = self._json_to_dict(row['events'])
                    if isinstance(events, dict):
                        events = list(events.values())
                    elif not isinstance(events, list):
                        events = []
                    webhook = Webhook(
                        url=row['url'],
                        api_key_name=row['api_key_name'],
                        api_key_value=row.get('api_key_value'),
                        events=events,
                        # Ownership fields for TAMS API v7.0 compliance
                        owner_id=row.get('owner_id'),
                        created_by=row.get('created_by'),
                        created=row.get('created')
                    )
                    webhooks.append(webhook)
            
            return webhooks
            
        except Exception as e:
            logger.error(f"Failed to list webhooks: {e}")
            return []

    async def create_webhook(self, webhook: WebhookPost) -> bool:
        """Create a new webhook in VAST store"""
        try:
            webhook_data = {
                'id': str(uuid.uuid4()),
                'url': webhook.url,
                'api_key_name': webhook.api_key_name,
                'api_key_value': webhook.api_key_value,
                'events': self._dict_to_json(webhook.events),
                # Ownership fields for TAMS API v7.0 compliance
                'owner_id': webhook.owner_id or "system",
                'created_by': webhook.created_by or "system",
                'created': datetime.now(timezone.utc),
                'updated': datetime.now(timezone.utc)
            }
            self.db_manager.insert('webhooks', {k: [v] for k, v in webhook_data.items()})
            logger.info(f"Created webhook for URL {webhook.url}")
            return True
        except Exception as e:
            logger.error(f"Failed to create webhook: {e}")
            return False

    async def list_deletion_requests(self) -> List[DeletionRequest]:
        """List deletion requests from VAST store"""
        try:
            results = self.db_manager.select('deletion_requests', output_by_row=True)
            requests = []
            
            if isinstance(results, list):
                for row in results:
                    request = DeletionRequest(
                        request_id=str(row['id']),
                        flow_id=uuid.UUID(row['flow_id']) if not isinstance(row['flow_id'], uuid.UUID) else row['flow_id'],
                        timerange=row['timerange'],
                        status=str(row['status']),
                        created=row['created'] if isinstance(row['created'], datetime) else datetime.fromisoformat(str(row['created'])),
                        updated=row['updated'] if not row['updated'] or isinstance(row['updated'], datetime) else datetime.fromisoformat(str(row['updated']))
                    )
                    requests.append(request)
            
            return requests
            
        except Exception as e:
            logger.error(f"Failed to list deletion requests: {e}")
            return []

    async def create_deletion_request(self, deletion_request: DeletionRequest) -> bool:
        """Create a new deletion request in VAST store"""
        try:
            request_data = {
                'id': deletion_request.request_id,
                'flow_id': str(deletion_request.flow_id),
                'timerange': deletion_request.timerange,
                'status': deletion_request.status,
                'created': deletion_request.created,
                'updated': deletion_request.updated
            }
            self.db_manager.insert('deletion_requests', {k: [v] for k, v in request_data.items()})
            logger.info(f"Created deletion request {deletion_request.request_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create deletion request: {e}")
            return False

    async def get_deletion_request(self, request_id: str) -> Optional[DeletionRequest]:
        """Get deletion request by ID"""
        try:
            predicate = (ibis_.id == request_id)
            results = self.db_manager.select('deletion_requests', predicate=predicate, output_by_row=True)
            
            if not results:
                return None
            
            if isinstance(results, list) and results:
                row = results[0]
            elif isinstance(results, dict):
                row = results
            else:
                return None
            
            # Defensive extraction for possible list values
            def extract_first(val):
                if isinstance(val, list):
                    return val[0] if val else None
                return val
            req_id = extract_first(row['id'])
            flow_id_val = extract_first(row['flow_id'])
            timerange_val = extract_first(row['timerange'])
            status_val = extract_first(row['status'])
            created_val = extract_first(row['created'])
            updated_val = extract_first(row['updated'])
            if not (req_id and flow_id_val and timerange_val and status_val and created_val):
                return None
            request = DeletionRequest(
                request_id=str(req_id),
                flow_id=uuid.UUID(flow_id_val) if not isinstance(flow_id_val, uuid.UUID) else flow_id_val,
                timerange=timerange_val,
                status=str(status_val),
                created=created_val if isinstance(created_val, datetime) else datetime.fromisoformat(str(created_val)),
                updated=None if not updated_val else (updated_val if isinstance(updated_val, datetime) else datetime.fromisoformat(str(updated_val)))
            )
            
            return request
            
        except Exception as e:
            logger.error(f"Failed to get deletion request {request_id}: {e}")
            return None 

    async def delete_source(self, source_id: str, soft_delete: bool = True, cascade: bool = True, deleted_by: str = "system") -> bool:
        """
        Delete a source from the VAST store by its unique identifier.

        Args:
            source_id (str): The unique identifier of the source to delete.
            soft_delete (bool): If True, mark as deleted instead of physically removing.
            cascade (bool): If True, also delete associated flows.
            deleted_by (str): User or system performing the deletion.

        Returns:
            bool: True if the source was deleted, False if not found or deletion failed.
        """
        try:
            if soft_delete:
                # Soft delete - mark as deleted
                success = await self.soft_delete_record('sources', source_id, deleted_by)
                if success and cascade:
                    # Also soft delete associated flows
                    flows = await self.list_flows({'source_id': source_id})
                    for flow in flows:
                        await self.delete_flow(str(flow.id), soft_delete=True, cascade=True, deleted_by=deleted_by)
                return success
            else:
                # Hard delete - physically remove
                if cascade:
                    # Also hard delete associated flows
                    flows = await self.list_flows({'source_id': source_id})
                    for flow in flows:
                        await self.delete_flow(str(flow.id), soft_delete=False, cascade=True, deleted_by=deleted_by)
                
                # Delete from VAST database
                from ibis import _ as ibis_
                predicate = (ibis_.id == source_id)
                deleted_count = self.db_manager.delete('sources', predicate)
                if deleted_count > 0:
                    logger.info(f"Hard deleted source {source_id} from VAST store")
                    return True
                else:
                    logger.warning(f"Source {source_id} not found for hard deletion")
                    return False
        except Exception as e:
            logger.error(f"Failed to delete source {source_id}: {e}")
            return False 

    async def delete_object(self, object_id: str, soft_delete: bool = True, deleted_by: str = "system") -> bool:
        """
        Delete an object from the VAST store by its unique identifier.

        Args:
            object_id (str): The unique identifier of the object to delete.
            soft_delete (bool): If True, mark as deleted instead of physically removing.
            deleted_by (str): User or system performing the deletion.

        Returns:
            bool: True if the object was deleted, False if not found or deletion failed.
        """
        try:
            if soft_delete:
                # Soft delete - mark as deleted
                success = await self.soft_delete_record('objects', object_id, deleted_by)
                return success
            else:
                # Hard delete - physically remove
                from ibis import _ as ibis_
                predicate = (ibis_.object_id == object_id)
                deleted_count = self.db_manager.delete('objects', predicate)
                if deleted_count > 0:
                    logger.info(f"Hard deleted object {object_id} from VAST store")
                    return True
                else:
                    logger.warning(f"Object {object_id} not found for hard deletion")
                    return False
        except Exception as e:
            logger.error(f"Failed to delete object {object_id}: {e}")
            return False 

    # Authentication methods
    async def create_user(self, user: User) -> bool:
        """Create a new user in VAST store"""
        try:
            user_data = {
                'user_id': user.user_id,
                'username': user.username,
                'email': user.email or "",
                'full_name': user.full_name or "",
                'is_active': user.is_active,
                'is_admin': user.is_admin,
                'password_hash': user.password_hash or "",
                'password_salt': user.password_salt or "",
                'password_changed_at': user.password_changed_at or datetime.now(timezone.utc),
                'failed_login_attempts': user.failed_login_attempts,
                'locked_until': user.locked_until,
                'last_login_at': user.last_login_at,
                'last_login_ip': user.last_login_ip or "",
                'created_by': user.created_by or "system",
                'updated_by': user.updated_by or "system",
                'created': user.created or datetime.now(timezone.utc),
                'updated': user.updated or datetime.now(timezone.utc),
                'metadata': self._dict_to_json(user.metadata or {}),
                'deleted': False,
                'deleted_at': None,
                'deleted_by': None
            }
            self.db_manager.insert('users', {k: [v] for k, v in user_data.items()})
            logger.info(f"Created user {user.username} in VAST store")
            return True
        except Exception as e:
            logger.error(f"Failed to create user {user.username}: {e}")
            return False

    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            predicate = (ibis_.user_id == user_id)
            predicate = self._add_soft_delete_predicate(predicate)
            results = self.db_manager.select('users', predicate=predicate, output_by_row=True)
            
            if not results:
                return None
            
            if isinstance(results, list) and results:
                row = results[0]
            elif isinstance(results, dict):
                row = results
            else:
                return None
            
            user_data = {
                'user_id': row['user_id'],
                'username': row['username'],
                'email': row['email'] if row['email'] else None,
                'full_name': row['full_name'] if row['full_name'] else None,
                'is_active': row['is_active'],
                'is_admin': row['is_admin'],
                'password_hash': row['password_hash'] if row['password_hash'] else None,
                'password_salt': row['password_salt'] if row['password_salt'] else None,
                'password_changed_at': row['password_changed_at'],
                'failed_login_attempts': row['failed_login_attempts'],
                'locked_until': row['locked_until'],
                'last_login_at': row['last_login_at'],
                'last_login_ip': row['last_login_ip'] if row['last_login_ip'] else None,
                'created_by': row['created_by'] if row['created_by'] else None,
                'updated_by': row['updated_by'] if row['updated_by'] else None,
                'created': row['created'],
                'updated': row['updated'],
                'metadata': self._json_to_dict(row['metadata']),
                'deleted': row.get('deleted', False),
                'deleted_at': row.get('deleted_at'),
                'deleted_by': row.get('deleted_by')
            }
            
            return User(**user_data)
            
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        try:
            predicate = (ibis_.username == username)
            predicate = self._add_soft_delete_predicate(predicate)
            results = self.db_manager.select('users', predicate=predicate, output_by_row=True)
            
            if not results:
                return None
            
            if isinstance(results, list) and results:
                row = results[0]
            elif isinstance(results, dict):
                row = results
            else:
                return None
            
            user_data = {
                'user_id': row['user_id'],
                'username': row['username'],
                'email': row['email'] if row['email'] else None,
                'full_name': row['full_name'] if row['full_name'] else None,
                'is_active': row['is_active'],
                'is_admin': row['is_admin'],
                'password_hash': row['password_hash'] if row['password_hash'] else None,
                'password_salt': row['password_salt'] if row['password_salt'] else None,
                'password_changed_at': row['password_changed_at'],
                'failed_login_attempts': row['failed_login_attempts'],
                'locked_until': row['locked_until'],
                'last_login_at': row['last_login_at'],
                'last_login_ip': row['last_login_ip'] if row['last_login_ip'] else None,
                'created_by': row['created_by'] if row['created_by'] else None,
                'updated_by': row['updated_by'] if row['updated_by'] else None,
                'created': row['created'],
                'updated': row['updated'],
                'metadata': self._json_to_dict(row['metadata']),
                'deleted': row.get('deleted', False),
                'deleted_at': row.get('deleted_at'),
                'deleted_by': row.get('deleted_by')
            }
            
            return User(**user_data)
            
        except Exception as e:
            logger.error(f"Failed to get user by username {username}: {e}")
            return None

    async def list_users(self, filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> List[User]:
        """List users with optional filtering"""
        try:
            predicate = None
            if filters:
                conditions = []
                if 'is_active' in filters:
                    conditions.append((ibis_.is_active == filters['is_active']))
                if 'is_admin' in filters:
                    conditions.append((ibis_.is_admin == filters['is_admin']))
                if conditions:
                    predicate = conditions[0] if len(conditions) == 1 else conditions[0] & conditions[1]
            
            predicate = self._add_soft_delete_predicate(predicate)
            results = self.db_manager.select('users', predicate=predicate, output_by_row=True)
            
            if limit and isinstance(results, list):
                results = results[:limit]
            
            users = []
            if isinstance(results, list):
                for row in results:
                    user_data = {
                        'user_id': row['user_id'],
                        'username': row['username'],
                        'email': row['email'] if row['email'] else None,
                        'full_name': row['full_name'] if row['full_name'] else None,
                        'is_active': row['is_active'],
                        'is_admin': row['is_admin'],
                        'password_hash': row['password_hash'] if row['password_hash'] else None,
                        'password_salt': row['password_salt'] if row['password_salt'] else None,
                        'password_changed_at': row['password_changed_at'],
                        'failed_login_attempts': row['failed_login_attempts'],
                        'locked_until': row['locked_until'],
                        'last_login_at': row['last_login_at'],
                        'last_login_ip': row['last_login_ip'] if row['last_login_ip'] else None,
                        'created_by': row['created_by'] if row['created_by'] else None,
                        'updated_by': row['updated_by'] if row['updated_by'] else None,
                        'created': row['created'],
                        'updated': row['updated'],
                        'metadata': self._json_to_dict(row['metadata']),
                        'deleted': row.get('deleted', False),
                        'deleted_at': row.get('deleted_at'),
                        'deleted_by': row.get('deleted_by')
                    }
                    users.append(User(**user_data))
            
            return users
            
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            return []

    async def update_user(self, user_id: str, user: User) -> bool:
        """Update a user"""
        try:
            update_data = {
                'email': user.email or "",
                'full_name': user.full_name or "",
                'is_active': user.is_active,
                'is_admin': user.is_admin,
                'password_hash': user.password_hash or "",
                'password_salt': user.password_salt or "",
                'password_changed_at': user.password_changed_at or datetime.now(timezone.utc),
                'failed_login_attempts': user.failed_login_attempts,
                'locked_until': user.locked_until,
                'last_login_at': user.last_login_at,
                'last_login_ip': user.last_login_ip or "",
                'updated_by': user.updated_by or "system",
                'updated': datetime.now(timezone.utc),
                'metadata': self._dict_to_json(user.metadata or {})
            }
            
            predicate = (ibis_.user_id == user_id)
            predicate = self._add_soft_delete_predicate(predicate)
            
            self.db_manager.update('users', update_data, predicate)
            logger.info(f"Updated user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {e}")
            return False

    async def delete_user(self, user_id: str, soft_delete: bool = True, deleted_by: str = "system") -> bool:
        """Delete a user"""
        try:
            if soft_delete:
                success = await self.soft_delete_record('users', user_id, deleted_by)
            else:
                success = await self.hard_delete_record('users', user_id)
            
            if success:
                logger.info(f"Deleted user {user_id}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            return False

    async def create_api_token(self, token: ApiToken) -> bool:
        """Create a new API token in VAST store"""
        try:
            token_data = {
                'token_id': token.token_id,
                'user_id': token.user_id,
                'token_hash': token.token_hash or "",
                'token_name': token.token_name,
                'token_type': token.token_type,
                'permissions': self._dict_to_json(token.permissions or []),
                'scopes': self._dict_to_json(token.scopes or []),
                'allowed_ips': self._dict_to_json(token.allowed_ips or []),
                'is_active': token.is_active,
                'created_at': token.created_at or datetime.now(timezone.utc),
                'expires_at': token.expires_at,
                'last_used_at': token.last_used_at,
                'last_used_ip': token.last_used_ip or "",
                'usage_count': token.usage_count,
                'revoked_at': token.revoked_at,
                'revoked_by': token.revoked_by or "",
                'revocation_reason': token.revocation_reason or "",
                'created_by': token.created_by or "system",
                'metadata': self._dict_to_json(token.metadata or {}),
                'deleted': False,
                'deleted_at': None,
                'deleted_by': None
            }
            self.db_manager.insert('api_tokens', {k: [v] for k, v in token_data.items()})
            logger.info(f"Created API token {token.token_name} for user {token.user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create API token: {e}")
            return False

    async def get_api_token(self, token_id: str) -> Optional[ApiToken]:
        """Get API token by ID"""
        try:
            predicate = (ibis_.token_id == token_id)
            predicate = self._add_soft_delete_predicate(predicate)
            results = self.db_manager.select('api_tokens', predicate=predicate, output_by_row=True)
            
            if not results:
                return None
            
            if isinstance(results, list) and results:
                row = results[0]
            elif isinstance(results, dict):
                row = results
            else:
                return None
            
            token_data = {
                'token_id': row['token_id'],
                'user_id': row['user_id'],
                'token_name': row['token_name'],
                'token_type': row['token_type'],
                'token_hash': row.get('token_hash'),
                'permissions': self._json_to_list(row['permissions']),
                'scopes': self._json_to_list(row['scopes']),
                'allowed_ips': self._json_to_list(row['allowed_ips']),
                'is_active': row['is_active'],
                'created_at': row['created_at'],
                'expires_at': row['expires_at'],
                'last_used_at': row['last_used_at'],
                'last_used_ip': row['last_used_ip'] if row['last_used_ip'] else None,
                'usage_count': row['usage_count'],
                'revoked_at': row['revoked_at'],
                'revoked_by': row['revoked_by'] if row['revoked_by'] else None,
                'revocation_reason': row['revocation_reason'] if row['revocation_reason'] else None,
                'created_by': row['created_by'] if row['created_by'] else None,
                'metadata': self._json_to_dict(row['metadata']),
                'deleted': row.get('deleted', False),
                'deleted_at': row.get('deleted_at'),
                'deleted_by': row.get('deleted_by')
            }
            
            return ApiToken(**token_data)
            
        except Exception as e:
            logger.error(f"Failed to get API token {token_id}: {e}")
            return None

    async def delete_api_token(self, token_id: str) -> bool:
        """Delete an API token (soft delete)"""
        try:
            # Use soft delete to preserve audit trail
            predicate = (ibis_.token_id == token_id)
            predicate = self._add_soft_delete_predicate(predicate)
            
            # Get the token first to get the token_id for soft delete
            token = await self.get_api_token(token_id)
            if not token:
                return False
                
            success = await self.soft_delete_record('api_tokens', token_id, 'system')
            if success:
                logger.info(f"API token {token_id} soft deleted successfully")
                return True
            else:
                logger.warning(f"API token {token_id} not found for deletion")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete API token {token_id}: {e}")
            return False

    async def list_api_tokens(self, user_id: Optional[str] = None, filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> List[ApiToken]:
        """List API tokens with optional filtering"""
        try:
            predicate = None
            if user_id:
                predicate = (ibis_.user_id == user_id)
            
            if filters:
                conditions = []
                if 'is_active' in filters:
                    conditions.append((ibis_.is_active == filters['is_active']))
                if 'token_type' in filters:
                    conditions.append((ibis_.token_type == filters['token_type']))
                if conditions:
                    if predicate:
                        predicate = predicate & conditions[0] if len(conditions) == 1 else predicate & conditions[0] & conditions[1]
                    else:
                        predicate = conditions[0] if len(conditions) == 1 else conditions[0] & conditions[1]
            
            predicate = self._add_soft_delete_predicate(predicate)
            results = self.db_manager.select('api_tokens', predicate=predicate, output_by_row=True)
            
            if limit and isinstance(results, list):
                results = results[:limit]
            
            tokens = []
            if isinstance(results, list):
                for row in results:
                    token_data = {
                        'token_id': row['token_id'],
                        'user_id': row['user_id'],
                        'token_name': row['token_name'],
                        'token_type': row['token_type'],
                        'permissions': self._json_to_dict(row['permissions']),
                        'scopes': self._json_to_dict(row['scopes']),
                        'allowed_ips': self._json_to_dict(row['allowed_ips']),
                        'is_active': row['is_active'],
                        'created_at': row['created_at'],
                        'expires_at': row['expires_at'],
                        'last_used_at': row['last_used_at'],
                        'last_used_ip': row['last_used_ip'] if row['last_used_ip'] else None,
                        'usage_count': row['usage_count'],
                        'revoked_at': row['revoked_at'],
                        'revoked_by': row['revoked_by'] if row['revoked_by'] else None,
                        'revocation_reason': row['revocation_reason'] if row['revocation_reason'] else None,
                        'created_by': row['created_by'] if row['created_by'] else None,
                        'metadata': self._json_to_dict(row['metadata']),
                        'deleted': row.get('deleted', False),
                        'deleted_at': row.get('deleted_at'),
                        'deleted_by': row.get('deleted_by')
                    }
                    tokens.append(ApiToken(**token_data))
            
            return tokens
            
        except Exception as e:
            logger.error(f"Failed to list API tokens: {e}")
            return []

    async def create_auth_log(self, log: AuthLog) -> bool:
        """Create an authentication log entry"""
        try:
            log_data = {
                'log_id': log.log_id,
                'user_id': log.user_id or "",
                'session_id': log.session_id or "",
                'event_type': log.event_type,
                'auth_method': log.auth_method,
                'success': log.success,
                'ip_address': log.ip_address or "",
                'user_agent': log.user_agent or "",
                'request_path': log.request_path or "",
                'error_code': log.error_code or "",
                'error_message': log.error_message or "",
                'timestamp': log.timestamp or datetime.now(timezone.utc),
                'metadata': self._dict_to_json(log.metadata or {}),
                'deleted': False,
                'deleted_at': None,
                'deleted_by': None
            }
            self.db_manager.insert('auth_logs', {k: [v] for k, v in log_data.items()})
            return True
        except Exception as e:
            logger.error(f"Failed to create auth log: {e}")
            return False 

    # Column Management Methods
    def get_table_columns(self, table_name: str) -> pa.Schema:
        """
        Get column definitions for a specific table.
        
        Args:
            table_name: Name of the table to get columns for
            
        Returns:
            PyArrow schema containing column definitions
        """
        try:
            return self.db_manager.get_table_columns(table_name)
        except Exception as e:
            logger.error(f"Failed to get columns for table {table_name}: {e}")
            raise
    
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

    def select(self, table_name: str, predicate=None, columns=None, limit=None, include_row_ids=False):
        """Select records from a table with optional predicate filtering."""
        try:
            # Add soft delete predicate
            final_predicate = self._add_soft_delete_predicate(predicate)
            
            # Query the database
            result = self.db_manager.select(
                table_name=table_name,
                predicate=final_predicate,
                columns=columns,
                limit=limit,
                include_row_ids=include_row_ids
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in VASTStore select for table {table_name}: {e}")
            raise