"""
Segment Storage Service

This module handles all flow segment-related storage operations including
CRUD operations, filtering, and segment management.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import HTTPException
from ..common.storage.interfaces import StorageInterface
from ..common.storage.timestamp_utils import (
    get_tams_timestamp,
    prepare_data_for_pyarrow
)
from .models import FlowSegment
from ..service.storage_models import FlowStorage, FlowStoragePost, MediaObject
from ..common.models import HttpRequest

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
                            from ..common.models import TimeRange
                            segment_data['timerange'] = TimeRange(value=f"{timerange_start}_{timerange_end}")
                        elif timerange_start:
                            from ..common.models import TimeRange
                            segment_data['timerange'] = TimeRange(value=str(timerange_start))
                        else:
                            # Provide a default timerange if both are missing
                            from ..common.models import TimeRange
                            segment_data['timerange'] = TimeRange(value="0:0")
                        
                        # Parse JSON fields
                        for field in ['ts_offset', 'last_duration', 'get_urls']:
                            if field in segment_data and isinstance(segment_data[field], str):
                                try:
                                    import json
                                    parsed = json.loads(segment_data[field])
                                    if field == 'get_urls' and isinstance(parsed, list):
                                        # Convert list of dicts to GetUrl objects
                                        from .models import GetUrl
                                        segment_data[field] = [GetUrl(**url) if isinstance(url, dict) else url for url in parsed]
                                    else:
                                        segment_data[field] = parsed
                                except (json.JSONDecodeError, TypeError) as e:
                                    logger.debug(f"Failed to parse {field}: {e}")
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
                            from ..common.models import TimeRange
                            segment_data['timerange'] = TimeRange(value=f"{timerange_start}_{timerange_end}")
                        elif timerange_start:
                            from ..common.models import TimeRange
                            segment_data['timerange'] = TimeRange(value=str(timerange_start))
                        else:
                            # Provide a default timerange if both are missing
                            from ..common.models import TimeRange
                            segment_data['timerange'] = TimeRange(value="0:0")
                        
                        # Parse JSON fields (including get_urls into GetUrl models)
                        for field in ['ts_offset', 'last_duration', 'get_urls']:
                            if field in segment_data and isinstance(segment_data[field], str):
                                try:
                                    import json
                                    parsed = json.loads(segment_data[field])
                                    if field == 'get_urls' and isinstance(parsed, list):
                                        from .models import GetUrl
                                        segment_data[field] = [GetUrl(**url) if isinstance(url, dict) else url for url in parsed]
                                    else:
                                        segment_data[field] = parsed
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
                        from ..common.models import TimeRange
                        segment_data['timerange'] = TimeRange(value=f"{timerange_start}_{timerange_end}")
                    elif timerange_start:
                        from ..common.models import TimeRange
                        segment_data['timerange'] = TimeRange(value=str(timerange_start))
                    else:
                        # Provide a default timerange if both are missing
                        from ..common.models import TimeRange
                        segment_data['timerange'] = TimeRange(value="0:0")
                    
                    # Parse JSON fields (including get_urls into GetUrl models)
                    for field in ['ts_offset', 'last_duration', 'get_urls']:
                        if field in segment_data and isinstance(segment_data[field], str):
                            try:
                                import json
                                parsed = json.loads(segment_data[field])
                                if field == 'get_urls' and isinstance(parsed, list):
                                    from .models import GetUrl
                                    segment_data[field] = [GetUrl(**url) if isinstance(url, dict) else url for url in parsed]
                                else:
                                    segment_data[field] = parsed
                            except (json.JSONDecodeError, TypeError):
                                pass
                    segments.append(FlowSegment(**segment_data))
            
            # Filter by timerange if provided
            if timerange:
                try:
                    from ..core.timerange_utils import parse_tams_timerange
                    query_start, query_end = parse_tams_timerange(timerange)
                    
                    # Only filter if we got valid start and end times (not infinity)
                    if query_start is not None and query_end is not None and query_end != float('inf'):
                        filtered_segments = []
                        for segment in segments:
                            # Parse segment timerange
                            if segment.timerange and segment.timerange.value:
                                seg_start, seg_end = parse_tams_timerange(segment.timerange.value)
                                
                                # Check if segment overlaps with query timerange
                                # Overlap: segment_start < query_end AND segment_end > query_start
                                if seg_start is not None and seg_end is not None:
                                    if seg_start < query_end and seg_end > query_start:
                                        filtered_segments.append(segment)
                            
                        segments = filtered_segments
                        logger.debug(f"Filtered {len(segments)} segments matching timerange {timerange} (query: {query_start}s to {query_end}s)")
                except Exception as e:
                    logger.warning(f"Failed to filter segments by timerange {timerange}: {e}")
                    # Continue with unfiltered segments if parsing fails
            
            # Populate get_urls if missing (per TAMS spec - service should auto-populate controlled URLs)
            for segment in segments:
                if not segment.get_urls or len(segment.get_urls) == 0:
                    logger.debug(f"Auto-populating get_urls for segment with object_id: {segment.object_id}")
                    # Generate get_urls for the object_id
                    get_urls = await self._generate_get_urls(segment.object_id)
                    if get_urls:
                        logger.debug(f"Generated {len(get_urls)} get_urls for object_id: {segment.object_id}")
                        segment.get_urls = get_urls
                    else:
                        logger.warning(f"Failed to generate get_urls for object_id: {segment.object_id}")
            
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
            
            # Maintain normalized relationship and object reference tracking
            try:
                import json as _json
                import uuid as _uuid
                # 1) Insert into flow_object_references if not already present
                existing = self.vast_db.query("flow_object_references").select("id").where(
                    f"flow_id = '{flow_id}' AND object_id = '{segment_data.get('object_id')}'"
                ).execute()
                already_exists = False
                if isinstance(existing, dict) and 'data' in existing:
                    data = existing['data']
                    # VAST returns column arrays; check if any rows exist
                    if isinstance(data, dict) and data and any(len(col) > 0 for col in data.values() if isinstance(col, list)):
                        already_exists = True
                    elif isinstance(data, list) and len(data) > 0:
                        already_exists = True
                elif isinstance(existing, list) and len(existing) > 0:
                    already_exists = True
                
                if not already_exists:
                    ref_row = {
                        "id": str(_uuid.uuid4()),
                        "flow_id": flow_id,
                        "object_id": segment_data.get('object_id'),
                        "created": get_tams_timestamp()
                    }
                    ref_row = prepare_data_for_pyarrow(ref_row)
                    self.vast_db.insert_record("flow_object_references", ref_row)
                
                # Note: We no longer update objects.referenced_by_flows as JSON
                # It's computed dynamically from segments/flow_object_references tables using JOINs
                # This is cleaner, avoids JSON parsing complexity, and uses normalized relational data
            except Exception as rel_err:
                logger.warning("Failed to update flow-object references for flow %s, object %s: %s", flow_id, segment_data.get('object_id'), rel_err)
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
    
    def _derive_content_type_from_flow(self, flow: Any) -> str:
        """
        Derive content-type (container MIME type) from Flow per TAMS 8.0 spec.
        AppNote 0018 requires content-type inheritance from Flow when storage is allocated.
        
        Priority:
        1. flow.container (authoritative source per TAMS spec)
        2. Heuristics based on format/codec
        """
        try:
            # First check flow.container (authoritative source per TAMS spec)
            flow_container = getattr(flow, 'container', None)
            if flow_container and isinstance(flow_container, str) and '/' in flow_container:
                return flow_container
            
            # Fallback to heuristics based on format/codec
            flow_format = getattr(flow, 'format', None)
            flow_codec = getattr(flow, 'codec', None)
            
            # Common TAMS container mappings based on format
            # Default to video/mp2t (MPEG-TS) for video flows as shown in TAMS examples
            if flow_format == "urn:x-nmos:format:video":
                # Video flows: typically MPEG-TS container
                return "video/mp2t"
            elif flow_format == "urn:x-nmos:format:audio":
                # Audio flows: can vary, default to MPEG-TS
                return "video/mp2t"  # Audio can also be in MPEG-TS
            elif flow_format == "urn:x-nmos:format:image":
                # Image flows: derive from codec if available
                if flow_codec:
                    # Codec like "image/jpeg" can serve as container for images
                    return flow_codec
                return "image/jpeg"  # Default for images
            elif flow_format == "urn:x-nmos:format:data":
                return "application/octet-stream"  # Default for data
            else:
                # Fallback: try to use codec if available, otherwise default
                if flow_codec and '/' in flow_codec:
                    return flow_codec
                return "video/mp2t"  # Conservative default per TAMS examples
        except Exception as e:
            logger.warning(f"Failed to derive content-type from flow: {e}")
            return "video/mp2t"  # Safe fallback
    
    async def create_flow_storage(self, flow_id: str, storage_request: FlowStoragePost) -> Optional[FlowStorage]:
        """Create storage allocation for a flow"""
        try:
            import uuid
            import json
            
            # Get Flow to derive content-type (TAMS 8.0 AppNote 0018 requirement)
            from ..flows.service import FlowStorageService
            flow_service = FlowStorageService(self.vast_db, self.s3_client)
            flow = await flow_service.get_flow(flow_id)
            if not flow:
                raise HTTPException(status_code=404, detail=f"Flow {flow_id} not found")
            
            # Derive content-type from Flow per TAMS 8.0 spec
            content_type = self._derive_content_type_from_flow(flow)
            logger.debug(f"Derived content-type '{content_type}' from flow {flow_id} (format: {getattr(flow, 'format', None)}, codec: {getattr(flow, 'codec', None)})")
            
            # Get default storage backend
            storage_id = None
            if storage_request.storage_id:
                storage_id = storage_request.storage_id
            else:
                # Get default storage backend
                from ..storagebackends.service import StorageBackendService
                backend_service = StorageBackendService(self.vast_db, self.s3_client)
                backends = await backend_service.get_storage_backends()
                default_backend = next((b for b in backends if b.default_storage), None)
                if default_backend:
                    storage_id = default_backend.id
                    logger.debug(f"Using default storage backend: {storage_id}")
                else:
                    logger.warning("No default storage backend found, storage_id will be None")
            
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
                now = get_tams_timestamp()
                year = str(now.year)
                month = f"{now.month:02d}"
                date = f"{now.day:02d}"
                
                # Use TAMS path format: {tams_storage_path}/{year}/{month}/{date}/{object_id}
                # Normalize paths to avoid double slashes
                tams_path = self.settings.tams_storage_path.strip('/')
                relative_storage_path = f"{tams_path}/{year}/{month}/{date}/{object_id}"
                
                # Look up backend if storage_id is provided
                backend_info = None
                if storage_id:
                    try:
                        from ..storagebackends.service import StorageBackendService
                        backend_service = StorageBackendService(self.vast_db, self.s3_client)
                        backend = await backend_service.get_storage_backend(storage_id)
                        if backend:
                            backend_info = backend.model_dump()
                            # Include root_path in storage_path if backend has one
                            backend_root_path = backend.root_path
                            if backend_root_path:
                                backend_root_path = backend_root_path.strip('/')
                                storage_path = f"{backend_root_path}/{relative_storage_path}"
                            else:
                                storage_path = relative_storage_path
                        else:
                            storage_path = relative_storage_path
                    except Exception as e:
                        logger.warning(f"Failed to load storage backend {storage_id} for root_path: {e}")
                        storage_path = relative_storage_path
                else:
                    storage_path = relative_storage_path
                
                # Generate presigned URL for upload with content-type (TAMS 8.0 requirement)
                # Pass relative_storage_path (without root_path) since _generate_presigned_url
                # will use key_prefix from storage_backend if provided
                presigned_url = await self._generate_presigned_url(
                    key=relative_storage_path,
                    operation="put_object",
                    expiration=self.settings.s3_presigned_url_upload_timeout,
                    storage_backend=backend_info,
                    content_type=content_type
                )
                
                if not presigned_url:
                    raise HTTPException(status_code=500, detail=f"Failed to generate presigned URL for object {object_id}")
                
                # Create MediaObject with content-type in put_url (TAMS 8.0 requirement)
                # Use model_validate with alias key for proper serialization
                put_url_data = {
                    "url": presigned_url,
                    "content-type": content_type,  # Required by TAMS 8.0 spec (using alias)
                    "headers": {}
                }
                media_object = MediaObject(
                    object_id=object_id,
                    put_url=HttpRequest.model_validate(put_url_data),
                    metadata={"storage_path": storage_path}  # Full path including root_path
                )
                
                media_objects.append(media_object)
                
                # Create Object record in database with storage_id, storage_path, and content_type in metadata
                from ..objects.models import Object
                object_metadata = {
                    "storage_path": storage_path,  # Full path including root_path
                    "content_type": content_type  # Store for GET URL generation (TAMS 8.0)
                }
                if storage_id:
                    object_metadata["storage_id"] = storage_id
                
                obj = Object(
                    id=object_id,
                    referenced_by_flows=[flow_id],
                    first_referenced_by_flow=flow_id,
                    metadata=object_metadata,
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
            if isinstance(result, dict) and 'data' in result and isinstance(result['data'], dict):
                # VAST tabular format: columns dict -> reconstruct first row
                columns = result['data']
                if not columns:
                    return None
                # Determine row count
                try:
                    row_count = len(next(iter(columns.values())))
                except StopIteration:
                    row_count = 0
                if row_count == 0:
                    return None
                obj_data = {}
                for col, values in columns.items():
                    try:
                        obj_data[col] = values[0] if isinstance(values, list) and values else values
                    except Exception:
                        obj_data[col] = None
            elif isinstance(result, list) and result:
                first = result[0]
                obj_data = dict(first) if isinstance(first, dict) else first
            else:
                return None
            
            # Parse metadata JSON string if present
            if 'metadata' in obj_data and isinstance(obj_data['metadata'], str):
                try:
                    import json
                    obj_data['metadata'] = json.loads(obj_data['metadata'])
                except (json.JSONDecodeError, TypeError):
                    obj_data['metadata'] = None
            
            return obj_data
        except Exception as e:
            logger.error("Failed to get object %s: %s", object_id, e)
            return None
    
    async def _create_object(self, obj):
        """Create an object"""
        try:
            now = get_tams_timestamp()
            obj.created = now
            
            object_data = obj.model_dump()
            
            # Convert timestamp fields to PyArrow format using centralized function
            from ..common.storage.timestamp_utils import prepare_data_for_pyarrow
            object_data = prepare_data_for_pyarrow(object_data)
            
            self.vast_db.insert_record("objects", object_data)
            return True
        except Exception as e:
            logger.error("Failed to create object: %s", e)
            return False
    
    async def _generate_presigned_url(self, key: str, operation: str, expiration: int = 3600, storage_backend: Optional[Dict[str, Any]] = None, content_type: Optional[str] = None) -> Optional[str]:
        """Generate presigned URL; prefer backend-specific endpoint/credentials if provided.
        
        Args:
            key: S3 object key
            operation: S3 operation (get_object, put_object)
            expiration: URL expiration in seconds
            storage_backend: Optional backend-specific config
            content_type: MIME type for PUT requests (TAMS 8.0 requirement - must match Flow)
        """
        try:
            import inspect
            http_method = 'GET' if operation.lower() in ('get', 'get_object') else 'PUT'
            # Use provided content_type or fallback (TAMS 8.0 requires content-type for PUT)
            final_content_type = content_type or 'application/octet-stream'
            
            # Only use storage_backend if it has valid credentials (both access_key and secret_key)
            access_key = storage_backend.get('access_key') if storage_backend else None
            secret_key = storage_backend.get('secret_key') if storage_backend else None
            has_valid_credentials = (
                access_key and secret_key and 
                isinstance(access_key, str) and isinstance(secret_key, str) and
                access_key.strip() and secret_key.strip()
            )
            
            if storage_backend and has_valid_credentials:
                from vasts3 import S3Client, S3Config
                
                # Use backend-specific values when available, fallback to settings
                backend_root_path = storage_backend.get('root_path') or getattr(self.settings, 's3_root_path', None)
                key_prefix = backend_root_path.strip('/') if backend_root_path else None
                
                cfg = S3Config(
                    endpoint_url=storage_backend.get('endpoint_url'),
                    bucket_name=storage_backend.get('bucket_name') or self.settings.s3_bucket_name,
                    access_key=access_key,
                    secret_key=secret_key,
                    region=storage_backend.get('region') or self.settings.s3_region,
                    use_ssl=storage_backend.get('use_ssl') if storage_backend.get('use_ssl') is not None else self.settings.s3_use_ssl,
                    chunk_size=self.settings.vaststore_s3_chunk_size,
                    max_concurrent_parts=self.settings.vaststore_s3_max_concurrent_parts,
                    key_prefix=key_prefix,
                )
                tmp_client = S3Client(cfg)
                sig = inspect.signature(tmp_client.generate_presigned_url)
                supported = set(sig.parameters.keys())
                candidate_kwargs = {
                    'key': key,
                    'operation': operation,
                    'expires_in': expiration,
                    'expiration': expiration,
                    'method': http_method,
                    'http_method': http_method,
                    'content_type': final_content_type if http_method == 'PUT' else None,
                    # Note: response_content_type and response_content_disposition are not included
                    # because VAST S3 backend does not support these parameters in presigned URLs
                }
                # Remove None values
                candidate_kwargs = {k: v for k, v in candidate_kwargs.items() if v is not None}
                kwargs = {k: v for k, v in candidate_kwargs.items() if k in supported}
                return tmp_client.generate_presigned_url(**kwargs)
            sig = inspect.signature(self.s3_client.generate_presigned_url)
            supported = set(sig.parameters.keys())
            candidate_kwargs = {
                'key': key,
                'operation': operation,
                'expires_in': expiration,
                'expiration': expiration,
                'method': http_method,
                'http_method': http_method,
                'content_type': final_content_type if http_method == 'PUT' else None,
                # Note: response_content_type and response_content_disposition are not included
                # because VAST S3 backend does not support these parameters in presigned URLs
            }
            # Remove None values
            candidate_kwargs = {k: v for k, v in candidate_kwargs.items() if v is not None}
            kwargs = {k: v for k, v in candidate_kwargs.items() if k in supported}
            return self.s3_client.generate_presigned_url(**kwargs)
        except Exception as e:
            logger.error("Failed to generate presigned URL: %s", e)
            return None
    
    async def _generate_get_urls(self, object_id: str) -> Optional[List[Dict[str, Any]]]:
        """Generate get_urls for an object_id"""
        try:
            # Get the object to find its storage path and storage_id
            obj_dict = await self._get_object(object_id)
            
            # Try to get storage path, storage_id, and content_type from object metadata
            storage_path = None
            storage_id = None
            content_type = None
            if obj_dict:
                # Handle both Object model (with _internal_metadata) and raw dict
                metadata = None
                if hasattr(obj_dict, '_internal_metadata'):
                    metadata = obj_dict._internal_metadata
                elif isinstance(obj_dict, dict):
                    metadata_raw = obj_dict.get('metadata', {})
                    if isinstance(metadata_raw, str):
                        import json
                        try:
                            metadata = json.loads(metadata_raw)
                        except:
                            metadata = {}
                    elif isinstance(metadata_raw, dict):
                        metadata = metadata_raw
                
                if metadata and isinstance(metadata, dict):
                    storage_path = metadata.get('storage_path')
                    storage_id = metadata.get('storage_id')
                    content_type = metadata.get('content_type')  # Retrieve stored content-type for GET URLs
                
                # If no storage path in metadata, reconstruct from created timestamp
                if not storage_path:
                    created = obj_dict.get('created') if isinstance(obj_dict, dict) else getattr(obj_dict, 'created', None)
                    if created:
                        # Parse created timestamp if it's a string
                        if isinstance(created, str):
                            from datetime import datetime
                            try:
                                dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                            except:
                                dt = get_tams_timestamp()
                        else:
                            dt = created if hasattr(created, 'year') else get_tams_timestamp()
                        
                        year = str(dt.year)
                        month = f"{dt.month:02d}"
                        date = f"{dt.day:02d}"
                        tams_path = self.settings.tams_storage_path.strip('/')
                        relative_path = f"{tams_path}/{year}/{month}/{date}/{object_id}"
                        
                        # Include root_path if storage_id is available
                        if storage_id:
                            try:
                                from ..storagebackends.service import StorageBackendService
                                backend_service = StorageBackendService(self.vast_db, self.s3_client)
                                backend = await backend_service.get_storage_backend(storage_id)
                                if backend and backend.root_path:
                                    root_path = backend.root_path.strip('/')
                                    storage_path = f"{root_path}/{relative_path}"
                                else:
                                    storage_path = relative_path
                            except Exception as e:
                                logger.warning(f"Failed to load backend {storage_id} for path reconstruction: {e}")
                                storage_path = relative_path
                        else:
                            storage_path = relative_path
            
            # Fallback: if object doesn't exist or path can't be determined, use current date
            if not storage_path:
                logger.warning(f"Object {object_id} not found or no storage path, using current date for path reconstruction")
                now = get_tams_timestamp()
                year = str(now.year)
                month = f"{now.month:02d}"
                date = f"{now.day:02d}"
                tams_path = self.settings.tams_storage_path.strip('/')
                relative_path = f"{tams_path}/{year}/{month}/{date}/{object_id}"
                
                # Include root_path if storage_id is available
                if storage_id:
                    try:
                        from ..storagebackends.service import StorageBackendService
                        backend_service = StorageBackendService(self.vast_db, self.s3_client)
                        backend = await backend_service.get_storage_backend(storage_id)
                        if backend and backend.root_path:
                            root_path = backend.root_path.strip('/')
                            storage_path = f"{root_path}/{relative_path}"
                        else:
                            storage_path = relative_path
                    except Exception as e:
                        logger.warning(f"Failed to load backend {storage_id} for fallback path: {e}")
                        storage_path = relative_path
                else:
                    storage_path = relative_path
            
            # Generate presigned GET URL
            backend_info = None
            relative_storage_path = storage_path
            if storage_id:
                try:
                    from ..storagebackends.service import StorageBackendService
                    backend_service = StorageBackendService(self.vast_db, self.s3_client)
                    backend = await backend_service.get_storage_backend(storage_id)
                    if backend:
                        backend_info = backend.model_dump()
                        # If storage_path includes root_path, strip it for use with key_prefix
                        backend_root_path = backend.root_path
                        if backend_root_path:
                            backend_root_path = backend_root_path.strip('/')
                            if storage_path.startswith(backend_root_path + '/'):
                                relative_storage_path = storage_path[len(backend_root_path) + 1:]
                            elif storage_path == backend_root_path:
                                relative_storage_path = ""
                except Exception as e:
                    logger.warning(f"Failed to load storage backend {storage_id}: {e}")
            
            get_url = await self._generate_presigned_url(
                key=relative_storage_path,
                operation="get_object",
                expiration=self.settings.s3_presigned_url_download_timeout if hasattr(self.settings, 's3_presigned_url_download_timeout') else 3600,
                storage_backend=backend_info,
                content_type=content_type  # Use stored content-type for response-content-type header
            )
            
            if not get_url:
                return None
            
            # If no storage_id from object metadata, try to get default storage backend
            if not storage_id:
                from ..storagebackends.service import StorageBackendService
                backend_service = StorageBackendService(self.vast_db, self.s3_client)
                backends = await backend_service.get_storage_backends()
                default_backend = next((b for b in backends if b.default_storage), None)
                if default_backend:
                    storage_id = default_backend.id
                    logger.debug(f"Using default storage backend for get_urls: {storage_id}")
                else:
                    # Generate a valid TAMS UUID as last resort
                    import uuid
                    storage_id = str(uuid.uuid4())
                    logger.warning(f"No storage_id found for object {object_id}, generated UUID: {storage_id}")
            
            # Return get_urls in TAMS format
            from .models import GetUrl
            get_url_obj = GetUrl(
                url=get_url,
                storage_id=storage_id,
                presigned=True,
                controlled=True,
                store_type="http_object_store",
                provider=self.settings.s3_provider if hasattr(self.settings, 's3_provider') else "aws",
                store_product=self.settings.s3_store_product if hasattr(self.settings, 's3_store_product') else "s3"
            )
            return [get_url_obj]
        except Exception as e:
            logger.error(f"Failed to generate get_urls for object {object_id}: {e}")
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
