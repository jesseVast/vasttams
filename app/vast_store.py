"""
VAST Database Store for TAMS using vastdbmanager.py

This implementation uses the vastdbmanager module to provide a clean interface
to VAST Database for TAMS (Time-addressable Media Store) operations.
"""

import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union, Tuple
import pandas as pd
import pyarrow as pa
from pathlib import Path

from .vastdbmanager import Vastdbmanager
from .models import (
    Source, Flow, FlowSegment, Object, DeletionRequest, 
    TimeRange, UUID, Tags, VideoFlow, AudioFlow, DataFlow, ImageFlow, MultiFlow,
    CollectionItem, GetUrl
)

logger = logging.getLogger(__name__)


class VASTStore:
    """
    VAST Database Store for TAMS using vastdbmanager
    
    This class provides a high-level interface to VAST Database for TAMS operations,
    using the vastdbmanager module for connection and table management.
    """
    
    def __init__(self, 
                 endpoint: str = "http://localhost:8080",
                 access_key: str = "test-access-key",
                 secret_key: str = "test-secret-key", 
                 bucket: str = "tams-bucket",
                 schema: str = "tams-schema"):
        """
        Initialize VAST Store with connection parameters
        
        Args:
            endpoint: VAST Database endpoint URL
            access_key: S3 access key for authentication
            secret_key: S3 secret key for authentication
            bucket: Bucket name for TAMS data
            schema: Schema name for TAMS tables
        """
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self.schema = schema
        
        # Initialize VAST database manager
        try:
            self.db_manager = Vastdbmanager(
                endpoint=endpoint,
                access_key=access_key,
                secret_key=secret_key,
                bucket=bucket,
                schema=schema
            )
            logger.info(f"VAST Store initialized with endpoint: {endpoint}, bucket: {bucket}, schema: {schema}")
            
            # Setup TAMS tables with schemas
            self._setup_tams_tables()
            
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
            ('collected_by', pa.string())  # JSON string
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
            ('flow_collection', pa.string())  # JSON string
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
            ('duration_seconds', pa.float64())
        ])
        
        # Object table schema
        object_schema = pa.schema([
            ('object_id', pa.string()),
            ('flow_references', pa.string()),  # JSON string
            ('size', pa.int64()),
            ('created', pa.timestamp('us')),
            ('last_accessed', pa.timestamp('us')),
            ('access_count', pa.int32())
        ])
        
        # Webhook table schema
        webhook_schema = pa.schema([
            ('id', pa.string()),
            ('url', pa.string()),
            ('api_key_name', pa.string()),
            ('api_key_value', pa.string()),
            ('events', pa.string()),  # JSON string
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
        
        # Create tables
        tables_config = {
            'sources': source_schema,
            'flows': flow_schema,
            'segments': segment_schema,
            'objects': object_schema,
            'webhooks': webhook_schema,
            'deletion_requests': deletion_request_schema
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
                start_time = datetime.fromtimestamp(start_seconds)
                end_time = datetime.fromtimestamp(end_seconds) if end_seconds != float('inf') else start_time + timedelta(seconds=duration)
                
            else:
                # Single timestamp
                start_seconds = self._parse_timestamp(clean_range)
                start_time = datetime.fromtimestamp(start_seconds)
                end_time = start_time
                duration = 0
            
            return start_time, end_time, duration
            
        except Exception as e:
            logger.warning(f"Failed to parse timerange '{timerange}': {e}")
            # Return default values
            now = datetime.utcnow()
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
    
    def _dict_to_json(self, data: Dict[str, Any]) -> str:
        """Convert dictionary to JSON string"""
        return json.dumps(data) if data else ""
    
    def _json_to_dict(self, json_str: str) -> Dict[str, Any]:
        """Convert JSON string to dictionary"""
        try:
            return json.loads(json_str) if json_str else {}
        except json.JSONDecodeError:
            return {}
    
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
                'created': source.created or datetime.utcnow(),
                'updated': source.updated or datetime.utcnow(),
                'tags': self._dict_to_json(source.tags.__root__ if source.tags else {}),
                'source_collection': self._dict_to_json([item.dict() for item in source.source_collection] if source.source_collection else []),
                'collected_by': self._dict_to_json([str(uuid) for uuid in source.collected_by] if source.collected_by else [])
            }
            
            # Insert into VAST database
            self.db_manager.insert('sources', source_data)
            
            logger.info(f"Created source {source.id} in VAST store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create source {source.id}: {e}")
            return False
    
    async def get_source(self, source_id: str) -> Optional[Source]:
        """Get source by ID"""
        try:
            # Query for specific source
            predicate = f"id = '{source_id}'"
            results = self.db_manager.select('sources', predicate=predicate)
            
            if not results:
                return None
            
            # Convert first result back to Source model
            row = results[0]
            source_data = {
                'id': row['id'],
                'format': row['format'],
                'label': row['label'] if row['label'] else None,
                'description': row['description'] if row['description'] else None,
                'created_by': row['created_by'] if row['created_by'] else None,
                'updated_by': row['updated_by'] if row['updated_by'] else None,
                'created': row['created'],
                'updated': row['updated'],
                'tags': Tags(__root__=self._json_to_dict(row['tags'])),
                'source_collection': [CollectionItem(**item) for item in self._json_to_dict(row['source_collection'])],
                'collected_by': [UUID(uuid) for uuid in self._json_to_dict(row['collected_by'])]
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
                    conditions.append(f"label = '{filters['label']}'")
                if 'format' in filters:
                    conditions.append(f"format = '{filters['format']}'")
                if conditions:
                    predicate = " AND ".join(conditions)
            
            # Query sources
            results = self.db_manager.select('sources', predicate=predicate)
            
            # Apply limit
            if limit:
                results = results[:limit]
            
            # Convert to Source models
            sources = []
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
                    'tags': Tags(__root__=self._json_to_dict(row['tags'])),
                    'source_collection': [CollectionItem(**item) for item in self._json_to_dict(row['source_collection'])],
                    'collected_by': [UUID(uuid) for uuid in self._json_to_dict(row['collected_by'])]
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
                'created': flow.created or datetime.utcnow(),
                'updated': flow.updated or datetime.utcnow(),
                'tags': self._dict_to_json(flow.tags.__root__ if flow.tags else {}),
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
                'flow_collection': self._dict_to_json([str(uuid) for uuid in getattr(flow, 'flow_collection', [])])
            }
            
            # Insert into VAST database
            self.db_manager.insert('flows', flow_data)
            
            logger.info(f"Created flow {flow.id} in VAST store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create flow {flow.id}: {e}")
            return False
    
    async def get_flow(self, flow_id: str) -> Optional[Flow]:
        """Get flow by ID"""
        try:
            # Query for specific flow
            predicate = f"id = '{flow_id}'"
            results = self.db_manager.select('flows', predicate=predicate)
            
            if not results:
                return None
            
            # Convert first result back to Flow model
            row = results[0]
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
                'tags': Tags(__root__=self._json_to_dict(row['tags'])),
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
                    'flow_collection': [UUID(uuid) for uuid in self._json_to_dict(row['flow_collection'])],
                })
                return MultiFlow(**flow_data)
            else:
                return DataFlow(**flow_data)
            
        except Exception as e:
            logger.error(f"Failed to get flow {flow_id}: {e}")
            return None
    
    async def create_flow_segment(self, segment: FlowSegment, flow_id: str) -> bool:
        """Create a new flow segment in VAST store"""
        try:
            # Parse timerange for time-series optimization
            start_time, end_time, duration = self._parse_timerange(segment.timerange)
            
            # Convert segment to dictionary
            segment_data = {
                'id': str(uuid.uuid4()),
                'flow_id': flow_id,
                'object_id': segment.object_id,
                'timerange': segment.timerange,
                'ts_offset': segment.ts_offset or "",
                'last_duration': segment.last_duration or "",
                'sample_offset': segment.sample_offset or 0,
                'sample_count': segment.sample_count or 0,
                'get_urls': self._dict_to_json([url.dict() for url in segment.get_urls] if segment.get_urls else []),
                'key_frame_count': segment.key_frame_count or 0,
                'created': datetime.utcnow(),
                'start_time': start_time,
                'end_time': end_time,
                'duration_seconds': duration
            }
            
            # Insert into VAST database
            self.db_manager.insert('segments', segment_data)
            
            logger.info(f"Created flow segment for flow {flow_id} in VAST store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create flow segment for flow {flow_id}: {e}")
            return False
    
    async def get_flow_segments(self, flow_id: str, timerange: Optional[str] = None) -> List[FlowSegment]:
        """Get flow segments with optional time range filtering"""
        try:
            # Build predicate
            predicate = f"flow_id = '{flow_id}'"
            if timerange:
                target_start, target_end, _ = self._parse_timerange(timerange)
                predicate += f" AND start_time <= '{target_end.isoformat()}' AND end_time >= '{target_start.isoformat()}'"
            
            # Query segments
            results = self.db_manager.select('segments', predicate=predicate)
            
            # Convert to FlowSegment models
            segments = []
            for row in results:
                segment = FlowSegment(
                    object_id=row['object_id'],
                    timerange=row['timerange'],
                    ts_offset=row['ts_offset'] if row['ts_offset'] else None,
                    last_duration=row['last_duration'] if row['last_duration'] else None,
                    sample_offset=row['sample_offset'],
                    sample_count=row['sample_count'],
                    get_urls=[GetUrl(**url) for url in self._json_to_dict(row['get_urls'])],
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
                'created': obj.created or datetime.utcnow(),
                'last_accessed': datetime.utcnow(),
                'access_count': 0
            }
            
            # Insert into VAST database
            self.db_manager.insert('objects', object_data)
            
            logger.info(f"Created object {obj.object_id} in VAST store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create object {obj.object_id}: {e}")
            return False
    
    async def get_object(self, object_id: str) -> Optional[Object]:
        """Get media object by ID"""
        try:
            # Query for specific object
            predicate = f"object_id = '{object_id}'"
            results = self.db_manager.select('objects', predicate=predicate)
            
            if not results:
                return None
            
            row = results[0]
            
            # Update access count and last accessed time
            update_data = {
                'access_count': row['access_count'] + 1,
                'last_accessed': datetime.utcnow()
            }
            self.db_manager.update('objects', update_data, predicate)
            
            # Convert back to Object model
            obj = Object(
                object_id=row['object_id'],
                flow_references=self._json_to_dict(row['flow_references']),
                size=row['size'],
                created=row['created']
            )
            
            return obj
            
        except Exception as e:
            logger.error(f"Failed to get object {object_id}: {e}")
            return None
    
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
            if query_type == "flow_usage":
                return await self._flow_usage_analytics(**kwargs)
            elif query_type == "storage_usage":
                return await self._storage_usage_analytics(**kwargs)
            elif query_type == "time_range_analysis":
                return await self._time_range_analysis(**kwargs)
            elif query_type == "catalog_summary":
                return await self._catalog_summary(**kwargs)
            else:
                raise ValueError(f"Unknown analytics query type: {query_type}")
                
        except Exception as e:
            logger.error(f"Analytics query failed: {e}")
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
            
            # Group by format
            format_counts = df['format'].value_counts().to_dict()
            
            # Calculate storage estimates
            total_storage = 0
            for _, row in df.iterrows():
                if row['format'] == "urn:x-nmos:format:video":
                    pixels = row['frame_width'] * row['frame_height']
                    total_storage += pixels
                elif row['format'] == "urn:x-nmos:format:audio":
                    total_storage += row['sample_rate'] * row['channels'] * 2
            
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
            # Get all objects
            results = self.db_manager.select('objects')
            
            if not results:
                return {"total_objects": 0, "total_size": 0, "average_size": 0}
            
            df = pd.DataFrame(results)
            
            total_size = df['size'].sum()
            access_counts = df['access_count'].tolist()
            
            return {
                "total_objects": len(df),
                "total_size_bytes": total_size,
                "average_size_bytes": total_size / len(df),
                "most_accessed": max(access_counts) if access_counts else 0,
                "least_accessed": min(access_counts) if access_counts else 0,
                "average_access_count": sum(access_counts) / len(access_counts) if access_counts else 0
            }
            
        except Exception as e:
            logger.error(f"Storage usage analytics failed: {e}")
            return {"error": str(e)}
    
    async def _time_range_analysis(self, **kwargs) -> Dict[str, Any]:
        """Analyze time range patterns in flow segments"""
        try:
            # Get all segments
            results = self.db_manager.select('segments')
            
            if not results:
                return {"total_segments": 0, "average_duration": 0}
            
            df = pd.DataFrame(results)
            durations = df['duration_seconds'].tolist()
            
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
                    conditions.append(f"source_id = '{filters['source_id']}'")
                if 'format' in filters:
                    conditions.append(f"format = '{filters['format']}'")
                if 'codec' in filters:
                    conditions.append(f"codec = '{filters['codec']}'")
                if 'label' in filters:
                    conditions.append(f"label = '{filters['label']}'")
                if conditions:
                    predicate = " AND ".join(conditions)
            
            # Query flows
            results = self.db_manager.select('flows', predicate=predicate)
            
            # Apply limit
            if limit:
                results = results[:limit]
            
            # Convert to Flow models
            flows = []
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
                    'tags': Tags(__root__=self._json_to_dict(row['tags'])),
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