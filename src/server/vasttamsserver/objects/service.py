"""
Object Storage Service

This module handles all media object-related storage operations including
CRUD operations and object management.
"""

import logging
import json
import urllib.parse
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from fastapi import HTTPException
from ..common.storage.interfaces import StorageInterface
from ..common.storage.timestamp_utils import (
    get_tams_timestamp,
    prepare_data_for_pyarrow
)
from .models import Object, ObjectInstance

logger = logging.getLogger(__name__)


class ObjectStorageService:
    """Handles media object-related storage operations"""
    
    def __init__(self, vast_db, s3_client):
        self.vast_db = vast_db
        self.s3_client = s3_client
    
    async def get_object(self, object_id: str) -> Optional[Object]:
        """Get a specific object by ID using optimized JOIN query"""
        try:
            # Use JOIN query to get object with referenced flows in a single query
            # This is more efficient than separate queries
            objects_table = self.vast_db.get_qualified_table_name("objects")
            segments_table = self.vast_db.get_qualified_table_name("segments")
            
            join_query = f"""
                SELECT 
                    o.id,
                    o.size,
                    o.timerange,
                    o.created,
                    o.first_referenced_by_flow,
                    o.metadata,
                    s.flow_id,
                    s.created as segment_created
                FROM {objects_table} o
                LEFT JOIN {segments_table} s ON o.id = s.object_id AND s.flow_id IS NOT NULL
                WHERE o.id = '{object_id}'
                ORDER BY s.created ASC
            """
            
            join_result = self.vast_db.execute_sql(join_query)
            
            # Debug logging for troubleshooting
            logger.debug("get_object query result type: %s, keys: %s", type(join_result), list(join_result.keys()) if isinstance(join_result, dict) else "N/A")
            
            # Process JOIN results: extract object data and collect flow_ids
            object_data = None
            referenced_flows = []
            first_ref_flow_id = None
            first_ref_created = None
            
            if isinstance(join_result, dict) and 'data' in join_result:
                data = join_result['data']
                if isinstance(data, dict) and data:
                    # Columnar format
                    # Check if we have any columns with data
                    if not data:
                        logger.warning("get_object: Empty data dict for object_id %s", object_id)
                        return None
                    
                    # Debug: log what columns we have
                    logger.debug("get_object: Data columns: %s", list(data.keys()))
                    
                    # Get number of rows from first non-empty column
                    num_rows = 0
                    for col_name, col_values in data.items():
                        if col_values and isinstance(col_values, list):
                            num_rows = len(col_values)
                            logger.debug("get_object: Found %d rows from column '%s'", col_name)
                            break
                    
                    if num_rows == 0:
                        logger.warning("get_object: No rows returned for object_id %s (object may not exist). Data keys: %s", object_id, list(data.keys()) if isinstance(data, dict) else "N/A")
                        return None
                    
                    # Get object data from first row
                    # Note: summary is a VAST extension and not part of TAMS Object model
                    # It's managed separately by /api/vast/objects endpoints, not included in TAMS /api/tams/v8.0/objects
                    object_data = {
                        'id': data.get('id', [None])[0] if data.get('id') else None,
                        'size': data.get('size', [None])[0] if data.get('size') else None,
                        'timerange': data.get('timerange', [None])[0] if data.get('timerange') else None,
                        'created': data.get('created', [None])[0] if data.get('created') else None,
                        'first_referenced_by_flow': data.get('first_referenced_by_flow', [None])[0] if data.get('first_referenced_by_flow') else None,
                        'metadata': data.get('metadata', [None])[0] if data.get('metadata') else None,
                    }
                    
                    # Collect all flow_ids from all rows
                    flow_ids = data.get('flow_id', [])
                    segment_created = data.get('segment_created', [])
                    for i in range(num_rows):
                        if i < len(flow_ids) and flow_ids[i]:
                            flow_id = str(flow_ids[i])
                            if flow_id not in referenced_flows:
                                referenced_flows.append(flow_id)
                            
                            # Track first referenced flow (earliest segment creation)
                            if i < len(segment_created) and segment_created[i]:
                                if first_ref_created is None or segment_created[i] < first_ref_created:
                                    first_ref_created = segment_created[i]
                                    first_ref_flow_id = flow_id
                elif isinstance(data, list) and len(data) > 0:
                    # Row-oriented format
                    first_row = data[0]
                    if isinstance(first_row, dict):
                        object_data = {
                            'id': first_row.get('id'),
                            'size': first_row.get('size'),
                            'timerange': first_row.get('timerange'),
                            'created': first_row.get('created'),
                            'first_referenced_by_flow': first_row.get('first_referenced_by_flow'),
                            'metadata': first_row.get('metadata'),
                        }
                        
                        # Collect flow_ids from all rows
                        for row in data:
                            if isinstance(row, dict) and row.get('flow_id'):
                                flow_id = str(row['flow_id'])
                                if flow_id not in referenced_flows:
                                    referenced_flows.append(flow_id)
                                
                                # Track first referenced flow
                                seg_created = row.get('segment_created')
                                if seg_created:
                                    if first_ref_created is None or seg_created < first_ref_created:
                                        first_ref_created = seg_created
                                        first_ref_flow_id = flow_id
            elif isinstance(join_result, list) and len(join_result) > 0:
                # Direct list result
                first_row = join_result[0]
                if isinstance(first_row, dict):
                    object_data = {
                        'id': first_row.get('id'),
                        'size': first_row.get('size'),
                        'timerange': first_row.get('timerange'),
                        'created': first_row.get('created'),
                        'first_referenced_by_flow': first_row.get('first_referenced_by_flow'),
                        'metadata': first_row.get('metadata'),
                    }
                    
                    # Collect flow_ids from all rows
                    for row in join_result:
                        if isinstance(row, dict) and row.get('flow_id'):
                            flow_id = str(row['flow_id'])
                            if flow_id not in referenced_flows:
                                referenced_flows.append(flow_id)
                            
                            # Track first referenced flow
                            seg_created = row.get('segment_created')
                            if seg_created:
                                if first_ref_created is None or seg_created < first_ref_created:
                                    first_ref_created = seg_created
                                    first_ref_flow_id = flow_id
            
            if not object_data or not object_data.get('id'):
                return None
            
            # Validate that we have object data, not instance data
            if 'label' in object_data and 'id' not in object_data:
                logger.error("get_object received instance data instead of object data for object_id %s", object_id)
                return None
            
            # Set referenced_by_flows (TAMS spec requirement)
            object_data['referenced_by_flows'] = referenced_flows if referenced_flows else []
            
            # Set first_referenced_by_flow if we found one from the JOIN query
            if first_ref_flow_id:
                object_data['first_referenced_by_flow'] = first_ref_flow_id
            elif not object_data.get('first_referenced_by_flow'):
                # Fallback: use the first referenced flow if we have any
                if referenced_flows:
                    object_data['first_referenced_by_flow'] = referenced_flows[0]
            
            # Parse timerange
            import json
            from ..common.models import TimeRange
            
            # Handle timerange - can be None or a string in database, but model requires TimeRange (TAMS spec requirement)
            if 'timerange' in object_data:
                timerange_value = object_data.get('timerange')
                if timerange_value is None or timerange_value == '':
                    # Provide a default timerange if missing (required by model)
                    object_data['timerange'] = TimeRange(value="0:0")
                elif isinstance(timerange_value, str):
                    # Convert string to TimeRange object
                    object_data['timerange'] = TimeRange(value=timerange_value)
                elif not isinstance(timerange_value, TimeRange):
                    # If it's already a dict or other format, try to convert
                    if isinstance(timerange_value, dict):
                        object_data['timerange'] = TimeRange(**timerange_value)
                    else:
                        # Fallback to default
                        object_data['timerange'] = TimeRange(value="0:0")
            else:
                # No timerange field - provide default
                object_data['timerange'] = TimeRange(value="0:0")
            
            # Remove metadata from object_data before creating Object model
            # (metadata is internal-only, not part of TAMS API contract)
            internal_metadata = None
            if 'metadata' in object_data:
                if isinstance(object_data['metadata'], str):
                    try:
                        internal_metadata = json.loads(object_data['metadata'])
                    except (json.JSONDecodeError, TypeError):
                        internal_metadata = None
                else:
                    internal_metadata = object_data['metadata']
                del object_data['metadata']
            
            # Check if size is missing and update from S3 if needed (fallback)
            # Note: The WHERE clause (size IS NULL OR size = 0) ensures atomicity and prevents
            # race conditions with background task updates. If both paths try to update simultaneously,
            # only one will succeed, which is safe and idempotent.
            if object_data.get('size') is None and internal_metadata and self.s3_client:
                storage_path = internal_metadata.get('storage_path')
                if storage_path:
                    try:
                        # Get object metadata from S3
                        s3_metadata = self.s3_client.get_object_metadata(key=storage_path)
                        if s3_metadata:
                            # vasts3 returns 'content_length' (lowercase, underscore), not 'ContentLength'
                            size = 0
                            if isinstance(s3_metadata, dict):
                                size = s3_metadata.get('content_length') or s3_metadata.get('ContentLength', 0) or 0
                            elif hasattr(s3_metadata, 'content_length'):
                                size = s3_metadata.content_length
                            elif hasattr(s3_metadata, 'ContentLength'):
                                size = s3_metadata.ContentLength
                            if size > 0:
                                # Update database with size (atomic with WHERE clause to handle race conditions)
                                objects_table = self.vast_db.get_qualified_table_name("objects")
                                update_sql = f"""
                                    UPDATE {objects_table} 
                                    SET size = {size} 
                                    WHERE id = '{object_id}' AND (size IS NULL OR size = 0)
                                """
                                self.vast_db.execute_sql(update_sql)
                                # Update object_data with the size we just retrieved
                                object_data['size'] = size
                                logger.debug("Updated missing size for object %s from S3: %d bytes", object_id, size)
                    except Exception as e:
                        # Handle 404 errors gracefully - object may have been deleted or doesn't exist yet
                        # This is expected in some scenarios (cleanup, test data, etc.)
                        error_msg = str(e).lower()
                        if '404' in error_msg or 'not found' in error_msg:
                            logger.debug("Object %s not found in S3 (expected in some scenarios): %s", object_id, storage_path)
                        else:
                            # Log other errors at debug level - object will be returned with NULL size
                            logger.debug("Failed to update size from S3 for object %s: %s", object_id, e)
            
            # At this point, object_data should have all required fields:
            # - id: checked on line 171
            # - referenced_by_flows: set on line 180 (defaults to [])
            # - timerange: set on lines 195-212 (defaults to TimeRange(value="0:0"))
            obj = Object(**object_data)  # type: ignore[arg-type]
            
            # Store metadata internally on the object instance for internal use only
            # (not exposed via API, stored as private attribute)
            if internal_metadata:
                setattr(obj, '_internal_metadata', internal_metadata)  # type: ignore[attr-defined]
            
            return obj
        except Exception as e:
            logger.error("Failed to get object %s: %s", object_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def create_object(self, obj: Object) -> bool:
        """Create a new object"""
        try:
            import json
            now = get_tams_timestamp()
            obj.created = now
            
            object_data = obj.model_dump()
            
            # Serialize metadata to JSON string
            if 'metadata' in object_data and object_data['metadata'] is not None:
                if isinstance(object_data['metadata'], dict):
                    object_data['metadata'] = json.dumps(object_data['metadata'])
                elif not isinstance(object_data['metadata'], str):
                    object_data['metadata'] = json.dumps(object_data['metadata'])
            
            # Convert timestamp fields to PyArrow format using centralized function
            from ..common.storage.timestamp_utils import prepare_data_for_pyarrow
            object_data = prepare_data_for_pyarrow(object_data)
            
            self.vast_db.insert_record("objects", object_data)
            return True
        except Exception as e:
            logger.error("Failed to create object: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_unreferenced_objects(self, exclude_object_ids: Optional[List[str]] = None) -> List[str]:
        """Get list of object IDs that are no longer referenced by any segments
        
        Per TAMS 8.0 spec: Objects that are no longer referenced by any Segments should be deleted.
        """
        try:
            segments_table = self.vast_db.get_qualified_table_name("segments")
            
            # Find all objects that have no segments referencing them
            # Get all object IDs from segments
            referenced_query = f"""
                SELECT DISTINCT object_id 
                FROM {segments_table} 
                WHERE object_id IS NOT NULL
            """
            ref_result = self.vast_db.execute_sql(referenced_query)
            
            referenced_object_ids = set()
            if isinstance(ref_result, dict) and 'data' in ref_result:
                data = ref_result['data']
                if isinstance(data, dict):
                    object_id_col = data.get('object_id', [])
                    if isinstance(object_id_col, list):
                        referenced_object_ids = {str(oid) for oid in object_id_col if oid}
                elif isinstance(data, list):
                    for row in data:
                        if isinstance(row, dict) and row.get('object_id'):
                            referenced_object_ids.add(str(row['object_id']))
                        elif isinstance(row, (list, tuple)) and len(row) > 0:
                            referenced_object_ids.add(str(row[0]))
            
            # Get all objects and filter out referenced ones
            all_objects_result = self.vast_db.query("objects").select("id").execute()
            all_object_ids = set()
            
            if isinstance(all_objects_result, dict) and 'data' in all_objects_result:
                data = all_objects_result['data']
                if isinstance(data, dict):
                    id_col = data.get('id', [])
                    if isinstance(id_col, list):
                        all_object_ids = {str(oid) for oid in id_col if oid}
                elif isinstance(data, list):
                    for row in data:
                        if isinstance(row, dict) and row.get('id'):
                            all_object_ids.add(str(row['id']))
                        elif isinstance(row, (list, tuple)) and len(row) > 0:
                            all_object_ids.add(str(row[0]))
            
            # Find unreferenced objects
            unreferenced = all_object_ids - referenced_object_ids
            
            # Exclude specified object IDs if provided
            if exclude_object_ids:
                unreferenced = unreferenced - set(exclude_object_ids)
            
            return list(unreferenced)
        except Exception as e:
            logger.error("Failed to get unreferenced objects: %s", e)
            return []
    
    async def delete_unreferenced_objects(self, object_ids: List[str]) -> int:
        """Delete objects and their S3 files if they are no longer referenced
        
        Returns number of objects deleted.
        Note: Uses delete_object which handles S3 deletion, so we don't need to manually delete instances here.
        """
        deleted_count = 0
        for object_id in object_ids:
            try:
                # Delete object (will handle instances and S3 deletion)
                await self.delete_object(object_id)
                deleted_count += 1
                logger.info("Deleted unreferenced object %s and S3 files", object_id)
            except Exception as e:
                logger.error("Failed to delete unreferenced object %s: %s", object_id, e)
                # Continue with other objects
        
        return deleted_count
    
    async def _delete_object_instances_s3(self, object_id: str) -> None:
        """Delete all instances and their S3 files for an object (helper for delete_object)"""
        instances = await self.list_object_instances(object_id)
        for instance in instances:
            if instance.controlled:
                storage_path = None
                storage_id = None
                # Try to get from instance metadata
                if instance.metadata and isinstance(instance.metadata, dict):
                    storage_path = instance.metadata.get('storage_path')
                    storage_id = instance.metadata.get('storage_id')
                
                # Fallback to URL parsing
                if not storage_path and instance.url:
                    storage_path = self._extract_storage_path_from_url(instance.url)
                
                if storage_path:
                    await self._delete_s3_object(storage_path, storage_id=storage_id)
        
        # Delete instances from database
        self.vast_db.query("object_instances").delete().where(f"object_id = '{object_id}'").execute()
    
    async def delete_object(self, object_id: str) -> bool:
        """Delete an object and all its instances and S3 files
        
        Per TAMS 8.0 spec: Objects are immutable and cannot be deleted if referenced by flows or segments.
        Raises ValueError if object has dependencies (will be caught by router and returned as 409 Conflict).
        """
        try:
            # Check if object exists and get its dependencies
            obj = await self.get_object(object_id)
            if not obj:
                # Idempotent delete: return True if object doesn't exist
                return True
            
            # TAMS 8.0: Objects are immutable - cannot be deleted if referenced by flows
            if obj.referenced_by_flows and len(obj.referenced_by_flows) > 0:
                raise ValueError(f"Cannot delete object {object_id}: {len(obj.referenced_by_flows)} flow references exist. Objects are immutable per TAMS spec.")
            
            # Check if object is referenced by any segments
            segments_table = self.vast_db.get_qualified_table_name("segments")
            check_segments_query = f"""
                SELECT COUNT(*) as count
                FROM {segments_table}
                WHERE object_id = '{object_id}'
            """
            segments_result = self.vast_db.execute_sql(check_segments_query)
            
            segment_count = 0
            if isinstance(segments_result, dict) and 'data' in segments_result:
                data = segments_result['data']
                if isinstance(data, dict) and 'count' in data:
                    count_values = data['count']
                    if isinstance(count_values, list) and len(count_values) > 0:
                        segment_count = count_values[0] or 0
                    elif isinstance(count_values, (int, float)):
                        segment_count = int(count_values)
                elif isinstance(data, list) and len(data) > 0:
                    first_row = data[0]
                    if isinstance(first_row, dict):
                        segment_count = first_row.get('count', 0) or 0
            
            if segment_count > 0:
                raise ValueError(f"Cannot delete object {object_id}: {segment_count} segment references exist. Objects are immutable per TAMS spec.")
            
            # Object has no dependencies - safe to delete
            # Delete all instances and S3 files first
            await self._delete_object_instances_s3(object_id)
            
            # Get object metadata to try to delete main storage path
            if obj and hasattr(obj, '_internal_metadata'):
                internal_metadata = getattr(obj, '_internal_metadata', None)  # type: ignore[attr-defined]
                if internal_metadata:
                    storage_path = internal_metadata.get('storage_path') if isinstance(internal_metadata, dict) else None
                    storage_id = internal_metadata.get('storage_id') if isinstance(internal_metadata, dict) else None
                if storage_path:
                    await self._delete_s3_object(storage_path, storage_id=storage_id)
            
            # Delete object from database
            self.vast_db.query("objects").delete().where(f"id = '{object_id}'").execute()
            return True
        except ValueError:
            # Re-raise ValueError (dependency violations) to be caught by router as 409 Conflict
            raise
        except Exception as e:
            logger.error("Failed to delete object %s: %s", object_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_objects(self) -> List[Object]:
        """Get all objects with referenced flows computed via JOIN query"""
        try:
            segments_table = self.vast_db.get_qualified_table_name("segments")
            objects_table = self.vast_db.get_qualified_table_name("objects")
            
            # Use JOIN query to get objects with their referenced flows in a single query
            # This is much more efficient than N+1 queries or even batch queries
            join_query = f"""
                SELECT 
                    o.id,
                    o.size,
                    o.timerange,
                    o.created,
                    s.flow_id,
                    s.created as segment_created
                FROM {objects_table} o
                LEFT JOIN {segments_table} s ON o.id = s.object_id AND s.flow_id IS NOT NULL
                ORDER BY o.id, s.created ASC
                LIMIT 10000
            """
            
            join_result = self.vast_db.execute_sql(join_query)
            
            # Process JOIN results: group by object_id and collect flow_ids
            objects_map = {}  # object_id -> object_data dict
            referenced_flows_map = {}  # object_id -> list of flow_ids
            first_ref_map = {}  # object_id -> (flow_id, first_created)
            
            if isinstance(join_result, dict) and 'data' in join_result:
                data = join_result['data']
                if isinstance(data, dict):
                    id_col = data.get('id', [])
                    size_col = data.get('size', [])
                    timerange_col = data.get('timerange', [])
                    created_col = data.get('created', [])
                    flow_id_col = data.get('flow_id', [])
                    segment_created_col = data.get('segment_created', [])
                    
                    if isinstance(id_col, list):
                        num_rows = len(id_col)
                        for i in range(num_rows):
                            object_id = id_col[i] if i < len(id_col) else None
                            if not object_id:
                                continue
                            
                            # Store object data (only once per object)
                            if object_id not in objects_map:
                                objects_map[object_id] = {
                                    'id': object_id,
                                    'size': size_col[i] if i < len(size_col) else None,
                                    'timerange': timerange_col[i] if i < len(timerange_col) else None,
                                    'created': created_col[i] if i < len(created_col) else None
                                }
                            
                            # Collect referenced flows
                            flow_id = flow_id_col[i] if i < len(flow_id_col) else None
                            segment_created = segment_created_col[i] if i < len(segment_created_col) else None
                            
                            if flow_id:
                                if object_id not in referenced_flows_map:
                                    referenced_flows_map[object_id] = []
                                if str(flow_id) not in referenced_flows_map[object_id]:
                                    referenced_flows_map[object_id].append(str(flow_id))
                                
                                # Track first referenced flow (earliest segment_created)
                                if object_id not in first_ref_map:
                                    first_ref_map[object_id] = (str(flow_id), segment_created)
                                else:
                                    _, existing_created = first_ref_map[object_id]
                                    if segment_created and (existing_created is None or segment_created < existing_created):
                                        first_ref_map[object_id] = (str(flow_id), segment_created)
            
            # Convert objects_map to list and add referenced_by_flows
            objects_data = list(objects_map.values())
            
            # Process each object: add referenced_by_flows and handle timerange
            objects = []
            import json
            from ..common.models import TimeRange
            
            for object_data in objects_data:
                object_id = object_data.get('id')
                if not object_id:
                    continue
                
                try:
                    # Remove referenced_by_flows from object_data if present (no longer stored in schema, computed dynamically)
                    if 'referenced_by_flows' in object_data:
                        del object_data['referenced_by_flows']
                    
                    # Use pre-computed referenced_by_flows from JOIN query
                    try:
                        referenced_flows = referenced_flows_map.get(object_id, [])
                        # Set referenced_by_flows (TAMS spec requirement) - always set, even if empty
                        object_data['referenced_by_flows'] = referenced_flows if referenced_flows else []
                        
                        # Use pre-computed first_referenced_by_flow
                        if object_id in first_ref_map:
                            flow_id, _ = first_ref_map[object_id]
                            object_data['first_referenced_by_flow'] = str(flow_id)
                    except Exception as e:
                        logger.error("Failed to set referenced_by_flows for object %s: %s", object_id, e)
                        # Set empty list on error - object will be returned but with no references
                        object_data['referenced_by_flows'] = []
                    
                    # Ensure referenced_by_flows is always set
                    if 'referenced_by_flows' not in object_data:
                        object_data['referenced_by_flows'] = []
                    
                    # Handle timerange - can be None or a string in database, but model requires TimeRange (TAMS spec requirement)
                    if 'timerange' in object_data:
                        timerange_value = object_data.get('timerange')
                        if timerange_value is None or timerange_value == '':
                            # Provide a default timerange if missing (required by model)
                            object_data['timerange'] = TimeRange(value="0:0")
                        elif isinstance(timerange_value, str):
                            # Parse string timerange
                            object_data['timerange'] = TimeRange(value=timerange_value)
                        elif not isinstance(timerange_value, TimeRange):
                            # Try to convert dict to TimeRange
                            if isinstance(timerange_value, dict):
                                object_data['timerange'] = TimeRange(**timerange_value)
                            else:
                                # Fallback to default
                                object_data['timerange'] = TimeRange(value="0:0")
                    else:
                        # No timerange field - provide default
                        object_data['timerange'] = TimeRange(value="0:0")
                    
                    # Ensure timerange is always set - double check it's a TimeRange instance
                    timerange_val = object_data.get('timerange')
                    if timerange_val is None or not isinstance(timerange_val, TimeRange):
                        object_data['timerange'] = TimeRange(value="0:0")
                    
                    # Ensure referenced_by_flows is always a list
                    if 'referenced_by_flows' not in object_data or not isinstance(object_data.get('referenced_by_flows'), list):
                        object_data['referenced_by_flows'] = []
                    
                    # Debug: log object_data before creation to catch any issues
                    logger.debug("Creating Object with data: id=%s, referenced_by_flows=%s, timerange=%s", 
                                object_id, type(object_data.get('referenced_by_flows')), type(object_data.get('timerange')))
                    
                    # Create Object instance
                    obj = Object(**object_data)
                    objects.append(obj)
                except Exception as e:
                    logger.error("Failed to process object %s: %s", object_id, e, exc_info=True)
                    # Skip invalid objects rather than failing entire request
                    continue
            
            return objects
        except Exception as e:
            logger.error("Failed to get objects: %s", e, exc_info=True)
            # If we have partial results, return them instead of failing completely
            if 'objects' in locals() and len(objects) > 0:
                logger.warning("Returning partial object list due to error: %s", e)
                return objects
            raise HTTPException(status_code=500, detail="Internal server error")
    
    # Object Instance Management (TAMS 8.0)
    
    async def create_object_instance(self, object_id: str, instance: ObjectInstance) -> bool:
        """Create a new instance for an object (TAMS 8.0)"""
        try:
            # Verify object exists
            obj = await self.get_object(object_id)
            if not obj:
                return False
            
            # Prepare instance data
            instance_data = instance.model_dump()
            instance_data['object_id'] = object_id
            instance_data['created'] = get_tams_timestamp()
            
            # Convert timestamp fields for PyArrow
            from ..common.storage.timestamp_utils import prepare_data_for_pyarrow
            instance_data = prepare_data_for_pyarrow(instance_data)
            
            # Insert instance record
            self.vast_db.insert_record("object_instances", instance_data)
            
            logger.debug("Created object instance %s for object %s", instance.label, object_id)
            return True
        except Exception as e:
            logger.error("Failed to create object instance for %s: %s", object_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def list_object_instances(self, object_id: str) -> List[ObjectInstance]:
        """List all instances for an object (TAMS 8.0)"""
        try:
            # Verify object exists
            obj = await self.get_object(object_id)
            if not obj:
                return []
            
            # Query instances for this object
            result = self.vast_db.query("object_instances").select("*").where(f"object_id = '{object_id}'").execute()
            
            instances = []
            # Handle VAST query result format (columnar or row-oriented)
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data:
                    # Columnar format - convert to row dictionaries
                    num_rows = len(next(iter(data.values())))
                    for i in range(num_rows):
                        instance_data = {}
                        for column, values in data.items():
                            if column != '$row_id':  # Skip internal row IDs
                                value = values[i] if i < len(values) else None
                                instance_data[column] = value
                        # Create ObjectInstance without object_id field (not part of model)
                        instance_dict = {k: v for k, v in instance_data.items() if k in ['label', 'storage_id', 'url', 'controlled', 'metadata']}
                        instances.append(ObjectInstance(**instance_dict))
                elif isinstance(data, list):
                    # Row-oriented format
                    for row in data:
                        if isinstance(row, str):
                            continue
                        instance_data = dict(row) if hasattr(row, '__iter__') and not isinstance(row, str) else {}
                        # Create ObjectInstance without object_id field (not part of model)
                        if isinstance(instance_data, dict):
                            instance_dict = {k: v for k, v in instance_data.items() if k in ['label', 'storage_id', 'url', 'controlled', 'metadata']}
                            instances.append(ObjectInstance(**instance_dict))
            elif isinstance(result, list):
                # Direct list result
                for row in result:
                    if isinstance(row, str):
                        continue
                    instance_data = dict(row) if hasattr(row, '__iter__') and not isinstance(row, str) else {}
                    # Create ObjectInstance without object_id field (not part of model)
                    if isinstance(instance_data, dict):
                        instance_dict = {k: v for k, v in instance_data.items() if k in ['label', 'storage_id', 'url', 'controlled', 'metadata']}
                    instances.append(ObjectInstance(**instance_dict))
            
            return instances
        except Exception as e:
            logger.error("Failed to list object instances for %s: %s", object_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    def _extract_storage_path_from_url(self, url: str) -> Optional[str]:
        """Extract storage path from S3 URL"""
        try:
            # Parse URL to extract key/path
            parsed = urllib.parse.urlparse(url)
            path = parsed.path
            
            # Remove leading slash
            if path.startswith('/'):
                path = path[1:]
            
            # Remove query parameters and fragment
            return path if path else None
        except Exception as e:
            logger.debug("Failed to extract storage path from URL %s: %s", url, e)
            return None
    
    def _get_storage_path_from_instance(self, instance_data: Dict[str, Any]) -> Optional[str]:
        """Get storage path from object instance metadata or URL"""
        # First try metadata
        if instance_data.get('metadata'):
            metadata = instance_data['metadata']
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except (json.JSONDecodeError, TypeError):
                    metadata = None
            
            if isinstance(metadata, dict):
                storage_path = metadata.get('storage_path')
                if storage_path:
                    return storage_path
        
        # Fallback to extracting from URL
        url = instance_data.get('url')
        if url:
            return self._extract_storage_path_from_url(url)
        
        return None
    
    async def _delete_s3_object(self, storage_path: str, storage_id: Optional[str] = None) -> bool:
        """Delete an object from S3 storage
        
        Args:
            storage_path: Full storage path (may include root_path)
            storage_id: Optional storage backend ID to use backend-specific client
        """
        try:
            s3_client = None
            relative_storage_path = storage_path
            
            # If storage_id is provided, create backend-specific client
            if storage_id:
                try:
                    from ..storagebackends.service import StorageBackendService
                    from vasts3 import S3Client, S3Config
                    from ..core.config import get_settings
                    
                    backend_service = StorageBackendService(self.vast_db, None)
                    backend = await backend_service.get_storage_backend(storage_id)
                    
                    if backend:
                        settings = get_settings()
                        backend_root_path = backend.root_path
                        
                        # If storage_path includes root_path, strip it for use with key_prefix
                        if backend_root_path:
                            backend_root_path = backend_root_path.strip('/')
                            if storage_path.startswith(backend_root_path + '/'):
                                relative_storage_path = storage_path[len(backend_root_path) + 1:]
                            elif storage_path == backend_root_path:
                                relative_storage_path = ""
                        
                        # Create backend-specific S3Client
                        key_prefix = backend_root_path.strip('/') if backend_root_path else ""
                        cfg = S3Config(
                            endpoint_url=backend.endpoint_url or settings.s3_endpoint_url,
                            bucket_name=backend.bucket_name or settings.s3_bucket_name,
                            access_key=backend.access_key or settings.s3_access_key_id,
                            secret_key=backend.secret_key or settings.s3_secret_access_key,
                            region=backend.region or settings.s3_region,
                            use_ssl=backend.use_ssl if backend.use_ssl is not None else settings.s3_use_ssl,
                            chunk_size=settings.vaststore_s3_chunk_size,
                            max_concurrent_parts=settings.vaststore_s3_max_concurrent_parts,
                            key_prefix=key_prefix,
                        )
                        s3_client = S3Client(cfg)
                except Exception as e:
                    logger.warning("Failed to create backend-specific client for S3 deletion: %s, falling back to default", e)
            
            # Fallback to default client if backend-specific client wasn't created
            if not s3_client:
                if not self.s3_client:
                    logger.warning("S3 client not available, cannot delete object from S3")
                    return False
                s3_client = self.s3_client
                # For default client, if storage_path includes a root_path that matches settings, strip it
                # Otherwise use as-is
                from ..core.config import get_settings
                settings = get_settings()
                if hasattr(settings, 's3_root_path') and settings.s3_root_path:
                    root_path = settings.s3_root_path.strip('/')
                    if storage_path.startswith(root_path + '/'):
                        relative_storage_path = storage_path[len(root_path) + 1:]
                    elif storage_path == root_path:
                        relative_storage_path = ""
            
            # Use S3Client delete method if available
            # Check if s3_client has delete_object method
            if hasattr(s3_client, 'delete_object'):
                s3_client.delete_object(key=relative_storage_path)
                logger.info("Deleted S3 object: %s", storage_path)
                return True
            elif hasattr(s3_client, 'delete'):
                s3_client.delete(key=relative_storage_path)  # type: ignore[attr-defined]
                logger.info("Deleted S3 object: %s", storage_path)
                return True
            else:
                # Fallback: try using boto3 directly if available
                try:
                    import boto3
                    from ..core.config import get_settings
                    settings = get_settings()
                    
                    # Determine endpoint and credentials
                    endpoint_url = settings.s3_endpoint_url
                    bucket_name = settings.s3_bucket_name
                    access_key = settings.s3_access_key_id
                    secret_key = settings.s3_secret_access_key
                    
                    if storage_id:
                        try:
                            from ..storagebackends.service import StorageBackendService
                            backend_service = StorageBackendService(self.vast_db, None)
                            backend = await backend_service.get_storage_backend(storage_id)
                            if backend:
                                endpoint_url = backend.endpoint_url or endpoint_url
                                bucket_name = backend.bucket_name or bucket_name
                                access_key = backend.access_key or access_key
                                secret_key = backend.secret_key or secret_key
                        except Exception as e:
                            logger.warning("Failed to get backend config for boto3 fallback: %s", e)
                    
                    s3_resource = boto3.resource(
                        's3',
                        endpoint_url=endpoint_url,
                        aws_access_key_id=access_key,
                        aws_secret_access_key=secret_key,
                        region_name=settings.s3_region,
                        use_ssl=settings.s3_use_ssl
                    )
                    
                    bucket = s3_resource.Bucket(bucket_name)  # type: ignore[attr-defined]
                    # Use relative_storage_path (root_path already stripped if needed)
                    bucket.Object(relative_storage_path).delete()  # type: ignore[attr-defined]
                    logger.info("Deleted S3 object via boto3: %s", relative_storage_path)
                    return True
                except ImportError:
                    logger.error("boto3 not available, cannot delete S3 object")
                    return False
                except Exception as e:
                    logger.error("Failed to delete S3 object %s via boto3: %s", storage_path, e)
                    return False
        except Exception as e:
            logger.error("Failed to delete S3 object %s: %s", storage_path, e)
            return False
    
    async def delete_object_instance(self, object_id: str, label: Optional[str] = None, storage_id: Optional[str] = None) -> bool:
        """Delete an object instance by label or storage_id (TAMS 8.0)
        
        Per TAMS 8.0 spec: If instance is controlled, delete from storage before removing from database.
        """
        try:
            # Verify object exists
            obj = await self.get_object(object_id)
            if not obj:
                return False
            
            # Get instance data before deletion to check if controlled and get storage path
            instance_result = None
            if label:
                instance_result = self.vast_db.query("object_instances").select("*").where(
                    f"object_id = '{object_id}' AND label = '{label}'"
                ).execute()
            elif storage_id:
                instance_result = self.vast_db.query("object_instances").select("*").where(
                    f"object_id = '{object_id}' AND storage_id = '{storage_id}'"
                ).execute()
            else:
                return False
            
            # Extract instance data
            instance_data = None
            if isinstance(instance_result, dict) and 'data' in instance_result:
                data = instance_result['data']
                if isinstance(data, dict) and data:
                    # Columnar format
                    num_rows = len(next(iter(data.values())))
                    if num_rows == 0:
                        # Instance not found - idempotent delete, return True
                        logger.debug("Instance not found for object %s (label=%s, storage_id=%s) - idempotent delete", 
                                   object_id, label, storage_id)
                        return True
                    instance_data = {col: values[0] for col, values in data.items() if col != '$row_id'}
                elif isinstance(data, list) and len(data) > 0:
                    instance_data = dict(data[0]) if isinstance(data[0], dict) else None
                else:
                    # Empty result - idempotent delete
                    logger.debug("Instance not found for object %s (label=%s, storage_id=%s) - idempotent delete", 
                               object_id, label, storage_id)
                    return True
            elif isinstance(instance_result, list) and len(instance_result) > 0:
                instance_data = dict(instance_result[0]) if isinstance(instance_result[0], dict) else None
            else:
                # No result - idempotent delete
                logger.debug("Instance not found for object %s (label=%s, storage_id=%s) - idempotent delete", 
                           object_id, label, storage_id)
                return True
            
            if not instance_data:
                # Instance not found - idempotent delete, return True
                logger.debug("Instance data empty for object %s (label=%s, storage_id=%s) - idempotent delete", 
                           object_id, label, storage_id)
                return True
            
            # Check if controlled and delete from S3 if needed (TAMS 8.0 spec)
            controlled = instance_data.get('controlled', False)
            if controlled:
                storage_path = self._get_storage_path_from_instance(instance_data)
                if storage_path:
                    # Use storage_id from parameter, or try to get from instance_data
                    instance_storage_id = storage_id
                    if not instance_storage_id and instance_data.get('metadata'):
                        metadata = instance_data.get('metadata')
                        if isinstance(metadata, str):
                            try:
                                metadata = json.loads(metadata)
                            except (json.JSONDecodeError, TypeError):
                                metadata = None
                        if isinstance(metadata, dict):
                            instance_storage_id = metadata.get('storage_id')
                    await self._delete_s3_object(storage_path, storage_id=instance_storage_id)
                else:
                    logger.warning("Could not determine storage path for controlled instance %s (object_id=%s, label=%s, storage_id=%s)", 
                                 instance_data.get('label', 'unknown'), object_id, label, storage_id)
            
            # Delete from database
            try:
                if label:
                    query = self.vast_db.query("object_instances").delete().where(f"object_id = '{object_id}' AND label = '{label}'")
                else:
                    query = self.vast_db.query("object_instances").delete().where(f"object_id = '{object_id}' AND storage_id = '{storage_id}'")
                
                query.execute()
                
                logger.debug("Deleted object instance for object %s (label=%s, storage_id=%s, controlled=%s)", 
                           object_id, label, storage_id, controlled)
                return True
            except Exception as delete_error:
                # If delete fails (e.g., instance already deleted), log but still return True (idempotent)
                logger.debug("Delete query returned no rows for object %s (label=%s, storage_id=%s) - idempotent delete: %s", 
                           object_id, label, storage_id, delete_error)
                return True
        except Exception as e:
            logger.error("Failed to delete object instance for %s: %s", object_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_object_summary(self, object_id: str) -> Optional[str]:
        """
        Get summary for an object (VAST extension, not part of TAMS spec).
        
        Args:
            object_id: Object ID
            
        Returns:
            Summary string or None if not set or column doesn't exist
        """
        try:
            objects_table = self.vast_db.get_qualified_table_name("objects")
            query = f"SELECT summary FROM {objects_table} WHERE id = '{object_id}'"
            result = self.vast_db.execute_sql(query)
            
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and 'summary' in data:
                    summary_list = data['summary']
                    if summary_list and len(summary_list) > 0:
                        return summary_list[0]
            return None
        except Exception as e:
            # Column might not exist in table - this is OK, just return None
            if 'COLUMN_NOT_FOUND' in str(e) or 'cannot be resolved' in str(e):
                logger.debug(f"Summary column does not exist for object {object_id} (this is OK)")
                return None
            logger.error(f"Failed to get summary for object {object_id}: {e}")
            return None
    
    async def update_object_summary(self, object_id: str, summary: Optional[str]) -> bool:
        """
        Update summary for an object (VAST extension, not part of TAMS spec).
        
        Args:
            object_id: Object ID
            summary: Summary text (None to clear)
            
        Returns:
            True if successful
        """
        try:
            # Verify object exists
            obj = await self.get_object(object_id)
            if not obj:
                raise HTTPException(status_code=404, detail="Object not found")
            
            # Use query builder for safer updates
            try:
                # Try UPDATE first using query builder
                query_builder = self.vast_db.query("objects")
                if summary is None:
                    # Clear summary - set to None
                    update_data = {'summary': [None]}
                else:
                    # Set summary
                    update_data = {'summary': [summary]}
                
                # Use update method if available, otherwise use delete+insert approach
                try:
                    query_builder.update(update_data).where(f"id = '{object_id}'").execute()
                    logger.debug(f"Updated summary for object {object_id} using query builder")
                except (AttributeError, Exception) as update_error:
                    # Fallback to delete+insert approach
                    logger.debug(f"Query builder update failed, using delete+insert: {update_error}")
                    
                    # Get existing object data
                    existing_data = await self.get_object(object_id)
                    if not existing_data:
                        raise HTTPException(status_code=404, detail="Object not found")
                    
                    # Get raw data from database (excluding summary - it may not exist in table)
                    objects_table = self.vast_db.get_qualified_table_name("objects")
                    # Explicitly list columns to avoid issues if summary column doesn't exist
                    select_query = f"SELECT id, size, timerange, created, first_referenced_by_flow, metadata FROM {objects_table} WHERE id = '{object_id}'"
                    result = self.vast_db.execute_sql(select_query)
                    
                    if isinstance(result, dict) and 'data' in result:
                        data = result['data']
                        if not data or not any(data.values()):
                            raise HTTPException(status_code=404, detail="Object not found")
                        
                        # Reconstruct object data with updated summary
                        from ..common.storage.timestamp_utils import prepare_data_for_pyarrow
                        updated_data = {}
                        for key in ['id', 'size', 'timerange', 'created', 'first_referenced_by_flow', 'metadata']:
                            if key in data and data[key]:
                                updated_data[key] = data[key][0]
                        
                        # Set summary (will be added to schema if it doesn't exist)
                        updated_data['summary'] = summary
                        
                        # Delete existing record
                        self.vast_db.query("objects").delete().where(f"id = '{object_id}'").execute()
                        
                        # Insert updated record
                        pyarrow_data = prepare_data_for_pyarrow(updated_data)
                        self.vast_db.insert_record("objects", pyarrow_data)
                        logger.debug(f"Updated summary for object {object_id} using delete+insert")
                
                return True
                
            except Exception as query_error:
                logger.error(f"Query builder approach failed: {query_error}")
                # Fallback to direct SQL (with proper escaping)
                # Note: If summary column doesn't exist, this will fail - that's expected
                # The column should be added via schema migration if summary feature is needed
                objects_table = self.vast_db.get_qualified_table_name("objects")
                try:
                    if summary is None:
                        update_query = f"UPDATE {objects_table} SET summary = NULL WHERE id = '{object_id}'"
                    else:
                        # Escape single quotes for SQL
                        summary_escaped = summary.replace("'", "''")
                        update_query = f"UPDATE {objects_table} SET summary = '{summary_escaped}' WHERE id = '{object_id}'"
                    
                    self.vast_db.execute_sql(update_query)
                    logger.debug(f"Updated summary for object {object_id} using direct SQL")
                    return True
                except Exception as sql_error:
                    if 'COLUMN_NOT_FOUND' in str(sql_error) or 'cannot be resolved' in str(sql_error):
                        logger.warning(f"Summary column does not exist in objects table. Cannot update summary for {object_id}. Add summary column via schema migration if needed.")
                        raise HTTPException(
                            status_code=400, 
                            detail="Summary column does not exist in objects table. This feature requires schema migration."
                        )
                    raise
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update summary for object {object_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to update object summary: {str(e)}")
            logger.error("Failed to delete object instance for %s: %s", object_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
