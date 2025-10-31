"""
TAMS Analytics Service

This module provides analytics data aggregation services for the TAMS API.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from ..analytics.models import (
    AnalyticsSummary,
    StorageStatistics,
    FormatBreakdown,
    TimeStatistics,
    CountStatistics,
    SourceAnalytics,
    FlowAnalytics,
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Handles analytics data aggregation"""
    
    def __init__(self, vast_db):
        self.vast_db = vast_db
    
    def _parse_sql_result(self, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse SQL result from VAST database"""
        if not result or 'data' not in result:
            logger.warning("No data in SQL result")
            return None
        
        data = result['data']
        if not data or len(data) == 0:
            logger.warning("Empty data in SQL result")
            return None
        
        # Handle columnar format (Trino) - dict with column arrays
        if isinstance(data, dict):
            # Convert columnar to row format
            rows = []
            columns = list(data.keys())
            if columns:
                num_rows = len(data[columns[0]]) if data[columns[0]] else 0
                for i in range(num_rows):
                    row = {}
                    for col in columns:
                        if col != '$row_id':  # Skip internal row IDs
                            row[col.lower()] = data[col][i] if i < len(data[col]) else None
                    rows.append(row)
                logger.debug("Parsed %d row(s) from columnar format, columns: %s", len(rows), list(rows[0].keys()) if rows else [])
                return rows[0] if len(rows) == 1 else rows
            return None
        elif isinstance(data, list):
            # Handle list of arrays (positional) or list of dicts
            if len(data) == 0:
                return None
            
            first_row = data[0]
            # If it's a list of arrays, we need column names from the result
            if isinstance(first_row, (list, tuple)):
                # Get column names if available, or use positional
                columns = result.get('columns', [col.lower() for col in ['total_sources', 'total_flows', 'total_segments', 'total_objects', 
                                                                          'total_storage_bytes', 'avg_size_bytes', 'min_size_bytes', 'max_size_bytes',
                                                                          'object_count_with_size', 'video_flows', 'audio_flows', 'image_flows', 
                                                                          'data_flows', 'multi_flows', 'earliest_source_created', 'latest_source_created',
                                                                          'earliest_flow_created', 'latest_flow_created', 'earliest_segment_created',
                                                                          'latest_segment_created', 'earliest_object_created', 'latest_object_created']])
                row = {}
                for idx, val in enumerate(first_row):
                    if idx < len(columns):
                        row[columns[idx].lower() if isinstance(columns[idx], str) else f'col_{idx}'] = val
                logger.debug("Parsed row from list format, keys: %s", list(row.keys()))
                return row
            elif isinstance(first_row, dict):
                # List of dicts - convert keys to lowercase
                row = {k.lower(): v for k, v in first_row.items() if k != '$row_id'}
                logger.debug("Parsed row from dict format, keys: %s", list(row.keys()))
                return row if len(data) == 1 else data
        
        logger.warning("Unknown data format in SQL result: %s", type(data))
        return None
    
    async def get_summary(self) -> AnalyticsSummary:
        """Get comprehensive analytics summary"""
        try:
            sources_table = self.vast_db.get_qualified_table_name("sources")
            flows_table = self.vast_db.get_qualified_table_name("flows")
            segments_table = self.vast_db.get_qualified_table_name("segments")
            objects_table = self.vast_db.get_qualified_table_name("objects")
            
            # Comprehensive overview query
            # Use subqueries to count each entity independently to avoid join issues
            # Wrap all subqueries in COALESCE to handle NULL when tables are empty
            # Note: Using COUNT(*) for segments because segment IDs may be NULL in some cases
            # Segments should have unique IDs (multiple flows can share a segment), but COUNT(*) 
            # handles the current data state where IDs might be NULL
            sql = f"""
                SELECT 
                    COALESCE((SELECT COUNT(DISTINCT id) FROM {sources_table}), 0) as total_sources,
                    COALESCE((SELECT COUNT(DISTINCT id) FROM {flows_table}), 0) as total_flows,
                    COALESCE((SELECT COUNT(*) FROM {segments_table}), 0) as total_segments,
                    COALESCE((SELECT COUNT(DISTINCT id) FROM {objects_table} WHERE id IS NOT NULL), 0) as total_objects,
                    COALESCE((SELECT COALESCE(SUM(size), 0) FROM {objects_table} WHERE size IS NOT NULL), 0) as total_storage_bytes,
                    COALESCE((SELECT COALESCE(AVG(size), 0) FROM {objects_table} WHERE size IS NOT NULL), 0) as avg_size_bytes,
                    (SELECT MIN(size) FROM {objects_table} WHERE size IS NOT NULL) as min_size_bytes,
                    (SELECT MAX(size) FROM {objects_table} WHERE size IS NOT NULL) as max_size_bytes,
                    COALESCE((SELECT COUNT(*) FROM {objects_table} WHERE size IS NOT NULL), 0) as object_count_with_size,
                    COALESCE((SELECT COUNT(DISTINCT id) FROM {flows_table} WHERE format = 'urn:x-nmos:format:video'), 0) as video_flows,
                    COALESCE((SELECT COUNT(DISTINCT id) FROM {flows_table} WHERE format = 'urn:x-nmos:format:audio'), 0) as audio_flows,
                    COALESCE((SELECT COUNT(DISTINCT id) FROM {flows_table} WHERE format = 'urn:x-nmos:format:image'), 0) as image_flows,
                    COALESCE((SELECT COUNT(DISTINCT id) FROM {flows_table} WHERE format = 'urn:x-nmos:format:data'), 0) as data_flows,
                    COALESCE((SELECT COUNT(DISTINCT id) FROM {flows_table} WHERE format = 'urn:x-nmos:format:multi'), 0) as multi_flows,
                    (SELECT MIN(created) FROM {sources_table}) as earliest_source_created,
                    (SELECT MAX(created) FROM {sources_table}) as latest_source_created,
                    (SELECT MIN(created) FROM {flows_table}) as earliest_flow_created,
                    (SELECT MAX(created) FROM {flows_table}) as latest_flow_created,
                    (SELECT MIN(created) FROM {segments_table}) as earliest_segment_created,
                    (SELECT MAX(created) FROM {segments_table}) as latest_segment_created,
                    (SELECT MIN(created) FROM {objects_table} WHERE created IS NOT NULL) as earliest_object_created,
                    (SELECT MAX(created) FROM {objects_table} WHERE created IS NOT NULL) as latest_object_created
            """
            
            result = self.vast_db.execute_sql(sql)
            logger.debug("SQL result type: %s, keys: %s", type(result), list(result.keys()) if isinstance(result, dict) else None)
            if isinstance(result, dict) and 'data' in result:
                logger.debug("Data type: %s, length: %s", type(result['data']), len(result['data']) if hasattr(result['data'], '__len__') else 'N/A')
                if isinstance(result['data'], dict):
                    logger.debug("Columnar data keys: %s", list(result['data'].keys()))
            
            row = self._parse_sql_result(result)
            
            if not row:
                logger.warning("Failed to parse SQL result, returning empty summary")
                # Return empty summary
                return AnalyticsSummary(
                    counts=CountStatistics(),
                    storage=StorageStatistics(),
                    formats=FormatBreakdown(),
                    time=TimeStatistics(),
                )
            
            logger.debug("Parsed row keys: %s", list(row.keys()) if isinstance(row, dict) else type(row))
            logger.debug("Full parsed row: %s", row)
            
            # Helper function to get value case-insensitively
            def get_value(key: str, default=0):
                if not isinstance(row, dict):
                    logger.warning("Row is not a dict, returning default for %s", key)
                    return default
                # Try exact match first
                if key in row:
                    val = row[key]
                    logger.debug("Found %s = %s (type: %s)", key, val, type(val))
                    return val if val is not None else default
                # Try case-insensitive match
                key_lower = key.lower()
                for k, v in row.items():
                    if k.lower() == key_lower:
                        logger.debug("Found %s (case-insensitive) = %s (type: %s)", k, v, type(v))
                        return v if v is not None else default
                logger.warning("Key %s not found in row keys: %s", key, list(row.keys()))
                return default
            
            # Extract values with defaults
            total_sources = int(get_value('total_sources', 0) or 0)
            total_flows = int(get_value('total_flows', 0) or 0)
            total_segments = int(get_value('total_segments', 0) or 0)
            total_objects = int(get_value('total_objects', 0) or 0)
            
            logger.info("Extracted counts - sources: %d, flows: %d, segments: %d, objects: %d", 
                       total_sources, total_flows, total_segments, total_objects)
            total_storage_bytes = int(get_value('total_storage_bytes', 0) or 0)
            avg_size_bytes = float(get_value('avg_size_bytes', 0) or 0)
            min_size_val = get_value('min_size_bytes')
            min_size_bytes = int(min_size_val) if min_size_val is not None and min_size_val != 0 else None
            max_size_val = get_value('max_size_bytes')
            max_size_bytes = int(max_size_val) if max_size_val is not None and max_size_val != 0 else None
            object_count_with_size = int(get_value('object_count_with_size', 0) or 0)
            
            # Calculate averages in Python to avoid CAST issues with Trino
            flows_per_source_avg = (float(total_flows) / total_sources) if total_sources > 0 else 0.0
            segments_per_flow_avg = (float(total_segments) / total_flows) if total_flows > 0 else 0.0
            
            return AnalyticsSummary(
                counts=CountStatistics(
                    total_sources=total_sources,
                    total_flows=total_flows,
                    total_segments=total_segments,
                    total_objects=total_objects,
                    flows_per_source_avg=flows_per_source_avg,
                    segments_per_flow_avg=segments_per_flow_avg,
                ),
                storage=StorageStatistics(
                    total_size_bytes=total_storage_bytes,
                    total_size_mb=round(total_storage_bytes / (1024 * 1024), 2),
                    total_size_gb=round(total_storage_bytes / (1024 * 1024 * 1024), 2),
                    average_size_bytes=round(avg_size_bytes, 2),
                    min_size_bytes=min_size_bytes,
                    max_size_bytes=max_size_bytes,
                    object_count_with_size=object_count_with_size,  # Use the updated count including S3 sizes
                ),
                formats=FormatBreakdown(
                    video_flows=int(get_value('video_flows', 0) or 0),
                    audio_flows=int(get_value('audio_flows', 0) or 0),
                    image_flows=int(get_value('image_flows', 0) or 0),
                    data_flows=int(get_value('data_flows', 0) or 0),
                    multi_flows=int(get_value('multi_flows', 0) or 0),
                    total_flows=int(get_value('total_flows', 0) or 0),
                ),
                time=TimeStatistics(
                    earliest_source_created=self._parse_datetime(get_value('earliest_source_created')),
                    latest_source_created=self._parse_datetime(get_value('latest_source_created')),
                    earliest_flow_created=self._parse_datetime(get_value('earliest_flow_created')),
                    latest_flow_created=self._parse_datetime(get_value('latest_flow_created')),
                    earliest_segment_created=self._parse_datetime(get_value('earliest_segment_created')),
                    latest_segment_created=self._parse_datetime(get_value('latest_segment_created')),
                    earliest_object_created=self._parse_datetime(get_value('earliest_object_created')),
                    latest_object_created=self._parse_datetime(get_value('latest_object_created')),
                ),
            )
            
        except Exception as e:
            logger.error("Error getting analytics summary: %s", e, exc_info=True)
            # Return empty summary on error
            return AnalyticsSummary(
                counts=CountStatistics(),
                storage=StorageStatistics(),
                formats=FormatBreakdown(),
                time=TimeStatistics(),
            )
    
    async def get_source_analytics(self) -> List[SourceAnalytics]:
        """Get analytics per source"""
        try:
            sources_table = self.vast_db.get_qualified_table_name("sources")
            flows_table = self.vast_db.get_qualified_table_name("flows")
            segments_table = self.vast_db.get_qualified_table_name("segments")
            # Objects are referenced via object_id in segments, not a separate table
            
            sql = f"""
                SELECT 
                    s.id,
                    s.label,
                    COUNT(DISTINCT f.id) as flow_count,
                    COUNT(DISTINCT seg.id) as segment_count,
                    0 as total_size_bytes,
                    MIN(s.created) as created
                FROM {sources_table} s
                LEFT JOIN {flows_table} f ON s.id = f.source_id
                LEFT JOIN {segments_table} seg ON f.id = seg.flow_id
                GROUP BY s.id, s.label, s.created
                ORDER BY s.created DESC NULLS LAST
            """
            
            result = self.vast_db.execute_sql(sql)
            rows = self._parse_sql_result(result)
            
            if not rows:
                return []
            
            # Handle both single row and multiple rows
            if isinstance(rows, dict):
                rows = [rows]
            
            analytics_list = []
            for row in rows:
                analytics_list.append(SourceAnalytics(
                    source_id=str(row.get('id', '')),
                    source_label=row.get('label'),
                    flow_count=int(row.get('flow_count', 0) or 0),
                    segment_count=int(row.get('segment_count', 0) or 0),
                    total_size_bytes=int(row.get('total_size_bytes', 0) or 0),
                    created=self._parse_datetime(row.get('created')),
                ))
            
            return analytics_list
            
        except Exception as e:
            logger.error("Error getting source analytics: %s", e, exc_info=True)
            return []
    
    async def get_flow_analytics(self) -> List[FlowAnalytics]:
        """Get analytics per flow"""
        try:
            flows_table = self.vast_db.get_qualified_table_name("flows")
            segments_table = self.vast_db.get_qualified_table_name("segments")
            # Objects are referenced via object_id in segments, not a separate table
            
            sql = f"""
                SELECT 
                    f.id,
                    f.label,
                    f.source_id,
                    f.format,
                    COUNT(DISTINCT seg.id) as segment_count,
                    0 as total_size_bytes,
                    MIN(f.created) as created
                FROM {flows_table} f
                LEFT JOIN {segments_table} seg ON f.id = seg.flow_id
                GROUP BY f.id, f.label, f.source_id, f.format, f.created
                ORDER BY f.created DESC NULLS LAST
            """
            
            result = self.vast_db.execute_sql(sql)
            rows = self._parse_sql_result(result)
            
            if not rows:
                return []
            
            # Handle both single row and multiple rows
            if isinstance(rows, dict):
                rows = [rows]
            
            analytics_list = []
            for row in rows:
                analytics_list.append(FlowAnalytics(
                    flow_id=str(row.get('id', '')),
                    flow_label=row.get('label'),
                    source_id=str(row.get('source_id', '')) if row.get('source_id') else None,
                    format=str(row.get('format', '')),
                    segment_count=int(row.get('segment_count', 0) or 0),
                    total_size_bytes=int(row.get('total_size_bytes', 0) or 0),
                    created=self._parse_datetime(row.get('created')),
                ))
            
            return analytics_list
            
        except Exception as e:
            logger.error("Error getting flow analytics: %s", e, exc_info=True)
            return []
    
    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime from various formats"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                # Try ISO format
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except:
                try:
                    # Try common formats
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
                        try:
                            return datetime.strptime(value, fmt)
                        except:
                            continue
                except:
                    pass
        return None

