"""
Segment Storage Service

This module handles all flow segment-related storage operations including
CRUD operations, filtering, and segment management.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import HTTPException
from .interfaces import StorageInterface
from ..models import FlowSegment, FlowStorage, FlowStoragePost, MediaObject, HttpRequest

logger = logging.getLogger(__name__)


class SegmentStorageService:
    """Handles flow segment-related storage operations"""
    
    def __init__(self, vast_db, s3_client, settings):
        self.vast_db = vast_db
        self.s3_client = s3_client
        self.settings = settings
    
    async def get_flow_segments(self, flow_id: str, timerange: Optional[str] = None) -> List[FlowSegment]:
        """Get flow segments with optional timerange filtering"""
        try:
            # Query segments using vaststore
            query = self.vast_db.query("segments").select("*").where(f"flow_id = '{flow_id}'")
            
            if timerange:
                # Add timerange filtering if provided
                # Note: timerange filtering is complex and would need proper parsing
                # For now, we'll skip timerange filtering to avoid schema issues
                logger.warning("Timerange filtering not yet implemented for segments")
            
            result = query.execute()
            
            # Convert to FlowSegment objects
            segments = []
            # VAST returns a dict with 'data' field containing column arrays
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data:
                    # Convert column arrays to row dictionaries
                    num_rows = len(next(iter(data.values())))
                    for i in range(num_rows):
                        segment_data = {}
                        for column, values in data.items():
                            if column != '$row_id':  # Skip internal row IDs
                                value = values[i] if i < len(values) else None
                                segment_data[column] = value
                        
                        # Reconstruct timerange from separate start/end fields
                        timerange_start = segment_data.pop('timerange_start', None)
                        timerange_end = segment_data.pop('timerange_end', None)
                        
                        # Create timerange object - required field
                        if timerange_start and timerange_end:
                            from ..models.core import TimeRange
                            segment_data['timerange'] = TimeRange(value=f"{timerange_start}_{timerange_end}")
                        elif timerange_start:
                            from ..models.core import TimeRange
                            segment_data['timerange'] = TimeRange(value=str(timerange_start))
                        else:
                            # Provide a default timerange if both are missing
                            from ..models.core import TimeRange
                            segment_data['timerange'] = TimeRange(value="0:0")
                        
                        # Parse JSON fields
                        for field in ['ts_offset', 'last_duration']:
                            if field in segment_data and isinstance(segment_data[field], str):
                                try:
                                    import json
                                    segment_data[field] = json.loads(segment_data[field])
                                except (json.JSONDecodeError, TypeError):
                                    pass
                        
                        segments.append(FlowSegment(**segment_data))
                elif isinstance(data, list):
                    # If data is a list, iterate directly
                    for row in data:
                        segment_data = dict(row) if hasattr(row, '__iter__') and not isinstance(row, str) else row
                        
                        # Reconstruct timerange from separate start/end fields
                        timerange_start = segment_data.pop('timerange_start', None)
                        timerange_end = segment_data.pop('timerange_end', None)
                        
                        # Create timerange object - required field
                        if timerange_start and timerange_end:
                            from ..models.core import TimeRange
                            segment_data['timerange'] = TimeRange(value=f"{timerange_start}_{timerange_end}")
                        elif timerange_start:
                            from ..models.core import TimeRange
                            segment_data['timerange'] = TimeRange(value=str(timerange_start))
                        else:
                            # Provide a default timerange if both are missing
                            from ..models.core import TimeRange
                            segment_data['timerange'] = TimeRange(value="0:0")
                        
                        # Parse JSON fields
                        for field in ['ts_offset', 'last_duration']:
                            if field in segment_data and isinstance(segment_data[field], str):
                                try:
                                    import json
                                    segment_data[field] = json.loads(segment_data[field])
                                except (json.JSONDecodeError, TypeError):
                                    pass
                        segments.append(FlowSegment(**segment_data))
            else:
                # Fallback for direct list results
                for row in result:
                    segment_data = dict(row) if hasattr(row, '__iter__') and not isinstance(row, str) else row
                    # Reconstruct timerange from separate start/end fields
                    timerange_start = segment_data.pop('timerange_start', None)
                    timerange_end = segment_data.pop('timerange_end', None)
                    
                    # Create timerange object - required field
                    if timerange_start and timerange_end:
                        from ..models.core import TimeRange
                        segment_data['timerange'] = TimeRange(value=f"{timerange_start}_{timerange_end}")
                    elif timerange_start:
                        from ..models.core import TimeRange
                        segment_data['timerange'] = TimeRange(value=str(timerange_start))
                    else:
                        # Provide a default timerange if both are missing
                        from ..models.core import TimeRange
                        segment_data['timerange'] = TimeRange(value="0:0")
                    
                    # Parse JSON fields
                    for field in ['ts_offset', 'last_duration']:
                        if field in segment_data and isinstance(segment_data[field], str):
                            try:
                                import json
                                segment_data[field] = json.loads(segment_data[field])
                            except (json.JSONDecodeError, TypeError):
                                pass
                    segments.append(FlowSegment(**segment_data))
            
            return segments
        except Exception as e:
            logger.error("Failed to get flow segments for %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def create_flow_segment(self, flow_id: str, segment: FlowSegment) -> bool:
        """Create a new flow segment"""
        try:
            segment_data = segment.model_dump()
            segment_data['flow_id'] = flow_id
            
            # Handle timerange splitting for database storage
            if 'timerange' in segment_data and segment_data['timerange']:
                timerange_obj = segment_data['timerange']
                if isinstance(timerange_obj, dict) and 'value' in timerange_obj:
                    timerange_value = timerange_obj['value']
                    # Split timerange into start and end for database storage
                    if '_' in timerange_value:
                        timerange_start, timerange_end = timerange_value.split('_', 1)
                        segment_data['timerange_start'] = timerange_start
                        segment_data['timerange_end'] = timerange_end
                        logger.debug(f"Split timerange {timerange_value} into start: {timerange_start}, end: {timerange_end}")
                    else:
                        # If no underscore, treat as start only
                        segment_data['timerange_start'] = timerange_value
                        segment_data['timerange_end'] = timerange_value
                        logger.debug(f"Set timerange {timerange_value} as both start and end")
                    
                    # Remove the original timerange field as it's not in the database schema
                    del segment_data['timerange']
                else:
                    # Handle case where timerange is already a string
                    timerange_value = str(timerange_obj)
                    if '_' in timerange_value:
                        timerange_start, timerange_end = timerange_value.split('_', 1)
                        segment_data['timerange_start'] = timerange_start
                        segment_data['timerange_end'] = timerange_end
                    else:
                        segment_data['timerange_start'] = timerange_value
                        segment_data['timerange_end'] = timerange_value
                    del segment_data['timerange']
            
            # Handle other JSON fields that need to be serialized
            for field in ['ts_offset', 'last_duration', 'get_urls']:
                if field in segment_data and segment_data[field] is not None:
                    if isinstance(segment_data[field], (dict, list)):
                        import json
                        segment_data[field] = json.dumps(segment_data[field])
                        logger.debug(f"Serialized {field} to JSON string")
            
            logger.debug("Creating segment with processed data: %s", segment_data)
            self.vast_db.insert_record("segments", segment_data)
            return True
        except Exception as e:
            logger.error("Failed to create flow segment: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_flow_segments(self, flow_id: str, timerange: Optional[str] = None) -> bool:
        """Delete flow segments"""
        try:
            # Delete segments using vaststore
            query = self.vast_db.query("segments").delete().where(f"flow_id = '{flow_id}'")
            if timerange:
                query = query.where(f"timerange = '{timerange}'")
            
            query.execute()
            return True
        except Exception as e:
            logger.error("Failed to delete flow segments for %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def create_flow_storage(self, flow_id: str, storage_request: FlowStoragePost) -> Optional[FlowStorage]:
        """Create storage allocation for a flow"""
        try:
            import uuid
            
            # Generate object IDs if not provided
            if storage_request.object_ids:
                object_ids = storage_request.object_ids
            else:
                limit = storage_request.limit or self.settings.flow_storage_default_limit
                object_ids = [str(uuid.uuid4()) for _ in range(limit)]
            
            # Validate that object IDs don't already exist
            for object_id in object_ids:
                existing_object = await self._get_object(object_id)
                if existing_object:
                    raise HTTPException(status_code=400, detail=f"Object ID {object_id} already exists")
            
            # Generate storage locations with presigned URLs
            media_objects = []
            for object_id in object_ids:
                # Generate TAMS-compliant storage path
                now = datetime.now()
                year = str(now.year)
                month = f"{now.month:02d}"
                date = f"{now.day:02d}"
                
                # Use TAMS path format: {tams_storage_path}/{year}/{month}/{date}/{object_id}
                storage_path = f"{self.settings.tams_storage_path}/{year}/{month}/{date}/{object_id}"
                
                # Generate presigned URL for upload
                presigned_url = await self._generate_presigned_url(
                    key=storage_path,
                    operation="put_object",
                    expiration=self.settings.s3_presigned_url_upload_timeout
                )
                
                if not presigned_url:
                    raise HTTPException(status_code=500, detail=f"Failed to generate presigned URL for object {object_id}")
                
                # Create MediaObject with the hierarchical path
                media_object = MediaObject(
                    object_id=object_id,
                    put_url=HttpRequest(
                        url=presigned_url,
                        headers={}
                    ),
                    metadata={"storage_path": storage_path}
                )
                
                media_objects.append(media_object)
                
                # Create Object record in database for TAMS compliance
                from ..models import Object
                obj = Object(
                    id=object_id,
                    referenced_by_flows=[flow_id],
                    first_referenced_by_flow=flow_id,
                    created=now
                )
                await self._create_object(obj)
            
            # Create FlowStorage response
            flow_storage = FlowStorage(
                flow_id=flow_id,
                media_objects=media_objects
            )
            
            return flow_storage
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to create flow storage for %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def _get_object(self, object_id: str):
        """Get an object by ID"""
        try:
            result = self.vast_db.query("objects").select("*").where(f"id = '{object_id}'").execute()
            
            # Handle VAST query result format
            rows = []
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict):
                    rows = list(data.values()) if data else []
                elif isinstance(data, list):
                    rows = data
            else:
                rows = result if isinstance(result, list) else []
            
            if not rows or len(rows) == 0:
                return None
            
            return dict(rows[0]) if hasattr(rows[0], '__iter__') and not isinstance(rows[0], str) else rows[0]
        except Exception as e:
            logger.error("Failed to get object %s: %s", object_id, e)
            return None
    
    async def _create_object(self, obj):
        """Create an object"""
        try:
            now = datetime.now(timezone.utc)
            obj.created = now
            
            object_data = obj.model_dump()
            self.vast_db.insert_record("objects", object_data)
            return True
        except Exception as e:
            logger.error("Failed to create object: %s", e)
            return False
    
    async def _generate_presigned_url(self, key: str, operation: str, expiration: int = 3600) -> Optional[str]:
        """Generate presigned URL for S3 operations"""
        try:
            return self.s3_client.generate_presigned_url(
                key=key,
                operation=operation,
                expiration=expiration
            )
        except Exception as e:
            logger.error("Failed to generate presigned URL: %s", e)
            return None
    
    async def get_segments_with_flow_and_object_details(self, flow_id: str) -> List[Dict[str, Any]]:
        """Get segments with flow and object details using join query"""
        try:
            segments_table = self.vast_db.get_qualified_table_name("segments")
            flows_table = self.vast_db.get_qualified_table_name("flows")
            objects_table = self.vast_db.get_qualified_table_name("objects")
            
            sql = f"""
                SELECT 
                    seg.id,
                    seg.flow_id,
                    seg.object_id,
                    seg.timerange_start,
                    seg.timerange_end,
                    seg.ts_offset,
                    seg.last_duration,
                    seg.sample_offset,
                    seg.sample_count,
                    seg.get_urls,
                    seg.key_frame_count,
                    seg.created,
                    f.label as flow_label,
                    f.format as flow_format,
                    f.description as flow_description,
                    o.size as object_size,
                    o.first_referenced_by_flow
                FROM {segments_table} seg
                JOIN {flows_table} f ON seg.flow_id = f.id
                JOIN {objects_table} o ON seg.object_id = o.id
                WHERE seg.flow_id = '{flow_id}'
                ORDER BY seg.timerange_start
            """
            
            result = self.vast_db.execute_sql(sql)
            if result and 'data' in result:
                segments = []
                for row in result['data']:
                    segments.append({
                        "id": row[0],
                        "flow_id": row[1],
                        "object_id": row[2],
                        "timerange_start": row[3],
                        "timerange_end": row[4],
                        "ts_offset": row[5],
                        "last_duration": row[6],
                        "sample_offset": row[7],
                        "sample_count": row[8],
                        "get_urls": row[9],
                        "key_frame_count": row[10],
                        "created": row[11],
                        "flow": {
                            "id": row[1],
                            "label": row[12],
                            "format": row[13],
                            "description": row[14]
                        },
                        "object": {
                            "id": row[2],
                            "size": row[15],
                            "first_referenced_by_flow": row[16]
                        }
                    })
                return segments
            return []
        except Exception as e:
            logger.error("Failed to get segments with flow and object details for %s: %s", flow_id, e)
            return []
    
    async def get_segment_analytics(self, flow_id: Optional[str] = None) -> Dict[str, Any]:
        """Get segment analytics using join queries"""
        try:
            segments_table = self.vast_db.get_qualified_table_name("segments")
            flows_table = self.vast_db.get_qualified_table_name("flows")
            objects_table = self.vast_db.get_qualified_table_name("objects")
            
            where_clause = f"WHERE seg.flow_id = '{flow_id}'" if flow_id else ""
            
            sql = f"""
                SELECT 
                    COUNT(seg.id) as total_segments,
                    COALESCE(SUM(seg.sample_count), 0) as total_samples,
                    COALESCE(SUM(o.size), 0) as total_size_bytes,
                    COUNT(DISTINCT seg.flow_id) as flow_count,
                    COUNT(DISTINCT seg.object_id) as object_count,
                    AVG(seg.sample_count) as avg_samples_per_segment,
                    MIN(seg.timerange_start) as earliest_timerange,
                    MAX(seg.timerange_end) as latest_timerange
                FROM {segments_table} seg
                JOIN {flows_table} f ON seg.flow_id = f.id
                JOIN {objects_table} o ON seg.object_id = o.id
                {where_clause}
            """
            
            result = self.vast_db.execute_sql(sql)
            if result and 'data' in result and len(result['data']) > 0:
                row = result['data'][0]
                return {
                    "total_segments": row[0] if row[0] is not None else 0,
                    "total_samples": row[1] if row[1] is not None else 0,
                    "total_size_bytes": row[2] if row[2] is not None else 0,
                    "flow_count": row[3] if row[3] is not None else 0,
                    "object_count": row[4] if row[4] is not None else 0,
                    "avg_samples_per_segment": row[5] if row[5] is not None else 0,
                    "earliest_timerange": row[6],
                    "latest_timerange": row[7],
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "total_segments": 0,
                    "total_samples": 0,
                    "total_size_bytes": 0,
                    "flow_count": 0,
                    "object_count": 0,
                    "avg_samples_per_segment": 0,
                    "earliest_timerange": None,
                    "latest_timerange": None,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error("Failed to get segment analytics: %s", e)
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
