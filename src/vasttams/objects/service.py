"""
Object Storage Service

This module handles all media object-related storage operations including
CRUD operations and object management.
"""

import logging
from typing import Optional, List
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
        """Get a specific object by ID"""
        try:
            result = self.vast_db.query("objects").select("*").where(f"id = '{object_id}'").execute()
            
            # Handle VAST query result format (columnar or row-oriented)
            object_data = None
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data:
                    # Columnar format - convert to row dictionary
                    # Get first row (index 0) since we're querying by ID
                    num_rows = len(next(iter(data.values())))
                    if num_rows == 0:
                        return None
                    
                    object_data = {}
                    for column, values in data.items():
                        if column != '$row_id':  # Skip internal row IDs
                            value = values[0] if len(values) > 0 else None
                            object_data[column] = value
                elif isinstance(data, list) and len(data) > 0:
                    # Row-oriented format
                    first_row = data[0]
                    if isinstance(first_row, dict):
                        object_data = first_row
                    else:
                        logger.warning("Unexpected row format in objects query result")
                        return None
            elif isinstance(result, list) and len(result) > 0:
                # Direct list result
                first_row = result[0]
                if isinstance(first_row, dict):
                    object_data = first_row
                else:
                    logger.warning("Unexpected row format in objects query result")
                    return None
            
            if not object_data:
                return None
            
            # Remove referenced_by_flows from object_data if present (no longer stored in schema, computed dynamically)
            if 'referenced_by_flows' in object_data:
                del object_data['referenced_by_flows']
            
            # Compute referenced_by_flows dynamically from segments/flow_object_references (normalized table)
            # Instead of storing as JSON, we compute it using a JOIN - cleaner and more maintainable
            try:
                segments_table = self.vast_db.get_qualified_table_name("segments")
                # Query distinct flow_ids that reference this object via segments
                ref_query = f"""
                    SELECT DISTINCT flow_id 
                    FROM {segments_table} 
                    WHERE object_id = '{object_id}' AND flow_id IS NOT NULL
                """
                ref_result = self.vast_db.execute_sql(ref_query)
                referenced_flows = []
                
                if isinstance(ref_result, dict) and 'data' in ref_result:
                    data = ref_result['data']
                    if isinstance(data, dict):
                        # Columnar format
                        flow_id_col = data.get('flow_id', [])
                        if isinstance(flow_id_col, list):
                            referenced_flows = [str(fid) for fid in flow_id_col if fid]
                    elif isinstance(data, list):
                        # Row-oriented format
                        for row in data:
                            if isinstance(row, dict) and row.get('flow_id'):
                                referenced_flows.append(str(row['flow_id']))
                            elif isinstance(row, (list, tuple)) and len(row) > 0:
                                referenced_flows.append(str(row[0]))
                
                # Also check flow_object_references table as fallback
                if not referenced_flows:
                    ref_table = self.vast_db.get_qualified_table_name("flow_object_references")
                    ref_query2 = f"""
                        SELECT DISTINCT flow_id 
                        FROM {ref_table} 
                        WHERE object_id = '{object_id}' AND flow_id IS NOT NULL
                    """
                    ref_result2 = self.vast_db.execute_sql(ref_query2)
                    if isinstance(ref_result2, dict) and 'data' in ref_result2:
                        data = ref_result2['data']
                        if isinstance(data, dict):
                            flow_id_col = data.get('flow_id', [])
                            if isinstance(flow_id_col, list):
                                referenced_flows = [str(fid) for fid in flow_id_col if fid]
                
                # Set referenced_by_flows (TAMS spec requirement)
                object_data['referenced_by_flows'] = referenced_flows if referenced_flows else []
                
                # Compute first_referenced_by_flow as the flow with earliest segment creation
                if referenced_flows:
                    first_ref_query = f"""
                        SELECT flow_id, MIN(created) as first_created
                        FROM {segments_table}
                        WHERE object_id = '{object_id}' AND flow_id IS NOT NULL
                        GROUP BY flow_id
                        ORDER BY first_created ASC
                        LIMIT 1
                    """
                    first_ref_result = self.vast_db.execute_sql(first_ref_query)
                    if isinstance(first_ref_result, dict) and 'data' in first_ref_result:
                        data = first_ref_result['data']
                        if isinstance(data, dict):
                            flow_id_col = data.get('flow_id', [])
                            if isinstance(flow_id_col, list) and len(flow_id_col) > 0:
                                object_data['first_referenced_by_flow'] = str(flow_id_col[0])
            except Exception as e:
                logger.error("Failed to compute referenced_by_flows for object %s: %s", object_id, e)
                # Set empty list on error - object will be returned but with no references
                object_data['referenced_by_flows'] = []
            
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
                        # Log but don't fail - object will be returned with NULL size
                        logger.debug("Failed to update size from S3 for object %s: %s", object_id, e)
            
            obj = Object(**object_data)
            
            # Store metadata internally on the object instance for internal use only
            # (not exposed via API, stored as private attribute)
            if internal_metadata:
                obj._internal_metadata = internal_metadata
            
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
    
    async def delete_object(self, object_id: str) -> bool:
        """Delete an object"""
        try:
            self.vast_db.query("objects").delete().where(f"id = '{object_id}'").execute()
            return True
        except Exception as e:
            logger.error("Failed to delete object %s: %s", object_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_objects(self) -> List[Object]:
        """Get all objects"""
        try:
            result = self.vast_db.query("objects").select("*").execute()
            
            # Handle VAST query result format (same as get_object)
            objects = []
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data:
                    # Convert column arrays to row dictionaries
                    num_rows = len(next(iter(data.values())))
                    for i in range(num_rows):
                        object_data = {}
                        for column, values in data.items():
                            if column != '$row_id':  # Skip internal row IDs
                                value = values[i] if i < len(values) else None
                                object_data[column] = value
                        if object_data:
                            # Strip metadata before creating Object (internal-only)
                            if 'metadata' in object_data:
                                del object_data['metadata']
                            objects.append(Object(**object_data))
                elif isinstance(data, list):
                    # If data is a list, iterate directly
                    for row in data:
                        object_data = dict(row) if hasattr(row, '__iter__') and not isinstance(row, str) else row
                        if object_data:
                            # Strip metadata before creating Object (internal-only)
                            if 'metadata' in object_data:
                                del object_data['metadata']
                            objects.append(Object(**object_data))
            else:
                # Fallback for direct list results
                for row in result if isinstance(result, list) else []:
                    object_data = dict(row) if hasattr(row, '__iter__') and not isinstance(row, str) else row
                    if object_data:
                        objects.append(Object(**object_data))
            
            return objects
        except Exception as e:
            logger.error("Failed to get objects: %s", e)
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
            
            logger.info("Created object instance %s for object %s", instance.label, object_id)
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
            rows = result.get('data', []) if isinstance(result, dict) else result
            
            for row in rows:
                instance_data = dict(row)
                # Create ObjectInstance without object_id field (not part of model)
                instance_dict = {k: v for k, v in instance_data.items() if k in ['label', 'storage_id', 'url', 'controlled', 'metadata']}
                instances.append(ObjectInstance(**instance_dict))
            
            return instances
        except Exception as e:
            logger.error("Failed to list object instances for %s: %s", object_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_object_instance(self, object_id: str, label: Optional[str] = None, storage_id: Optional[str] = None) -> bool:
        """Delete an object instance by label or storage_id (TAMS 8.0)"""
        try:
            # Verify object exists
            obj = await self.get_object(object_id)
            if not obj:
                return False
            
            # Build where clause
            if label:
                query = self.vast_db.query("object_instances").delete().where(f"object_id = '{object_id}' AND label = '{label}'")
            elif storage_id:
                query = self.vast_db.query("object_instances").delete().where(f"object_id = '{object_id}' AND storage_id = '{storage_id}'")
            else:
                return False
            
            query.execute()
            
            logger.info("Deleted object instance for object %s (label=%s, storage_id=%s)", object_id, label, storage_id)
            return True
        except Exception as e:
            logger.error("Failed to delete object instance for %s: %s", object_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
