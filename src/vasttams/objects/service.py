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
        """Delete an object and all its instances and S3 files"""
        try:
            # Delete all instances and S3 files first
            await self._delete_object_instances_s3(object_id)
            
            # Get object metadata to try to delete main storage path
            obj = await self.get_object(object_id)
            if obj and hasattr(obj, '_internal_metadata') and obj._internal_metadata:
                storage_path = obj._internal_metadata.get('storage_path')
                storage_id = obj._internal_metadata.get('storage_id')
                if storage_path:
                    await self._delete_s3_object(storage_path, storage_id=storage_id)
            
            # Delete object from database
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
                        key_prefix = backend_root_path.strip('/') if backend_root_path else None
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
                s3_client.delete(key=relative_storage_path)
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
                    
                    bucket = s3_resource.Bucket(bucket_name)
                    # Use relative_storage_path (root_path already stripped if needed)
                    bucket.Object(relative_storage_path).delete()
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
                        return False
                    instance_data = {col: values[0] for col, values in data.items() if col != '$row_id'}
                elif isinstance(data, list) and len(data) > 0:
                    instance_data = dict(data[0]) if isinstance(data[0], dict) else None
            elif isinstance(instance_result, list) and len(instance_result) > 0:
                instance_data = dict(instance_result[0]) if isinstance(instance_result[0], dict) else None
            
            if not instance_data:
                return False
            
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
            if label:
                query = self.vast_db.query("object_instances").delete().where(f"object_id = '{object_id}' AND label = '{label}'")
            else:
                query = self.vast_db.query("object_instances").delete().where(f"object_id = '{object_id}' AND storage_id = '{storage_id}'")
            
            query.execute()
            
            logger.info("Deleted object instance for object %s (label=%s, storage_id=%s, controlled=%s)", 
                       object_id, label, storage_id, controlled)
            return True
        except Exception as e:
            logger.error("Failed to delete object instance for %s: %s", object_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
